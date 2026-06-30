from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from targetsafe.chem import evaluate_smiles, mol_conformer_payload, mol_svg_data_uri
from targetsafe.compute_profiles import profile_options
from targetsafe.library import DEFAULT_LIBRARY_SOURCES, parse_uploaded_smiles_text
from targetsafe.pipeline import PipelineConfig, run_pipeline
from targetsafe.reference_drugs import known_context_for_smiles, reference_drug, reference_drugs
from targetsafe.runtime import runtime_status


DEFAULT_DISEASE = "EGFR mutation-positive NSCLC"
DEFAULT_TARGET = "EGFR"
DEFAULT_SEED = "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1"
DEFAULT_GOAL = "Maintain drug-likeness, reduce toxicity alerts, preserve EGFR evidence confidence"


class RunRequest(BaseModel):
    disease: str = Field(default=DEFAULT_DISEASE)
    target: str = Field(default=DEFAULT_TARGET)
    seed_smiles: str = Field(default=DEFAULT_SEED)
    optimization_goal: str = Field(default=DEFAULT_GOAL)
    candidate_count: int = Field(default=96, ge=20, le=10000)
    compute_profile: str = Field(default="full-research")
    allow_network: bool = True
    use_llm: bool = True
    use_gpu: bool = True
    enable_conformers: bool = True
    library_sources: list[str] = Field(default_factory=lambda: list(DEFAULT_LIBRARY_SOURCES))
    library_limit: int = Field(default=2000, ge=20, le=10000)
    detailed_eval_limit: int = Field(default=300, ge=20, le=2000)
    display_limit: int = Field(default=96, ge=10, le=500)
    conformer_limit: int = Field(default=24, ge=0, le=200)
    uploaded_smiles: list[str] = Field(default_factory=list)
    uploaded_library_id: str | None = None
    llm_api_key: str = Field(default="", max_length=4000)
    llm_base_url: str = Field(default="", max_length=400)
    llm_model: str = Field(default="", max_length=120)


class LibraryImportRequest(BaseModel):
    name: str = Field(default="Uploaded compound library")
    text: str = Field(default="")
    smiles: list[str] = Field(default_factory=list)


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
_UPLOADED_LIBRARIES: dict[str, dict[str, Any]] = {}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/compute-profiles")
def compute_profiles() -> list[dict[str, Any]]:
    return profile_options()


@app.get("/api/runtime-status")
def get_runtime_status() -> dict[str, Any]:
    return runtime_status(requested_gpu=True, requested_llm=True)


@app.get("/api/library/sources")
def get_library_sources() -> list[dict[str, Any]]:
    return [
        {"id": "seed_analog", "label": "Seed analog library", "requires_network": False},
        {"id": "chembl_target", "label": "ChEMBL target activity rows", "requires_network": True},
        {"id": "pubchem_reference", "label": "PubChem/reference drug structures", "requires_network": True},
        {"id": "uploaded", "label": "Uploaded/pasted SMILES library", "requires_network": False},
    ]


@app.post("/api/library/import")
def import_library(request: LibraryImportRequest) -> dict[str, Any]:
    rows = [*parse_uploaded_smiles_text(request.text), *[item.strip() for item in request.smiles if item.strip()]]
    library_id = f"uploaded_{len(_UPLOADED_LIBRARIES) + 1:04d}"
    _UPLOADED_LIBRARIES[library_id] = {"name": request.name, "smiles": rows}
    return {
        "library_id": library_id,
        "name": request.name,
        "compound_count": len(rows),
        "message": "Imported into the current API process; include uploaded library source in the next run.",
    }


@app.get("/api/reference-drugs")
def get_reference_drugs() -> list[dict[str, Any]]:
    return reference_drugs(include_structures=True)


@app.get("/api/reference-drugs/{drug_id}")
def get_reference_drug(drug_id: str) -> dict[str, Any]:
    drug = reference_drug(drug_id)
    if drug is None:
        raise HTTPException(status_code=404, detail="Reference drug not found.")
    return drug


@app.get("/api/depict")
def depict_smiles(smiles: str = Query(..., min_length=1, max_length=1200)) -> dict[str, Any]:
    descriptor = evaluate_smiles(smiles)
    return {
        "valid": descriptor.valid,
        "canonical_smiles": descriptor.canonical_smiles,
        "structure_svg": mol_svg_data_uri(smiles) if descriptor.valid else None,
        "method": descriptor.method,
        "molecular_weight": descriptor.molecular_weight,
        "qed": descriptor.qed,
        "sa_score": descriptor.sa_score,
        "alerts": descriptor.alerts,
    }


@app.post("/api/runs")
def create_run(request: RunRequest) -> dict[str, Any]:
    uploaded_smiles = list(request.uploaded_smiles)
    if request.uploaded_library_id and request.uploaded_library_id in _UPLOADED_LIBRARIES:
        uploaded_smiles.extend(_UPLOADED_LIBRARIES[request.uploaded_library_id].get("smiles", []))
    library_sources = list(request.library_sources)
    if uploaded_smiles and "uploaded" not in library_sources:
        library_sources.append("uploaded")
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
            library_sources=library_sources,
            library_limit=request.library_limit,
            detailed_eval_limit=request.detailed_eval_limit,
            display_limit=request.display_limit,
            conformer_limit=request.conformer_limit,
            uploaded_smiles=uploaded_smiles,
            llm_api_key=request.llm_api_key,
            llm_base_url=request.llm_base_url,
            llm_model=request.llm_model,
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


@app.get("/api/runs/{run_id}/agent-trace")
def get_agent_trace(run_id: str) -> list[dict[str, Any]]:
    payload = get_run(run_id)
    return payload.get("agent_events", [])


@app.get("/api/runs/{run_id}/validation")
def get_validation(run_id: str) -> dict[str, Any]:
    payload = get_run(run_id)
    return payload.get("validation_report", {})


@app.get("/api/runs/{run_id}/redesign-report")
def get_redesign_report(run_id: str) -> dict[str, Any]:
    payload = get_run(run_id)
    return payload.get("redesign_report", {})


@app.get("/api/runs/{run_id}/library-report")
def get_library_report(run_id: str) -> dict[str, Any]:
    payload = get_run(run_id)
    return payload.get("library_report", {})


@app.get("/api/runs/{run_id}/candidates")
def get_candidates(
    run_id: str,
    limit: int = Query(default=96, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status: str = Query(default="all"),
    source: str = Query(default="all"),
    sort: str = Query(default="rank"),
) -> dict[str, Any]:
    payload = get_run(run_id)
    candidates = list(payload.get("candidates", []))
    if status != "all":
        candidates = [
            candidate
            for candidate in candidates
            if (candidate.get("decision") or {}).get("final_status") == status
        ]
    if source != "all":
        candidates = [
            candidate
            for candidate in candidates
            if candidate.get("library_source") == source or candidate.get("source") == source
        ]
    if sort == "activity":
        candidates.sort(key=lambda item: item.get("predicted_activity") or -999, reverse=True)
    elif sort == "applicability":
        candidates.sort(key=lambda item: item.get("applicability_score") or 0, reverse=True)
    elif sort == "qed":
        candidates.sort(key=lambda item: ((item.get("descriptors") or {}).get("qed") or 0), reverse=True)
    total = len(candidates)
    return {
        "run_id": run_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": candidates[offset : offset + limit],
    }


@app.get("/api/runs/{run_id}/candidates/{candidate_id}/conformer")
def get_candidate_conformer(run_id: str, candidate_id: str) -> dict[str, Any]:
    payload = get_run(run_id)
    candidates = payload.get("candidates", [])
    for candidate in candidates:
        if candidate.get("candidate_id") != candidate_id:
            continue
        if candidate.get("conformer"):
            return candidate["conformer"]
        smiles = str(candidate.get("smiles", ""))
        descriptor = evaluate_smiles(smiles)
        if not descriptor.valid:
            raise HTTPException(status_code=422, detail="Candidate has invalid SMILES.")
        conformer = mol_conformer_payload(smiles)
        candidate["conformer"] = conformer
        return conformer or {"available": False, "label": "computed conformer unavailable", "message": "No conformer payload returned.", "atoms": [], "bonds": []}
    raise HTTPException(status_code=404, detail="Candidate not found in current API process.")


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
