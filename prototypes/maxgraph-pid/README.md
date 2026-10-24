# maxGraph forward-P&ID canvas — E3 vertical slice

This is **real maxGraph**, not the earlier custom SVG/HTML picture. Data comes from `docs/forward-pid/fixtures/expected_graph.json`; stage selection derives BFD/PFD/P&ID views. `src/engineering.js` owns semantic data and typed physical versus internal transitions; `src/main.js` only maps to maxGraph vertices and edges.

## Run

```sh
cd prototypes/maxgraph-pid
npm install
npm run dev
# open URL shown by Vite
npm test
npm run build
npm run test:browser # requires installed Playwright Chromium browser
```

Select BFD, PFD and P&ID. In P&ID select a symbol to inspect properties. Click **Insert discharge valve**; the source graph replaces `edge-19` with new valve `valve-dis-1` and three new edges (two physical, one internal), then redraws via maxGraph. Export semantic graph as JSON. The static initial geometry positions are illustrative; automatic ELK layout, regulated symbol stencils, Python API persistence, drag/drop transactions and agent generation are **not integrated**.

This is a self-contained benchmark workspace intended for verifying maxGraph suitability; no change to deployed production application or committed library selection.
