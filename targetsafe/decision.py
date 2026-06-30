from __future__ import annotations

from typing import Any

from targetsafe.models import CandidateRecord, DecisionResult, GateAudit
from targetsafe.thresholds import ThresholdRegistry, ThresholdRule


DECISION_POLICY_VERSION = "targetsafe.decision_policy.v2"


def decision_rulebook(thresholds: ThresholdRegistry | None = None) -> dict[str, Any]:
    registry = thresholds or ThresholdRegistry()
    return {
        "schema": "targetsafe.decision_rulebook.v1",
        "policy_version": DECISION_POLICY_VERSION,
        "plain_language": {
            "Go": (
                "Valid structure, no hard blockers, in applicability domain, conservative activity support, "
                "acceptable uncertainty, and sufficient graph evidence."
            ),
            "Hold": (
                "Valid or potentially useful molecule, but one or more review gates require more evidence, "
                "uncertainty reduction, analog review, API refresh, or expert medicinal chemistry review."
            ),
            "No-Go": (
                "Invalid structure, severe structural alert, or extreme descriptor blocker. Target-SAFE does "
                "not advance this candidate without regeneration or manual correction."
            ),
        },
        "thresholds": registry.to_dict(),
        "gate_semantics": {
            "pass": "Gate supports advancement.",
            "review": "Gate does not kill the candidate, but prevents confident Go.",
            "block": "Hard blocker; candidate becomes No-Go.",
        },
    }


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
        gate = GateAudit(
            gate_id="valid_smiles",
            criterion_id="molecular_identity",
            label="Valid molecular identity",
            observed_value=candidate.smiles,
            status="block",
            decision_effect="hard_block",
            message="SMILES failed structural validation.",
            source="SMILES parser / RDKit when available",
            rationale="A lead triage system cannot score a molecule whose structure cannot be parsed.",
        )
        return DecisionResult(
            final_status="No-Go",
            total_score=0.0,
            hard_gate_failures=["invalid_smiles"],
            reasons=["SMILES failed structural validation."],
            follow_up=["Replace or regenerate the candidate before evaluation."],
            threshold_ids=threshold_ids,
            criteria={"molecular_identity": "block"},
            gate_audit=[gate],
            decision_policy_version=DECISION_POLICY_VERSION,
        )

    failures: list[str] = []
    reasons: list[str] = []
    uncertainty: list[str] = []
    follow_up: list[str] = []
    criteria: dict[str, str] = {}
    gate_audit: list[GateAudit] = []

    _check_upper(
        desc.molecular_weight,
        registry.get("molecular_weight_extreme_max"),
        "molecular_weight_extreme",
        f"Molecular weight is high ({desc.molecular_weight:.1f}).",
        failures,
        reasons,
        criteria,
        gate_audit,
        "molecular_weight",
    )
    _check_upper(
        desc.logp,
        registry.get("logp_extreme_max"),
        "logp_extreme",
        f"LogP is high ({desc.logp:.2f}).",
        failures,
        reasons,
        criteria,
        gate_audit,
        "logp",
    )
    _check_upper(
        desc.tpsa,
        registry.get("tpsa_extreme_max"),
        "tpsa_extreme",
        f"TPSA is high ({desc.tpsa:.1f}).",
        failures,
        reasons,
        criteria,
        gate_audit,
        "tpsa",
    )
    _check_lower(
        desc.qed,
        registry.get("qed_min_floor"),
        "qed_low",
        f"QED is low ({desc.qed:.2f}).",
        failures,
        reasons,
        criteria,
        gate_audit,
        "qed",
    )
    _check_upper(
        desc.sa_score,
        registry.get("sa_score_max"),
        "synthetic_accessibility_low",
        f"SA score is high ({desc.sa_score:.2f}).",
        failures,
        reasons,
        criteria,
        gate_audit,
        "synthetic_accessibility",
    )

    if desc.severe_alerts:
        failures.append("severe_structural_alert")
        message = f"Severe alert(s): {', '.join(desc.severe_alerts[:3])}"
        reasons.append(message)
        criteria["structural_alerts"] = "block"
        gate_audit.append(
            GateAudit(
                gate_id="structural_alerts",
                criterion_id="structural_alerts",
                label="Severe structural alert screen",
                observed_value=desc.severe_alerts,
                status="block",
                decision_effect="hard_block",
                message=message,
                source="RDKit structural alert screen or Target-SAFE fallback alert patterns",
                rationale="Severe alerts are hard blockers in early triage because they can invalidate a confident lead claim.",
            )
        )
    elif desc.alerts:
        message = f"Structural alert(s) require review: {', '.join(desc.alerts[:3])}."
        uncertainty.append(message)
        follow_up.append("Run focused toxicity and medicinal chemistry review.")
        criteria["structural_alerts"] = "review"
        gate_audit.append(
            GateAudit(
                gate_id="structural_alerts",
                criterion_id="structural_alerts",
                label="Structural alert screen",
                observed_value=desc.alerts,
                status="review",
                decision_effect="review_required",
                message=message,
                source="RDKit structural alert screen or Target-SAFE fallback alert patterns",
                rationale="Non-severe alerts do not automatically kill a molecule, but they prevent a confident Go.",
            )
        )
    else:
        criteria["structural_alerts"] = "pass"
        gate_audit.append(
            GateAudit(
                gate_id="structural_alerts",
                criterion_id="structural_alerts",
                label="Structural alert screen",
                observed_value=[],
                status="pass",
                decision_effect="go_support",
                message="No structural alerts were detected by the available screen.",
                source="RDKit structural alert screen or Target-SAFE fallback alert patterns",
                rationale="Absence of known alerts supports, but does not prove, early safety plausibility.",
            )
        )

    interval = candidate.prediction_interval or {}
    lower_bound = float(interval.get("lower") or candidate.predicted_activity or 0.0)
    interval_width = float(interval.get("width") or 9.9)
    activity_rule = registry.get("activity_pchembl_lower_bound_min")
    uncertainty_rule = registry.get("prediction_interval_width_max")
    evidence_rule = registry.get("evidence_confidence_min_for_go")
    ad_rule = registry.get("applicability_similarity_min")

    if lower_bound >= activity_rule.value:
        criteria["conservative_activity"] = "pass"
        _append_threshold_gate(
            gate_audit,
            "conservative_activity",
            "conservative_activity",
            "Conservative activity lower bound",
            lower_bound,
            activity_rule,
            "pass",
            "go_support",
            f"Lower activity bound passes the Go floor ({lower_bound:.2f} >= {activity_rule.value:.2f} pChEMBL).",
        )
    else:
        criteria["conservative_activity"] = "review"
        message = (
            f"Conservative activity bound is below the Go floor "
            f"({lower_bound:.2f} < {activity_rule.value:.2f} pChEMBL)."
        )
        uncertainty.append(message)
        follow_up.append("Confirm activity with target-specific assay or stronger analog evidence.")
        _append_threshold_gate(
            gate_audit,
            "conservative_activity",
            "conservative_activity",
            "Conservative activity lower bound",
            lower_bound,
            activity_rule,
            "review",
            "review_required",
            message,
        )

    if candidate.in_applicability_domain and candidate.applicability_score >= ad_rule.value:
        criteria["applicability_domain"] = "pass"
        _append_threshold_gate(
            gate_audit,
            "applicability_domain",
            "applicability_domain",
            "QSAR applicability domain",
            candidate.applicability_score,
            ad_rule,
            "pass",
            "go_support",
            "Candidate is close enough to known analog evidence for the QSAR estimate to be considered in-domain.",
        )
    else:
        criteria["applicability_domain"] = "review"
        message = "QSAR applicability domain is weak; do not over-interpret activity."
        uncertainty.append(message)
        follow_up.append("Review nearest ChEMBL analogs or collect target-specific assay evidence.")
        _append_threshold_gate(
            gate_audit,
            "applicability_domain",
            "applicability_domain",
            "QSAR applicability domain",
            candidate.applicability_score,
            ad_rule,
            "review",
            "review_required",
            message,
        )

    if interval_width <= uncertainty_rule.value:
        criteria["prediction_uncertainty"] = "pass"
        _append_threshold_gate(
            gate_audit,
            "prediction_uncertainty",
            "prediction_uncertainty",
            "Prediction interval width",
            interval_width,
            uncertainty_rule,
            "pass",
            "go_support",
            f"Prediction interval is within the accepted width ({interval_width:.2f} <= {uncertainty_rule.value:.2f}).",
        )
    else:
        criteria["prediction_uncertainty"] = "review"
        message = f"Prediction interval is broad ({interval_width:.2f} pChEMBL); model confidence is insufficient for Go."
        uncertainty.append(message)
        _append_threshold_gate(
            gate_audit,
            "prediction_uncertainty",
            "prediction_uncertainty",
            "Prediction interval width",
            interval_width,
            uncertainty_rule,
            "review",
            "review_required",
            message,
        )

    if candidate.evidence_confidence >= evidence_rule.value:
        criteria["evidence_support"] = "pass"
        _append_threshold_gate(
            gate_audit,
            "evidence_support",
            "evidence_support",
            "Graph evidence confidence",
            candidate.evidence_confidence,
            evidence_rule,
            "pass",
            "go_support",
            "Candidate has enough graph-linked evidence for a cautious Go consideration.",
        )
    else:
        criteria["evidence_support"] = "review"
        message = "Evidence confidence is low."
        uncertainty.append(message)
        follow_up.append("Require additional public or internal assay evidence before prioritization.")
        _append_threshold_gate(
            gate_audit,
            "evidence_support",
            "evidence_support",
            "Graph evidence confidence",
            candidate.evidence_confidence,
            evidence_rule,
            "review",
            "review_required",
            message,
        )

    if desc.lipinski_violations:
        message = f"Lipinski violations: {desc.lipinski_violations}."
        uncertainty.append(message)
        criteria["lipinski"] = "review"
        gate_audit.append(
            GateAudit(
                gate_id="lipinski",
                criterion_id="lipinski",
                label="Lipinski review signal",
                observed_value=desc.lipinski_violations,
                status="review",
                decision_effect="review_required",
                message=message,
                source="Lipinski rule-of-five context",
                rationale="Lipinski violations are review signals here; extreme descriptor caps are the hard blockers.",
            )
        )
    else:
        criteria["lipinski"] = "pass"
        gate_audit.append(
            GateAudit(
                gate_id="lipinski",
                criterion_id="lipinski",
                label="Lipinski review signal",
                observed_value=0,
                status="pass",
                decision_effect="go_support",
                message="No Lipinski review violations detected.",
                source="Lipinski rule-of-five context",
                rationale="This supports oral drug-likeness plausibility but does not prove developability.",
            )
        )

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
        gate_audit=gate_audit,
        decision_policy_version=DECISION_POLICY_VERSION,
    )


def _check_upper(
    value: float,
    rule: ThresholdRule,
    failure_id: str,
    reason: str,
    failures: list[str],
    reasons: list[str],
    criteria: dict[str, str],
    gate_audit: list[GateAudit],
    criterion_id: str,
) -> None:
    if value > rule.value:
        failures.append(failure_id)
        reasons.append(reason)
        criteria[criterion_id] = "block"
        status = "block"
        effect = "hard_block"
        message = reason
    else:
        criteria[criterion_id] = "pass"
        status = "pass"
        effect = "go_support"
        message = f"{rule.label} passed ({value:.3g} <= {rule.value:.3g} {rule.units})."
    _append_threshold_gate(gate_audit, criterion_id, criterion_id, rule.label, value, rule, status, effect, message)


def _check_lower(
    value: float,
    rule: ThresholdRule,
    failure_id: str,
    reason: str,
    failures: list[str],
    reasons: list[str],
    criteria: dict[str, str],
    gate_audit: list[GateAudit],
    criterion_id: str,
) -> None:
    if value < rule.value:
        failures.append(failure_id)
        reasons.append(reason)
        criteria[criterion_id] = "block"
        status = "block"
        effect = "hard_block"
        message = reason
    else:
        criteria[criterion_id] = "pass"
        status = "pass"
        effect = "go_support"
        message = f"{rule.label} passed ({value:.3g} >= {rule.value:.3g} {rule.units})."
    _append_threshold_gate(gate_audit, criterion_id, criterion_id, rule.label, value, rule, status, effect, message)


def _append_threshold_gate(
    gate_audit: list[GateAudit],
    gate_id: str,
    criterion_id: str,
    label: str,
    observed_value: Any,
    rule: ThresholdRule,
    status: str,
    decision_effect: str,
    message: str,
) -> None:
    gate_audit.append(
        GateAudit(
            gate_id=gate_id,
            criterion_id=criterion_id,
            label=label,
            observed_value=round(observed_value, 4) if isinstance(observed_value, float) else observed_value,
            threshold_id=rule.id,
            threshold_value=rule.value,
            threshold_units=rule.units,
            direction=rule.direction,
            status=status,
            decision_effect=decision_effect,
            message=message,
            source=rule.source,
            rationale=rule.rationale,
        )
    )


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
