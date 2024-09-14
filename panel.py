from . import base_package

import bpy, os

from bpy.types import (UIList, Panel, Operator)

from bpy.props import *


import bpy


from collections import defaultdict

folder_path = os.path.dirname(__file__)

rev_leveled_map = dict()

refd_by = defaultdict(set)

extra_types = [
    'localize_lights',        
    'localize_cameras',       
    'localize_curves',        
    'localize_text_curves',   
    'localize_metaballs',     
    'localize_surface_curves',
    'localize_volumes',       
    'localize_grease_pencil', 
]

# Need local versions of bpy_extras.id_map_utils to modify how I see fit.
# Changes include:

# Finding at what level IDs are referenced

# Preventing IDs from being processed if they reference an ID who has referenced the current ID



def load_data(op: bpy.types.Operator, context: bpy.types.Context, item, ind_prefs, *, obj:str=None, col:str=None):
    from typing import Dict, Set
    from bpy.types import ID

    prefs = context.preferences.addons[base_package].preferences
    props = context.scene.optiploy_props
    activeCol = context.view_layer.active_layer_collection.collection
    
    #col: bpy.types.Collection = bpy.data.collections[col]
    bone_shapes = set()
    arms = set()
    map_to_do = {}
    gatherings = {
        'override': list(),
        'linked': list()
    }

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
        ref_map: Dict[ID, Set[ID]], id: ID, referenced_ids: Set, visited: Set, level
    ):
        """Recursively populate referenced_ids with IDs referenced by id."""
        if id in visited:
            # Avoid infinite recursion from circular references.
            return
        visited.add(id)

        if isinstance(id, bpy.types.Object) and isinstance(getattr(id, 'data', None), bpy.types.Armature):
            arms.add(id)
            bone_shapes.update(set(bone.custom_shape for bone in id.pose.bones))

        for ref in ref_map.get(id, []):
            if (ref in bone_shapes) and (id in arms):
                continue
            if id in refd_by[ref]: continue
            refd_by[id].add(ref)
            rev_leveled_map[ref] = max(rev_leveled_map.get(ref, -1), level)
            referenced_ids.add(ref)
            recursive_get_referenced_ids(
                ref_map=ref_map, id=ref, referenced_ids=referenced_ids, visited=visited, level=level+1
            )


    def get_all_referenced_ids(id: ID, ref_map: Dict[ID, Set[ID]]) -> Set[ID]:
        """Return a set of IDs directly or indirectly referenced by id."""
        referenced_ids = set()
        rev_leveled_map[id] = 0
        recursive_get_referenced_ids(
            ref_map=ref_map, id=id, referenced_ids=referenced_ids, visited=set(), level=0
        )
        return referenced_ids

    # Collections and objects are overridden by default through override_hierarchy_create
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
        bpy.types.Camera,
        #bpy.types.ShaderNodeTree,
        #bpy.types.GeometryNodeTree,
        #bpy.types.Image,

        # do NOT add images to this lol
        # i think it actually just makes a copy of the image. bad for optimization

    )

    if not os.path.exists(item.filepath):
        op.report({'ERROR'}, f"{item.filepath} doesn't exist!")
        op.report({'ERROR'}, "The .blend file no longer exists!")
        return {'CANCELLED'}
    
    try:
        with bpy.data.libraries.load(item.filepath, link=True, relative=True) as (From, To):
            if obj:
                To.objects = [obj]
            if col:
                To.collections = [col]
    except:
        op.report({'ERROR'}, f'The .blend you are trying to open is corrupt!')

    if obj:
        if To.objects[0] == None:
            op.report({'ERROR'}, f'Object "{obj}" could not be found in {os.path.basename(item.filepath)}')
            return {'CANCELLED'}
        obj: bpy.types.Object = To.objects[0]
        activeCol.objects.link(obj)
        new_obj = obj.override_hierarchy_create(context.scene, context.view_layer, reference=None, do_fully_editable=True)
        activeCol.objects.unlink(obj)
        obj = new_obj
        if not obj in set(activeCol.objects):
            activeCol.objects.link(obj)
        spawned = obj

    if col:
        if To.collections[0] == None:
            op.report({'ERROR'}, f'Collection "{col}" could not be found in {os.path.basename(item.filepath)}')
            return {'CANCELLED'}
        col: bpy.types.Collection = To.collections[0]
        #arms = set(filter(lambda a: a.type == 'ARMATURE', col.all_objects))
        context.scene.collection.children.link(col)
        new_col = col.override_hierarchy_create(context.scene, context.view_layer, reference=None, do_fully_editable=True)
        context.scene.collection.children.unlink(col)
        col = new_col
        #arms.update(set(filter(lambda a: a.type == 'ARMATURE', col.all_objects)))
        #bone_shapes = set(bone.custom_shape for arm in arms for bone in arm.pose.bones)
        spawned = col
        
    id_ref = get_id_reference_map()
    id_ref = get_all_referenced_ids(spawned, id_ref)

    sorted_refs = list(map(lambda a: a[0],
        sorted(list(
            rev_leveled_map.items()
        ), key=lambda a: a[1])
    ))

    rev_leveled_map.clear()
    refd_by.clear()

    for ID in sorted_refs:
        if not ID.library: continue

        if isinstance(ID, override_support):
            possible_override = ID.override_create(remap_local_usages=True)
            if possible_override != None:
                drivers = getattr(
                            getattr(
                                getattr(possible_override, 'shape_keys', None),
                            'animation_data', None),
                        'drivers', None)
                if drivers:
                    [setattr(target, 'id', possible_override) if target.id == ID else None for driver in drivers for variable in driver.driver.variables for target in variable.targets]
                    # This is really specific, but with good cause.
                    # Say you have a mesh ID with a shape key ID, and the shape key has values that are being driven by the mesh ID.
                    # On some occasions, when creating an overridden mesh with a shape key ID (which will therefore creating an overridden copy of the shape key), the values on the shape key ID will continue to be driven by the linked mesh. This "function comprehension" corrects that.

                    # Don't know how many other situations where something like this can happen, but I don't imagine it being difficult to fix.

                    # This has led me to come across a serious design flaw in Blender, but one I'm not sure can be fixed. You can replace IDs with other IDs, even if users are using those IDs on a read-only attribute. It will lead to data corruption.

                ID = possible_override

        gatherings['linked'].append(ID)
    
    for ID in sorted_refs:
        if not ID.override_library: continue
        if ID.override_library.reference in gatherings['linked']:
            gatherings['linked'].remove(ID.override_library.reference)
        gatherings['override'].append(ID)

    '''
    
    What's the reason for all this weird code?

    This is the result of my desire for "data isolation." When OptiPloy used my first method of linking, spawning previously spawned collections with different settings would localize
    the data in the previously spawned collections. That really annoyed me. Using bpy.data.temp_data() didn't help, because linking within it would break Blender, and my only real
    solution was to have a second instance of Blender running to prepare the data for the main instance to use, which actually worked. But I didn't like it, because despite using
    factory settings, its RAM usage would increase with every spawned item. Too bad considering how well it worked. But I *really* wanted it to all be local.

    My solution? Library overrides!

    Library overridden IDs float between a state of localized and linked. Technically with every "LO" ID, you *are* increasing storage usage, but not as much as you would be since it
    still very much relies on the linked stuff. It *is* a good solution for this "data isolation" concept, because it prevents the localization of pre-existing data, but its far from
    the best one. I have to implement checks for specific things. I don't doubt that makes people unhappy, but its not like this code is being ran 24/7. Right now, the only checks
    being performed are for drivers between meshes and their shape keys (literally) and preventing bone shapes from being processed if they are only used by any armature. It's
    possible I'll run into more situations that I need to counter, but it cannot be that hard to fix.

    Famous last words?

    '''
        
    if ind_prefs.localize_collections:
        clean_remap(bpy.types.Collection)
    if ind_prefs.localize_objects:
        clean_remap(bpy.types.Object)
    if ind_prefs.localize_meshes:
        clean_remap(bpy.types.Mesh)
    if ind_prefs.localize_armatures:
        clean_remap(bpy.types.Armature)
    if ind_prefs.localize_materials:
        clean_remap(bpy.types.Material)
    if ind_prefs.localize_node_groups:
        clean_remap(bpy.types.NodeGroup)
        clean_remap(bpy.types.GeometryNodeTree)
        clean_remap(bpy.types.ShaderNodeTree)
    if ind_prefs.localize_images:
        clean_remap(bpy.types.Image)
    
    if ind_prefs.localize_surface_curves:
        clean_remap(bpy.types.SurfaceCurve)
    if ind_prefs.localize_lights:
        clean_remap(bpy.types.Light)
    if ind_prefs.localize_cameras:
        clean_remap(bpy.types.Camera)
    if ind_prefs.localize_curves:
        clean_remap(bpy.types.Curve)
    if ind_prefs.localize_text_curves:
        clean_remap(bpy.types.TextCurve)
    if ind_prefs.localize_metaballs:
        clean_remap(bpy.types.MetaBall)
    if ind_prefs.localize_volumes:
        clean_remap(bpy.types.Volume)
    if ind_prefs.localize_grease_pencil:
        clean_remap(bpy.types.GreasePencil)

    if col and prefs.to_cursor:
        for object in spawned.all_objects:
            if object.parent: continue
            object.location = context.scene.cursor.location

    context.scene['new_spawn'] = spawned # assign the newly spawned item to a globally accessible variable, giving developers the opportunity to further modify data in the scripts execution stage

    if prefs.execute_scripts:
        for text in filter(lambda a: isinstance(a, bpy.types.Text), gatherings['linked']):
            text.as_module()
    
    del context.scene['new_spawn']

    map_to_do.clear()
    gatherings['linked'].clear()
    gatherings['override'].clear()
    arms.clear()
    bone_shapes.clear()
    del sorted_refs, map_to_do, gatherings

    bpy.data.orphans_purge(True, True, True)
    return {'FINISHED'}

class SPAWNER_GENERIC_SPAWN_UL_List(UIList):
    def draw_item(self, context,
            layout, data,
            item, icon,
            active_data, active_propname,
            index):
        prefs = context.preferences.addons[base_package].preferences
        props = context.scene.optiploy_props
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

class SPAWNER_PT_folder_settings(Panel):
    bl_label = 'Settings'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences
        props = context.scene.optiploy_props
        layout = self.layout
        layout.label(text='Folder Settings')
        options = [
            'localize_collections',
            'localize_objects',
            'localize_meshes',
            'localize_materials',
            'localize_node_groups',
            'localize_images',
            'localize_armatures',
        ]

        folder = prefs.folders[props.selected_folder]
        layout.prop(folder, 'override_behavior')
        box = layout.box()
        box.enabled = folder.override_behavior
        for i in options:
            box.prop(folder, i)
        box.label(text='Extra Types')
        for i in extra_types:
            box.prop(folder, i)

class SPAWNER_PT_blend_settings(Panel):
    bl_label = 'Settings'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences
        props = context.scene.optiploy_props
        layout = self.layout
        folder = None
        if props.view == 'BLENDS':
            blend = prefs.blends[props.selected_blend]
        else:
            folder = prefs.folders[props.selected_folder]
            blend = folder.blends[folder.selected_blend]
        layout.label(text='Blend Settings')
        options = [
            'localize_collections',
            'localize_objects',
            'localize_meshes',
            'localize_materials',
            'localize_node_groups',
            'localize_images',
            'localize_armatures',
        ]
        row = layout.row()
        row.prop(blend, 'override_behavior')
        #row.enabled = getattr(folder, 'override_behavior', True)
        box = layout.box()
        box.enabled = blend.override_behavior
        for i in options:
            box.prop(blend, i)
        box.label(text='Extra Types')
        for i in extra_types:
            box.prop(blend, i)

class SPAWNER_PT_extra_settings(Panel):
    bl_label = 'Extra Localization Options'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    
    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences
        props = context.scene.optiploy_props
        layout = self.layout
        layout.label(text=self.bl_label)
        box = layout.box()
        for i in extra_types:
            box.prop(prefs, i)

class SPAWNER_PT_panel(Panel):
    bl_label = 'OptiPloy'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category = 'OptiPloy'

    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences
        data = prefs
        props = context.scene.optiploy_props
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
            row.popover('SPAWNER_PT_blend_settings', text='', icon='SETTINGS')
            blend = prefs.blends[props.selected_blend]
        
        if props.view == 'FOLDERS':
            if not len(prefs.folders):
                layout.row().label(text='Add a folder of .blend files in the preferences to get started!')
                return
            row = layout.row()
            row = row.row()
            row.label(text='', icon='FILE_FOLDER')
            row.prop(props, 'selected_folder', text='')
            row.popover('SPAWNER_PT_folder_settings', text='', icon='SETTINGS')
            folder = prefs.folders[props.selected_folder]
            data = folder
            if not len(folder.blends):
                layout.row().label(text='This folder has no .blend files marked! Has it been scanned?')
                return None
            row = layout.row()
            row.label(text='', icon='BLENDER')
            row = row.row()
            row.prop(folder, 'selected_blend', text='')
            row.popover('SPAWNER_PT_blend_settings', text='', icon='SETTINGS')
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
            box.popover('SPAWNER_PT_extra_settings')
            layout.operator('preferences.addon_show', text='Open Preferences').module = base_package
            if not context.preferences.use_preferences_save:
                layout.operator('wm.save_userpref')

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
        blend = self.blend
        folder = self.folder
        obj = self.object
        col = self.collection

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
    SPAWNER_OT_genericText,
    SPAWNER_PT_folder_settings,
    SPAWNER_PT_blend_settings,
    SPAWNER_PT_extra_settings,
]

def register():
    for i in classes:
        bpy.utils.register_class(i)

def unregister():
    for i in reversed(classes):
        bpy.utils.unregister_class(i)