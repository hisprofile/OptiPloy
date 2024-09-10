from . import base_package

import bpy, os
import pickle

from . import transmitter

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

def load_data(op: bpy.types.Operator, context: bpy.types.Context, item, ind_prefs, *, obj:str=None, col:str=None):
    prefs = context.preferences.addons[base_package].preferences
    props = context.scene.optidrop_props
    activeCol = context.view_layer.active_layer_collection.collection
    
    #col: bpy.types.Collection = bpy.data.collections[col]

    map_to_do = {}

    def recursive(d_block):
        user_map = bpy.data.user_map(subset=[d_block])
        IDs = user_map[d_block]
        map_to_do[d_block] = d_block.make_local()
        
        for ID in IDs:
            if map_to_do.get(ID): continue
            if getattr(ID, 'override_library') != None: continue
            recursive(ID)
        return d_block
    
    def remap():
        for linked, local in list(map_to_do.items()):
            linked.user_remap(local)
        map_to_do.clear()

    def clean_remap(TYPE):
        for ID in filter(lambda a: isinstance(a, TYPE), gatherings['override']):
            map_to_do[ID] = ID.make_local()
        remap()
        for ID in filter(lambda a: isinstance(a, TYPE), gatherings['linked']):
            map_to_do[ID] = ID.make_local()
        remap()

    override_support = (
        bpy.types.Mesh,
        bpy.types.Material,
        bpy.types.SurfaceCurve,
        bpy.types.Light,
        bpy.types.Curve,
        bpy.types.GreasePencil,
        bpy.types.MetaBall,
        bpy.types.TextCurve,
        bpy.types.Volume,
        bpy.types.Armature,
        bpy.types.Camera
    )

    
    oldTXTs = {*bpy.data.texts}

    if not os.path.exists(item.filepath):
        op.report({'ERROR'}, f"{item.filepath} doesn't exist!")
        op.report({'ERROR'}, "The .blend file no longer exists!")
        return {'CANCELLED'}
    
        
    with bpy.data.libraries.load(item.filepath, link=True, relative=True) as (From, To):
        if obj:
            To.objects = [obj]
        if col:
            To.collections = [col]

    gatherings = {
        'override': set(),
        'linked': set()
    }

    if obj:
        obj: bpy.types.Object = To.objects[0]
        obj = obj.override_create(remap_local_usages=True)
        activeCol.objects.link(obj)
        id_ref = get_id_reference_map()
        id_ref = get_all_referenced_ids(obj, id_ref)

        for ID in id_ref:
            if not ID.library: continue
            gatherings['linked'].add(ID)
        
        for ID in id_ref:
            if not ID.override_library: continue
            if ID.override_library.reference in gatherings['linked']:
                gatherings['linked'].remove(ID.override_library.reference)
            gatherings['override'].add(ID)

        if obj.parent != None:
            obj.parent.override_create(remap_local_usages=True)
            activeCol.objects.link(obj.parent)
        
        if ind_prefs.localize_objects:
            obj.make_local()
            if obj.parent: obj.parent.make_local()

    if col:
        col: bpy.types.Collection = To.collections[0]
        #col = col.make_local()
        context.scene.collection.children.link(col)
        new_col = col.override_hierarchy_create(context.scene, context.view_layer, reference=None, do_fully_editable=True)
        context.scene.collection.children.unlink(col)
        col = new_col
        id_ref = get_id_reference_map()
        id_ref = get_all_referenced_ids(col, id_ref)

        for ID in id_ref:
            if not ID.library: continue

            if isinstance(ID, override_support):
                possible_override = ID.override_create(remap_local_usages=True)
                if possible_override != None:
                    ID = possible_override
                    
            gatherings['linked'].add(ID)
        
        for ID in id_ref:
            if not ID.override_library: continue
            if ID.override_library.reference in gatherings['linked']:
                gatherings['linked'].remove(ID.override_library.reference)
            gatherings['override'].add(ID)

        if ind_prefs.localize_collections:
            map_to_do[col] = col.make_local()
            for colChild in col.children_recursive:
                map_to_do[colChild] = colChild.make_local()

            remap()

        if ind_prefs.localize_objects:
            for object in col.objects:
                map_to_do[object] = object.make_local()

            for colChild in col.children_recursive:
                for object in colChild.objects:
                    map_to_do[object] = object.make_local()

            remap()

        if ind_prefs.localize_meshes:
            clean_remap(bpy.types.Mesh)

        if ind_prefs.localize_armatures:
            clean_remap(bpy.types.Armature)

        if ind_prefs.localize_other_data:
            other_types = (
                bpy.types.SurfaceCurve,
                bpy.types.Light,
                bpy.types.Curve,
                bpy.types.GreasePencil,
                bpy.types.MetaBall,
                bpy.types.TextCurve,
                bpy.types.Volume,
            )

            clean_remap(other_types)

        if ind_prefs.localize_materials:
            clean_remap(bpy.types.Material)

        if ind_prefs.localize_node_groups:
            clean_remap(bpy.types.NodeGroup)
            clean_remap(bpy.types.GeometryNodeTree)
            clean_remap(bpy.types.ShaderNodeTree)

        if ind_prefs.localize_images:
            clean_remap(bpy.types.Image)

    if col and prefs.to_cursor:
        for object in col.all_objects:
            if object.parent: continue
            object.location = context.scene.cursor.location

    if prefs.execute_scripts:
        for text in filter(lambda a: isinstance(a, bpy.types.Text), gatherings['linked']):
            text.as_module()


    bpy.data.orphans_purge(False, True, True)
    return {'FINISHED'}

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
            box.prop(prefs, 'localize_collections')
            box.prop(prefs, 'localize_objects')
            box.prop(prefs, 'localize_meshes')
            box.prop(prefs, 'localize_materials')
            box.prop(prefs, 'localize_node_groups')
            box.prop(prefs, 'localize_images')
            box.prop(prefs, 'localize_armatures')
            '''
            layout.label(text='Library Overrides')
            box = layout.box()
            box.prop(prefs, 'library_overrides')
            r = box.row()
            r.enabled = prefs.library_overrides
            r.prop(prefs, 'localize_overridden_collections')
            '''

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
        prefs = context.preferences.addons[base_package].preferences
        props = context.scene.optidrop_props
        blend = self.blend
        folder = self.folder
        obj = self.object
        col = self.collection
        prefs_dict = dict()

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