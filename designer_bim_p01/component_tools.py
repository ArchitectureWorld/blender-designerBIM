# SPDX-License-Identifier: GPL-3.0-or-later
"""Component-scoped commands; native shortcuts pass through for other models."""
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy.types import Operator
from . import core,component_scene

_KEYMAPS=[]
PARTS=[('FRAME','门框截面','左右框与顶框共同截面'),('LEAF','门扇厚度','不改变门洞尺寸')]
SCOPES=[('INSTANCE','仅当前实例','建立局部参数覆盖，保留原共享定义'),
        ('DEFINITION','共享定义','修改同定义所有未覆盖的实例')]


def adapter():
    from . import addon
    return addon


def edit_id(context):
    return context.scene.get(component_scene.EDIT_KEY,'')


class _ComponentOperator:
    @classmethod
    def poll(cls,context):return adapter()._SceneOperator.poll(context)
    def fail(self,exc):
        self.report({'ERROR'},str(exc));return {'CANCELLED'}


class DBIM_OT_enter_component(_ComponentOperator,Operator):
    bl_idname='dbim.enter_component'
    bl_label='进入组件内部'
    bl_description='只开放当前门的内部结构；部件用参数编辑，不进入任意网格编辑'
    bl_options={'REGISTER','UNDO'}
    door_id:StringProperty(options={'HIDDEN'})

    def execute(self,context):
        a=adapter();old=edit_id(context)
        try:
            did=self.door_id or a.active_door_id(context)
            m=a.harvest_notes(context.scene)
            if did not in m.doors:raise core.ModelError('请选择门组件')
            context.scene[component_scene.EDIT_KEY]=did
            a.apply_model(context.scene,m)
            for o in context.selected_objects:o.select_set(False)
            part=next(o for o in context.scene.objects if o.get('dbim_owner')==context.scene[a.OWNER_KEY] and o.get('dbim_key')=='MODEL.'+did+'.jamb-left')
            part.select_set(True);context.view_layer.objects.active=part
            context.scene['dbim_active_door']=did
            return {'FINISHED'}
        except Exception as exc:
            context.scene[component_scene.EDIT_KEY]=old
            return self.fail(exc)


class DBIM_OT_exit_component(_ComponentOperator,Operator):
    bl_idname='dbim.exit_component'
    bl_label='退出组件内部'
    bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        a=adapter();did=edit_id(context)
        try:
            m=a.harvest_notes(context.scene)
            component_scene.check_generated_geometry(a._objects(context.scene))
            context.scene[component_scene.EDIT_KEY]=''
            a.apply_model(context.scene,m)
            if did in m.doors:a.select_door(context,did)
            return {'FINISHED'}
        except Exception as exc:
            context.scene[component_scene.EDIT_KEY]=did
            return self.fail(exc)


class DBIM_OT_select_part(_ComponentOperator,Operator):
    bl_idname='dbim.select_part'
    bl_label='选择内部部件'
    part:EnumProperty(items=PARTS,default='FRAME')
    def execute(self,context):
        did=edit_id(context)
        if not did:return {'CANCELLED'}
        for o in context.selected_objects:o.select_set(False)
        suffix='.leaf' if self.part=='LEAF' else '.jamb-left'
        o=next((o for o in adapter()._scene_objects(context.scene) if o.get('dbim_key')=='MODEL.'+did+suffix),None)
        if o:
            o.select_set(True);context.view_layer.objects.active=o
            return {'FINISHED'}
        return {'CANCELLED'}


class DBIM_OT_edit_component_part(_ComponentOperator,Operator):
    bl_idname='dbim.edit_component_part'
    bl_label='修改内部部件参数'
    bl_options={'REGISTER','UNDO'}
    part:EnumProperty(name='内部部件',items=PARTS,default='FRAME')
    scope:EnumProperty(name='作用范围',items=SCOPES,default='INSTANCE')
    value_mm:FloatProperty(name='截面 / 厚度 (mm)',default=60,min=.1,max=500,precision=1)

    def invoke(self,context,event):
        did=edit_id(context)
        if not did:return self.fail(core.ModelError('请先进入组件内部'))
        self.part=component_scene.part_from_object(context.active_object)
        f=core.effective_definition(adapter().get_model(context.scene),did)
        self.value_mm=f.leaf_thickness_mm if self.part=='LEAF' else f.frame_section_mm
        return context.window_manager.invoke_props_dialog(self,width=440)

    def draw(self,context):
        layout=self.layout;layout.prop(self,'part');layout.prop(self,'scope');layout.prop(self,'value_mm')
        m=adapter().get_model(context.scene);did=edit_id(context)
        if did not in m.doors:return
        if self.scope=='INSTANCE':layout.label(text='仅 '+m.doors[did].tag+'；保留共享定义，其他门不变')
        else:
            ids=core.affected_ids(m,did,'DEFINITION')
            layout.label(text='定义影响：'+', '.join(m.doors[k].tag for k in ids))
            layout.label(text='已有局部覆盖的门保留其覆盖值')
        layout.label(text='修改后自动更新三维与二维；人工说明保留并提示复核')

    def execute(self,context):
        try:
            did=edit_id(context)
            if not did:raise core.ModelError('请先进入组件内部')
            a=adapter();m=a.harvest_notes(context.scene)
            a.apply_model(context.scene,core.set_component_part(m,did,self.part,self.value_mm,scope=self.scope))
            return {'FINISHED'}
        except Exception as exc:return self.fail(exc)


class DBIM_OT_reset_component_part(_ComponentOperator,Operator):
    bl_idname='dbim.reset_component_part'
    bl_label='恢复部件继承'
    bl_options={'REGISTER','UNDO'}
    part:EnumProperty(items=PARTS,default='FRAME')
    def execute(self,context):
        try:
            a=adapter();did=edit_id(context)
            a.apply_model(context.scene,core.reset_component_part(a.harvest_notes(context.scene),did,self.part))
            return {'FINISHED'}
        except Exception as exc:return self.fail(exc)


class DBIM_OT_delete_door(_ComponentOperator,Operator):
    bl_idname='dbim.delete_door'
    bl_label='删除整个门组件'
    bl_description='删除当前门及其生成表达、回填墙洞；关联人工说明须明确确认'
    bl_options={'REGISTER','UNDO'}
    door_id:StringProperty(options={'HIDDEN'})
    delete_notes:BoolProperty(name='确认同时删除这樘门的人工说明',default=False)
    def invoke(self,context,event):
        self.door_id=adapter().active_door_id(context)
        self.delete_notes=False
        return context.window_manager.invoke_props_dialog(self,width=440)
    def draw(self,context):
        m=adapter().get_model(context.scene);did=self.door_id or adapter().active_door_id(context)
        if did not in m.doors:return
        self.layout.label(text='删除 '+m.doors[did].tag+' 整个实例，墙洞与二维表达同步')
        count=sum(n.door_id==did for n in m.notes.values())
        self.layout.label(text=f'关联人工说明：{count} 条')
        if count:self.layout.prop(self,'delete_notes')
        self.layout.label(text='其他门与说明保持不变；可 Ctrl+Z 撤销')
    def execute(self,context):
        try:
            a=adapter();m=a.harvest_notes(context.scene);did=self.door_id or a.active_door_id(context)
            n=core.delete_doors(m,(did,),delete_notes=self.delete_notes)
            a.apply_model(context.scene,n)
            next_id=next(iter(n.doors),'');context.scene['dbim_active_door']=next_id
            if next_id:a.select_door(context,next_id)
            return {'FINISHED'}
        except Exception as exc:return self.fail(exc)


class DBIM_OT_component_shortcut(Operator):
    bl_idname='dbim.component_shortcut'
    bl_label='DesignerBIM 组件快捷操作'
    action:StringProperty(options={'HIDDEN'})
    def invoke(self,context,event):
        a=adapter()
        if not context.area or context.area.type!='VIEW_3D' or a.STATE_KEY not in context.scene or context.mode!='OBJECT':return {'PASS_THROUGH'}
        owned=[o for o in context.selected_objects if o.get('dbim_owner')==context.scene.get(a.OWNER_KEY) and o.get('dbim_role')=='root']
        did=edit_id(context)
        if did:
            if self.action=='EDIT':return bpy.ops.dbim.exit_component('EXEC_DEFAULT')
            if self.action in ('MOVE','COPY','DELETE'):
                self.report({'WARNING'},'正在组件内部：请用部件参数编辑；Tab退出后才能操作整门')
                return {'CANCELLED'}
        if not owned:return {'PASS_THROUGH'}
        if len(owned)!=len(context.selected_objects) or len(owned)!=1:
            self.report({'WARNING'},'请选择一樘完整的门组件；未执行混合或多门操作')
            return {'CANCELLED'}
        if self.action=='EDIT':return bpy.ops.dbim.enter_component('EXEC_DEFAULT')
        if self.action=='MOVE':return bpy.ops.dbim.move_door('INVOKE_DEFAULT')
        if self.action=='COPY':return bpy.ops.dbim.add_door('INVOKE_DEFAULT',mode='COPY')
        if self.action=='DELETE':return bpy.ops.dbim.delete_door('INVOKE_DEFAULT')
        return {'PASS_THROUGH'}


def draw_component_controls(layout,context,m,did):
    editing=edit_id(context)
    box=layout.box()
    if editing in m.doors:
        d=m.doors[editing];f=core.effective_definition(m,editing)
        box.label(text='组件内部  /  '+d.tag,icon='OUTLINER_COLLECTION')
        row=box.row(align=True);row.scale_y=1.15
        for part,label in (('FRAME','门框'),('LEAF','门扇')):
            row.operator('dbim.select_part',text=label).part=part
        box.label(text=f'实际门框 {f.frame_section_mm:g} mm · 门扇 {f.leaf_thickness_mm:g} mm')
        box.operator('dbim.edit_component_part',text='编辑选中部件参数')
        row=box.row(align=True)
        row.operator('dbim.reset_component_part',text='门框恢复继承').part='FRAME'
        row.operator('dbim.reset_component_part',text='门扇恢复继承').part='LEAF'
        box.operator('dbim.exit_component',text='退出组件内部 · Tab',icon='LOOP_BACK')
        box.label(text='内部用参数编辑；任意网格修改尚未开放')
    else:
        box.label(text='整门模式  /  一樘门 = 一个组件',icon='OUTLINER_OB_EMPTY')
        if did in m.doors:
            box.operator('dbim.enter_component',text='进入组件内部 · Tab').door_id=did
            box.operator('dbim.delete_door',text='删除整樘门',icon='TRASH').door_id=did
            f=core.effective_definition(m,did)
            box.label(text=f'当前实际门框 {f.frame_section_mm:g} mm · 门扇 {f.leaf_thickness_mm:g} mm')
        else:
            box.operator('dbim.add_door',text='在墙上新增门',icon='ADD').mode='NEW'
        box.label(text='G 精确定位 · Shift+D 复制 · X 删除')


COMPONENT_CLASSES=(DBIM_OT_enter_component,DBIM_OT_exit_component,DBIM_OT_select_part,
                   DBIM_OT_edit_component_part,DBIM_OT_reset_component_part,DBIM_OT_delete_door,
                   DBIM_OT_component_shortcut)


def register_keymaps():
    kc=bpy.context.window_manager.keyconfigs.addon
    if not kc:return
    km=kc.keymaps.new(name='Object Mode',space_type='EMPTY')
    for key,shift,action in (('TAB',False,'EDIT'),('G',False,'MOVE'),('D',True,'COPY'),('X',False,'DELETE'),('DEL',False,'DELETE')):
        kmi=km.keymap_items.new('dbim.component_shortcut',key,'PRESS',shift=shift)
        kmi.properties.action=action;_KEYMAPS.append((km,kmi))


def unregister_keymaps():
    for km,kmi in _KEYMAPS:
        try:km.keymap_items.remove(kmi)
        except (ReferenceError,RuntimeError):pass
    _KEYMAPS.clear()
