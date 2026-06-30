# Target-SAFE Compute Profiles

## CPU demo

Purpose: stable judging demo.

- no live network required,
- no GPU required,
- fallback EGFR evidence,
- deterministic output.

Use when the presentation must be reliable.

## CPU evidence-grade

Purpose: public evidence refresh.

- ChEMBL,
- ClinicalTrials.gov,
- openFDA,
- RDKit descriptors,
- CPU QSAR path.

Use when internet/API access is available.

## GPU accelerated

Purpose: stronger molecular representation and uncertainty support.

- GPU detection,
- optional embedding/analog retrieval metadata,
- future ensemble uncertainty path,
- CPU fallback if GPU is unavailable.

Use when GPU is available but do not make GPU a hard requirement.

## API assisted

Purpose: improve language and graph-grounded reporting.

- optional LLM planner/report support,
- optional hosted ADMET or embedding adapters,
- API call logs retained.

Use when API credits are available.

## Full research mode

Purpose: best-quality final run.

- live public evidence,
- optional GPU acceleration,
- optional LLM graph-grounded summary,
- full reports and traceability.

Use when time and resources are available.
