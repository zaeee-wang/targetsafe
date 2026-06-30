# Target-SAFE UI Walkthrough

## Design Direction

The UI has been redesigned as an Apple-inspired molecular research atlas, not a landing page. The visual language uses:

- Pretendard typography,
- dark/light display modes,
- Apple-like white/parchment and near-black surface hierarchy,
- a single blue action color for interactive controls,
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
   - Switch between Korean/English and dark/light mode.
   - Open the seed molecule drawer to choose a known drug or control molecule instead of typing SMILES manually.
   - Run the stable CPU demo or the selected profile.
   - Compare compute profiles side by side, so CPU demo, GPU accelerated, API assisted, and full research modes are visibly different.
   - Review the target expansion map: EGFR is the scored pilot, while ALK/BRAF/KRAS/HER2 are expansion lanes that need target-specific evidence before scoring.

2. `Molecule Atlas`
   - Shows up to 96 generated candidates and controls as large molecule figures.
   - Shows known EGFR reference drugs and broader public drug atlas entries.
   - Uses improved fallback bond-line drawings when RDKit is unavailable.

### Seed Molecule Drawer

The drawer is designed for fast demo and stress testing.

- EGFR reference seeds come from the reference-drug layer when SMILES are available.
- General drug-like controls include familiar small molecules such as aspirin, caffeine, acetaminophen, ibuprofen, and metformin.
- Negative/stress controls include deliberately weak or invalid examples so users can test failure paths.
- Each drawer card requests a 2D depiction through `/api/depict`, so users can see the structure before applying it.
- Non-EGFR seeds are labeled as chemistry/UX tests, not target-specific scoring validation.

3. `Candidate Twin`
   - Shows the selected candidate as a molecular evidence twin.
   - Supports 2D structure and interactive 3D conformer views.
   - The 3D view is explicitly labeled as a computed conformer, not a binding pose.
   - Exports a simple `.xyz` conformer file for external viewers such as PyMOL or Avogadro.
   - Shows whether the candidate is a critic-generated redesign child or whether it has child suggestions.
   - Keeps parent/child comparison as a review aid, not as an optimized-drug claim.

4. `Evidence Graph`
   - Provides a dedicated zoomable and pannable graph explorer.
   - Defaults to selected-candidate neighborhood view to avoid label overlap.
   - Supports graph scope, node-type filter, edge-type filter, fit view, zoom controls, and selected-candidate centering.

5. `Known Drugs & Risks`
   - Shows known EGFR TKI structures and known label-level adverse reaction context.
   - Adds broader public drug atlas entries for visual browsing of existing drug-like molecules.
   - Clearly states that known-drug risk context is not candidate-specific toxicity.

6. `Reports`
   - Shows evidence mode, scientific validation status, model card, threshold registry, agentic trace, redesign report, and report link.
   - Agent trace is now an event timeline covering Plan, Act, Observe, Critique, Replan, Redesign, Re-evaluate, and Decide.
   - Validation panels distinguish insufficient fallback data from real validation metrics.

## Why This Fixes The Previous UI Problem

The previous UI placed run setup, candidates, twin, graph, trace, and model card on one long page. That made the app look like a crowded dashboard and made first-time use unclear.

The new UI separates actions by research intent:

- run first,
- select or type a seed molecule,
- inspect structures,
- inspect one candidate deeply,
- inspect evidence graph,
- inspect known drug risk context,
- inspect critic-driven redesign and validation status,
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
