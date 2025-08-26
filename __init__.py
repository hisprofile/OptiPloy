bl_info = {
    "name" : 'OptiPloy' ,
    "description" : "Improve your workflow with smarter linking tools!",
    "author" : "hisanimations",
    "version" : (1, 6, 3),
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