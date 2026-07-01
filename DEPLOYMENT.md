# Target-SAFE Deployment Guide

This guide explains how to let other people try Target-SAFE without needing your local development machine.

## Recommended Public Demo: Docker VM/VPS

Use this path for judges, teammates, or reviewers who need a browser-accessible demo.

### 1. Prepare a server

- Linux VM/VPS with Docker and Docker Compose plugin installed.
- Open inbound TCP port `5173`.
- Optional: attach a domain and reverse proxy later. The default demo works directly on `http://<server-ip>:5173/`.

### 2. Clone and run

```bash
git clone https://github.com/zaeee-wang/targetsafe.git
cd targetsafe
docker compose up --build -d
```

### 3. Verify

```bash
docker compose ps
docker compose logs --tail=80 backend
docker compose logs --tail=80 frontend
```

Open:

- `http://<server-ip-or-domain>:5173/`
- `http://<server-ip-or-domain>:5173/api/health`

### 4. Stop or update

```bash
docker compose down
git pull
docker compose up --build -d
```

## What The Public Docker Demo Does And Does Not Do

- It runs the FastAPI backend and React/Nginx frontend together.
- The frontend proxies `/api` to the backend container, so users only need port `5173`.
- It persists `outputs/` and `work/` as local bind mounts.
- It does not require an OpenAI, Anthropic, ChEMBL, PubChem, ClinicalTrials.gov, or openFDA key for the deterministic demo path.
- It does not require GPU. GPU is an optional enhancer, not a decision maker.

Target-SAFE always reports whether GPU/LLM/API lanes were requested, available, actually used, or replaced by fallback. Public demos should be presented as evidence-gated triage demos, not as GPU-dependent drug discovery claims.

## Local Windows Demo

Use this path when a reviewer clones the repository and wants to run it on a Windows workstation.

```powershell
.\START_TARGETSAFE.bat
```

or:

```powershell
.\scripts\start_targetsafe.ps1
```

Open:

```text
http://127.0.0.1:5173/
```

Stop only Target-SAFE processes started by the script:

```powershell
.\scripts\stop_targetsafe.ps1
```

Check Python, Node, backend/frontend health, and GPU visibility:

```powershell
.\scripts\check_targetsafe.ps1
```

## Local GPU Research Lane

For real local GPU diagnostics, use a Python environment where PyTorch can see CUDA.

```powershell
python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO CUDA')"
```

Then start Target-SAFE:

```powershell
.\scripts\start_targetsafe.ps1
```

Open `Run Console -> Execution Reality` or call:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/gpu-diagnostics
```

If hardware is visible but PyTorch CUDA is not usable, Target-SAFE will report that distinction rather than pretending the GPU lane ran.

## Optional NVIDIA Docker Path

Only use this if the server has NVIDIA Container Toolkit configured.

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
```

This still does not make GPU a final decision maker. It only enables optional acceleration lanes where the backend can actually use the GPU runtime.

## Recommended Demo Script

1. Open `Run Console`.
2. Choose `Full research mode` for the full path, or `Stable CPU demo` for rehearsals.
3. Run triage.
4. Open `Molecule Atlas` and show library size plus Go/Hold/No-Go counts.
5. Open `Candidate Twin` for representative Go, Hold, and No-Go candidates.
6. Open `Reports` and show `Agent Flow Diagram`, decision rulebook, validation status, and technical trace appendix.
7. Open `Evidence Graph` and `Known Drugs & Risks` to show source-grounded context.

## Security And Secrets

- LLM API keys entered in the UI are sent only with the current run/test request.
- API keys are not stored in `localStorage`, run payloads, reports, cache, or logs.
- Public Docker demos should avoid embedding secrets in image layers.
- If you set environment variables such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` on a private server, keep them in deployment secrets or shell environment, not in Git.

## Pre-Push / Pre-Deploy Checks

```powershell
python -m unittest discover -s tests
cd frontend
npm run build
cd ..
docker compose config
```

For a running local demo:

```powershell
.\scripts\check_targetsafe.ps1
```
