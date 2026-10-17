"""Run only inside Blender 5.2.2. No mocks; writes into the chosen test directory.

blender --background --factory-startup --python scripts/blender_smoke_test.py -- /path/to/output
"""
import json
from pathlib import Path
import sys
import traceback
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from designer_bim_p01 import core, addon


def run(output):
    assert bpy.app.version == (5,2,2), f'Requires exact baseline 5.2.2, got {bpy.app.version_string}'
    addon.register()
    old_scene_names=set(bpy.data.scenes.keys())
    scene=addon.create_demo_scene(bpy.context)
    assert old_scene_names.issubset(set(bpy.data.scenes.keys())), 'Existing scenes were removed'
    assert scene is bpy.context.scene
    owner=scene[addon.OWNER_KEY]
    def obj(key):
        return next(o for o in addon._objects(scene) if o.get('dbim_key')==key and o.get('dbim_owner')==owner)
    assert len(addon.get_model(scene).doors)==3
    addon.select_door(bpy.context,'door-01')
    assert bpy.ops.dbim.set_width('EXEC_DEFAULT',door_id='door-01',width_mm=1200,scope='INSTANCE') == {'FINISHED'}
    m=addon.get_model(scene)
    assert [d.width_mm for d in m.doors.values()]==[1200,900,900]
    assert obj('PLAN.door-01.width-label').data.body=='1200'
    assert obj('ELEVATION.door-01.width-label').data.body=='1200'
    jamb=obj('MODEL.door-01.jamb-left')
    xs=[v.co.x for v in jamb.data.vertices]
    assert abs((max(xs)-min(xs))-.06)<1e-6
    assert bpy.ops.dbim.set_frame('EXEC_DEFAULT',definition_id='door-def-01',frame_mm=80)=={'FINISHED'}
    assert [d.width_mm for d in addon.get_model(scene).doors.values()]==[1200,900,900]
    m=core.add_note(addon.get_model(scene),'door-02','人工说明 / KEEP',note_id='smoke-note')
    addon.apply_model(scene,m)
    note=obj('ELEVATION.note.smoke-note')
    note.data.body='Edited in Blender text object'
    note.location.x+=.123
    harvested=addon.harvest_notes(scene)
    assert harvested.notes['smoke-note'].text=='Edited in Blender text object'
    assert abs(harvested.notes['smoke-note'].position_mm[0]-4623)<1e-3
    addon.apply_model(scene,core.set_width(harvested,'door-02',1100))
    assert note.data.body=='Edited in Blender text object'
    assert core.note_requires_review(addon.get_model(scene),'smoke-note')
    assert 'REVIEW' in obj('ELEVATION.note.smoke-note.review').data.body
    # A rejected update must leave saved state intact.
    before=scene[addon.STATE_KEY]
    try:
        core.set_width(addon.get_model(scene),'door-01',99999)
    except core.ModelError:
        pass
    else:
        raise AssertionError('Invalid width accepted')
    assert scene[addon.STATE_KEY]==before
    # Fault injection on the real adapter: preserve native notes during rollback.
    note.data.body='Native note survives failed rebuild'
    original_render=addon._render_scene
    calls=[0]
    def fail_once(scene_arg,model_arg):
        calls[0]+=1
        original_render(scene_arg,model_arg)
        if calls[0]==1:
            raise RuntimeError('Intentional smoke-test rebuild failure')
    addon._render_scene=fail_once
    try:
        try:
            addon.apply_model(scene,core.set_width(addon.harvest_notes(scene),'door-03',1000))
        except RuntimeError:
            pass
        else:
            raise AssertionError('Injected failure was not raised')
    finally:
        addon._render_scene=original_render
    assert addon.get_model(scene).doors['door-03'].width_mm==900
    assert addon.get_model(scene).notes['smoke-note'].text=='Native note survives failed rebuild'
    assert note.data.body=='Native note survives failed rebuild'
    output.mkdir(parents=True,exist_ok=True)
    filepath=output/'P01_smoke_roundtrip.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(filepath))
    saved=scene[addon.STATE_KEY]
    name=scene.name
    bpy.ops.wm.open_mainfile(filepath=str(filepath))
    scene=bpy.data.scenes[name]
    assert scene[addon.STATE_KEY]==saved
    assert addon.get_model(scene).notes['smoke-note'].text=='Native note survives failed rebuild'
    assert core.note_requires_review(addon.get_model(scene),'smoke-note')
    addon.apply_model(scene,core.set_width(addon.harvest_notes(scene),'door-03',1000))
    assert addon.get_model(scene).doors['door-03'].width_mm==1000
    return {'runtime':bpy.app.version_string,'result':'PASS','checks':[
        'registration','non-destructive demo','instance scope','shared definition',
        'real mesh dimensions','plan and elevation labels','manual text/location harvest',
        'review warning','failed rebuild preserves native notes','invalid edit atomicity','save/reopen','edit after reopen'],
        'not_covered':['mouse drag','Esc cancel','Ctrl+Z undo','three-editor layout','visual quality']}

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
output=Path(args[0]) if args else ROOT/'reports'/'blender-runtime'
try:
    result=run(output)
except Exception:
    result={'runtime':bpy.app.version_string,'result':'FAIL','traceback':traceback.format_exc()}
    output.mkdir(parents=True,exist_ok=True)
    (output/'runtime-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    raise
(output/'runtime-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
