from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from targetsafe.compute_profiles import profile_options
from targetsafe.pipeline import PipelineConfig, run_pipeline
from targetsafe.reference_drugs import known_context_for_smiles, reference_drug, reference_drugs


DEFAULT_DISEASE = "EGFR mutation-positive NSCLC"
DEFAULT_TARGET = "EGFR"
DEFAULT_SEED = "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1"
DEFAULT_GOAL = "Maintain drug-likeness, reduce toxicity alerts, preserve EGFR evidence confidence"


class RunRequest(BaseModel):
    disease: str = Field(default=DEFAULT_DISEASE)
    target: str = Field(default=DEFAULT_TARGET)
    seed_smiles: str = Field(default=DEFAULT_SEED)
    optimization_goal: str = Field(default=DEFAULT_GOAL)
    candidate_count: int = Field(default=60, ge=20, le=120)
    compute_profile: str = Field(default="cpu-demo")
    allow_network: bool = False
    use_llm: bool = False
    use_gpu: bool = False
    enable_conformers: bool = True


app = FastAPI(
    title="Target-SAFE API",
    version="0.2.0",
    description="Evidence-gated molecular digital twin triage API for EGFR lead candidates.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_RUNS: dict[str, dict[str, Any]] = {}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/compute-profiles")
def compute_profiles() -> list[dict[str, Any]]:
    return profile_options()


@app.get("/api/reference-drugs")
def get_reference_drugs() -> list[dict[str, Any]]:
    return reference_drugs(include_structures=True)


@app.get("/api/reference-drugs/{drug_id}")
def get_reference_drug(drug_id: str) -> dict[str, Any]:
    drug = reference_drug(drug_id)
    if drug is None:
        raise HTTPException(status_code=404, detail="Reference drug not found.")
    return drug


@app.post("/api/runs")
def create_run(request: RunRequest) -> dict[str, Any]:
    result = run_pipeline(
        PipelineConfig(
            disease=request.disease,
            target=request.target,
            seed_smiles=request.seed_smiles,
            optimization_goal=request.optimization_goal,
            candidate_count=request.candidate_count,
            compute_profile=request.compute_profile,
            allow_network=request.allow_network,
            use_llm=request.use_llm,
            use_gpu=request.use_gpu,
            enable_conformers=request.enable_conformers,
            output_dir=Path("outputs"),
        )
    )
    payload = result.to_public_dict()
    _RUNS[result.run_id] = payload
    return payload


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    payload = _RUNS.get(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Run not found in current API process.")
    return payload


@app.get("/api/runs/{run_id}/evidence-graph")
def get_evidence_graph(run_id: str) -> dict[str, Any]:
    payload = get_run(run_id)
    return payload.get("evidence_graph", {})


@app.get("/api/runs/{run_id}/candidates/{candidate_id}/known-context")
def get_candidate_known_context(run_id: str, candidate_id: str) -> dict[str, Any]:
    payload = get_run(run_id)
    candidates = payload.get("candidates", [])
    for candidate in candidates:
        if candidate.get("candidate_id") == candidate_id:
            return known_context_for_smiles(str(candidate.get("smiles", "")))
    raise HTTPException(status_code=404, detail="Candidate not found in current API process.")


@app.get("/api/runs/{run_id}/report", response_class=HTMLResponse)
def get_report(run_id: str) -> str:
    payload = get_run(run_id)
    report_path = payload.get("report_path")
    if not report_path or not Path(report_path).exists():
        raise HTTPException(status_code=404, detail="Report file not found.")
    return Path(report_path).read_text(encoding="utf-8")


@app.get("/api/model-card/egfr")
def get_model_card() -> dict[str, Any]:
    path = Path("outputs/model_card_egfr.json")
    if path.exists():
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    result = run_pipeline(PipelineConfig(candidate_count=20, compute_profile="cpu-demo", output_dir=Path("outputs")))
    _RUNS[result.run_id] = result.to_public_dict()
    return result.model_card


@app.get("/api/thresholds")
def get_thresholds() -> dict[str, Any]:
    path = Path("outputs/threshold_registry.json")
    if path.exists():
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    result = run_pipeline(PipelineConfig(candidate_count=20, compute_profile="cpu-demo", output_dir=Path("outputs")))
    _RUNS[result.run_id] = result.to_public_dict()
    return result.threshold_registry
