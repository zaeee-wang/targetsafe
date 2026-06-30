from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ToolCallLog:
    source: str
    query: str
    status: str
    cached: bool = False
    item_count: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceBundle:
    target: str
    disease: str
    chembl_activities: list[dict[str, Any]] = field(default_factory=list)
    pubchem_records: list[dict[str, Any]] = field(default_factory=list)
    clinical_trials: list[dict[str, Any]] = field(default_factory=list)
    regulatory_risks: list[dict[str, Any]] = field(default_factory=list)
    known_inhibitors: list[dict[str, Any]] = field(default_factory=list)
    evidence_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DescriptorResult:
    valid: bool
    canonical_smiles: str
    molecular_weight: float = 0.0
    logp: float = 0.0
    tpsa: float = 0.0
    hbd: int = 0
    hba: int = 0
    rotatable_bonds: int = 0
    qed: float = 0.0
    lipinski_violations: int = 0
    alerts: list[str] = field(default_factory=list)
    severe_alerts: list[str] = field(default_factory=list)
    sa_score: float = 5.0
    method: str = "heuristic"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionResult:
    final_status: str
    total_score: float
    hard_gate_failures: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    uncertainty: list[str] = field(default_factory=list)
    follow_up: list[str] = field(default_factory=list)
    critic_findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateRecord:
    candidate_id: str
    smiles: str
    source: str
    descriptors: DescriptorResult | None = None
    predicted_activity: float | None = None
    evidence_confidence: float = 0.0
    applicability_score: float = 0.0
    in_applicability_domain: bool = False
    decision: DecisionResult | None = None
    structure_svg: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "smiles": self.smiles,
            "source": self.source,
            "descriptors": self.descriptors.to_dict() if self.descriptors else None,
            "predicted_activity": self.predicted_activity,
            "evidence_confidence": self.evidence_confidence,
            "applicability_score": self.applicability_score,
            "in_applicability_domain": self.in_applicability_domain,
            "decision": self.decision.to_dict() if self.decision else None,
        }


@dataclass
class PipelineResult:
    run_id: str
    plan: list[str]
    evidence: EvidenceBundle
    candidates: list[CandidateRecord]
    tool_logs: list[ToolCallLog]
    report_path: str | None = None
    evaluation_report: dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "plan": self.plan,
            "evidence": self.evidence.to_dict(),
            "candidates": [c.to_public_dict() for c in self.candidates],
            "tool_logs": [log.to_dict() for log in self.tool_logs],
            "report_path": self.report_path,
            "evaluation_report": self.evaluation_report,
        }

