"""P01 editable-instance contract; tests real state and vector geometry, never bpy mocks."""
from dataclasses import replace
from pathlib import Path
import json
import math
import pytest
from designer_bim_p01 import core, geometry


def call(name, *args, **kwargs):
    fn = getattr(core, name, None)
    assert callable(fn), f'{name} is not implemented'
    return fn(*args, **kwargs)


def test_schema1_migration_retains_identities_and_review_status():
    raw = (Path(__file__).parent/'fixtures/schema1_notes.json').read_text(encoding='utf-8')
    m = core.loads(raw)
    assert m.schema_version == 2
    assert m.revision == 3
    assert set(m.doors) == {'door-01','door-02','door-03'}
    assert all(d.handing == 'LEFT' for d in m.doors.values())
    assert not core.note_requires_review(m, 'fresh')
    assert core.note_requires_review(m, 'stale')
    assert m.notes['fresh'].text == '保留并保持已复核'
    assert json.loads(raw)['schema_version'] == 1
    assert core.loads(core.dumps(m)) == m


def test_copy_gets_unique_identity_and_tag_but_shares_definition():
    m = core.set_width(core.demo_model(), 'door-01', 1000)
    m = core.add_note(m, 'door-01', 'Do not duplicate this approval', note_id='n')
    n = call('copy_door', m, 'door-01', 3000, instance_id='copy-1')
    d = n.doors['copy-1']
    assert d.tag == 'D04'
    assert d.width_mm == 1000 and d.height_mm == 2100
    assert d.center_x_mm == 3000 and d.definition_id == m.doors['door-01'].definition_id
    assert n.doors['door-01'] == m.doors['door-01']
    assert n.notes == m.notes and n.definitions == m.definitions
    assert len(m.doors) == 3 and n.revision == m.revision + 1
    shared = core.set_frame_section(n, d.definition_id, 80)
    assert shared.doors['copy-1'].width_mm == 1000


def test_new_door_uses_requested_dimensions_and_shared_definition():
    m=core.demo_model()
    n=call('add_door',m,'door-def-01',3000,width_mm=1100,height_mm=2400,handing='RIGHT',instance_id='new')
    d=n.doors['new']
    assert (d.width_mm,d.height_mm,d.handing)==(1100,2400,'RIGHT')
    assert d.tag=='D04' and d.wall_id==m.wall.id
    assert len(n.definitions)==1


def test_copy_uuid_not_reused():
    m=core.demo_model()
    a=call('copy_door',m,'door-01',3000)
    b=call('copy_door',m,'door-01',3000)
    assert set(a.doors)-set(m.doors) != set(b.doors)-set(m.doors)


def test_duplicate_ids_are_rejected_before_mutation():
    m=core.demo_model()
    before=core.dumps(m)
    with pytest.raises(core.ModelError):
        call('copy_door',m,'door-01',3000,instance_id='door-01')
    assert core.dumps(m)==before


@pytest.mark.parametrize('position',[1750,100,8999,float('nan'),float('inf'),True])
def test_invalid_create_is_atomic(position):
    m=core.demo_model();before=core.dumps(m)
    with pytest.raises(core.ModelError):
        call('add_door',m,'door-def-01',position)
    assert core.dumps(m)==before


def test_auto_position_is_valid_and_finds_nearest_gap():
    m=core.demo_model()
    pos=call('suggest_center',m,900,preferred_mm=1750)
    n=call('copy_door',m,'door-01',pos,instance_id='n')
    assert len(n.doors)==4 and pos==2770
    pos2=call('suggest_center',n,900,preferred_mm=1750)
    assert pos2!=pos
    assert len(call('copy_door',n,'door-01',pos2).doors)==5


def test_no_room_has_explicit_error():
    with pytest.raises(core.ModelError):
        call('suggest_center',core.demo_model(),8000)


def test_move_preserves_identity_dimensions_and_notes_requests_review():
    m=core.add_note(core.demo_model(),'door-01','Keep',note_id='n')
    n=call('move_door',m,'door-01',1900)
    assert n.doors['door-01'].id=='door-01'
    assert n.doors['door-01'].center_x_mm==1900
    assert n.doors['door-01'].width_mm==900
    assert n.doors['door-02']==m.doors['door-02']
    assert n.notes==m.notes and core.note_requires_review(n,'n')
    assert m.doors['door-01'].center_x_mm==1750
    assert call('move_door',n,'door-01',1900) is n


def test_move_overlap_rejects_whole_edit():
    m=core.demo_model(); before=core.dumps(m)
    with pytest.raises(core.ModelError):
        call('move_door',m,'door-01',4000)
    assert core.dumps(m)==before


def test_height_scopes_and_geometry_agree():
    m=core.demo_model()
    n=call('set_height',m,'door-01',2400,scope='SELECTED',selected_ids=['door-01','door-03'])
    assert [n.doors[k].height_mm for k in m.doors]==[2400,2100,2400]
    assert all(d.width_mm==900 for d in n.doors.values())
    wall=sum(p.volume_mm3 for p in geometry.model_parts(n) if p.role=='wall')
    expected=n.wall.length_mm*n.wall.depth_mm*n.wall.height_mm-sum(d.width_mm*d.height_mm*n.wall.depth_mm for d in n.doors.values())
    assert math.isclose(wall,expected)
    dr=geometry.drawing(n,'ELEVATION')
    assert next(t for t in dr.texts if t.key=='door-01.height-label').text=='H 2400'
    dim=next(l for l in dr.lines if l.key=='door-01.height-line')
    assert dim.points[-1][1]-dim.points[0][1]==2400
    assert call('set_height',n,'door-01',2400) is n


@pytest.mark.parametrize('height',[100,3000,float('nan'),True])
def test_invalid_height_is_atomic(height):
    m=core.demo_model();before=core.dumps(m)
    with pytest.raises(core.ModelError):
        call('set_height',m,'door-01',height)
    assert core.dumps(m)==before


def test_left_right_handing_mirrors_leaf_and_plan_not_entire_wall():
    m=core.demo_model()
    n=call('set_handing',m,'door-01','RIGHT')
    center=m.doors['door-01'].center_x_mm
    left=next(p for p in geometry.model_parts(m) if p.key=='door-01.leaf')
    right=next(p for p in geometry.model_parts(n) if p.key=='door-01.leaf')
    assert left.maximum_mm[0]==pytest.approx(2*center-right.minimum_mm[0])
    assert left.minimum_mm[0]==pytest.approx(2*center-right.maximum_mm[0])
    assert left.size_mm==right.size_mm
    lp=next(l for l in geometry.drawing(m,'PLAN').lines if l.key=='door-01.swing')
    rp=next(l for l in geometry.drawing(n,'PLAN').lines if l.key=='door-01.swing')
    for (x,y),(rx,ry) in zip(lp.points,rp.points):
        assert (rx,ry)==pytest.approx((2*center-x,y))
    assert n.doors['door-02']==m.doors['door-02']
    assert {p.key for p in geometry.model_parts(n)}=={p.key for p in geometry.model_parts(m)}
    assert call('set_handing',n,'door-01','RIGHT') is n


def test_3d_open_leaf_and_plan_symbol_have_same_footprint():
    for handing in ('LEFT','RIGHT'):
        m=call('set_handing',core.demo_model(),'door-01',handing)
        p=next(p for p in geometry.model_parts(m) if p.key=='door-01.leaf')
        line=next(l for l in geometry.drawing(m,'PLAN').lines if l.key=='door-01.open-leaf')
        assert p.minimum_mm[:2]==(min(x for x,y in line.points),min(y for x,y in line.points))
        assert p.maximum_mm[:2]==(max(x for x,y in line.points),max(y for x,y in line.points))


def test_bad_handing_and_unknown_ids_rejected():
    m=core.demo_model()
    for fn,args in [('set_handing',('door-01','UP')),('move_door',('missing',1000)),('copy_door',('missing',3000)),('set_height',('missing',2300)),('add_door',('missing',3000))]:
        with pytest.raises(core.ModelError):
            call(fn,m,*args)


def test_changes_in_handing_and_height_flag_only_affected_note():
    m=core.add_note(core.demo_model(),'door-01','a',note_id='a')
    m=core.add_note(m,'door-02','b',note_id='b')
    n=call('set_handing',m,'door-01','RIGHT')
    assert core.note_requires_review(n,'a') and not core.note_requires_review(n,'b')
    n=core.confirm_note(n,'a')
    n=call('set_height',n,'door-01',2400)
    assert core.note_requires_review(n,'a') and not core.note_requires_review(n,'b')
    assert core.loads(core.dumps(n))==n
