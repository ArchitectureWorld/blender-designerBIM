"""Pin the valid text baseline used by the real Blender runtime adapter."""
import ast
from pathlib import Path


def test_drawing_text_uses_supported_blender_baseline():
    source = Path(__file__).resolve().parents[1] / 'designer_bim_p01' / 'addon.py'
    values = [node.value.value for node in ast.walk(ast.parse(source.read_text()))
              if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
              and any(isinstance(t, ast.Attribute) and t.attr == 'align_y' for t in node.targets)]
    assert values == ['BOTTOM_BASELINE']
