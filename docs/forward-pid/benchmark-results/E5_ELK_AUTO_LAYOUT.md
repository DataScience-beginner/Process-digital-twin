# E5 — ELK auto-layout on real maxGraph P&ID canvas

Date: 2026-10-24
Source PR: https://github.com/DataScience-beginner/Process-digital-twin/pull/23

## Implementation

- Dependency: `elkjs` alongside actual `@maxgraph/core`; this is **not a custom diagramming engine**.
- `src/layout.js`: constructs an ELK layered/RIGHT/ORTHOGONAL view projection from detailed graph nodes and **physical_connection** edges (excludes all internal equipment transitions). It computes widths, heights, x/y and routed edge sections; authoritative engineering graph is untouched.
- `src/main.js`: asynchronous layout, stale response token guard, maxGraph vertex positions, orthogonal graph edges and zoom-to-fit derived from layout dimensions. The previous fixture-specific coordinate table has been deleted.
- `test/layout.test.js`: unique positions for 11 objects, 22-node parallel case, positive dimensions and separate pump placements, BFD placement checks.
- `test/browser.spec.js`: real Chromium layout and engineering edit interactions, screenshots before and after valve insertion, and duty/standby. Extended to assert the browser's actual ELK positions and no overlap of the two pump nodes.

## Scope and limitations

The current result automatically positions **schematic engineering graph elements**. ELK layout is not yet a company-standard issued P&ID: it does not certify ISA/ISO symbol consistency, pipe routing and collision-free annotations, line label space, nozzle orientation, traceable revision clouds, drawing sheet pagination, line crosses and jumps, electrical or instrument loop notation, or drawing checker approval. The symbols are illustrative maxGraph primitives.

The 11- and 22-object synthetic fixtures are not full refinery sections. Engineering data is sourced from approved **fixture templates**, not a real simulator or engineering-basis database. Layout does not itself design valve or instrument arrangement. All outputs remain 'proposed_validation_pending'.

## Acceptance evidence

CI:
- Baseline passing ELK browser run: https://github.com/DataScience-beginner/Process-digital-twin/actions/runs/40081217409
- New browser assertion run: see latest GitHub Actions on the feature branch.

## Next engineering milestone

Host this real browser-built workspace as an authenticated preview for the user, then add supported industrial P&ID stencils and nozzle/port-aware connectors. Connect a real process simulator's PFD stream attributes to the graph generator. Keep semantic graph as master and reject any drawing modifications that cannot be mapped back to engineering commands.
