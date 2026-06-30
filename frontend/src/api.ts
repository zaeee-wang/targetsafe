import type { AgentEvent, KnownContext, PipelineResult, RedesignReport, ReferenceDrug, RunRequest, StructureDepiction, ValidationReport } from "./types";

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
