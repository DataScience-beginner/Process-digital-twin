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

## MVP 0.9 — Staged Discipline Publishing
Goal: complete the multidisciplinary engineering publish backbone before change management.

- [x] Persistent publication stages and dependencies
- [x] Publish Design Basis
- [x] Publish Simulation
- [x] Select / publish approved Configuration
- [x] Publish Process / Safety data
  - [x] vessel preliminary holdup sizing
  - [x] pump rated duty
  - [x] PSV structured relief basis
  - [x] final PSV orifice sizing explicitly reserved for a qualified relief service
- [x] Publish Instrumentation / DCS
  - [x] FCV preliminary deterministic Cv sizing
  - [x] FT range basis
  - [x] FIC minimum-flow DCS loop details
  - [x] LIC vessel-level DCS loop details
- [x] Publish Mechanical
  - [x] V-101 preliminary mechanical datasheet basis
  - [x] P-101 preliminary package datasheet basis
- [x] Publish Costing
  - [x] object-level demo parametric estimates
  - [x] section total
  - [x] explicit provenance and non-commercial demo status
- [x] Publish All executes the controlled stage order
- [x] Engineering View retains the connected P&ID while showing the publishing toolbar
- [x] PSV, LCV, FT, FIC, LT, LIC and PT are selectable in the object inspector
- [x] Published values remain object-specific and provenance-linked

## MVP 0.9A — Detailed Object / Datasheet Views
Goal: every selected engineering item can open a detailed calculation/datasheet view in addition to the compact sidebar.

- [ ] Add "Open Detail / Pop-out" action for selected P&ID objects
- [ ] Detailed object header: tag, type, service, revision, maturity/status
- [ ] Show Design Basis criteria linked to the selected object
- [ ] Calculation detail sections:
  - [ ] inputs
  - [ ] criteria / limits
  - [ ] calculation method / service
  - [ ] Normal / Maximum / Turndown case results
  - [ ] governing case and why
  - [ ] outputs
  - [ ] provenance / revision
- [ ] Full-page object datasheet route for pop-out
- [ ] In-page modal/dialog for quick review

## MVP 0.9B — PSV Scenario / Relief Detail
- [ ] Structured relief-scenario register for PSV-101
- [ ] Show why each scenario is considered
- [ ] Show required inputs and current data completeness
- [ ] Show screening result for each scenario
- [ ] Show preliminary selected scenario and selection rationale
- [ ] Do not claim a final governing case until the qualified relief service runs
- [ ] Final orifice sizing remains a gated qualified deterministic service

## MVP 0.9C — Stream Numbering, Line Numbering and Line Sizing
- [ ] Add four-digit process stream numbers
- [ ] Preserve simulator stream ID separately from engineering stream number
- [ ] Add project fluid code and piping class criteria
- [ ] Define line-number format: size - fluid code - stream/sequence - piping class
- [ ] Deterministic liquid line-sizing service
- [ ] Size V-101 → P-101 suction line
- [ ] Size P-101 discharge line
- [ ] Size minimum-flow recycle line
- [ ] Show Normal / Maximum / Turndown velocities for selected sizes
- [ ] Publish line-sizing records with criteria and provenance
- [ ] Show stream numbers and line numbers on Engineering View
- [ ] Add line summary to relevant equipment detailed views

## MVP 0.9D — Project / Equipment Dashboard
- [ ] Publication-stage completion summary
- [ ] Equipment / valve / instrument status matrix
- [ ] Discipline completion per object
- [ ] Cost per major equipment / valve
- [ ] Total section/project demo estimate
- [ ] Outstanding / TBD / gated items
- [ ] Links from dashboard to Engineering View and object detail pages

## MVP 1.0 — Vendor / EPC Information Thread
- [ ] Vendor enquiry package inputs
- [ ] Vendor document register
- [ ] Vendor datasheet / offer comparison
- [ ] Vendor deviations and TQs
- [ ] Selected vendor data writeback
- [ ] EPC comments / actions / approvals
- [ ] Procurement / fabrication status
- [ ] Preserve licensor vs vendor ownership of each value

## MVP 1.1 — Change / Impact Intelligence
- [ ] Criterion change -> affected objects
- [ ] Simulation result change -> affected calculations / equipment
- [ ] Affected / Update Required states
- [ ] Engineering View highlighting
- [ ] Semantic revision diff
- [ ] Revision-cloud generation from changed semantic objects

## Later lifecycle thread
- [ ] Operations / historian mappings
- [ ] approval / revision / audit trail hardening

## Non-negotiable rules
1. Design Basis is structured engineering data, not only a PDF.
2. Simulation owns PFD-level equipment, streams and conditions; it does not invent P&ID instrumentation.
3. Approved engineering configurations own how PFD topology expands into P&ID topology.
4. Every displayed value has provenance.
5. Engineering View remains conventional; Graph View exposes the digital thread.
6. No AI-generated safety-critical calculations.
7. Unknown configurations stop for engineering review instead of being invented.
