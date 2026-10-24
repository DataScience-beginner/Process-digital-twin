# E4.1 — First automatic PFD → P&ID configuration expansion

**Date:** 2026-10-24  
**Epic:** https://github.com/DataScience-beginner/Process-digital-twin/issues/19  
**Canvas PR:** https://github.com/DataScience-beginner/Process-digital-twin/pull/23  
**Status:** Benchmarked on synthetic BENCH-001; not a production agent or safety-engineered drawing.

## What is now different from the prior static demo?

The P&ID graph loaded by `prototypes/maxgraph-pid/src/engineering.js` is **no longer copied from `expected_graph.json`**. Instead:
1. Read approved source `docs/forward-pid/fixtures/pfd_input.json` (section, equipment, directed streams and requirements).
2. Read domain-maintained `prototypes/maxgraph-pid/configurations/pump-transfer.json`.
3. `src/generate.js` checks explicit PFD approval, vessel/pump types, source stream phase and endpoint topology, configuration status, declared version and pump arrangement.
4. If exactly one approved configuration matches, it expands the versioned configuration's physical symbols/ports and its path definition into a directed detailed engineering graph.
5. All node and connection IDs, physical/internal edge types, revision, configuration source, stream lineage and unknown engineering values are emitted.
6. `src/main.js` renders the output through **real maxGraph**. The **Generate P&ID from approved PFD** button re-runs the selection and regeneration. A separate engineering command can then insert XV-102, update edges, validate and redraw.
7. If source/standard is unapproved, wrong topology or no applicable standard, return `requires_decision`, with no silently generated engineering arrangement.

## Ground-truth checks

`test/generation.test.js` compares *the generated* graph to the independent `expected_graph.json` fixture: 11 semantic nodes, 19 port-level edges, same configuration and provenance, all unknown numerical values null. Failure tests: unapproved PFD; nonmatching pump arrangement; broken PFD stream; draft-only standard.

This is deliberate **configuration rule reuse**, not LLM improvisation. The **approved standard** in the example is synthetic. It does NOT establish that a liquid pump system always requires a specific isolation valve or that the illustration is an issued design.

## Architecture learning

**Configuration registry = domain product.** The domain engineering team owns approved versioned templates, applicability criteria, port schema and symbol mapping. IT owns generic selection/execution/validation APIs and drawing interactions. The detailed graph remains independent of maxGraph geometry; graph-backed modification regenerates the canvas.

## Limitations / remaining work

- Current matching/expansion is intentionally bounded to *one synthetic pump arrangement* and the fixture's known IDs. The selector is coded in JavaScript prototype, not yet a Python service.
- No live simulation API or real BFD ingestion, multi-unit configuration variants, validated standards library, professional drafting stencils, ELK placement, hydraulic sizing, instrumentation selection or qualified engineering approval workflow.
- Initial drawing coordinates remain illustrative. Automatic generation of graph objects is not automatic CAD layout.
- A public web deployment is not available yet. Run locally with `cd prototypes/maxgraph-pid && npm install && npm run dev`; GitHub Actions records browser screenshots.
- The selected sample status is **proposed validation pending**; data reproduction is not process engineering approval.

## Next bounded milestone

Extract this versioned-library-driven generation engine into a generic, testable Python backend contract; add a second genuinely different approved variant (e.g. parallel duty/standby arrangement) and verify unmatched project cases generate decisions, not guessed equipment. Then evaluate ELK auto-layout with maxGraph and actual company stencil libraries.
