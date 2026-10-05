# Instructions for coding agents

Scope: `services/plant-model-service/**`

- Preserve separation between canonical engineering semantics and drawing/layout data.
- Do not add LLM dependencies unless a later task explicitly requests them.
- Do not add coordinates to core Equipment or Connection models.
- Connections must always resolve by immutable object ID and named port.
- Prefer Pydantic v2 validation and explicit enums.
- Every new domain rule requires a unit test.
- Keep the MVP intentionally small; avoid speculative abstractions.
- Deterministic engineering calculations, when added, must be pure/testable functions or services with typed inputs/outputs.
- Do not make tags primary keys.
