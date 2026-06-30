# Target-SAFE Molecular Evidence Digital Twin

Target-SAFE is an evidence-gated lead triage platform for the 4th JUMP AI Agentic Drug Challenge. The EGFR mutation-positive NSCLC pilot classifies seed-derived lead candidates as `Go`, `Hold`, or `No-Go` while showing the molecular structure, descriptor risks, predicted activity interval, applicability domain, external evidence, critic findings, and next validation steps.

The project does **not** claim that AI invented a drug. It demonstrates how an agentic system can narrow early lead-review scope with transparent, reproducible evidence.

## What Changed

The earlier MVP was useful but too close to a rule-based table. This version adds:

- React + TypeScript molecular digital twin UI.
- Apple-inspired dark/light research atlas UI with separated app sections.
- Korean/English language switch and dark/light display switch.
- FastAPI backend.
- CPU/GPU/API compute profile selector.
- `Full research mode` is now the default run profile, with a stable CPU demo kept as a fallback action.
- Optional OpenAI-compatible LLM API key input in the Run Console; the key is sent with the run request and is not returned in reports.
- Runtime status panel that separates GPU/LLM `requested`, `available`, `used`, and fallback status.
- GPU diagnostics that distinguish OS-visible GPU hardware, PyTorch CUDA usability, DirectML availability, and the actual Target-SAFE accelerated lane.
- LLM provider selector for deterministic fallback, OpenAI, Anthropic, and OpenAI-compatible custom endpoints.
- Run example/test-case drawer for EGFR positive control, caffeine out-of-domain control, invalid SMILES, structural-alert stress control, and uploaded mini-library checks.
- Seed molecule drawer for choosing known drugs and control molecules without hand-typing SMILES.
- Library-scale staged triage across seed analogs, ChEMBL target molecules, PubChem/reference records, and pasted/uploaded SMILES.
- RDKit 2D structure depiction and interactive computed conformer view.
- Improved fallback 2D bond-line depiction when RDKit is unavailable.
- Known EGFR drug reference library plus a broader public drug atlas.
- Computed conformer XYZ export for external viewers such as PyMOL or Avogadro.
- Compute profile comparison matrix and target expansion map.
- Scoped evidence graph view to avoid unreadable all-node label overlap.
- Threshold registry with source/rationale for every decision gate.
- Candidate-level gate audit showing observed value, threshold, direction, pass/review/block status, source, and rationale for each Go/Hold/No-Go decision.
- Analog-supported EGFR QSAR with prediction interval and applicability domain.
- Agentic trace with `Plan -> Act -> Observe -> Critique -> Replan -> Redesign -> Re-evaluate -> Decide` events.
- Critic-triggered constrained redesign loop with parent/child candidate comparison.
- EGFR QSAR validation outputs that report metrics only when enough structure/activity rows exist.
- Evidence mode badges that distinguish offline fallback, live, cached, mixed, and error fallback evidence.
- Tool-call error summary that distinguishes network refused, timeout, empty result, cached, network disabled, and fallback states.
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
- `Seed Molecule Drawer`: choose EGFR reference seeds, general drug-like controls, or negative/stress controls with structure previews.
- `Molecule Atlas`: browse candidate pages with source/status/sort filters and lazy 2D structure loading.
- `Candidate Twin`: inspect one candidate in 2D/3D with decision rationale, critic redesign context, and XYZ export.
- `Evidence Graph`: zoom and pan through scoped graph-grounded evidence.
- `Known Drugs & Risks`: review known EGFR TKI structures, label-level risk context, and a broader public drug atlas.
- `Reports`: evidence mode, runtime status, library-scale screening summary, scientific validation, model card, threshold registry, agentic trace, redesign report, and readable HTML report.

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

`Full research mode` requests live evidence, GPU, and LLM lanes by default. The UI distinguishes what was requested from what was actually available and used. GPU status reports OS-visible GPU hardware, PyTorch CUDA availability, optional DirectML availability, device name when detected, whether the accelerated similarity lane ran, and fallback reason when it did not. If a PC has an NVIDIA GPU but the active Python environment has no CUDA-enabled PyTorch, Target-SAFE reports that hardware was detected but the compute backend is unavailable.

LLM support can use deterministic fallback, OpenAI, Anthropic, or an OpenAI-compatible custom endpoint. API keys are accepted in the Run Console for a single run/test request and are not returned in run payloads, reports, or logs.

GPU and LLM are optional enhancers. The core pipeline works without either.

## Outputs

Generated outputs are written to `outputs/`:

- `model_card_egfr.json`
- `threshold_registry.json`
- `evidence_graph.json`
- `ablation_report.html`
- `evaluation_metrics_egfr.json`
- `qsar_validation_report.html`
- `scaffold_split_summary.json`
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
- `GET /api/runtime-status`
- `GET /api/gpu-diagnostics`
- `GET /api/llm/providers`
- `POST /api/llm/test`
- `GET /api/decision-rules`
- `GET /api/run-examples`
- `GET /api/library/sources`
- `POST /api/library/import`
- `GET /api/reference-drugs`
- `GET /api/reference-drugs/{drug_id}`
- `POST /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/candidates?limit=&offset=&status=&source=&sort=`
- `GET /api/runs/{run_id}/evidence-graph`
- `GET /api/runs/{run_id}/agent-trace`
- `GET /api/runs/{run_id}/validation`
- `GET /api/runs/{run_id}/redesign-report`
- `GET /api/runs/{run_id}/library-report`
- `GET /api/runs/{run_id}/candidates/{candidate_id}/conformer`
- `GET /api/runs/{run_id}/candidates/{candidate_id}/known-context`
- `GET /api/runs/{run_id}/report`
- `GET /api/model-card/egfr`
- `GET /api/thresholds`

## Safety And Scope

Target-SAFE is a decision-support artifact. Generated candidates, predicted activity, conformers, and graph explanations require medicinal chemistry review and experimental confirmation. Clinical and regulatory signals are class-level context only.

EGFR is the scored scientific pilot. Other target families can be shown in the public drug atlas, but Go/Hold/No-Go scoring should not be reused for non-EGFR targets until target-specific assay evidence, applicability-domain checks, and thresholds are added.

GPU and LLM lanes are optional enhancers, not final decision makers. The final Go/Hold/No-Go decision is grounded in descriptors, analog evidence, applicability-domain checks, sourced thresholds, evidence graph support, and Critic Agent review. If validation data are insufficient, Target-SAFE reports `insufficient_data` rather than fabricating model metrics.
