import bpy
from .__init__ import IDNAME

import typing
import os
from bpy.props import *
from bpy.types import Operator
from glob import glob

def scan(item, skip = False) -> list:
    itemType = item.bl_rna.identifier
    if itemType == 'blends':
        if (len(item.objects) + len(item.collections) != 0) and skip:
            #print(f'"{item.name}" has spawnables defined, and skip has been set to true. Skipping!')
            return
        print(f'Opening {item.filepath}...')
        with bpy.data.libraries.load(item.filepath, assets_only=True) as (From, To):
            pass
        print(f'Opened!')
        print(f'Found {len(From.objects)} object(s)')
        item.objects.clear()
        for obj in From.objects:
            new = item.objects.add()
            new.name = obj
        print(f'Found {len(From.collections)} collection(s)')
        item.collections.clear()
        for col in From.collections:
            new = item.collections.add()
            new.name = col
        del From, To
    
    if itemType == 'folders':
        blends = glob('*.blend', root_dir=item.filepath)
        for blend in blends:
            if (item.get(blend) != None) and skip: continue
            blend_path = os.path.join(item.filepath, blend)
            if not os.path.exists(blend_path): continue
            print(f'Opening {blend_path}...')
            with bpy.data.libraries.load(blend_path, assets_only=True) as (From, To):
                pass
            if len(From.objects) + len(From.collections) == 0:
                continue
            print(f'Opened!')
            print(f'Found {len(From.objects)} object(s)')
            newBlend = item.blends.add()
            newBlend.name = blend

            for obj in From.objects:
                new = newBlend.objects.add()
                new.name = obj
            for col in From.collections:
                new = newBlend.collections.add()
                new.name = col
            

class SPAWNER_OT_SCAN(Operator):
    bl_idname = 'spawner.scan'
    bl_label = 'Scanner'
    bl_description = 'Combs through .blend files to look for spawnable objects or collections'

    blend: IntProperty(name='.blend file', default=-1)
    scan_blend: BoolProperty(default=False, name='Scan .blend Files', description='Comb through all the .blend entries to prep them to spawn from')
    folder: IntProperty(name='Folder', default=-1)
    scan_folder: BoolProperty(default=False, name='Scan Folders', description='Comb through all the folder entries to prep them to spawn from')
    skip_scanned: BoolProperty(default=True, name='Skip Scanned', description='Skips .blend files that were already scanned, leaving to only scan the new ones')

    def execute(self, context):
        prefs = context.preferences.addons[IDNAME].preferences
        blend = self.blend
        sBlend = self.scan_blend
        folder = self.folder
        sFolder = self.scan_folder
        skip = self.skip_scanned

        if sBlend:
            for blend in prefs.blends:
                scan(blend, skip)
            return {'FINISHED'}
        if sFolder:
            for folder in prefs.folders:
                scan(folder, skip)
            return {'FINISHED'}
        if blend != -1 and folder == -1:
            scan(blend)
            return {'FINISHED'}
        
        if folder != -1 and blend == -1:
            scan(folder)
            return {'FINISHED'}
        
        if not -1 in {folder, blend}:
            scan(prefs.folders[folder].blends[blend])
            return {'FINISHED'}

        return {'FINISHED'}