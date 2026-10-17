# P01 progress / 2026-10-16

Scope: user-approved door interaction prototype. Mid-task runtime baseline fixed to Blender 5.2.2.

1. State core: 19 RED → GREEN tests. Independent widths, shared definition, validation, notes, review, JSON roundtrip.
2. Geometry/drawings: 7 RED → GREEN tests. Real wall openings, stable keys, fixed frame sizes, consistent plan/elevation dimensions, SVG escaping.
3. Packaging/drag mapping: 5 RED → GREEN tests. Exact baseline metadata, pure drag math, runtime adapter static structure.
4. Visual regression: actual SVG rendered. Found bottom witness lines colliding with footer and center leader crossing door tag. Added 2 failing regression tests, fixed layout and leader endpoint, 33 total pass.
5. Runtime adapter implemented: sidebar, operators, three-view layout, scalar width drag, manual notes, save/load handlers, SVG/JSON export. Syntax only verified; NOT executed in Blender.
6. Code review: rollback previously used stale stored JSON and could erase a recently edited native note after rebuild failure. Adapter now snapshots current notes before rebuild; actual Blender fault-injection check added to smoke script but NOT RUN.
7. Remaining acceptance: install/enable in exact 5.2.2, run smoke script, manually check three-view layout, selection, numeric dialog, drag/Esc/Ctrl+Z, fonts, notes and save/reopen.

Ruling: deliver an extension candidate and reproducible generator rather than fabricate a pre-generated .blend or claim unexecuted runtime tests passed.
Ruling: retain an isolated JSON adapter for this probe; do not present it as a finalized IFC production schema. Validate this and a second path-driven probe before freezing a library contract.
