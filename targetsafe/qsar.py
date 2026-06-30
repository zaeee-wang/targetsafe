from __future__ import annotations

import math

from targetsafe.chem import tanimoto_like_similarity
from targetsafe.models import CandidateRecord, EvidenceBundle


class EvidenceWeightedQSAR:
    """Deterministic QSAR-like scorer for MVP triage.

    This is intentionally conservative: it returns a ranking aid, not a claim of
    true potency. If scikit-learn/RDKit models are added later, this class can be
    replaced behind the same interface.
    """

    def __init__(self, evidence: EvidenceBundle) -> None:
        self.evidence = evidence
        self.references = [item["smiles"] for item in evidence.known_inhibitors if item.get("smiles")]

    def score(self, candidate: CandidateRecord) -> CandidateRecord:
        desc = candidate.descriptors
        if not desc or not desc.valid:
            candidate.predicted_activity = 0.0
            candidate.applicability_score = 0.0
            candidate.evidence_confidence = 0.0
            candidate.in_applicability_domain = False
            return candidate

        similarity = max((tanimoto_like_similarity(candidate.smiles, ref) for ref in self.references), default=0.0)
        activity = 6.2
        activity += 1.1 * similarity
        activity += 0.6 * desc.qed
        activity += 0.25 * _window_score(desc.logp, 1.2, 4.2)
        activity += 0.25 * _window_score(desc.tpsa, 45, 115)
        activity -= 0.35 * len(desc.alerts)
        activity -= 0.18 * desc.lipinski_violations
        activity -= 0.12 * max(0.0, desc.sa_score - 5.0)

        data_support = min(1.0, len(self.evidence.chembl_activities) / 50.0)
        confidence = 0.25 + 0.45 * similarity + 0.20 * data_support + 0.10 * desc.qed
        if len(desc.alerts):
            confidence -= 0.08
        if similarity < 0.18:
            confidence -= 0.12

        candidate.predicted_activity = max(0.0, min(10.0, activity))
        candidate.applicability_score = similarity
        candidate.evidence_confidence = max(0.0, min(1.0, confidence))
        candidate.in_applicability_domain = similarity >= 0.18
        return candidate


def _window_score(value: float, low: float, high: float) -> float:
    if low <= value <= high:
        return 1.0
    distance = low - value if value < low else value - high
    return math.exp(-(distance / max(high - low, 1.0)) ** 2)

