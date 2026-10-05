# MVP 0.1 Specification

## Use case
Represent a small process configuration digitally before attempting any drawing automation.

### Equipment
**V-101 — Vertical Separator**
- FEED_INLET (process/in)
- VAPOR_OUTLET (process/out)
- LIQUID_OUTLET (process/out)
- VENT (vent/out)
- DRAIN (drain/out)
- PSV_NOZZLE (process/out)

**P-101 — Centrifugal Pump**
- SUCTION (process/in)
- DISCHARGE (process/out)
- DRAIN (drain/out)

### Required connection
V-101.LIQUID_OUTLET -> P-101.SUCTION

## Acceptance criteria
- Duplicate equipment IDs rejected.
- Duplicate equipment tags rejected.
- Duplicate port names inside one equipment item rejected.
- Connection to unknown equipment rejected.
- Connection to unknown port rejected.
- Valid model round-trips to/from JSON.
- No drawing/location fields are required in the canonical model.

## Explicitly out of scope
- Process calculations
- Instrumentation
- Line numbering
- P&ID drafting
- PFD drafting
- automatic layout
- AI/LLM
- Engineering Base
- database persistence
- DEXPI
