# E4.3 — Automatic P&ID Layout (ELK + maxGraph)

**Date:** 2026-10-24  
**Status:** experimental engineering-graph-driven layout, CI gates required before acceptance.  
**PR:** https://github.com/DataScience-beginner/Process-digital-twin/pull/23

## Architecture implemented

- `src/layout.js` converts the currently visible BFD/PFD/P&ID graph to the **ELK layered graph layout engine**.
- ELK computes node coordinates, total diagram bounds and orthogonal edge routes. Internal equipment transitions are excluded from *drawn* piping edges, while still retained in the semantic graph and its validation.
- `src/main.js` now awaits ELK layout before inserting nodes and edges into the real maxGraph canvas. A render sequence token prevents an older async layout result from overwriting a new scenario or stage selection.
- The old per-tag `positions` lookup table was deleted from canvas code. Symbol footprint dimensions are based on equipment type, not object IDs.
- `fitCanvas` derives zoom from computed diagram bounds and viewport size.
- All edits still modify and validate the authoritative semantic graph, then re-render; ELK does NOT change graph IDs, ports or upstream/downstream connectivity.

## Verification

- Node tests in `test/layout.test.js` check generated placement for both single and parallel pump configurations, distinct positioning of pumps, and graph-based functional block placement.
- Browser test `test/browser.spec.js` checks maxGraph rendering, graph-backed discharge valve insertion, and multi-pump scenario switching, including screenshots.
- See branch workflow: https://github.com/DataScience-beginner/Process-digital-twin/actions?query=branch%3Afeature%2Fmaxgraph-forward-pid-workspace

## Limitations

- ELK performs **topological layout**, not engineering P&ID drafting according to company standards, piping symbol orientation, page breaks, notes, legend, signal-line layering or collision-free off-page connectors. Any claim that this is a production-grade automatic P&ID would be premature.
- maxGraph currently receives node positions from ELK; its built-in orthogonal edge style routes the lines. ELK route sections are computed and available for future explicit edge-bend mapping, but not yet applied to every maxGraph edge.
- No editable professionally approved stencil library yet; symbols are standard maxGraph placeholder shapes.
- The browser demo remains branch code/CI artifacts, **not deployed publicly**.
- Domain rules and configuration engineering review remain mandatory before commercial use.

## Next small milestones

1. Consume ELK edge bend points in maxGraph geometry and verify routing/nozzle alignment.
2. Register standards-compliant equipment and ISA valve/instrument stencils; validate equipment ports with fixed anchors.
3. Add multi-sheet logic, off-page connectors, annotation zones, PDF/DXF export and revision management.
