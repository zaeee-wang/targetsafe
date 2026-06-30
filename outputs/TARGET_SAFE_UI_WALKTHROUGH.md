# Target-SAFE UI Walkthrough

## First View

The first screen is the working triage dashboard, not a marketing page.

It shows:

- disease and target,
- selected compute profile,
- run status,
- Go/Hold/No-Go counts,
- evidence completeness for the selected candidate,
- top molecular candidate after a run.

## Candidate Board

Candidates are grouped into `Go`, `Hold`, and `No-Go` columns. Each row shows:

- candidate ID,
- conservative lower pChEMBL bound,
- applicability-domain score.

Selecting a row opens the molecular evidence twin.

## Molecular Evidence Twin

The twin is the main demonstration surface.

Left:

- RDKit-generated 2D structure,
- optional 3D computed conformer.

Center:

- final decision,
- main reasons,
- predicted activity interval,
- pass/review/block criteria.

Right:

- target-fit rail,
- QED/SA rail,
- alert rail,
- evidence graph rail.

Footer:

- nearest known analogs,
- next validation steps.

## Evidence Graph

The graph connects:

- candidate,
- descriptor,
- prediction,
- known analogs,
- thresholds,
- structural alerts,
- class-level clinical/regulatory risks,
- final decision.

The graph is used for explanation and traceability, not as a hidden scoring model.

## Model Card And Trace

The lower panels expose:

- agent plan,
- tool-call statuses,
- EGFR QSAR model card,
- report link.

This is designed to answer the judging question: "Why did the agent decide this, and what evidence supports that decision?"
