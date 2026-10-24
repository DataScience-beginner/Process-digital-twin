# Benchmark 01 — One PFD Section, Forward-to-P&ID Fixture

**Status:** Fixture contract v0.1, intended as the first *executable* acceptance benchmark after selection/installation of candidate libraries. Illustrative data only; NOT issued engineering.

## Trigger and user contract

When a sample PFD module is marked `approved`, the autonomous workflow must expand its semantic flow from V-101 through P-101 to the downstream boundary by choosing an approved applicable configuration, without chat prompts or manual selection. If no valid approved template matches, report `requires_decision` rather than guessing. For this benchmark, assume a **fixture standard** `TRANSFER_PUMP_SUCTION_V1` is explicitly approved and applicable only to the defined fixture. No assumption that this is a generally valid real-world pump arrangement.

## Structured PFD input

```yaml
project_id: BENCH-001
section_id: FEED_TRANSFER
publication:
  source: synthetic_pfd
  id: PFD-BENCH-001
  revision: "A"
  approval_status: approved
  design_case: NORMAL
objects:
  - {id: eq-vessel-1, type: vertical_separator, tag: V-101}
  - {id: eq-pump-1, type: centrifugal_pump, tag: P-101}
interfaces:
  - {id: inlet-boundary-1, name: upstream_feed, direction: in}
  - {id: outlet-boundary-1, name: downstream_header, direction: out}
streams:
  - {id: str-101, from: eq-vessel-1, to: eq-pump-1, service: liquid}
  - {id: str-102, from: eq-pump-1, to: outlet-boundary-1, service: liquid}
requirements:
  pump_arrangement: single_pump
  suction_isolation: required_by_fixture_standard
  simulation_data_status: not_supplied
```

The scenario deliberately has no pressure/temperature/flow/density/size/schedule/specification; do not fabricate any. It tests topology and data lineage only.

## Expected expansion / fixtures

Graph objects with stable IDs unrelated to tags:
- `eq-vessel-1` with liquid outlet nozzle `nz-v-1`
- suction pipe `pipe-suc-1`, isolation valve `valve-suc-1`, suction pipe `pipe-suc-2`
- `eq-pump-1` with suction nozzle `nz-p-s` and discharge nozzle `nz-p-d`
- downstream pipe `pipe-dis-1` and boundary `outlet-boundary-1`
- explicit upstream feed boundary `inlet-boundary-1`

Expected liquid path (port-level edges must additionally exist, and all elements must support appropriate directions):

```
inlet-boundary-1 -> eq-vessel-1
eq-vessel-1 -> nz-v-1 -> pipe-suc-1 -> valve-suc-1
 -> pipe-suc-2 -> nz-p-s -> eq-pump-1 -> nz-p-d
 -> pipe-dis-1 -> outlet-boundary-1
```

Each transformation from equipment body to nozzle must be *explicitly modeled/typed* (not arbitrary association traversal). Simulation stream IDs `str-101` and `str-102` link to relevant semantic flow with provenance; generated line IDs are unassigned until engineering basis provides a valid line-number rule.

## Required outputs

- Expanded semantic graph with ports and directed edges.
- Configuration version and applicability proof (`TRANSFER_PUMP_SUCTION_V1`), source revision, trace to PFD object/stream, unresolved engineering attributes.
- Derived functional upstream/downstream trace and full physical trace.
- Validation report: graph integrity, source provenance, ports, identity, structure, unresolved required data.
- Drawing view using registered symbols and source IDs once a drawing backend is selected. Drawing coordinates shall not be stored in semantic objects.

## Negative tests

1. Remove `pipe-suc-2 -> nz-p-s` edge: must fail completeness check.
2. Reverse pump suction flow through inlet-only port: must fail direction check.
3. Connect to nonexistent nozzle port: must fail port reference validation.
4. Rename `P-101` to `P-900`: stable ID and topology must remain unchanged.
5. Reuse object ID for valve and pipe: must fail uniqueness check.
6. Remove standard approval: must produce exception, no silent assembly.
7. Supply false line-spec/pressure value: must fail provenance validation.
8. Format round-trip through candidate library: compare stable IDs, individual physical ports and connection graph, not just high-level equipment trace.

## Definition of done for E1

Engineering criteria and fixtures are reviewed, synthetic source and expected graph are machine-readable, failing-case tests exist, and each candidate implementation can be evaluated using the same fixture. No suggestion that an unexecuted fixture demonstrates working automation.
