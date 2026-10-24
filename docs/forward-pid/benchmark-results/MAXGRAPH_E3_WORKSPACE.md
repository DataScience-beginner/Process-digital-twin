# E3 — maxGraph Interactive Canvas: Executed Vertical Slice

**Date:** 2026-10-24  
**Working branch:** `feature/maxgraph-forward-pid-workspace`  
**PR:** https://github.com/DataScience-beginner/Process-digital-twin/pull/23  
**Successful browser validation:** https://github.com/DataScience-beginner/Process-digital-twin/actions/runs/40077662137  
**Screenshot artifact:** https://github.com/DataScience-beginner/Process-digital-twin/actions/runs/40077662137/artifacts/12554095516

## Implemented / verified

- Actual third-party `@maxgraph/core` browser Graph instance (not custom SVG-only presentation).
- BFD functional blocks (3), PFD simulation stream-level view, and P&ID detailed physical connectivity view generated from project fixture; source BFD is a *derived illustrative functional abstraction*, not real user-supplied BFD translation.
- Native maxGraph vertices/edges, engineering object selection, properties and stream lineage panel, zoom and graph JSON export.
- `Insert discharge valve` operates on semantic fixture graph first: adds XV-102, replaces old physical connection to downstream boundary with two physical edges and one internal flow transition, validates named port direction, then renders new maxGraph view.
- `npm test`: engineering model graph/port tests passed.
- `npm run build`: Vite production bundle compiled.
- `npm run test:browser`: Playwright Chromium verified visible actual SVG canvas, BFD/PFD/P&ID transitions, valve insertion counts (11/19 -> 12/21), selected item properties and export-backed source graph.
- Two browser screenshots captured in GitHub Actions artifacts, before and after valve insertion.

## Design boundary

`src/engineering.js` is the contract fixture / graph command layer. `src/main.js` renders this through a real maxGraph canvas. No drawing geometry is stored in our authoritative E1 graph. The geometry in the UI is illustrative and still manually supplied initial placement; maxGraph handles edge drawing/routing.

## Remaining limitations / blockers before demo deployment

- This project is currently a **source branch and GitHub CI artifact**, not a public running deployment. To view interactive GUI locally: `cd prototypes/maxgraph-pid && npm install && npm run dev`.
- No live Python backend, persistent database, ELK automatic layout, company symbol registry, approved safety and process rules, engineering simulator binding, or zero-prompt configuration selection yet.
- Editing by free drag in the canvas is not yet translated back into semantic engineering commands. Graph command button is a controlled first step.
- **Not a production P&ID:** default maxGraph shapes for early evaluation; no validation of ISA/ISO company stencil conformance.
- The previous initial browser test failed from an invalid `graph.fit()` method. Fixed by using upstream supported `graph.zoomTo()`; successful Playwright test confirms no silent blank workspace.

## Next minimal milestone

Use Python-side approved configuration selection to turn fixture PFD into a detailed engineering graph through real engineering rules/configuration data (no fixed graph loaded as sole source), expose it to the maxGraph workspace, and compare rendered output against E1 expected data. Then add automatic layout and drawing symbol standards.

**Do not call this completed autonomous BFD->PFD->P&ID translation.** It is a successfully tested real canvas and graph-backed editing vertical slice.
