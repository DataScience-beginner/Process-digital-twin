# Autonomous Forward-Engineering P&ID — Architecture & Research Baseline

**Status:** Proposed / architecture discovery, 2026-10-24  
**Epic:** https://github.com/DataScience-beginner/Process-digital-twin/issues/19  
**Scope:** one engineering PFD section; not a completed production system  
**Repository policy:** existing `services/plant-model-service` code is a reference prototype, NOT an incumbent that must be retained.

## 1. Problem and non-negotiable operating contract

Build a **zero-prompt, exception-driven, forward-engineering** system. From an approved BFD + simulation + PFD + design basis and project-specific requirements, **agents** must discover known standard configurations, match/apply approved variants, assemble an engineering graph, generate P&IDs and linked data, run validations and prepare revisions. A process engineer must **not** prompt for routine work, select/drag standard assemblies, copy reference projects, transfer values by hand or route known pipelines. Users only intervene for (1) wrong/unresolved assembly, (2) genuinely new configurations/requirements, and (3) mandatory qualified engineering approval.

Primary use case is **greenfield generation**. Existing P&ID digitization is an *optional secondary library-building intake*; do not bias architectural selection to OCR-first products.

Human approvals cannot be eliminated when required by engineering governance. Agent proposals do not constitute validated process-safety design.

## 2. Required engineering thread

`BFD -> simulation publication -> PFD functional topology -> approved engineering configuration expansion -> detailed P&ID semantic graph -> drawing view(s) -> line/instrument/equipment lists & change impact`.

Maintain project ID, stable non-tag object IDs, source reference, criteria, design cases, engineering provenance, revision, lifecycle status. A change at any stage generates a scoped impact proposal, not a silent rewrite of approved upstream data.

### Hierarchy

Plant -> Process section -> PFD functional module -> Engineering configuration -> Micro-configuration -> Physical/semantic objects and ports. Configurations can span multiple drawing sheets. Sheet ownership is a presentation concern, not topology identity. Support upstream/downstream section interfaces, recycle loops, branches, standby arrangements, reversible flow and off-page references. **A connection is between named engineering ports**, not inferred from screen coordinates.

Keep two representations if the chosen library supports them: *detailed physical connectivity graph* (nozzles, line segments, valves, junctions, instruments, signals and interfaces) and a *derived functional graph* for configuration search and agent planning. Functional graph must not overwrite detailed semantics.

## 3. Buy/reuse-first architecture selection

No final stack selected. Avoid implementing generic canvas, graph algorithms, layout engines, CAD serialization, workflow retries or schema/DEXPI conversion when a maintained library covers these adequately. Evaluate tool fitness with an executable fixture and total cost of ownership, not feature brochures.

| Component / source | Observed strengths | Constraints / verification question | Provisional role |
|---|---|---|---|
| [openpidl](https://github.com/openpid-com/openpidl) / [architecture](https://github.com/openpid-com/openpidl/blob/main/docs/ARCHITECTURE.md) | Python declarative PIDL YAML, engineering graph, normalization, traversal, JSON and DEXPI/Proteus conversion, taxonomy YAML. Source package 0.0.1 alpha, LGPL-3.0-only. | Can exact named ports/nozzles and persistent IDs survive round trip? Its documented tag-derived IDs and normalized nozzle chains may lose important identity/detail. Assess tests and active maintenance. | Leading candidate for engineering configuration definition and graph/interchange |
| [SFILES2](https://github.com/process-intelligence-research/SFILES2) / [TU Delft notes](https://www.pi-research.org/research/software/sfiles/) | PFD/P&ID graph ↔ concise sequence notation; research on autocompletion and P&ID generation. | Not itself a complete detailed engineering schema or P&ID generator; test specific process topology mapping. | Optional functional topology / R&D representation |
| [pyDEXPI](https://github.com/process-intelligence-research/pyDEXPI) | Python DEXPI data model, Proteus XML ingestion, engineering graph/toolkits. Source release 1.2.0 with Python >=3.12 and AGPL-3.0. | Commercial/AGPL network-use implications; verify interoperability and export coverage; direct embedding not yet approved. | Standards compatibility benchmark or separately licensed adapter |
| [Programmatic-PID](https://github.com/D-sorganization/Programmatic_PID) | Python YAML input, DXF via ezdxf, SVG previews, symbols, instruments, control loops, multi-sheet example. | Example includes fixed x/y dimensions. Determine whether it can achieve automated standards-compliant layouts and source IDs, and inspect license/maintainer reliability. | Forward-generation drawing benchmark |
| [maxGraph](https://github.com/maxGraph/maxGraph) / [docs](https://maxgraph.github.io/maxGraph/docs/getting-started/) | Apache-2.0, SVG canvas, custom shapes and ports, editing, routing, XML, browser UI; packages/core vs examples. | TypeScript client dependency; does canvas emit *controlled engineering commands* rather than owning semantic truth? Large-P&ID performance and fidelity. | Candidate exception-only engineering drawing canvas |
| [draw.io](https://github.com/jgraph/drawio) | Complete Apache-licensed-source diagram application and shape editor with embedding options. | Editor UI larger than needed; integration/asset-license constraints, data-binding and deterministic command interception. | Comparator against maxGraph for reduced UI effort |
| [ELK](https://eclipse.dev/elk/) | Automatic hierarchical/node/port layout and orthogonal edge routing. | Routing/annotations may still need company drafting checks. | Layout benchmark, not engineering semantics |
| [NetworkX](https://networkx.org/) | Mature graph algorithms and topology checks. | Never assume traversability alone proves physically valid port connection. | Graph analysis adapter |
| [ezdxf](https://ezdxf.readthedocs.io/) | DXF export/import utilities. | DXF is not semantic engineering truth. | CAD output adapter |
| [IDAES-UI](https://github.com/IDAES/idaes-ui) | Example of simulation-origin data-backed flowsheet display. | Not detailed P&ID generation. | Architectural precedent |
| [Prefect](https://www.prefect.io/) / [Dagster](https://dagster.io/) | Orchestration, retries/event triggers and asset monitoring. | Choose only after proving small workflow and desired operational model. | Candidate job orchestration |
| Siemens COMOS / Aucotec Engineering Base (commercial) | Typical/module management and database-centric engineering. | Need procurement/API/automation licensing confirmation and costed POC; vendor capabilities are not equivalent to open-source access. | Buy-vs-build commercial benchmark |

**Licensing review:** Do not infer from permissive license of a codebase that bundled symbols have identical rights. pyDEXPI is AGPL, openpidl LGPL, maxGraph Apache. Document obligations and commercial options prior to shipping. This is technical planning, not legal advice.

## 4. Leading architectural alternatives

**A — openpidl-led:** engineering graph/DSL is authoritative; other layers plug in. Minimum original schema but significant alpha/mapping risk.

**B — industrial/commercial engine-led:** obtain module+typical+API engine from commercial vendor and add agent orchestration. Mature engineering features but possible lock-in and expensive/nonexistent deep API access.

**C — hybrid / replaceable adapters:** choose *one* demonstrated authoritative detailed engineering contract (could be openpidl; existing custom model is expendable), use SFILES2 only for higher-level topology if valuable, drawing backend via Programmatic-PID/maxGraph/ELK, DEXPI via suitable licensed adapter. Recommended **hypothesis**, not decision. Reject unnecessary adapters if they add conversion loss or maintenance burden.

Important: never create parallel unsynchronized graph masters. A canvas position is never source of process connectivity. Human correction must generate validated graph commands and a redraw, not edit a detached picture.

## 5. Event-driven agent workflow

**Triggers:** new approved PFD; simulation/basis revision; new project; reviewed change; accepted configuration standard. Not chat messages.

1. Read and completeness-check authoritative project inputs.
2. Decompose PFD into functional modules with typed cross-section boundaries.
3. Search authorized approved configuration catalog and evaluate applicability/variant rules.
4. Instantiate graph/configuration deterministically; retain citations to standard and source conditions.
5. Auto-generate symbol mapping, routing, annotations, and drawing sheets.
6. Run deterministic topology, ports, design-data, rule and drafting validation; auto-correct *only bounded safe cases*.
7. If unresolved/new/unsafe, create concise engineering exception with evidence and suggested options; await authorized decision.
8. Produce approved and revision-tracked drawing+structured deliverables; do not confuse preview with issued drawings.

The agent may recommend a standard but cannot claim one exists if no approved source is registered. Keep tenant-private drawings, drawings learned from clients, and model-training controls isolated.

## 6. Epic rollout (deliver one acceptance-based slice at a time)

- **E0 Documentation and catalog:** this baseline, references, explicit decisions and risks.
- **E1 Fixture specification:** V-101 liquid outlet -> suction isolation valve -> P-101 suction -> discharge -> downstream interface; cases and data-binding expectations stated. No drawings or tools required yet.
- **E2 Engineering-contract bakeoff:** openpidl (and optionally pyDEXPI/SFILES2 where appropriate), compare exact structure, stable identifiers, upstream/downstream traces and lossless conversions. Record pass/fail on real code.
- **E3 Drawing bakeoff:** automatic visual generation & correction canvas from same graph using maxGraph vs draw.io / Programmatic-PID; symbols, nozzle anchors, editable DXF/SVG and congestion.
- **E4 Automatic approved-variant selection and assembly:** no user prompts; demonstrate standard configuration application.
- **E5 Decision-only review, rule validation, audit/versioning:** engineer only handles exceptions and approvals.
- **E6 Change propagation and multi-section interfaces.**
- **E7 New configuration intake:** hand-sketch candidate recognition, graph reconstruction, engineer approval and subsequent automatic reuse.

## 7. E1 test fixture acceptance contract

**Objects:** V-101, upstream liquid nozzle, suction line segment(s), isolation valve XV-101, P-101 suction/discharge nozzles, boundary source/sink; separate signal objects if included. These are **illustrative fixture labels**, not real project tags.

**Ground truth:** stable object IDs independent of displayed tags; named compatible process ports; explicit unique flow edges; derived upstream and downstream reachability and clear line vs simulation stream relation; source case, provenance, revision, missing-spec state, and validation outcome. Treat pump body flow as a specifically supported transition, not generic free-flow across all equipment associations.

**Failure cases:** remove pipe/nozzle edge; invert direction where disallowed; reference nonexistent port; duplicate ID; rename tag; missing line specification; non-approved configuration. Expected results must not silently pass.

**Success:** fixture is expressible and re-serializable without losing physical connectivity; engine can generate it from structured project inputs without manual prompts/assembly; compare output between candidates.

## 8. Decision log

| Date | Decision or open question | Status |
|---|---|---|
| 2026-10-24 | Focus product on forward PFD-to-P&ID generation, not digitization. | Fixed |
| 2026-10-24 | Agent-run generation with human interventions restricted to exceptions, truly new requirements and mandated approvals. | Fixed |
| 2026-10-24 | Buy/reuse first, existing plant-model prototype may be replaced. | Fixed |
| 2026-10-24 | Select openpidl, SFILES2, Programmatic-PID, maxGraph/draw.io, pyDEXPI only after fixture benchmark. | Pending |
| 2026-10-24 | Choose authoritative detailed graph schema and configuration rule storage. | Pending |
| 2026-10-24 | Choose canvas and layout engine using true nozzle-anchor and graph command tests. | Pending |
| 2026-10-24 | Commercial tool/API pricing and license review. | Pending |

## 9. Source/reference index

- openpidl: https://github.com/openpid-com/openpidl ; https://github.com/openpid-com/openpidl/blob/main/docs/ARCHITECTURE.md
- SFILES2: https://github.com/process-intelligence-research/SFILES2 ; https://www.pi-research.org/research/software/sfiles/
- pyDEXPI: https://github.com/process-intelligence-research/pyDEXPI
- Programmatic-PID: https://github.com/D-sorganization/Programmatic_PID
- maxGraph: https://github.com/maxGraph/maxGraph ; https://maxgraph.github.io/maxGraph/docs/getting-started/
- diagrams.net: https://github.com/jgraph/drawio
- Eclipse Layout Kernel: https://eclipse.dev/elk/
- NetworkX: https://networkx.org/
- ezdxf: https://ezdxf.readthedocs.io/
- IDAES flowsheet visualizer: https://github.com/IDAES/idaes-ui
- Prefect: https://www.prefect.io/
- Dagster: https://dagster.io/
- DEXPI consortium: https://dexpi.org/

**Research limitation:** repository capability claims and documented examples are not equivalent to executed integration benchmarks; maturity, licensing, round-trip fidelity and performance remain to be verified against E1 fixture.
