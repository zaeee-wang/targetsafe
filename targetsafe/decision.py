from __future__ import annotations

from targetsafe.models import CandidateRecord, DecisionResult


def decide_candidate(candidate: CandidateRecord) -> DecisionResult:
    desc = candidate.descriptors
    if not desc or not desc.valid:
        return DecisionResult(
            final_status="No-Go",
            total_score=0.0,
            hard_gate_failures=["invalid_smiles"],
            reasons=["SMILES failed structural validation."],
            follow_up=["Replace or regenerate the candidate before evaluation."],
        )

    failures: list[str] = []
    reasons: list[str] = []
    uncertainty: list[str] = []
    follow_up: list[str] = []

    if desc.severe_alerts:
        failures.append("severe_structural_alert")
        reasons.append(f"Severe alert(s): {', '.join(desc.severe_alerts[:3])}")
    if desc.molecular_weight > 650:
        failures.append("molecular_weight_extreme")
        reasons.append(f"Molecular weight is high ({desc.molecular_weight:.1f}).")
    if desc.logp > 6.0:
        failures.append("logp_extreme")
        reasons.append(f"LogP is high ({desc.logp:.2f}).")
    if desc.tpsa > 170:
        failures.append("tpsa_extreme")
        reasons.append(f"TPSA is high ({desc.tpsa:.1f}).")
    if desc.qed < 0.20:
        failures.append("qed_low")
        reasons.append(f"QED is low ({desc.qed:.2f}).")
    if desc.sa_score > 8.0:
        failures.append("synthetic_accessibility_low")
        reasons.append(f"SA score is high ({desc.sa_score:.2f}).")

    activity_component = (candidate.predicted_activity or 0.0) / 10.0
    drug_likeness = desc.qed
    toxicity_safety = max(0.0, 1.0 - 0.18 * len(desc.alerts) - 0.35 * len(desc.severe_alerts))
    synthetic = max(0.0, min(1.0, 1.0 - (desc.sa_score - 1.0) / 9.0))
    evidence = candidate.evidence_confidence
    score = (
        0.30 * activity_component
        + 0.25 * drug_likeness
        + 0.20 * toxicity_safety
        + 0.15 * synthetic
        + 0.10 * evidence
    )

    if not candidate.in_applicability_domain:
        uncertainty.append("QSAR applicability domain is weak; do not over-interpret activity.")
        follow_up.append("Review nearest ChEMBL analogs or collect target-specific assay evidence.")
    if candidate.evidence_confidence < 0.35:
        uncertainty.append("Evidence confidence is low.")
        follow_up.append("Require additional public or internal assay evidence before prioritization.")
    if desc.alerts and not desc.severe_alerts:
        uncertainty.append(f"Structural alert(s) require review: {', '.join(desc.alerts[:3])}.")
        follow_up.append("Run focused toxicity and medicinal chemistry review.")
    if desc.lipinski_violations:
        uncertainty.append(f"Lipinski violations: {desc.lipinski_violations}.")

    if failures:
        status = "No-Go"
    elif score >= 0.68 and candidate.in_applicability_domain and candidate.evidence_confidence >= 0.45 and not desc.alerts:
        status = "Go"
        reasons.append("Passed hard gates with acceptable activity, drug-likeness, and evidence confidence.")
    else:
        status = "Hold"
        reasons.append("Candidate remains plausible but needs additional evidence or risk reduction.")

    if not follow_up:
        follow_up.append("Confirm with orthogonal assay, ADMET panel, and expert medicinal chemistry review.")

    return DecisionResult(
        final_status=status,
        total_score=max(0.0, min(1.0, score)),
        hard_gate_failures=failures,
        reasons=reasons,
        uncertainty=uncertainty,
        follow_up=follow_up,
    )


def rank_candidates(candidates: list[CandidateRecord]) -> list[CandidateRecord]:
    order = {"Go": 0, "Hold": 1, "No-Go": 2}
    return sorted(
        candidates,
        key=lambda c: (
            order.get(c.decision.final_status if c.decision else "No-Go", 9),
            -(c.decision.total_score if c.decision else 0.0),
            c.candidate_id,
        ),
    )

