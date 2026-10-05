# Digital BDEP — Engineering Revision, Review and Client Issue Control

## Purpose
Support many engineers and autonomous agents working in parallel without allowing uncontrolled changes to the approved plant engineering model.

The user-facing language is engineering/document-control language. Software source-control concepts may inspire the implementation, but they are not the vocabulary presented to process, instrumentation, mechanical, project or client users.

## Core engineering objects

### Approved Engineering Baseline
The controlled internal plant-engineering state from which new work starts.

It is immutable after approval. A successful integration creates a new baseline revision rather than modifying the old one in place.

### Engineering Change Package (ECP)
A bounded set of proposed semantic engineering changes prepared against one Approved Engineering Baseline.

An ECP contains:
- base baseline ID
- Working Revision
- maker / originating agent
- object/property-level change records
- source object/property revisions
- provenance
- change reason
- impact states
- required Discipline Checks
- Affected-Discipline Reviews
- Engineering Approval Gate
- exact content hash reviewed by each approver

### Engineering Change Record
One semantic change such as:

STR-S102 / cases.maximum.mass_flow / 92 -> 110 t/h

This is preferred over a text/file diff because engineering review must understand object identity, units, case, property and downstream dependency.

### Engineering Review Package
The review presentation of one ECP.

Reviewers see:
- Approved value
- Proposed value
- source/provenance
- calculation trace
- affected objects
- Affected / Update Required items
- engineering conflicts
- stale governed inputs
- drawing representations
- HAZOP impact where relevant

### Integration Queue
Approved ECPs do not modify the Approved Engineering Baseline immediately.

The Integration Queue serializes incorporation. Before each ECP is integrated, the platform rechecks:
- current Approved Engineering Baseline
- reviewed content hash
- required approvals
- direct Engineering Conflicts
- Stale Input
- Affected / Update Required items
- deterministic engineering checks
- drawing/model validation

If the baseline has moved since the ECP was prepared, the package must Refresh Against Baseline and be revalidated.

### Release Candidate
A frozen candidate snapshot created from one exact Approved Engineering Baseline for formal issue checks.

The release manifest freezes:
- plant model
- Design Basis revision
- design cases
- simulation publications
- calculation records and calculation-service versions
- PFD revisions
- P&ID revisions
- MSD revisions
- equipment/line/instrument/PSV summaries
- vendor information included in the issue
- HAZOP references/status
- approval evidence
- export artifacts

### Client Issue
An immutable formally released BDEP revision.

The client viewer is bound to a Client Issue and must not read live internal working state.

## Engineering workflow

Approved Engineering Baseline
→ Engineering Change Package
→ Engineering Review Package
→ Discipline Check
→ Affected-Discipline Review
→ Engineering Approval Gate
→ Integration Queue
→ New Approved Engineering Baseline
→ Release Candidate
→ Release Checks / Authorization
→ Client Issue

## Parallel engineering rule
No project-wide hard lock is required for normal work.

Every ECP records the object/property revision it read. When it is submitted or integrated, the platform detects:
- same-property competing edits → Engineering Conflict
- changed governed input → Stale Input / Refresh Against Baseline
- changed upstream dependency → Affected / Update Required

The system must never silently resolve a safety-critical engineering conflict.

## Maker / checker rule
The maker of an ECP cannot perform its required Discipline Check or Engineering Approval Gate.

Autonomous agents may prepare ECPs, deterministic calculations, impact analysis and review evidence. Human approval requirements are determined by company governance and change criticality.

## Client visibility rule
The client service queries only Client Issue records with status=released and client_visible=true.

The client view must not expose:
- Working Revisions
- ECPs
- internal reviewer identities/comments
- Engineering Conflicts
- rejected changes
- Integration Queue
- Release Candidates
- internal cost information unless specifically included in the Client Issue manifest

Client comments are anchored to the exact Client Issue, drawing/object and revision. They create an internal action/ECP if engineering modification is required; they never modify the released issue directly.

## Initial implementation slice
The current prototype establishes:
- persistent Approved Engineering Baseline
- persistent ECPs
- object/property-level Engineering Change Records
- persistent multidisciplinary review requirements
- maker/checker separation
- reviewed-content hashes
- Integration Queue persistence
- Release Candidate persistence
- immutable Client Issue manifest
- server-side released-only client catalog
- separate internal revision-control and client-issue views

Next:
- object/property revision ledger
- direct conflict detection between simultaneous ECPs
- governed-input stale detection from dependency graph
- release approval requirements
- baseline integration transaction
- client comment/action thread
- compare/impact modes in the main engineering workspace
