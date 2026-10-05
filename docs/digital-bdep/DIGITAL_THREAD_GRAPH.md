# Digital Thread Graph + Drawing Representation

## Principle

The Digital BDEP shall maintain **two linked structures**:

1. **Semantic engineering graph** — the digital thread.
2. **Drawing representation graph** — the drafter-quality P&ID view.

They are linked by immutable object IDs but are not the same model.

## Why

The engineering graph must survive:
- drawing rearrangement
- sheet splitting
- tag changes
- PFD/P&ID/MSD view changes
- Visio/Web renderer changes
- DEXPI exchange

The drawing is a representation of the plant; it is not the plant database.

## Semantic graph

Typical node classes:
- Equipment
- ProcessNozzle
- InstrumentNozzle
- AccessNozzle
- Line / PipingNetworkSegment
- Valve
- Instrument
- ControlLoop / ProcessInstrumentationFunction
- Boundary / OffPageConnector
- Calculation
- Datasheet
- Requirement
- Revision / Approval

Typical edge classes:
- CONNECTS_TO
- HAS_NOZZLE
- MEASURES
- CONTROLS
- PROTECTS
- FEEDS
- RETURNS_TO
- CALCULATED_BY
- REPRESENTED_ON
- DERIVED_FROM
- AFFECTS
- APPROVED_BY

Example:

```text
V-101
  ├─HAS_NOZZLE→ N-V101-LIQ
  ├─HAS_NOZZLE→ N-V101-PSV
  └─HAS_NOZZLE→ N-V101-REC

N-V101-LIQ
  └─CONNECTS_TO→ L-V101-LIQ
       └─CONNECTS_TO→ LCV-101
            └─CONNECTS_TO→ P-101.SUCTION

LT-101
  └─MEASURES→ V-101.LEVEL

LIC-101
  ├─RECEIVES_FROM→ LT-101
  └─CONTROLS→ LCV-101

PSV-101
  └─PROTECTS→ V-101
```

## Drawing representation graph

Each semantic object may have zero or more representations.

```json
{
  "representation_id": "REP-PID101-V101",
  "semantic_object_id": "EQ-V101",
  "drawing_id": "PID-101",
  "symbol_master": "VESSEL_VERTICAL",
  "position": {"x": 210, "y": 300},
  "rotation": 0
}
```

A nozzle representation similarly links to its semantic nozzle object and defines the exact graphical anchor/connection point.

## DEXPI alignment

DEXPI's conceptual model and graphics model follow the same separation:
- conceptual objects represent engineering meaning;
- representation groups map graphics to conceptual objects;
- composition of graphical groups can mirror composition of conceptual objects;
- a conceptual model can exist without a diagram.

DEXPI 2.0.1 further distinguishes nozzle classes such as ProcessNozzle, InstrumentNozzle and AccessNozzle in its reference P&ID.

## Architecture rule

Never infer the digital thread from line geometry when semantic connectivity already exists.

Instead:

```text
Semantic graph
     ↓
Drafter workflow / layout decisions
     ↓
Drawing representation graph
     ↓
SVG / Visio / PDF
```

For imports from legacy drawings, geometry may be used to reconstruct semantic relationships, but once confirmed the semantic graph becomes authoritative.

## Next implementation change

MVP 0.4 shall introduce:
- explicit Nozzle objects;
- semantic graph adjacency API;
- DrawingView and Representation objects;
- semantic_object_id linkage for every shape;
- edge-to-route linkage for every rendered line;
- graph validation independent of drawing validation;
- object impact traversal for future change propagation.
