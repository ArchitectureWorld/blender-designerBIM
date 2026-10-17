"""Regression tests exercise actual state transformations, no bpy mocks."""
import copy
import json
import math
import pytest
from designer_bim_p01 import core


def model():
    assert callable(getattr(core, 'demo_model', None)), 'demo_model implementation is missing'
    return core.demo_model()


def test_demo_has_three_instances_and_one_shared_definition():
    m = model()
    assert len(m.doors) == 3
    assert len(m.definitions) == 1
    assert {d.definition_id for d in m.doors.values()} == {'door-def-01'}
    assert [d.width_mm for d in m.doors.values()] == [900, 900, 900]


def test_width_changes_only_target_instance_and_preserves_definition():
    m = model()
    n = core.set_width(m, 'door-01', 1200)
    assert [d.width_mm for d in n.doors.values()] == [1200, 900, 900]
    assert n.doors['door-01'].definition_id == m.doors['door-01'].definition_id
    assert m.doors['door-01'].width_mm == 900
    assert n.revision == m.revision + 1


def test_definition_scope_and_selection_scope_are_explicit():
    m = model()
    s = core.set_width(m, 'door-01', 1000, scope='SELECTED', selected_ids=['door-01', 'door-03'])
    assert [d.width_mm for d in s.doors.values()] == [1000, 900, 1000]
    a = core.set_width(s, 'door-01', 1100, scope='DEFINITION')
    assert [d.width_mm for d in a.doors.values()] == [1100]*3


def test_shared_frame_edit_does_not_reset_instance_widths():
    m = core.set_width(model(), 'door-01', 1200)
    n = core.set_frame_section(m, 'door-def-01', 80)
    assert n.definitions['door-def-01'].frame_section_mm == 80
    assert [d.width_mm for d in n.doors.values()] == [1200, 900, 900]


@pytest.mark.parametrize('value', [0, -1, float('nan'), float('inf'), 10000, 120])
def test_invalid_width_rejected_without_mutating_old_state(value):
    m = model()
    before = core.dumps(m)
    with pytest.raises(core.ModelError):
        core.set_width(m, 'door-01', value)
    assert core.dumps(m) == before


def test_noop_edit_does_not_create_revision():
    m = model()
    assert core.set_width(m, 'door-01', 900).revision == m.revision


def test_empty_or_foreign_selection_is_rejected():
    m = model()
    with pytest.raises(core.ModelError):
        core.set_width(m, 'door-01', 1000, scope='SELECTED', selected_ids=[])
    with pytest.raises(core.ModelError):
        core.set_width(m, 'door-01', 1000, scope='SELECTED', selected_ids=['alien'])


def test_collision_rejected_atomically():
    m = model()
    data = json.loads(core.dumps(m))
    data['doors']['door-02']['center_x_mm'] = 2200
    with pytest.raises(core.ModelError):
        core.loads(json.dumps(data))


def test_note_preserved_and_only_relevant_change_requires_review():
    m = core.add_note(model(), 'door-02', '人工收口说明', view='ELEVATION', position_mm=(4500, 2500), note_id='note-01')
    unchanged = core.set_width(m, 'door-01', 1200)
    assert not core.note_requires_review(unchanged, 'note-01')
    changed = core.set_width(unchanged, 'door-02', 1100)
    assert changed.notes['note-01'].text == '人工收口说明'
    assert changed.notes['note-01'].position_mm == (4500, 2500)
    assert core.note_requires_review(changed, 'note-01')
    reviewed = core.confirm_note(changed, 'note-01')
    assert not core.note_requires_review(reviewed, 'note-01')


def test_shared_frame_edit_marks_associated_note_for_review():
    m = core.add_note(model(), 'door-02', 'Review frame', note_id='n')
    n = core.set_frame_section(m, 'door-def-01', 80)
    assert core.note_requires_review(n, 'n')


def test_editing_note_text_does_not_implicitly_confirm_geometry():
    m = core.add_note(model(), 'door-02', 'Original', note_id='n')
    m = core.set_width(m, 'door-02', 1200)
    n = core.edit_note(m, 'n', text='Hand edited', position_mm=(4000, 2600))
    assert core.note_requires_review(n, 'n')
    assert n.notes['n'].text == 'Hand edited'


def test_json_roundtrip_retains_all_identities_and_review_state():
    m = core.add_note(model(), 'door-02', '中文 <>& text', note_id='n')
    m = core.set_width(m, 'door-02', 1200)
    n = core.loads(core.dumps(m))
    assert n == m
    assert core.note_requires_review(n, 'n')


def test_future_schema_is_rejected_not_silently_overwritten():
    data = json.loads(core.dumps(model()))
    data['schema_version'] = 999
    with pytest.raises(core.ModelError, match='schema'):
        core.loads(json.dumps(data))


def test_orphan_instance_reference_is_rejected():
    data = json.loads(core.dumps(model()))
    data['doors']['door-01']['definition_id'] = 'deleted'
    with pytest.raises(core.ModelError):
        core.loads(json.dumps(data))
