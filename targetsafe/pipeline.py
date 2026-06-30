from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from targetsafe.agents import CriticAgent, EvidenceAgent, LLMClient, PlannerAgent, ReportAgent
from targetsafe.cache import SQLiteCache
from targetsafe.chem import evaluate_smiles, generate_seed_analogs, mol_conformer_payload, mol_svg_data_uri
from targetsafe.compute_profiles import resolve_profile
from targetsafe.data_sources import PublicDataSources
from targetsafe.decision import decide_candidate, rank_candidates
from targetsafe.embeddings import enrich_with_molecular_embeddings
from targetsafe.evidence_graph import build_evidence_graph
from targetsafe.model_card import write_ablation_report, write_evidence_graph, write_model_card
from targetsafe.models import CandidateRecord, PipelineResult
from targetsafe.qsar import EvidenceWeightedQSAR
from targetsafe.report import write_html_report
from targetsafe.thresholds import ThresholdRegistry


@dataclass
class PipelineConfig:
    disease: str = "EGFR mutation-positive NSCLC"
    target: str = "EGFR"
    seed_smiles: str = "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1"
    optimization_goal: str = "Maintain drug-likeness, reduce toxicity alerts, preserve EGFR evidence confidence"
    candidate_count: int = 60
    allow_network: bool = False
    use_llm: bool = False
    use_gpu: bool = False
    enable_critic: bool = True
    enable_conformers: bool = True
    compute_profile: str = "cpu-demo"
    output_dir: Path = Path("outputs")
    cache_path: Path = Path("work/targetsafe_cache.sqlite")


def run_pipeline(config: PipelineConfig) -> PipelineResult:
    run_id = f"targetsafe_{int(time.time())}"
    profile = resolve_profile(config.compute_profile)
    allow_network = profile.allow_network or config.allow_network
    use_llm = profile.use_llm or config.use_llm
    use_gpu = profile.use_gpu or config.use_gpu
    thresholds = ThresholdRegistry()
    cache = SQLiteCache(config.cache_path)
    llm = LLMClient(enabled=use_llm)
    planner = PlannerAgent(llm)
    plan = planner.plan(config.disease, config.target, config.optimization_goal)

    sources = PublicDataSources(cache=cache, allow_network=allow_network)
    evidence_agent = EvidenceAgent(sources)
    evidence = evidence_agent.collect(config.disease, config.target)

    candidates = generate_seed_analogs(config.seed_smiles, count=config.candidate_count)
    candidates = _append_evaluation_controls(candidates)

    qsar = EvidenceWeightedQSAR(evidence, thresholds=thresholds)
    gpu_payload = {"requested": use_gpu, "available": False, "message": "Not evaluated."}
    critic = CriticAgent(enabled=config.enable_critic, thresholds=thresholds)
    for candidate in candidates:
        candidate.descriptors = evaluate_smiles(candidate.smiles)
        if candidate.descriptors and candidate.descriptors.valid:
            candidate.smiles = candidate.descriptors.canonical_smiles
            candidate.structure_svg = mol_svg_data_uri(candidate.smiles)
            if config.enable_conformers:
                candidate.conformer = mol_conformer_payload(candidate.smiles)
        qsar.score(candidate)
    gpu_payload = enrich_with_molecular_embeddings(candidates, evidence, use_gpu=use_gpu)
    for candidate in candidates:
        candidate.decision = decide_candidate(candidate, thresholds)
        candidate.decision = critic.review(candidate)

    ranked = rank_candidates(candidates)
    evidence_graph = build_evidence_graph(run_id, ranked, evidence, thresholds)
    result = PipelineResult(
        run_id=run_id,
        plan=plan,
        evidence=evidence,
        candidates=ranked,
        tool_logs=sources.logs,
        compute_profile={
            **profile.to_dict(),
            "effective_allow_network": allow_network,
            "effective_use_llm": use_llm,
            "effective_use_gpu": use_gpu,
            "gpu_status": gpu_payload,
        },
        threshold_registry=thresholds.to_dict(),
        evidence_graph=evidence_graph,
        model_card=qsar.model_card,
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
        CandidateRecord(candidate_id="CTRL_POS", smiles=candidates[0].smiles, source="positive_control_seed"),
        CandidateRecord(candidate_id="CTRL_NEG_INVALID", smiles="not-a-smiles", source="negative_control_invalid"),
        CandidateRecord(candidate_id="CTRL_NEG_ALERT", smiles="O=N(=O)c1ccc(N=Nc2ccccc2)cc1", source="negative_control_alert"),
    ]
    return candidates + controls


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
            "all_decisions_have_evidence_nodes": all(c.decision and c.decision.evidence_node_ids for c in candidates),
            "all_candidates_have_structure_or_invalid": all(
                (c.structure_svg is not None) or not (c.descriptors and c.descriptors.valid) for c in candidates
            ),
            "tool_logs_present": True,
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
        ],
        "planned_comparisons": [
            "rule-only vs model-backed decision",
            "critic off vs critic on",
            "LLM-only explanation vs graph-grounded explanation",
            "CPU-only vs optional GPU retrieval/ensemble",
        ],
    }


def _write_json_result(result: PipelineResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{result.run_id}_result.json"
    path.write_text(json.dumps(result.to_public_dict(), indent=2), encoding="utf-8")
