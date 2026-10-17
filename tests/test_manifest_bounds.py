"""Regression for the actual Blender 5.2.2 extension validator failure."""
from pathlib import Path
import tomllib


def test_permission_reason_fits_blender_manifest_limit():
    manifest = tomllib.loads((Path(__file__).resolve().parents[1] / 'designer_bim_p01' / 'blender_manifest.toml').read_text())
    for key, reason in manifest.get('permissions', {}).items():
        assert isinstance(reason, str) and 1 <= len(reason) <= 64, (key, reason)
