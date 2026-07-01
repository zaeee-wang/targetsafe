export type Status = "Go" | "Hold" | "No-Go" | "Unscored";

export interface DescriptorResult {
  valid: boolean;
  canonical_smiles: string;
  molecular_weight: number;
  logp: number;
  tpsa: number;
  hbd: number;
  hba: number;
  rotatable_bonds: number;
  qed: number;
  lipinski_violations: number;
  alerts: string[];
  severe_alerts: string[];
  sa_score: number;
  method: string;
}

export interface DecisionResult {
  final_status: Status;
  total_score: number;
  hard_gate_failures: string[];
  reasons: string[];
  uncertainty: string[];
  follow_up: string[];
  critic_findings: string[];
  threshold_ids: string[];
  evidence_node_ids: string[];
  criteria: Record<string, string>;
  gate_audit: GateAudit[];
  decision_policy_version: string;
}

export interface GateAudit {
  gate_id: string;
  criterion_id: string;
  label: string;
  observed_value: unknown;
  threshold_id: string;
  threshold_value: unknown;
  threshold_units: string;
  direction: string;
  status: string;
  decision_effect: string;
  message: string;
  source: string;
  rationale: string;
}

export interface Analog {
  name: string;
  smiles: string;
  similarity: number;
  pchembl?: number;
  activity_nM?: number;
  source?: string;
  method?: string;
}

export interface PredictionInterval {
  lower: number;
  mean: number;
  upper: number;
  width: number;
}

export interface ConformerAtom {
  index: number;
  element: string;
  x: number;
  y: number;
  z: number;
}

export interface ConformerBond {
  begin: number;
  end: number;
  order: number;
}

export interface ConformerPayload {
  available: boolean;
  label: string;
  message: string;
  atoms: ConformerAtom[];
  bonds: ConformerBond[];
}

export interface Candidate {
  candidate_id: string;
  smiles: string;
  source: string;
  library_source: string;
  source_compound_id: string;
  source_name: string;
  diversity_cluster: string;
  screening_stage: string;
  prefilter_reason: string;
  parent_candidate_id: string | null;
  generation: number;
  redesign_reason: string;
  redesign_action: string;
  descriptors: DescriptorResult | null;
  predicted_activity: number | null;
  evidence_confidence: number;
  applicability_score: number;
  in_applicability_domain: boolean;
  decision: DecisionResult | null;
  structure_svg: string | null;
  conformer: ConformerPayload | null;
  prediction_interval: PredictionInterval | null;
  nearest_analogs: Analog[];
  molecular_twin: {
    title?: string;
    definition?: string;
    evidence_completeness?: number;
    sections?: Record<string, unknown>;
  };
  evidence_node_ids: string[];
  activity_cliff_flags: Array<Record<string, unknown>>;
  assay_recommendations: Array<Record<string, unknown>>;
  target_specific_interpretation: string;
  candidate_errors: Array<Record<string, unknown>>;
  candidate_decision_flow: CandidateDecisionFlowNode[];
}

export interface CandidateDecisionFlowNode {
  id: string;
  label: string;
  status: "done" | "review" | "fallback" | "blocked" | string;
  summary: string;
}

export interface EvidenceGraph {
  run_id: string;
  schema: string;
  summary: {
    node_count: number;
    edge_count: number;
    edge_counts: Record<string, number>;
  };
  nodes: Array<Record<string, unknown> & { id: string; type: string; label?: string }>;
  edges: Array<{ source: string; target: string; type: string; weight?: number }>;
}

export interface AgentEvent {
  step: number;
  phase: string;
  agent: string;
  action: string;
  status: string;
  candidate_id?: string | null;
  detail: Record<string, unknown>;
}

export interface AgentFlowNode {
  id: string;
  label: string;
  agent?: string;
  status: "done" | "review" | "fallback" | "blocked" | string;
  event_count?: number;
  summary?: string;
  event_steps?: number[];
}

export interface AgentFlowEdge {
  source: string;
  target: string;
  type?: string;
}

export interface AgentTraceSummary {
  schema?: string;
  plain_summary: string[];
  flow_nodes: AgentFlowNode[];
  flow_edges: AgentFlowEdge[];
  phase_summaries: Record<string, { label?: string; status?: string; summary?: string; event_count?: number }>;
  fallback_events_count: number;
  critic_findings_count: number;
  decision_impact: string;
}

export interface EvidenceMode {
  mode: string;
  label: string;
  counts?: Record<string, number>;
  cached_calls?: number;
  live_calls?: number;
  interpretation?: string;
}

export interface ValidationReport {
  status?: string;
  dataset_size?: number;
  minimum_required_rows?: number;
  model_type?: string;
  interpretation?: string;
  metrics?: Record<string, unknown>;
  split_summary?: Record<string, unknown>;
  applicability_domain_performance?: Record<string, unknown>;
  outputs?: Record<string, string>;
}

export interface RedesignReport {
  schema?: string;
  iteration_limit?: number;
  definition?: string;
  created_children?: number;
  comparisons?: Array<Record<string, unknown>>;
  skipped?: Array<Record<string, unknown>>;
}

export interface PipelineResult {
  run_id: string;
  plan: string[];
  evidence: {
    target: string;
    disease: string;
    chembl_activities: Array<Record<string, unknown>>;
    pubchem_records: Array<Record<string, unknown>>;
    clinical_trials: Array<Record<string, unknown>>;
    regulatory_risks: Array<Record<string, unknown>>;
    known_inhibitors: ReferenceDrug[];
    evidence_notes: string[];
  };
  candidates: Candidate[];
  tool_logs: Array<Record<string, unknown>>;
  agent_events: AgentEvent[];
  report_path: string | null;
  evaluation_report: {
    status_counts?: Record<Status, number>;
    acceptance_checks?: Record<string, boolean>;
    redesign_child_count?: number;
  };
  compute_profile: Record<string, unknown>;
  threshold_registry: {
    registry_version: string;
    policy: string;
    rules: Record<string, Record<string, unknown>>;
  };
  evidence_graph: EvidenceGraph;
  model_card: Record<string, unknown>;
  ablation_report_path: string | null;
  redesign_report: RedesignReport;
  validation_report: ValidationReport;
  evidence_mode: EvidenceMode;
  runtime_status: RuntimeStatus;
  gpu_diagnostics: Record<string, unknown>;
  tool_error_summary: ToolErrorSummary;
  input_example_id: string;
  library_report: LibraryReport;
  screening_stages: ScreeningStage[];
  target_profile: Record<string, unknown>;
  scoring_mode: string;
  assay_plan: Record<string, unknown>;
  activity_cliff_report: Record<string, unknown>;
  target_readiness: Record<string, unknown>;
  scientific_extensions: Record<string, unknown>;
  error_summary: ErrorSummary;
  log_path: string;
  performance_summary: Record<string, unknown>;
  cache_summary: Record<string, unknown>;
  api_circuit_breaker_summary: Record<string, unknown>;
  agent_trace_summary: AgentTraceSummary;
}

export interface RunRequest {
  disease: string;
  target: string;
  seed_smiles: string;
  optimization_goal: string;
  candidate_count: number;
  compute_profile: string;
  allow_network: boolean;
  use_llm: boolean;
  use_gpu: boolean;
  enable_conformers: boolean;
  library_sources: string[];
  library_limit: number;
  detailed_eval_limit: number;
  display_limit: number;
  conformer_limit: number;
  uploaded_smiles: string[];
  uploaded_library_id?: string | null;
  llm_api_key: string;
  llm_provider: string;
  llm_base_url: string;
  llm_model: string;
  llm_custom_model: string;
  input_example_id: string;
}

export interface ReferenceDrug {
  drug_id: string;
  name: string;
  smiles: string;
  pubchem_cid: string;
  chembl_id: string;
  context: string;
  activity_evidence: string;
  label_risk_context: string[];
  evidence_source: string;
  source_status: string;
  structure_svg?: string | null;
  structure_image_url?: string | null;
  category?: string;
  pchembl?: number;
  activity_nM?: number;
}

export interface KnownContextDrug {
  drug_id: string;
  name: string;
  smiles: string;
  pubchem_cid: string;
  chembl_id: string;
  similarity: number;
  label_risk_context: string[];
  evidence_source: string;
  source_status: string;
}

export interface KnownContext {
  schema: string;
  interpretation: string;
  nearest_known_drugs: KnownContextDrug[];
}

export interface StructureDepiction {
  valid: boolean;
  canonical_smiles: string;
  structure_svg: string | null;
  method: string;
  molecular_weight: number;
  qed: number;
  sa_score: number;
  alerts: string[];
}

export interface MoleculeCheckResult {
  schema: string;
  name: string;
  target: string;
  input_smiles: string;
  canonical_smiles: string;
  valid: boolean;
  viability: "invalid" | "blocked" | "review" | "plausible_seed" | string;
  can_use_as_seed: boolean;
  structure_svg: string | null;
  descriptors: DescriptorResult;
  reasons: string[];
  suggestions: string[];
  interpretation: string;
}

export interface SavedMolecule {
  id: string;
  name: string;
  smiles: string;
  target: string;
  viability: string;
  saved_at: string;
  structure_svg?: string | null;
}

export interface RuntimeStatus {
  schema?: string;
  gpu?: Record<string, unknown>;
  gpu_diagnostics?: Record<string, unknown>;
  llm?: Record<string, unknown>;
  public_evidence_apis?: Record<string, unknown>;
}

export interface LlmProvider {
  id: string;
  label: string;
  requires_key: boolean;
  default_model: string;
  models: string[];
  base_url: string;
  description: string;
}

export interface LlmTestResult {
  ok: boolean;
  provider: string;
  used: boolean;
  model?: string;
  base_url_configured?: boolean;
  message: string;
}

export interface RunExample {
  id: string;
  label: string;
  description: string;
  expected_behavior: string;
  scoring_mode?: string;
  interpretation_limit?: string;
  default_library_sources?: string[];
  request: Partial<RunRequest>;
}

export interface ToolErrorSummary {
  schema?: string;
  total_calls?: number;
  categories?: Record<string, number>;
  by_source?: Record<string, unknown>;
  has_live_errors?: boolean;
  interpretation?: string;
}

export interface ErrorSummary {
  schema?: string;
  total_errors?: number;
  categories?: Record<string, number>;
  severities?: Record<string, number>;
  sources?: Record<string, number>;
  has_blocking_error?: boolean;
  interpretation?: string;
}

export interface LibraryReport {
  schema?: string;
  library_sources?: string[];
  source_input_counts?: Record<string, number>;
  raw_input_count?: number;
  valid_unique_count?: number;
  invalid_or_unparseable_count?: number;
  duplicate_count?: number;
  library_limit?: number;
  detailed_eval_limit?: number;
  detailed_evaluation_count?: number;
  prefilter_pass_not_detailed_count?: number;
  diversity_cluster_count?: number;
  final_candidate_count?: number;
  display_asset_count?: number;
  conformer_asset_count?: number;
  interpretation?: string;
}

export interface ScreeningStage {
  stage: string;
  count: number;
  description: string;
}

export interface CandidatePage {
  run_id: string;
  total: number;
  limit: number;
  offset: number;
  items: Candidate[];
}

export interface LibraryImportResult {
  library_id: string;
  name: string;
  compound_count: number;
  message: string;
}
