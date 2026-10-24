# E4.2 — Duty / standby generation benchmark (synthetic)

**Status:** Implemented on PR #23 experimental branch; not an issued industrial P&ID.

## Demo progression

1. Select **Single pump**: approved source PFD BENCH-001 -> synthetic standard TRANSFER_PUMP_SUCTION_V1 -> 11 objects / 19 directed port transitions -> maxGraph visual.
2. Select **Duty / standby**: source PFD BENCH-002 with two centrifugal pumps and four stream mappings -> synthetic standard TRANSFER_PUMP_DUTY_STANDBY_V1 -> 22 objects and parallel branches through common suction and discharge headers -> maxGraph visual.
3. Switch between BFD/PFD/P&ID views; select equipment/valves/pipes for properties. The canvas uses **actual @maxgraph/core**.
4. On unapproved PFD, missing stream, ambiguous pump roles, invalid nozzle/branch port or unapproved configuration, the generator returns a decision exception instead of inventing connections.
5. Unknown engineering values such as pressure, pipe class, flow and size are preserved as null, not fabricated.

## Source design

- `prototypes/maxgraph-pid/fixtures/pfd_duty_standby.json` — source PFD and equipment roles.
- `prototypes/maxgraph-pid/configurations/pump-duty-standby.json` — approved fixture-specific configuration: named nodes, ports, suction and discharge routes.
- `prototypes/maxgraph-pid/src/generate-parallel.js` — generic role resolution and path expansion; no hardcoded P-101A/P-101B graph code.
- `prototypes/maxgraph-pid/src/engineering.js` — stage-specific live graph and scenario swapping.
- `prototypes/maxgraph-pid/src/main.js` — maxGraph visualization; still initially positioned with sample coordinates.
- `prototypes/maxgraph-pid/test/parallel.test.js` — source approval, branch topology, rejection tests, route integrity.
- `prototypes/maxgraph-pid/test/browser.spec.js` — Chromium tests switching arrangements and visual views; CI screenshots.

## Important limitations

The fixture's duty/standby design is **illustrative**. It is not reviewed for specific site design requirements or standby isolation, check valves, pressure protection, hydraulics, bypasses, instrument loops, operability, HAZOP, piping specification or P&ID symbology compliance.

Engineering automation currently follows a pre-approved synthetic route-template, not agent selection across a rich commercial library, and has no live simulator feed. Drawing node placements are static examples; maxGraph does edge routing but ELK/drafter-level sheet automation and collision checks are pending.

**Next engineering milestone:** use a layout engine (ELK) driven by graph topology and standard orientation/branch rules, plus a versioned symbol/stencil registry. Validate multi-pump graph routing and produce actual visual screenshot, with no coordinate table embedded in P&ID UI. Do not conflate automatic semantic graph generation with complete drafting automation.
