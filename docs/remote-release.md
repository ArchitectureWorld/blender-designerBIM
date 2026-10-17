# Remote publication contract

Stable feed: `https://raw.githubusercontent.com/ArchitectureWorld/blender-designerBIM/main/extensions/index.json`

This source is a public static JSON v1 Blender extension repository, not a Git clone endpoint. Installer archives are immutable per version under GitHub Releases. The listing is updated only after the new archive downloads anonymously and matches its byte size and SHA-256. No GitHub Pages configuration or user access token is required.

## Release a later build

1. Develop on a branch, add tests, and run `python -m pytest -q`.
2. Increase the manifest version. Do not recycle an already-published version.
3. Add `docs/releases/vX.Y.Z.md`, including exact test coverage and known runtime limitations.
4. Merge to main. Changes to the manifest trigger `.github/workflows/publish.yml`.
5. Check the workflow's test and public-repository verification steps. The release is a prerelease until actual Blender acceptance justifies changing that policy.

If publishing fails, the existing feed remains usable until the new archive has been verified. The public feed and GitHub prerelease are separate: a prerelease can be intentionally listed in this test repository. Do not use a GitHub `latest` shortcut, which need not select a prerelease.

## Verification

`python scripts/build_release.py --out dist` builds local ZIPs and index.

`python scripts/verify_remote.py --expected-version X.Y.Z` downloads the actual public index and archive, checks size, SHA-256, ZIP root and manifest consistency, and repeats the JSON request with Blender version/platform query parameters.

These checks do not execute Blender. Runtime tests remain `scripts/blender_smoke_test.py` and manual mouse/layout/undo verification in Blender 5.2.2.

## Import provenance

The initially empty repository may be populated through a checksummed tar.xz transfer of the previously delivered source plus release tooling. Only ordinary relative files are accepted; .git/.github paths are excluded from import; existing addon source is never overwritten. The import is committed as readable normal files, then the temporary transfer archive is removed. The source package preserves the original v0.1.0 reports as historical evidence.

## Primary specifications

- https://docs.blender.org/manual/en/latest/advanced/extensions/creating_repository/static_repository.html
- https://developer.blender.org/docs/features/extensions/api_listing/v1/
- https://docs.blender.org/manual/en/latest/editors/preferences/extensions.html
- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- https://cli.github.com/manual/gh_release_create
