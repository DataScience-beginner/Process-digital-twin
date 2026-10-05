# Digital BDEP P&ID Drafting Standards Baseline

## Purpose
Define the standards hierarchy for the Python P&ID renderer before automatic layout is developed.

## Standards hierarchy

### 1. ISO 10628-1 — diagram content and drafting
Use as the baseline for:
- classification and content of process diagrams
- overall representation principles
- drafting rules for chemical/petrochemical flow diagrams

### 2. ISO 10628-2 + ISO 14617 — process graphical symbols
Use as the baseline taxonomy for:
- equipment symbols
- piping components
- valves
- process connections
- terminal/boundary symbols
- general graphical-symbol construction rules

### 3. ANSI/ISA-5.1 — instrumentation and control
Use for:
- instrument identification semantics
- functional tag letters
- instrument/control functions
- instrument bubble conventions
- signal/control relationships

Do not embed or reproduce proprietary standard artwork. Implement company-approved SVG masters mapped to the semantic classes.

### 4. IEC 62424 — P&ID/control-engineering information exchange
Use for:
- explicit process-control engineering requests
- mapping P&ID objects to control-engineering objects
- preserving machine-readable control semantics

### 5. DEXPI 2.x — digital interchange
Use for:
- vendor-neutral plant/process model mapping
- topology and engineering-attribute exchange
- graphics/interchange boundary when appropriate

## Company standard overlay
The renderer must support a project/company profile overriding:
- exact SVG symbol master
- tag format
- line number format
- text height/font
- line weights
- signal-line patterns
- nozzle display convention
- valve/actuator representation
- border/grid/title block
- notes/revision style
- off-page connector style
- preferred module layouts

## Architecture rule
Standards do not belong in coordinates.

Canonical plant model:
engineering meaning and connectivity.

Drafting profile:
how the company represents that meaning.

Drawing view model:
where objects are placed on a particular sheet.

## Engineering drawing quality rules for MVP
- monochrome engineering canvas by default
- no decorative fills/rounded UI shapes inside P&ID
- consistent stroke widths
- orthogonal process lines
- clear main-flow hierarchy
- equipment rendered from approved symbol masters
- instrument bubbles rendered from approved instrument master
- valves rendered by valve/actuator class
- no text overlapping symbols/lines
- minimum clearances around equipment and annotations
- explicit boundary/off-page connector objects
- semantic process and signal lines have distinct line styles
- drawing title block and notes area are reserved geometry
- graphical repositioning must not alter engineering revision state
