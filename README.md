# Target-SAFE Lead Agent

Evidence-gated lead triage MVP for the 4th JUMP AI Agentic Drug Challenge.

## Problem And Contribution

The initial project idea was a broad multi-agent molecule optimization system.
That direction is useful, but it can look similar to many "LLM + RDKit +
ChEMBL + ADMET + report" demos and can overclaim what virtual candidates mean.

Target-SAFE narrows the contribution: it is not a system that claims to invent
a drug. It is an evidence-gated triage agent that helps researchers decide
which early lead candidates should be advanced, held for more evidence, or
rejected. The program contributes a transparent `Go / Hold / No-Go` workflow
with hard gates, evidence confidence, applicability-domain checks, critic
findings, and reproducible logs.

The app focuses on EGFR-mutant NSCLC and classifies seed-derived candidates as
`Go`, `Hold`, or `No-Go` using transparent tool-grounded evidence:

- optional RDKit chemistry descriptors and alerts
- ChEMBL/PubChem/ClinicalTrials.gov/openFDA API clients with SQLite cache
- deterministic QSAR-like confidence and applicability-domain scoring
- hard gates before weighted ranking
- critic findings and an HTML report

The core pipeline runs without local GPU and without optional packages. If
RDKit or Streamlit are unavailable, the project falls back to deterministic
heuristics so the demo and tests still work.

## Run

```powershell
python -m unittest discover -s tests
python app.py
```

For the dashboard, install dependencies and run:

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## Optional LLM API

Set these environment variables to let Planner/Critic/Report use an
OpenAI-compatible chat completions endpoint:

```powershell
$env:OPENAI_API_KEY="..."
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_MODEL="gpt-4.1-mini"
```

The deterministic pipeline works without these variables.

## Deliverables

- Implementation guide: `outputs/TARGET_SAFE_IMPLEMENTATION_GUIDE.md`
- Program bundle: `outputs/targetsafe_program_bundle.zip`

Generated run reports such as `outputs/targetsafe_*_result.json` and
`outputs/targetsafe_*_targetsafe_report.html` are demo artifacts and are not
intended to be committed.
