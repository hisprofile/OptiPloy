bl_info = {
    "name" : 'OptiPloy' ,
    "description" : "Append things like rigs while linking all the useless data back to the source .blend file",
    "author" : "hisanimations",
    "version" : (1, 1, 0),
    "blender" : (3, 0, 0),
    "location" : "View3d > Spawner",
    "support" : "COMMUNITY",
    "category" : "Assets",
    "doc_url": "https://github.com/hisprofile/OptiPloy"
}

base_package = __package__
from . import preferences, panel, transmitter, tx_rx

def register():
    preferences.register()
    panel.register()
    transmitter.register()
    tx_rx.register()

def unregister():
    preferences.unregister()
    panel.unregister()
    transmitter.unregister()

if __name__ == '__main__':
    register()