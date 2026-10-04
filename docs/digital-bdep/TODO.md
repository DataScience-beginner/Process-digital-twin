# Digital BDEP — Implementation TODO

## Current completed foundation
- [x] Python-only plant model
- [x] Pump + separator semantic graph
- [x] Explicit nozzle nodes and digital-thread relationships
- [x] Separate Engineering View and Graph View
- [x] Drafter workflow: process skeleton
- [x] PSV / vent / drain
- [x] Instrumentation and control loops
- [x] Cleanup / annotation layer
- [x] Initial drawing-quality checks

## MVP 0.6A — Design Basis + Object-Centric Digital Thread
Goal: make Design Basis criteria structured, queryable and directly connected to the engineering objects they govern.

- [ ] Define structured Design Basis model
- [ ] Define criterion categories:
  - feed / battery-limit conditions
  - operating and design cases
  - flow / sizing margins
  - vessel criteria
  - pump criteria
  - control-valve criteria
  - PSV / relief criteria
  - line-sizing criteria
  - materials criteria
  - utilities / ambient criteria
  - applicable standards / company practices
- [ ] Every criterion has:
  - immutable ID
  - value + unit
  - revision / status
  - source / provenance
  - applicability scope
  - explicit target object IDs where needed
- [ ] Add V-101 relevant criteria
- [ ] Add P-101 relevant criteria
- [ ] Add FCV-101 relevant criteria
- [ ] Add object dossier API returning only criteria relevant to selected object
- [ ] Add provenance for every displayed value
- [ ] Unit tests: object-specific criteria must not leak to unrelated objects

## MVP 0.6B — Simulation Publisher
Goal: prove that the upstream process topology comes from a simulation-like source, not from the P&ID.

- [ ] Define simulation case model
- [ ] Support NORMAL / MAXIMUM / TURNDOWN cases
- [ ] Publish equipment objects only at simulation/PFD level
- [ ] Publish stream objects with source/destination equipment
- [ ] Publish P / T / flow / phase / density / viscosity / enthalpy / composition
- [ ] Link every simulation case to a Design Basis revision
- [ ] Generate canonical PFD graph from equipment + streams
- [ ] Tests for V-101 -> stream -> P-101 topology

## MVP 0.6C — PostgreSQL Canonical Process Database
Goal: persist Design Basis, simulation results, plant objects and provenance.

- [ ] SQLAlchemy 2.x persistence layer
- [ ] PostgreSQL connection via DATABASE_URL
- [ ] Alembic migrations
- [ ] Core tables:
  - projects
  - design_basis_revisions
  - design_basis_criteria
  - criterion_object_links
  - design_cases
  - simulation_cases
  - equipment
  - streams
  - stream_components
  - engineering_records
  - record_object_links
- [ ] Keep flexible supplemental attributes in JSONB only where appropriate
- [ ] Database tests use isolated test DB / SQLite-compatible schema where possible

## MVP 0.6D — Object-Centric Viewer Sidebar
Goal: clicking an engineering object opens its complete Digital BDEP thread without showing the entire project.

For V-101 / P-101 / FCV-101 show tabs:
- [ ] Overview
- [ ] Design Basis
- [ ] Process
- [ ] P&ID
- [ ] Calculations
- [ ] Instrumentation
- [ ] Mechanical
- [ ] Electrical
- [ ] Cost
- [ ] EPC / Vendor
- [ ] Operations
- [ ] History / provenance

Every displayed value must show where it came from.

## MVP 0.7 — Process Configuration Matcher
- [ ] Read canonical PFD topology
- [ ] Match EXACT / KNOWN VARIANT / UNKNOWN
- [ ] First approved configuration: VESSEL_TO_PUMP_STANDARD_V1
- [ ] Match by deterministic topology + applicability rules
- [ ] AI may assist semantic matching only; it must not invent engineering topology

## MVP 0.8 — Engineering Topology Compiler
- [ ] Expand PFD topology into P&ID semantic topology
- [ ] Add approved modules:
  - vessel level control
  - pressure indication
  - vessel protection
  - vent / drain
  - pump suction arrangement
  - pump discharge arrangement
  - pump minimum-flow recycle
- [ ] Generate the current V-101 / P-101 P&ID from configuration data instead of manual demo code
- [ ] Validate applicability before compilation

## MVP 0.9 — Change / Impact Intelligence
- [ ] Criterion change -> affected objects
- [ ] Simulation result change -> affected calculations / equipment
- [ ] Affected / Update Required states
- [ ] Engineering View highlighting
- [ ] Semantic revision diff
- [ ] Revision-cloud generation from changed semantic objects

## MVP 1.0 — Calculation and Discipline Thread
- [ ] Deterministic process calculations
- [ ] Instrument sizing
- [ ] Mechanical / electrical interfaces
- [ ] Cost records
- [ ] EPC / vendor data
- [ ] Operations / historian mappings
- [ ] approval / revision / audit trail

## Non-negotiable rules
1. Design Basis is structured engineering data, not only a PDF.
2. Simulation owns PFD-level equipment, streams and conditions; it does not invent P&ID instrumentation.
3. Approved engineering configurations own how PFD topology expands into P&ID topology.
4. Every displayed value has provenance.
5. Engineering View remains conventional; Graph View exposes the digital thread.
6. No AI-generated safety-critical calculations.
7. Unknown configurations stop for engineering review instead of being invented.
