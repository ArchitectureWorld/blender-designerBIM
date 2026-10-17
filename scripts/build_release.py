"""Build deterministic Blender ZIPs and a v1 static extension repository.

This validates distribution metadata, NOT Blender runtime behaviour.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
import zipfile
from pathlib import Path

REPOSITORY = "ArchitectureWorld/blender-designerBIM"
STAMP = (2026, 1, 1, 0, 0, 0)
EXCLUDED = {".git", "__pycache__", ".pytest_cache", "dist", "bootstrap", ".venv", "node_modules"}
ROOT_FILES = {"README.md", "LICENSE", ".gitignore", "AGENTS.md", "pytest.ini"}
SOURCE_DIRS = {"designer_bim_p01", "tests", "scripts", "docs", "reports", "samples", ".github"}


def _write_zip(destination: Path, records: list[tuple[Path, str]]) -> None:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, name in sorted(records, key=lambda pair: pair[1]):
            if path.is_symlink():
                raise ValueError(f"Do not package symlinks: {path}")
            info = zipfile.ZipInfo(name, date_time=STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError("Corrupt generated ZIP")


def build_release(root: Path, output: Path, repository: str = REPOSITORY) -> dict[str, Path]:
    root, output = Path(root).resolve(), Path(output).resolve()
    if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Expected repository in owner/name form")
    addon = root / "designer_bim_p01"
    manifest = tomllib.loads((addon / "blender_manifest.toml").read_text(encoding="utf-8"))
    required = ("schema_version", "id", "version", "name", "tagline", "maintainer", "type", "license", "blender_version_min")
    if any(not manifest.get(key) for key in required):
        raise ValueError("Incomplete extension manifest")
    if manifest["id"] != "designer_bim_p01" or manifest["type"] != "add-on":
        raise ValueError("Unexpected extension identity")
    if manifest["blender_version_min"] != "5.2.2" or manifest.get("blender_version_max") != "5.3.0":
        raise ValueError("Do not silently change the Blender 5.2.2 baseline")
    version = manifest["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Release version must be numeric major.minor.patch")
    output.mkdir(parents=True, exist_ok=True)
    installer = output / f"designer_bim_p01-{version}-blender5.2.2.zip"
    source = output / f"designer_bim_p01-{version}-source.zip"
    records = [(p, p.name) for p in addon.iterdir() if p.is_file() and p.suffix in (".py", ".toml")]
    records += [(root / "LICENSE", "LICENSE"), (root / "README.md", "README.md")]
    _write_zip(installer, records)
    records = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if not path.is_file() or any(part in EXCLUDED for part in relative.parts):
            continue
        if relative.parts[0] not in SOURCE_DIRS and relative.as_posix() not in ROOT_FILES:
            continue
        if path.suffix in (".pyc", ".pem", ".key", ".zip", ".xz") or path.name.startswith(".env"):
            continue
        if output == path or output in path.parents:
            continue
        records.append((path, "DesignerBIM_P01/" + relative.as_posix()))
    _write_zip(source, records)
    public_keys = (*required, "website", "tags", "blender_version_max", "platforms", "permissions")
    entry = {key: manifest[key] for key in public_keys if key in manifest}
    raw = installer.read_bytes()
    entry.update(
        archive_size=len(raw),
        archive_hash="sha256:" + hashlib.sha256(raw).hexdigest(),
        archive_url=f"https://github.com/{repository}/releases/download/v{version}/{installer.name}",
    )
    index = output / "index.json"
    index.write_text(json.dumps({"version": "v1", "blocklist": [], "data": [entry]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checksums = output / "SHA256SUMS"
    checksums.write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in (installer, source, index)), encoding="utf-8")
    build_report = output / "build-verification.json"
    build_report.write_text(json.dumps({
        "version": version,
        "target_blender": "5.2.2",
        "package_zip_integrity": "PASS",
        "index_hash_and_size": "PASS",
        "blender_runtime_integration": "NOT_RUN",
        "blender_extension_cli_validation": "NOT_RUN",
        "mouse_undo_layout_save_reopen": "NOT_RUN",
        "status": "PRE_RELEASE_FOR_USER_TESTING",
        "note": "Distribution checks must not be presented as Blender 5.2.2 runtime acceptance",
    }, indent=2) + "\n", encoding="utf-8")
    return {"installer": installer, "source": source, "index": index, "checksums": checksums, "report": build_report}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("dist"))
    parser.add_argument("--repo", default=REPOSITORY)
    args = parser.parse_args()
    result = build_release(Path(__file__).resolve().parents[1], args.out, args.repo)
    print(json.dumps({key: str(value) for key, value in result.items()}, indent=2))


if __name__ == "__main__":
    main()
