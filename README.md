# Target-SAFE Molecular Evidence Digital Twin

Target-SAFE is an evidence-gated lead triage platform for the 4th JUMP AI Agentic Drug Challenge. The EGFR mutation-positive NSCLC pilot classifies seed-derived lead candidates as `Go`, `Hold`, or `No-Go` while showing the molecular structure, descriptor risks, predicted activity interval, applicability domain, external evidence, critic findings, and next validation steps.

The project does **not** claim that AI invented a drug. It demonstrates how an agentic system can narrow early lead-review scope with transparent, reproducible evidence.

## What Changed

The earlier MVP was useful but too close to a rule-based table. This version adds:

- React + TypeScript molecular digital twin UI.
- Dark Pretendard-based research atlas UI with separated app sections.
- FastAPI backend.
- CPU/GPU/API compute profile selector.
- RDKit 2D structure depiction and interactive computed conformer view.
- Improved fallback 2D bond-line depiction when RDKit is unavailable.
- Known EGFR drug reference library plus a broader public drug atlas.
- Computed conformer XYZ export for external viewers such as PyMOL or Avogadro.
- Compute profile comparison matrix and target expansion map.
- Scoped evidence graph view to avoid unreadable all-node label overlap.
- Threshold registry with source/rationale for every decision gate.
- Analog-supported EGFR QSAR with prediction interval and applicability domain.
- GraphRAG-lite evidence graph.
- Model card, ablation report, HTML report, and JSON outputs.
- Streamlit fallback demo.

## Run Backend

```powershell
pip install -r requirements.txt
uvicorn targetsafe.api:app --reload
```

The API runs at `http://127.0.0.1:8000`.

## Run React Frontend

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at `http://127.0.0.1:5173` and proxies `/api` to the FastAPI backend.

Main UI sections:

- `Run Console`: configure and start a triage run.
- `Molecule Atlas`: inspect up to 96 candidate previews and public/reference-drug structures.
- `Candidate Twin`: inspect one candidate in 2D/3D with decision rationale and XYZ export.
- `Evidence Graph`: zoom and pan through scoped graph-grounded evidence.
- `Known Drugs & Risks`: review known EGFR TKI structures, label-level risk context, and a broader public drug atlas.
- `Reports`: model card, threshold registry, trace, and HTML report.

## Backup Streamlit Demo

```powershell
streamlit run app.py
```

If Streamlit is unavailable, `python app.py` runs a CLI demo.

## Test

```powershell
python -m unittest discover -s tests
cd frontend
npm run build
```

## Compute Profiles

- `CPU demo`: stable offline demo with fallback evidence.
- `CPU evidence-grade`: live public API evidence refresh.
- `GPU accelerated`: optional GPU path with graceful CPU fallback.
- `API assisted`: optional LLM/report support.
- `Full research mode`: live evidence + optional GPU + optional LLM.

GPU and LLM are optional. The core pipeline works without either.

## Outputs

Generated outputs are written to `outputs/`:

- `model_card_egfr.json`
- `threshold_registry.json`
- `evidence_graph.json`
- `ablation_report.html`
- `*_targetsafe_report.html`
- `*_result.json`

User-facing guide:

- `outputs/TARGET_SAFE_IMPLEMENTATION_GUIDE.md`
- Korean problem statement: `outputs/TARGET_SAFE_PROBLEM_STATEMENT_KO.md`
- UI walkthrough: `outputs/TARGET_SAFE_UI_WALKTHROUGH.md`
- Compute profile guide: `outputs/TARGET_SAFE_COMPUTE_PROFILES.md`

## API

- `GET /api/health`
- `GET /api/compute-profiles`
- `GET /api/reference-drugs`
- `GET /api/reference-drugs/{drug_id}`
- `POST /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/evidence-graph`
- `GET /api/runs/{run_id}/candidates/{candidate_id}/known-context`
- `GET /api/runs/{run_id}/report`
- `GET /api/model-card/egfr`
- `GET /api/thresholds`

## Safety And Scope

Target-SAFE is a decision-support artifact. Generated candidates, predicted activity, conformers, and graph explanations require medicinal chemistry review and experimental confirmation. Clinical and regulatory signals are class-level context only.

EGFR is the scored scientific pilot. Other target families can be shown in the public drug atlas, but Go/Hold/No-Go scoring should not be reused for non-EGFR targets until target-specific assay evidence, applicability-domain checks, and thresholds are added.
