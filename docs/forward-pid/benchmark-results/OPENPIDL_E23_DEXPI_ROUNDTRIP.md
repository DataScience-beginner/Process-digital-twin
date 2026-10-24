# E2.3 — Actual PIDL → Proteus/DEXPI XML → PIDL benchmark (2026-10-24)

**Source:** https://github.com/DataScience-beginner/Process-digital-twin/actions/runs/40075999048  
**Experiment code:** `experiments/openpidl/dexpi_roundtrip.py`  
**Fixture:** `BENCH-001` (11 semantic nodes, 19 port-level directed graph transitions); synthetic only.

## Execution

GitHub Actions installed actual upstream openpidl and ran:
1. Fixture → port-aware native `PIDLDocument` (serialize to JSON and parse again).
2. `PidlParser` plus our strict port metadata recovery.
3. `ProteusWriter().write(graph, xml_path)` to XML.
4. `ProteusReader().read(xml_path)`.
5. `PidlCompiler().compile(read_graph)`, native PIDL JSON transport, `PidlParser` back to a graph.
6. Compare identities, physical ports, directed edges and lineage with expected fixture.

The workflow **completed successfully as an audit**, but the engineering-fidelity assessment **failed**.

## Results

| Stage | Observed |
|---|---|
| Port-aware input PIDL/engineering graph | 2 equipment + 6 inline items + 3 nozzles = 11 nodes, 19 connections; **full port metadata passes** |
| Writer XML | `PlantModel`, 2 Equipment, 3 Nozzle, 19 PipingNetworkSegment, 1 PipingComponent, 19 Connection |
| Reader graph | 5 objects (2 equipment + 3 nozzles), 19 edges with rewritten graph IDs such as `line:edge-01`; no valve/piping/boundary nodes retained as semantic objects |
| Compiler output PIDL | 2 equipment, 3 nozzles, **0 inline items, 0 valves, 1 line** |
| Full exact port-level comparison | **FAIL**; 11-node/19-edge detailed engineering graph was not recoverable |

### Noteworthy defects and interpretation

- The writer models *all* our graph edges as piping segments, including `internal_transition` edges inside equipment. This is semantically incorrect: internal process traversal is not a physically drawn piping segment.
- The native writer serializes only supported node kinds and attributes. Our custom boundary and piping segment nodes are not faithfully represented; read-back therefore excludes their identity.
- Reader graph object IDs acquire `equipment:`, `nozzle:`, etc. prefixes, while original DEXPI IDs remain in attributes; a mapping could restore some identity, but not missing object/port semantics.
- Compiler coalesces multiple segments into one line and drops unidentified/no-layout inline nodes in this test. This is a potentially useful high-level projection, but **not** an authoritative detailed P&ID round-trip.
- The XML being parseable by the library does not independently certify DEXPI schema conformance or third-party CAD interoperability.

## Decision

**RED for lossless engineering exchange through this native path.**  
**GREEN for the previous E2.2 native PIDL document + port-aware adapter roundtrip.**

Retain the openpidl candidate for structured P&ID modeling, parsing and *possibly partial* DEXPI exchange. Do not use its current XML converter to write back to the authoritative detailed engineering graph. The correct next step is **one small intervention**: characterize a DEXPI export adapter that emits *physical piping edges only*, retains stable IDs via explicit mapping, preserves valve and boundary details where the standard supports them, and produces a loss report for anything the exporter cannot encode. Do not implement a fresh DEXPI format or silently claim the adapter fixes all issues.

## Future acceptance criteria

- Distinguish detailed physical graph from a simplified functional graph.
- Preserve all 11 object IDs and port definitions; physical connection edges and internal transitions must remain typed distinctly.
- No known valve, pipe segment, nozzle, source stream, approved configuration ID or revision may silently disappear.
- Record any semantically unsupported property as **documented loss** and block publish when critical.
- Validate generated XML with independent DEXPI schema/interoperability checks, not just same-library re-import.

**Important caveat:** This benchmark intentionally feeds the whole graph, including internal transitions, into an interchange pipeline originally designed for P&ID piping segments. It proves this naïve native route unsuitable; not that standards-compliant DEXPI export of a suitably transformed model is impossible.
