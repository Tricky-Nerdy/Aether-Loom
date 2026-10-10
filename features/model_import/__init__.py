from . import ffxiv_character_ot
from . import panels
from . import textools_ui
from . import vrm_ot

modules = (ffxiv_character_ot, vrm_ot, panels, textools_ui)

def register():
    for mod in modules:
        mod.register()

def unregister():
    for mod in modules:
        mod.unregister()
