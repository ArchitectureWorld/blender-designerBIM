# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit, parameter-backed instance commands; never transform generated meshes.

Only the existing straight demo wall is supported. Left/right refers to hinge
position viewed from -Y. Source approvals/annotations are not copied to new doors.
"""
import json
import bpy
from bpy.props import EnumProperty, FloatProperty, StringProperty
from bpy.types import Operator
from . import core

SCOPE_ITEMS=[('INSTANCE','仅当前门',''),('SELECTED','选中的门','一次性批量修改'),
             ('DEFINITION','同定义全部门','明确修改这一共享定义的所有门高')]
HAND_ITEMS=[('LEFT','左铰','正面看铰链在左边，向 +Y 开启'),
            ('RIGHT','右铰','正面看铰链在右边，向 +Y 开启')]


def _adapter():
    # Lazy import avoids a registration-time circular dependency.
    from . import addon
    return addon


class _InstanceOperator:
    @classmethod
    def poll(cls,context):
        return _adapter()._SceneOperator.poll(context)

    def fail(self,exc):
        self.report({'ERROR'},str(exc))
        return {'CANCELLED'}


def _validation_line(layout, candidate):
    try:
        candidate()
        layout.label(text='位置及尺寸可用（仅原型几何检查）',icon='CHECKMARK')
    except (core.ModelError,KeyError,ValueError) as exc:
        row=layout.row(); row.alert=True
        row.label(text=str(exc)[:72],icon='ERROR')


class DBIM_OT_add_door(_InstanceOperator,Operator):
    bl_idname='dbim.add_door'
    bl_label='新增 / 复制门实例'
    bl_description='生成新编号，保留共享定义；不复制人工说明与已复核状态'
    bl_options={'REGISTER','UNDO'}
    mode: EnumProperty(items=[('NEW','新增门',''),('COPY','复制当前门','')],default='NEW',options={'HIDDEN'})
    source_id: StringProperty(options={'HIDDEN'})
    center_x_mm: FloatProperty(name='门中心距墙左端 (mm)',default=3000,min=1,max=100000,precision=1)
    width_mm: FloatProperty(name='门洞宽度 (mm)',default=900,min=300,max=6000,precision=1)
    height_mm: FloatProperty(name='门洞高度 (mm)',default=2100,min=500,max=6000,precision=1)
    handing: EnumProperty(name='铰链位置',items=HAND_ITEMS,default='LEFT')

    def _candidate(self,m,door_id):
        source=m.doors[door_id]
        if self.mode=='COPY':
            return core.copy_door(m,door_id,self.center_x_mm)
        return core.add_door(m,source.definition_id,self.center_x_mm,width_mm=self.width_mm,
                             height_mm=self.height_mm,handing=self.handing)

    def invoke(self,context,event):
        try:
            a=_adapter(); m=a.get_model(context.scene)
            self.source_id=a.active_door_id(context)
            source=m.doors[self.source_id]
            if self.mode=='COPY':
                self.width_mm=source.width_mm; self.height_mm=source.height_mm; self.handing=source.handing
            self.center_x_mm=core.suggest_center(m,self.width_mm,preferred_mm=source.center_x_mm)
            return context.window_manager.invoke_props_dialog(self,width=460)
        except Exception as exc:
            return self.fail(exc)

    def draw(self,context):
        layout=self.layout
        m=_adapter().get_model(context.scene)
        source=self.source_id or _adapter().active_door_id(context)
        layout.label(text=('复制 '+m.doors[source].tag) if self.mode=='COPY' else '新增共享定义的门')
        layout.prop(self,'center_x_mm')
        if self.mode=='NEW':
            layout.prop(self,'width_mm'); layout.prop(self,'height_mm'); layout.prop(self,'handing')
        else:
            d=m.doors[source]
            layout.label(text=f'继承：{d.width_mm:g} × {d.height_mm:g} mm；开向保持')
        layout.label(text='新编号自动生成；不复制原门的人工说明。')
        _validation_line(layout,lambda:self._candidate(m,source))

    def execute(self,context):
        try:
            a=_adapter(); m=a.harvest_notes(context.scene)
            source=self.source_id or a.active_door_id(context)
            if source not in m.doors:
                raise core.ModelError('原门已不存在，请重新选择')
            n=self._candidate(m,source)
            new_id=next(iter(set(n.doors)-set(m.doors)))
            a.apply_model(context.scene,n)
            a.select_door(context,new_id)
            self.report({'INFO'},'已创建 '+n.doors[new_id].tag+'；三维、平面和立面同步')
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_move_door(_InstanceOperator,Operator):
    bl_idname='dbim.move_door'
    bl_label='沿墙精确定位'
    bl_description='按墙左端绝对坐标或相对位移定位当前门，同时重建墙洞和二维表达'
    bl_options={'REGISTER','UNDO'}
    door_id: StringProperty(options={'HIDDEN'})
    mode: EnumProperty(name='定位方式',items=[('ABSOLUTE','绝对位置','门中心距墙左端'),
                                              ('DELTA','相对移动','正值向 +X，负值向 -X')],default='ABSOLUTE')
    center_x_mm: FloatProperty(name='门中心距墙左端 (mm)',default=1750,min=1,max=100000,precision=1)
    offset_mm: FloatProperty(name='沿墙位移 (mm)',default=0,min=-100000,max=100000,precision=1)

    def _target(self,m,did):
        return self.center_x_mm if self.mode=='ABSOLUTE' else m.doors[did].center_x_mm+self.offset_mm

    def invoke(self,context,event):
        try:
            a=_adapter(); self.door_id=a.active_door_id(context)
            self.center_x_mm=a.get_model(context.scene).doors[self.door_id].center_x_mm
            self.offset_mm=0
            return context.window_manager.invoke_props_dialog(self,width=440)
        except Exception as exc:
            return self.fail(exc)

    def draw(self,context):
        layout=self.layout; m=_adapter().get_model(context.scene)
        did=self.door_id or _adapter().active_door_id(context)
        layout.label(text='仅修改 '+m.doors[did].tag+'；高度、宽度和共享关系保持')
        layout.prop(self,'mode')
        layout.prop(self,'center_x_mm' if self.mode=='ABSOLUTE' else 'offset_mm')
        layout.label(text=f'目标中心：{self._target(m,did):g} mm')
        _validation_line(layout,lambda:core.move_door(m,did,self._target(m,did)))

    def execute(self,context):
        try:
            a=_adapter(); m=a.harvest_notes(context.scene)
            did=self.door_id or a.active_door_id(context)
            n=core.move_door(m,did,self._target(m,did))
            a.apply_model(context.scene,n)
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_set_height(_InstanceOperator,Operator):
    bl_idname='dbim.set_height'
    bl_label='修改门洞高度'
    bl_description='修改参数并同步墙洞、立面尺寸；不缩放门框截面'
    bl_options={'REGISTER','UNDO'}
    door_id: StringProperty(options={'HIDDEN'})
    height_mm: FloatProperty(name='门洞高度 (mm)',default=2100,min=500,max=6000,precision=1)
    scope: EnumProperty(name='作用范围',items=SCOPE_ITEMS,default='INSTANCE')
    selected_json: StringProperty(default='[]',options={'HIDDEN'})

    def invoke(self,context,event):
        try:
            a=_adapter(); self.door_id=a.active_door_id(context)
            self.height_mm=a.get_model(context.scene).doors[self.door_id].height_mm
            self.selected_json=json.dumps(a.selected_door_ids(context))
            return context.window_manager.invoke_props_dialog(self,width=440)
        except Exception as exc:
            return self.fail(exc)

    def draw(self,context):
        layout=self.layout; layout.prop(self,'scope'); layout.prop(self,'height_mm')
        try:
            m=_adapter().get_model(context.scene)
            ids=core.affected_ids(m,self.door_id,self.scope,json.loads(self.selected_json))
            layout.label(text='影响：'+', '.join(m.doors[k].tag for k in ids))
            _validation_line(layout,lambda:core.set_height(m,self.door_id,self.height_mm,scope=self.scope,selected_ids=ids))
        except (core.ModelError,ValueError) as exc:
            layout.label(text=str(exc),icon='ERROR')

    def execute(self,context):
        try:
            a=_adapter(); m=a.harvest_notes(context.scene)
            did=self.door_id or a.active_door_id(context)
            ids=json.loads(self.selected_json)
            if not ids and self.scope=='SELECTED':
                ids=a.selected_door_ids(context)
            a.apply_model(context.scene,core.set_height(m,did,self.height_mm,scope=self.scope,selected_ids=ids))
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


class DBIM_OT_set_handing(_InstanceOperator,Operator):
    bl_idname='dbim.set_handing'
    bl_label='修改左右开向'
    bl_description='修改当前实例的铰链侧，不镜像墙体或共享定义'
    bl_options={'REGISTER','UNDO'}
    door_id: StringProperty(options={'HIDDEN'})
    handing: EnumProperty(name='铰链位置',items=HAND_ITEMS,default='LEFT')

    def invoke(self,context,event):
        try:
            a=_adapter(); self.door_id=a.active_door_id(context)
            self.handing=a.get_model(context.scene).doors[self.door_id].handing
            return context.window_manager.invoke_props_dialog(self,width=440)
        except Exception as exc:
            return self.fail(exc)

    def draw(self,context):
        self.layout.prop(self,'handing',expand=True)
        self.layout.label(text='从 -Y 正面看铰链；原型门扇固定向 +Y 开90°。')
        self.layout.label(text='仅当前实例；三维门扇与平面开启符号一致。')

    def execute(self,context):
        try:
            a=_adapter(); m=a.harvest_notes(context.scene)
            did=self.door_id or a.active_door_id(context)
            a.apply_model(context.scene,core.set_handing(m,did,self.handing))
            return {'FINISHED'}
        except Exception as exc:
            return self.fail(exc)


def draw_instance_controls(layout,context,m,did):
    if did not in m.doors:
        return
    d=m.doors[did]; f=m.definitions[d.definition_id]
    box=layout.box(); box.label(text='2  创建与编辑实例')
    row=box.row(align=True); row.scale_y=1.15
    row.operator('dbim.add_door',text='新增门',icon='ADD').mode='NEW'
    row.operator('dbim.add_door',text='复制当前门',icon='DUPLICATE').mode='COPY'
    box.label(text=f'{d.tag} · {d.width_mm:g} × {d.height_mm:g} mm · '+('左铰' if d.handing=='LEFT' else '右铰'))
    box.label(text=f'中心距墙左端 {d.center_x_mm:g} mm')
    row=box.row(align=True); row.scale_y=1.15
    row.operator('dbim.set_width',text='门洞宽度')
    row.operator('dbim.set_height',text='门洞高度')
    row=box.row(align=True); row.scale_y=1.15
    row.operator('dbim.move_door',text='精确定位')
    row.operator('dbim.set_handing',text='左右开向')
    box.label(text='蓝色箭头：拖动当前门宽；复制请用上方按钮。')
    box.separator()
    box.label(text=f'共享门框截面：{f.frame_section_mm:g} mm')
    box.operator('dbim.set_frame',text='统一修改共享门框')


INSTANCE_CLASSES=(DBIM_OT_add_door,DBIM_OT_move_door,DBIM_OT_set_height,DBIM_OT_set_handing)
