# DesignerBIM remote extension release

Goal: publish existing P01 code to ArchitectureWorld/blender-designerBIM and provide an anonymous HTTPS Blender repository URL with a downloadable, hash-verified installation archive.

User-approved scope: upload source and release for Blender remote updates. No feature redesign. Target Blender 5.2.2; keep the declared upper bound exclusive at 5.3.0. Existing runtime limitations remain explicit.

Architecture (revised 2026-10-19): normal source tree on main; deterministic Python builder; GitHub Releases for immutable versioned ZIPs; GitHub Pages is the single public static v1 listing and serves a checksum-identical ZIP mirror. A single publication workflow tests, releases and deploys; no separate updater or user account token. Repository Pages Source must be set to GitHub Actions.

Tasks:
- [x] Re-run imported 33 tests; preserve original test evidence.
- [x] RED: test deterministic ZIP, root manifest, exact baseline, archive hash/size/URL, source-only packaging and bad metadata rejection.
- [x] GREEN: implement builder and public-URL verifier; bump packaging release to 0.1.1; update installation/migration/release documentation.
- [ ] Validate whole suite and archive; publish source using a verified import archive if required by connector transfer constraints.
- [ ] Publish prerelease and static feed through repository-scoped Actions token; never overwrite a published version.
- [ ] Read Actions results, release assets and public index; report runtime testing separately from distribution verification.

Review: avoid local/remote duplicate registration, stale index/hash, malformed ZIP root, destructive source import, upstream runtime claims, and secrets in a public repository. Unknown Blender runtime/UI outcomes remain NOT_RUN.

Ruling: the imported scripts/blender_smoke_test.py is a standalone Blender entry point and cannot be collected by non-Blender pytest. Added pytest.ini testpaths=tests; retained the actual Blender runner unchanged and explicitly NOT_RUN. Full `python -m pytest -q` must pass; source archives must include this configuration.
