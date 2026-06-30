# Target-SAFE Molecular Evidence Digital Twin

Target-SAFE is an evidence-gated lead triage platform for the 4th JUMP AI Agentic Drug Challenge. The EGFR mutation-positive NSCLC pilot classifies seed-derived lead candidates as `Go`, `Hold`, or `No-Go` while showing the molecular structure, descriptor risks, predicted activity interval, applicability domain, external evidence, critic findings, and next validation steps.

The project does **not** claim that AI invented a drug. It demonstrates how an agentic system can narrow early lead-review scope with transparent, reproducible evidence.

## What Changed

The earlier MVP was useful but too close to a rule-based table. This version adds:

- React + TypeScript molecular digital twin UI.
- FastAPI backend.
- CPU/GPU/API compute profile selector.
- RDKit 2D structure depiction and optional computed conformer view.
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
- `POST /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/evidence-graph`
- `GET /api/runs/{run_id}/report`
- `GET /api/model-card/egfr`
- `GET /api/thresholds`

## Safety And Scope

Target-SAFE is a decision-support artifact. Generated candidates, predicted activity, conformers, and graph explanations require medicinal chemistry review and experimental confirmation. Clinical and regulatory signals are class-level context only.
