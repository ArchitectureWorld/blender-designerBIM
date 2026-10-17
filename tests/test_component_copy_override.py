"""Copy validates the resolved component, never a temporary shared-only shape."""
from designer_bim_p01 import core


def test_copy_small_opening_keeps_local_frame_override_before_validation():
    m = core.set_component_part(core.demo_model(), 'door-01', 'FRAME', 15, scope='INSTANCE')
    m = core.set_width(m, 'door-01', 350)
    m = core.set_component_part(m, 'door-02', 'FRAME', 150, scope='DEFINITION')
    n = core.copy_door(m, 'door-01', 3000, instance_id='copy-local')
    assert n.doors['copy-local'].width_mm == 350
    assert n.doors['copy-local'].frame_section_override_mm == 15
    assert core.effective_definition(n, 'copy-local').frame_section_mm == 15
    assert n.doors['copy-local'].definition_id == m.doors['door-01'].definition_id
    assert n.revision == m.revision + 1
