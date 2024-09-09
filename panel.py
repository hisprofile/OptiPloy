from . import base_package

import bpy, os
import pickle

from . import transmitter
from . import tx_rx

from bpy.types import (UIList, Panel, Operator,
                       Mesh, Object, Material,
                       Armature, NodeGroup, Image,
                       Collection, Text)

from bpy.props import *

from typing import Dict, Set
import bpy
from bpy.types import ID

import time

folder_path = os.path.dirname(__file__)

# no longer exists in 4.2 bpy_extras
def get_id_reference_map() -> Dict[ID, Set[ID]]:
    """Return a dictionary of direct datablock references for every datablock in the blend file."""
    inv_map = {}
    for key, values in bpy.data.user_map().items():
        for value in values:
            if value == key:
                # So an object is not considered to be referencing itself.
                continue
            inv_map.setdefault(value, set()).add(key)
    return inv_map


def recursive_get_referenced_ids(
    ref_map: Dict[ID, Set[ID]], id: ID, referenced_ids: Set, visited: Set
):
    """Recursively populate referenced_ids with IDs referenced by id."""
    if id in visited:
        # Avoid infinite recursion from circular references.
        return
    visited.add(id)
    for ref in ref_map.get(id, []):
        referenced_ids.add(ref)
        recursive_get_referenced_ids(
            ref_map=ref_map, id=ref, referenced_ids=referenced_ids, visited=visited
        )


def get_all_referenced_ids(id: ID, ref_map: Dict[ID, Set[ID]]) -> Set[ID]:
    """Return a set of IDs directly or indirectly referenced by id."""
    referenced_ids = set()
    recursive_get_referenced_ids(
        ref_map=ref_map, id=id, referenced_ids=referenced_ids, visited=set()
    )
    return referenced_ids


class SPAWNER_GENERIC_SPAWN_UL_List(UIList):
    def draw_item(self, context,
            layout, data,
            item, icon,
            active_data, active_propname,
            index):
        prefs = context.preferences.addons[base_package].preferences
        props = context.scene.optidrop_props
        itemType = item.bl_rna.identifier
        Type = 'OBJECT' if itemType == 'objects' else 'COLLECTION'
        Icon = 'OBJECT_DATA' if itemType == 'objects' else 'OUTLINER_COLLECTION'
        row = layout.row()
        row.label(text=item.name, icon=Icon)
        row = row.row()
        row.alignment='RIGHT'
        op = row.operator('spawner.spawner')

        if props.view == 'BLENDS':
            op.blend = props.selected_blend
            op.folder = ''
        if props.view == 'FOLDERS':
            folder = prefs.folders[props.selected_folder]
            op.folder = props.selected_folder
            op.blend = folder.selected_blend
        if Type == 'OBJECT':
            op.object = item.name
            op.collection = ''
        if Type == 'COLLECTION':
            op.collection = item.name
            op.object = ''


class SPAWNER_PT_panel(Panel):
    bl_label = base_package
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category = 'OptiPloy'

    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences
        data = prefs
        props = context.scene.optidrop_props
        layout = self.layout
        box = layout.box()
        
        row = box.row()
        row.label(text='View Mode')
        row.alignment = 'RIGHT'
        row.scale_x = 2
        row.scale_y = 1.6
        row.prop(props, 'view', expand=True, icon_only=True, text='View')

        if props.view == 'BLENDS':
            if not len(prefs.blends):
                layout.row().label(text='Add a .blend file in the preferences to get started!')
                return
            row = layout.row()
            row.label(text='', icon='BLENDER')
            row = row.row()
            row.prop(props, 'selected_blend', text='')
            blend = prefs.blends[props.selected_blend]
        
        if props.view == 'FOLDERS':
            if not len(prefs.folders):
                layout.row().label(text='Add a folder of .blend files in the preferences to get started!')
                return
            row = layout.row()
            row = row.row()
            row.label(text='', icon='FILE_FOLDER')
            row.prop(props, 'selected_folder', text='')
            folder = prefs.folders[props.selected_folder]
            data = folder
            if not len(folder.blends):
                layout.row().label(text='This folder has no .blend files marked! Has it been scanned?')
                return None
            row = layout.row()
            row.label(text='', icon='BLENDER')
            row = row.row()
            row.prop(folder, 'selected_blend', text='')
            blend = folder.blends[data.selected_blend]
        
        if props.view != 'TOOLS':
            box = layout.box()
            if not (len(blend.objects) + len(blend.collections)):
                box.row().label(text="Nothing in this file detected! Mark items as assets!")
                return
            objBox = box.box()
            objBox.row().label(text='Objects', icon='OBJECT_DATA')
            if len(blend.objects):
                objBox.row().template_list('SPAWNER_GENERIC_SPAWN_UL_List', 'Items',
                                        blend, 'objects', prefs, 'null')
            else:
                objBox.row().label(text='No objects added!')
            
            colBox = box.box()
            colBox.row().label(text='Collections', icon='OUTLINER_COLLECTION')
            if len(blend.collections):
                colBox.row().template_list('SPAWNER_GENERIC_SPAWN_UL_List', 'Collections',
                                           blend, 'collections', prefs, 'null')
            else:
                colBox.row().label(text='No collections added!')

        if props.view == 'TOOLS':
            layout.label(text='Post-Processing')
            box = layout.box()
            box.prop(prefs, 'to_cursor')
            box.prop(prefs, 'execute_scripts')
            layout.label(text='Behavior')
            box = layout.box()
            #box.enabled = 1 - prefs.library_overrides
            box.prop(prefs, 'localize_objects')
            box.prop(prefs, 'localize_meshes')
            box.prop(prefs, 'localize_materials')
            box.prop(prefs, 'localize_node_groups')
            box.prop(prefs, 'localize_images')
            box.prop(prefs, 'localize_armatures')
            box.prop(prefs, 'localize_collections')

class SPAWNER_OT_SPAWNER(Operator):
    bl_idname = 'spawner.spawner'
    bl_label = 'Spawn'
    bl_description = 'Spawn it!'
    bl_options = {'UNDO'}

    type: EnumProperty(
        items=(
            ('COLLECTION', 'Collection', 'This spawnable is a collection', 'COLLECTION', 0),
            ('OBJECT', 'Object', 'This spawnable is an object', 'OBJECT', 1)
        ),
        name='Type',
        options=set()
    )

    blend: StringProperty(default='')
    folder: StringProperty(default='')
    object: StringProperty(default='')
    collection: StringProperty(default='')

    def execute(self, context):
        if transmitter.client == None:
            print("OptiPloy's second instance of Blender does not exist. Launching...")
            tx_rx.register()
            timeout = time.time()
            while transmitter.last_msg != 'CLIENT_CONNECTED':
                time.sleep(1)
                if (time.time() - timeout) > 10:
                    print("Could not create new instance of OptiPloy!")
                    self.report({'ERROR'}, "Could not create new instance of OptiPloy!")
                    return {'CANCELLED'}
        root_prefs = context.preferences.addons[base_package].preferences
        prefs = context.preferences.addons[base_package].preferences
        props = context.scene.optidrop_props
        blend = self.blend
        folder = self.folder
        obj = self.object
        col = self.collection
        prefs_dict = dict()
        attempts = 0
        blend_path = os.path.join(folder_path, 'temp.blend')

        options = [
            'localize_objects',
            'localize_meshes',
            'localize_materials',
            'localize_node_groups',
            'localize_images',
            'localize_armatures',
            'localize_collections'
        ]

        if folder and blend:
            folder = prefs.folders[folder]
            if folder.override_behavior:
                prefs = folder
            entry = folder.blends[blend]
            if entry.override_behavior:
                prefs = entry

        if blend and not folder:
            entry = prefs.blends[blend]
            if entry.override_behavior:
                prefs = entry

        for option in options:
            prefs_dict[option] = getattr(prefs, option)

        prefs_dict['localize_collections'] = True
        prefs_dict['localize_objects'] = True

        if not os.path.exists(entry.filepath):
            self.report({'ERROR'}, 'Filepath for this .blend file no longer exists!')
            return {'CANCELLED'}

        prefs_dict['filepath'] = entry.filepath
        
        if obj:
            prefs_dict['obj'] = obj
        
        if col:
            prefs_dict['col'] = col

        dict_as_bytes = pickle.dumps(prefs_dict)
        transmitter.write('INCOMING_JOB')
        transmitter.write(dict_as_bytes)

        while transmitter.last_msg != 'JOB_FINISHED': # Do nothing until received JOB_FINISHED
            time.sleep(0.01)
            if transmitter.last_msg == 'CLIENT_CLOSE':
                attempts += 1
                if attempts == 3:
                    self.report({'ERROR'}, 'Client crashed three times while trying to complete job. Check console for errors!')
                    return {'CANCELLED'}
                self.report({'WARNING'}, 'Client crashed while performing job. Retrying...')
                while transmitter.last_msg != 'CLIENT_CONNECTED':
                    time.sleep(0.1)
                transmitter.write('INCOMING_JOB')
                transmitter.write(dict_as_bytes)
            continue

        if transmitter.last_msg == 'JOB_FINISHED':
            pass
        elif transmitter.last_msg == 'BAD_FILE':
            self.report({'ERROR'}, 'The file you attempted to load from is corrupt!')
            return {'CANCELLED'}
        else:
            self.report({'ERROR'}, 'Received an inappropriate response from the client! Result of job is undetermined!')
            if os.path.exists(blend_path):
                os.remove(blend_path)
            return {'CANCELLED'}

        transmitter.write('NOTED')

        with bpy.data.libraries.load(blend_path, relative=True) as (From, To):
            if obj:
                To.objects = [obj]
            if col:
                To.collections = [col]

        if obj:
            obj: bpy.types.Objects = To.objects[0]
            activeCol = context.view_layer.active_layer_collection.collection
            activeCol.objects.link(obj)

            if obj.parent:
                activeCol.objects.link(obj.parent)
                obj = obj.parent

            if root_prefs.to_cursor:
                obj.location = context.scene.cursor.location

            context.scene['new_spawn'] = col

        if col:
            col: bpy.types.Collection = To.collections[0]
            context.scene.collection.children.link(col)

            

            #for obj in col.objects:
            #    if obj.override_library:
            #        obj.override_library.resync(context.scene, view_layer=context.view_layer)
            #for colChild in col.children_recursive:
            #    for obj in colChild.all_objects:
            #        if obj.override_library:
            #            obj.override_library.resync(context.scene, view_layer=context.view_layer)
            #

            if prefs.to_cursor:
                for obj in col.all_objects:
                    if obj.parent: continue
                    obj.location = context.scene.cursor.location

            #if col.override_library:
            #    col.override_library.resync(context.scene, view_layer=None, residual_storage=None, do_hierarchy_enforce=True, do_whole_hierarchy=True)
            context.scene['new_spawn'] = col

        refmap = get_id_reference_map()
        refmap = get_all_referenced_ids(context.scene['new_spawn'], refmap)

        if prefs.execute_scripts:
            for ID in refmap:
                if not isinstance(ID, Text): continue
                ID.as_module()

        os.remove(blend_path)

        del context.scene['new_spawn']

        return {'FINISHED'}

        if obj:
            return load_data(self, context, entry, prefs, obj=obj)
        
        if col:
            return load_data(self, context, entry, prefs, col=col)

class SPAWNER_OBJECT_UL_List(UIList):
    def draw_item(self, context,
            layout, data,
            item, icon,
            active_data, active_propname,
            index):
        layout.label(text=item.name)

def textBox(self, sentence, icon='NONE', line=56):
    layout = self.box().column()
    sentence = sentence.split(' ')
    mix = sentence[0]
    sentence.pop(0)
    broken = False
    while True:
        add = ' ' + sentence[0]
        if len(mix + add) < line:
            mix += add
            sentence.pop(0)
            if sentence == []:
                layout.row().label(text=mix, icon='NONE' if broken else icon)
                return None

        else:
            layout.row().label(text=mix, icon='NONE' if broken else icon)
            broken = True
            mix = sentence[0]
            sentence.pop(0)
            if sentence == []:
                layout.row().label(text=mix)
                return None


class SPAWNER_OT_genericText(bpy.types.Operator):
    bl_idname = 'spawner.textbox'
    bl_label = 'Hints'
    bl_description = 'A window will display any possible questions you have'

    text: StringProperty(default='')
    icons: StringProperty()
    size: StringProperty()
    width: IntProperty(default=400)
    url: StringProperty(default='')

    def invoke(self, context, event):
        if event.shift and self.url != '':
            bpy.ops.wm.url_open(url=self.url)
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self, width=self.width)
    
    def draw(self, context):
        sentences = self.text.split('\n')
        icons = self.icons.split(',')
        sizes = self.size.split(',')
        for sentence, icon, size in zip(sentences, icons, sizes):
            textBox(self.layout, sentence, icon, int(size))

    def execute(self, context):
        return {'FINISHED'}


classes = [
    SPAWNER_PT_panel,
    SPAWNER_GENERIC_SPAWN_UL_List,
    SPAWNER_OT_SPAWNER,
    SPAWNER_OT_genericText
]

def register():
    for i in classes:
        bpy.utils.register_class(i)

def unregister():
    for i in reversed(classes):
        bpy.utils.unregister_class(i)