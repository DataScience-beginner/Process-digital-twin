# E2-01 Actual openpidl Compatibility Benchmark — 2026-10-24

**Execution:** [GitHub Actions Run #40075572145](https://github.com/DataScience-beginner/Process-digital-twin/actions/runs/40075572145) — successful job.  
**Artifact:** [openpidl-compatibility-result.zip](https://github.com/DataScience-beginner/Process-digital-twin/actions/runs/40075572145/artifacts/12553316038)  
**Fixture:** `docs/forward-pid/fixtures/{pfd_input.json,expected_graph.json}`.  
**Benchmark source:** `experiments/openpidl/benchmark.py`.  
**Upstream:** https://github.com/openpid-com/openpidl, checked out and installed in ephemeral GitHub Actions runner.

## Observed results

| Check | Real observed result |
|---|---|
| Install actual upstream project via pip -e | PASS |
| Import/use `EngineeringGraph`, `GraphNode`, `GraphEdge` | PASS |
| Convert our E1 fixture into generic engineering graph | PASS |
| Serialize/deserialize via upstream `JsonSerializer` and `JsonDeserializer` | PASS |
| Generic graph: object IDs retained | 11 / 11 |
| Generic graph: edge IDs retained | 19 / 19 |
| Generic graph: exact named-port arrays retained as node `attrs` | 11 / 11 |
| Generic graph: exact source/destination ports retained as edge `attrs` | 19 / 19 |
| Rename display tag while preserving object ID | PASS |
| Build native `PIDLDocument`, parse via `PidlParser` | PASS |
| Native PIDL projection: object IDs retained | 11 / 11 |
| Native PIDL projection: edge IDs retained | 19 / 19 |
| Native PIDL projection: exact object-port arrays preserved | **0 / 11** |
| Native PIDL projection: exact connection endpoint ports preserved | **0 / 19** |
| Automation/agent selection, DEXPI roundtrip, layout and drawing quality | NOT TESTED |

## Interpretation

**Generic graph JSON round-trip:** Lossless for our tested custom metadata *because we explicitly added port and lineage data in opaque `attrs`*. This does **not** prove native openpidl's semantic schema fully understands our physical ports.

**Native PIDLDocument -> PidlParser -> EngineeringGraph:** In the tested public parsing path, the native `LineEndpoint.port` values are not retained as explicit graph-edge port attributes, and custom `InlineItem.properties.ports` are nested as `custom_attributes` instead of recovered into standardized port arrays. Port fidelity checks therefore fail. Equipment nozzle identities and object IDs were maintained in this fixture. We must not claim all port data irrecoverably lost; raw schema fields and alternate conversion paths deserve follow-up.

**Important nuance:** Our test modeled boundary and piping-segment fixture nodes as `InlineItem` objects where the PIDL document lacked a direct matching top-level fixture category. Native PIDL may support more idiomatic representations for some segments. Rebenchmark after exploring official extension points before classifying library incompatible.

## Decision

- Keep openpidl on shortlist, **particularly its EngineeringGraph and JSON adapter capabilities**.
- Do not select native PIDL as our *sole detailed physical graph master* on these results.
- Prefer testing documented semantic extensions and a port-aware adapter over writing a fresh platform from scratch.
- Next: test `LineEndpoint.port`, `InlineItem.properties` and `Nozzle` fidelity with a round-trip adapter; benchmark full PIDL->DEXPI->PIDL with explicit data-quality diff.
- Do not include an openpidl dependency in production services until benchmark and license review are complete.

## Reproducibility

Run the workflow `E2 openpidl Compatibility Experiment` on branch `experiment/openpidl-compatibility-e2`. It fetches upstream openpidl as a separate checkout, installs into GitHub-hosted Python 3.12, runs our benchmark and publishes the JSON artifact. Our production service dependencies are untouched.

This constitutes execution against actual upstream source; does not establish enterprise-grade engineering correctness or capacity.
