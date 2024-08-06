IDNAME = 'OptiPloy'
bl_info = {
    "name" : 'OptiPloy' ,
    "description" : "Append things like rigs while linking all the useless data back to the source .blend file",
    "author" : "hisanimations",
    "version" : (1, 0, 0),
    "blender" : (3, 0, 0),
    "location" : "View3d > Spawner",
    "support" : "COMMUNITY",
    "category" : "Assets",
    "doc_url": "https://github.com/hisprofile/OptiDrop"
}

from . import preferences, panel

import os, glob
import importlib, sys
pack_path = os.path.dirname(__file__)
for filename in [*glob.glob('**.py', root_dir=pack_path), *glob.glob('**/*.py', root_dir=pack_path)]:
    #print(filename)
    if filename == os.path.basename(__file__): continue
    module = sys.modules.get("{}.{}".format(__name__,filename[:-3]))
    if module: importlib.reload(module)

def register():
    preferences.register()
    panel.register()

def unregister():
    preferences.unregister()
    panel.unregister()

if __name__ == '__main__':
    register()