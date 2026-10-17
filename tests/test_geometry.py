import math
import xml.etree.ElementTree as ET
from designer_bim_p01 import core, geometry


def scene(m=None):
    assert callable(getattr(geometry, 'model_parts', None)), 'model_parts missing'
    return geometry.model_parts(m or core.demo_model())


def test_wall_has_real_openings_not_overlaid_door_rectangles():
    m = core.demo_model()
    wall_parts = [p for p in scene(m) if p.role == 'wall']
    volume = sum(p.volume_mm3 for p in wall_parts)
    expected = m.wall.length_mm*m.wall.height_mm*m.wall.depth_mm - sum(d.width_mm*d.height_mm*m.wall.depth_mm for d in m.doors.values())
    assert math.isclose(volume, expected)
    assert len(wall_parts) == 7


def test_frame_thickness_is_not_scaled_with_opening_width():
    m = core.set_width(core.demo_model(), 'door-01', 1200)
    frames = [p for p in scene(m) if p.door_id == 'door-01' and p.role == 'frame']
    assert len(frames) == 3
    jamb = next(p for p in frames if p.key.endswith('jamb-left'))
    assert jamb.size_mm[0] == 60
    assert jamb.size_mm[2] == 2100


def test_geometry_keys_stay_stable_through_instance_edit():
    m = core.demo_model()
    n = core.set_width(m, 'door-01', 1200)
    assert {p.key for p in scene(m)} == {p.key for p in scene(n)}


def test_both_drawings_get_new_width_and_link_to_same_instance():
    assert callable(getattr(geometry, 'drawing', None)), 'drawing missing'
    m = core.set_width(core.demo_model(), 'door-01', 1200)
    for view in ('PLAN', 'ELEVATION'):
        drawing = geometry.drawing(m, view)
        label = next(x for x in drawing.texts if x.key == 'door-01.width-label')
        assert label.text == '1200'
        assert label.door_id == 'door-01'
        witness = next(x for x in drawing.lines if x.key == 'door-01.width-line')
        assert math.isclose(witness.points[-1][0]-witness.points[0][0], 1200)


def test_svg_is_valid_and_escapes_manual_notes():
    assert callable(getattr(geometry, 'svg_document', None)), 'svg_document missing'
    m = core.add_note(core.demo_model(), 'door-02', '人工 <check> & test', note_id='n')
    svg = geometry.svg_document(m)
    root = ET.fromstring(svg)
    text = ''.join(root.itertext())
    assert '人工 <check> & test' in text
    assert 'DesignerBIM' in text
    assert root.attrib['width'] == '420mm'


def test_review_state_is_exposed_without_overwriting_note_body():
    m = core.add_note(core.demo_model(), 'door-02', 'Keep this text', note_id='n')
    m = core.set_width(m, 'door-02', 1100)
    assert callable(getattr(geometry, 'drawing', None)), 'drawing missing'
    d = geometry.drawing(m, 'ELEVATION')
    assert any(t.text == 'Keep this text' and t.role == 'manual' for t in d.texts)
    assert any('REVIEW' in t.text and t.role == 'review' for t in d.texts)


def test_geometry_counts_and_vertices_are_valid():
    for p in scene():
        assert len(p.vertices_mm) == 8
        assert len(p.faces) == 6
        assert all(math.isfinite(c) for v in p.vertices_mm for c in v)
        assert all(0 <= i < 8 for f in p.faces for i in f)


def test_a3_dimensions_do_not_hit_footer_or_bottom_border():
    m=core.set_width(core.demo_model(),'door-01',1200)
    root=ET.fromstring(geometry.svg_document(m))
    coords=[]
    for element in root.iter():
        if 'points' in element.attrib:
            coords.extend(float(pair.split(',')[1]) for pair in element.attrib['points'].split())
    assert max(coords)<283, 'Plan witness lines must leave space for footer'
    footer=next(e for e in root.iter() if (e.text or '').startswith('PROTOTYPE'))
    assert float(footer.attrib['y'])>max(coords)+4


def test_default_manual_leader_avoids_door_center_tag():
    m=core.add_note(core.demo_model(),'door-02','note',note_id='n')
    dr=geometry.drawing(m,'ELEVATION')
    leader=next(l for l in dr.lines if l.key=='note.n.leader')
    d=m.doors['door-02']
    assert leader.points[-1]==(d.center_x_mm+d.width_mm/2,d.height_mm)
