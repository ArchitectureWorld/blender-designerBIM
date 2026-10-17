"""Distribution contract: a valid build is not Blender runtime acceptance."""
import hashlib
import importlib.util
import json
import tomllib
import zipfile
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
REPO="ArchitectureWorld/blender-designerBIM"
VERSION="0.3.0"

def builder():
    path=ROOT/'scripts/build_release.py'
    assert path.is_file(), 'remote release builder is missing'
    spec=importlib.util.spec_from_file_location('release_builder',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def verifier():
    path=ROOT/'scripts/verify_remote.py'
    assert path.is_file(), 'public repository verifier is missing'
    spec=importlib.util.spec_from_file_location('verify_remote',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def test_release_has_installable_manifest_at_zip_root(tmp_path):
    result=builder().build_release(ROOT,tmp_path,REPO)
    with zipfile.ZipFile(result['installer']) as archive:
        assert archive.testzip() is None
        assert {'blender_manifest.toml','__init__.py','LICENSE','instance_tools.py'} <= set(archive.namelist())
        m=tomllib.loads(archive.read('blender_manifest.toml').decode())
        assert m['id']=='designer_bim_p01' and m['version']==VERSION
        assert m['blender_version_min']=='5.2.2' and m['blender_version_max']=='5.3.0'

def test_listing_hash_size_and_version_are_derived_from_actual_zip(tmp_path):
    r=builder().build_release(ROOT,tmp_path,REPO)
    listing=json.loads(r['index'].read_text())
    assert listing['version']=='v1' and listing['blocklist']==[] and len(listing['data'])==1
    entry=listing['data'][0];raw=r['installer'].read_bytes()
    assert entry['archive_size']==len(raw)
    assert entry['archive_hash']=='sha256:'+hashlib.sha256(raw).hexdigest()
    assert entry['archive_url']==f'https://github.com/{REPO}/releases/download/v{VERSION}/designer_bim_p01-{VERSION}-blender5.2.2.zip'
    assert entry['blender_version_min']=='5.2.2' and entry['blender_version_max']=='5.3.0'

def test_release_is_deterministic(tmp_path):
    a=builder().build_release(ROOT,tmp_path/'a',REPO);b=builder().build_release(ROOT,tmp_path/'b',REPO)
    for key in ('installer','source','index','checksums'):
        assert a[key].read_bytes()==b[key].read_bytes()

def test_source_archive_includes_tests_and_excludes_generated_or_private_files(tmp_path):
    r=builder().build_release(ROOT,tmp_path,REPO)
    with zipfile.ZipFile(r['source']) as archive:
        names=archive.namelist()
        assert any(n.endswith('/tests/test_core.py') for n in names)
        assert 'DesignerBIM_P01/pytest.ini' in names
        assert any(n.endswith('/scripts/build_release.py') for n in names)
        assert not any('/.git/' in n or '/__pycache__/' in n or '/dist/' in n or '/bootstrap/' in n for n in names)
        assert not any(n.endswith('.pyc') or n.endswith('.env') for n in names)

@pytest.mark.parametrize('bad_repo',['','https://github.com/a/b','a/b/c','a/../b'])
def test_invalid_repository_rejected(tmp_path,bad_repo):
    with pytest.raises(ValueError,match='repository'):
        builder().build_release(ROOT,tmp_path,bad_repo)

def test_public_verifier_rejects_corrupt_archive(tmp_path):
    r=builder().build_release(ROOT,tmp_path,REPO); listing=json.loads(r['index'].read_text())
    verifier().validate_download(listing,r['installer'].read_bytes(),VERSION)
    with pytest.raises(ValueError):
        verifier().validate_download(listing,b'not a zip',VERSION)

def test_public_verifier_rejects_wrong_expected_version(tmp_path):
    r=builder().build_release(ROOT,tmp_path,REPO); listing=json.loads(r['index'].read_text())
    with pytest.raises(ValueError):
        verifier().validate_download(listing,r['installer'].read_bytes(),'9.9.9')
