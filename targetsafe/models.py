from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AgentEvent:
    step: int
    phase: str
    agent: str
    action: str
    status: str
    candidate_id: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolCallLog:
    source: str
    query: str
    status: str
    cached: bool = False
    item_count: int = 0
    message: str = ""
    error_category: str = ""
    duration_ms: float | None = None
    attempt: int = 1
    provider: str = ""
    endpoint: str = ""
    error_code: str = ""
    severity: str = "info"
    fallback_used: bool = False
    debug_ref: str = ""

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
class GateAudit:
    gate_id: str
    criterion_id: str
    label: str
    observed_value: Any
    threshold_id: str = ""
    threshold_value: Any = None
    threshold_units: str = ""
    direction: str = ""
    status: str = "review"
    decision_effect: str = "review_required"
    message: str = ""
    source: str = ""
    rationale: str = ""

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
    threshold_ids: list[str] = field(default_factory=list)
    evidence_node_ids: list[str] = field(default_factory=list)
    criteria: dict[str, str] = field(default_factory=dict)
    gate_audit: list[GateAudit] = field(default_factory=list)
    decision_policy_version: str = "targetsafe.decision_policy.v2"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateRecord:
    candidate_id: str
    smiles: str
    source: str
    library_source: str = ""
    source_compound_id: str = ""
    source_name: str = ""
    diversity_cluster: str = ""
    screening_stage: str = "proposed"
    prefilter_reason: str = ""
    parent_candidate_id: str | None = None
    generation: int = 0
    redesign_reason: str = ""
    redesign_action: str = ""
    descriptors: DescriptorResult | None = None
    predicted_activity: float | None = None
    evidence_confidence: float = 0.0
    applicability_score: float = 0.0
    in_applicability_domain: bool = False
    decision: DecisionResult | None = None
    structure_svg: str | None = None
    conformer: dict[str, Any] | None = None
    prediction_interval: dict[str, float] | None = None
    nearest_analogs: list[dict[str, Any]] = field(default_factory=list)
    molecular_twin: dict[str, Any] = field(default_factory=dict)
    evidence_node_ids: list[str] = field(default_factory=list)
    activity_cliff_flags: list[dict[str, Any]] = field(default_factory=list)
    assay_recommendations: list[dict[str, Any]] = field(default_factory=list)
    target_specific_interpretation: str = ""
    candidate_errors: list[dict[str, Any]] = field(default_factory=list)
    candidate_decision_flow: list[dict[str, Any]] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "smiles": self.smiles,
            "source": self.source,
            "library_source": self.library_source or self.source,
            "source_compound_id": self.source_compound_id,
            "source_name": self.source_name,
            "diversity_cluster": self.diversity_cluster,
            "screening_stage": self.screening_stage,
            "prefilter_reason": self.prefilter_reason,
            "parent_candidate_id": self.parent_candidate_id,
            "generation": self.generation,
            "redesign_reason": self.redesign_reason,
            "redesign_action": self.redesign_action,
            "descriptors": self.descriptors.to_dict() if self.descriptors else None,
            "predicted_activity": self.predicted_activity,
            "evidence_confidence": self.evidence_confidence,
            "applicability_score": self.applicability_score,
            "in_applicability_domain": self.in_applicability_domain,
            "decision": self.decision.to_dict() if self.decision else None,
            "structure_svg": self.structure_svg,
            "conformer": self.conformer,
            "prediction_interval": self.prediction_interval,
            "nearest_analogs": self.nearest_analogs,
            "molecular_twin": self.molecular_twin,
            "evidence_node_ids": self.evidence_node_ids,
            "activity_cliff_flags": self.activity_cliff_flags,
            "assay_recommendations": self.assay_recommendations,
            "target_specific_interpretation": self.target_specific_interpretation,
            "candidate_errors": self.candidate_errors,
            "candidate_decision_flow": self.candidate_decision_flow,
        }


@dataclass
class PipelineResult:
    run_id: str
    plan: list[str]
    evidence: EvidenceBundle
    candidates: list[CandidateRecord]
    tool_logs: list[ToolCallLog]
    agent_events: list[AgentEvent] = field(default_factory=list)
    report_path: str | None = None
    evaluation_report: dict[str, Any] = field(default_factory=dict)
    compute_profile: dict[str, Any] = field(default_factory=dict)
    threshold_registry: dict[str, Any] = field(default_factory=dict)
    evidence_graph: dict[str, Any] = field(default_factory=dict)
    model_card: dict[str, Any] = field(default_factory=dict)
    ablation_report_path: str | None = None
    redesign_report: dict[str, Any] = field(default_factory=dict)
    validation_report: dict[str, Any] = field(default_factory=dict)
    evidence_mode: dict[str, Any] = field(default_factory=dict)
    runtime_status: dict[str, Any] = field(default_factory=dict)
    gpu_diagnostics: dict[str, Any] = field(default_factory=dict)
    tool_error_summary: dict[str, Any] = field(default_factory=dict)
    input_example_id: str = ""
    library_report: dict[str, Any] = field(default_factory=dict)
    screening_stages: list[dict[str, Any]] = field(default_factory=list)
    target_profile: dict[str, Any] = field(default_factory=dict)
    scoring_mode: str = "scored_pilot"
    assay_plan: dict[str, Any] = field(default_factory=dict)
    activity_cliff_report: dict[str, Any] = field(default_factory=dict)
    target_readiness: dict[str, Any] = field(default_factory=dict)
    scientific_extensions: dict[str, Any] = field(default_factory=dict)
    error_summary: dict[str, Any] = field(default_factory=dict)
    log_path: str = ""
    performance_summary: dict[str, Any] = field(default_factory=dict)
    cache_summary: dict[str, Any] = field(default_factory=dict)
    api_circuit_breaker_summary: dict[str, Any] = field(default_factory=dict)
    agent_trace_summary: dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "plan": self.plan,
            "evidence": self.evidence.to_dict(),
            "candidates": [c.to_public_dict() for c in self.candidates],
            "tool_logs": [log.to_dict() for log in self.tool_logs],
            "agent_events": [event.to_dict() for event in self.agent_events],
            "report_path": self.report_path,
            "evaluation_report": self.evaluation_report,
            "compute_profile": self.compute_profile,
            "threshold_registry": self.threshold_registry,
            "evidence_graph": self.evidence_graph,
            "model_card": self.model_card,
            "ablation_report_path": self.ablation_report_path,
            "redesign_report": self.redesign_report,
            "validation_report": self.validation_report,
            "evidence_mode": self.evidence_mode,
            "runtime_status": self.runtime_status,
            "gpu_diagnostics": self.gpu_diagnostics,
            "tool_error_summary": self.tool_error_summary,
            "input_example_id": self.input_example_id,
            "library_report": self.library_report,
            "screening_stages": self.screening_stages,
            "target_profile": self.target_profile,
            "scoring_mode": self.scoring_mode,
            "assay_plan": self.assay_plan,
            "activity_cliff_report": self.activity_cliff_report,
            "target_readiness": self.target_readiness,
            "scientific_extensions": self.scientific_extensions,
            "error_summary": self.error_summary,
            "log_path": self.log_path,
            "performance_summary": self.performance_summary,
            "cache_summary": self.cache_summary,
            "api_circuit_breaker_summary": self.api_circuit_breaker_summary,
            "agent_trace_summary": self.agent_trace_summary,
        }
