from __future__ import annotations

from typing import Any

from targetsafe.chem import tanimoto_like_similarity
from targetsafe.models import CandidateRecord, EvidenceBundle


def build_target_readiness(evidence: EvidenceBundle, target_profile: dict[str, Any]) -> dict[str, Any]:
    chembl_rows = evidence.chembl_activities or []
    pchembl_rows = [
        row for row in chembl_rows
        if row.get("pchembl_value") is not None or row.get("pchembl") is not None
    ]
    reference_count = len([drug for drug in evidence.known_inhibitors if drug.get("smiles")])
    scoring_mode = str(target_profile.get("scoring_mode") or "evidence_only")
    enough_rows = len(pchembl_rows) >= 25
    validated_pilot = scoring_mode == "scored_pilot"
    status = "ready" if validated_pilot and enough_rows else "pilot_limited" if validated_pilot else "evidence_only"
    blockers: list[str] = []
    if not validated_pilot:
        blockers.append("target_specific_qsar_not_validated")
    if not enough_rows:
        blockers.append("insufficient_pchembl_rows")
    if reference_count < 3:
        blockers.append("limited_reference_drug_context")
    return {
        "schema": "targetsafe.target_readiness.v1",
        "target": evidence.target,
        "disease": evidence.disease,
        "scoring_mode": scoring_mode,
        "status": status,
        "badge": target_profile.get("badge", "Evidence-only"),
        "chembl_activity_rows": len(chembl_rows),
        "pchembl_rows": len(pchembl_rows),
        "known_reference_count": reference_count,
        "threshold_registry_available": True,
        "validation_required": not (validated_pilot and enough_rows),
        "blockers": blockers,
        "interpretation": (
            "Target-specific Go/Hold/No-Go scoring is enabled for this pilot, but validation quality still depends on live or curated activity rows."
            if validated_pilot
            else "This target is shown as evidence-readiness and descriptor triage only. Confident target-specific Go decisions are suppressed until assay/QSAR validation exists."
        ),
    }


def apply_target_interpretation(candidates: list[CandidateRecord], readiness: dict[str, Any]) -> None:
    scoring_mode = str(readiness.get("scoring_mode") or "evidence_only")
    interpretation = str(readiness.get("interpretation") or "")
    if scoring_mode == "scored_pilot":
        for candidate in candidates:
            candidate.target_specific_interpretation = interpretation
        return
    for candidate in candidates:
        candidate.target_specific_interpretation = interpretation
        decision = candidate.decision
        if not decision:
            continue
        if decision.final_status == "Go":
            decision.final_status = "Hold"
            decision.uncertainty.append("target_specific_validation_missing")
            decision.reasons.insert(0, "Evidence-only target profile: confident Go is withheld until target-specific QSAR/assay validation exists.")
            decision.criteria["target_readiness"] = "review"


def build_activity_cliff_report(candidates: list[CandidateRecord]) -> dict[str, Any]:
    pairs: list[dict[str, Any]] = []
    scored = [
        candidate for candidate in candidates
        if candidate.descriptors and candidate.descriptors.valid and candidate.predicted_activity is not None
    ]
    for index, left in enumerate(scored):
        for right in scored[index + 1:]:
            similarity = tanimoto_like_similarity(left.smiles, right.smiles)
            if similarity < 0.62:
                continue
            delta = abs(float(left.predicted_activity or 0.0) - float(right.predicted_activity or 0.0))
            if delta < 0.75:
                continue
            pair = {
                "left_candidate_id": left.candidate_id,
                "right_candidate_id": right.candidate_id,
                "similarity": round(similarity, 3),
                "activity_delta": round(delta, 3),
                "risk_level": "high" if similarity >= 0.72 and delta >= 1.2 else "review",
                "interpretation": "Similar structures with materially different predicted activity indicate an activity-cliff/QSAR fragility zone.",
            }
            pairs.append(pair)
    pairs = sorted(pairs, key=lambda item: (item["risk_level"] != "high", -float(item["activity_delta"])))[:20]
    by_candidate: dict[str, list[dict[str, Any]]] = {}
    for pair in pairs:
        for key in ("left_candidate_id", "right_candidate_id"):
            candidate_id = str(pair[key])
            by_candidate.setdefault(candidate_id, []).append(pair)
    for candidate in candidates:
        candidate.activity_cliff_flags = by_candidate.get(candidate.candidate_id, [])[:3]
    status = "detected" if pairs else "not_detected"
    return {
        "schema": "targetsafe.activity_cliff_report.v1",
        "status": status,
        "pair_count": len(pairs),
        "minimum_similarity": 0.62,
        "minimum_activity_delta": 0.75,
        "pairs": pairs,
        "interpretation": (
            "Potential activity cliffs were found. Treat affected predictions as fragile and prioritize orthogonal assay confirmation."
            if pairs
            else "No activity-cliff-like pair was detected in the detailed evaluated set; this is not proof that cliffs are absent."
        ),
    }


def build_assay_plan(candidates: list[CandidateRecord], readiness: dict[str, Any], cliff_report: dict[str, Any]) -> dict[str, Any]:
    recommendations: list[dict[str, Any]] = []
    for candidate in candidates:
        decision = candidate.decision
        if not decision:
            continue
        items = _candidate_assays(candidate, readiness)
        candidate.assay_recommendations = items
        for item in items:
            recommendations.append({**item, "candidate_id": candidate.candidate_id})
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda item: (priority_order.get(str(item.get("priority")), 9), item.get("candidate_id", "")))
    return {
        "schema": "targetsafe.assay_plan.v1",
        "recommendation_count": len(recommendations),
        "candidate_count": len([candidate for candidate in candidates if candidate.assay_recommendations]),
        "top_recommendations": recommendations[:30],
        "activity_cliff_pair_count": cliff_report.get("pair_count", 0),
        "interpretation": "Assay Planner recommends the next validation step that would most reduce Hold-state uncertainty; it does not replace medicinal chemistry or wet-lab review.",
    }


def build_scientific_extensions(
    candidates: list[CandidateRecord],
    evidence: EvidenceBundle,
    target_profile: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    readiness = build_target_readiness(evidence, target_profile)
    apply_target_interpretation(candidates, readiness)
    cliff_report = build_activity_cliff_report(candidates)
    assay_plan = build_assay_plan(candidates, readiness, cliff_report)
    summary = {
        "schema": "targetsafe.scientific_extensions.v1",
        "enabled": ["assay_planner", "activity_cliff_radar", "target_readiness"],
        "target_readiness_status": readiness.get("status"),
        "activity_cliff_status": cliff_report.get("status"),
        "assay_recommendation_count": assay_plan.get("recommendation_count"),
        "novelty_positioning": "The agent does not only rank candidates; it identifies fragile evidence, suppresses overconfident target transfer, and proposes the next uncertainty-reducing assay.",
    }
    return assay_plan, cliff_report, readiness, summary


def _candidate_assays(candidate: CandidateRecord, readiness: dict[str, Any]) -> list[dict[str, Any]]:
    decision = candidate.decision
    desc = candidate.descriptors
    if not decision:
        return []
    if desc and not desc.valid:
        return [
            {
                "assay": "Input correction / structure curation",
                "priority": "high",
                "uncertainty_resolved": "invalid_smiles",
                "cost_time_class": "computational_minutes",
                "decision_impact": "Required before any biological assay is meaningful.",
                "rationale": "Invalid structures are No-Go controls and should not enter assay planning.",
            }
        ]
    items: list[dict[str, Any]] = []
    if decision.final_status == "No-Go":
        blockers = ", ".join(decision.hard_gate_failures[:2]) or "hard blocker"
        return [
            {
                "assay": "Medicinal chemistry triage review",
                "priority": "high",
                "uncertainty_resolved": blockers,
                "cost_time_class": "expert_review",
                "decision_impact": "Confirm whether the blocker is intrinsic or caused by malformed input.",
                "rationale": "No-Go candidates should not be advanced to potency assays without blocker review.",
            }
        ]
    if not candidate.in_applicability_domain or "target_specific_validation_missing" in decision.uncertainty:
        items.append(
            {
                "assay": f"{readiness.get('target', 'target')} biochemical IC50 confirmation",
                "priority": "high",
                "uncertainty_resolved": "target_activity_and_applicability_domain",
                "cost_time_class": "wet_lab_days",
                "decision_impact": "Can move a Hold candidate toward Go or confirm deprioritization.",
                "rationale": "Target-specific evidence is insufficient for confident prioritization.",
            }
        )
    if candidate.prediction_interval and float(candidate.prediction_interval.get("width", 0.0)) > 1.4:
        items.append(
            {
                "assay": "Orthogonal potency assay or replicate assay",
                "priority": "medium",
                "uncertainty_resolved": "broad_prediction_interval",
                "cost_time_class": "wet_lab_days",
                "decision_impact": "Narrows activity interval used by the conservative decision gate.",
                "rationale": "The model interval is broad enough to prevent a confident Go decision.",
            }
        )
    if candidate.activity_cliff_flags:
        items.append(
            {
                "assay": "Matched analog pair potency retest",
                "priority": "medium",
                "uncertainty_resolved": "activity_cliff_fragility",
                "cost_time_class": "wet_lab_days",
                "decision_impact": "Tests whether a small structural change invalidates the predicted ranking.",
                "rationale": "Potential activity cliff pairs make local QSAR interpolation fragile.",
            }
        )
    if desc and (desc.alerts or desc.severe_alerts):
        items.append(
            {
                "assay": "In vitro safety counter-screen / alert review",
                "priority": "medium" if not desc.severe_alerts else "high",
                "uncertainty_resolved": "structural_alert_risk",
                "cost_time_class": "panel_days",
                "decision_impact": "Determines whether the structural alert is acceptable, mitigable, or blocking.",
                "rationale": "Structural alerts are context signals, not final toxicity conclusions.",
            }
        )
    if not items and decision.final_status == "Go":
        items.append(
            {
                "assay": "Confirmatory target potency and ADMET mini-panel",
                "priority": "low",
                "uncertainty_resolved": "go_candidate_confirmation",
                "cost_time_class": "wet_lab_days",
                "decision_impact": "Confirms whether computational Go survives first experimental checks.",
                "rationale": "Go is a triage label, not proof of efficacy or safety.",
            }
        )
    return items[:4]
