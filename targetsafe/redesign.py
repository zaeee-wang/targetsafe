from __future__ import annotations

from typing import Any

from targetsafe.chem import evaluate_smiles, mol_conformer_payload, mol_svg_data_uri
from targetsafe.decision import decide_candidate
from targetsafe.library import diversity_cluster_id
from targetsafe.models import AgentEvent, CandidateRecord, EvidenceBundle
from targetsafe.qsar import EvidenceWeightedQSAR
from targetsafe.reference_drugs import REFERENCE_EGFR_DRUGS
from targetsafe.thresholds import ThresholdRegistry


def run_redesign_iteration(
    candidates: list[CandidateRecord],
    evidence: EvidenceBundle,
    qsar: EvidenceWeightedQSAR,
    critic: Any,
    thresholds: ThresholdRegistry,
    *,
    enable_conformers: bool = True,
    max_children: int = 6,
    start_step: int = 1,
) -> tuple[list[CandidateRecord], dict[str, Any], list[AgentEvent]]:
    """Create one constrained critic-driven redesign iteration.

    The function intentionally uses curated EGFR reference templates rather than
    arbitrary SMILES surgery. This keeps the demo chemically conservative: the
    agent proposes a safer/in-domain comparison candidate, then re-runs the same
    deterministic evaluation stack.
    """

    events: list[AgentEvent] = []
    children: list[CandidateRecord] = []
    comparisons: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    step = start_step

    for parent in _redesign_parent_candidates(candidates):
        if len(children) >= max_children:
            break
        reason = _redesign_reason(parent, thresholds)
        if reason == "invalid_smiles":
            skipped.append(
                {
                    "candidate_id": parent.candidate_id,
                    "reason": reason,
                    "action": "No redesign attempted; fix or replace invalid input first.",
                }
            )
            events.append(
                AgentEvent(
                    step=step,
                    phase="Critique",
                    agent="Critic Agent",
                    action="skip_invalid_redesign",
                    status="blocked",
                    candidate_id=parent.candidate_id,
                    detail={"reason": reason},
                )
            )
            step += 1
            continue

        template = _template_for_reason(parent, evidence, reason)
        if not template:
            skipped.append({"candidate_id": parent.candidate_id, "reason": reason, "action": "No curated EGFR template available."})
            continue

        action = _redesign_action(reason, template)
        child = CandidateRecord(
            candidate_id=f"{parent.candidate_id}_R1",
            smiles=str(template["smiles"]),
            source="critic_redesign_suggestion",
            library_source="critic_redesign",
            source_compound_id=str(template.get("chembl_id") or template.get("drug_id") or "critic_template"),
            source_name=str(template.get("name") or "Curated EGFR template"),
            diversity_cluster=diversity_cluster_id(str(template["smiles"])),
            screening_stage="stage3_redesign_re_evaluation",
            parent_candidate_id=parent.candidate_id,
            generation=parent.generation + 1,
            redesign_reason=reason,
            redesign_action=action,
        )

        events.extend(
            [
                AgentEvent(
                    step=step,
                    phase="Critique",
                    agent="Critic Agent",
                    action="identify_redesign_need",
                    status="review",
                    candidate_id=parent.candidate_id,
                    detail={"reason": reason, "parent_status": parent.decision.final_status if parent.decision else "Unscored"},
                ),
                AgentEvent(
                    step=step + 1,
                    phase="Replan",
                    agent="Planner Agent",
                    action="select_constrained_redesign_strategy",
                    status="completed",
                    candidate_id=parent.candidate_id,
                    detail={"action": action, "template": template.get("name")},
                ),
            ]
        )
        step += 2

        _evaluate_child(child, qsar, critic, thresholds, enable_conformers=enable_conformers)
        children.append(child)
        comparisons.append(_comparison(parent, child, reason, action))
        events.append(
            AgentEvent(
                step=step,
                phase="Re-evaluate",
                agent="Redesign Agent",
                action="score_redesign_child",
                status=child.decision.final_status if child.decision else "Unscored",
                candidate_id=child.candidate_id,
                detail={
                    "parent_candidate_id": parent.candidate_id,
                    "reason": reason,
                    "decision_delta": _decision_delta(parent, child),
                },
            )
        )
        step += 1

    report = {
        "schema": "targetsafe.redesign_report.v1",
        "iteration_limit": 1,
        "definition": "Critic findings trigger constrained EGFR analog/template suggestions, then the same evaluator re-scores child candidates.",
        "created_children": len(children),
        "comparisons": comparisons,
        "skipped": skipped,
    }
    return children, report, events


def _redesign_parent_candidates(candidates: list[CandidateRecord]) -> list[CandidateRecord]:
    ranked: list[tuple[int, CandidateRecord]] = []
    for candidate in candidates:
        decision = candidate.decision
        if not decision or candidate.generation > 0:
            continue
        reason = _redesign_reason(candidate, ThresholdRegistry())
        priority = {
            "severe_alert": 0,
            "high_logp": 1,
            "out_of_domain": 2,
            "broad_prediction_interval": 3,
            "invalid_smiles": 4,
        }.get(reason, 9)
        if priority < 9:
            ranked.append((priority, candidate))
    ranked.sort(key=lambda item: (item[0], item[1].candidate_id))
    return [candidate for _, candidate in ranked]


def _redesign_reason(candidate: CandidateRecord, thresholds: ThresholdRegistry) -> str:
    desc = candidate.descriptors
    if not desc or not desc.valid:
        return "invalid_smiles"
    if desc.severe_alerts:
        return "severe_alert"
    if desc.logp > thresholds.get("logp_extreme_max").value - 0.4:
        return "high_logp"
    interval = candidate.prediction_interval or {}
    if not candidate.in_applicability_domain:
        return "out_of_domain"
    if float(interval.get("width", 0.0) or 0.0) > thresholds.get("prediction_interval_width_max").value:
        return "broad_prediction_interval"
    return ""


def _template_for_reason(candidate: CandidateRecord, evidence: EvidenceBundle, reason: str) -> dict[str, Any] | None:
    references = [drug for drug in REFERENCE_EGFR_DRUGS if drug.get("smiles")]
    if not references:
        return None
    if reason == "high_logp":
        parent_logp = candidate.descriptors.logp if candidate.descriptors else 99.0
        scored = [(evaluate_smiles(str(drug["smiles"])).logp, drug) for drug in references]
        scored.sort(key=lambda item: (abs(item[0] - min(item[0], parent_logp - 0.8)), item[0]))
        return scored[0][1]
    if reason in {"out_of_domain", "broad_prediction_interval"} and candidate.nearest_analogs:
        nearest_name = str(candidate.nearest_analogs[0].get("name", "")).lower()
        for drug in references:
            if str(drug.get("name", "")).lower().split()[0] in nearest_name:
                return drug
    if reason == "severe_alert":
        for drug in references:
            desc = evaluate_smiles(str(drug["smiles"]))
            if desc.valid and not desc.severe_alerts:
                return drug
    return references[0]


def _redesign_action(reason: str, template: dict[str, Any]) -> str:
    name = str(template.get("name", "EGFR reference analog"))
    actions = {
        "high_logp": f"Compare against lower-lipophilicity curated EGFR template ({name}).",
        "severe_alert": f"Replace alert-bearing motif with curated EGFR reference template ({name}).",
        "out_of_domain": f"Anchor toward nearest known EGFR analog template ({name}) to restore applicability-domain support.",
        "broad_prediction_interval": f"Use in-domain EGFR template ({name}) as a lower-uncertainty comparison child.",
    }
    return actions.get(reason, f"Use curated EGFR reference template ({name}) for conservative re-evaluation.")


def _evaluate_child(
    child: CandidateRecord,
    qsar: EvidenceWeightedQSAR,
    critic: Any,
    thresholds: ThresholdRegistry,
    *,
    enable_conformers: bool,
) -> None:
    child.descriptors = evaluate_smiles(child.smiles)
    if child.descriptors and child.descriptors.valid:
        child.smiles = child.descriptors.canonical_smiles
        child.structure_svg = mol_svg_data_uri(child.smiles)
        if enable_conformers:
            child.conformer = mol_conformer_payload(child.smiles)
    qsar.score(child)
    child.decision = decide_candidate(child, thresholds)
    child.decision = critic.review(child)


def _comparison(parent: CandidateRecord, child: CandidateRecord, reason: str, action: str) -> dict[str, Any]:
    return {
        "parent_candidate_id": parent.candidate_id,
        "child_candidate_id": child.candidate_id,
        "reason": reason,
        "action": action,
        "parent": _snapshot(parent),
        "child": _snapshot(child),
        "interpretation": (
            "A child candidate is a constrained comparison suggestion, not an optimized drug claim. "
            "It must pass the same threshold, applicability, and evidence checks as any other candidate."
        ),
    }


def _snapshot(candidate: CandidateRecord) -> dict[str, Any]:
    desc = candidate.descriptors
    interval = candidate.prediction_interval or {}
    return {
        "status": candidate.decision.final_status if candidate.decision else "Unscored",
        "logp": round(desc.logp, 3) if desc else None,
        "qed": round(desc.qed, 3) if desc else None,
        "sa_score": round(desc.sa_score, 3) if desc else None,
        "alerts": len(desc.alerts) if desc else None,
        "severe_alerts": len(desc.severe_alerts) if desc else None,
        "activity_lower": interval.get("lower"),
        "interval_width": interval.get("width"),
        "applicability_score": round(candidate.applicability_score, 3),
        "in_applicability_domain": candidate.in_applicability_domain,
    }


def _decision_delta(parent: CandidateRecord, child: CandidateRecord) -> str:
    parent_status = parent.decision.final_status if parent.decision else "Unscored"
    child_status = child.decision.final_status if child.decision else "Unscored"
    if parent_status == child_status:
        return "same_status"
    return f"{parent_status}_to_{child_status}"
