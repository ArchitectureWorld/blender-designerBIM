# DesignerBIM / Prototype 01 — approved scope

Date: 2026-10-16. Version: 0.1.0. This is a door interaction prototype, not a production BIM system.

## Acceptance
A new, isolated Blender scene with one wall and three instances sharing one definition. Change D01 opening width 900 → 1200 mm without changing D02/D03; change the shared frame section without resetting widths. Update 3D, plan, elevation and dimension labels from the same state. Preserve manual notes and flag them for review after related changes. Save/reload state and retain all relationships. Provide a width drag handle and undo/cancel support.

## Implementation sequence
1. RED tests for pure-Python state, scoped edits, validation, manual notes, persistence and generated representations.
2. GREEN deterministic core and 2D SVG exporter; no Blender dependency.
3. Blender adapter, sidebar, parameter operations, manual note sync, non-destructive demo scene and three-view layout.
4. Blender integration script exercising actual generated meshes, text, saving/reopening and UI operators.
5. Execute what the available environment supports; package source, installable extension, demo generator, instructions and honest test report.

## Decisions / exclusions
- Both connected development hosts returned connection errors. Work is isolated under /mnt/data/blender_bim_p01; do not touch aludiy-designer or BIM-baogui.
- The container has no Blender/bpy; download and package-network access failed. Blender runtime checks must remain explicitly NOT RUN unless access is restored.
- New scene only. Existing scenes are not deleted. Layout changes occur only on an explicit button.
- Millimetres in serialized core; metres at Blender boundary. Stable definition / instance / note IDs. JSON schema 1; reject unknown versions.
- 2D diagrams are vector geometry and text on dedicated auxiliary boards in the same scene. This prototype does not claim arbitrary model sectioning, IFC-native storage, DWG or production construction drawings.
- Manual note text/location is separate from generated geometry and synchronized before operations and saves. Related geometry changes trigger REVIEW; only explicit confirmation clears it.
- No arbitrary mesh editing, Agent, component library, publish workflow, full SU/Rhino keymap, or arbitrary wall/door placement in this phase.

## Baseline update (user instruction during implementation)
Blender **5.2.2** is the target runtime. The package declares minimum 5.2.2 and excludes 5.3+; later 5.2 patches are not claimed tested. Runtime tests must record `bpy.app.version_string` and fail this acceptance suite if it is not exactly 5.2.2. Do not substitute another version's runtime pass. The prototype is an isolated adapter spike, not a finalized production BIM schema or component library contract.
