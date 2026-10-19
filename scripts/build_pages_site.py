"""Build the single public GitHub Pages Blender extension repository.

The release index points at an immutable GitHub Release ZIP while publication is
in progress; the Pages index rewrites only the download URL to the Pages copy.
Both copies are validated against the same published SHA-256 and byte size.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from scripts.verify_remote import validate_download

PAGES_BASE = "https://architectureworld.github.io/blender-designerBIM"


def build_pages_site(index_file: Path, installer_file: Path, output_dir: Path) -> dict:
    index_file = Path(index_file)
    installer_file = Path(installer_file)
    output_dir = Path(output_dir)
    listing = json.loads(index_file.read_text(encoding="utf-8"))
    records = listing.get("data", [])
    if len(records) != 1 or records[0].get("id") != "designer_bim_p01":
        raise ValueError("Expected one DesignerBIM extension")
    entry = records[0]
    version = entry["version"]
    filename = f"designer_bim_p01-{version}-blender5.2.2.zip"
    if installer_file.name != filename:
        raise ValueError("Installer filename/version mismatch")
    raw = installer_file.read_bytes()
    validate_download(listing, raw, version)
    entry["archive_url"] = f"{PAGES_BASE}/{filename}"
    validate_download(listing, raw, version)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    (output_dir / filename).write_bytes(raw)
    (output_dir / "index.json").write_text(
        json.dumps(listing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "index": output_dir / "index.json",
        "installer": output_dir / filename,
        "version": version,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=Path("dist/index.json"))
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("site"))
    args = parser.parse_args()
    result = build_pages_site(args.index, args.package, args.output)
    print(json.dumps({key: str(value) for key, value in result.items()}, indent=2))


if __name__ == "__main__":
    main()
