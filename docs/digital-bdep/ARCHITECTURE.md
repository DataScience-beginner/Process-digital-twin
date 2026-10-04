# Digital BDEP Foundation Architecture

## Objective
Build a data-centric Basic Design Engineering Package (BDEP) platform in which engineering objects and relationships are the master, while PFDs, P&IDs, MSDs, datasheets, summaries, calculations and dashboards are views/services built on top of the same plant model.

## Core principles
1. **Plant model is the master** — not PDF, Visio, SVG or a rendered P&ID.
2. **Engineering model and drawing model are separate** — engineering topology must survive layout changes.
3. **Permanent object IDs are immutable** — tags such as P-101 may change; object IDs do not.
4. **Connectivity is port-to-port** — e.g. V-101.LIQUID_OUTLET -> P-101.SUCTION.
5. **Deterministic calculations own numbers** — AI orchestrates but does not invent engineering calculations.
6. **AI proposes typed actions** — deterministic application code validates and applies them.
7. **Templates/modules encode approved engineering patterns** — pump, vessel, exchanger, control loop, PSV, etc.
8. **DEXPI is an interoperability boundary** — internal APIs may use JSON/Pydantic; external exchange can map to DEXPI/other standards.

## Target logical architecture
```text
Configuration Library + Project Inputs
                |
                v
        Canonical Plant Model
                |
    +-----------+-----------+
    |           |           |
    v           v           v
Calculation   Rules      AI/Chat
Services      Engine     Orchestrator
    |           |           |
    +-----------+-----------+
                |
                v
        Updated Plant Model
                |
    +-----------+-----------+-----------+
    |           |           |           |
    v           v           v           v
   PFD         P&ID        MSD      Datasheets/Lists
                |
                v
        Digital BDEP Viewer
                |
                v
        Client / EPC / Vendor
```

## Initial vertical slice
The first implementation proves one complete path only:

- Vertical vessel V-101
- Centrifugal pump P-101
- Port definitions
- Connection V-101.LIQUID_OUTLET -> P-101.SUCTION
- JSON serialization/validation
- Later: simple SVG/web rendering

No AI, no Engineering Base integration, no DEXPI export and no automatic layout are required for MVP 0.1.

## Future layers
### Plant semantics
Equipment, ports, lines, valves, instruments, relief devices, control loops and relationships.

### Engineering properties
Operating/design cases, units, provenance, calculation references and approval status.

### Calculation dependency graph
Tracks what must be recalculated when an upstream property changes.

### Drawing/view model
Stores symbols, sheet, position, orientation, routing and annotation without changing engineering topology.

### Workflow model
Tracks status such as Working, Calculated, Checked, Approved, Stale, Blocked.

## Drafting roadmap
After the plant model is stable:
1. major equipment placement
2. functional clusters
3. orthogonal routing
4. instrument placement
5. labels/notes
6. cross-sheet references
7. congestion scoring/sheet splitting
8. revision clouds from semantic diffs
9. chat-driven design/data/layout commands
