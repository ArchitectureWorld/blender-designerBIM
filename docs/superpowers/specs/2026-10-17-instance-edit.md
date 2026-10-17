# P01 v0.2.0 — editable door instances

Approved context: user can load v0.1.1 and asks to continue development and finish publication. This is not acceptance of all P01 runtime interactions.

## Bounded increment
Keep the existing wall, three-view system and extension identity. Add explicit parameter-backed create/copy, absolute/relative placement along the existing straight wall, height editing and left/right handing. All consume one model and regenerate wall openings and vector drawings. No native Shift+D conversion, general wall host editing, IFC, Agent or duct prototype in this release.

Handing convention: viewed from -Y towards the wall, LEFT/RIGHT selects the hinge side. The 3D test leaf is shown at a fixed 90 degree opening toward +Y to agree with the plan symbol. This is a simplified representation, not a manufacturing door model.

Schema 2 adds handing. Schema 1 loads through explicit migration preserving identities, revision and reviewed/stale note states. Save the original v1 JSON backup in the scene on first successful write. Reject future schemas; never replace published v0.1.1 bytes.

Create/copy generates unique IDs/tags, retains shared definition, and does NOT copy manual notes. Reject overlapping openings, inadequate prototype margins, invalid dimensions and unknown IDs before scene changes. Moving/height/handing of an annotated instance retains its note and requests review; unrelated instances remain unaffected.

## Acceptance scenario
On demo, copy D01 to X=3000 mm, move the new occurrence to X=3200 mm, set H=2400 mm, change LEFT to RIGHT. Confirm source and definition are unchanged and 3D/plan/elevation agree. Invalid overlap leaves all state unchanged. Add a note, move the door, see REVIEW. Save/reopen then change frame section for all occurrences, preserving independent dimensions. Run original full test suite too.

Target remains Blender 5.2.2; publication is prerelease. No pure-Python or static result may be reported as actual Blender GUI acceptance.

Placement tie-break: equally close available centers prefer +X, matching copying forward along the wall.
