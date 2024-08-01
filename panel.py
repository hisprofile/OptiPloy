from .__init__ import IDNAME

import bpy

from bpy.types import UIList, Panel, Operator
from bpy.props import *

def load_data(context, item, *, obj=None, col=None):
    #print(item, obj, col)
    prefs = context.preferences.addons[IDNAME].preferences
    props = context.scene.optidrop_props
    activeCol = context.view_layer.active_layer_collection.collection

    map_to_do = {}

    def recursive(d_block):
        user_map = bpy.data.user_map(subset=[d_block])
        IDs = user_map[d_block]
        map_to_do[d_block] = d_block.make_local()
        
        for ID in IDs:
            if map_to_do.get(ID): continue
            recursive(ID)
        return d_block

    oldOBJs = {*bpy.data.objects}
    oldMesh = {*bpy.data.meshes}
    oldMats = {*bpy.data.materials}
    oldNGs = {*bpy.data.node_groups}
    oldIMGs = {*bpy.data.images}
    oldARMs = {*bpy.data.armatures}
    
    with bpy.data.libraries.load(item.filepath, link=True) as (From, To):
        if obj:
            To.objects = [obj]
        if col:
            To.collections = [col]
    
    #return
    
    newOBJs = {*bpy.data.objects} - oldOBJs
    newMesh = {*bpy.data.meshes} - oldMesh
    newMats = {*bpy.data.materials} - oldMats
    newNGs = {*bpy.data.node_groups} - oldNGs
    newIMGs = {*bpy.data.images} - oldIMGs
    newARMs = {*bpy.data.armatures} - oldARMs
    del oldOBJs
    del oldMesh
    del oldMats
    del oldNGs
    del oldIMGs
    del oldARMs

    if obj:
        obj = To.objects[0]
        obj = recursive(obj)

    if col:
        col = To.collections[0]
        col = col.make_local()

        for colChild in col.children_recursive:
            recursive(colChild)

        context.scene.collection.children.link(col)
                
        for object in col.objects:
            recursive(object)
    
    #for ID in newOBJs:
    #    if map_to_do.get(ID) != None: continue
    #    recursive(ID)

    if prefs.localize_meshes:
        for ID in newMesh:
            recursive(ID)
    if prefs.localize_materials:
        for ID in newMats:
            recursive(ID)
    if prefs.localize_node_groups:
        for ID in newNGs:
            recursive(ID)
    if prefs.localize_images:
        for ID in newIMGs:
            recursive(ID)
    if prefs.localize_armatures:
        for ID in newARMs:
            recursive(ID)
    for linked, local in list(map_to_do.items()):
        linked.user_remap(local)

    if obj:
        object = obj
        while object.parent != None:
            object = object.parent
            activeCol.objects.link(object)
        activeCol.objects.link(obj)
        object.location = context.scene.cursor.location

    if col:
        for object in col.all_objects:
            if object.parent: continue
            object.location = context.scene.cursor.location
    bpy.data.orphans_purge()

class SPAWNER_GENERIC_SPAWN_UL_List(UIList):
    def draw_item(self, context,
            layout, data,
            item, icon,
            active_data, active_propname,
            index):
        prefs = context.preferences.addons[IDNAME].preferences
        props = context.scene.optidrop_props
        itemType = item.bl_rna.identifier
        Type = 'OBJECT' if itemType == 'objects' else 'COLLECTION'
        Icon = 'OBJECT_DATA' if itemType == 'objects' else 'OUTLINER_COLLECTION'
        layout.label(text=item.name, icon=Icon)
        op = layout.operator('spawner.spawner')

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
    bl_label = IDNAME
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category = 'Spawner'

    def draw(self, context):
        prefs = context.preferences.addons[IDNAME].preferences
        data = prefs
        props = context.scene.optidrop_props
        layout = self.layout
        box = layout.box()
        
        row = box.row()
        row.label(text='View Mode')
        row.alignment = 'RIGHT'
        row.scale_x = 2
        #row.ui_units_x = 2
        row.scale_y = 1.6
        row.prop(props, 'view', expand=True, icon_only=True, text='View')

        #blend = props.selected_blend
        #folder = props.selected_folder

        if props.view == 'BLENDS':
            if not len(prefs.blends):
                layout.row().label(text='Add a .blend file in the preferences to get started!')
                return
            layout.row().prop(props, 'selected_blend')
            blend = prefs.blends[props.selected_blend]
        
        if props.view == 'FOLDERS':
            if not len(prefs.folders):
                layout.row().label(text='Add a folder of .blend files in the preferences to get started!')
                return
            layout.row().prop(props, 'selected_folder')
            folder = prefs.folders[props.selected_folder]
            data = folder
            if not len(folder.blends):
                layout.row().label(text='This folder has no .blend files marked! Has it been scanned?')
                return None
            layout.row().prop(folder, 'selected_blend')
            blend = folder.blends[data.selected_blend]
        
        if props.view != 'TOOLS':
            #layout.row().label(text='.blend files')
            box = layout.box()
            #if not len(prefs.blends):
            #    box.row().label(text='Add a .blend file in the preferences to get started!')
            #    return
            #box.row().prop(props, 'selected_blend')
            #blend = prefs.blends.get(props.selected_blend)
            if not (len(blend.objects) + len(blend.collections)):
                box.row().label(text="Nothing in this file detected! Mark items as assets!")
                return
            objBox = box.box()
            objBox.row().label(text='Objects', icon='OBJECT_DATA')
            if len(blend.objects):
                #objBox = box.box()
                #objBox.row().label(text='Object', icon='OBJECT_DATA')
                objBox.row().template_list('SPAWNER_GENERIC_SPAWN_UL_List', 'Items',
                                        blend, 'objects', prefs, 'null')
            else:
                objBox.row().label(text='No objects added!')
            
            colBox = box.box()
            colBox.row().label(text='Collections', icon='OUTLINER_COLLECTION')
            if len(blend.collections):
                #colBox.row().label(text='Collections', icon='OUTLINER_COLLECTION')
                colBox.row().template_list('SPAWNER_GENERIC_SPAWN_UL_List', 'Collections',
                                           blend, 'collections', prefs, 'null')
            else:
                colBox.row().label(text='No collections added!')

        if props.view == 'TOOLS':
            box = layout.box()
            box.prop(prefs, 'to_cursor')
            box.prop(prefs, 'localize_meshes')
            box.prop(prefs, 'localize_materials')
            box.prop(prefs, 'localize_node_groups')
            box.prop(prefs, 'localize_images')
            box.prop(prefs, 'localize_armatures')
        
        #if props.view == 'FOLDERS':
        #    layout.row().label(text='Folders')
        #    box = layout.box()
        #    box.row().prop(props, 'selected_folder')
        #    if (folder := prefs.folders.get(props.selected_folder)):
        #        box.row().prop(folder, 'selected_blend')

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
        prefs = context.preferences.addons[IDNAME].preferences
        props = context.scene.optidrop_props
        blend = self.blend
        folder = self.folder
        obj = self.object
        col = self.collection

        if folder and blend:
            entry = prefs.folders[folder].blends[blend]

        if blend and not folder:
            entry = prefs.blends[blend]

        if obj:
            load_data(context, entry, obj=obj)
        
        if col:
            load_data(context, entry, col=col)

        return {'FINISHED'}

        #if blend and folder:



class SPAWNER_OBJECT_UL_List(UIList):
    def draw_item(self, context,
            layout, data,
            item, icon,
            active_data, active_propname,
            index):
        layout.label(text=item.name)

classes = [
    SPAWNER_PT_panel,
    SPAWNER_GENERIC_SPAWN_UL_List,
    SPAWNER_OT_SPAWNER
]

def register():
    for i in classes:
        bpy.utils.register_class(i)

def unregister():
    for i in reversed(classes):
        bpy.utils.unregister_class(i)