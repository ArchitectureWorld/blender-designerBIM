"""Distribution contract: a valid build is not Blender runtime acceptance."""
import hashlib
import importlib.util
import io
import json
import shutil
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = "ArchitectureWorld/blender-designerBIM"


def builder():
    path = ROOT / "scripts/build_release.py"
    assert path.is_file(), "remote release builder is missing"
    spec = importlib.util.spec_from_file_location("release_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_has_installable_manifest_at_zip_root(tmp_path):
    result = builder().build_release(ROOT, tmp_path, REPO)
    with zipfile.ZipFile(result["installer"]) as archive:
        assert archive.testzip() is None
        assert "blender_manifest.toml" in archive.namelist()
        assert "__init__.py" in archive.namelist()
        assert "LICENSE" in archive.namelist()
        manifest = tomllib.loads(archive.read("blender_manifest.toml").decode())
        assert manifest["id"] == "designer_bim_p01"
        assert manifest["version"] == "0.1.1"
        assert manifest["blender_version_min"] == "5.2.2"
        assert manifest["blender_version_max"] == "5.3.0"


def test_listing_hash_size_and_version_are_derived_from_actual_zip(tmp_path):
    result = builder().build_release(ROOT, tmp_path, REPO)
    listing = json.loads(result["index"].read_text())
    assert listing["version"] == "v1"
    assert listing["blocklist"] == []
    assert len(listing["data"]) == 1
    entry = listing["data"][0]
    raw = result["installer"].read_bytes()
    assert entry["archive_size"] == len(raw)
    assert entry["archive_hash"] == "sha256:" + hashlib.sha256(raw).hexdigest()
    assert entry["archive_url"] == (
        "https://github.com/ArchitectureWorld/blender-designerBIM/releases/download/"
        "v0.1.1/designer_bim_p01-0.1.1-blender5.2.2.zip"
    )
    assert entry["blender_version_min"] == "5.2.2"
    assert entry["blender_version_max"] == "5.3.0"


def test_release_is_deterministic(tmp_path):
    a = builder().build_release(ROOT, tmp_path / "a", REPO)
    b = builder().build_release(ROOT, tmp_path / "b", REPO)
    for key in ("installer", "source", "index", "checksums"):
        assert a[key].read_bytes() == b[key].read_bytes()


def test_source_archive_includes_tests_and_excludes_generated_or_private_files(tmp_path):
    result = builder().build_release(ROOT, tmp_path, REPO)
    with zipfile.ZipFile(result["source"]) as archive:
        names = archive.namelist()
        assert any(name.endswith("/tests/test_core.py") for name in names)
        assert "DesignerBIM_P01/pytest.ini" in names
        assert any(name.endswith("/scripts/build_release.py") for name in names)
        assert not any("/.git/" in name or "/__pycache__/" in name for name in names)
        assert not any("/dist/" in name or "/bootstrap/" in name for name in names)
        assert not any(name.endswith(".pyc") or name.endswith(".env") for name in names)


@pytest.mark.parametrize("bad_repo", ["", "https://github.com/a/b", "a/b/c", "a/../b"])
def test_invalid_repository_rejected(tmp_path, bad_repo):
    with pytest.raises(ValueError, match="repository"):
        builder().build_release(ROOT, tmp_path, bad_repo)


def test_public_verifier_rejects_corrupt_archive(tmp_path):
    module = builder()
    result = module.build_release(ROOT, tmp_path, REPO)
    listing = json.loads(result["index"].read_text())
    path = ROOT / "scripts/verify_remote.py"
    assert path.is_file(), "public repository verifier is missing"
    spec = importlib.util.spec_from_file_location("verify_remote", path)
    remote = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(remote)
    remote.validate_download(listing, result["installer"].read_bytes(), "0.1.1")
    with pytest.raises(ValueError):
        remote.validate_download(listing, b"not a zip", "0.1.1")


def test_public_verifier_rejects_wrong_expected_version(tmp_path):
    result = builder().build_release(ROOT, tmp_path, REPO)
    listing = json.loads(result["index"].read_text())
    path = ROOT / "scripts/verify_remote.py"
    assert path.is_file(), "public repository verifier is missing"
    spec = importlib.util.spec_from_file_location("verify_remote", path)
    remote = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(remote)
    with pytest.raises(ValueError):
        remote.validate_download(listing, result["installer"].read_bytes(), "9.9.9")
