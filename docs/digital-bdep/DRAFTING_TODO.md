# MVP 0.3A / 0.3B — Engineering Drawing Standard TODO

## Goal
Replace the prototype/toy-looking drawing layer with a standards-aware drafting foundation before automatic layout.

## 0.3A — Drawing standard layer
- [ ] Create DraftingProfile model.
- [ ] Define stroke/text/spacing/grid defaults.
- [ ] Create symbol registry keyed by canonical object type.
- [ ] Separate symbol geometry from plant objects.
- [ ] Add equipment symbol masters: vertical vessel, centrifugal pump.
- [ ] Add valve masters: isolation, check, control, relief.
- [ ] Add instrumentation master with tag/function text.
- [ ] Add boundary/off-page connector master.
- [ ] Add nozzle/port anchor definitions.
- [ ] Add process/signal/association line-style definitions.
- [ ] Add drawing border/title-block/notes-zone definition.
- [ ] Unit-test every registry key used by the current plant model.

## 0.3B — Engineering-grade redraw
- [ ] Render current V-101/P-101 configuration using only symbol registry masters.
- [ ] Use monochrome P&ID canvas.
- [ ] Use consistent scale and text sizing.
- [ ] Route all process lines orthogonally.
- [ ] Show vessel nozzles/connections explicitly.
- [ ] Keep instrumentation close to the measured/controlled function.
- [ ] Render control signals distinctly from process piping.
- [ ] Add line identifiers as a separate annotation layer.
- [ ] Add border, grid and title block.
- [ ] Add drawing-quality checker for overlaps/out-of-bounds/missing symbol mapping.

## 0.4 — only after 0.3B approval
- [ ] Move current manual positions into DrawingView JSON.
- [ ] Generate symbol placement from functional clusters.
- [ ] Add automatic orthogonal router.
- [ ] Preserve positions during local edits.
- [ ] Add congestion score and sheet split recommendations.

## Acceptance gate before auto-layout
The manually arranged output generated from the same symbol/drafting engine must visually resemble a normal engineering P&ID. If the approved static result is not acceptable, automatic layout must not proceed.
