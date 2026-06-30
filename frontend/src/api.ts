import type { PipelineResult, RunRequest } from "./types";

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
