# SPDX-License-Identifier: GPL-3.0-or-later
"""Native collection-instance presentation, separate from engineering identity.

Private occurrence/view collections are evaluated geometry, NOT new component
library definitions. Only an explicit component editing session links its MODEL
payload into the scene. Source parts retain their IDs and are not welded.
"""
import hashlib
import json
import bpy
from mathutils import Vector
from . import core

EDIT_KEY='dbim_component_edit'
PAYLOAD='component_payload'
VIEW_NAMES={'MODEL':'三维','PLAN':'平面','ELEVATION':'立面'}
PART_NAMES={'frame':'门框','leaf':'门扇'}


def owned_collections(scene):
    owner=scene.get('dbim_p01_owner')
    return [c for c in bpy.data.collections if owner and c.get('dbim_owner')==owner]


def payload(scene,door_id,view):
    for c in owned_collections(scene):
        if c.get('dbim_collection_role')==PAYLOAD and c.get('dbim_door')==door_id and c.get('dbim_view')==view:
            return c
    c=bpy.data.collections.new('P01 component '+door_id+' '+view)
    c['dbim_owner']=scene['dbim_p01_owner']
    c['dbim_collection_role']=PAYLOAD
    c['dbim_door']=door_id
    c['dbim_view']=view
    return c


def route_object(scene,obj,visible_collection,view,door_id,role):
    internal=bool(door_id) and role not in ('root','manual','annotation','review')
    target=payload(scene,door_id,view) if internal else visible_collection
    if obj.name not in target.objects:
        target.objects.link(obj)
    # Relocate only links we own. Never unlink a user's unrelated collection.
    for c in list(obj.users_collection):
        if c!=target and c.get('dbim_owner')==scene['dbim_p01_owner']:
            c.objects.unlink(obj)
    obj['dbim_internal']=internal


def setup_root(builder,door,view,offset):
    key='ROOT.'+door.id if view=='MODEL' else view+'.ROOT.'+door.id
    root=builder.obj(key,view,'EMPTY','root',door.id)
    c=payload(builder.scene,door.id,view)
    anchor=Vector((door.center_x_mm*.001,0,0))+offset
    c.instance_offset=anchor
    c.name=door.tag+' · '+VIEW_NAMES[view]+' · 内部'
    c['dbim_definition']=door.definition_id
    root.instance_type='COLLECTION'
    root.instance_collection=c
    root.location=anchor
    root.rotation_euler=(0,0,0)
    root.scale=(1,1,1)
    root.name=door.tag+' · 门' if view=='MODEL' else door.tag+' · '+VIEW_NAMES[view]+'表达'
    root.empty_display_type='PLAIN_AXES'
    root.empty_display_size=.08
    root['dbim_definition']=door.definition_id
    root['dbim_component_proxy']=True
    return root


def mesh_fingerprint(obj):
    if obj.type!='MESH':return ''
    data={'v':[tuple(round(float(c),6) for c in v.co) for v in obj.data.vertices],
          'f':[tuple(p.vertices) for p in obj.data.polygons]}
    return hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest()


def check_generated_geometry(objects):
    for o in objects:
        if o.get('dbim_role') in ('frame','leaf') and o.type=='MESH':
            if o.mode=='EDIT':
                raise core.ModelError('请退出网格编辑；组件内部请使用参数编辑，不会自动覆盖网格修改')
            stored=o.get('dbim_generated_fingerprint','')
            if stored and mesh_fingerprint(o)!=stored:
                raise core.ModelError('检测到未支持的内部网格修改：'+o.name+'。请撤销该修改或另存副本；本次刷新已停止，未覆盖几何')


def sync_edit_visibility(scene,model,view_collections):
    editing=scene.get(EDIT_KEY,'')
    if editing not in model.doors:
        editing='';scene[EDIT_KEY]=''
    for c in list(owned_collections(scene)):
        if c.get('dbim_collection_role')!=PAYLOAD:continue
        opened=c.get('dbim_door')==editing and c.get('dbim_view')=='MODEL'
        for parent in (scene.collection,*view_collections.values()):
            linked=c.name in parent.children
            desired=opened and parent==view_collections['MODEL']
            if desired and not linked:parent.children.link(c)
            if not desired and linked:parent.children.unlink(c)
        if c.get('dbim_door') not in model.doors and not c.objects and not c.children:
            bpy.data.collections.remove(c)
    for o in list(scene.objects):
        if o.get('dbim_owner')!=scene['dbim_p01_owner']:continue
        if o.get('dbim_role')=='root':
            hide=bool(editing) and o.get('dbim_door')==editing and o.get('dbim_view')=='MODEL'
            for vl in scene.view_layers:
                if o.name in vl.objects:o.hide_set(hide,view_layer=vl)
            o.hide_render=hide
            o.hide_select=bool(editing)
        elif o.get('dbim_internal'):
            o.hide_select=not (o.get('dbim_door')==editing and o.get('dbim_view')=='MODEL')
    for vl in scene.view_layers:vl.update()


def part_from_object(obj):
    return 'LEAF' if obj and obj.get('dbim_role')=='leaf' else 'FRAME'
