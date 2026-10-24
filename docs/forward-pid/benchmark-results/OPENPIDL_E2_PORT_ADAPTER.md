# E2-02 — openpidl Port-Aware Adapter Trial

**Date:** 2026-10-24  
**Run:** https://github.com/DataScience-beginner/Process-digital-twin/actions/runs/40075827779  
**Parent epic:** https://github.com/DataScience-beginner/Process-digital-twin/issues/19  
**Fixture:** BENCH-001, 11 semantic objects, 19 directed edges.

## Experiment scope

Check if the E1 physical connectivity graph can be represented and reconstructed through **actual upstream openpidl v1.2 `PIDLDocument` fields and public APIs**, without monkeypatching or forking openpidl.

**Encoder** (`experiments/openpidl/port_adapter.py`) stores:
- immutable IDs as native Equipment/Nozzle/InlineItem/Line IDs, independent of editable display tags;
- named `LineEndpoint.ref` and `LineEndpoint.port` at line endpoints;
- equipment and inline-item typed port arrays and provenance using their existing `properties` dictionaries;
- nozzle detail maps inside parent Equipment.properties, keyed by registered nozzle ID;
- line kind and source simulation-stream reference in declared Pydantic `extra=allow` fields `x_graph_edge_kind` and `x_source_stream_id`.

**Decoder** runs upstream `PidlParser().parse(doc)`, then restores the named-port metadata from the original **serialized PIDL document fields** (not fixture data or a hidden original graph). It rejects missing/mismatched port refs, wrong directions and missing source stream lineage.

**Transport:** real `PIDLDocument.model_dump_json(by_alias=True)` -> `PIDLDocument.model_validate_json(...)` -> native parser + adapter.

## Executed tests

- Native PIDL JSON serialization/deserialization; graph reconstruction: **11/11 node IDs and port arrays**, **19/19 edge IDs and exact source/destination port references**.
- Invalid/missing named port, wrong flow direction, removed stream lineage rejected.
- Equipment display-tag rename does not change permanent object identity.
- GitHub Actions job **completed successfully** on the upstream openpidl checkout.

## Interpretation and decision

**Qualified PASS for this fixture:** A **thin port-aware adapter** can preserve our data on top of upstream openpidl structures. This overturns the prior conclusion that native PIDL-based integration would inherently lose all port detail. The *unmodified default PidlParser output remains incomplete*, so a strict application adapter is still required.

**Architecture:** openpidl is now a serious candidate for P&ID format/graph foundation. Avoid implementing a competing generic graph parser if its present upstream modules satisfy our needs. Keep one chosen authoritative engineering contract and explicit versioned extension scheme.

**Not established:** correctness of native YAML writers, DEXPI round-trip interoperability, branch and recycle connectivity, engineering calculations, automatic template applicability, generated professional drawings, enterprise performance, or long-term compatibility of vendor extension fields. *This is a metadata-fidelity test, not autonomous P&ID generation.*

## Next minimal test

E2.3: run PIDL (with explicit port extensions) -> **DEXPI/Proteus** -> PIDL and compare nozzle/port IDs and physical connections. If the converter drops extension properties, formally label DEXPI as a partial interchange boundary with machine-readable loss report—do not silently claim lossless interoperability.

Until E2.3, do not finalize a standard or merge library dependencies into production code.
