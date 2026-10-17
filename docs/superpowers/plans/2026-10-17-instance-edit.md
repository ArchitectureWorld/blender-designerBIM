# P01 instance editing implementation plan

Goal: turn a fixed door demo into a bounded editable component prototype and publish v0.2.0 using the existing feed.
Spec: docs/superpowers/specs/2026-10-17-instance-edit.md
Constraints: Blender 5.2.2; same extension ID; non-destructive scenes; no hidden network calls; preserve notes and GUIDs; publish only immutable versioned assets.

1. Add failing state/geometry regression tests. Implement schema migration, create/copy/move/height/handing and deterministic placements. Verify original and new tests.
2. Add Blender operators and a compact instance panel, fix stale version display, and add matching geometry/height dimensions. Add real Blender smoke script; do not mock bpy to claim runtime acceptance.
3. Version manifest and release tests; write short Chinese acceptance guide; run complete tests/compile/build. Push a development branch, run CI incl. exact-version runtime when available, merge only verified changes, run existing publish pipeline and inspect public feed/assets.

Review focus: no copying notes with instances; no overlap or partial writes; legacy REVIEW flags; fixed section dimensions; new GUIDs versus shared definition; future schema rejection; original GUI functions preserved.
