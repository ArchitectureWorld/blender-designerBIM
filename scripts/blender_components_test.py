"""Real Blender integration for encapsulated components, never a bpy mock."""
import json
from pathlib import Path
import sys
import traceback
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from designer_bim_p01 import addon, core


def run(output):
    assert bpy.app.version == (5,2,2), bpy.app.version_string
    addon.register()
    results=[]
    def check(name,fn):
        try:
            fn(); results.append({'name':name,'result':'PASS'})
        except Exception:
            results.append({'name':name,'result':'FAIL','traceback':traceback.format_exc()})
    def scene():
        return addon.create_demo_scene(bpy.context)
    def objects(s):
        return [o for o in bpy.data.objects if o.get('dbim_owner')==s[addon.OWNER_KEY]]
    def obj(s,key):
        return next(o for o in objects(s) if o.get('dbim_key')==key)
    def roots(s):
        return [o for o in s.objects if o.get('dbim_role')=='root' and o.get('dbim_view')=='MODEL']

    def encapsulation():
        s=scene(); r=obj(s,'ROOT.door-01')
        assert r.instance_type=='COLLECTION' and r.instance_collection is not None, 'Door is not a native collection instance'
        assert len(roots(s))==3
        assert len(r.instance_collection.objects)==4, 'Source must retain frame parts and leaf'
        assert not any(o.get('dbim_door') and o.type=='MESH' for o in s.objects), 'Door pieces are still flat scene objects'
        assert r.instance_collection.name not in s.collection.children
        addon.select_door(bpy.context,'door-01')
        assert list(bpy.context.selected_objects)==[r], 'Selecting one component must not multi-select its internals/2D'
        assert r.get('dbim_definition')=='door-def-01'
        for view in ('PLAN','ELEVATION'):
            proxies=[o for o in s.objects if o.get('dbim_view')==view and o.get('dbim_door')=='door-01' and o.instance_type=='COLLECTION']
            assert len(proxies)==1 and proxies[0].get('dbim_definition')=='door-def-01'
        bpy.context.view_layer.update()
        # Depsgraph iterator entries are ephemeral RNA wrappers, not persistent objects.
        count=sum(1 for i in bpy.context.evaluated_depsgraph_get().object_instances
                  if i.is_instance and i.parent and i.parent.original==r)
        assert count>=4, 'Instance source does not render through dependency graph'
    check('one scene component with native instanced geometry and 2D proxies',encapsulation)

    def editing():
        s=scene(); r=obj(s,'ROOT.door-01')
        assert bpy.ops.dbim.enter_component('EXEC_DEFAULT',door_id='door-01')=={'FINISHED'}
        part=obj(s,'MODEL.door-01.jamb-left')
        assert part.name in s.objects and not part.hide_select
        assert r.hide_get(), 'Normal proxy duplicates edit geometry'
        assert not any(o.get('dbim_door')=='door-02' and o.type=='MESH' for o in s.objects)
        for o in bpy.context.selected_objects:o.select_set(False)
        part.select_set(True); bpy.context.view_layer.objects.active=part
        assert bpy.ops.dbim.edit_component_part('EXEC_DEFAULT',part='FRAME',value_mm=80,scope='INSTANCE')=={'FINISHED'}
        m=addon.get_model(s)
        assert core.effective_definition(m,'door-01').frame_section_mm==80
        assert core.effective_definition(m,'door-02').frame_section_mm==60
        assert m.doors['door-01'].definition_id=='door-def-01'
        assert bpy.ops.dbim.exit_component('EXEC_DEFAULT')=={'FINISHED'}
        assert part.name not in s.objects and not r.hide_get()
        assert list(bpy.context.selected_objects)==[r]
        assert bpy.ops.dbim.enter_component('EXEC_DEFAULT',door_id='door-02')=={'FINISHED'}
        assert bpy.ops.dbim.edit_component_part('EXEC_DEFAULT',part='FRAME',value_mm=70,scope='DEFINITION')=={'FINISHED'}
        assert bpy.ops.dbim.exit_component('EXEC_DEFAULT')=={'FINISHED'}
        m=addon.get_model(s)
        assert core.effective_definition(m,'door-01').frame_section_mm==80
        assert core.effective_definition(m,'door-03').frame_section_mm==70
    check('enter/select/edit local vs shared/exit preserves true component identity',editing)

    def lifecycle():
        s=scene(); before=set(addon.get_model(s).doors)
        assert bpy.ops.dbim.add_door('EXEC_DEFAULT',mode='COPY',source_id='door-01',center_x_mm=3000)=={'FINISHED'}
        did=next(iter(set(addon.get_model(s).doors)-before))
        r=obj(s,'ROOT.'+did); pointer=r.as_pointer()
        assert bpy.ops.dbim.move_door('EXEC_DEFAULT',door_id=did,mode='DELTA',offset_mm=200)=={'FINISHED'}
        assert obj(s,'ROOT.'+did).as_pointer()==pointer
        assert abs(r.location.x-3.2)<1e-5
        for _ in range(3):addon.apply_model(s,addon.harvest_notes(s))
        assert len(roots(s))==4
        assert len({o.get('dbim_key') for o in objects(s)})==len(objects(s))
        m=core.add_note(addon.get_model(s),did,'delete only with consent',note_id='delete-note')
        m=core.add_note(m,'door-02','keep',note_id='keep-note');addon.apply_model(s,m)
        saved=s[addon.STATE_KEY]
        try:bpy.ops.dbim.delete_door('EXEC_DEFAULT',door_id=did,delete_notes=False)
        except RuntimeError:pass
        assert s[addon.STATE_KEY]==saved
        assert bpy.ops.dbim.delete_door('EXEC_DEFAULT',door_id=did,delete_notes=True)=={'FINISHED'}
        assert not any(o.get('dbim_door')==did for o in objects(s))
        assert not any(c.get('dbim_owner')==s[addon.OWNER_KEY] and c.get('dbim_door')==did for c in bpy.data.collections)
        assert set(addon.get_model(s).notes)=={'keep-note'}
        assert not any(t.door_id==did for t in __import__('designer_bim_p01.geometry',fromlist=['drawing']).drawing(addon.get_model(s),'PLAN').texts)
    check('copy/move/refresh/delete cleans all representations, protects unrelated notes',lifecycle)

    def empty_wall():
        s=scene()
        for did in tuple(addon.get_model(s).doors):
            assert bpy.ops.dbim.delete_door('EXEC_DEFAULT',door_id=did,delete_notes=True)=={'FINISHED'}
        assert not roots(s)
        assert bpy.ops.dbim.add_door('EXEC_DEFAULT',mode='NEW',center_x_mm=1750)=={'FINISHED'}
        assert len(roots(s))==1
    check('deleting the last door does not prevent adding a new component',empty_wall)

    def guard():
        s=scene(); bpy.ops.dbim.enter_component('EXEC_DEFAULT',door_id='door-01')
        mesh=obj(s,'MODEL.door-01.leaf').data
        mesh.vertices[0].co.x+=.05; mesh.update()
        saved=s[addon.STATE_KEY]
        try:addon.apply_model(s,addon.get_model(s))
        except core.ModelError:pass
        else:raise AssertionError('Unsupported hand mesh edit was silently erased')
        assert s[addon.STATE_KEY]==saved
        mesh.vertices[0].co.x-=.05; mesh.update()
        bpy.ops.dbim.exit_component('EXEC_DEFAULT')
    check('unsupported raw mesh edit is rejected rather than lost',guard)

    def roundtrip():
        s=scene(); name=s.name
        legacy=(ROOT/'tests/fixtures/schema1_notes.json').read_text()
        s[addon.STATE_KEY]=legacy
        addon.apply_model(s,core.loads(legacy))
        assert s['dbim_p01_schema1_backup']==legacy
        assert not core.note_requires_review(addon.get_model(s),'fresh')
        assert core.note_requires_review(addon.get_model(s),'stale')
        # Simulate a v0.2 flat scene, including a native note edit.
        r=obj(s,'ROOT.door-01'); payload=r.instance_collection
        r.instance_type='NONE';r.instance_collection=None
        model_collection=next(c for c in s.collection.children if c.get('dbim_view')=='MODEL')
        for o in list(payload.objects):
            model_collection.objects.link(o);payload.objects.unlink(o)
        note=obj(s,'ELEVATION.note.fresh');note.data.body='native edit before migration'
        addon.apply_model(s,addon.harvest_notes(s))
        assert obj(s,'ROOT.door-01').instance_type=='COLLECTION'
        assert addon.get_model(s).notes['fresh'].text=='native edit before migration'
        assert bpy.ops.dbim.enter_component('EXEC_DEFAULT',door_id='door-01')=={'FINISHED'}
        assert bpy.ops.dbim.edit_component_part('EXEC_DEFAULT',part='LEAF',value_mm=50,scope='INSTANCE')=={'FINISHED'}
        output.mkdir(parents=True,exist_ok=True)
        path=output/'component_roundtrip.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(path))
        saved=s[addon.STATE_KEY]
        bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.data.scenes[name]
        assert s[addon.STATE_KEY]==saved
        assert not s.get('dbim_component_edit',''), 'Reopened project should start closed, not expose internal parts'
        assert not any(o.get('dbim_door') and o.type=='MESH' for o in s.objects)
        assert core.effective_definition(addon.get_model(s),'door-01').leaf_thickness_mm==50
        assert bpy.ops.dbim.set_width('EXEC_DEFAULT',door_id='door-01',width_mm=1200)=={'FINISHED'}
        assert addon.get_model(s).notes['fresh'].text=='native edit before migration'
        assert obj(s,'PLAN.door-01.width-label').data.body=='1200'
    check('flat-source migration, manual notes, scoped edits and save/reopen',roundtrip)
    addon.unregister()
    result={'runtime':bpy.app.version_string,'checks':results,'result':'FAIL' if any(r['result']=='FAIL' for r in results) else 'PASS',
            'not_covered':['Windows interactive user acceptance','full arbitrary mesh authoring','IFC production']}
    output.mkdir(parents=True,exist_ok=True)
    (output/'components-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result['result']!='PASS':raise AssertionError('Component integration failed')

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
run(Path(args[0]) if args else ROOT/'reports/blender-components')
