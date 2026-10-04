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

- [x] Define structured Design Basis model
- [x] Define criterion categories:
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
- [x] Every criterion has:
  - immutable ID
  - value + unit
  - revision / status
  - source / provenance
  - applicability scope
  - explicit target object IDs where needed
- [x] Add V-101 relevant criteria
- [x] Add P-101 relevant criteria
- [x] Add FCV-101 relevant criteria
- [x] Add object dossier API returning only criteria relevant to selected object
- [x] Add provenance for every displayed value
- [x] Unit tests: object-specific criteria must not leak to unrelated objects

## MVP 0.6B — Simulation Publisher
Goal: prove that the upstream process topology comes from a simulation-like source, not from the P&ID.

- [x] Define simulation case model
- [x] Support NORMAL / MAXIMUM / TURNDOWN cases
- [x] Publish equipment objects only at simulation/PFD level
- [x] Publish stream objects with source/destination equipment
- [x] Publish P / T / flow / phase / density / viscosity / enthalpy / composition
- [x] Link every simulation case to a Design Basis revision
- [x] Generate canonical PFD graph from equipment + streams
- [x] Tests for V-101 -> stream -> P-101 topology

## MVP 0.6C — PostgreSQL Canonical Process Database
Goal: persist Design Basis, simulation results, plant objects and provenance.

- [x] SQLAlchemy 2.x persistence layer
- [x] PostgreSQL connection via DATABASE_URL
- [x] Alembic migrations
- [x] Core tables:
  - projects
  - design_basis_revisions
  - design_basis_criteria
  - criterion_object_links
  - design_cases
  - simulation_cases
  - equipment
  - streams
  - stream_case_results
  - stream_components
  - engineering_records
  - record_object_links
- [x] Keep flexible supplemental attributes in JSON/JSONB-compatible columns only where appropriate
- [x] Database tests use isolated test DB / SQLite-compatible schema where possible

## MVP 0.6D — Object-Centric Viewer Sidebar
Goal: clicking an engineering object opens its complete Digital BDEP thread without showing the entire project.

For V-101 / P-101 / FCV-101 show tabs:
- [x] Overview
- [x] Design Basis
- [x] Process
- [x] P&ID
- [x] Calculations
- [x] Instrumentation
- [x] Mechanical
- [x] Electrical
- [x] Cost
- [x] EPC / Vendor
- [x] Operations
- [x] History / provenance

Every displayed value must show where it came from. ✅ Implemented for the first V-101 / P-101 / FCV-101 database-backed vertical slice.

## MVP 0.7 — Process Configuration Matcher
- [x] Read canonical PFD topology
- [x] Match EXACT / KNOWN VARIANT / UNKNOWN
- [x] First approved configuration: VESSEL_TO_PUMP_STANDARD_V1
- [x] Match by deterministic topology + applicability rules
- [x] AI may assist semantic matching only; it must not invent engineering topology
- [x] Persist approved configuration definitions/version in canonical database
- [x] Require linked Design Basis facts before declaring EXACT
- [x] Configuration Match viewer shows PFD input, mapping, applicability and permitted modules

## MVP 0.8 — Engineering Topology Compiler
- [x] Expand PFD topology into P&ID semantic topology
- [ ] Add approved modules:
  - [x] vessel level control
  - [x] pressure indication
  - [x] vessel protection
  - [x] vent / drain
  - [x] pump suction arrangement
  - [x] pump discharge arrangement
  - [x] pump minimum-flow recycle
- [x] Generate the current V-101 / P-101 P&ID from configuration data instead of manual demo code
- [x] Validate applicability before compilation
- [x] Preserve PFD stream → P&ID connection provenance
- [x] Block KNOWN_VARIANT / UNKNOWN before P&ID compilation
- [x] Prove semantic equivalence against approved reference graph
- [x] Drive Engineering View and Graph View from compiled topology
- [x] Verify compiled graph passes the connected drafter workflow
- [x] Add compiler trace viewer

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
