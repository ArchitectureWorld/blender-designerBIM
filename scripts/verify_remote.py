"""Verify public Blender repository and archive without any authentication."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import tomllib
import urllib.request
import zipfile
from pathlib import Path

REPO_URL = "https://raw.githubusercontent.com/ArchitectureWorld/blender-designerBIM/main/extensions/index.json"


def validate_download(listing: dict, archive_bytes: bytes, expected_version: str) -> dict:
    if listing.get("version") != "v1" or listing.get("blocklist") != []:
        raise ValueError("Unexpected repository format or blocklist")
    matches = [item for item in listing.get("data", []) if item.get("id") == "designer_bim_p01"]
    if len(matches) != 1:
        raise ValueError("Expected exactly one DesignerBIM listing")
    entry = matches[0]
    if entry.get("version") != expected_version:
        raise ValueError("Repository has not published the expected version")
    if len(archive_bytes) != entry.get("archive_size"):
        raise ValueError("Downloaded archive size mismatch")
    digest = "sha256:" + hashlib.sha256(archive_bytes).hexdigest()
    if digest != entry.get("archive_hash"):
        raise ValueError("Downloaded archive hash mismatch")
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        if archive.testzip() is not None:
            raise ValueError("Archive CRC validation failed")
        names = set(archive.namelist())
        if not {"blender_manifest.toml", "__init__.py", "LICENSE"}.issubset(names):
            raise ValueError("Not an installable Blender extension ZIP")
        manifest = tomllib.loads(archive.read("blender_manifest.toml").decode("utf-8"))
    for key in ("schema_version", "id", "version", "type", "blender_version_min", "blender_version_max", "license"):
        if manifest.get(key) != entry.get(key):
            raise ValueError(f"Repository and package disagree on {key}")
    if manifest["blender_version_min"] != "5.2.2" or manifest.get("blender_version_max") != "5.3.0":
        raise ValueError("Unexpected supported Blender range")
    return {"version": expected_version, "archive_size": len(archive_bytes), "archive_hash": digest,
            "archive_url": entry["archive_url"], "anonymous_download": "PASS", "zip_manifest_and_checksum": "PASS",
            "blender_runtime": "NOT_RUN"}


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "DesignerBIM-Release-Check/1.0", "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}: {url}")
        return response.read()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=REPO_URL)
    parser.add_argument("--index-file", type=Path)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--attempts", type=int, default=12)
    args = parser.parse_args()
    result = None
    for attempt in range(args.attempts):
        try:
            raw = args.index_file.read_bytes() if args.index_file else download(args.url)
            listing = json.loads(raw)
            entry = next(item for item in listing["data"] if item["id"] == "designer_bim_p01")
            result = validate_download(listing, download(entry["archive_url"]), args.expected_version)
            if not args.index_file:
                query_url = args.url + ("&" if "?" in args.url else "?") + "blender_version=5.2.2&platform=windows-x64"
                queried = json.loads(download(query_url))
                if queried != listing:
                    raise ValueError("Blender version/platform query returned different repository content")
                result.update(repository_url=args.url, repository_http="PASS", blender_query_parameters="PASS")
            break
        except Exception as error:
            print(f"Attempt {attempt + 1}/{args.attempts}: {type(error).__name__}: {error}", flush=True)
            if attempt + 1 == args.attempts:
                raise
            time.sleep(10)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
