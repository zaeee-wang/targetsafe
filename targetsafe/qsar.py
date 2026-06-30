from __future__ import annotations

import math
from statistics import mean
from typing import Any

from targetsafe.chem import RDKIT_AVAILABLE, tanimoto_like_similarity
from targetsafe.models import CandidateRecord, EvidenceBundle
from targetsafe.thresholds import ThresholdRegistry


class EvidenceWeightedQSAR:
    """Evidence-backed EGFR activity estimator.

    The class keeps the old public interface (`score(candidate)`) but no longer
    uses an opaque weighted score. It returns an analog-supported activity
    estimate with an interval and an explicit applicability-domain signal. When
    live ChEMBL rows contain canonical SMILES and pChEMBL values, this object can
    be extended into a scaffold-split sklearn model behind the same interface.
    """

    def __init__(self, evidence: EvidenceBundle, thresholds: ThresholdRegistry | None = None) -> None:
        self.evidence = evidence
        self.thresholds = thresholds or ThresholdRegistry()
        self.training_rows = self._training_rows(evidence)
        self.model_card = self._build_model_card()

    def score(self, candidate: CandidateRecord) -> CandidateRecord:
        desc = candidate.descriptors
        if not desc or not desc.valid:
            candidate.predicted_activity = 0.0
            candidate.prediction_interval = {"lower": 0.0, "mean": 0.0, "upper": 0.0, "width": 0.0}
            candidate.applicability_score = 0.0
            candidate.evidence_confidence = 0.0
            candidate.in_applicability_domain = False
            candidate.nearest_analogs = []
            return candidate

        analogs = []
        for row in self.training_rows:
            similarity = tanimoto_like_similarity(candidate.smiles, row["smiles"])
            analogs.append({**row, "similarity": similarity})
        analogs = sorted(analogs, key=lambda item: item["similarity"], reverse=True)
        nearest = analogs[:5]
        best_similarity = nearest[0]["similarity"] if nearest else 0.0

        if nearest:
            weights = [max(item["similarity"], 0.01) ** 2 for item in nearest]
            weighted = sum(item["pchembl"] * weight for item, weight in zip(nearest, weights)) / sum(weights)
            spread = max(0.35, _weighted_deviation(nearest, weights, weighted))
        else:
            weighted = 0.0
            spread = 2.0

        alert_penalty = 0.15 * len(desc.alerts) + 0.45 * len(desc.severe_alerts)
        lipinski_penalty = 0.10 * desc.lipinski_violations
        activity_mean = max(0.0, min(10.0, weighted - alert_penalty - lipinski_penalty))
        interval_width = _interval_width(best_similarity, spread, len(self.training_rows), len(desc.alerts))
        lower = max(0.0, activity_mean - interval_width / 2.0)
        upper = min(10.0, activity_mean + interval_width / 2.0)

        ad_threshold = self.thresholds.get("applicability_similarity_min").value
        candidate.predicted_activity = activity_mean
        candidate.prediction_interval = {
            "lower": round(lower, 3),
            "mean": round(activity_mean, 3),
            "upper": round(upper, 3),
            "width": round(upper - lower, 3),
        }
        candidate.applicability_score = best_similarity
        candidate.in_applicability_domain = best_similarity >= ad_threshold
        candidate.nearest_analogs = [
            {
                "name": item["name"],
                "smiles": item["smiles"],
                "similarity": round(item["similarity"], 3),
                "pchembl": item["pchembl"],
                "activity_nM": item.get("activity_nM"),
                "source": item["source"],
            }
            for item in nearest[:3]
        ]
        candidate.evidence_confidence = self._confidence(candidate, len(self.training_rows), best_similarity)
        return candidate

    def _confidence(self, candidate: CandidateRecord, training_size: int, similarity: float) -> float:
        desc = candidate.descriptors
        if not desc or not desc.valid:
            return 0.0
        data_support = min(1.0, training_size / 25.0)
        descriptor_support = 1.0 if desc.method == "rdkit" else 0.55
        alert_penalty = min(0.45, 0.10 * len(desc.alerts) + 0.20 * len(desc.severe_alerts))
        confidence = (similarity + data_support + descriptor_support) / 3.0 - alert_penalty
        return round(max(0.0, min(1.0, confidence)), 3)

    def _training_rows(self, evidence: EvidenceBundle) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in evidence.known_inhibitors:
            smiles = item.get("smiles")
            pchembl = item.get("pchembl")
            if smiles and pchembl is not None:
                rows.append(
                    {
                        "name": item.get("name", "EGFR reference"),
                        "smiles": str(smiles),
                        "pchembl": float(pchembl),
                        "activity_nM": item.get("activity_nM"),
                        "source": item.get("activity_source") or item.get("evidence") or "known EGFR inhibitor",
                    }
                )
        for item in evidence.chembl_activities:
            smiles = item.get("canonical_smiles") or (item.get("molecule_structures") or {}).get("canonical_smiles")
            pchembl = item.get("pchembl_value")
            if smiles and pchembl is not None:
                try:
                    rows.append(
                        {
                            "name": item.get("molecule_chembl_id", "ChEMBL EGFR activity"),
                            "smiles": str(smiles),
                            "pchembl": float(pchembl),
                            "activity_nM": item.get("standard_value"),
                            "source": "ChEMBL activity pchembl_value",
                        }
                    )
                except (TypeError, ValueError):
                    continue
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            key = row["smiles"]
            if key in seen:
                continue
            seen.add(key)
            unique.append(row)
        return unique

    def _build_model_card(self) -> dict[str, Any]:
        values = [row["pchembl"] for row in self.training_rows]
        return {
            "model_id": "egfr_analog_evidence_qsar_v1",
            "target": self.evidence.target,
            "disease_context": self.evidence.disease,
            "model_type": "analog-supported QSAR fallback; scaffold-split sklearn model hook ready",
            "rdkit_available": RDKIT_AVAILABLE,
            "training_size": len(self.training_rows),
            "activity_label": "pChEMBL when available; fallback pChEMBL is computed from listed nM reference controls",
            "activity_range": {
                "min": round(min(values), 3) if values else None,
                "mean": round(mean(values), 3) if values else None,
                "max": round(max(values), 3) if values else None,
            },
            "applicability_domain": {
                "method": "nearest reference analog similarity",
                "threshold_id": "applicability_similarity_min",
                "threshold_value": self.thresholds.get("applicability_similarity_min").value,
            },
            "prediction_interval": {
                "method": "nearest-neighbor activity spread widened for low similarity, sparse data, and alerts",
                "threshold_id": "prediction_interval_width_max",
            },
            "limitations": [
                "Offline fallback references are sufficient for demo triage, not for publication-grade potency modeling.",
                "Live ChEMBL mode should be used to replace the fallback set before scientific interpretation.",
                "Predictions are ranking aids and cannot establish efficacy or safety.",
            ],
        }


def _weighted_deviation(rows: list[dict[str, Any]], weights: list[float], center: float) -> float:
    if not rows:
        return 1.0
    variance = sum(weight * ((row["pchembl"] - center) ** 2) for row, weight in zip(rows, weights)) / sum(weights)
    return math.sqrt(max(variance, 0.0))


def _interval_width(best_similarity: float, spread: float, training_size: int, alert_count: int) -> float:
    if best_similarity >= 0.95:
        return max(0.45, min(1.05, 0.55 + 0.25 * spread + 0.15 * alert_count))
    sparse_penalty = max(0.0, 1.0 - min(training_size, 25) / 25.0)
    domain_penalty = max(0.0, 0.45 - best_similarity)
    width = 0.55 + spread + 0.85 * sparse_penalty + 1.4 * domain_penalty + 0.20 * alert_count
    return max(0.45, min(3.2, width))
