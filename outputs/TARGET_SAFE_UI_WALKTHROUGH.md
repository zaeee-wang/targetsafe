# Target-SAFE UI Walkthrough

## Design Direction

The UI has been redesigned as a dark molecular research atlas, not a landing page. The visual language uses:

- Pretendard typography,
- black laboratory-stage surfaces,
- large molecule figures,
- thin evidence rails,
- separated work sections,
- minimal copy,
- no crowded all-in-one dashboard.

The goal is to make the molecule and its evidence state feel like the inspected research object.

## App Structure

Target-SAFE now uses six sections.

1. `Run Console`
   - Configure disease, target, seed SMILES, candidate count, compute profile, API/GPU/LLM toggles.
   - Run the stable CPU demo or the selected profile.
   - Compare compute profiles side by side, so CPU demo, GPU accelerated, API assisted, and full research modes are visibly different.
   - Review the target expansion map: EGFR is the scored pilot, while ALK/BRAF/KRAS/HER2 are expansion lanes that need target-specific evidence before scoring.

2. `Molecule Atlas`
   - Shows up to 96 generated candidates and controls as large molecule figures.
   - Shows known EGFR reference drugs and broader public drug atlas entries.
   - Uses improved fallback bond-line drawings when RDKit is unavailable.

3. `Candidate Twin`
   - Shows the selected candidate as a molecular evidence twin.
   - Supports 2D structure and interactive 3D conformer views.
   - The 3D view is explicitly labeled as a computed conformer, not a binding pose.
   - Exports a simple `.xyz` conformer file for external viewers such as PyMOL or Avogadro.

4. `Evidence Graph`
   - Provides a dedicated zoomable and pannable graph explorer.
   - Defaults to selected-candidate neighborhood view to avoid label overlap.
   - Supports graph scope, node-type filter, edge-type filter, fit view, zoom controls, and selected-candidate centering.

5. `Known Drugs & Risks`
   - Shows known EGFR TKI structures and known label-level adverse reaction context.
   - Adds broader public drug atlas entries for visual browsing of existing drug-like molecules.
   - Clearly states that known-drug risk context is not candidate-specific toxicity.

6. `Reports`
   - Shows model card, threshold registry, agent trace, and report link.

## Why This Fixes The Previous UI Problem

The previous UI placed run setup, candidates, twin, graph, trace, and model card on one long page. That made the app look like a crowded dashboard and made first-time use unclear.

The new UI separates actions by research intent:

- run first,
- inspect structures,
- inspect one candidate deeply,
- inspect evidence graph,
- inspect known drug risk context,
- export reports.

This makes the system easier to demonstrate and easier for judges to understand.

## Known Drug Risk Interpretation

Known EGFR drug side effects are shown only as reference context.

Target-SAFE does not say:

- a generated candidate has the same adverse effects,
- label warnings prove candidate toxicity,
- similarity is sufficient for safety conclusion.

Target-SAFE does say:

- these are known EGFR TKI review topics,
- similar scaffolds should be reviewed carefully,
- follow-up assays and expert review are required.
