from __future__ import annotations

from targetsafe.models import CandidateRecord, DecisionResult
from targetsafe.thresholds import ThresholdRegistry


def decide_candidate(candidate: CandidateRecord, thresholds: ThresholdRegistry | None = None) -> DecisionResult:
    registry = thresholds or ThresholdRegistry()
    desc = candidate.descriptors
    threshold_ids = [
        "molecular_weight_extreme_max",
        "logp_extreme_max",
        "tpsa_extreme_max",
        "qed_min_floor",
        "sa_score_max",
        "activity_pchembl_lower_bound_min",
        "applicability_similarity_min",
        "evidence_confidence_min_for_go",
        "prediction_interval_width_max",
    ]
    if not desc or not desc.valid:
        return DecisionResult(
            final_status="No-Go",
            total_score=0.0,
            hard_gate_failures=["invalid_smiles"],
            reasons=["SMILES failed structural validation."],
            follow_up=["Replace or regenerate the candidate before evaluation."],
            threshold_ids=threshold_ids,
            criteria={"molecular_identity": "block"},
        )

    failures: list[str] = []
    reasons: list[str] = []
    uncertainty: list[str] = []
    follow_up: list[str] = []
    criteria: dict[str, str] = {}

    _check_upper(
        desc.molecular_weight,
        registry.get("molecular_weight_extreme_max").value,
        "molecular_weight_extreme",
        f"Molecular weight is high ({desc.molecular_weight:.1f}).",
        failures,
        reasons,
        criteria,
        "molecular_weight",
    )
    _check_upper(
        desc.logp,
        registry.get("logp_extreme_max").value,
        "logp_extreme",
        f"LogP is high ({desc.logp:.2f}).",
        failures,
        reasons,
        criteria,
        "logp",
    )
    _check_upper(
        desc.tpsa,
        registry.get("tpsa_extreme_max").value,
        "tpsa_extreme",
        f"TPSA is high ({desc.tpsa:.1f}).",
        failures,
        reasons,
        criteria,
        "tpsa",
    )
    _check_lower(
        desc.qed,
        registry.get("qed_min_floor").value,
        "qed_low",
        f"QED is low ({desc.qed:.2f}).",
        failures,
        reasons,
        criteria,
        "qed",
    )
    _check_upper(
        desc.sa_score,
        registry.get("sa_score_max").value,
        "synthetic_accessibility_low",
        f"SA score is high ({desc.sa_score:.2f}).",
        failures,
        reasons,
        criteria,
        "synthetic_accessibility",
    )

    if desc.severe_alerts:
        failures.append("severe_structural_alert")
        reasons.append(f"Severe alert(s): {', '.join(desc.severe_alerts[:3])}")
        criteria["structural_alerts"] = "block"
    elif desc.alerts:
        uncertainty.append(f"Structural alert(s) require review: {', '.join(desc.alerts[:3])}.")
        follow_up.append("Run focused toxicity and medicinal chemistry review.")
        criteria["structural_alerts"] = "review"
    else:
        criteria["structural_alerts"] = "pass"

    interval = candidate.prediction_interval or {}
    lower_bound = float(interval.get("lower") or candidate.predicted_activity or 0.0)
    interval_width = float(interval.get("width") or 9.9)
    activity_threshold = registry.get("activity_pchembl_lower_bound_min").value
    uncertainty_threshold = registry.get("prediction_interval_width_max").value
    evidence_threshold = registry.get("evidence_confidence_min_for_go").value
    ad_threshold = registry.get("applicability_similarity_min").value

    if lower_bound >= activity_threshold:
        criteria["conservative_activity"] = "pass"
    else:
        criteria["conservative_activity"] = "review"
        uncertainty.append(
            f"Conservative activity bound is below the Go floor ({lower_bound:.2f} < {activity_threshold:.2f} pChEMBL)."
        )
        follow_up.append("Confirm activity with target-specific assay or stronger analog evidence.")

    if candidate.in_applicability_domain and candidate.applicability_score >= ad_threshold:
        criteria["applicability_domain"] = "pass"
    else:
        criteria["applicability_domain"] = "review"
        uncertainty.append("QSAR applicability domain is weak; do not over-interpret activity.")
        follow_up.append("Review nearest ChEMBL analogs or collect target-specific assay evidence.")

    if interval_width <= uncertainty_threshold:
        criteria["prediction_uncertainty"] = "pass"
    else:
        criteria["prediction_uncertainty"] = "review"
        uncertainty.append(
            f"Prediction interval is broad ({interval_width:.2f} pChEMBL); model confidence is insufficient for Go."
        )

    if candidate.evidence_confidence >= evidence_threshold:
        criteria["evidence_support"] = "pass"
    else:
        criteria["evidence_support"] = "review"
        uncertainty.append("Evidence confidence is low.")
        follow_up.append("Require additional public or internal assay evidence before prioritization.")

    if desc.lipinski_violations:
        uncertainty.append(f"Lipinski violations: {desc.lipinski_violations}.")
        criteria["lipinski"] = "review"
    else:
        criteria["lipinski"] = "pass"

    if failures:
        status = "No-Go"
    elif all(value == "pass" for value in criteria.values()):
        status = "Go"
        reasons.append("Passed sourced hard gates, conservative activity bound, applicability-domain, and evidence checks.")
    else:
        status = "Hold"
        reasons.append("Candidate remains plausible but needs additional evidence, uncertainty reduction, or risk review.")

    if not follow_up:
        follow_up.append("Confirm with orthogonal assay, ADMET panel, and expert medicinal chemistry review.")

    passed = sum(1 for value in criteria.values() if value == "pass")
    blocked = sum(1 for value in criteria.values() if value == "block")
    total = max(1, len(criteria))
    support_score = 0.0 if blocked else passed / total

    return DecisionResult(
        final_status=status,
        total_score=round(max(0.0, min(1.0, support_score)), 3),
        hard_gate_failures=failures,
        reasons=reasons,
        uncertainty=uncertainty,
        follow_up=follow_up,
        threshold_ids=threshold_ids,
        criteria=criteria,
    )


def _check_upper(
    value: float,
    threshold: float,
    failure_id: str,
    reason: str,
    failures: list[str],
    reasons: list[str],
    criteria: dict[str, str],
    criterion_id: str,
) -> None:
    if value > threshold:
        failures.append(failure_id)
        reasons.append(reason)
        criteria[criterion_id] = "block"
    else:
        criteria[criterion_id] = "pass"


def _check_lower(
    value: float,
    threshold: float,
    failure_id: str,
    reason: str,
    failures: list[str],
    reasons: list[str],
    criteria: dict[str, str],
    criterion_id: str,
) -> None:
    if value < threshold:
        failures.append(failure_id)
        reasons.append(reason)
        criteria[criterion_id] = "block"
    else:
        criteria[criterion_id] = "pass"


def rank_candidates(candidates: list[CandidateRecord]) -> list[CandidateRecord]:
    order = {"Go": 0, "Hold": 1, "No-Go": 2}
    return sorted(
        candidates,
        key=lambda c: (
            order.get(c.decision.final_status if c.decision else "No-Go", 9),
            -(c.prediction_interval or {}).get("lower", 0.0),
            -(c.decision.total_score if c.decision else 0.0),
            c.candidate_id,
        ),
    )
