from . import base_package

import bpy, os

from bpy.types import (UIList, Panel, Operator, Menu)
from bpy.props import *
from collections import defaultdict

from pathlib import Path

folder_path = os.path.dirname(__file__)

options = [
    'localize_collections',
    'localize_objects',
    'localize_meshes',
    'localize_materials',
    'localize_node_groups',
    'localize_images',
    'localize_armatures',
]

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

def only(item, *argv):
    for arg in argv:
        if arg != item:
            return False
    return True

def load_data(op: bpy.types.Operator, context: bpy.types.Context, scene_viewlayer, *, post_process=False, ind_prefs=None, obj:bpy.types.Object=None, col:bpy.types.Collection=None, ):
    from typing import Dict, Set
    from bpy.types import ID

    prefs = context.preferences.addons[base_package].preferences
    props = context.scene.optiploy_props
    activeCol = context.view_layer.active_layer_collection.collection
    scene, view_layer = scene_viewlayer
    #view_layer = context.view_layer
    
    #col: bpy.types.Collection = bpy.data.collections[col]
    bone_shapes = set()
    arms = set()
    map_to_do = {}
    gatherings = {
        'override': list(),
        'linked': list()
    }
    rev_leveled_map = dict()
    refd_by = defaultdict(set)

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
            if id in refd_by[ref]:
                # if the current ID was already referenced by its reference, then don't process it.
                continue
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
    
    # Need local versions of bpy_extras.id_map_utils to modify how I see fit.
    # Changes include:

    # Finding at what level IDs are referenced

    # Preventing IDs from being processed if they reference an ID who has referenced the current ID

    # Collections and objects are overridden by default through override_hierarchy_create
    override_support = (
        bpy.types.Mesh,
        bpy.types.Material,
        bpy.types.SurfaceCurve,
        bpy.types.Light,
        bpy.types.Curve,
        bpy.types.GreasePencil,
        getattr(bpy.types, 'GreasePencilv3', bpy.types.GreasePencil),
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

    additional = list()
    prime_override = dict()

    def override_order(reference):
        rev_l = list(reversed(sorted(list(
                rev_leveled_map.items()
            ) + additional, key=lambda a: a[1])))
        
        #print(rev_l)
        #print(additional)

        for ID, _ in rev_l:
            ID: bpy.types.ID
            context.scene['test_prop'] = ID
            possible_override = ID.override_create(remap_local_usages=True)
            del context.scene['test_prop']
            if possible_override != None:
                drivers = getattr(getattr(getattr(possible_override, 'shape_keys', None),'animation_data', None),'drivers', None)
                if drivers:
                    [setattr(target, 'id', possible_override) if target.id == ID else None for driver in drivers for variable in driver.driver.variables for target in variable.targets]
                if (prime := prime_override.get(ID)) != None:
                    possible_override.user_remap(prime)
                    if isinstance(possible_override, bpy.types.Mesh) and (getattr(possible_override, 'shape_keys', None) != None):
                        bpy.data.batch_remove({possible_override.shape_keys})
                    bpy.data.batch_remove({possible_override})
                else:
                    prime_override[ID] = possible_override
                    possible_override.use_fake_user = True

            if ID == reference:
                old, spawned = ID, possible_override
        return spawned

    def recurse2(ID, level=0, line:list=[]):
        if rev_leveled_map.get(ID, -1) >= level: return
        if type(ID) != bpy.types.Key:
            rev_leveled_map[ID] = level
        line = list(line)
        line.append(ID)
        '''

        This function was the missing piece of a puzzle. OptiPloy is complete now. No more errors when spawning.
        I'd been searching for this functionality for EVER. Finally found it, without AI and without searching.
        I feel like I have to flaunt it, idk
        I know how simple it is, but what it does is so crucial

        UPDATE:
        I was so wrong when I wrote that and I shattered into pieces when I realized it didn't work.
        Now it does!
        The old version that message is referring to did not account for loops in the user hierarchy. This one does.
        If ID2 is referencing/using ID1 but has already been in the "line", we need to stop here.
        So instead of infinitely looping, lets mention ID1 again in the overriding process specifically for ID2.
        So after the duplicate ID1 has been overridden, we can replace it with the original ID1 that was overridden.

        We can't replace the linked IDs with the overridden IDs or else the overridden IDs will reference themselves.
        THAT causes a data corruption error. But that's not happening in this case.

        Now there are zero errors :)

        UPDATE 2 may 24 2025:
        sisyphean struggle

        UPDATE 3 may 25 2025:
        i talked with zayjax today about their rigs, and how one of their very complicated rigs broke the importer.
        i also told them how i worked around it and fixed the importer. i had him try the importer on his many rigs,
        and it worked. EVERY. SINGLE. TIME. could this be it??

        '''
        
        refs = bpy.data.user_map().get(ID, [])
        # refs is the list of IDs that are using the given ID
        for ref in refs:
            if ref == ID: continue
            if type(ref) == bpy.types.Key:
                if getattr(ID, 'shape_keys', None) == ID: continue
            if getattr(ref, 'library', None) == None: continue
            if ID in refd_by[ref]:
                continue
            refd_by[ID].add(ref)
            if ref in line:
                additional.append((ID, line.index(ref)-1))
                continue

            recurse2(ref, level + 1, line)

    if obj:
        if not obj in list(view_layer.objects):
            activeCol.objects.link(obj)
        if ind_prefs.importer == 'STABLE':
            new_obj = obj.override_hierarchy_create(scene, view_layer, reference=None, do_fully_editable=True)
            for user_col in obj.users_collection:
                if user_col.library: continue
                user_col.objects.unlink(obj)
            obj = new_obj
            if obj == None: return {'CANCELLED'}
            spawned = obj
        else:
            parent = obj
            while parent.parent:
                parent = parent.parent
                if parent in list(view_layer.objects): continue
                activeCol.objects.link(parent)
            rev_leveled_map[obj] = 0
            recurse2(obj, 1)
            spawned = override_order(obj)
            rev_leveled_map.clear()
            refd_by.clear()

    if col:
        if not col in scene.collection.children_recursive:
            scene.collection.children.link(col)
        if ind_prefs.importer == 'STABLE':
            col_users = bpy.data.user_map(subset=[col])[col]
            new_col = col.override_hierarchy_create(scene, view_layer, reference=None, do_fully_editable=True)
            if new_col == None: return {'CANCELLED'}
            for user in col_users:
                if isinstance(user, bpy.types.Scene):
                    if col in list(user.collection.children):
                        user.collection.children.unlink(col)
                if isinstance(user, bpy.types.Collection):
                    if user.library: continue
                    if col in list(user.children):
                        user.children.unlink(col)
            col = new_col
            spawned = col
        else:
            recurse2(col, 0, [])
            for object in list(col.all_objects):
                if object.parent: continue
                recurse2(object, 0, [])
            spawned = override_order(col)
            override_order(col)
            rev_leveled_map.clear()
            refd_by.clear()

    rev_leveled_map.clear()
    refd_by.clear()
    id_ref = get_id_reference_map()
    id_ref = get_all_referenced_ids(spawned, id_ref)

    sorted_refs = list(map(lambda a: a[0],
        sorted(list(
            rev_leveled_map.items()
        ), key=lambda a: a[1])
    ))

    rev_leveled_map.clear()
    refd_by.clear()

    for ID in filter(lambda a: getattr(a, 'library', None) != None, sorted_refs):
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
    
    for ID in filter(lambda a: getattr(a, 'override_library', None) != None, sorted_refs):
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
        clean_remap(bpy.types.GreasePencilv3)

    if col and prefs.to_cursor:
        for object in spawned.all_objects:
            if object.parent: continue
            object.location = scene.cursor.location

    if obj and prefs.to_cursor:
        top = spawned
        while top.parent != None:
            top = top.parent
        top.location = scene.cursor.location

    context.scene['new_spawn'] = spawned # assign the newly spawned item to a globally accessible variable, giving developers the opportunity to further modify data in the scripts execution stage
    scene['optiploy_last_spawned'] = spawned
    context.scene['optiploy_last_spawned'] = spawned
    if prefs.execute_scripts:
        for text in filter(lambda a: isinstance(a, bpy.types.Text), gatherings['linked']):
            text.as_module()

    scn = context.scene

    # init rigid body physics
    for id in filter(lambda a: isinstance(a, bpy.types.Object), gatherings['override']):
        if getattr(id, 'rigid_body', None):
            if scn.rigidbody_world == None:
                bpy.ops.rigidbody.world_add()
            if (rbw := getattr(scn.rigidbody_world, 'collection', None)) == None:
                rbw = bpy.data.collections.new('RigidBodyWorld')
                scn.rigidbody_world.collection = rbw
            if not id in list(rbw.objects): rbw.objects.link(id)
        if getattr(id, 'rigid_body_constraint', None):
            if scn.rigidbody_world == None:
                bpy.ops.rigidbody.world_add()
            if (rbc := getattr(scn.rigidbody_world, 'constraints', None)) == None:
                rbc = bpy.data.collections.new('RigidBodyConstraints')
                scn.rigidbody_world.constraints = rbc
            if not id in list(rbc.objects): rbc.objects.link(id)
    
    del context.scene['new_spawn']

    map_to_do.clear()
    gatherings['linked'].clear()
    gatherings['override'].clear()
    arms.clear()
    bone_shapes.clear()
    del sorted_refs, map_to_do, gatherings

    bpy.data.orphans_purge(True, False, True)
    return {'FINISHED'}

class SPAWNER_GENERIC_SPAWN_UL_List(UIList):
    def draw_item(self, context,
            layout: bpy.types.UILayout, data,
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
        if Type == 'OBJECT':
            if index != prefs.obj_index:
                row.label(text='Spawn')
                row.separator()
                row.enabled = False
                return
            
        if Type == 'COLLECTION':
            if index != prefs.col_index:
                row.label(text='Spawn')
                row.separator()
                row.enabled = False
                return
            
        op = row.operator('spawner.spawner')
        op.activate=True
        if props.view == 'BLENDS':
            op.blend = int(props.selected_blend)
            op.folder = -1
        if props.view == 'FOLDERS':
            folder = prefs.folders[int(props.selected_folder)]
            op.folder = int(props.selected_folder)
            op.blend = int(folder.selected_blend)
        if Type == 'OBJECT':
            op.object = item.name
            op.collection = ''
        if Type == 'COLLECTION':
            op.collection = item.name
            op.object = ''

class SPAWNER_PT_folder_settings(Panel):
    bl_label = 'Settings'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    bl_options = {'INSTANCED'}

    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences
        props = context.scene.optiploy_props
        layout = self.layout
        layout.label(text='Folder Settings')

        folder = prefs.folders[int(props.selected_folder)]
        layout.prop(folder, 'override_behavior')
        box = layout.box()
        r = box.row()
        r.label(text = 'Importer')
        r.operator('wm.url_open', text='', icon='QUESTION').url = os.path.join(os.path.dirname(__file__), 'htmls', 'importers.html')
        box.row().prop(folder, 'importer', expand=True)
        box.enabled = folder.override_behavior
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
    bl_region_type = 'WINDOW'

    bl_options = {'INSTANCED'}

    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences
        props = context.scene.optiploy_props
        layout = self.layout
        folder = None
        if props.view == 'BLENDS':
            blend = prefs.blends[int(props.selected_blend)]
        else:
            folder = prefs.folders[int(props.selected_folder)]
            blend = folder.blends[int(folder.selected_blend)]
        layout.label(text='Blend Settings')
        row = layout.row()
        row.prop(blend, 'override_behavior')
        #row.enabled = getattr(folder, 'override_behavior', True)
        box = layout.box()
        box.enabled = blend.override_behavior
        r = box.row()
        r.label(text = 'Importer')
        r.operator('wm.url_open', text='', icon='QUESTION').url = os.path.join(os.path.dirname(__file__), 'htmls', 'importers.html')
        box.row().prop(blend, 'importer', expand=True)
        box = layout.box()
        box.enabled = blend.override_behavior
        for i in options:
            box.prop(blend, i)
        box.label(text='Extra Types')
        for i in extra_types:
            box.prop(blend, i)

class SPAWNER_PT_extra_settings(Panel):
    bl_label = 'Extra Localization Options'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    bl_options = {'INSTANCED'}
    
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
            blend_ind = int(props.selected_blend or '0')
            blend = prefs.blends[blend_ind]

            row = layout.row()
            row.alert = True
            op = row.operator('spawner.open_blend', text='', icon='BLENDER')
            op.text = '''Hold CTRL to reload the .blend file as a library.
Hold SHIFT to open the .blend file in a new instance of Blender.
Hold ALT to re-scan the .blend file in OptiPloy.
Don't worry about the button being red. It's only meant to call your attention.'''
            op.icons='EVENT_CTRL,EVENT_SHIFT,EVENT_ALT,QUESTION'
            op.size='56,56,56,56'
            op.width=350
            op.path = blend.filepath
            op.folder = -1
            op.blend = int(props.selected_blend or '0')

            row = row.row()
            row.alert = False
            row.prop(props, 'selected_blend', text='')
            row.popover('SPAWNER_PT_blend_settings', text='', icon='SETTINGS')
            
        if props.view == 'FOLDERS':
            if not len(prefs.folders):
                layout.row().label(text='Add a folder of .blend files in the preferences to get started!')
                return
            folder_ind = int(props.selected_folder or '0')
            folder = prefs.folders[folder_ind]

            row = layout.row()
            row.alert=True
            op = row.operator('spawner.open_folder', text='', icon='FILE_FOLDER')
            op.text = '''Hold ALT to re-scan the .blend file in OptiPloy.
Don't worry about the button being red. It's only meant to call your attention.'''
            op.icons='EVENT_ALT,QUESTION'
            op.size='56,56'
            op.width=350
            op.folder = folder_ind
            row = row.row()
            row.alert=False
            #row.label(text='', icon='FILE_FOLDER')
            row.prop(props, 'selected_folder', text='')
            row.popover('SPAWNER_PT_folder_settings', text='', icon='SETTINGS')
            if not len(folder.blends):
                layout.row().label(text='This folder has no .blend files marked! Has it been scanned?')
                return None
            blend_ind = int(folder.selected_blend or '0')
            blend = folder.blends[blend_ind]
            row = layout.row()
            row.alert = True
            #row.label(text='', icon='BLENDER')
            op = row.operator('spawner.open_blend', text='', icon='BLENDER')
            op.text = '''Hold CTRL to reload the .blend file as a library.
Hold SHIFT to open the .blend file in a new instance of Blender.
Hold ALT to re-scan the .blend file in OptiPloy.
Don't worry about the button being red. It's only meant to call your attention.'''
            op.icons='EVENT_CTRL,EVENT_SHIFT,EVENT_ALT,QUESTION'
            op.size='56,56,56,56'
            op.width=350
            op.path = blend.filepath
            op.folder = int(int(props.selected_folder))
            op.blend = int(folder.selected_blend)

            row = row.row()
            row.alert = False
            row.prop(folder, 'selected_blend', text='')
            row.popover('SPAWNER_PT_blend_settings', text='', icon='SETTINGS')
        
        if props.view != 'TOOLS':
            box = layout.box()
            if not (len(blend.objects) + len(blend.collections)):
                box.row().label(text="Nothing in this file detected! Mark items as assets!")
                return
            objBox = box.box()
            row = objBox.row()
            row.label(text='Objects', icon='OBJECT_DATA')
            op = row.operator('spawner.textbox', icon='QUESTION', text='')
            if len(blend.objects):
                objBox.row().template_list('SPAWNER_GENERIC_SPAWN_UL_List', 'Items',
                                        blend, 'objects', prefs, 'obj_index')
                op.text = '''Here are the objects you can spawn!
To spawn an item, it has to be the active item. This serves as a way of confirming.'''
                op.icons = 'OBJECT_DATA,CHECKMARK'
                op.size='56,56'
                op.width=350
            else:
                objBox.row().label(text='No objects added!')
                op.text = '''The selected .blend file has no objects marked as assets!'''
                op.icons = 'ERROR'
                op.size='56'
                op.width=350
            
            colBox = box.box()
            row = colBox.row()
            row.label(text='Collections', icon='OUTLINER_COLLECTION')
            op = row.operator('spawner.textbox', icon='QUESTION', text='')
            if len(blend.collections):
                colBox.row().template_list('SPAWNER_GENERIC_SPAWN_UL_List', 'Collections',
                                           blend, 'collections', prefs, 'col_index')
                op.text = '''Here are the collections you can spawn!
To spawn an item, it has to be the active item. This serves as a way of confirming.'''
                op.icons = 'OUTLINER_COLLECTION,CHECKMARK'
                op.size='56,56'
                op.width=350
            else:
                colBox.row().label(text='No collections added!')
                op.text = '''The selected .blend file has no collections marked as assets!'''
                op.icons = 'ERROR'
                op.size='56'
                op.width=350

        if props.view == 'TOOLS':
            col = layout.column()
            r = col.row()
            r.label(text='Importer')
            r.operator('wm.url_open', text='', icon='QUESTION').url = os.path.join(os.path.dirname(__file__), 'htmls', 'importers.html')
            col.box().row().prop(prefs, 'importer', expand=True)
            layout.label(text='Post-Processing')
            box = layout.box()
            box.prop(prefs, 'to_cursor')
            box.prop(prefs, 'execute_scripts')
            layout.label(text='Behavior')
            box = layout.box()
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
            layout.separator()
            op = layout.operator('spawner.textbox', text='Donate')
            op.text = '''Like the add-on? Consider supporting my work:
LINK:https://ko-fi.com/hisanimations|NAME:Ko-Fi
LINK:https://superhivemarket.com/products/optiploy-pro|NAME:Buy OptiPloy Pro on Superhive'''
            op.size = '56,56,56'
            op.icons = 'BLANK1,NONE,NONE'
            op.width = 350

class mod_saver(Operator):
    def invoke(self, context, event):
        ctrl, shift, alt = event.ctrl, event.shift, event.alt
        scn = context.scene
        scn['key_ctrl'] = ctrl
        scn['key_shift'] = shift
        scn['key_alt'] = alt
        
        return_val = self.execute(context)
        
        del scn['key_ctrl'], scn['key_shift'], scn['key_alt']
        return return_val

class SPAWNER_OT_SPAWNER(mod_saver):
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

    blend:  IntProperty(default=-1)
    folder: IntProperty(default=-1)
    object: StringProperty(default='')
    collection: StringProperty(default='')
    activate: BoolProperty()
    scene: StringProperty(default='')

    index: IntProperty()

    def execute(self, context):
        if not self.activate: return {'CANCELLED'}
        prefs = context.preferences.addons[base_package].preferences
        blend = self.blend
        folder = self.folder
        obj = self.object
        col = self.collection

        if (folder != -1) and (blend != -1):
            folder = prefs.folders[folder]
            if folder.override_behavior:
                prefs = folder
            entry = folder.blends[blend]
            if entry.override_behavior:
                prefs = entry

        if (blend != -1) and (folder == -1):
            entry = prefs.blends[blend]
            if entry.override_behavior:
                prefs = entry

        if not os.path.exists(entry.filepath):
            self.report({'ERROR'}, f"{entry.filepath} doesn't exist!")
            #self.report({'ERROR'}, "The .blend file no longer exists!")
            return {'CANCELLED'}
        
        try:
            with bpy.data.libraries.load(entry.filepath, link=True, relative=True) as (From, To):
                if obj:
                    To.objects = [obj]
                if col:
                    To.collections = [col]
        except:
            self.report({'ERROR'}, f'The .blend you are trying to open is corrupt!')
            return {'CANCELLED'}
        
        import_scene = bpy.data.scenes.get(self.scene, None) or context.scene
        view_layer = getattr(import_scene, 'view_layers', [context.view_layer])[0] if self.scene else context.view_layer

        scene_viewlayer = [import_scene, view_layer]

        if obj:
            if To.objects[0] == None:
                self.report({'ERROR'}, f'Object "{obj}" could not be found in {os.path.basename(entry.filepath)}')
                return {'CANCELLED'}
            return load_data(self, context, scene_viewlayer, ind_prefs=prefs, obj=To.objects[0])
        
        if col:
            if To.collections[0] == None:
                self.report({'ERROR'}, f'Collection "{col}" could not be found in {os.path.basename(entry.filepath)}')
                return {'CANCELLED'}
            return load_data(self, context, scene_viewlayer, ind_prefs=prefs, col=To.collections[0])
        
        self.report({'WARNING'}, 'What?')
        return {'CANCELLED'}
    
class SPAWNER_OT_POST_OPTIMIZE(mod_saver):
    bl_idname = 'spawner.post_optimize'
    bl_label = 'Optimize with OptiPloy'
    bl_description = 'Optimize the selected linked objects with OptiPloy'

    bl_options = {'UNDO'}

    def execute(self, context):
        #print(context.space_data, context.area.type, context.window, context.screen)
        #return {'CANCELLED'}

        #import_scene = bpy.data.scenes.get(self.scene, None) or context.scene
        #view_layer = getattr(import_scene, 'view_layers', [context.view_layer])[0] if self.scene else context.view_layer

        scene_viewlayer = [context.scene, context.view_layer]

        if context.area.type == 'VIEW_3D':
            ids = context.selected_objects
        if context.area.type == 'OUTLINER':
            ids = context.selected_ids
        cols = set(filter(lambda a: isinstance(a, bpy.types.Collection) and getattr(a, 'library', None) != None, ids)) # get selected collections
        objs = filter(lambda a: isinstance(a, bpy.types.Object), ids) # get selected objects
        objs = set(filter(lambda a: not (True in [col in cols for col in a.users_collection]), objs))  # remove objects if their collection is selected
        objs = set(filter(lambda a: not (getattr(a, 'parent', False) in objs), objs)) # only get the top most selected objects
        true_ids = set()
        for id in objs:
            for col in id.users_collection:
                if col.library:
                    cols.add(col)
                    break
            else:
                true_ids.add(id)
        ids = true_ids.union(cols)
        prefs = context.preferences.addons[base_package].preferences
        for id in ids: 
            conditions_for_instance = [
                getattr(id, 'type', None) == 'EMPTY', # if object is an empty
                getattr(id, 'instance_type', None) == 'COLLECTION', # if the empty has its instance type set to collection
                getattr(getattr(id, 'instance_collection', None), 'library', None) != None, # and the instanced collection has linked library data
            ]
            conditions_for_object = [
                isinstance(id, bpy.types.Object),
                id.library != None,
            ]
            conditions_for_col = [
                isinstance(id, bpy.types.Collection),
                id.library != None,
            ]

            if not False in conditions_for_instance:
                col = id.instance_collection
                return_val = load_data(self, context, scene_viewlayer, ind_prefs=prefs, col=col)
                if return_val == {'FINISHED'}:
                    bpy.data.objects.remove(id)
            elif not False in conditions_for_col:
                load_data(self, context, scene_viewlayer, ind_prefs=prefs, col=id)
            elif not False in conditions_for_object:
                load_data(self, context, scene_viewlayer, ind_prefs=prefs, obj=id)
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
    if sentence.startswith('LINK:'):
        url, name = sentence.split('|')
        url = url.split('LINK:', maxsplit=1)[1]
        name = name.split('NAME:', maxsplit=1)[1]
        #print(url, name)
        layout.row().operator('wm.url_open', text=name, icon='URL').url = url
        return None
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

class generictext(bpy.types.Operator):
    text: StringProperty(default='')
    icons: StringProperty()
    size: StringProperty()
    width: IntProperty(default=400)
    url: StringProperty(default='')

    def invoke(self, context, event):
        if not getattr(self, 'prompt', True):
            return self.execute(context)
        if event.shift and self.url != '':
            bpy.ops.wm.url_open(url=self.url)
            return self.execute(context)
        self.invoke_extra(context, event)
        return context.window_manager.invoke_props_dialog(self, width=self.width)
    
    def invoke_extra(self, context, event):
        pass
    
    def draw(self, context):
        sentences = self.text.split('\n')
        icons = self.icons.split(',')
        sizes = self.size.split(',')
        for sentence, icon, size in zip(sentences, icons, sizes):
            textBox(self.layout, sentence, icon, int(size))
        self.draw_extra(context)

    def draw_extra(self, context):
        pass

    def execute(self, context):
        return {'FINISHED'}

class SPAWNER_OT_genericText(generictext):
    bl_idname = 'spawner.textbox'
    bl_label = 'Hints'
    bl_description = 'A window will display any possible questions you have'

class SPAWNER_OT_open_blend(generictext):

    bl_idname = 'spawner.open_blend'
    bl_label = 'Blend Multi-Tool'
    bl_description = 'Hold Shift to open the selected .blend file, hold Ctrl to reload, hold Alt to re-scan'

    blend: IntProperty()
    folder: IntProperty()
    path: StringProperty(name='Path')

    blend_path_add: StringProperty(default='', subtype='FILE_PATH')
    use_current_blend:BoolProperty(default=False)

    def invoke(self, context, event):
        blendPath = Path(str(self.path))

        if (event.ctrl + event.shift + event.alt) > 1:
            return {'CANCELLED'}
            self.text = 'tee hee no'
            self.icons = 'NONE'
            self.size='56'
            self.width = 310
            return context.window_manager.invoke_props_dialog(self, width=self.width)

        if event.ctrl:
            for lib in bpy.data.libraries:
                blendPathLib = Path(bpy.path.abspath(lib.filepath))
                if blendPathLib == blendPath: lib.reload(); return {'FINISHED'}
            return {'FINISHED'}
        
        if event.shift:
            import subprocess
            subprocess.Popen([bpy.app.binary_path, blendPath])
            return {'FINISHED'}
        
        if event.alt:
            return bpy.ops.spawner.scan('INVOKE_DEFAULT', blend=self.blend, folder=self.folder)
        
        return context.window_manager.invoke_props_dialog(self, width=self.width)
    

    def draw_extra(self, context):
        layout = self.layout
        layout.separator()
        col = layout.column()
        main_row = col.row()
        r = main_row.row()
        r.alignment = 'LEFT'
        r.label(text='Add .blend')
        r = main_row.row()
        r.alignment = 'RIGHT'
        r.enabled = bpy.data.is_saved
        r.prop(self, 'use_current_blend', text='Add Active .blend')
        box = col.box()
        col_box = box.column()
        row = col_box.row()
        row.prop(self, 'blend_path_add', text='Filepath')
        row.enabled = 1-(self.use_current_blend and bpy.data.is_saved)
        op = col_box.operator('spawner.add_entry')
        op.filepath = bpy.data.filepath if (self.use_current_blend and bpy.data.is_saved) else bpy.path.abspath(self.blend_path_add)
        op.execute_only = True
        op.blend = True
        op.folder = bool(self.folder+1)
        op.folder_select = self.folder
    
class SPAWNER_OT_open_folder(generictext):

    bl_idname = 'spawner.open_folder'
    bl_label = 'Folder Multi-Tool'
    bl_description = 'Hold Shift to open the selected folder, hold Ctrl to reload, hold Alt to re-scan'

    folder: IntProperty()
    path: StringProperty(name='Path')

    folder_path_add: StringProperty(default='', subtype='DIR_PATH')
    add_category: BoolProperty(default=False)
    category_name: StringProperty(default='New Category')

    def invoke(self, context, event):
        blendPath = Path(str(self.path))
        self.category_name = 'New Category'

        if (event.ctrl + event.shift + event.alt) > 1:
            return {'CANCELLED'}
            self.text = 'tee hee no'
            self.icons = 'NONE'
            self.size='56'
            self.width = 310
            return context.window_manager.invoke_props_dialog(self, width=self.width)

        if event.ctrl:
            #for lib in bpy.data.libraries:
            #    blendPathLib = Path(bpy.path.abspath(lib.filepath))
            #    if blendPathLib == blendPath: lib.reload(); return {'FINISHED'}
            return {'FINISHED'}
        
        if event.shift:
            #import subprocess
            #subprocess.Popen([bpy.app.binary_path, blendPath])
            return {'FINISHED'}
        
        if event.alt:
            return bpy.ops.spawner.scan('INVOKE_DEFAULT', blend=-1, folder=self.folder)
        
        return context.window_manager.invoke_props_dialog(self, width=self.width)
    

    def draw_extra(self, context):
        layout = self.layout
        layout.separator()
        col = layout.column()
        main_row = col.row()
        r = main_row.row()
        r.alignment = 'LEFT'
        r.label(text='Add Folder')
        r = main_row.row()
        r.alignment = 'RIGHT'
        r.prop(self, 'add_category', text='Add Category')
        box = col.box()
        col_box = box.column()
        row = col_box.row()
        if self.add_category:
            r = row.row()
            r.alignment = 'LEFT'
            r.label(text='Category Name:')
            r = row.row()
            r.alignment = 'RIGHT'
            row.prop(self, 'category_name', text='')
        else:
            row.prop(self, 'folder_path_add', text='Filepath')
        #row.enabled = 1-self.add_category
        op = col_box.operator('spawner.add_entry', text='Add Folder Entry')
        op.directory = self.folder_path_add
        op.execute_only = True
        op.blend = False
        op.folder = True
        op.category = self.add_category
        op.category_name = self.category_name

def draw_item(self:bpy.types.Menu, context):
    layout = self.layout
    layout.separator()
    layout.operator('spawner.post_optimize')

classes = [
    SPAWNER_PT_panel,
    SPAWNER_GENERIC_SPAWN_UL_List,
    SPAWNER_OT_SPAWNER,
    SPAWNER_OT_POST_OPTIMIZE,
    SPAWNER_OT_genericText,
    SPAWNER_PT_extra_settings,
    SPAWNER_PT_folder_settings,
    SPAWNER_PT_blend_settings,
    SPAWNER_OT_open_blend,
    SPAWNER_OT_open_folder
]

def register():
    for i in classes:
        bpy.utils.register_class(i)
    bpy.types.VIEW3D_MT_object.append(draw_item)
    bpy.types.OUTLINER_MT_context_menu.append(draw_item)
    bpy.types.OUTLINER_MT_object.append(draw_item)
    bpy.types.OUTLINER_MT_collection.append(draw_item)

def unregister():
    for i in reversed(classes):
        bpy.utils.unregister_class(i)
    bpy.types.VIEW3D_MT_object.remove(draw_item)
    bpy.types.OUTLINER_MT_context_menu.remove(draw_item)
    bpy.types.OUTLINER_MT_object.remove(draw_item)
    bpy.types.OUTLINER_MT_collection.remove(draw_item)