"""Actual Blender 5.2.2 state/geometry/serialization acceptance, not mocked bpy.

blender -b --factory-startup --python-exit-code 1 --python scripts/blender_instances_test.py -- OUTPUT
Interactive dialog/mouse/undo/visual layout still require separate GUI acceptance.
"""
import json
from pathlib import Path
import sys
import traceback
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from designer_bim_p01 import addon,core,geometry


def run(output):
    assert bpy.app.version == (5,2,2), bpy.app.version_string
    addon.register()
    original_scenes=set(bpy.data.scenes.keys())
    scene=addon.create_demo_scene(bpy.context)
    name=scene.name
    assert original_scenes.issubset(bpy.data.scenes.keys())
    legacy=(ROOT/'tests/fixtures/schema1_notes.json').read_text(encoding='utf-8')
    scene[addon.STATE_KEY]=legacy
    addon.apply_model(scene,core.loads(legacy))
    assert scene['dbim_p01_schema1_backup']==legacy
    assert not core.note_requires_review(addon.get_model(scene),'fresh')
    assert core.note_requires_review(addon.get_model(scene),'stale')
    before=set(addon.get_model(scene).doors)
    assert bpy.ops.dbim.add_door('EXEC_DEFAULT',mode='COPY',source_id='door-01',center_x_mm=3000)=={'FINISHED'}
    m=addon.get_model(scene)
    did=next(iter(set(m.doors)-before))
    assert m.doors[did].tag=='D04' and m.doors[did].definition_id=='door-def-01'
    assert len(m.notes)==2
    assert bpy.ops.dbim.move_door('EXEC_DEFAULT',door_id=did,mode='DELTA',offset_mm=200)=={'FINISHED'}
    assert addon.get_model(scene).doors[did].center_x_mm==3200
    assert bpy.ops.dbim.set_height('EXEC_DEFAULT',door_id=did,height_mm=2400,scope='INSTANCE')=={'FINISHED'}
    assert bpy.ops.dbim.set_handing('EXEC_DEFAULT',door_id=did,handing='RIGHT')=={'FINISHED'}
    m=addon.get_model(scene)
    assert m.doors[did].height_mm==2400 and m.doors[did].handing=='RIGHT'
    assert m.doors['door-01'].height_mm==2100
    owner=scene[addon.OWNER_KEY]
    def obj(key):
        return next(o for o in addon._objects(scene) if o.get('dbim_owner')==owner and o.get('dbim_key')==key)
    assert obj('ELEVATION.'+did+'.height-label').data.body=='H 2400'
    expected=next(p for p in geometry.model_parts(m) if p.key==did+'.leaf')
    leaf=obj('MODEL.'+did+'.leaf')
    for vertex,xyz in zip(leaf.data.vertices,expected.vertices_mm):
        assert max(abs(a-b*.001) for a,b in zip(vertex.co,xyz))<1e-5
    saved=scene[addon.STATE_KEY]
    try:
        bpy.ops.dbim.move_door('EXEC_DEFAULT',door_id=did,mode='ABSOLUTE',center_x_mm=4500)
    except RuntimeError:
        pass  # Blender raises on report(ERROR); the state must still be identical.
    assert scene[addon.STATE_KEY]==saved
    assert bpy.ops.dbim.add_door('EXEC_DEFAULT',mode='NEW',source_id=did,center_x_mm=570,width_mm=900,height_mm=2300,handing='RIGHT')=={'FINISHED'}
    m=addon.get_model(scene)
    assert len(m.doors)==5 and len(m.definitions)==1
    m=core.add_note(m,did,'Keep after placement',note_id='new-note')
    addon.apply_model(scene,m)
    text_obj=obj('ELEVATION.note.new-note')
    text_obj.data.body='Edited native text survives move'
    text_obj.location.x+=.1
    assert bpy.ops.dbim.move_door('EXEC_DEFAULT',door_id=did,mode='DELTA',offset_mm=-100)=={'FINISHED'}
    m=addon.get_model(scene)
    assert m.notes['new-note'].text=='Edited native text survives move'
    assert core.note_requires_review(m,'new-note')
    output.mkdir(parents=True,exist_ok=True)
    path=output/'P01_v020_roundtrip.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    saved=scene[addon.STATE_KEY]
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene=bpy.data.scenes[name]
    assert scene[addon.STATE_KEY]==saved
    m=addon.get_model(scene)
    widths={key:d.width_mm for key,d in m.doors.items()}
    assert bpy.ops.dbim.set_frame('EXEC_DEFAULT',definition_id='door-def-01',frame_mm=80)=={'FINISHED'}
    m=addon.get_model(scene)
    assert widths=={key:d.width_mm for key,d in m.doors.items()}
    assert m.doors[did].height_mm==2400 and m.doors[did].handing=='RIGHT'
    (output/'roundtrip.svg').write_text(geometry.svg_document(m),encoding='utf-8')
    addon.unregister()
    return {'runtime':bpy.app.version_string,'result':'PASS','checks':[
        'exact Blender baseline','registered operators','legacy migration and backup','legacy review flags',
        'copy ID and definition','new door','absolute and relative position','invalid move atomicity',
        'height dimension text','handed mesh coordinates','native annotation harvest',
        'save/reopen','shared edit after reopen','unregister'],
        'not_covered':['interactive dialogs','mouse dragging','Ctrl+Z','visual three-view layout']}


args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
output=Path(args[0]) if args else ROOT/'reports/blender-instances'
try:
    result=run(output)
except Exception:
    output.mkdir(parents=True,exist_ok=True)
    (output/'instances-result.json').write_text(json.dumps({'runtime':bpy.app.version_string,'result':'FAIL','traceback':traceback.format_exc()},ensure_ascii=False,indent=2),encoding='utf-8')
    raise
(output/'instances-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
