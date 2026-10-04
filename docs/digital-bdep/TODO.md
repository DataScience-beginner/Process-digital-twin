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

- [x] Add "Open Detail / Pop-out" action for selected P&ID objects
- [x] Detailed object header: tag, type, service, revision, maturity/status
- [x] Show Design Basis criteria linked to the selected object
- [x] Calculation detail sections:
  - [x] inputs
  - [x] criteria / limits
  - [x] calculation method / service
  - [x] Normal / Maximum / Turndown case results
  - [x] governing case and why
  - [x] outputs
  - [x] provenance / revision
- [x] Full-page object datasheet route for pop-out
- [x] In-page modal/dialog for quick review

## MVP 0.9B — PSV Scenario / Relief Detail
- [x] Structured relief-scenario register for PSV-101
- [x] Show why each scenario is considered
- [x] Show required inputs and current data completeness
- [x] Show screening result for each scenario
- [x] Show preliminary selected scenario and selection rationale
- [x] Do not claim a final governing case until the qualified relief service runs
- [x] Final orifice sizing remains a gated qualified deterministic service

## MVP 0.9C — Stream Numbering, Line Numbering and Line Sizing
- [x] Add four-digit process stream numbers
- [x] Preserve simulator stream ID separately from engineering stream number
- [x] Add project fluid code and piping class criteria
- [x] Define line-number format: size - fluid code - stream/sequence - piping class
- [x] Deterministic liquid line-sizing service
- [x] Size V-101 → P-101 suction line
- [x] Size P-101 discharge line
- [x] Size minimum-flow recycle line
- [x] Show Normal / Maximum / Turndown velocities for selected sizes
- [x] Publish line-sizing records with criteria and provenance
- [x] Show stream numbers and line numbers on Engineering View
- [x] Add line summary to relevant equipment detailed views

## MVP 0.9D — Project / Equipment Dashboard
- [x] Publication-stage completion summary
- [x] Primary-equipment status matrix with valves/instruments rolled up as child discipline objects
- [x] Discipline completion per object
- [x] Cost per major equipment / valve
- [x] Total section/project demo estimate
- [x] Outstanding / TBD / gated items
- [x] Links from dashboard to Engineering View and object detail pages

## MVP 0.9E — Relationship-Aware Entity Inspector
- [x] Every visible P&ID object is selectable: equipment, PSV, CV, manual valves, NRV, instruments, junctions and boundaries
- [x] Visible process / utility / instrument / signal routes are selectable entities
- [x] Equipment selection shows only actually connected nodes and lines
- [x] Line selection reverses context to FROM / THROUGH / TO
- [x] Line path shows connected equipment, nozzles, valves, instruments and boundaries
- [x] Child objects retain semantic identity but dashboard reporting rolls them into primary equipment
- [x] Line-sizing calculations are opened from the selected line instead of being dumped into every connected equipment calculation tab
- [x] Generic entity detail route supports line / connection pop-outs

## MVP 0.10 — Engineering Calculation & Datasheet Workspace
Goal: make the Digital BDEP calculation viewer feel like an in-house engineering calculation tool, not a summary card.

- [x] Full workspace header: object/tag, service, revision, maturity, governing basis and connected entities
- [x] Discipline tabs inside one datasheet/calculation workspace:
  - [x] Process / Safety
  - [x] Instrumentation / DCS
  - [x] Technical / Mechanical
  - [x] Electrical
  - [x] Cost Estimate
  - [x] Vendor / EPC
  - [x] Operations
  - [x] HAZOP
  - [x] Provenance / Audit
- [x] Every calculation renders:
  - [x] input register with source and revision
  - [x] criteria / limits
  - [x] equations
  - [x] numerical substitution
  - [x] intermediate results
  - [x] Normal / Maximum / Turndown case matrix
  - [x] standard-size / candidate selection table
  - [x] validation checks
  - [x] governing case + reason
  - [x] final selected result
  - [x] assumptions
  - [x] limitations / engineering gates
  - [x] downstream consumers
- [x] PSV-101 complete demo relief trace
  - [x] scenario register
  - [x] blocked-vapor-outlet deterministic load
  - [x] relieving pressure
  - [x] choked-flow check
  - [x] vapor mass-flux calculation
  - [x] required effective area
  - [x] standard-orifice candidate table
  - [x] selected demo orifice
  - [x] selected-area capacity check
  - [x] explicit safety approval gate for final issue
- [x] Line sizing full candidate trace
- [x] Pump full duty trace
- [x] Vessel full holdup trace
- [x] FCV full Cv trace
- [x] Datasheet-style printable layout

## MVP 0.11 — HAZOP Digital-Thread Demonstrator
- [ ] Build HAZOP nodes automatically from process sections / connected graph (current demo nodes are deterministic and entity-linked, but explicitly authored)
- [x] Pre-populate design intent, operating envelope and connected equipment/lines
- [x] Guideword/deviation rows
- [x] Candidate causes linked to actual valves/equipment/lines
- [x] Existing safeguards linked to actual instruments/PSVs/interlocks
- [x] Consequences and action/recommendation fields
- [x] Jump from HAZOP row to engineering entity/calculation
- [x] Show how a design change can identify affected HAZOP rows
- [x] Explicit rule: HAZOP assistant supports the workshop; it does not replace the multidisciplinary HAZOP team

## MVP 0.12 — Engineering Export Layer
- [x] PDF calculation/datasheet export
- [x] Standalone SVG engineering drawing export
- [ ] DEXPI 2.x XML exporter: semantic prototype complete; official schema/profile validation still pending
- [x] Visio adapter / VDX or VSDX mapping
- [x] CAD DXF exporter
- [x] DWG converter adapter via approved Autodesk/ODA service; do not fake binary DWG
- [ ] Export manifest with model revision, drawing revision, provenance and generation timestamp

## MVP 0.13 — Multi-Sheet / Continuation P&ID
- [x] Add second approved demo process section
- [x] Off-page connector from PID-DEMO-001 to PID-DEMO-002
- [x] Same line/object IDs continue across sheets
- [ ] General automatic cross-sheet reference engine (current PID-001/PID-002 continuation is generated from the approved demo continuation definition)
- [ ] Selecting continuation line shows both drawing representations in one live inspector
- [x] Preserve one semantic line identity (LINE-1103) across PID-DEMO-001 / PID-DEMO-002 summary and continuation register

## MVP 0.14 — Generated BDEP Summaries
- [x] Equipment list
- [x] Stream list
- [x] Line list
- [x] Valve list
- [x] Control-valve list
- [x] Instrument index
- [x] Control-loop list
- [x] PSV / relief summary
- [x] Calculation register
- [x] Mechanical / technical summary
- [x] Cost summary
- [x] Publication / completion summary
- [x] Export summaries to HTML / CSV / PDF

## MVP 0.15 — Engineering Revision, Review & Client Issue Control
Goal: support many engineers and autonomous agents working simultaneously while preserving a controlled approved engineering baseline and exposing only formally issued revisions to the client.

### Engineering nomenclature — use in UI/API/domain language
Use engineering / digital-plant terminology in user-facing features. Git-like mechanics may be used internally, but do not expose software-development jargon as the primary engineering language.

- **Approved Engineering Baseline** — controlled internal reference state used for new engineering work
- **Engineering Change Package (ECP)** — isolated proposed engineering change against a known baseline
- **Working Revision** — current editable state inside an ECP
- **Engineering Change Record** — immutable record of one proposed semantic change
- **Engineering Change Comparison** — semantic before/after comparison
- **Engineering Conflict** — incompatible simultaneous changes requiring engineering resolution
- **Refresh Against Baseline** — update an ECP when its input/reference versions are no longer current
- **Engineering Review Package** — submitted ECP presented to checkers/approvers
- **Discipline Check** — maker/checker technical verification
- **Affected-Discipline Review** — required review created from dependency/impact analysis
- **Engineering Approval Gate** — final internal authorization before integration
- **Integration Queue** — serialized queue that revalidates approved ECPs before incorporation
- **Integrate into Approved Baseline** — controlled incorporation of an approved ECP
- **Release Candidate** — frozen candidate snapshot undergoing issue checks
- **Client Issue** — immutable formally released BDEP revision visible to the client
- **Superseded Client Issue** — older released revision retained for traceability
- **Affected / Update Required** — downstream engineering item invalidated by an upstream change
- **Stale Input** — calculation or record created from an older source-object/property version
- **Client Comment / Client Action** — client feedback tied to the exact released object/drawing/revision

### Revision-control foundation
- [ ] Persistent Approved Engineering Baseline
- [ ] Persistent Engineering Change Package
- [ ] Property/object-level Engineering Change Records
- [ ] Store base object/property revision used by each change
- [ ] Detect direct semantic Engineering Conflicts
- [ ] Detect Stale Input / Refresh Against Baseline requirement
- [ ] Support many concurrent ECPs without project-wide hard locking
- [ ] Soft work reservations / awareness for engineers and agents
- [ ] Immutable audit events for status transitions

### Review and approval
- [ ] Maker cannot approve own engineering change
- [ ] Configurable Discipline Check requirements
- [ ] Configurable Affected-Discipline Review requirements
- [ ] Engineering Approval Gate
- [ ] Approval stores reviewed content hash / revision
- [ ] Material change after approval invalidates prior approval
- [ ] Explicit statuses: Working / In Review / Checked / Approved / Conflict / Stale Input / Affected / Update Required / Blocked

### Integration queue
- [ ] Approved ECP enters Integration Queue
- [ ] Revalidate ECP against latest Approved Engineering Baseline
- [ ] Re-run deterministic engineering checks before integration
- [ ] Re-run dependency / impact checks before integration
- [ ] Block integration on conflicts or stale governed inputs
- [ ] Create new immutable Approved Engineering Baseline revision after successful integration

### Release candidate and client issue
- [ ] Create Release Candidate from one exact Approved Engineering Baseline
- [ ] Freeze model, criteria, design cases, calculations, drawings, summaries and service versions in release manifest
- [ ] Discipline Leads confirm release content
- [ ] Project Engineering Manager approval
- [ ] QA / Document Control issue check
- [ ] Authorized release approval
- [ ] Create immutable Client Issue
- [ ] Client account sees **released Client Issues only**
- [ ] Client cannot see ECPs, working revisions, internal review comments, conflicts, rejected changes or release candidates
- [ ] Client comments are anchored to released object + drawing + Client Issue revision
- [ ] Client comment may create a new internal action/ECP; it never edits the released baseline directly

### Viewer integration
- [ ] Internal header: Approved Baseline / Active ECP / Working Revision
- [ ] Compare mode: Approved vs Proposed
- [ ] Impact mode: Changed / Affected / Update Required / Conflict
- [ ] Object History / Revision tab in right inspector
- [ ] Canvas-safe highlighting without altering engineering geometry
- [ ] Client viewer mode is read-only and bound to a Client Issue snapshot

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
7. Unknown configurations stop for engineering review instead of being invented.\n8. Primary equipment is the project/dashboard reporting entity; valves, PSV and instrument bubbles remain traceable semantic child objects and roll up to the parent equipment/system.
