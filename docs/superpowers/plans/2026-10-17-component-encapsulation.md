# Component encapsulation implementation plan

**Goal:** expose each door as one component without welding away its structure.
**Architecture:** private per-occurrence/view geometry collections rendered through one collection instance proxy per view. JSON remains prototype authority; local frame/leaf overrides are explicit. Manual notes remain view-local and associated by ID.
**Tech Stack:** Python, Blender 5.2.2, pytest, GitHub Actions.
**Spec:** ../specs/2026-10-17-component-encapsulation.md

## Global constraints
Extension designer_bim_p01, >=5.2.2 <5.3.0; original update URL; no hidden network; don't overwrite published releases or user notes.

## Tasks
- [ ] Test-first schema3 effective parameters, old signature migration, safe deletion and empty-wall geometry.
- [ ] Test-first Blender encapsulation: single selectable occurrence; internal source objects unlinked; per-view proxies; active edit source only; cleanup.
- [ ] Implement private collections and controlled part editing, keyboard routing, fingerprint guard and old flat-scene migration.
- [ ] Run original regression, new integration and GUI selection smoke on exact Blender; retain evidence and limitations.
- [ ] Review diff; publish immutable v0.3.0 through existing workflow and verify public feed/archive.

## Review focus
Preserve native note edits and review flags. Don't delete external geometry. Exiting edit/undo/load must restore encapsulation. Local overrides must not silently become new definitions. Never advertise production library/IFC support.
