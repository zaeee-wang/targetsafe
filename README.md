# Target-SAFE Molecular Evidence Digital Twin

Target-SAFE is an evidence-gated lead triage platform for the 4th JUMP AI Agentic Drug Challenge. The EGFR mutation-positive NSCLC pilot classifies seed-derived lead candidates as `Go`, `Hold`, or `No-Go` while showing the molecular structure, descriptor risks, predicted activity interval, applicability domain, external evidence, critic findings, and next validation steps.

The project does **not** claim that AI invented a drug. It demonstrates how an agentic system can narrow early lead-review scope with transparent, reproducible evidence.

## Try It Yourself

There are three supported ways to try Target-SAFE.

1. **Public VM / VPS demo:** deploy the bundled FastAPI backend and React/Nginx frontend with Docker Compose.
2. **Local Windows demo:** run `START_TARGETSAFE.bat` or `.\scripts\start_targetsafe.ps1`, then open `http://127.0.0.1:5173/`.
3. **Local GPU research lane:** run the app from a CUDA-enabled Python environment so `/api/gpu-diagnostics` can confirm the actual PyTorch CUDA backend.

For public sharing, use the Docker path:

```bash
git clone https://github.com/zaeee-wang/targetsafe.git
cd targetsafe
docker compose up --build -d
```

Open `http://<server-ip-or-domain>:5173/` and check `http://<server-ip-or-domain>:5173/api/health`.

Detailed deployment notes are in [DEPLOYMENT.md](DEPLOYMENT.md). The public Docker demo does not require GPU or LLM API keys; those lanes are optional and clearly reported as requested/available/used/fallback in the UI.

## Recommended Judge Demo Flow

For a competition reviewer or teammate:

1. Open `Run Console` and click `Run Full research mode` or `Stable CPU demo`.
2. Open `Molecule Atlas` and inspect the Go/Hold/No-Go distribution.
3. Open `Candidate Twin` for one Go, one Hold, and one No-Go candidate.
4. Open `Reports` and review the `Agent Flow Diagram`, decision rulebook, validation status, and technical trace appendix.
5. Open `Evidence Graph` and `Known Drugs & Risks` to confirm evidence context and reference-drug risk framing.

## What Changed

The earlier MVP was useful but too close to a rule-based table. This version adds:

- React + TypeScript molecular digital twin UI.
- Pintel-inspired, Target-SAFE-specific `Molecular Evidence Flow` UI with separated app sections, not a landing page.
- Korean/English language switch and dark/light display switch.
- Rewritten native Korean UI copy, replacing the previous broken/awkward translation strings.
- Collapsible navigation drawer so the research workspace is not permanently consumed by the left rail.
- Interactive Three.js molecular/evidence orbital in the Run Console, with reduced-motion fallback.
- Compact Run Console sections for inputs, library, LLM/API settings, and execution truth.
- FastAPI backend.
- SQLite cache telemetry with hit/miss/stale/negative-cache summaries.
- Per-run API circuit breaker and stale-cache fallback to reduce repeated public API failure delays.
- Bounded run execution manager plus performance/debug endpoints for local demo operability.
- CPU/GPU/API compute profile selector.
- `Full research mode` is now the default run profile, with a stable CPU demo kept as a fallback action.
- Optional OpenAI-compatible LLM API key input in the Run Console; the key is sent with the run request and is not returned in reports.
- Runtime status panel that separates GPU/LLM `requested`, `available`, `used`, and fallback status.
- GPU diagnostics that distinguish OS-visible GPU hardware, PyTorch CUDA usability, DirectML availability, and the actual Target-SAFE accelerated lane.
- LLM provider selector for deterministic fallback, OpenAI, Anthropic, and OpenAI-compatible custom endpoints.
- Run example/test-case drawer for EGFR positive control, caffeine out-of-domain control, invalid SMILES, structural-alert stress control, and uploaded mini-library checks.
- Target Scenario Library for EGFR scored pilot plus ALK/BRAF/KRAS/HER2 evidence-only scenarios, so non-EGFR targets are explored without overclaiming target-specific Go decisions.
- Assay Planner that recommends the next uncertainty-reducing validation step for Hold/No-Go candidates.
- Activity Cliff Radar that flags similar candidate pairs with large predicted activity deltas as QSAR fragility zones.
- Target Readiness panel that shows whether each target has enough assay/QSAR evidence for confident scoring.
- Structured run logging, API gating, and candidate-level error records for debugging network, chemistry, GPU, LLM, and fallback states.
- Guided setup strip that explains evidence scope, compute lane, staged triage, and first inspection target.
- Judge Demo tab that turns one run into a competition-ready story: problem, agentic loop, evidence-gated decision, representative candidates, runtime truth, and contribution.
- Seed molecule drawer for choosing known drugs and control molecules without hand-typing SMILES.
- Library-scale staged triage across seed analogs, ChEMBL target molecules, PubChem/reference records, and pasted/uploaded SMILES.
- Library Browser metric band, richer filters, and 2-4 candidate comparison drawer for large compound sets.
- RDKit 2D structure depiction and interactive computed conformer view.
- Improved fallback 2D bond-line depiction when RDKit is unavailable.
- Known EGFR drug reference library plus a broader public drug atlas.
- Computed conformer XYZ export for external viewers such as PyMOL or Avogadro.
- Compute profile comparison matrix and target expansion map.
- Scoped evidence graph view to avoid unreadable all-node label overlap.
- Evidence graph label-density control and legend for readable selected-candidate neighborhoods.
- Threshold registry with source/rationale for every decision gate.
- Candidate-level gate audit showing observed value, threshold, direction, pass/review/block status, source, and rationale for each Go/Hold/No-Go decision.
- Candidate Twin gate rail that summarizes pass/review/block gates before showing the detailed audit table.
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

Fastest local path on Windows:

```powershell
.\START_TARGETSAFE.bat
```

or:

```powershell
.\scripts\start_targetsafe.ps1
```

Then open `http://127.0.0.1:5173/`.

To stop only the processes started by the script:

```powershell
.\scripts\stop_targetsafe.ps1
```

To diagnose Python, Node, API health, and CUDA/GPU visibility:

```powershell
.\scripts\check_targetsafe.ps1
```

Manual backend run:

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
- `Judge Demo`: present one completed run as a short evaluation-ready story for reviewers.
- `Seed Molecule Drawer`: choose EGFR reference seeds, general drug-like controls, or negative/stress controls with structure previews.
- `Library Browser`: browse candidate pages with source/status/property/risk filters, lazy 2D structure loading, and comparison drawer.
- `Candidate Twin`: inspect one candidate in 2D/3D with decision rationale, critic redesign context, and XYZ export.
- `Evidence Graph`: zoom and pan through scoped graph-grounded evidence.
- `Known Drugs & Risks`: review known EGFR TKI structures, label-level risk context, and a broader public drug atlas.
- `Reports`: evidence mode, runtime status, library-scale screening summary, scientific validation, model card, threshold registry, agentic trace, redesign report, and readable HTML report.

## Docker Demo

CPU-compatible shared demo:

```powershell
docker compose up --build -d
```

Then open `http://127.0.0.1:5173/`. GPU acceleration is best tested with the local `.venv` route because the app reports the actual Python CUDA backend used by Target-SAFE. An optional `docker-compose.gpu.yml` is included for NVIDIA Container Toolkit environments.

For a public VM/VPS demo, expose TCP port `5173` and use the same command. The frontend proxies `/api` to the backend container, so users only need the frontend URL.

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

- `DEPLOYMENT.md`
- `outputs/TARGET_SAFE_IMPLEMENTATION_GUIDE.md`
- Korean problem statement: `outputs/TARGET_SAFE_PROBLEM_STATEMENT_KO.md`
- UI walkthrough: `outputs/TARGET_SAFE_UI_WALKTHROUGH.md`
- UI/UX design guide: `outputs/TARGET_SAFE_UI_UX_DESIGN_GUIDE_KO.md`
- Compute profile guide: `outputs/TARGET_SAFE_COMPUTE_PROFILES.md`

## API

- `GET /api/health`
- `GET /api/compute-profiles`
- `GET /api/runtime-status`
- `GET /api/gpu-diagnostics`
- `GET /api/cache/stats`
- `GET /api/debug/performance`
- `GET /api/llm/providers`
- `POST /api/llm/test`
- `GET /api/decision-rules`
- `GET /api/run-examples`
- `GET /api/target-profiles`
- `GET /api/library/sources`
- `POST /api/library/import`
- `GET /api/reference-drugs`
- `GET /api/reference-drugs/{drug_id}`
- `POST /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/status`
- `GET /api/runs/{run_id}/candidates?limit=&offset=&status=&source=&sort=`
- `GET /api/runs/{run_id}/evidence-graph`
- `GET /api/runs/{run_id}/agent-trace`
- `GET /api/runs/{run_id}/validation`
- `GET /api/runs/{run_id}/redesign-report`
- `GET /api/runs/{run_id}/library-report`
- `GET /api/runs/{run_id}/assay-plan`
- `GET /api/runs/{run_id}/activity-cliffs`
- `GET /api/runs/{run_id}/target-readiness`
- `GET /api/runs/{run_id}/logs?level=&category=`
- `GET /api/debug/health`
- `GET /api/runs/{run_id}/candidates/{candidate_id}/conformer`
- `GET /api/runs/{run_id}/candidates/{candidate_id}/known-context`
- `GET /api/runs/{run_id}/report`
- `GET /api/model-card/egfr`
- `GET /api/thresholds`

## Safety And Scope

Target-SAFE is a decision-support artifact. Generated candidates, predicted activity, conformers, and graph explanations require medicinal chemistry review and experimental confirmation. Clinical and regulatory signals are class-level context only.

EGFR is the scored scientific pilot. Other target families can be shown in the public drug atlas, but Go/Hold/No-Go scoring should not be reused for non-EGFR targets until target-specific assay evidence, applicability-domain checks, and thresholds are added.

GPU and LLM lanes are optional enhancers, not final decision makers. The final Go/Hold/No-Go decision is grounded in descriptors, analog evidence, applicability-domain checks, sourced thresholds, evidence graph support, and Critic Agent review. If validation data are insufficient, Target-SAFE reports `insufficient_data` rather than fabricating model metrics.
