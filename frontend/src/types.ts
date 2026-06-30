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
  report_path: string | null;
  evaluation_report: {
    status_counts?: Record<Status, number>;
    acceptance_checks?: Record<string, boolean>;
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
