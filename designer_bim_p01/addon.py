# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender 5.2.2 adapter for a deliberately bounded door-interaction prototype.

Source of truth: validated versioned JSON on the prototype scene. Geometry,
vector drawings and generated labels are projections, not independent objects
with independently editable dimensions. Manual note text/positions are harvested
before regeneration and before saving. This module never deletes other scenes,
accesses the network, or runs user-provided code.
"""
import json
import math
import os
from pathlib import Path
from uuid import uuid4

import bpy
from bpy.app.handlers import persistent
from bpy.props import EnumProperty, FloatProperty, StringProperty
from bpy.types import GizmoGroup, Operator, Panel
from bpy_extras import view3d_utils
from bpy_extras.io_utils import ExportHelper
from mathutils import Matrix, Vector
from mathutils.geometry import intersect_line_plane

from . import core, geometry, interaction, component_scene
from .instance_tools import INSTANCE_CLASSES, draw_instance_controls
from .component_tools import COMPONENT_CLASSES, draw_component_controls, register_keymaps, unregister_keymaps

TARGET_VERSION=(5,2,2)
STATE_KEY='dbim_p01_state'
OWNER_KEY='dbim_p01_owner'
ERROR_KEY='dbim_p01_error'
OFFSETS={'PLAN':Vector((0,8,0)), 'ELEVATION':Vector((0,-8,0))}
_AREA_MODES={}
_BUSY=False
_FONT=None
_COLORS={'wall':(.68,.73,.78,1),'frame':(.10,.25,.38,1),'leaf':(.69,.52,.31,1),
         'manual':(.49,.29,.10,1),'review':(.82,.20,.07,1),'line':(.045,.07,.10,1)}


def get_model(scene):
    if STATE_KEY not in scene:
        raise core.ModelError('请先创建 P01 原型场景')
    return core.loads(scene[STATE_KEY])


def active_door_id(context):
    obj=context.active_object
    if obj and obj.get('dbim_owner')==context.scene.get(OWNER_KEY):
        door_id=obj.get('dbim_door','')
        if door_id:
            return door_id
    return context.scene.get('dbim_active_door','door-01')


def selected_door_ids(context):
    owner=context.scene.get(OWNER_KEY)
    return tuple(dict.fromkeys(o.get('dbim_door') for o in context.selected_objects
                              if o.get('dbim_owner')==owner and o.get('dbim_door')))


def _objects(scene):
    # Include private collection payloads, not only directly linked scene objects.
    owner=scene.get(OWNER_KEY)
    return [o for o in bpy.data.objects if owner and o.get('dbim_owner')==owner]


def _scene_objects(scene):
    owner=scene.get(OWNER_KEY)
    return [o for o in scene.objects if owner and o.get('dbim_owner')==owner]


def _font():
    global _FONT
    if _FONT is not None:
        try:
            _=_FONT.name
            return _FONT
        except ReferenceError:
            _FONT=None
    candidates=[
        os.path.join(os.environ.get('WINDIR','C:/Windows'),'Fonts','msyh.ttc'),
        '/System/Library/Fonts/PingFang.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
    ]
    for path in candidates:
        if Path(path).is_file():
            try:
                _FONT=bpy.data.fonts.load(path,check_existing=True)
                return _FONT
            except (RuntimeError,OSError):
                pass
    return None


def _collection(scene,view):
    for c in scene.collection.children:
        if c.get('dbim_owner')==scene[OWNER_KEY] and c.get('dbim_view')==view:
            return c
    c=bpy.data.collections.new(f'P01 | {view}')
    c['dbim_owner']=scene[OWNER_KEY]
    c['dbim_view']=view
    scene.collection.children.link(c)
    return c


class _Builder:
    def __init__(self,scene):
        self.scene=scene
        self.owner=scene[OWNER_KEY]
        self.existing={}
        for o in _objects(scene):
            key=o.get('dbim_key')
            if key in self.existing:
                raise core.ModelError('检测到原生复制产生的重复 ID。P01 不支持 Shift+D 复制生成物；请撤销复制。')
            self.existing[key]=o
        self.used=set()
        self.collections={view:_collection(scene,view) for view in ('MODEL','PLAN','ELEVATION')}

    def obj(self,key,view,kind,role,door_id=''):
        o=self.existing.get(key)
        if o is None:
            if kind=='MESH':
                data=bpy.data.meshes.new('P01 '+key)
            elif kind=='CURVE':
                data=bpy.data.curves.new('P01 '+key,'CURVE')
            elif kind=='FONT':
                data=bpy.data.curves.new('P01 '+key,'FONT')
            else:
                data=None
            o=bpy.data.objects.new('P01 '+key,data)
            self.collections[view].objects.link(o)
        if o.type!=kind:
            raise core.ModelError('生成物类型已被改变，请撤销修改后重试：'+key)
        o['dbim_owner']=self.owner
        o['dbim_key']=key
        o['dbim_view']=view
        o['dbim_role']=role
        o['dbim_door']=door_id
        o.lock_location=(True,True,True)
        o.lock_rotation=(True,True,True)
        o.lock_scale=(True,True,True)
        o.hide_select=(not door_id and role!='root') or role in ('title','subtitle','review','dimension')
        component_scene.route_object(self.scene,o,self.collections[view],view,door_id,role)
        self.used.add(key)
        return o

    def finish(self):
        for key,o in self.existing.items():
            if key not in self.used:
                # Only our own generated object; never remove unrelated objects.
                data=o.data
                bpy.data.objects.remove(o,do_unlink=True)
                if data and data.users==0:
                    if isinstance(data,bpy.types.Mesh):
                        bpy.data.meshes.remove(data)
                    elif isinstance(data,bpy.types.Curve):
                        bpy.data.curves.remove(data)


def _render_scene(scene,m):
    b=_Builder(scene)
    for d in m.doors.values():
        for view in ('MODEL','PLAN','ELEVATION'):
            component_scene.setup_root(b,d,view,Vector((0,0,0)) if view=='MODEL' else OFFSETS[view])
    for p in geometry.model_parts(m):
        key='MODEL.'+p.key
        o=b.obj(key,'MODEL','MESH',p.role,p.door_id)
        # Never apply object scaling to a door. Coordinates come from its parameters.
        o.data.clear_geometry()
        o.data.from_pydata([tuple(c*.001 for c in v) for v in p.vertices_mm],[],p.faces)
        o.data.update()
        o.location=(0,0,0)
        o.rotation_euler=(0,0,0)
        o.scale=(1,1,1)
        o.color=_COLORS[p.role]
        o['dbim_generated_fingerprint']=component_scene.mesh_fingerprint(o)
        if p.door_id:
            o['dbim_definition']=m.doors[p.door_id].definition_id
    font=_font()
    for view in ('PLAN','ELEVATION'):
        offset=OFFSETS[view]
        dr=geometry.drawing(m,view)
        for l in dr.lines:
            o=b.obj(view+'.'+l.key,view,'CURVE',l.role,l.door_id)
            c=o.data
            c.dimensions='3D'
            c.resolution_u=1
            c.bevel_depth=max(.0005,l.width_mm*.001/2)
            c.bevel_resolution=0
            c.splines.clear()
            spl=c.splines.new('POLY')
            spl.points.add(len(l.points)-1)
            for pt,coord in zip(spl.points,l.points):
                pt.co=(coord[0]*.001,coord[1]*.001,.012,1)
            spl.use_cyclic_u=l.closed
            o.location=offset
            o.rotation_euler=(0,0,0)
            o.scale=(1,1,1)
            o.color=_COLORS['manual'] if l.role=='annotation' else _COLORS['line']
        for t in dr.texts:
            o=b.obj(view+'.'+t.key,view,'FONT',t.role,t.door_id)
            c=o.data
            c.body=t.text
            c.size=t.size_mm*.001
            c.align_x=t.align
            c.align_y='BOTTOM_BASELINE'
            c.extrude=0
            if font:
                c.font=font
            o.location=offset+Vector((t.position_mm[0]*.001,t.position_mm[1]*.001,.025))
            o.rotation_euler=(0,0,0)
            o.scale=(1,1,1)
            o.color=_COLORS.get(t.role,_COLORS['line'])
            if t.role=='manual':
                o['dbim_note']=t.note_id
                o.lock_location=(False,False,True)
                o.hide_select=False
    b.finish()
    component_scene.sync_edit_visibility(scene,m,b.collections)
    _refresh_local_visibility(scene)


def harvest_notes(scene):
    """Capture native text edits and XY translation without acknowledging review."""
    m=get_model(scene)
    for o in _objects(scene):
        if o.get('dbim_role')!='manual' or o.type!='FONT':
            continue
        nid=o.get('dbim_note','')
        if nid not in m.notes:
            continue
        offset=OFFSETS[m.notes[nid].view]
        # Blender float storage has limited precision; avoid artificial revisions.
        pos=(round((o.location.x-offset.x)*1000,3),round((o.location.y-offset.y)*1000,3))
        m=core.edit_note(m,nid,text=o.data.body,position_mm=pos)
    return m


def apply_model(scene,m):
    """Commit JSON only after a successful rebuild; restore old output on failure."""
    global _BUSY
    core.validate(m)
    component_scene.check_generated_geometry(_objects(scene))
    old=scene.get(STATE_KEY)
    # Snapshot manual text/location too: rolling back to stale JSON would erase
    # a native note edit made immediately before an unsuccessful rebuild.
    rollback_model=harvest_notes(scene) if old else None
    _BUSY=True
    try:
        _render_scene(scene,m)
        if old:
            old_schema=json.loads(old).get('schema_version')
            # Preserve dbim_p01_schema1_backup and dbim_p01_schema2_backup independently.
            if old_schema in (1,2):
                backup_key=f'dbim_p01_schema{old_schema}_backup'
                if backup_key not in scene:scene[backup_key]=old
        scene[STATE_KEY]=core.dumps(m)
        scene[ERROR_KEY]=''
    except Exception as exc:
        scene[ERROR_KEY]=str(exc)
        if rollback_model is not None:
            try:
                _render_scene(scene,rollback_model)
                scene[STATE_KEY]=core.dumps(rollback_model)
            except Exception:
                pass  # Keep original serialized state available for recovery.
        raise
    finally:
        _BUSY=False
    for wm in bpy.data.window_managers:
        for window in wm.windows:
            if window.scene==scene:
                for area in window.screen.areas:
                    area.tag_redraw()


def create_demo_scene(context):
    # A new scene, never factory reset or scene deletion.
    scene=bpy.data.scenes.new('DesignerBIM P01 — Door Lab')
    scene[OWNER_KEY]=str(uuid4())
    scene['dbim_target_blender']='5.2.2'
    scene['dbim_active_door']='door-01'
    scene.unit_settings.system='METRIC'
    scene.unit_settings.scale_length=1
    scene.unit_settings.length_unit='MILLIMETERS'
    scene.world=bpy.data.worlds.new('P01 World')
    scene.world.color=(.8,.8,.8)
    if context.window:
        context.window.scene=scene
    apply_model(scene,core.demo_model())
    if context.window:
        select_door(context,'door-01')
        area=context.area if context.area and context.area.type=='VIEW_3D' else None
        if area:
            configure_view(context,area,'MODEL',isolate=False)
    return scene


def select_door(context,door_id):
    m=get_model(context.scene)
    if door_id not in m.doors:
        raise core.ModelError('Unknown door')
    if context.scene.get(component_scene.EDIT_KEY):
        component_scene.check_generated_geometry(_objects(context.scene))
        context.scene[component_scene.EDIT_KEY]=''
        apply_model(context.scene,harvest_notes(context.scene))
    context.view_layer.update()
    for o in context.selected_objects:o.select_set(False)
    mode=area_mode(context)
    root=next((o for o in _scene_objects(context.scene) if o.get('dbim_door')==door_id
               and o.get('dbim_role')=='root' and o.get('dbim_view')==mode),None)
    if root:
        root.select_set(True)
        context.view_layer.objects.active=root
    context.scene['dbim_active_door']=door_id


def area_mode(context):
    if not context.area or context.area.type!='VIEW_3D':
        return 'MODEL'
    key=context.area.as_pointer()
    if key in _AREA_MODES:
        return _AREA_MODES[key]
    y=context.space_data.region_3d.view_location.y
    if y>4:
        return 'PLAN'
    if y<-4:
        return 'ELEVATION'
    return 'MODEL'


def _refresh_local_visibility(scene):
    for wm in bpy.data.window_managers:
        for window in wm.windows:
            if window.scene!=scene:
                continue
            for area in window.screen.areas:
                if area.type!='VIEW_3D':
                    continue
                space=area.spaces.active
                if not space.local_view:
                    continue
                mode=_AREA_MODES.get(area.as_pointer())
                if mode is None:
                    y=space.region_3d.view_location.y
                    mode='PLAN' if y>4 else ('ELEVATION' if y<-4 else 'MODEL')
                for o in _scene_objects(scene):
                    o.local_view_set(space,o.get('dbim_view')==mode)


def configure_view(context,area,mode,isolate=True):
    _AREA_MODES[area.as_pointer()]=mode
    space=area.spaces.active
    space.show_region_ui=(mode=='MODEL')
    space.show_gizmo=True
    space.overlay.show_floor=False
    space.overlay.show_axis_x=False
    space.overlay.show_axis_y=False
    space.shading.type='SOLID'
    space.shading.color_type='OBJECT'
    space.shading.light='STUDIO' if mode=='MODEL' else 'FLAT'
    space.shading.show_shadows=(mode=='MODEL')
    space.shading.background_type='WORLD' if mode=='MODEL' else 'VIEWPORT'
    space.shading.background_color=(.94,.95,.96)
    rv=space.region_3d
    if mode=='MODEL':
        rv.view_rotation=Vector((3,-9,5)).to_track_quat('Z','Y')
        rv.view_location=(4.5,0,1.4)
        rv.view_distance=12
        rv.view_perspective='PERSP'
    else:
        from mathutils import Quaternion
        rv.view_rotation=Quaternion((1,0,0,0))
        rv.view_location=(4.5,8.5,0) if mode=='PLAN' else (4.5,-6.6,0)
        rv.view_distance=11
        rv.view_perspective='ORTHO'
    if isolate:
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        if region:
            selected=list(context.selected_objects)
            active=context.view_layer.objects.active
            try:
                with context.temp_override(area=area,region=region):
                    if not space.local_view:
                        for o in context.selected_objects:
                            o.select_set(False)
                        candidate=next((o for o in _scene_objects(context.scene) if o.get('dbim_view')==mode and not o.hide_select),None)
                        if candidate:
                            candidate.select_set(True)
                            context.view_layer.objects.active=candidate
                            bpy.ops.view3d.localview(frame_selected=False)
                    _refresh_local_visibility(context.scene)
            finally:
                for o in context.selected_objects:
                    o.select_set(False)
                for o in selected:
                    o.select_set(True)
                context.view_layer.objects.active=active
    area.tag_redraw()


def setup_three_views(context):
    if not context.window or not context.screen:
        raise core.ModelError('三视图排布需要 Blender 图形界面')
    areas=[a for a in context.screen.areas if a.type=='VIEW_3D']
    if not areas:
        raise core.ModelError('当前工作区没有三维视图')
    if len(areas)<3:
        base=max(areas,key=lambda a:a.width*a.height)
        x0,y0,w,h=base.x,base.y,base.width,base.height
        def within(a):
            return a.type=='VIEW_3D' and x0<=a.x+a.width/2<=x0+w and y0<=a.y+a.height/2<=y0+h
        with context.temp_override(area=base):
            bpy.ops.screen.area_split(direction='VERTICAL',factor=.56)
        pair=[a for a in context.screen.areas if within(a)]
        right=max(pair,key=lambda a:a.x)
        with context.temp_override(area=right):
            bpy.ops.screen.area_split(direction='HORIZONTAL',factor=.40)
        areas=[a for a in context.screen.areas if within(a)]
    if len(areas)<3:
        raise core.ModelError('自动分屏未完成；可用“当前视图”按钮分别切换平面／立面')
    chosen=sorted(areas,key=lambda a:(a.x,-a.y))[:3]
    left=min(chosen,key=lambda a:a.x)
    others=[a for a in chosen if a!=left]
    top=max(others,key=lambda a:a.y)
    bottom=min(others,key=lambda a:a.y)
    for area,mode in ((left,'MODEL'),(top,'ELEVATION'),(bottom,'PLAN')):
        configure_view(context,area,mode)


class _SceneOperator:
    @classmethod
    def poll(cls,context):
        return context.scene is not None and STATE_KEY in context.scene and context.mode=='OBJECT'

    def fail(self,exc):
        self.report({'ERROR'},str(exc))
        return {'CANCELLED'}


class DBIM_OT_create_demo(Operator):
    bl_idname='dbim.create_demo'
    bl_label='创建原型场景（不删除已有场景）'
    bl_description='新建一面墙和三樘共享定义的门，并生成关联平面、立面'
    bl_options={'REGISTER','UNDO'}

    def execute(self,context):
        try:
            create_demo_scene(context)
        except Exception as exc:
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}
        self.report({'INFO'},'已创建独立场景；下一步点击“三视图排布”')
        return {'FINISHED'}


class DBIM_OT_select_door(_SceneOperator,Operator):
    bl_idname='dbim.select_door'
    bl_label='选择门实例'
    door_id: StringProperty()

    def execute(self,context):
        try:
            select_door(context,self.door_id)
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_set_width(_SceneOperator,Operator):
    bl_idname='dbim.set_width'
    bl_label='修改门洞宽度'
    bl_description='改变工程参数，而不是缩放网格；门中心位置保持不动'
    bl_options={'REGISTER','UNDO'}
    door_id: StringProperty(options={'HIDDEN'})
    width_mm: FloatProperty(name='门洞宽度 (mm)',default=900,min=300,max=6000,precision=1)
    scope: EnumProperty(name='作用范围',items=[
        ('INSTANCE','只改当前实例','不修改其他门'),
        ('SELECTED','一次性修改选中实例','不创建新的联动关系'),
        ('DEFINITION','本定义的全部实例','统一门洞宽度，需明确选择'),
    ],default='INSTANCE')
    selected_json: StringProperty(default='[]',options={'HIDDEN'})

    def invoke(self,context,event):
        try:
            self.door_id=active_door_id(context)
            self.width_mm=get_model(context.scene).doors[self.door_id].width_mm
            self.selected_json=json.dumps(selected_door_ids(context))
            return context.window_manager.invoke_props_dialog(self,width=420)
        except Exception as exc:
            return self.fail(exc)

    def draw(self,context):
        layout=self.layout
        layout.prop(self,'scope')
        layout.prop(self,'width_mm')
        try:
            m=get_model(context.scene)
            ids=core.affected_ids(m,self.door_id,self.scope,json.loads(self.selected_json))
            layout.label(text='影响：'+', '.join(m.doors[k].tag for k in ids))
        except core.ModelError as exc:
            layout.label(text=str(exc),icon='ERROR')
        layout.label(text='中心固定；门框截面不随宽度缩放。')

    def execute(self,context):
        try:
            m=harvest_notes(context.scene)
            door=self.door_id or active_door_id(context)
            ids=json.loads(self.selected_json)
            if not ids and self.scope=='SELECTED':
                ids=selected_door_ids(context)
            new=core.set_width(m,door,self.width_mm,scope=self.scope,selected_ids=ids)
            apply_model(context.scene,new)
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_set_frame(_SceneOperator,Operator):
    bl_idname='dbim.set_frame'
    bl_label='统一修改共享门框截面'
    bl_options={'REGISTER','UNDO'}
    definition_id: StringProperty(options={'HIDDEN'})
    frame_mm: FloatProperty(name='门框截面 (mm)',default=60,min=15,max=150,precision=1)

    def invoke(self,context,event):
        try:
            m=get_model(context.scene)
            self.definition_id=m.doors[active_door_id(context)].definition_id
            self.frame_mm=m.definitions[self.definition_id].frame_section_mm
            return context.window_manager.invoke_props_dialog(self,width=420)
        except Exception as exc:
            return self.fail(exc)

    def draw(self,context):
        self.layout.prop(self,'frame_mm')
        m=get_model(context.scene)
        tags=[d.tag for d in m.doors.values() if d.definition_id==self.definition_id]
        self.layout.label(text='影响共享定义的全部门：'+', '.join(tags))
        self.layout.label(text='保留各门已设定的门洞宽度。')

    def execute(self,context):
        try:
            m=harvest_notes(context.scene)
            def_id=self.definition_id or m.doors[active_door_id(context)].definition_id
            apply_model(context.scene,core.set_frame_section(m,def_id,self.frame_mm))
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_add_note(_SceneOperator,Operator):
    bl_idname='dbim.add_note'
    bl_label='添加人工说明'
    bl_options={'REGISTER','UNDO'}
    door_id: StringProperty(options={'HIDDEN'})
    text: StringProperty(name='说明内容',default='收口需结合现场复核',maxlen=4000)
    view: EnumProperty(name='所属视图',items=[('ELEVATION','立面',''),('PLAN','平面','')],default='ELEVATION')

    def invoke(self,context,event):
        self.door_id=active_door_id(context)
        return context.window_manager.invoke_props_dialog(self,width=480)

    def execute(self,context):
        try:
            m=harvest_notes(context.scene)
            m=core.add_note(m,self.door_id or active_door_id(context),self.text,view=self.view)
            apply_model(context.scene,m)
            self.report({'INFO'},'人工说明已关联；后续相关几何变化将提示复核')
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_edit_note(_SceneOperator,Operator):
    bl_idname='dbim.edit_note'
    bl_label='编辑人工说明'
    bl_options={'REGISTER','UNDO'}
    note_id: StringProperty(options={'HIDDEN'})
    text: StringProperty(name='说明内容',maxlen=4000)

    def invoke(self,context,event):
        try:
            m=harvest_notes(context.scene)
            self.text=m.notes[self.note_id].text
            return context.window_manager.invoke_props_dialog(self,width=480)
        except Exception as exc:
            return self.fail(exc)

    def execute(self,context):
        try:
            apply_model(context.scene,core.edit_note(harvest_notes(context.scene),self.note_id,text=self.text))
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_confirm_note(_SceneOperator,Operator):
    bl_idname='dbim.confirm_note'
    bl_label='确认已复核此说明'
    bl_options={'REGISTER','UNDO'}
    note_id: StringProperty(options={'HIDDEN'})

    def execute(self,context):
        try:
            apply_model(context.scene,core.confirm_note(harvest_notes(context.scene),self.note_id))
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_refresh(_SceneOperator,Operator):
    bl_idname='dbim.refresh'
    bl_label='同步说明并重建表达'
    bl_options={'REGISTER','UNDO'}

    def execute(self,context):
        if context.mode!='OBJECT':
            self.report({'WARNING'},'先退出编辑模式，再刷新')
            return {'CANCELLED'}
        try:
            apply_model(context.scene,harvest_notes(context.scene))
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_layout(_SceneOperator,Operator):
    bl_idname='dbim.layout'
    bl_label='三视图排布（调整当前工作区）'
    bl_description='左侧三维；右上立面；右下平面。只在点击后调整当前工作区'

    def invoke(self,context,event):
        return context.window_manager.invoke_confirm(self,event)

    def execute(self,context):
        try:
            setup_three_views(context)
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_view(_SceneOperator,Operator):
    bl_idname='dbim.view'
    bl_label='切换当前视图'
    mode: EnumProperty(items=[('MODEL','三维',''),('PLAN','平面',''),('ELEVATION','立面','')])

    def execute(self,context):
        try:
            if not context.area or context.area.type!='VIEW_3D':
                raise core.ModelError('请从三维视图运行')
            configure_view(context,context.area,self.mode)
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_export_svg(_SceneOperator,Operator,ExportHelper):
    bl_idname='dbim.export_svg'
    bl_label='导出 A3 矢量测试图（SVG）'
    filename_ext='.svg'
    filter_glob: StringProperty(default='*.svg',options={'HIDDEN'})

    def execute(self,context):
        try:
            m=harvest_notes(context.scene)
            apply_model(context.scene,m)
            Path(self.filepath).write_text(geometry.svg_document(m),encoding='utf-8')
            self.report({'INFO'},'已导出 SVG；原型图纸，不用于施工；打印须关闭缩放')
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_export_json(_SceneOperator,Operator,ExportHelper):
    bl_idname='dbim.export_json'
    bl_label='导出组件状态（JSON）'
    filename_ext='.json'
    filter_glob: StringProperty(default='*.json',options={'HIDDEN'})

    def execute(self,context):
        try:
            m=harvest_notes(context.scene)
            apply_model(context.scene,m)
            Path(self.filepath).write_text(core.dumps(m),encoding='utf-8')
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_drag_width(_SceneOperator,Operator):
    bl_idname='dbim.drag_width'
    bl_label='拖动门洞宽度（仅当前实例）'
    bl_options={'REGISTER','UNDO','BLOCKING'}
    door_id: StringProperty(options={'HIDDEN'})
    view: StringProperty(default='MODEL',options={'HIDDEN'})

    def _x(self,context,event):
        pos=(event.mouse_region_x,event.mouse_region_y)
        rv=context.space_data.region_3d
        origin=view3d_utils.region_2d_to_origin_3d(context.region,rv,pos)
        direction=view3d_utils.region_2d_to_vector_3d(context.region,rv,pos)
        hit=intersect_line_plane(origin,origin+direction,self._plane,self._normal,False)
        return hit.x if hit else None

    def invoke(self,context,event):
        try:
            if not context.area or context.area.type!='VIEW_3D' or context.region.type!='WINDOW':
                raise core.ModelError('请拖动视图中门右侧的箭头手柄')
            self.door_id=self.door_id or active_door_id(context)
            self._baseline=harvest_notes(context.scene)
            d=self._baseline.doors[self.door_id]
            self._width=d.width_mm
            self._plane=_handle_position(d,self.view)
            direction=view3d_utils.region_2d_to_vector_3d(context.region,context.space_data.region_3d,
                                                      (event.mouse_region_x,event.mouse_region_y))
            self._normal=Vector((0,direction.y,direction.z)) if self.view=='MODEL' else Vector((0,0,1))
            if self._normal.length<.01:
                raise core.ModelError('视线平行于宽度方向；请旋转视图再拖动')
            self._normal.normalize()
            self._start_x=self._x(context,event)
            if self._start_x is None:
                raise core.ModelError('无法计算拖动平面；请切回标准视图')
            self._last_width=self._width
            self._invalid=False
            context.window_manager.modal_handler_add(self)
            context.area.header_text_set('门洞宽度：仅当前实例 | Shift 1mm / 默认10mm | 松开确认 | Esc取消')
            return {'RUNNING_MODAL'}
        except Exception as exc:
            return self.fail(exc)

    def modal(self,context,event):
        if event.type in {'ESC','RIGHTMOUSE'}:
            apply_model(context.scene,self._baseline)
            context.area.header_text_set(None)
            return {'CANCELLED'}
        if event.type=='MOUSEMOVE':
            try:
                x=self._x(context,event)
                if x is None:
                    raise core.ModelError('当前视角无法定位')
                width=interaction.width_from_drag(self._width,self._start_x,x,1 if event.shift else 10)
                proposed=core.set_width(self._baseline,self.door_id,width)
                if width!=self._last_width:
                    apply_model(context.scene,proposed)
                    self._last_width=width
                self._invalid=False
                context.area.header_text_set(f'门洞 {width:g} mm | 仅当前实例 | Shift精调 | 松开确认 / Esc取消')
            except Exception as exc:
                self._invalid=True
                context.area.header_text_set('无效宽度：'+str(exc)+' | 松开将取消')
            return {'RUNNING_MODAL'}
        if event.type=='LEFTMOUSE' and event.value=='RELEASE':
            context.area.header_text_set(None)
            if self._invalid:
                apply_model(context.scene,self._baseline)
                self.report({'WARNING'},'无效拖动已取消，原尺寸保留')
                return {'CANCELLED'}
            return {'FINISHED'}
        return {'RUNNING_MODAL'}


def _handle_position(door,view):
    right=(door.center_x_mm+door.width_mm/2)*.001
    if view=='MODEL':
        return Vector((right,-.14,door.height_mm*.0005))
    offset=OFFSETS[view]
    return offset+Vector((right,-.50 if view=='PLAN' else -.38,.07))


class DBIM_GGT_width(GizmoGroup):
    bl_idname='DBIM_GGT_width'
    bl_label='DesignerBIM opening width'
    bl_space_type='VIEW_3D'
    bl_region_type='WINDOW'
    bl_options={'3D','PERSISTENT'}

    @classmethod
    def poll(cls,context):
        return context.mode=='OBJECT' and STATE_KEY in context.scene

    def setup(self,context):
        self.arrow=self.gizmos.new('GIZMO_GT_arrow_3d')
        self.arrow.color=(.1,.5,.75)
        self.arrow.alpha=.9
        self.arrow.color_highlight=(.3,.75,1)
        self.arrow.alpha_highlight=1
        self.arrow.scale_basis=.8
        self.arrow.line_width=3
        self.op=self.arrow.target_set_operator('dbim.drag_width')

    def draw_prepare(self,context):
        try:
            m=get_model(context.scene)
            did=active_door_id(context)
            d=m.doors[did]
            view=area_mode(context)
            self.arrow.hide=False
            self.arrow.matrix_basis=Matrix.Translation(_handle_position(d,view)) @ Vector((1,0,0)).to_track_quat('Z','Y').to_matrix().to_4x4()
            self.op.door_id=did
            self.op.view=view
        except (core.ModelError,KeyError):
            self.arrow.hide=True


class DBIM_PT_main(Panel):
    bl_label='DesignerBIM · 门组件实验'
    bl_idname='DBIM_PT_main'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category='DesignerBIM'

    def draw(self,context):
        layout=self.layout
        layout.label(text='P01  ·  v0.3.0  ·  基线 Blender 5.2.2')
        if bpy.app.version!=TARGET_VERSION:
            box=layout.box(); box.alert=True
            box.label(text='当前版本不是验收基线 5.2.2',icon='ERROR')
        if STATE_KEY not in context.scene:
            layout.operator('dbim.create_demo',icon='ADD')
            layout.label(text='新建独立场景；不会清空当前模型。')
            return
        try:
            m=get_model(context.scene)
        except core.ModelError as exc:
            layout.label(text=str(exc),icon='ERROR')
            return
        layout.operator('dbim.layout',icon='WINDOW')
        row=layout.row(align=True)
        for mode,label in (('MODEL','三维'),('PLAN','平面'),('ELEVATION','立面')):
            row.operator('dbim.view',text=label).mode=mode
        did=active_door_id(context)
        selected=selected_door_ids(context)
        box=layout.box()
        box.label(text='1  选择实例')
        for index,d in enumerate(m.doors.values()):
            if index%4==0:
                row=box.row(align=True)
            op=row.operator('dbim.select_door',text=d.tag,depress=(d.id==did))
            op.door_id=d.id
        box.label(text='选中：'+(', '.join(m.doors[k].tag for k in selected if k in m.doors) or '无'))
        draw_component_controls(layout,context,m,did)
        if not context.scene.get(component_scene.EDIT_KEY):
            draw_instance_controls(layout,context,m,did)
        box=layout.box()
        box.label(text='3  人工说明与复核')
        box.operator('dbim.add_note',icon='ADD')
        for n in m.notes.values():
            row=box.row(align=True)
            needs=core.note_requires_review(m,n.id)
            row.label(text=m.doors[n.door_id].tag+': '+n.text[:14],icon='ERROR' if needs else 'CHECKMARK')
            row.operator('dbim.edit_note',text='编辑').note_id=n.id
            if needs:
                box.operator('dbim.confirm_note',text='确认已复核 '+m.doors[n.door_id].tag).note_id=n.id
        box.label(text='文字可原位编辑、G移动；刷新/保存时同步。')
        box=layout.box()
        box.label(text='4  检查与输出')
        box.operator('dbim.refresh',icon='FILE_REFRESH')
        box.operator('dbim.export_svg')
        box.operator('dbim.export_json')
        box.label(text=f'状态版本：{m.schema_version}  ·  修改：r{m.revision}')
        if context.scene.get(ERROR_KEY):
            layout.label(text=context.scene[ERROR_KEY][:70],icon='ERROR')
        layout.label(text='默认选择整门；Tab进入/退出组件内部。')
        layout.label(text='交互原型，非施工图生产工具。',icon='INFO')


@persistent
def save_pre(_dummy):
    if _BUSY:
        return
    for scene in bpy.data.scenes:
        if STATE_KEY in scene:
            try:
                apply_model(scene,harvest_notes(scene))
            except Exception as exc:
                scene[ERROR_KEY]='保存前同步失败：'+str(exc)
                print('DesignerBIM WARNING:',scene[ERROR_KEY])


@persistent
def load_post(_dummy):
    global _FONT
    _FONT=None
    _AREA_MODES.clear()
    for scene in bpy.data.scenes:
        if STATE_KEY in scene:
            try:
                m=core.loads(scene[STATE_KEY])
                scene[component_scene.EDIT_KEY]=''
                apply_model(scene,harvest_notes(scene))
            except Exception as exc:
                # Never silently migrate or overwrite unsupported future data.
                scene[ERROR_KEY]=str(exc)


CLASSES=(DBIM_OT_create_demo,DBIM_OT_select_door,DBIM_OT_set_width,DBIM_OT_set_frame,
         DBIM_OT_add_note,DBIM_OT_edit_note,DBIM_OT_confirm_note,DBIM_OT_refresh,
         DBIM_OT_layout,DBIM_OT_view,DBIM_OT_export_svg,DBIM_OT_export_json,
         DBIM_OT_drag_width,DBIM_GGT_width,*INSTANCE_CLASSES,*COMPONENT_CLASSES,DBIM_PT_main)


def register():
    if bpy.app.version<TARGET_VERSION or bpy.app.version>=(5,3,0):
        raise RuntimeError('DesignerBIM P01 的开发基线是 Blender 5.2.2；本包限制在 5.2.x（>=5.2.2）')
    registered=[]
    try:
        for cls in CLASSES:
            bpy.utils.register_class(cls)
            registered.append(cls)
        if save_pre not in bpy.app.handlers.save_pre:
            bpy.app.handlers.save_pre.append(save_pre)
        if load_post not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(load_post)
        register_keymaps()
        # Existing files can migrate immediately after a remote update/re-enable.
        load_post(None)
    except Exception:
        for cls in reversed(registered):
            bpy.utils.unregister_class(cls)
        raise


def unregister():
    unregister_keymaps()
    for handlers,fn in ((bpy.app.handlers.save_pre,save_pre),(bpy.app.handlers.load_post,load_post)):
        if fn in handlers:
            handlers.remove(fn)
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    _AREA_MODES.clear()
