"""Generate the actual example .blend using a locally installed Blender 5.2.2.

blender --background --factory-startup --python scripts/create_demo.py -- /path/P01.blend

This is a generator, not a pre-validated .blend file. Use a NEW Blender process.
"""
from pathlib import Path
import sys
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from designer_bim_p01 import addon
assert bpy.app.version==(5,2,2), f'Requires Blender 5.2.2, found {bpy.app.version_string}'
addon.register()
scene=addon.create_demo_scene(bpy.context)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
path=Path(args[0]).expanduser().resolve() if args else ROOT/'samples'/'DesignerBIM_P01.blend'
path.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('Saved generated prototype:',path)
