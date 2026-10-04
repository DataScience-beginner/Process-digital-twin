# Codex Brief — Digital BDEP Foundation

## Mission
Implement the Digital BDEP platform incrementally. Do not jump directly to a full P&ID generator.

## Immediate milestone: MVP 0.1
From one JSON file:
1. instantiate V-101 (vertical separator)
2. instantiate P-101 (centrifugal pump)
3. validate their ports
4. validate the connection V-101.LIQUID_OUTLET -> P-101.SUCTION
5. serialize/deserialize the plant model
6. provide unit tests for valid and invalid connectivity

## Non-negotiable architecture rules
- The canonical plant model is independent of drawing coordinates.
- Equipment tags are not primary IDs.
- Every connection must use explicit object + port endpoints.
- Undefined objects/ports must fail validation.
- Calculation logic must remain deterministic.
- AI/LLM code must not be added to MVP 0.1.
- Do not couple the plant model directly to Visio, SVG or Engineering Base.
- Keep adapters at the boundary.
- Prefer small typed models and tests over broad abstractions.

## Current repository context
This repository already contains an ASP.NET Core equipment service and cloud infrastructure. The new plant-model service is intentionally isolated initially so the domain model can evolve quickly without disrupting the existing service.

## Planned increments
- 0.1 Core plant model + vessel/pump connectivity
- 0.2 Reusable pump module
- 0.3 Reusable vessel/control module
- 0.4 Simple web/SVG renderer
- 0.5 Orthogonal routing + layout constraints
- 0.6 Deterministic line-sizing service hook
- 0.7 Typed chat commands
- 0.8 Engineering Base adapter
- 0.9 DEXPI import/export
- 1.0 Digital BDEP viewer vertical slice

## Definition of done for 0.1
All tests pass and the example JSON loads into a valid PlantModel. Invalid equipment IDs or port names must raise a validation error with a useful message.
