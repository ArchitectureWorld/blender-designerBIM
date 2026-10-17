from pathlib import Path
import tomllib
import pytest
from designer_bim_p01 import interaction
ROOT=Path(__file__).resolve().parents[1]


def test_installable_extension_pins_requested_blender_baseline():
    path=ROOT/'designer_bim_p01'/'blender_manifest.toml'
    assert path.exists(), 'installable manifest missing'
    d=tomllib.loads(path.read_text())
    assert d['blender_version_min']=='5.2.2'
    assert d['blender_version_max']=='5.3.0'
    assert d['type']=='add-on'
    assert 'SPDX:GPL-3.0-or-later' in d['license']


def test_drag_grows_opening_symmetrically_about_fixed_center():
    assert callable(getattr(interaction,'width_from_drag',None)), 'width drag mapping missing'
    assert interaction.width_from_drag(900,1.0,1.15)==1200
    assert interaction.width_from_drag(900,1.0,.95)==800


def test_drag_precision_is_explicit():
    assert callable(getattr(interaction,'width_from_drag',None)), 'width drag mapping missing'
    assert interaction.width_from_drag(900,1.0,1.002,step_mm=10)==900
    assert interaction.width_from_drag(900,1.0,1.002,step_mm=1)==904


def test_drag_invalid_input_rejected():
    assert callable(getattr(interaction,'width_from_drag',None)), 'width drag mapping missing'
    with pytest.raises(ValueError):
        interaction.width_from_drag(900,0,float('nan'))


def test_runtime_adapter_exists_without_installing_into_user_startup():
    path=ROOT/'designer_bim_p01'/'addon.py'
    assert path.exists(), 'Blender adapter missing'
    import ast
    tree=ast.parse(path.read_text())
    names={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    assert {'register','unregister','create_demo_scene','apply_model'} <= names
