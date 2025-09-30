import bpy
from bpy.types import (Operator, Panel, PropertyGroup, Menu)
from bpy.props import (StringProperty, CollectionProperty,
                        IntProperty, EnumProperty,
                        BoolProperty, PointerProperty, FloatProperty)
from .props_append import extra_register, extra_unregister

flag_YES = {'YES'}
flag_MAKE_LIST = {'MAKE_LIST'}

valids = (Operator, Panel, Menu)

floating_id: bpy.types.ID = None

def inherits_from(a, b):
    if isinstance(b, tuple):
        try:
            for i in b:
                if a == i: return False
                if issubclass(a, i): return True
            return False
        except TypeError:
            return False
    try:
        if a == b: return False
        return issubclass(a, b)
    except TypeError:
        return False

def template_any_ID(layout: bpy.types.UILayout, data, property: str, type_property: str, text: str='', text_ctxt: str='', translate: bool=True) -> None:
    id_type_to_collection_name = {
        'ACTION': 'actions',
        'ARMATURE': 'armatures',
        'BRUSH': 'brushes',
        'CAMERA': 'cameras',
        'CACHEFILE': 'cache_files',
        'COLLECTION': 'collections',
        'CURVE': 'curves',
        'CURVES': 'curves',
        'FONT': 'fonts',
        'GREASEPENCIL': 'grease_pencils',
        'GREASEPENCIL_V3': 'grease_pencils_v3',
        'IMAGE': 'images',
        'KEY': 'shape_keys',
        'LATTICE': 'lattices',
        'LIBRARY': 'libraries',
        'LIGHT': 'lights',
        'LIGHT_PROBE': 'lightprobes',
        'LINESTYLE': 'linestyles',
        'MASK': 'masks',
        'MATERIAL': 'materials',
        'MESH': 'meshes',
        'META': 'metaballs',
        'MOVIECLIP': 'movieclips',
        'NODETREE': 'node_groups',
        'OBJECT': 'objects',
        'PAINTCURVE': 'paint_curves',
        'PALETTE': 'palettes',
        'PARTICLE': 'particles',
        'POINTCLOUD': 'pointclouds',
        'SCENE': 'scenes',
        'SCREEN': 'screens',
        'SOUND': 'sounds',
        'SPEAKER': 'speakers',
        'TEXT': 'texts',
        'TEXTURE': 'textures',
        'VOLUME': 'volumes',
        'WINDOWMANAGER': 'window_managers',
        'WORKSPACE': 'workspaces',
        'WORLD': 'worlds'
        }

    row = layout.row(align=True)
    row.alignment = 'EXPAND'
    sub = row.row(align=True)
    sub.alignment = 'LEFT'
    sub.prop(data, type_property, icon_only=False, text='')

    sub = row.row(align=True)
    sub.alignment = 'EXPAND'

    type_name = getattr(data, type_property)
    if type_name in id_type_to_collection_name:
        icon = data.bl_rna.properties[type_property].enum_items[type_name].icon
        sub.prop_search(data, property, bpy.data, id_type_to_collection_name[type_name], text='', icon=icon)

def return_ids(context):
    if context.area.type in {'OUTLINER', 'VIEW_3D'}:
        return context.selected_ids
    elif getattr(context, 'id', None):
        return context.id
    elif context.area.type == 'PROPERTIES':
        space = context.space_data
        space_context = space.context
        match space_context:
            case 'OBJECT':
                return context.object
            case 'DATA':
                return context.object.data
            case 'MATERIAL':
                return context.material
            case 'SCENE':
                return context.scene
            case 'TEXTURE':
                return context.texture
            case 'WORLD':
                return context.world
            case 'COLLECTION':
                return context.collection
            case 'PARTICLES':
                return context.particle_settings
    return floating_id

def return_ids_set(context: bpy.types.Context, poll=False) -> set:
    gatherings = set()
    ids = return_ids(context)
    if '__iter__' in dir(ids):
        gatherings.update(set(ids))
    else:
        gatherings.add(ids)
    gatherings.discard(None)
    if not gatherings:
        return None
    return gatherings

    
class SPAWNER_OT_ID_QUICK_ATTACH(Operator):
    bl_idname = 'spawner.id_quick_attach'
    bl_label = 'ID Quick Attach'
    bl_description = 'Attach list of parasitic IDs to a host ID to ensure their import. If only one parasitic ID is selected, it will not be put in a list. Assigned property will be "optiploy_attach"'

    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if not hasattr(context, 'id'):
            return False
        if len(getattr(context, 'selected_ids', [])) < 2:
            return False
        return True

    def does_exist_prop(self, context):
        id = context.id
        prop = id.get('optiploy_attach', 'HAS_NO_PROP')
        return prop != 'HAS_NO_PROP'
    
    def can_add_to_existing(self, context):
        id: bpy.types.ID = context.id
        prop = id.get('optiploy_attach', 'HAS_NO_PROP')
        if isinstance(prop, list):
            return flag_YES
        if isinstance(prop, bpy.types.ID):
            return flag_MAKE_LIST
        return False

    def execute(self, context):
        host_id = getattr(context, 'id', None)
        if host_id is None:
            return {'CANCELLED'}
        parasitic_ids = return_ids_set(context)
        parasitic_ids.discard(host_id)
        parasitic_ids = list(parasitic_ids)
        if len(parasitic_ids) == 0:
            return {'CANCELLED'}

        can_add = self.can_add_to_existing(context)
        if bool(can_add):
            existing_ids = host_id.get('optiploy_attach')
            if can_add == flag_MAKE_LIST:
                existing_ids = [existing_ids]
            existing_ids.extend(parasitic_ids)
            host_id['optiploy_attach'] = existing_ids
            return {'FINISHED'}
        else:
            if len(parasitic_ids) == 1:
                host_id['optiploy_attach'] = parasitic_ids[0]
            else:
                host_id['optiploy_attach'] = parasitic_ids
            return {'FINISHED'}

class SPAWNER_OT_ID_ATTACH(Operator):
    bl_idname = 'spawner.id_attach'
    bl_label = 'ID Attach'
    bl_description = 'Quickly attach a selected ID to an ID'

    add_to_existing: BoolProperty(default=False, name='Add to Existing', description='Add to the existing property')

    was_invoked = False

    bl_options = {'UNDO'}

    def update_prop(self, context):
        if self.property == '':
            self.property = 'optiploy_attach'

    
    def does_exist_prop(self, context):
        props = context.window_manager.optiploy_props
        if not props.id: return 'HAS_NO_PROP'
        prop = props.id.get(props.property, 'HAS_NO_PROP')
        return prop != 'HAS_NO_PROP'
    
    
    def can_add_to_existing(self, context):
        props = context.window_manager.optiploy_props
        if not props.id: return False
        prop = props.id.get(props.property, 'HAS_NO_PROP')
        if isinstance(prop, list):
            return flag_YES
        if isinstance(prop, bpy.types.ID):
            return flag_MAKE_LIST
        return False

    def invoke(self, context, event):
        self.was_invoked = True
        return context.window_manager.invoke_props_dialog(self, width=400, title='ID Attach', confirm_text='Attach')

    def execute(self, context):
        if not self.was_invoked:
            return self.invoke(context, None)
        
        self.was_invoked = False
        props = context.window_manager.optiploy_props
        if not props.id: return {'CANCELLED'}
        selected_ids = list(return_ids_set(context))
        can_append =  self.can_add_to_existing(context)
        if self.does_exist_prop(context) and bool(can_append) and self.add_to_existing:
            if can_append is flag_MAKE_LIST:
                props.id[props.property] = [props.id[props.property]]
            props.id[props.property] += selected_ids
            return {'FINISHED'}
        if len(selected_ids) == 1:
            selected_ids = selected_ids[0]
        props.id[props.property] = selected_ids
        return {'FINISHED'}


    def draw(self, context):
        does_exist = self.does_exist_prop(context)
        can_append = self.can_add_to_existing(context)
        props = context.window_manager.optiploy_props

        layout = self.layout
        alert = does_exist and not (bool(can_append) and self.add_to_existing) and bool(props.id)
        box = layout.box().column()
        box.label(text='Property:')
        row = box.row()
        row.prop(props, 'property', text='')
        row.alert = alert
        box.alert = alert

        box = layout.box().column()
        box.label(text='Host Data-Block:')
        template_any_ID(box, props, 'id', 'id_type')
        
        box = layout.box().column()
        row = box.row()
        row.prop(self, 'add_to_existing')
        row.enabled = does_exist and bool(can_append)
        if alert:
            box.label(text='Will replace existing property!', icon='ERROR')

class SPAWNER_OT_ID_REMOVE_FROM_HOSTS(Operator):
    bl_idname = 'spawner.id_remove_from_hosts'
    bl_label = 'Remove Selected ID(s) from Host(s)'
    bl_description = 'Remove all selected IDs as an attachment on any host'

    def execute(self, context):
        ids = return_ids_set(context)
        hosts = set()
        [hosts.add(host) for id in ids for host in bpy.data.user_map(subset=[id])[id]]

        for host in hosts:
            if host.library: continue
            for prop, value in list(host.items()):
                if isinstance(value, bpy.types.ID):
                    if value in ids:
                        del host[prop]
                        continue
                elif isinstance(value, list):
                    for id in ids:
                        if not id in value: continue
                        value.remove(id)
                    if len(value) == 0:
                        del host[prop]
                    else:
                        host[prop] = value
                else:
                    continue
        return {'FINISHED'}

class SPAWNER_OT_PARASITE_REMOVE(Operator):
    bl_idname = 'spawner.parasite_remove'
    bl_label = 'Remove ID(s) from Selected Host(s)'
    bl_description = 'From the selected host(s), remove all attachments to data-blocks in the form of custom properties'

    def execute(self, context):
        hosts = return_ids_set(context)
        for host in hosts:
            if host.library: continue
            for prop, value in list(host.items()):
                if isinstance(value, bpy.types.ID):
                    del host[prop]
                    continue
                elif isinstance(value, list):
                    for item in value:
                        if not isinstance(item, bpy.types.ID): continue
                        value.remove(item)
                    if len(value) == 0:
                        del host[prop]
                    else:
                        host[prop] = value
                else:
                    continue
        return {'FINISHED'}

class SPAWNER_OT_make_props_overridable(Operator):
    bl_idname = 'spawner.make_props_overridable'
    bl_label = 'Make Properties Overridable'
    bl_description = 'Make all custom properties on this ID library overridable'

    def execute(self, context):
        ids = return_ids_set(context)
        if not ids: return {'CANCELLED'}
        for id in ids:
            if id.library: continue
            id: bpy.types.ID
            for prop in id.keys():
                id.property_overridable_library_set(f'["{prop}"]', True)
        return {'FINISHED'}

#class SPAWNER_OT_CONTEXT(Operator):
#    bl_idname = 'spawner.context'
#    bl_label = 'context'
#
#    def execute(self, context):
#        print(return_ids_set(context))
#        [print(i) for i in dir(context)]
#        return {'FINISHED'}
#        print(context.space_data.node_tree.nodes.active)
#        print(dir(context.space_data.id))
#        print(context.space_data, context.area.type, context.window, context.screen)


class anyID(PropertyGroup):
    name: StringProperty(default='', name='Name')
    owner: StringProperty(default='', name='Owner')
    mark_for_deletion: BoolProperty(default=False, name='Mark for Deletion')

class SPAWNER_MT_id_tools(Menu):
    bl_label = 'OptiPloy ID Tools'
    def draw(self, context):
        layout:bpy.types.UILayout = self.layout
        ids = return_ids_set(context)
        if not ids: return None
        if context.area.type == 'OUTLINER':
            layout.operator('spawner.id_quick_attach')
            layout.operator('spawner.id_attach')
            layout.operator('spawner.id_remove_from_hosts')
            layout.operator('spawner.parasite_remove')
            layout.separator()
            layout.operator('spawner.make_props_overridable')
        else:
            layout.operator('spawner.id_attach')
            layout.operator('spawner.id_remove_from_hosts')
            layout.operator('spawner.parasite_remove')
            layout.separator()
            layout.operator('spawner.make_props_overridable')

def menu_func(self: bpy.types.Menu, context):
    global floating_id
    if context.area.type == 'OUTLINER':
        self.layout.separator()
        self.layout.menu(SPAWNER_MT_id_tools.__name__, text='OptiPloy ID Tools')
    elif getattr(context, 'id', False):
        self.layout.separator()
        self.layout.menu(SPAWNER_MT_id_tools.__name__, text='OptiPloy ID Tools')
        self.layout.popover('SPAWNER_PT_id_behavior')
        floating_id = context.id
    else:
        return

block = False
def extend_props(cls):
    def reset_id(self, context):
        self.id = None
    cls.id = PointerProperty(type=bpy.types.ID)
    cls.property = StringProperty(default='optiploy_attach')
    cls.id_type = EnumProperty(items=[
        ('', 'ID Type', ''),
        ('ACTION', 'Action', '', 'ACTION', 0),
        ('ARMATURE', 'Armature', '', 'ARMATURE_DATA', 1),
        ('BRUSH', 'Brush', '', 'BRUSH_DATA', 2),
        ('CACHEFILE', 'Cache File', '', 'FILE', 3),
        ('CAMERA', 'Camera', '', 'CAMERA_DATA', 4),
        ('COLLECTION', 'Collection', '', 'OUTLINER_COLLECTION', 5),
        ('CURVE', 'Curve', '', 'CURVE_DATA', 6),
        ('CURVES', 'Curves', '', 'CURVES_DATA', 7),
        ('FONT', 'Font', '', 'FONT_DATA', 8),
        ('GREASEPENCIL', 'Grease Pencil', '', 'GREASEPENCIL', 9),
        ('GREASEPENCIL_V3', 'Grease Pencil v3', '', 'GREASEPENCIL', 10),
        ('IMAGE', 'Image', '', 'IMAGE_DATA', 11),
        ('KEY', 'Key', '', 'SHAPEKEY_DATA', 12),
        ('LATTICE', 'Lattice', '', 'LATTICE_DATA', 13),
        ('LIBRARY', 'Library', '', 'LIBRARY_DATA_DIRECT', 14),
        ('LIGHT', 'Light', '', 'LIGHT_DATA', 15),
        ('LIGHT_PROBE', 'Light Probe', '', 'LIGHTPROBE_SPHERE', 16),
        ('LINESTYLE', 'Line Style', '', 'LINE_DATA', 17),
        ('MASK', 'Mask', '', 'MOD_MASK', 18),
        ('MATERIAL', 'Material', '', 'MATERIAL_DATA', 19),
        ('', '', ''),
        ('MESH', 'Mesh', '', 'MESH_DATA', 20),
        ('META', 'Metaball', '', 'META_DATA', 21),
        ('MOVIECLIP', 'Movie Clip', '', 'TRACKER', 22),
        ('NODETREE', 'Node Tree', '', 'NODETREE', 23),
        ('OBJECT', 'Object', '', 'OBJECT_DATA', 24),
        ('PAINTCURVE', 'Paint Curve', '', 'CURVE_BEZCURVE', 25),
        ('PALETTE', 'Palette', '', 'COLOR', 26),
        ('PARTICLE', 'Particle', '', 'PARTICLE_DATA', 27),
        ('POINTCLOUD', 'Point Cloud', '', 'POINTCLOUD_DATA', 28),
        ('SCENE', 'Scene', '', 'SCENE_DATA', 29),
        ('SCREEN', 'Screen', '', 'WORKSPACE', 30),
        ('SOUND', 'Sound', '', 'SOUND', 31),
        ('SPEAKER', 'Speaker', '', 'SPEAKER', 32),
        ('TEXT', 'Text', '', 'TEXT', 33),
        ('TEXTURE', 'Texture', '', 'TEXTURE_DATA', 34),
        ('VOLUME', 'Volume', '', 'VOLUME_DATA', 35),
        ('WINDOWMANAGER', 'Window Manager', '', 'WINDOW', 36),
        ('WORKSPACE', 'Workspace', '', 'WORKSPACE', 37),
        ('WORLD', 'World', '', 'WORLD_DATA', 38)
    ],
        name='ID Type',
        description='Type of data block to set values to',
        options={'SKIP_SAVE'},
        default='OBJECT',
        update=reset_id)

def remove_props(cls):
    del cls.id_type
    del cls.id
    del cls.property

id_behavior_update_block = False
def id_behavior_update(self, context: bpy.types.Context):
    global id_behavior_update_block
    if id_behavior_update_block:
        return
    id_behavior_update_block = True

    if getattr(context.area, 'type', None) == 'OUTLINER':
        [setattr(id, 'optiploy_id_behavior', self.optiploy_id_behavior) for id in context.selected_ids]
    id_behavior_update_block = False

class SPAWNER_PT_id_behavior(Panel):
    bl_label = 'OptiPloy ID Behavior'
    bl_region_type = 'WINDOW'
    bl_space_type = 'OUTLINER'
    bl_options = {'INSTANCED'}

    def draw(self, context):
        if not getattr(context, 'id', None):
            return
        layout = self.layout
        layout.label(text='Only change if experienced!')
        
        col = layout.column()
        col.props_enum(context.id, 'optiploy_id_behavior')

extra_register.append(extend_props)
extra_unregister.append(remove_props)

classes = [
    SPAWNER_OT_ID_QUICK_ATTACH,
    SPAWNER_OT_ID_ATTACH,
    SPAWNER_OT_ID_REMOVE_FROM_HOSTS,
    SPAWNER_OT_PARASITE_REMOVE,
    SPAWNER_OT_make_props_overridable,
    SPAWNER_MT_id_tools,
    SPAWNER_PT_id_behavior,
]

r, ur = bpy.utils.register_classes_factory(classes)

def register():
    bpy.types.UI_MT_button_context_menu.append(menu_func)
    r()

    bpy.types.ID.optiploy_id_behavior = EnumProperty(
        items=(
            ('DO_NOTHING', 'Do Nothing', 'Perform no additional operations on this ID'),
            ('PREFER_OVERRIDE', 'Prefer Override', 'Prefer overrides over localizing'),
            ('STAY_LINKED', 'Stay Linked', 'Never override nor localize the ID, leaving it linked for maximum efficiency')
        ),
        name = 'ID Behavior',
        description = 'Change how OptiPloy treats individual IDs',
        default='DO_NOTHING',
        update=id_behavior_update
    )

    pass

def unregister():
    bpy.types.UI_MT_button_context_menu.remove(menu_func)
    del bpy.types.ID.optiploy_id_behavior
    ur()