from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class ThresholdRule:
    id: str
    label: str
    value: float
    units: str
    direction: str
    source: str
    rationale: str
    computed_from: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ThresholdRegistry:
    def __init__(self, rules: list[ThresholdRule] | None = None) -> None:
        self._rules = {rule.id: rule for rule in (rules or default_threshold_rules())}

    def get(self, rule_id: str) -> ThresholdRule:
        return self._rules[rule_id]

    def ids(self) -> list[str]:
        return sorted(self._rules)

    def to_dict(self) -> dict[str, Any]:
        return {
            "registry_version": "2026-06-30",
            "policy": (
                "Thresholds are decision-support gates, not universal medicinal chemistry laws. "
                "Each value carries provenance so it can be replaced by target-specific calibration."
            ),
            "rules": {rule_id: rule.to_dict() for rule_id, rule in sorted(self._rules.items())},
        }

    def write_json(self, output_dir: str | Path) -> str:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        path = output / "threshold_registry.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return str(path)


def default_threshold_rules() -> list[ThresholdRule]:
    today = date.today().isoformat()
    return [
        ThresholdRule(
            id="activity_pchembl_lower_bound_min",
            label="Conservative EGFR activity floor",
            value=7.0,
            units="pChEMBL",
            direction="greater_or_equal",
            source="ChEMBL pChEMBL convention; operational early-lead triage policy",
            rationale=(
                "pChEMBL 7 corresponds to 100 nM when derived from IC50/Ki/Kd in molar units. "
                "Target-SAFE uses the lower prediction bound, not the mean, to avoid overclaiming."
            ),
            computed_from="-log10(activity_M); 100 nM = 1e-7 M",
            created_at=today,
        ),
        ThresholdRule(
            id="applicability_similarity_min",
            label="Minimum nearest-analog similarity",
            value=0.18,
            units="Tanimoto-like similarity",
            direction="greater_or_equal",
            source="Target-SAFE applicability-domain calibration on the EGFR reference set",
            rationale=(
                "Below this level, the candidate is treated as outside the analog evidence domain. "
                "Live ChEMBL training can replace this static floor with a scaffold-split calibration."
            ),
            computed_from="nearest reference analog similarity",
            created_at=today,
        ),
        ThresholdRule(
            id="evidence_confidence_min_for_go",
            label="Minimum graph evidence support for Go",
            value=0.45,
            units="0-1 support ratio",
            direction="greater_or_equal",
            source="Target-SAFE graph completeness policy",
            rationale=(
                "Go requires at least moderate tool-grounded support. Lower values keep the candidate "
                "in Hold until assay, analog, or external evidence is added."
            ),
            computed_from="analog support + data availability + descriptor reliability + alert penalties",
            created_at=today,
        ),
        ThresholdRule(
            id="prediction_interval_width_max",
            label="Maximum acceptable activity uncertainty",
            value=1.4,
            units="pChEMBL interval width",
            direction="less_or_equal",
            source="Target-SAFE uncertainty policy",
            rationale=(
                "A broad interval means the model is not precise enough for Go. The candidate can still "
                "remain Hold when the mean looks promising."
            ),
            computed_from="upper prediction bound - lower prediction bound",
            created_at=today,
        ),
        ThresholdRule(
            id="qed_min_floor",
            label="Very low QED floor",
            value=0.20,
            units="QED",
            direction="greater_or_equal",
            source="RDKit QED implementation of Bickerton et al. Quantifying the chemical beauty of drugs",
            rationale="A very low QED is treated as a hard early-triage warning rather than a potency claim.",
            computed_from="RDKit QED or deterministic fallback descriptor model",
            created_at=today,
        ),
        ThresholdRule(
            id="molecular_weight_extreme_max",
            label="Extreme molecular weight cap",
            value=650.0,
            units="Da",
            direction="less_or_equal",
            source="Lipinski rule-of-five context with a relaxed kinase-inhibitor triage margin",
            rationale="Used only as an extreme hard gate; softer MW concerns remain in Hold uncertainty.",
            computed_from="RDKit MolWt or deterministic fallback descriptor model",
            created_at=today,
        ),
        ThresholdRule(
            id="logp_extreme_max",
            label="Extreme logP cap",
            value=6.0,
            units="Crippen MolLogP",
            direction="less_or_equal",
            source="Lipinski rule-of-five context with a relaxed early-lead triage margin",
            rationale="High lipophilicity can drive ADMET risk; this cap prevents confident Go calls.",
            computed_from="RDKit Crippen MolLogP or deterministic fallback descriptor model",
            created_at=today,
        ),
        ThresholdRule(
            id="tpsa_extreme_max",
            label="Extreme TPSA cap",
            value=170.0,
            units="Angstrom^2",
            direction="less_or_equal",
            source="Veber oral bioavailability context with relaxed early-lead triage margin",
            rationale="Used as a conservative hard gate for very polar candidates in this oral TKI pilot.",
            computed_from="RDKit TPSA or deterministic fallback descriptor model",
            created_at=today,
        ),
        ThresholdRule(
            id="sa_score_max",
            label="Synthetic accessibility risk cap",
            value=8.0,
            units="SA score",
            direction="less_or_equal",
            source="Ertl-Schuffenhauer synthetic accessibility score interpretation; Target-SAFE fallback policy",
            rationale="High SA candidates should not be advanced without synthetic route review.",
            computed_from="RDKit-backed or deterministic fallback SA approximation",
            created_at=today,
        ),
    ]
