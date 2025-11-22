bl_info = {
    "name" : 'OptiPloy' ,
    "description" : "Improve your workflow with smarter linking tools!",
    "author" : "hisanimations",
    "version" : (1, 8, 1),
    "blender" : (3, 4, 0),
    "location" : "View3d > Spawner",
    "support" : "COMMUNITY",
    "category" : "Assets",
    "doc_url": "https://github.com/hisprofile/OptiPloy"
}

base_package = __package__
from . import preferences, panel, load_operators, id_tools

def register():
    preferences.register()
    panel.register()
    load_operators.register()
    id_tools.register()

def unregister():
    preferences.unregister()
    panel.unregister()
    load_operators.unregister()
    id_tools.unregister()

if __name__ == '__main__':
    register()