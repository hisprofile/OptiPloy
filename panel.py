from . import base_package

import bpy

from bpy.types import UIList, Panel, Operator
from bpy.props import *

def load_data(context: bpy.types.Context, item, *, obj:bpy.types.Object=None, col:bpy.types.Collection=None):
    prefs = context.preferences.addons[base_package].preferences
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
    oldTXTs = {*bpy.data.texts}
    
    with bpy.data.libraries.load(item.filepath, link=True, relative=True) as (From, To):
        if obj:
            To.objects = [obj]
        if col:
            To.collections = [col]
    
    
    newOBJs = {*bpy.data.objects} - oldOBJs
    newMesh = {*bpy.data.meshes} - oldMesh
    newMats = {*bpy.data.materials} - oldMats
    newNGs = {*bpy.data.node_groups} - oldNGs
    newIMGs = {*bpy.data.images} - oldIMGs
    newARMs = {*bpy.data.armatures} - oldARMs
    newTXTs = {*bpy.data.texts} - oldTXTs
    if prefs.execute_scripts:
        for txt in newTXTs:
            exec(txt.as_string())
    del oldOBJs
    del oldMesh
    del oldMats
    del oldNGs
    del oldIMGs
    del oldARMs

    if obj:
        obj = To.objects[0]
        if not prefs.library_overrides:
            obj = recursive(obj)
        else:
            obj.override_create()


    if col:
        col = To.collections[0]
        
        context.scene.collection.children.link(col)
        if not prefs.library_overrides:
            col = col.make_local()
            for colChild in col.children_recursive:
                recursive(colChild)

                for object in colChild.objects:
                    recursive(object)

            for object in col.objects:
                recursive(object)
        
        else:
            new_col = col.override_hierarchy_create(context.scene, context.view_layer, reference=None, do_fully_editable=True)
            if prefs.localize_overriden_collections:
                new_col = new_col.make_local()
            context.scene.collection.children.unlink(col)
            col = new_col
            gather_meshes = set()
            for object in col.all_objects:
                gather_meshes.add(object.data)
            for mesh in gather_meshes:
                o_mesh = mesh.override_create(remap_local_usages=True)
                if not isinstance(mesh, bpy.types.Mesh): continue

                skey_data = o_mesh.shape_keys
                if skey_data == None: continue
                if skey_data.animation_data == None: continue
                for driver in skey_data.animation_data.drivers:
                    driver = driver.driver
                    targets = [target for variable in driver.variables for target in variable.targets]
                    for target in targets:
                        if target.id == mesh: target.id = o_mesh

            '''
            
            This logic is strange, but was written for a specific set of rigs, where a mesh data-block's shape keys are
            driven by the custom properties of the mesh data-block. When an overriden copy is made of the mesh, any
            target of the drivers will not have its ID replaced with the new copy. In this case, the code goes through
            all the drivers of the shape key data, check if any target is targeting the original mesh, and if it does,
            change the target to the copy.

            You cannot create an overriden copy of the mesh data-block, and then remap all users of the mesh with the
            override copy, because it will lead the copy to reference itself (mesh.override_library.reference - READ ONLY!)
            despite having the reference attribute be read only. An unfortunate flaw. Either remove the read only attribute,
            or change the way how bpy.types.ID.user_remap works.

            It does not affect other rigs, unless they follow the control scheme prepared for said set of rigs. In which
            case it repairs them.
            
            '''

    if not prefs.library_overrides:
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
        if prefs.to_cursor:
            object.location = context.scene.cursor.location

    if col and prefs.to_cursor:
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
            box.enabled = 1 - prefs.library_overrides
            box.prop(prefs, 'localize_meshes')
            box.prop(prefs, 'localize_materials')
            box.prop(prefs, 'localize_node_groups')
            box.prop(prefs, 'localize_images')
            box.prop(prefs, 'localize_armatures')
            layout.label(text='Library Overrides')
            box = layout.box()
            box.prop(prefs, 'library_overrides')
            r = box.row()
            r.enabled = prefs.library_overrides
            r.prop(prefs, 'localize_overridden_collections')
        

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

        if folder and blend:
            entry = prefs.folders[folder].blends[blend]

        if blend and not folder:
            entry = prefs.blends[blend]

        if obj:
            load_data(context, entry, obj=obj)
        
        if col:
            load_data(context, entry, col=col)

        return {'FINISHED'}


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