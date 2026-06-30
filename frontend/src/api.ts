import type {
  AgentEvent,
  CandidatePage,
  ConformerPayload,
  KnownContext,
  LlmProvider,
  LlmTestResult,
  LibraryImportResult,
  PipelineResult,
  RedesignReport,
  ReferenceDrug,
  RunExample,
  RunRequest,
  RuntimeStatus,
  StructureDepiction,
  ValidationReport
} from "./types";

const API_BASE = import.meta.env.VITE_TARGETSAFE_API ?? "";

export async function createRun(request: RunRequest): Promise<PipelineResult> {
  const response = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Run failed with ${response.status}`);
  }
  return response.json();
}

export async function fetchProfiles(): Promise<Array<Record<string, unknown>>> {
  const response = await fetch(`${API_BASE}/api/compute-profiles`);
  if (!response.ok) {
    throw new Error("Unable to load compute profiles.");
  }
  return response.json();
}

export async function fetchRuntimeStatus(): Promise<RuntimeStatus> {
  const response = await fetch(`${API_BASE}/api/runtime-status`);
  if (!response.ok) {
    throw new Error("Unable to load runtime status.");
  }
  return response.json();
}

export async function fetchGpuDiagnostics(): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}/api/gpu-diagnostics`);
  if (!response.ok) {
    throw new Error("Unable to load GPU diagnostics.");
  }
  return response.json();
}

export async function fetchLlmProviders(): Promise<LlmProvider[]> {
  const response = await fetch(`${API_BASE}/api/llm/providers`);
  if (!response.ok) {
    throw new Error("Unable to load LLM providers.");
  }
  return response.json();
}

export async function testLlmConnection(request: RunRequest): Promise<LlmTestResult> {
  const response = await fetch(`${API_BASE}/api/llm/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      llm_provider: request.llm_provider,
      llm_api_key: request.llm_api_key,
      llm_base_url: request.llm_base_url,
      llm_model: request.llm_model,
      llm_custom_model: request.llm_custom_model
    })
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unable to test LLM connection.");
  }
  return response.json();
}

export async function fetchRunExamples(): Promise<RunExample[]> {
  const response = await fetch(`${API_BASE}/api/run-examples`);
  if (!response.ok) {
    throw new Error("Unable to load run examples.");
  }
  return response.json();
}

export async function fetchDecisionRules(): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}/api/decision-rules`);
  if (!response.ok) {
    throw new Error("Unable to load decision rules.");
  }
  return response.json();
}

export async function fetchReferenceDrugs(): Promise<ReferenceDrug[]> {
  const response = await fetch(`${API_BASE}/api/reference-drugs`);
  if (!response.ok) {
    throw new Error("Unable to load reference drugs.");
  }
  return response.json();
}

export async function fetchKnownContext(runId: string, candidateId: string): Promise<KnownContext> {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/candidates/${candidateId}/known-context`);
  if (!response.ok) {
    throw new Error("Unable to load candidate known-drug context.");
  }
  return response.json();
}

export async function fetchCandidates(
  runId: string,
  options: { limit: number; offset: number; status?: string; source?: string; sort?: string }
): Promise<CandidatePage> {
  const params = new URLSearchParams({
    limit: String(options.limit),
    offset: String(options.offset),
    status: options.status ?? "all",
    source: options.source ?? "all",
    sort: options.sort ?? "rank"
  });
  const response = await fetch(`${API_BASE}/api/runs/${runId}/candidates?${params.toString()}`);
  if (!response.ok) {
    throw new Error("Unable to load candidate page.");
  }
  return response.json();
}

export async function fetchConformer(runId: string, candidateId: string): Promise<ConformerPayload> {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/candidates/${candidateId}/conformer`);
  if (!response.ok) {
    throw new Error("Unable to load conformer.");
  }
  return response.json();
}

export async function importLibrary(name: string, text: string): Promise<LibraryImportResult> {
  const response = await fetch(`${API_BASE}/api/library/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, text })
  });
  if (!response.ok) {
    throw new Error("Unable to import library.");
  }
  return response.json();
}

export async function fetchDepiction(smiles: string): Promise<StructureDepiction> {
  const response = await fetch(`${API_BASE}/api/depict?smiles=${encodeURIComponent(smiles)}`);
  if (!response.ok) {
    throw new Error("Unable to depict molecule.");
  }
  return response.json();
}

export async function fetchAgentTrace(runId: string): Promise<AgentEvent[]> {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/agent-trace`);
  if (!response.ok) {
    throw new Error("Unable to load agent trace.");
  }
  return response.json();
}

export async function fetchValidation(runId: string): Promise<ValidationReport> {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/validation`);
  if (!response.ok) {
    throw new Error("Unable to load validation report.");
  }
  return response.json();
}

export async function fetchRedesignReport(runId: string): Promise<RedesignReport> {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/redesign-report`);
  if (!response.ok) {
    throw new Error("Unable to load redesign report.");
  }
  return response.json();
}
