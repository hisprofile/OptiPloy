import bpy
from . import base_package

import os
from glob import glob

from bpy.props import (StringProperty, CollectionProperty,
                        IntProperty, EnumProperty,
                        BoolProperty, PointerProperty)
from bpy.types import (UIList, PropertyGroup,
                        AddonPreferences, Operator)

from bpy_extras.io_utils import ImportHelper

def sorter(self, context):
    prefs = context.preferences.addons[base_package].preferences
    indices = sorted([(i.name.lower(), i.name, n) for n, i in enumerate(prefs.blends)], key=lambda a: a[0], reverse=True)
    if indices:
        active = prefs.blends[prefs.blend_index].name

        for blend, b, n in indices:
            #ind = prefs.blends.find(n)
            prefs.blends.move(n, 0)

        prefs.blend_index = prefs.blends.find(active)

    indices = sorted([(i.name.lower(), i.name) for i in prefs.folders], key=lambda a: a[0], reverse=True)
    if indices:
        active = prefs.folders[prefs.folder_index].name
        for folder, f in indices:
            ind = prefs.folders.find(f)
            prefs.folders.move(ind, 0)

        prefs.folder_index = prefs.folders.find(active)

def exists(self, context):
    prefs = context.preferences.addons[base_package].preferences
    for blend in prefs.blends:
        blend.exists = os.path.exists(blend.filepath)
    
    for folder in prefs.folders:
        folder.exists = os.path.exists(folder.filepath)

def blends_CB(self, context):
    prefs = context.preferences.addons[base_package].preferences
    items = []
    for n, blend in enumerate(prefs.blends):
        items.append((blend.name, blend.name, 'This is a .blend file!', 'BLENDER', n))
    return items

def folders_CB(self, context):
    prefs = context.preferences.addons[base_package].preferences
    items = []
    for n, folder in enumerate(prefs.folders):
        items.append((folder.name, folder.name, 'This is a folder!', 'FILE_FOLDER', n))
    return items

def folders_blend_CB(self, context):
    prefs = context.preferences.addons[base_package].preferences
    items = []
    folder = context.scene.optiploy_props.selected_folder
    for n, blend in enumerate(prefs.folders[folder].blends):
        items.append((blend.name, blend.name, 'This is a .blend file!', 'BLENDER', n))
    return items

class objects(PropertyGroup):
    name: StringProperty(default='')

class collections(PropertyGroup):
    name: StringProperty(default='')

class blends(PropertyGroup):
    objects: CollectionProperty(type=objects, name='Spawnables', description='List of spawnable items detected in this .blend file')
    collections: CollectionProperty(type=collections, name='Spawnables', description='List of spawnable items detected in this .blend file')
    filepath: StringProperty(name='Filepath', description='Path to a .blend file', options=set(), subtype='FILE_PATH', update=exists)
    name: StringProperty(name='Name')#, update=sorter)
    exists: BoolProperty(default=True)

    override_behavior: BoolProperty(default=False, name='Override Behavior')
    localize_collections: BoolProperty(name='Localize collections', description='Fully localize new collections. Will not include new objects from the source .blend file',default=True, options=set())
    localize_objects: BoolProperty(default=False, name='Localize all linked objects', options=set())
    localize_meshes: BoolProperty(default=False, name='Localize all linked mesh data', options=set())
    localize_materials: BoolProperty(default=False, name='Localize all linked materials', options=set())
    localize_node_groups: BoolProperty(default=False, name='Localize all linked node groups', options=set())
    localize_images: BoolProperty(default=False, name='Localize all linked images', options=set())
    localize_armatures: BoolProperty(default=False, name='Localize all armatures', options=set())

    localize_lights:        BoolProperty(default=False, name='Localize lights', options=set())
    localize_cameras:       BoolProperty(default=False, name='Localize cameras', options=set())
    localize_curves:        BoolProperty(default=False, name='Localize curves', options=set())
    localize_text_curves:   BoolProperty(default=False, name='Localize text curves', options=set())
    localize_metaballs:     BoolProperty(default=False, name='Localize metaballs', options=set())
    localize_surface_curves:BoolProperty(default=False, name='Localize surface curves', options=set())
    localize_volumes:       BoolProperty(default=False, name='Localize volumes', options=set())
    localize_grease_pencil: BoolProperty(default=False, name='Localize grease pencil', options=set())

class folders(PropertyGroup):
    blends: CollectionProperty(type=blends, name='.blend files', description='List of .blend files under this folder.')
    blend_index: IntProperty(default=0)
    filepath: StringProperty(name='Folder Path', description='Path to this directory', subtype='DIR_PATH', update=exists)
    name: StringProperty(name='Name')#, options=set(), update=sorter)
    exists: BoolProperty(default=False)
    selected_blend: EnumProperty(items=folders_blend_CB, name='Selected .blend', description='Selected .blend file under active folder')

    override_behavior:      BoolProperty(default=False, name='Override Behavior')
    localize_collections:   BoolProperty(name='Localize collections', description='Fully localize new collections. Will not include new objects from the source .blend file',default=True, options=set())
    localize_objects:       BoolProperty(default=False, name='Localize all linked objects', options=set())
    localize_meshes:        BoolProperty(default=False, name='Localize all linked mesh data', options=set())
    localize_materials:     BoolProperty(default=False, name='Localize all linked materials', options=set())
    localize_node_groups:   BoolProperty(default=False, name='Localize all linked node groups', options=set())
    localize_images:        BoolProperty(default=False, name='Localize all linked images', options=set())
    localize_armatures:     BoolProperty(default=False, name='Localize all armatures', options=set())

    localize_lights:        BoolProperty(default=False, name='Localize lights', options=set())
    localize_cameras:       BoolProperty(default=False, name='Localize cameras', options=set())
    localize_curves:        BoolProperty(default=False, name='Localize curves', options=set())
    localize_text_curves:   BoolProperty(default=False, name='Localize text curves', options=set())
    localize_metaballs:     BoolProperty(default=False, name='Localize metaballs', options=set())
    localize_surface_curves:BoolProperty(default=False, name='Localize surface curves', options=set())
    localize_volumes:       BoolProperty(default=False, name='Localize volumes', options=set())
    localize_grease_pencil: BoolProperty(default=False, name='Localize grease pencil', options=set())

class BLENDS_SPAWNER_UL_List(UIList):
    def draw_item(self, context,
            layout, data,
            item, icon,
            active_data, active_propname,
            index):
        prefs = context.preferences.addons[base_package].preferences
        row = layout.row()
        row.alignment = 'EXPAND'
        row.label(text='', icon='BLENDER' if item.exists else 'CANCEL')
        
        if data.blends[data.blend_index] == item:
            row.prop(item, 'name', text='', expand=True)
        else:
            row.label(text=item.name)

        row = row.row()
        row.alignment = 'RIGHT'
        row.label(text=str(len(item.objects)), icon='OBJECT_DATA')
        row.label(text=str(len(item.collections)), icon='OUTLINER_COLLECTION')
        op = row.operator('spawner.scan')
        op.blend = index
        op.folder = -1
        if data != prefs:
            op.folder = prefs.folders.find(data.name)


class FOLDERS_SPAWNER_UL_List(UIList):
    def draw_item(self, context,
            layout, data,
            item, icon,
            active_data, active_propname,
            index):
        prefs = context.preferences.addons[base_package].preferences
        folders = prefs.folders
        row = layout.row()
        row.label(text='', icon='FILE_FOLDER' if item.exists else 'CANCEL')
        if prefs.folders[prefs.folder_index] == item:
            row.prop(item, 'name', text='')
        else:
            row.label(text=item.name)
        row = row.row()
        row.alignment='RIGHT'
        row.label(text=str(len(item.blends)), icon='BLENDER')
        op = row.operator('spawner.scan')
        op.folder = prefs.folders.find(item.name)
        op.blend = -1

class SPAWNER_GENERIC_UL_List(UIList):
    def draw_item(self, context,
            layout, data,
            item, icon,
            active_data, active_propname,
            index):
        layout.label(text=item.name)

class blendentriespref(AddonPreferences):
    bl_idname = base_package

    blends: CollectionProperty(type=blends)
    blend_index: IntProperty(name='Blend Entry Index', min=0, options=set())
    selected_blend: EnumProperty(items=blends_CB, options=set(), name='Selected .blend File', description='Selected .blend file')
    blend_more_info: BoolProperty(default=False, name='Show More', description='Show more of the selected .blend file', options=set())

    folders: CollectionProperty(type=folders)
    folder_index: IntProperty(name='Folder Entry Index', min=0, options=set())
    selected_folder: EnumProperty(items=folders_CB, options=set(), name='Selected Folder', description='Selected Folder')
    folder_more_info: BoolProperty(default=False, name='Show More', description='Show more of the selected .blend file', options=set())
    folder_blend_more_info: BoolProperty(default=False, name='Show More', description='Show more of the selected .blend file', options=set())

    null: IntProperty(min=0, max=0)

    to_cursor: BoolProperty(default=True, name='Move Parents to Cursor', options=set())

    localize_collections:   BoolProperty(name='Localize collections', description='Fully localize new collections. Will not include new objects from the source .blend file',default=True, options=set())
    localize_objects:       BoolProperty(default=True, name='Localize linked objects', options=set())
    localize_meshes:        BoolProperty(default=False, name='Localize linked mesh data', options=set())
    localize_materials:     BoolProperty(default=False, name='Localize linked materials', options=set())
    localize_node_groups:   BoolProperty(default=False, name='Localize linked node groups', options=set())
    localize_images:        BoolProperty(default=False, name='Localize linked images', options=set())
    localize_armatures:     BoolProperty(default=False, name='Localize armatures', options=set())

    localize_lights:        BoolProperty(default=False, name='Localize lights', options=set())
    localize_cameras:       BoolProperty(default=False, name='Localize cameras', options=set())
    localize_curves:        BoolProperty(default=False, name='Localize curves', options=set())
    localize_text_curves:   BoolProperty(default=False, name='Localize text curves', options=set())
    localize_metaballs:     BoolProperty(default=False, name='Localize metaballs', options=set())
    localize_surface_curves:BoolProperty(default=False, name='Localize surface curves', options=set())
    localize_volumes:       BoolProperty(default=False, name='Localize volumes', options=set())
    localize_grease_pencil: BoolProperty(default=False, name='Localize grease pencil', options=set())
    
    #library_overrides: BoolProperty(default=False, name='Make Library Overrides', description='Make objects and their data partially editable. You may still modify properties, such as shape keys',options=set())
    
    execute_scripts: BoolProperty(default=True, name='Execute Attached Scripts', options=set())
    

    def draw(self, context):
        layout = self.layout

        op = layout.row().operator('spawner.textbox', text="Assets not showing?", icon='QUESTION')
        op.text = 'In OptiPloy, collections or objects need to be marked as "Assets" if they are to be used. If the scanning isn\'t returning any results, try marking objects or collections as assets.'
        op.size = '56'
        op.icons = 'ASSET_MANAGER'
        op.width=350
        layout.row().label(text='.blend entries', icon='BLENDER')
        box = layout.box()
        row = box.row()
        row.template_list('BLENDS_SPAWNER_UL_List', 'Blends', self, 'blends', self, 'blend_index')
        col = row.column()
        col.operator('spawner.add_entry', text='', icon='ADD').blends=True
        col.operator('spawner.remove_entry', text='', icon='REMOVE').blends=True

        if (len(self.blends) != 0) and (self.blend_index < len(self.blends)):
            blend = self.blends[self.blend_index]
            box.row().prop(blend, 'filepath')
            row = box.row()
            row.prop(self, 'blend_more_info', toggle=True)
            if self.blend_more_info:

                box.row().label(text='Objects', icon='OBJECT_DATA')
                objBox = box.box()
                if len(blend.objects) > 0:
                    objBox.template_list('SPAWNER_GENERIC_UL_List', 'Objects', blend, 'objects', self, 'null')
                else:
                    objBox.label(text='No objects!')
                
                box.row().label(text='Collections', icon='OUTLINER_COLLECTION')
                colBox = box.box()
                if len(blend.collections) > 0:
                    colBox.template_list('SPAWNER_GENERIC_UL_List', 'Collections', blend, 'collections', self, 'null')
                else:
                    colBox.label(text='No collections!')

        layout.row().label(text='Folder entries', icon='FILE_FOLDER')
        box = layout.box()
        row = box.row()
        row.template_list('FOLDERS_SPAWNER_UL_List', 'Folders', self, 'folders', self, 'folder_index')
        col = row.column()
        col.operator('spawner.add_entry', text='', icon='ADD').blends=False
        col.operator('spawner.remove_entry', text='', icon='REMOVE').blends=False

        if (len(self.folders) != 0) and (self.folder_index < len(self.folders)):
            folder = self.folders[self.folder_index]
            box.row().prop(folder, 'filepath')
            row = box.row()
            row.prop(self, 'folder_more_info', toggle=True)
            if self.folder_more_info and len(folder.blends) > 0:
                blend = folder.blends[max(min(folder.blend_index, len(folder.blends)-1), 0)]
                row = box.row()
                row.template_list('BLENDS_SPAWNER_UL_List', '.blend files', folder, 'blends', folder, 'blend_index')
                box.row().label(text='Objects', icon='OBJECT_DATA')
                objBox = box.box()
                if len(blend.objects) > 0:
                    objBox.template_list('SPAWNER_GENERIC_UL_List', 'Objects', blend, 'objects', self, 'null')
                else:
                    objBox.label(text='No objects!')
                box.row().label(text='Collections', icon='OUTLINER_COLLECTION')
                colBox = box.box()
                if len(blend.collections) > 0:    
                    colBox.template_list('SPAWNER_GENERIC_UL_List', 'Collections', blend, 'collections', self, 'null')
                else:
                    colBox.label(text='No collections!')
        
class SPAWNER_OT_Add_Entry(Operator, ImportHelper):
    bl_idname = 'spawner.add_entry'
    bl_label = 'Add Blend Entry'
    bl_description = 'Add a .blend file to spawn from'

    filepath: StringProperty()
    directory: StringProperty()
    blends: BoolProperty(default=True)
    filter_glob: StringProperty(default='*.blend')

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences
        if self.blends:
            new_entry = prefs.blends.add()
            new_entry.filepath = self.filepath
            new_entry.filepath = bpy.path.abspath(new_entry.filepath) # just in case
            name = os.path.basename(self.filepath).rsplit('.', maxsplit=1)[0]
            new_entry.name = name
            prefs.blend_index = prefs.blends.find(name)
            bpy.ops.spawner.scan(blend=prefs.blend_index, folder=-1, scan_blend=False, scan_folder=False)
            
        else:
            new_entry = prefs.folders.add()
            new_entry.filepath = self.directory
            new_entry.filepath = bpy.path.abspath(new_entry.filepath) # just in case
            name = os.path.basename(self.directory.rstrip("\\/"))
            new_entry.name = name
            prefs.folder_index = prefs.folders.find(name)
            bpy.ops.spawner.scan(blend=-1, folder=prefs.folder_index, scan_blend=False, scan_folder=False)

        return {'FINISHED'}
    
class SPAWNER_OT_Remove_Entry(Operator):
    bl_idname = 'spawner.remove_entry'
    bl_label = 'Remove Blend Entry'
    bl_description = 'Add a .blend file to spawn from'

    blends: BoolProperty(default=True)

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences
        if self.blends:
            index = prefs.blend_index
            prefs.blend_index -= 1
            prefs.blends.remove(index)
        else:
            index = prefs.folder_index
            prefs.folder_index -= 1
            prefs.folders.remove(index)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
    

def scan(item, skip = False) -> list:
    itemType = item.bl_rna.identifier
    if itemType == 'blends':
        if (len(item.objects) + len(item.collections) != 0) and skip:
            return
        print(f'Opening {item.filepath}...')
        with bpy.data.libraries.load(item.filepath, assets_only=True) as (From, To):
            pass
        print(f'Opened!')
        print(f'Found {len(From.objects)} object(s)')
        item.objects.clear()
        for obj in sorted(From.objects):
            new = item.objects.add()
            new.name = obj
        print(f'Found {len(From.collections)} collection(s)')
        item.collections.clear()
        for col in sorted(From.collections):
            new = item.collections.add()
            new.name = col
        del From, To
    
    if itemType == 'folders':
        blends = glob('*.blend', root_dir=item.filepath)
        if not skip:
            item.blends.clear()
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
            print(f'Found {len(From.collections)} collections(s)')
            newBlend = item.blends.add()
            newBlend.name = blend
            newBlend.filepath = blend_path

            for obj in sorted(From.objects):
                new = newBlend.objects.add()
                new.name = obj
            for col in sorted(From.collections):
                new = newBlend.collections.add()
                new.name = col
            

class SPAWNER_OT_SCAN(Operator):
    bl_idname = 'spawner.scan'
    bl_label = 'Scan'
    bl_description = 'Combs through .blend files to look for spawnable objects or collections'

    blend: IntProperty(name='.blend file', default=-1)
    scan_blend: BoolProperty(default=False, name='Scan .blend Files', description='Comb through all the .blend entries to prep them to spawn from')
    folder: IntProperty(name='Folder', default=-1)
    scan_folder: BoolProperty(default=False, name='Scan Folders', description='Comb through all the folder entries to prep them to spawn from')
    skip_scanned: BoolProperty(default=True, name='Skip Scanned', description='Skips .blend files that were already scanned, leaving to only scan the new ones')

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences
        blend = self.blend
        sBlend = self.scan_blend
        folder = self.folder
        sFolder = self.scan_folder
        skip = self.skip_scanned

        print(folder, blend)

        if sBlend:
            for blend in prefs.blends:
                scan(blend, skip)
            return {'FINISHED'}
        if sFolder:
            for folder in prefs.folders:
                scan(folder, skip)
            return {'FINISHED'}
        if blend != -1 and folder == -1:
            blend = prefs.blends[blend]
            scan(blend, False)
            return {'FINISHED'}
        
        if folder != -1 and blend == -1:
            folder = prefs.folders[folder]
            scan(folder)
            return {'FINISHED'}
        
        if not -1 in {folder, blend}:
            scan(prefs.folders[folder].blends[blend])
            return {'FINISHED'}

        return {'FINISHED'}
    
class SPAWNER_OT_CONTEXT(Operator):
    bl_idname = 'spawner.context'
    bl_label = 'context'

    def execute(self, context):
        #return {'FINISHED'}
        print(context.property)
        #transmitter.put_to_queue(str(random.random()))
        #loop = asyncio.new_event_loop()
        #asyncio.set_event_loop(loop)
        #asyncio.run(transmitter.write_to_this_hoe(str(random.random())))
        #transmitter.client.write('hello!\n'.encode())
        #transmitter.write('hello!')
        #print(dir(context.ui_list))
        #print('\n'.join(dir(context)))
        #print(context.region)
        #print(context.region_data)
        #print(context)
        #print(context.property)
        #print(context.ui_list)
        #print(context.space_data)
        #print(context.property.index())
        #print(dir(context.property))
        return {'FINISHED'}

class spawner_props(PropertyGroup):
    selected_blend: EnumProperty(items=blends_CB, options=set(), name='Selected .blend File', description='Selected .blend file')
    selected_folder: EnumProperty(items=folders_CB, options=set(), name='Selected Folder', description='Selected Folder')
    view: EnumProperty(items = (
        ('BLENDS', 'Blend Files', 'Spawn from your list of .blend files', 'BLENDER', 0),
        ('FOLDERS', 'Folders', 'Spawn from your list of folders', 'FILE_FOLDER', 1),
        ('TOOLS', 'Tools', 'Choose from the assortment of tools', 'TOOL_SETTINGS', 2)
    ),
    name='View', description='View', options=set()
    )

classes = [
    objects,
    collections,
    blends,
    folders,
    spawner_props,
    BLENDS_SPAWNER_UL_List,
    FOLDERS_SPAWNER_UL_List,
    SPAWNER_GENERIC_UL_List,
    blendentriespref,
    SPAWNER_OT_Add_Entry,
    SPAWNER_OT_Remove_Entry,
    SPAWNER_OT_SCAN,
    SPAWNER_OT_CONTEXT
]

def register():
    for i in classes:
        bpy.utils.register_class(i)

    bpy.types.Scene.optiploy_props = PointerProperty(type=spawner_props)

def unregister():
    for i in reversed(classes):
        bpy.utils.unregister_class(i)
    del bpy.types.Scene.optiploy_props