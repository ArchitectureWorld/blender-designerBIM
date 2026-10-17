"""Blender GUI viewport picking and component editing under Xvfb.

Uses real VIEW_3D selection/depth buffer. Not a substitute for Windows UX testing.
"""
import json, os, sys, traceback, subprocess
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from designer_bim_p01 import addon,core
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
OUT=Path(args[0]) if args else ROOT/'reports/gui-components';OUT.mkdir(parents=True,exist_ok=True)
state={'step':0,'checks':[]}


def finish(error=None):
    result={'result':'FAIL' if error else 'PASS','runtime':bpy.app.version_string,'checks':state['checks'],
            'not_covered':['Windows GUI','hardware pointer events','full three-view layout']}
    if error:result['traceback']=error
    (OUT/'gui-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    try:bpy.ops.screen.screenshot(filepath=str(OUT/'component-gui.png'))
    except Exception:pass
    print(json.dumps(result,ensure_ascii=False),flush=True)
    os._exit(1 if error else 0)


def tick():
    try:
        assert bpy.app.version==(5,2,2)
        window=bpy.context.window_manager.windows[0]
        area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
        region=next(r for r in area.regions if r.type=='WINDOW')
        with bpy.context.temp_override(window=window,area=area,region=region):
            context=bpy.context
            step=state['step']
            if step==0:
                addon.register();addon.create_demo_scene(context)
                addon.configure_view(context,area,'MODEL',isolate=True)
                rv=area.spaces.active.region_3d
                rv.view_rotation=Vector((0,-1,0)).to_track_quat('Z','Y')
                rv.view_location=(1.75,0,1.1);rv.view_distance=3.8;rv.view_perspective='ORTHO'
                area.spaces.active.show_region_ui=False
                state['checks'].append('GUI startup and model-only view')
            elif step in (1,2,4):
                point=(1.33,-.101,1.0) if step in (1,4) else (1.388,.48,1.0)
                p=location_3d_to_region_2d(region,area.spaces.active.region_3d,Vector(point))
                assert p is not None
                bpy.ops.object.select_all(action='DESELECT')
                bpy.ops.view3d.select('EXEC_DEFAULT',location=(round(p.x),round(p.y)),extend=False)
                selected=list(context.selected_objects)
                assert len(selected)==1, [(o.name,o.get('dbim_key')) for o in selected]
                key=selected[0].get('dbim_key')
                expected='MODEL.door-01.jamb-left' if step==4 else 'ROOT.door-01'
                assert key==expected,(step,key,expected)
                state['checks'].append('internal part picking' if step==4 else ('single whole-door picking on frame' if step==1 else 'single whole-door picking on leaf'))
            elif step==3:
                assert bpy.ops.dbim.component_shortcut('INVOKE_DEFAULT',action='EDIT')=={'FINISHED'}
                assert context.scene.get('dbim_component_edit')=='door-01'
                state['checks'].append('component shortcut enters internals')
            elif step==5:
                assert bpy.ops.dbim.edit_component_part('EXEC_DEFAULT',part='FRAME',value_mm=80,scope='INSTANCE')=={'FINISHED'}
                assert core.effective_definition(addon.get_model(context.scene),'door-01').frame_section_mm==80
                assert bpy.ops.dbim.component_shortcut('INVOKE_DEFAULT',action='EDIT')=={'FINISHED'}
                assert not context.scene.get('dbim_component_edit')
                assert len(context.selected_objects)==1
                state['checks'].append('GUI part edit/exit restores single selection')
            elif step==6:
                bpy.ops.ed.undo_push(message='component before move')
                assert bpy.ops.dbim.move_door('EXEC_DEFAULT',door_id='door-01',mode='DELTA',offset_mm=100)=={'FINISHED'}
                bpy.ops.ed.undo_push(message='component after move')
                bpy.ops.ed.undo()
                assert addon.get_model(context.scene).doors['door-01'].center_x_mm==1750
                r=next(o for o in context.scene.objects if o.get('dbim_key')=='ROOT.door-01')
                assert abs(r.location.x-1.75)<1e-5 and r.instance_type=='COLLECTION'
                state['checks'].append('actual Blender undo restores root and engineering state')
            elif step==7:
                # Exercise the actual Object Mode keymap, not just operator invocation.
                wid=subprocess.check_output(['xdotool','search','--onlyvisible','--pid',str(os.getpid())],text=True).splitlines()[0]
                subprocess.run(['xdotool','windowfocus','--sync',wid],check=True)
                state['checks'].append('X11 focus set on Blender window')
                subprocess.run(['xdotool','mousemove',str(region.x+region.width//2),
                                str(window.height-(region.y+region.height//2)),
                                'key','Tab'],check=True)
            elif step==8:
                assert context.mode=='OBJECT' and context.scene.get('dbim_component_edit')=='door-01', (context.mode,context.scene.get('dbim_component_edit'))
                state['checks'].append('OS keyboard Tab enters component')
                subprocess.run(['xdotool','key','Tab'],check=True)
            elif step==9:
                assert context.mode=='OBJECT' and not context.scene.get('dbim_component_edit'), (context.mode,context.scene.get('dbim_component_edit'))
                state['checks'].append('OS keyboard Tab exits without entering raw mesh edit')
            elif step==10:
                bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'component-gui.blend'))
                state['checks'].append('GUI scene saved')
            else:
                finish();return None
            state['step']+=1
            area.tag_redraw()
        return 1.0
    except Exception:
        finish(traceback.format_exc());return None

bpy.app.timers.register(tick,first_interval=3.0)
