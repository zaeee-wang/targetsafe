# Target-SAFE UI Walkthrough

## Design Direction

The UI now follows a quiet Apple-inspired product-gallery language:

- white and parchment surfaces,
- a single blue action color,
- thin chrome and hairline borders,
- molecule imagery treated as the primary artifact,
- no decorative gradients,
- no card shadows except a soft product-style shadow under molecule renders.

The goal is not to imitate a consumer landing page. The goal is to make the candidate molecule feel like the inspected product while preserving research-tool clarity.

## First View

The first screen explains the workflow in three steps:

1. select compute profile,
2. run triage,
3. inspect the molecular twin.

The `Run CPU demo` button gives first-time users a safe starting point. The normal `Run triage` action remains in the sticky top bar.

## Molecule Catalog

After a run, candidates appear as a molecule catalog instead of a plain table.

Each molecule card shows:

- 2D structure image,
- Go/Hold/No-Go status,
- candidate ID,
- conservative lower pChEMBL bound,
- applicability-domain score,
- source label.

Selecting a molecule opens the molecular evidence twin.

## Molecular Evidence Twin

The twin is the main inspection surface.

Left:

- large 2D molecular structure,
- 3D model panel.

If RDKit is installed, the 2D structure and conformer can use RDKit outputs. If RDKit is unavailable, Target-SAFE renders a SMILES schematic and a fallback 3D layout so the UI remains visual and demonstrable.

Center:

- final decision,
- main rationale,
- conservative activity interval,
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

This answers the judging question: "Why did the agent decide this, and what evidence supports that decision?"
