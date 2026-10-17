"""Component semantics tested without Blender, not GUI acceptance."""
import json
from dataclasses import replace
import pytest
from designer_bim_p01 import core, geometry


def api(name):
    fn=getattr(core,name,None)
    assert callable(fn), f'{name}: required component operation is absent'
    return fn


def test_local_frame_override_preserves_definition_and_other_instances():
    m=core.demo_model()
    n=api('set_component_part')(m,'door-01','FRAME',80,scope='INSTANCE')
    assert n.doors['door-01'].definition_id==m.doors['door-01'].definition_id
    assert api('effective_definition')(n,'door-01').frame_section_mm==80
    assert api('effective_definition')(n,'door-02').frame_section_mm==60
    assert n.definitions['door-def-01'].frame_section_mm==60
    assert n.revision==m.revision+1


def test_shared_change_preserves_local_override_and_reset_restores_inheritance():
    m=api('set_component_part')(core.demo_model(),'door-01','FRAME',80,scope='INSTANCE')
    n=api('set_component_part')(m,'door-02','FRAME',70,scope='DEFINITION')
    assert api('effective_definition')(n,'door-01').frame_section_mm==80
    assert api('effective_definition')(n,'door-03').frame_section_mm==70
    r=api('reset_component_part')(n,'door-01','FRAME')
    assert api('effective_definition')(r,'door-01').frame_section_mm==70
    assert len(r.definitions)==1


def test_part_override_changes_both_3d_and_plan_and_roundtrips():
    m=api('set_component_part')(core.demo_model(),'door-01','LEAF',50,scope='INSTANCE')
    p=next(p for p in geometry.model_parts(m) if p.key=='door-01.leaf')
    assert p.size_mm[0]==50
    line=next(l for l in geometry.drawing(m,'PLAN').lines if l.key=='door-01.open-leaf')
    assert max(x for x,y in line.points)-min(x for x,y in line.points)==50
    assert core.loads(core.dumps(m))==m


def test_local_frame_dimension_matches_2d_and_3d():
    m=api('set_component_part')(core.demo_model(),'door-01','FRAME',85,scope='INSTANCE')
    p=next(p for p in geometry.model_parts(m) if p.key=='door-01.jamb-left')
    line=next(l for l in geometry.drawing(m,'PLAN').lines if l.key=='door-01.jamb-left')
    assert p.size_mm[0]==85
    assert max(x for x,y in line.points)-min(x for x,y in line.points)==85


@pytest.mark.parametrize('part,value',[('FRAME',0),('FRAME',151),('FRAME',float('nan')),('LEAF',201),('LEAF',-1),('OTHER',50)])
def test_invalid_internal_edit_is_atomic(part,value):
    m=core.demo_model(); before=core.dumps(m)
    with pytest.raises(core.ModelError):
        api('set_component_part')(m,'door-01',part,value,scope='INSTANCE')
    assert core.dumps(m)==before


def test_edit_scope_must_be_explicit_and_valid():
    with pytest.raises(core.ModelError):
        api('set_component_part')(core.demo_model(),'door-01','FRAME',80,scope='SELECTED')


def test_copy_keeps_overrides_not_notes():
    m=api('set_component_part')(core.demo_model(),'door-01','FRAME',80,scope='INSTANCE')
    m=core.add_note(m,'door-01','source note',note_id='n')
    n=core.copy_door(m,'door-01',3000)
    new_id=next(iter(set(n.doors)-set(m.doors)))
    assert api('effective_definition')(n,new_id).frame_section_mm==80
    assert n.notes==m.notes


def test_local_edit_marks_only_affected_note():
    m=core.add_note(core.demo_model(),'door-01','one',note_id='one')
    m=core.add_note(m,'door-02','two',note_id='two')
    n=api('set_component_part')(m,'door-01','FRAME',80,scope='INSTANCE')
    assert core.note_requires_review(n,'one')
    assert not core.note_requires_review(n,'two')


def test_delete_requires_explicit_note_confirmation_and_preserves_others():
    m=core.add_note(core.demo_model(),'door-01','remove?',note_id='one')
    m=core.add_note(m,'door-02','keep',note_id='two')
    before=core.dumps(m)
    with pytest.raises(core.ModelError):
        api('delete_doors')(m,('door-01',))
    assert core.dumps(m)==before
    n=api('delete_doors')(m,('door-01',),delete_notes=True)
    assert set(n.doors)=={'door-02','door-03'} and set(n.notes)=={'two'}
    assert n.doors['door-02']==m.doors['door-02']
    assert not core.note_requires_review(n,'two')
    assert not any(p.door_id=='door-01' for p in geometry.model_parts(n))
    assert not any(t.door_id=='door-01' for t in geometry.drawing(n,'PLAN').texts)


def test_delete_last_door_keeps_wall_and_allows_new_instance():
    m=core.demo_model()
    n=api('delete_doors')(m,tuple(m.doors))
    assert not n.doors and n.definitions==m.definitions
    assert len(geometry.model_parts(n))==1
    assert geometry.model_parts(n)[0].size_mm==(9000,200,3000)
    assert '<svg' in geometry.svg_document(n)
    n=core.add_door(n,'door-def-01',1750)
    assert len(n.doors)==1


def test_unknown_and_empty_delete_rejected():
    for ids in ((),('alien',),('door-01','alien')):
        with pytest.raises(core.ModelError):api('delete_doors')(core.demo_model(),ids)


def test_schema2_migration_keeps_ids_text_and_actual_review_state():
    raw=json.loads(core.dumps(core.add_note(core.demo_model(),'door-01','keep',note_id='n')))
    raw['schema_version']=2
    for d in raw['doors'].values():
        d.pop('frame_section_override_mm',None);d.pop('leaf_thickness_override_mm',None)
    import hashlib
    payload={'instance':raw['doors']['door-01'],'definition':raw['definitions']['door-def-01'],'host':raw['wall']}
    raw['notes']['n']['reviewed_signature']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:24]
    n=core.loads(json.dumps(raw))
    assert n.schema_version==3
    assert not core.note_requires_review(n,'n')
    raw['notes']['n']['reviewed_signature']='stale'
    assert core.note_requires_review(core.loads(json.dumps(raw)),'n')


def test_schema1_migration_still_keeps_original_review_flags():
    from pathlib import Path
    m=core.loads((Path(__file__).parent/'fixtures/schema1_notes.json').read_text())
    assert m.schema_version==3
    assert not core.note_requires_review(m,'fresh')
    assert core.note_requires_review(m,'stale')
