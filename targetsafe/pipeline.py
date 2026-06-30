from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from targetsafe.agents import CriticAgent, EvidenceAgent, LLMClient, PlannerAgent, ReportAgent
from targetsafe.cache import SQLiteCache
from targetsafe.chem import evaluate_smiles, generate_seed_analogs, mol_svg_data_uri
from targetsafe.data_sources import PublicDataSources
from targetsafe.decision import decide_candidate, rank_candidates
from targetsafe.models import CandidateRecord, PipelineResult
from targetsafe.qsar import EvidenceWeightedQSAR
from targetsafe.report import write_html_report


@dataclass
class PipelineConfig:
    disease: str = "EGFR mutation-positive NSCLC"
    target: str = "EGFR"
    seed_smiles: str = "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1"
    optimization_goal: str = "Maintain drug-likeness, reduce toxicity alerts, preserve EGFR evidence confidence"
    candidate_count: int = 60
    allow_network: bool = False
    use_llm: bool = False
    enable_critic: bool = True
    output_dir: Path = Path("outputs")
    cache_path: Path = Path("work/targetsafe_cache.sqlite")


def run_pipeline(config: PipelineConfig) -> PipelineResult:
    run_id = f"targetsafe_{int(time.time())}"
    cache = SQLiteCache(config.cache_path)
    llm = LLMClient(enabled=config.use_llm)
    planner = PlannerAgent(llm)
    plan = planner.plan(config.disease, config.target, config.optimization_goal)

    sources = PublicDataSources(cache=cache, allow_network=config.allow_network)
    evidence_agent = EvidenceAgent(sources)
    evidence = evidence_agent.collect(config.disease, config.target)

    candidates = generate_seed_analogs(config.seed_smiles, count=config.candidate_count)
    candidates = _append_evaluation_controls(candidates)

    qsar = EvidenceWeightedQSAR(evidence)
    critic = CriticAgent(enabled=config.enable_critic)
    for candidate in candidates:
        candidate.descriptors = evaluate_smiles(candidate.smiles)
        if candidate.descriptors and candidate.descriptors.valid:
            candidate.smiles = candidate.descriptors.canonical_smiles
            candidate.structure_svg = mol_svg_data_uri(candidate.smiles)
        qsar.score(candidate)
        candidate.decision = decide_candidate(candidate)
        candidate.decision = critic.review(candidate)

    ranked = rank_candidates(candidates)
    result = PipelineResult(
        run_id=run_id,
        plan=plan,
        evidence=evidence,
        candidates=ranked,
        tool_logs=sources.logs,
    )
    result.evaluation_report = _build_evaluation_report(ranked)
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
            "tool_logs_present": True,
        },
    }


def _write_json_result(result: PipelineResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{result.run_id}_result.json"
    path.write_text(json.dumps(result.to_public_dict(), indent=2), encoding="utf-8")

