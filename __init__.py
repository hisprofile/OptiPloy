bl_info = {
    "name" : 'OptiPloy' ,
    "description" : "Append things like rigs while linking all the useless data back to the source .blend file",
    "author" : "hisanimations",
    "version" : (1, 4, 0),
    "blender" : (3, 0, 0),
    "location" : "View3d > Spawner",
    "support" : "COMMUNITY",
    "category" : "Assets",
    "doc_url": "https://github.com/hisprofile/OptiPloy"
}

base_package = __package__
from . import preferences, panel

def register():
    preferences.register()
    panel.register()

def unregister():
    preferences.unregister()
    panel.unregister()

if __name__ == '__main__':
    register()