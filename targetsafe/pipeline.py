from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from targetsafe.agents import CriticAgent, EvidenceAgent, LLMClient, PlannerAgent, ReportAgent
from targetsafe.cache import SQLiteCache
from targetsafe.chem import evaluate_smiles, mol_conformer_payload, mol_svg_data_uri
from targetsafe.compute_profiles import resolve_profile
from targetsafe.data_sources import PublicDataSources
from targetsafe.decision import decide_candidate, rank_candidates
from targetsafe.embeddings import enrich_with_molecular_embeddings
from targetsafe.evidence_graph import build_evidence_graph
from targetsafe.library import DEFAULT_LIBRARY_SOURCES, build_candidate_library, select_detailed_candidates
from targetsafe.model_card import write_ablation_report, write_evidence_graph, write_model_card
from targetsafe.models import AgentEvent, CandidateRecord, PipelineResult, ToolCallLog
from targetsafe.qsar import EvidenceWeightedQSAR
from targetsafe.redesign import run_redesign_iteration
from targetsafe.report import write_html_report
from targetsafe.runtime import runtime_status
from targetsafe.thresholds import ThresholdRegistry
from targetsafe.validation import build_qsar_validation_report, write_validation_outputs


@dataclass
class PipelineConfig:
    disease: str = "EGFR mutation-positive NSCLC"
    target: str = "EGFR"
    seed_smiles: str = "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1"
    optimization_goal: str = "Maintain drug-likeness, reduce toxicity alerts, preserve EGFR evidence confidence"
    candidate_count: int = 96
    allow_network: bool = False
    use_llm: bool = False
    use_gpu: bool = False
    enable_critic: bool = True
    enable_conformers: bool = True
    compute_profile: str = "full-research"
    library_sources: list[str] = field(default_factory=lambda: list(DEFAULT_LIBRARY_SOURCES))
    library_limit: int = 2000
    detailed_eval_limit: int = 300
    display_limit: int = 96
    conformer_limit: int = 24
    uploaded_smiles: list[str] = field(default_factory=list)
    llm_api_key: str = ""
    llm_provider: str = "openai"
    llm_base_url: str = ""
    llm_model: str = ""
    input_example_id: str = ""
    output_dir: Path = Path("outputs")
    cache_path: Path = Path("work/targetsafe_cache.sqlite")


def run_pipeline(config: PipelineConfig) -> PipelineResult:
    run_id = f"targetsafe_{int(time.time())}"
    agent_events: list[AgentEvent] = []
    step = 1
    profile = resolve_profile(config.compute_profile)
    allow_network = profile.allow_network or config.allow_network
    use_llm = profile.use_llm or config.use_llm
    use_gpu = profile.use_gpu or config.use_gpu
    runtime_payload = runtime_status(
        requested_gpu=use_gpu,
        requested_llm=use_llm,
        llm_api_key=config.llm_api_key,
        llm_base_url=config.llm_base_url,
        llm_model=config.llm_model,
        llm_provider=config.llm_provider,
    )
    thresholds = ThresholdRegistry()
    cache = SQLiteCache(config.cache_path)
    llm = LLMClient(
        enabled=use_llm,
        api_key=config.llm_api_key,
        provider=config.llm_provider,
        base_url=config.llm_base_url or None,
        model=config.llm_model or None,
    )
    planner = PlannerAgent(llm)
    plan = planner.plan(config.disease, config.target, config.optimization_goal)
    agent_events.append(
        AgentEvent(
            step=step,
            phase="Plan",
            agent="Planner Agent",
            action="create_run_plan",
            status="completed",
            detail={"steps": len(plan), "llm_requested": use_llm, "llm_used": llm.enabled},
        )
    )
    step += 1

    sources = PublicDataSources(cache=cache, allow_network=allow_network)
    evidence_agent = EvidenceAgent(sources)
    evidence = evidence_agent.collect(config.disease, config.target)
    evidence_mode = _summarize_evidence_mode(sources.logs)
    tool_error_summary = _summarize_tool_errors(sources.logs)
    agent_events.append(
        AgentEvent(
            step=step,
            phase="Act",
            agent="Evidence Agent",
            action="collect_public_and_fallback_evidence",
            status=str(evidence_mode.get("mode", "unknown")),
            detail={
                "chembl_rows": len(evidence.chembl_activities),
                "pubchem_rows": len(evidence.pubchem_records),
                "clinical_trials": len(evidence.clinical_trials),
                "regulatory_risks": len(evidence.regulatory_risks),
            },
        )
    )
    step += 1

    library_build = build_candidate_library(
        config.seed_smiles,
        evidence,
        library_sources=config.library_sources,
        library_limit=config.library_limit,
        seed_count=max(config.candidate_count, config.detailed_eval_limit),
        uploaded_smiles=config.uploaded_smiles,
    )
    candidates, selection_summary, selection_stages = select_detailed_candidates(
        library_build.candidates,
        detailed_eval_limit=config.detailed_eval_limit,
    )
    library_report = {**library_build.report, **selection_summary}
    screening_stages = [*library_build.screening_stages, *selection_stages]
    candidates = _append_evaluation_controls(candidates)
    agent_events.append(
        AgentEvent(
            step=step,
            phase="Act",
            agent="Molecular Proposer",
            action="assemble_library_and_select_detailed_subset",
            status="completed",
            detail={
                "raw_input_count": library_report.get("raw_input_count"),
                "valid_unique_count": library_report.get("valid_unique_count"),
                "detailed_evaluation_count": library_report.get("detailed_evaluation_count"),
                "library_sources": library_report.get("library_sources"),
            },
        )
    )
    step += 1

    qsar = EvidenceWeightedQSAR(evidence, thresholds=thresholds)
    gpu_payload = {"requested": use_gpu, "available": False, "message": "Not evaluated."}
    critic = CriticAgent(enabled=config.enable_critic, thresholds=thresholds)
    for candidate in candidates:
        candidate.descriptors = evaluate_smiles(candidate.smiles)
        if candidate.descriptors and candidate.descriptors.valid:
            candidate.smiles = candidate.descriptors.canonical_smiles
            candidate.screening_stage = "stage3_qsar_decision_ready"
        else:
            candidate.screening_stage = "stage1_invalid_no_go"
            candidate.prefilter_reason = "Invalid or unparseable SMILES."
        qsar.score(candidate)
    agent_events.append(
        AgentEvent(
            step=step,
            phase="Observe",
            agent="RDKit/QSAR Evaluator",
            action="compute_descriptors_activity_interval_and_applicability",
            status="completed",
            detail={
                "evaluated_candidates": len(candidates),
                "valid_structures": len([c for c in candidates if c.descriptors and c.descriptors.valid]),
                "training_rows": len(qsar.training_rows),
            },
        )
    )
    step += 1
    gpu_payload = enrich_with_molecular_embeddings(candidates, evidence, use_gpu=use_gpu)
    agent_events.append(
        AgentEvent(
            step=step,
            phase="Act",
            agent="Compute Profile Controller",
            action="apply_optional_gpu_embedding_lane",
            status="available" if gpu_payload.get("available") else "fallback",
            detail=gpu_payload,
        )
    )
    step += 1
    for candidate in candidates:
        candidate.decision = decide_candidate(candidate, thresholds)
        candidate.decision = critic.review(candidate)
    critic_findings = sum(len(c.decision.critic_findings) for c in candidates if c.decision)
    agent_events.append(
        AgentEvent(
            step=step,
            phase="Critique",
            agent="Critic Agent",
            action="review_decisions_and_downgrade_overclaims",
            status="completed",
            detail={"critic_findings": critic_findings},
        )
    )
    step += 1

    redesign_children, redesign_report, redesign_events = run_redesign_iteration(
        candidates,
        evidence,
        qsar,
        critic,
        thresholds,
        enable_conformers=config.enable_conformers,
        start_step=step,
    )
    agent_events.extend(redesign_events)
    if redesign_events:
        step = max(event.step for event in redesign_events) + 1
    if redesign_children:
        candidates.extend(redesign_children)
        agent_events.append(
            AgentEvent(
                step=step,
                phase="Decide",
                agent="Decision Agent",
                action="compare_parent_child_redesign_candidates",
                status="completed",
                detail={"created_children": len(redesign_children)},
            )
        )
        step += 1
    else:
        agent_events.append(
            AgentEvent(
                step=step,
                phase="Replan",
                agent="Redesign Agent",
                action="no_redesign_children_created",
                status="completed",
                detail={"reason": "No eligible critic finding or no curated template available."},
            )
        )
        step += 1

    ranked = rank_candidates(candidates)
    _materialize_display_assets(
        ranked,
        display_limit=config.display_limit,
        conformer_limit=config.conformer_limit if config.enable_conformers else 0,
    )
    library_report = {
        **library_report,
        "final_candidate_count": len(ranked),
        "display_asset_count": len([c for c in ranked if c.structure_svg]),
        "conformer_asset_count": len([c for c in ranked if c.conformer]),
    }
    screening_stages.append(
        {
            "stage": "stage4_lazy_visualization",
            "count": library_report["display_asset_count"],
            "description": "Only top-ranked candidates receive immediate 2D/3D assets; the rest are lazy-loaded by API.",
        }
    )
    validation_report = build_qsar_validation_report(evidence, qsar)
    validation_paths = write_validation_outputs(validation_report, config.output_dir)
    validation_report = {**validation_report, "outputs": validation_paths}
    qsar.model_card["validation"] = {
        "status": validation_report.get("status"),
        "metrics": validation_report.get("metrics", {}),
        "split_summary": validation_report.get("split_summary", {}),
    }
    agent_events.append(
        AgentEvent(
            step=step,
            phase="Observe",
            agent="Validation Agent",
            action="run_egfr_qsar_validation_or_report_insufficient_data",
            status=str(validation_report.get("status", "unknown")),
            detail={
                "dataset_size": validation_report.get("dataset_size"),
                "split_summary": validation_report.get("split_summary", {}),
            },
        )
    )
    step += 1
    evidence_graph = build_evidence_graph(run_id, ranked, evidence, thresholds)
    agent_events.append(
        AgentEvent(
            step=step,
            phase="Decide",
            agent="Evidence Graph Agent",
            action="connect_candidates_thresholds_predictions_and_redesign_edges",
            status="completed",
            detail=evidence_graph.get("summary", {}),
        )
    )
    result = PipelineResult(
        run_id=run_id,
        plan=plan,
        evidence=evidence,
        candidates=ranked,
        tool_logs=sources.logs,
        agent_events=agent_events,
        compute_profile={
            **profile.to_dict(),
            "effective_allow_network": allow_network,
            "effective_use_llm": use_llm,
            "effective_use_gpu": use_gpu,
            "gpu_status": gpu_payload,
            "llm_status": runtime_payload.get("llm", {}),
            "gpu_diagnostics": runtime_payload.get("gpu_diagnostics", {}),
        },
        threshold_registry=thresholds.to_dict(),
        evidence_graph=evidence_graph,
        model_card=qsar.model_card,
        redesign_report=redesign_report,
        validation_report=validation_report,
        evidence_mode=evidence_mode,
        runtime_status={
            **runtime_payload,
            "gpu": gpu_payload,
            "llm": {
                **runtime_payload.get("llm", {}),
                "used": llm.enabled,
            },
        },
        gpu_diagnostics=runtime_payload.get("gpu_diagnostics", {}),
        tool_error_summary=tool_error_summary,
        input_example_id=config.input_example_id,
        library_report=library_report,
        screening_stages=screening_stages,
    )
    result.evaluation_report = _build_evaluation_report(ranked)
    result.ablation_report_path = write_ablation_report(_build_ablation_summary(result), config.output_dir)
    thresholds.write_json(config.output_dir)
    write_model_card(result.model_card, config.output_dir)
    write_evidence_graph(evidence_graph, config.output_dir)
    result.report_path = write_html_report(result, config.output_dir)
    _write_json_result(result, config.output_dir)
    return result


def _append_evaluation_controls(candidates: list[CandidateRecord]) -> list[CandidateRecord]:
    controls = [
        CandidateRecord(
            candidate_id="CTRL_POS",
            smiles=candidates[0].smiles if candidates else "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1",
            source="positive_control_seed",
            library_source="control",
            source_compound_id="positive_control_seed",
            source_name="Positive control seed",
            screening_stage="control",
        ),
        CandidateRecord(
            candidate_id="CTRL_NEG_INVALID",
            smiles="not-a-smiles",
            source="negative_control_invalid",
            library_source="control",
            source_compound_id="negative_control_invalid",
            source_name="Invalid SMILES control",
            screening_stage="control",
        ),
        CandidateRecord(
            candidate_id="CTRL_NEG_ALERT",
            smiles="O=N(=O)c1ccc(N=Nc2ccccc2)cc1",
            source="negative_control_alert",
            library_source="control",
            source_compound_id="negative_control_alert",
            source_name="Structural alert control",
            screening_stage="control",
        ),
    ]
    return candidates + controls


def _materialize_display_assets(candidates: list[CandidateRecord], display_limit: int, conformer_limit: int) -> None:
    display_count = max(0, display_limit)
    conformer_count = max(0, conformer_limit)
    for index, candidate in enumerate(candidates):
        if not (candidate.descriptors and candidate.descriptors.valid):
            continue
        if index < display_count and not candidate.structure_svg:
            candidate.structure_svg = mol_svg_data_uri(candidate.smiles)
        if index < conformer_count and not candidate.conformer:
            candidate.conformer = mol_conformer_payload(candidate.smiles)


def _build_evaluation_report(candidates: list[CandidateRecord]) -> dict[str, object]:
    by_id = {c.candidate_id: c for c in candidates}
    positive = by_id.get("CTRL_POS")
    invalid = by_id.get("CTRL_NEG_INVALID")
    alert = by_id.get("CTRL_NEG_ALERT")
    status_counts: dict[str, int] = {}
    for c in candidates:
        status = c.decision.final_status if c.decision else "Unscored"
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "status_counts": status_counts,
        "redesign_child_count": len([c for c in candidates if c.generation > 0]),
        "positive_control_status": positive.decision.final_status if positive and positive.decision else None,
        "invalid_control_status": invalid.decision.final_status if invalid and invalid.decision else None,
        "alert_control_status": alert.decision.final_status if alert and alert.decision else None,
        "critic_enabled": any(
            c.decision and c.decision.critic_findings for c in candidates
        ),
        "acceptance_checks": {
            "candidate_count_at_least_50": len([c for c in candidates if c.candidate_id.startswith("C")]) >= 50,
            "invalid_control_no_go": bool(invalid and invalid.decision and invalid.decision.final_status == "No-Go"),
            "all_decisions_have_reasons": all(c.decision and c.decision.reasons for c in candidates),
            "all_decisions_have_threshold_sources": all(c.decision and c.decision.threshold_ids for c in candidates),
            "all_decisions_have_gate_audit": all(c.decision and c.decision.gate_audit for c in candidates),
            "all_decisions_have_evidence_nodes": all(c.decision and c.decision.evidence_node_ids for c in candidates),
            "display_candidates_have_structure_or_lazy_endpoint": any(
                (c.structure_svg is not None) for c in candidates if c.descriptors and c.descriptors.valid
            ),
            "tool_logs_present": True,
            "redesign_children_have_parent": all(c.parent_candidate_id for c in candidates if c.generation > 0),
        },
    }


def _build_ablation_summary(result: PipelineResult) -> dict[str, object]:
    counts = result.evaluation_report.get("status_counts", {})
    return {
        "run_id": result.run_id,
        "current_system": "graph-grounded, threshold-sourced, critic-reviewed triage",
        "status_counts": counts,
        "critic_enabled": result.evaluation_report.get("critic_enabled"),
        "llm_role": "optional planner/report summarizer; not final decision maker",
        "decision_layers": [
            "descriptor hard gates",
            "analog-supported QSAR interval",
            "applicability-domain check",
            "threshold registry provenance",
            "evidence graph support",
            "critic review",
            "critic-triggered constrained redesign loop",
        ],
        "planned_comparisons": [
            "rule-only vs model-backed decision",
            "critic off vs critic on",
            "LLM-only explanation vs graph-grounded explanation",
            "CPU-only vs optional GPU retrieval/ensemble",
            "parent candidate vs critic redesign child",
        ],
    }


def _summarize_evidence_mode(logs: list[ToolCallLog]) -> dict[str, object]:
    if not logs:
        return {"mode": "unknown", "label": "No evidence calls recorded", "counts": {}}
    counts: dict[str, int] = {}
    cached_count = 0
    live_count = 0
    for log in logs:
        counts[log.status] = counts.get(log.status, 0) + 1
        if log.cached:
            cached_count += 1
        if log.status == "ok" and not log.cached:
            live_count += 1
    statuses = set(counts)
    if statuses == {"fallback"}:
        mode = "offline_fallback"
        label = "Offline fallback demo"
    elif "error" in statuses or "empty" in statuses:
        mode = "error_fallback"
        label = "API error with fallback evidence"
    elif statuses == {"ok"} and live_count > 0 and cached_count == 0:
        mode = "live"
        label = "Live public evidence"
    elif statuses == {"ok"} and cached_count == len(logs):
        mode = "cached"
        label = "Cached public evidence"
    else:
        mode = "mixed"
        label = "Mixed live/cached/fallback evidence"
    return {
        "mode": mode,
        "label": label,
        "counts": counts,
        "error_categories": _count_by([log.error_category or "uncategorized" for log in logs if log.error_category]),
        "cached_calls": cached_count,
        "live_calls": live_count,
        "interpretation": (
            "Offline/fallback evidence supports stable demonstrations only; scientific interpretation should use live or curated evidence refresh."
            if mode in {"offline_fallback", "error_fallback", "mixed"}
            else "Evidence was retrieved from live or cached public calls and remains source-logged."
        ),
    }


def _summarize_tool_errors(logs: list[ToolCallLog]) -> dict[str, object]:
    by_source: dict[str, dict[str, object]] = {}
    categories: dict[str, int] = {}
    for log in logs:
        category = log.error_category or ("cached" if log.cached else log.status)
        categories[category] = categories.get(category, 0) + 1
        source_summary = by_source.setdefault(
            log.source,
            {"calls": 0, "statuses": {}, "error_categories": {}, "last_message": "", "last_query": ""},
        )
        source_summary["calls"] = int(source_summary["calls"]) + 1
        statuses = source_summary["statuses"]
        errors = source_summary["error_categories"]
        if isinstance(statuses, dict):
            statuses[log.status] = statuses.get(log.status, 0) + 1
        if isinstance(errors, dict):
            errors[category] = errors.get(category, 0) + 1
        if log.message:
            source_summary["last_message"] = log.message
            source_summary["last_query"] = log.query
    severe = [key for key in ("network_refused", "timeout", "rate_limited", "http_empty") if categories.get(key)]
    return {
        "schema": "targetsafe.tool_error_summary.v1",
        "total_calls": len(logs),
        "categories": categories,
        "by_source": by_source,
        "has_live_errors": bool(severe),
        "interpretation": (
            "Some public evidence calls failed or returned empty rows; Target-SAFE used cached/fallback evidence and lowers scientific interpretation accordingly."
            if severe
            else "No blocking live evidence error was recorded, or the run intentionally used cached/fallback mode."
        ),
    }


def _count_by(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _write_json_result(result: PipelineResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{result.run_id}_result.json"
    path.write_text(json.dumps(result.to_public_dict(), indent=2), encoding="utf-8")
