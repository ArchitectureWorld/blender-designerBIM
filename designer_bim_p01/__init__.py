"""DesignerBIM Prototype 01. Core modules also run without Blender."""

def register():
    from . import addon
    addon.register()

def unregister():
    from . import addon
    addon.unregister()
