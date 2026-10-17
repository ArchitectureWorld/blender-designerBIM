# DesignerBIM development and releases

- This repository is ONLY Blender DesignerBIM, not the aluminum DIY platform or Revit reporting plugin.
- User target is Blender **5.2.2**. The manifest range is >=5.2.2 and <5.3.0, but untested patch versions are not claims of acceptance.
- Current P01 is a bounded JSON-backed door/drawing interaction prototype, not IFC-native production BIM or a stable component-library contract.
- Do not treat pure Python checks, ZIP validation or successful publishing as Blender runtime acceptance.
- Protect user scenes and manual notes. Do not add hidden network behaviour, arbitrary code execution, or a second custom updater.
- Keep extension ID `designer_bim_p01` and the remote source URL stable. Never replace the bytes of an already-published version.
- Changes: add regression tests first; run `python -m pytest -q` and compile checks. For runtime changes, use actual Blender 5.2.2 and report what was/was not tested.
- Releases: increment `designer_bim_p01/blender_manifest.toml` version; add `docs/releases/vX.Y.Z.md`; merge to main. The publish workflow tests, builds, publishes a prerelease, verifies anonymous download and updates `extensions/index.json`.
- Keep the channel marked prerelease until the five-step real Blender acceptance is complete. Do not use GitHub `/releases/latest/download/` for this channel because it excludes prereleases.
- Binary install packages belong in GitHub Releases. `scripts/build_release.py` is the one current build entry point; `scripts/build_package.py` is retained as a compatibility entry point.
