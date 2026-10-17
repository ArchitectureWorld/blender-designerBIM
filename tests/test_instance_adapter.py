"""Static adapter checks. These do not assert Blender runtime acceptance."""
import ast
from pathlib import Path
import tomllib

ROOT=Path(__file__).resolve().parents[1]


def test_new_operators_have_undo_and_explicit_ids():
    p=ROOT/'designer_bim_p01/instance_tools.py'
    assert p.is_file(), 'new instance UI adapter missing'
    tree=ast.parse(p.read_text(encoding='utf-8'))
    names={n.name:n for n in tree.body if isinstance(n,ast.ClassDef)}
    expected={'DBIM_OT_add_door','DBIM_OT_move_door','DBIM_OT_set_height','DBIM_OT_set_handing'}
    assert expected <= names.keys()
    for name in expected:
        values={target.id:ast.literal_eval(n.value) for n in names[name].body if isinstance(n,ast.Assign) for target in n.targets if isinstance(target,ast.Name) and target.id in ('bl_idname','bl_options')}
        assert 'UNDO' in values['bl_options']
        assert values['bl_idname'].startswith('dbim.')


def test_core_adapter_registers_new_tools_and_keeps_old_scene_key():
    text=(ROOT/'designer_bim_p01/addon.py').read_text(encoding='utf-8')
    assert 'INSTANCE_CLASSES' in text
    assert 'draw_instance_controls' in text
    assert "STATE_KEY='dbim_p01_state'" in text
    assert 'dbim_p01_schema1_backup' in text
    assert 'v0.1.0' not in text


def test_runtime_acceptance_script_covers_new_operations():
    p=ROOT/'scripts/blender_instances_test.py'
    assert p.is_file(), 'real Blender regression script missing'
    text=p.read_text(encoding='utf-8')
    for name in ('bpy.ops.dbim.add_door','bpy.ops.dbim.move_door','bpy.ops.dbim.set_height','bpy.ops.dbim.set_handing','bpy.ops.wm.open_mainfile'):
        assert name in text
    assert 'bpy.app.version == (5,2,2)' in text
