import bpy
from bpy.types import Panel
from bpy.props import EnumProperty

flag_YES = {'YES'}
flag_MAKE_LIST = {'MAKE_LIST'}

floating_id: bpy.types.ID = None
id_behavior_update_block = False

def return_ids(context):
    if context.area.type in {'OUTLINER', 'VIEW_3D'}:
        return getattr(context, 'selected_ids', None)
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

def id_behavior_update(self, context: bpy.types.Context):
    global id_behavior_update_block
    if id_behavior_update_block:
        return
    id_behavior_update_block = True

    if getattr(context.area, 'type', None) == 'OUTLINER':
        [setattr(id, 'optiploy_id_behavior', self.optiploy_id_behavior) for id in context.selected_ids]
    id_behavior_update_block = False


def text_behavior_update(self, context: bpy.types.Context):
    global id_behavior_update_block
    if id_behavior_update_block:
        return
    id_behavior_update_block = True

    if getattr(context.area, 'type', None) == 'OUTLINER':
        [setattr(id, 'optiploy_text_behavior', self.optiploy_text_behavior) for id in context.selected_ids if isinstance(id, bpy.types.Text)]
    id_behavior_update_block = False


def menu_func(self: bpy.types.Menu, context):
    global floating_id
    if not return_ids_set(context): return
    if getattr(context, 'id', False):
        self.layout.separator()
        self.layout.popover('SPAWNER_PT_id_behavior')
        floating_id = context.id
    else:
        return
    

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

        if isinstance(context.id, bpy.types.Text):
            col = layout.column()
            col.label(text='Text Behavior')
            col.props_enum(context.id, 'optiploy_text_behavior')


classes = [
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
            ('STAY_LINKED', 'Stay Linked', 'Never override nor localize the ID, leaving it linked for maximum efficiency'),
            #('ALWAYS_OVERRIDE', 'Always Override', 'Always override the ID')
        ),
        name = 'ID Behavior',
        description = 'Change how OptiPloy treats individual IDs',
        default='DO_NOTHING',
        update=id_behavior_update
    )
    bpy.types.Text.optiploy_text_behavior = EnumProperty(
        items=(
            ('NO_EXECUTE', 'Do Not Execute', 'Do not execute this text'),
            ('EXECUTE', 'Always Execute', 'Always execute this text')
        ),
        name='Text Behavior',
        description='Change how OptiPloy treats imported Texts',
        default='EXECUTE',
        update=text_behavior_update
    )

def unregister():
    bpy.types.UI_MT_button_context_menu.remove(menu_func)
    del bpy.types.ID.optiploy_id_behavior
    del bpy.types.Text.optiploy_text_behavior
    ur()