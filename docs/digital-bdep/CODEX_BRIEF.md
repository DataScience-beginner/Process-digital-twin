# Codex Brief — Digital BDEP Foundation

## Technology decision
The Digital BDEP platform is **Python-only**. Do not add new C#/.NET components for this workstream. Existing legacy/demo C# code in the repository may remain untouched until a later migration decision.

Preferred stack for the current phase:
- Python 3.11+
- Pydantic v2 for canonical engineering contracts
- FastAPI for APIs/web endpoints
- pytest for tests
- JSON for internal service contracts
- SVG/HTML for the early viewer

## Mission
Implement the Digital BDEP platform incrementally. Do not jump directly to a full P&ID generator.

## Immediate milestone: MVP 0.1
From Python:
1. instantiate V-101 (vertical separator)
2. instantiate P-101 (centrifugal pump)
3. validate their ports
4. validate V-101.LIQUID_OUTLET -> P-101.SUCTION
5. expose the canonical plant model as JSON
6. render a small browser viewer without putting drawing coordinates into the canonical plant model

## Non-negotiable architecture rules
- The canonical plant model is independent of drawing coordinates.
- Equipment tags are not primary IDs.
- Every connection uses explicit object + port endpoints.
- Undefined objects/ports fail validation.
- Deterministic engineering calculations remain typed/testable Python services.
- AI/LLM code is not part of the deterministic calculation layer.
- Do not couple the plant model directly to Visio, SVG or Engineering Base.
- Keep adapters/renderers at the boundary.
- Every new engineering rule requires a unit test.

## Planned increments
- 0.1 Core plant model + vessel/pump connectivity + basic viewer
- 0.2 Reusable pump installation module
- 0.3 Reusable vessel/control module
- 0.4 Data-driven SVG renderer
- 0.5 Orthogonal routing + layout constraints
- 0.6 Deterministic calculation-service hooks
- 0.7 Typed chat commands
- 0.8 Engineering Base adapter
- 0.9 DEXPI import/export
- 1.0 Digital BDEP viewer vertical slice
