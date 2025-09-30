import bpy
from . import base_package

import os
from glob import glob

from .load_operators import generictext

from bpy.props import (StringProperty, CollectionProperty,
                        IntProperty, EnumProperty,
                        BoolProperty, PointerProperty)
from bpy.types import (UIList, PropertyGroup,
                        AddonPreferences, Operator)

from .panel import SPAWNER_PT_panel

ref_keeper = dict()

def update_ref_keeper(self, context: bpy.types.Context):
    prefs = context.preferences.addons[__package__].preferences
    ref_keeper.clear()
    for blend in prefs.blends:
        ref_keeper[blend] = blend.name
    for folder in prefs.folders:
        ref_keeper[folder] = folder.name
        for blend in folder.blends:
            ref_keeper[blend] = blend.name

def only(item, *argv):
    for arg in argv:
        if arg != item:
            return False
    return True

def exists(self, context):
    prefs = context.preferences.addons[base_package].preferences
    for blend in prefs.blends:
        blend.exists = os.path.exists(blend.filepath)
    
    for folder in prefs.folders:
        folder.exists = os.path.exists(folder.filepath)

def blends_CB(self, context):
    prefs = context.preferences.addons[base_package].preferences
    for n, blend in enumerate(prefs.blends):
        if not blend in ref_keeper: ref_keeper[blend] = blend.name
        yield (str(n), ref_keeper[blend], 'This is a .blend file!', 'BLENDER', n)

def folders_CB(self, context):
    prefs = context.preferences.addons[base_package].preferences
    for n, folder in enumerate(prefs.folders):
        icon = 'FILE_FOLDER' if not folder.category else 'ASSET_MANAGER'
        if not folder in ref_keeper: ref_keeper[folder] = folder.name
        yield (str(n), ref_keeper[folder], 'This is a folder!', icon, n)

def folders_blend_CB(self, context):
    prefs = context.preferences.addons[base_package].preferences
    folder = context.window_manager.optiploy_props.selected_folder
    for n, blend in enumerate(prefs.folders[int(folder)].blends):
        if not blend in ref_keeper: ref_keeper[blend] = blend.name
        yield (str(n), ref_keeper[blend], 'This is a .blend file!', 'BLENDER', n)

class objects(PropertyGroup):
    name: StringProperty(default='')

class collections(PropertyGroup):
    name: StringProperty(default='')

class blends(PropertyGroup):
    objects: CollectionProperty(type=objects, name='Spawnables', description='List of spawnable items detected in this .blend file')
    collections: CollectionProperty(type=collections, name='Spawnables', description='List of spawnable items detected in this .blend file')
    filepath: StringProperty(name='Filepath', description='Path to a .blend file', options=set(), subtype='FILE_PATH', update=exists)
    name: StringProperty(name='Name', update=update_ref_keeper)
    exists: BoolProperty(default=True)

    override_behavior: BoolProperty(default=False, name='Override Behavior')
    localize_collections:   BoolProperty(name='Localize collections', description='Fully localize new collections. Will not include new objects from the source .blend file',default=True, options=set())
    localize_objects:       BoolProperty(default=False, name='Localize objects', options=set())
    localize_meshes:        BoolProperty(default=False, name='Localize mesh data', options=set())
    localize_materials:     BoolProperty(default=False, name='Localize materials', options=set())
    localize_node_groups:   BoolProperty(default=False, name='Localize node groups', options=set())
    localize_images:        BoolProperty(default=False, name='Localize images', options=set())
    localize_armatures:     BoolProperty(default=False, name='Localize armatures', options=set())
    localize_actions:       BoolProperty(default=True, name='Localize actions', options=set())

    localize_lights:        BoolProperty(default=False, name='Localize lights', options=set())
    localize_cameras:       BoolProperty(default=False, name='Localize cameras', options=set())
    localize_curves:        BoolProperty(default=False, name='Localize curves', options=set())
    localize_text_curves:   BoolProperty(default=False, name='Localize text curves', options=set())
    localize_metaballs:     BoolProperty(default=False, name='Localize metaballs', options=set())
    localize_surface_curves:BoolProperty(default=False, name='Localize surface curves', options=set())
    localize_volumes:       BoolProperty(default=False, name='Localize volumes', options=set())
    localize_grease_pencil: BoolProperty(default=False, name='Localize grease pencil', options=set())

    
    importer: EnumProperty(items=(('FAST', 'Fast', 'Fast importer'), ('STABLE', 'Stable', 'Stable importer')), name='Importer', description='Which importer to use', default='FAST')

class folders(PropertyGroup):
    blends: CollectionProperty(type=blends, name='.blend files', description='List of .blend files under this folder.')
    blend_index: IntProperty(default=0)
    filepath: StringProperty(name='Folder Path', description='Path to this directory', subtype='DIR_PATH', update=exists)
    name: StringProperty(name='Name', update=update_ref_keeper)
    exists: BoolProperty(default=False)
    category: BoolProperty(default=False)
    recursive: BoolProperty(name='Include subfolders', description='Should subfolders be scanned as well?', default=False)
    selected_blend: EnumProperty(items=folders_blend_CB, name='Selected .blend', description='Selected .blend file under active folder')

    override_behavior:      BoolProperty(default=False, name='Override Behavior')
    localize_collections:   BoolProperty(name='Localize collections', description='Fully localize new collections. Will not include new objects from the source .blend file',default=True, options=set())
    localize_objects:       BoolProperty(default=False, name='Localize objects', options=set())
    localize_meshes:        BoolProperty(default=False, name='Localize mesh data', options=set())
    localize_materials:     BoolProperty(default=False, name='Localize materials', options=set())
    localize_node_groups:   BoolProperty(default=False, name='Localize node groups', options=set())
    localize_images:        BoolProperty(default=False, name='Localize images', options=set())
    localize_armatures:     BoolProperty(default=False, name='Localize armatures', options=set())
    localize_actions:       BoolProperty(default=True, name='Localize actions', options=set())

    localize_lights:        BoolProperty(default=False, name='Localize lights', options=set())
    localize_cameras:       BoolProperty(default=False, name='Localize cameras', options=set())
    localize_curves:        BoolProperty(default=False, name='Localize curves', options=set())
    localize_text_curves:   BoolProperty(default=False, name='Localize text curves', options=set())
    localize_metaballs:     BoolProperty(default=False, name='Localize metaballs', options=set())
    localize_surface_curves:BoolProperty(default=False, name='Localize surface curves', options=set())
    localize_volumes:       BoolProperty(default=False, name='Localize volumes', options=set())
    localize_grease_pencil: BoolProperty(default=False, name='Localize grease pencil', options=set())
    
    importer: EnumProperty(items=(('FAST', 'Fast', 'Fast importer'), ('STABLE', 'Stable', 'Stable importer')), name='Importer', description='Which importer to use', default='FAST')

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
        if item.exists:
            icon = 'FILE_FOLDER'
        elif item.category:
            icon = 'ASSET_MANAGER'
        else:
            icon = 'CANCEL'
        row.label(text='', icon=icon)
        if prefs.folders[prefs.folder_index] == item:
            row.prop(item, 'name', text='')
        else:
            row.label(text=item.name)
        row = row.row()
        row.alignment='RIGHT'
        row.label(text=str(len(item.blends)), icon='BLENDER')
        op = row.operator('spawner.scan')
        op.folder = index
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

    def update_blend_show(self, context):
        self['folder_more_info'] = False

    def update_folder_show(self, context):
        self['blend_more_info'] = False

    def category_update(self, context):
        panel = SPAWNER_PT_panel
        if 'bl_rna' in panel.__dict__:
            bpy.utils.unregister_class(panel)
        panel.bl_category = self.category
        bpy.utils.register_class(panel)

    blends: CollectionProperty(type=blends)
    blend_index: IntProperty(name='Blend Entry Index', min=0, options=set())
    selected_blend: EnumProperty(items=blends_CB, options=set(), name='Selected .blend File', description='Selected .blend file')
    blend_more_info: BoolProperty(default=False, name='Show More', description='Show more of the selected .blend file', options=set(), update=update_blend_show)#get=get_blend_show, set=set_blend_show)

    folders: CollectionProperty(type=folders)
    folder_index: IntProperty(name='Folder Entry Index', min=0, options=set())
    selected_folder: EnumProperty(items=folders_CB, options=set(), name='Selected Folder', description='Selected Folder')
    folder_more_info: BoolProperty(default=False, name='Show More', description='Show more of the selected .blend file', options=set(), update=update_folder_show)
    #folder_blend_more_info: BoolProperty(default=False, name='Show More', description='Show more of the selected .blend file', options=set())
    
    obj_index: IntProperty(default=0, options=set())#, update=redraw)
    col_index: IntProperty(default=0, options=set())#, update=redraw)

    null: IntProperty(min=0, max=0)

    to_cursor: BoolProperty(default=True, name='Move Parents to Cursor', options=set())

    localize_collections:   BoolProperty(name='Localize collections', description='Fully localize new collections. Will not include new objects from the source .blend file',default=True, options=set())
    localize_objects:       BoolProperty(default=True, name='Localize objects', options=set())
    localize_meshes:        BoolProperty(default=False, name='Localize mesh data', options=set())
    localize_materials:     BoolProperty(default=False, name='Localize materials', options=set())
    localize_node_groups:   BoolProperty(default=False, name='Localize node groups', options=set())
    localize_images:        BoolProperty(default=False, name='Localize images', options=set())
    localize_armatures:     BoolProperty(default=False, name='Localize armatures', options=set())
    localize_actions:       BoolProperty(default=True, name='Localize actions', options=set())

    localize_lights:        BoolProperty(default=False, name='Localize lights', options=set())
    localize_cameras:       BoolProperty(default=False, name='Localize cameras', options=set())
    localize_curves:        BoolProperty(default=False, name='Localize curves', options=set())
    localize_text_curves:   BoolProperty(default=False, name='Localize text curves', options=set())
    localize_metaballs:     BoolProperty(default=False, name='Localize metaballs', options=set())
    localize_surface_curves:BoolProperty(default=False, name='Localize surface curves', options=set())
    localize_volumes:       BoolProperty(default=False, name='Localize volumes', options=set())
    localize_grease_pencil: BoolProperty(default=False, name='Localize grease pencil', options=set())
    
    objects_to_active_collection: BoolProperty(default=True, name='Assign Objects to Active Collection', description='Assigns imported collections to the active collection in the view layer. If disable, imports will always be assigned to scene collection')
    collections_to_active_collection: BoolProperty(default=False, name='Assign Collections to Active Collection', description='Assigns imported collections to the active collection in the view layer. If disable, imports will always be assigned to scene collection')

    execute_scripts: BoolProperty(default=True, name='Execute Attached Scripts', options=set())

    importer: EnumProperty(items=(('FAST', 'Fast', 'Fast importer'), ('STABLE', 'Stable', 'Stable importer')), name='Importer', description='Which importer to use', default='FAST')

    category: StringProperty(default='OptiPloy', name='Panel Category', description='The Viewport category to place OptiPloy under', update=category_update)

    def set_ops(self, op, type):
        alpha_text = '''This can only be undone through reverting to saved preferences.
Hold SHIFT to reverse sort.'''
        alpha_icons = 'SORTALPHA,EVENT_SHIFT'
        alpha_size = '56,56'
        op.text = alpha_text
        op.icons = alpha_icons
        op.size = alpha_size
        #match type:
        if type == 'BLEND':
            op.blend=True
            op.folder = False
            op.object = False
            op.collection = False
            return
        elif type == 'FOLDER':
            op.blend = False
            op.folder = True
            op.object = False
            op.collection = False
            return
        elif type == 'FOLDER_BLEND':
            op.blend = True
            op.folder = True
            op.object = False
            op.collection = False
            return
        elif type == 'BLEND_OBJECT':
            op.blend = True
            op.folder = False
            op.object = True
            op.collection = False
            return
        elif type == 'BLEND_COLLECTION':
            op.blend = True
            op.folder = False
            op.object = False
            op.collection = True
            return
        elif type == 'FOLDER_BLEND_OBJECT':
            op.blend = True
            op.folder = True
            op.object = True
            op.collection = False
            return
        elif type == 'FOLDER_BLEND_COLLECTION':
            op.blend = True
            op.folder = True
            op.object = False
            op.collection = True
            return
        return

    def draw(self, context):
        layout = self.layout
        alpha_text = '''This can only be undone through reverting to saved preferences.
Hold SHIFT to reverse sort.'''
        alpha_icons = 'SORTALPHA,EVENT_SHIFT'
        alpha_size = '56,56'
        
        layout.prop(self, 'category')
        
        op = layout.row().operator('spawner.textbox', text="Assets not showing?", icon='QUESTION')
        op.text = 'In OptiPloy, collections or objects need to be marked as "Assets" if they are to be used. If the scanning isn\'t returning any results, ensure objects or collections are marked as assets.'
        op.size = '58'
        op.icons = 'ASSET_MANAGER'
        op.width=350
        layout.row().label(text='.blend entries', icon='BLENDER')
        box = layout.box()
        row = box.row()
        row.template_list('BLENDS_SPAWNER_UL_List', 'Blends', self, 'blends', self, 'blend_index')
        col = row.column()

        op = col.operator('spawner.add_entry', text='', icon='ADD')
        op.blend=True
        op.folder = False
        op = col.operator('spawner.remove_entry', text='', icon='REMOVE')
        op.blend = True
        op.folder = False

        col.separator()

        for offset, icon in [(-1, 'TRIA_UP'), (1, 'TRIA_DOWN')]:
            op = col.operator('spawner.move', text='', icon=icon)
            op.offset = offset
            op.blend = True
            op.folder = False
            op.object = False
            op.collection = False

        col.separator()

        op = col.operator('spawner.alpha_sort', text='', icon='SORTALPHA')
        
        op.text = alpha_text
        op.icons = alpha_icons
        op.size = alpha_size
        op.width=310
        op.blend=True
        op.folder=False
        op.object=False
        op.collection=False

        if (len(self.blends) != 0) and (self.blend_index < len(self.blends)):
            blend = self.blends[self.blend_index]
            box.row().prop(blend, 'filepath')
            row = box.row()
            row.prop(self, 'blend_more_info', toggle=True)
            if self.blend_more_info:

                objBox = box.box()
                objBox.row().label(text='Objects', icon='OBJECT_DATA')
                row = objBox.row()
                if len(blend.objects) > 0:
                    row.template_list('SPAWNER_GENERIC_UL_List', 'Objects', blend, 'objects', self, 'obj_index')
                    col = row.column()
                    for offset, icon in [(-1, 'TRIA_UP'), (1, 'TRIA_DOWN')]:
                        op = col.operator('spawner.move', text='', icon=icon)
                        op.offset = offset
                        op.blend = True
                        op.folder = False
                        op.object = True
                        op.collection = False

                    col.separator()

                    op = col.operator('spawner.alpha_sort', text='', icon='SORTALPHA')
                    op.text = alpha_text
                    op.icons = alpha_icons
                    op.size = alpha_size
                    op.width=310
                    op.blend=True
                    op.folder=False
                    op.object=True
                    op.collection=False
                else:
                    row.label(text='No objects!')
                
                colBox = box.box()
                colBox.row().label(text='Collections', icon='OUTLINER_COLLECTION')
                row = colBox.row()
                if len(blend.collections) > 0:
                    row.template_list('SPAWNER_GENERIC_UL_List', 'Collections', blend, 'collections', self, 'col_index')
                    col = row.column()
                    for offset, icon in [(-1, 'TRIA_UP'), (1, 'TRIA_DOWN')]:
                        op = col.operator('spawner.move', text='', icon=icon)
                        op.offset = offset
                        op.blend = True
                        op.folder = False
                        op.object = False
                        op.collection = True
                    col.separator()

                    op = col.operator('spawner.alpha_sort', text='', icon='SORTALPHA')
                    op.text = alpha_text
                    op.icons = alpha_icons
                    op.size = alpha_size
                    op.width=310
                    op.blend=True
                    op.folder=False
                    op.object=False
                    op.collection=True
                else:
                    row.label(text='No collections!')
        row = layout.row()
        #col = layout.column()
        row = row.row()
        row.alignment = 'EXPAND'
        row.label(text='Folder entries', icon='FILE_FOLDER')
        row = row.row()
        row.alignment = 'RIGHT'
        row.label(text='Hold Shift to add a "Category"')
        row = row.row(align=True)
        row.label(text='', icon='ASSET_MANAGER')

        box = layout.box()
        row = box.row()
        row.template_list('FOLDERS_SPAWNER_UL_List', 'Folders', self, 'folders', self, 'folder_index')
        col = row.column()

        op = col.operator('spawner.add_entry', text='', icon='ADD')
        op.blend=False
        op.folder = True
        op = col.operator('spawner.remove_entry', text='', icon='REMOVE')
        op.blend = False
        op.folder = True

        col.separator()

        for offset, icon in [(-1, 'TRIA_UP'), (1, 'TRIA_DOWN')]:
            op = col.operator('spawner.move', text='', icon=icon)
            op.offset = offset
            op.blend = False
            op.folder = True
            op.object = False
            op.collection = False

        col.separator()

        op = col.operator('spawner.alpha_sort', text='', icon='SORTALPHA')
        op.text = alpha_text
        op.icons = alpha_icons
        op.size = alpha_size
        op.width=310
        op.blend=False
        op.folder=True
        op.object=False
        op.collection=False

        if (len(self.folders) != 0) and (self.folder_index < len(self.folders)):
            folder = self.folders[self.folder_index]
            col = box.column(align=False)
            if folder.category:
                box.row().label(text='This is a category, a way to organize separated .blend files.')
            else:
                col.row().prop(folder, 'recursive')
                col.separator()
                col.row().prop(folder, 'filepath')
            row = box.row()
            row.prop(self, 'folder_more_info', toggle=True)
            if self.folder_more_info:# and len(folder.blends) > 0:
                
                row = box.row()
                box = row.box()
                box.row().label(text='.blends', icon='BLENDER')
                row = box.row()
                row.template_list('BLENDS_SPAWNER_UL_List', '.blend files', folder, 'blends', folder, 'blend_index')
                col = row.column()

                op = col.operator('spawner.add_entry', text='', icon='ADD')
                op.blend=True
                op.folder = True
                op = col.operator('spawner.remove_entry', text='', icon='REMOVE')
                op.blend = True
                op.folder = True

                col.separator()#1, 'LINE')

                for offset, icon in [(-1, 'TRIA_UP'), (1, 'TRIA_DOWN')]:
                    op = col.operator('spawner.move', text='', icon=icon)
                    op.offset = offset
                    op.blend = True
                    op.folder = True
                    op.object = False
                    op.collection = False
                col.separator()

                op = col.operator('spawner.alpha_sort', text='', icon='SORTALPHA')
                op.text = alpha_text
                op.icons = alpha_icons
                op.size = alpha_size
                op.width=310
                op.blend=True
                op.folder=True
                op.object=False
                op.collection=False
                if len(folder.blends) > 0:
                    blend = folder.blends[max(min(folder.blend_index, len(folder.blends)-1), 0)]
                    box.row().prop(blend, 'filepath')
                    objBox = box.box()
                    objBox.row().label(text='Objects', icon='OBJECT_DATA')
                    row = objBox.row()
                    if len(blend.objects) > 0:
                        row.template_list('SPAWNER_GENERIC_UL_List', 'Objects', blend, 'objects', self, 'obj_index')
                        col = row.column()
                        for offset, icon in [(-1, 'TRIA_UP'), (1, 'TRIA_DOWN')]:
                            op = col.operator('spawner.move', text='', icon=icon)
                            op.offset = offset
                            op.blend = True
                            op.folder = True
                            op.object = True
                            op.collection = False
                        col.separator()

                        op = col.operator('spawner.alpha_sort', text='', icon='SORTALPHA')
                        op.text = alpha_text
                        op.icons = alpha_icons
                        op.size = alpha_size
                        op.width=310
                        op.blend=True
                        op.folder=True
                        op.object=True
                        op.collection=False
                    else:
                        row.label(text='No objects!')
                    
                    colBox = box.box()
                    colBox.row().label(text='Collections', icon='OUTLINER_COLLECTION')
                    row = colBox.row()
                    if len(blend.collections) > 0:
                        row.template_list('SPAWNER_GENERIC_UL_List', 'Collections', blend, 'collections', self, 'col_index')
                        col = row.column()
                        for offset, icon in [(-1, 'TRIA_UP'), (1, 'TRIA_DOWN')]:
                            op = col.operator('spawner.move', text='', icon=icon)
                            op.offset = offset
                            op.blend = True
                            op.folder = True
                            op.object = False
                            op.collection = True

                        col.separator()

                        op = col.operator('spawner.alpha_sort', text='', icon='SORTALPHA')
                        op.text = alpha_text
                        op.icons = alpha_icons
                        op.size = alpha_size
                        op.width=310
                        op.blend=True
                        op.folder=True
                        op.object=False
                        op.collection=True
                    else:
                        row.label(text='No collections!')
        
class SPAWNER_OT_Add_Entry(Operator):
    bl_idname = 'spawner.add_entry'
    bl_label = 'Add Blend Entry'
    bl_description = 'Add a .blend file to spawn from'

    #bl_options = {''}

    filepath: StringProperty()
    directory: StringProperty()
    blend: BoolProperty(default=True, options={'HIDDEN'})
    folder: BoolProperty(default=False, options={'HIDDEN'})
    filter_glob: StringProperty(default='*.blend', options={'HIDDEN'})
    execute_only: BoolProperty(default=False, options={'HIDDEN'})
    category: BoolProperty(default=False, options={'HIDDEN'})
    category_name: StringProperty(default='', options={'HIDDEN'})
    folder_select: IntProperty(default=-1, options={'HIDDEN'})
    folder_recursive: BoolProperty(name='Folder Recursive Scan', description='Add recursive scans for folders and its sub-folders', default=False)
    _shift = None

    def invoke(self, context, event):
        if self.execute_only:
            self.execute_only = False
            return self.execute(context)
        self._shift = event.shift
        if self.folder and self._shift:
            return self.execute(context)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences

        if self.blend and self.folder:
            if not os.path.exists(self.filepath):
                self.report({'ERROR'}, f'{self.filepath} does not exist!')
                return {'CANCELLED'}
            folder = prefs.folders[prefs.folder_index]
            if self.folder_select > -1:
                folder = prefs.folders[self.folder_select]
                self.folder_select = -1
            new_entry = folder.blends.add()
            new_entry.filepath = self.filepath
            name = os.path.basename(self.filepath).rsplit('.', maxsplit=1)[0]
            new_entry.name = name
            scan(self, context, new_entry)
        elif self.blend:
            if not os.path.exists(self.filepath):
                self.report({'ERROR'}, f'{self.filepath} does not exist!')
                return {'CANCELLED'}
            new_entry = prefs.blends.add()
            new_entry.filepath = self.filepath
            new_entry.filepath = bpy.path.abspath(new_entry.filepath) # just in case
            name = os.path.basename(self.filepath).rsplit('.', maxsplit=1)[0]
            new_entry.name = name
            scan(self, context, new_entry)
        else:
            if not os.path.exists(self.directory) and not self._shift:
                self.report({'ERROR'}, f'{self.directory} does not exist!')
                return {'CANCELLED'}
            new_entry = prefs.folders.add()
            if self._shift or self.category:
                new_name = 'New Category'
                if self.category:
                    new_name = self.category_name
                self.category = False
                new_entry.category = True
                new_entry.name = new_name
            else:
                new_entry.filepath = self.directory
                new_entry.recursive = self.folder_recursive
                directory: str = self.directory
                directory = directory.removesuffix('/')
                directory = directory.removesuffix('\\')
                name = os.path.basename(directory)
                new_entry.name = name
                scan(self, context, new_entry)
        context.window_manager.progress_end()
        return {'FINISHED'}
    
class SPAWNER_OT_Remove_Entry(Operator):
    bl_idname = 'spawner.remove_entry'
    bl_label = 'Remove Blend Entry'
    bl_description = 'Add a .blend file to spawn from'

    blend: BoolProperty(default=True)
    folder: BoolProperty(default=False)

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences
        if self.blend and self.folder:
            folder = prefs.folders[prefs.folder_index]
            folder.blends.remove(folder.blend_index)
            folder.blend_index -= 1
        elif self.blend:
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

def scan(op: bpy.types.Operator, context: bpy.types.Context, item, skip = False):
    wm = context.window_manager
    wm.progress_begin(0, 9999)
    wm.progress_update(0)
    failed = 0

    itemType = item.bl_rna.identifier
    if itemType == 'blends':
        if (len(item.objects) + len(item.collections) != 0) and skip:
            return
        wm.progress_update(1)
        if not os.path.exists(item.filepath):
            op.report({'ERROR'}, f'{item.filepath} does not exist!')
            return {'CANCELLED'}
        print(f'Opening {item.filepath}...')
        try:
            if bpy.data.filepath == item.filepath:
                class From:
                    objects = [obj.name for obj in bpy.data.objects if obj.asset_data]
                    collections = [col.name for col in bpy.data.collections if col.asset_data]
                class To:
                    pass
            else:
                with bpy.data.libraries.load(item.filepath, assets_only=True) as (From, To):
                    pass
        except:
            op.report({'ERROR'}, f'Could not open {item.filepath}! Is it corrupt?')
            return {'CANCELLED'}
        print(f'Opened!')
        item.objects.clear()
        item.collections.clear()
        if len(From.objects) + len(From.collections) == 0:
            op.report({'WARNING'}, f'{item.filepath} does not have any objects or collections marked as assets!')
            return {'FINISHED'}
        wm.progress_update(2)
        print(f'Found {len(From.objects)} object(s)')
        for obj in sorted(From.objects):
            new = item.objects.add()
            new.name = obj

        wm.progress_update(3)
        print(f'Found {len(From.collections)} collection(s)')
        for col in sorted(From.collections):
            new = item.collections.add()
            new.name = col
        del From, To
        return {'FINISHED'}
    
    if itemType == 'folders':
        print(f'Recursive Scan: {item.recursive}')

        globPath = '*.blend'
        if item.recursive:
            globPath = '**/' + globPath
        
        blends = glob(globPath, root_dir=item.filepath, recursive=item.recursive)
        print(f'Scan result count: {len(blends)}')
        
        if not skip:
            item.blends.clear()
        wm.progress_update(1)
        for n, blend in enumerate(blends):
            if (item.get(blend) != None) and skip: continue
            blend_path = os.path.join(item.filepath, blend)
            if not os.path.exists(blend_path): continue
            wm.progress_update(n*10)
            print(f'Opening {blend_path}...')
            try:
                if bpy.data.filepath == blend_path:
                    class From:
                        objects = [obj.name for obj in bpy.data.objects if obj.asset_data]
                        collections = [col.name for col in bpy.data.collections if col.asset_data]
                    class To:
                        pass
                else:
                    with bpy.data.libraries.load(blend_path, assets_only=True) as (From, To):
                        pass
            except:
                op.report({'ERROR'}, f'Could not open {blend_path}! Is it corrupt?')
                failed += 1
                continue
            print(f'Opened!')
            print(f'Found {len(From.objects)} object(s)')
            print(f'Found {len(From.collections)} collections(s)')
            newBlend = item.blends.add()
            newBlend.name = os.path.splitext(blend)[0]
            newBlend.filepath = blend_path
            wm.progress_update(n*10+1)
            for obj in sorted(From.objects):
                new = newBlend.objects.add()
                new.name = obj
            wm.progress_update(n*10+2)
            for col in sorted(From.collections):
                new = newBlend.collections.add()
                new.name = col
        if failed:
            op.report({'WARNING'}, f'{failed} error(s) occured. Read INFO to learn more')
        return {'FINISHED'}

class SPAWNER_OT_SCAN(Operator):
    bl_idname = 'spawner.scan'
    bl_label = 'Scan'
    bl_description = 'Combs through .blend files to look for spawnable objects or collections'

    blend: IntProperty(name='.blend file', default=-1)
    folder: IntProperty(name='Folder', default=-1)

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences
        blend = self.blend
        folder = self.folder

        if blend != -1 and folder == -1:
            blend = prefs.blends[blend]
            return_val = scan(self, context, blend, False)
            context.window_manager.progress_end()
            return return_val
        
        if folder != -1 and blend == -1:
            folder = prefs.folders[folder]
            if folder.category:
                for blend in folder.blends:
                    scan(self, context, blend)
                return_val = {'FINISHED'}
            else:
                return_val = scan(self, context, folder)
            context.window_manager.progress_end()
            return return_val
        
        if not -1 in {folder, blend}:
            blend = prefs.folders[folder].blends[blend]
            return_val = scan(self, context, blend)
            context.window_manager.progress_end()
            return return_val

        return {'FINISHED'}
    
class SPAWNER_OT_ALPHA_SORT(generictext):
    bl_idname = 'spawner.alpha_sort'
    bl_label = 'Sort by Alphabet'
    bl_description = 'Hold SHIFT to sort backwards'

    blend:      BoolProperty(default=False)
    folder:     BoolProperty(default=False)
    object:     BoolProperty(default=False)
    collection: BoolProperty(default=False)

    _shift = None

    def invoke_extra(self, context, event):
        self._shift = event.shift
    
    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences

        B = self.blend
        F = self.folder
        O = self.object
        C = self.collection

        if B == True and only(False, F, O, C):
            item = prefs.blends
        
        if F == True and only(False, B, O, C):
            item = prefs.folders
        
        if only(True, B, F) and only(False, O, C):
            folder = prefs.folders[prefs.folder_index]
            item = folder.blends
        
        if F == False:
            blend = prefs.blends[prefs.blend_index]
        else:
            folder = prefs.folders[prefs.folder_index]
            blend = folder.blends[folder.blend_index]

        if O == True:
            item = blend.objects
        
        if C == True:
            item = blend.collections

        ln = enumerate(item)

        rev = sorted(ln, key=lambda a: a[1].name.casefold())
        if not self._shift:
            rev = reversed(rev)
        rev = list(map(lambda a: a[0], rev))

        for i in rev:
            item.move(i, 0)
            for n, _ in enumerate(rev):
                val = rev[n]
                if val < i:
                    rev[n] += 1
        update_ref_keeper(self, context)
        return {'FINISHED'}
    
class SPAWNER_OT_MOVE(Operator):
    bl_idname = 'spawner.move'
    bl_label = 'Move'
    bl_description = 'Hold SHIFT to move an item to the top or bottom'

    offset:     IntProperty(default=0)
    blend:      BoolProperty(default=False)
    folder:     BoolProperty(default=False)
    object:     BoolProperty(default=False)
    collection: BoolProperty(default=False)
    _shift = None

    def invoke(self, context, event):
        self._shift = event.shift
        return self.execute(context)
    
    def move(self, context):
        prefs = context.preferences.addons[base_package].preferences

        B = self.blend
        F = self.folder
        O = self.object
        C = self.collection
        offset = self.offset

        if B == True and only(False, F, O, C):
            item = prefs.blends
            index = prefs.blend_index
            maxlen = len(item) - 1
            if self._shift:
                offset = 0 if (offset < 0) else maxlen
            else:
                offset = index + offset
            offset = min(max(offset, 0), maxlen)
            item.move(index, offset)
            prefs.blend_index = offset
            return {'FINISHED'}
        
        if F == True and only(False, B, O, C):
            item = prefs.folders
            index = prefs.folder_index
            maxlen = len(item) - 1
            if self._shift:
                offset = 0 if (offset < 0) else maxlen
            else:
                offset = index + offset
            offset = min(max(offset, 0), maxlen)
            item.move(index, offset)
            prefs.folder_index = offset
            return {'FINISHED'}
        
        if only(True, B, F) and only(False, O, C):
            folder = prefs.folders[prefs.folder_index]
            item = folder.blends
            index = folder.blend_index
            maxlen = len(item) - 1
            if self._shift:
                offset = 0 if (offset < 0) else maxlen
            else:
                offset = index + offset
            offset = min(max(offset, 0), maxlen)
            item.move(index, offset)
            folder.blend_index = offset
            return {'FINISHED'}
        
        if F == False:
            blend = prefs.blends[prefs.blend_index]
        else:
            folder = prefs.folders[prefs.folder_index]
            blend = folder.blends[folder.blend_index]


        if O == True:
            item = blend.objects
            index = prefs.obj_index
            maxlen = len(item) - 1
            if self._shift:
                offset = 0 if (offset < 0) else maxlen
            else:
                offset = index + offset
            offset = min(max(offset, 0), maxlen)
            item.move(index, offset)
            prefs.obj_index = offset
            return {'FINISHED'}
        
        if C == True:
            item = blend.collections
            index = prefs.col_index
            maxlen = len(item) - 1
            if self._shift:
                offset = 0 if (offset < 0) else maxlen
            else:
                offset = index + offset
            offset = min(max(offset, 0), maxlen)
            item.move(index, offset)
            prefs.col_index = offset
            return {'FINISHED'}
        return {'FINISHED'}

    def execute(self, context):
        self.move(context)
        update_ref_keeper(self, context)
        return {'FINISHED'}
    
class SPAWNER_OT_CONTEXT(Operator):
    bl_idname = 'spawner.context'
    bl_label = 'context'

    def execute(self, context):
        print(context.space_data, context.area.type, context.window, context.screen)
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

    @classmethod
    def register(cls):
        from .props_append import extra_register
        for reg in extra_register:
            reg(cls)
    
    @classmethod
    def unregister(cls):
        from .props_append import extra_unregister
        for unreg in extra_unregister:
            unreg(cls)

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
    SPAWNER_OT_ALPHA_SORT,
    SPAWNER_OT_MOVE,
    #SPAWNER_OT_CONTEXT,
]

def register():
    for i in classes:
        bpy.utils.register_class(i)
    bpy.types.WindowManager.optiploy_props = PointerProperty(type=spawner_props)

def unregister():
    for i in reversed(classes):
        bpy.utils.unregister_class(i)
    del bpy.types.WindowManager.optiploy_props
