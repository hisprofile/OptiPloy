from . import base_package

import bpy, os

from bpy.types import (UIList, Panel, Operator, Menu)
from bpy.props import *
from collections import defaultdict
from id_tools import return_ids_set
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
	'localize_actions',
]

options_icons = [
	'OUTLINER_COLLECTION',
	'OBJECT_DATA',
	'MESH_DATA',
	'MATERIAL',
	'NODETREE',
	'IMAGE_DATA',
	'ARMATURE_DATA',
	'ACTION',

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

extra_types_icons = [
	'LIGHT_DATA',
	'CAMERA_DATA',
	'CURVE_DATA',
	'FONT_DATA',
	'META_DATA',
	'SURFACE_DATA',
	'VOLUME_DATA',
	'OUTLINER_DATA_GREASEPENCIL'
]

op_props = [
	'activate',
	'blend',
	'collection',
	'folder',
	'index',
	'object'
]

def draw_options(data, layout, options, icons):
	for prop, icon in zip(options, icons):
		row = layout.row()
		r = row.row()
		r.prop(data, prop)
		r = row.row(align=True)
		r.label(text='', icon='UNLINKED' if getattr(data, prop) else 'LINKED')
		r.label(text='', icon=icon)

class SPAWNER_GENERIC_SPAWN_UL_List(UIList):
	def draw_item(self, context,
			layout: bpy.types.UILayout, data,
			item, icon,
			active_data, active_propname,
			index):
		prefs = context.preferences.addons[base_package].preferences
		props = context.window_manager.optiploy_props
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
		row = row.row(align=True)
		row.alignment = 'RIGHT'
		benchmark_op = row.operator('spawner.spawner', icon='DISK_DRIVE', text='')
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

		for attr in op_props:
			setattr(benchmark_op, attr, getattr(op, attr))
		benchmark_op.do_storage_benchmark = True
		op.do_storage_benchmark = False

class SPAWNER_PT_folder_settings(Panel):
	bl_label = 'Settings'
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'WINDOW'

	bl_options = {'INSTANCED'}

	def draw(self, context):
		prefs = context.preferences.addons[base_package].preferences
		props = context.window_manager.optiploy_props
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
		draw_options(folder, box, options, options_icons)
		box.label(text='Extra Types')
		draw_options(folder, box, extra_types, extra_types_icons)

class SPAWNER_PT_blend_settings(Panel):
	bl_label = 'Settings'
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'WINDOW'

	bl_options = {'INSTANCED'}

	def draw(self, context):
		prefs = context.preferences.addons[base_package].preferences
		props = context.window_manager.optiploy_props
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
		draw_options(blend, box, options, options_icons)
		box.label(text='Extra Types')
		draw_options(blend, box, extra_types, extra_types_icons)

class SPAWNER_PT_extra_settings(Panel):
	bl_label = 'Extra Localization Options'
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'WINDOW'

	bl_options = {'INSTANCED'}
	
	def draw(self, context):
		prefs = context.preferences.addons[base_package].preferences
		props = context.window_manager.optiploy_props
		layout = self.layout
		layout.label(text=self.bl_label)
		box = layout.box()
		draw_options(prefs, box, extra_types, extra_types_icons)

class SPAWNER_PT_panel(Panel):
	bl_label = 'OptiPloy'
	bl_space_type='VIEW_3D'
	bl_region_type='UI'
	bl_category = 'OptiPloy'

	def draw(self, context):
		prefs = context.preferences.addons[base_package].preferences
		data = prefs
		props = context.window_manager.optiploy_props
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
				colBox.row().template_list('SPAWNER_GENERIC_SPAWN_UL_List', 'Collections', blend, 'collections', prefs, 'col_index')
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
			layout.operator('preferences.addon_show', text='Open Preferences').module = base_package
			if not context.preferences.use_preferences_save:
				layout.operator('wm.save_userpref')
			col = layout.column()
			r = col.row()
			r.label(text='Importer')
			r.operator('wm.url_open', text='', icon='QUESTION').url = os.path.join(os.path.dirname(__file__), 'htmls', 'importers.html')
			col.box().row().prop(prefs, 'importer', expand=True)
			layout.label(text='Post-Processing')
			box = layout.box()
			box.prop(prefs, 'to_cursor')
			box.prop(prefs, 'execute_scripts')
			box.prop(prefs, 'objects_to_active_collection')
			box.prop(prefs, 'collections_to_active_collection')
			layout.label(text='Behavior')
			box = layout.box()
			draw_options(prefs, box, options, options_icons)
			box.popover('SPAWNER_PT_extra_settings')
#			layout.separator()
#			op = layout.operator('spawner.textbox', text='Donate')
#			op.text = '''Like the add-on? Consider supporting my work:
#LINK:https://ko-fi.com/hisanimations|NAME:Ko-Fi
#LINK:https://superhivemarket.com/products/optiploy-pro|NAME:Buy OptiPloy Pro on Superhive'''
#			op.size = '56,56,56'
#			op.icons = 'BLANK1,NONE,NONE'
#			op.width = 350



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


def draw_item(self:bpy.types.Menu, context):
	layout = self.layout
	ids = return_ids_set(context)
	if not ids: return None
	layout.separator()
	layout.operator('spawner.post_optimize')
	layout.menu('SPAWNER_MT_id_tools')
	layout.popover('SPAWNER_PT_id_behavior')

def add_optiploy_link(self:bpy.types.Menu, context):
	layout = self.layout
	layout.operator('spawner.link', icon='LINK_BLEND')

classes = [
	SPAWNER_PT_panel,
	SPAWNER_GENERIC_SPAWN_UL_List,
	SPAWNER_PT_extra_settings,
	SPAWNER_PT_folder_settings,
	SPAWNER_PT_blend_settings,
]

def register():
	SPAWNER_PT_panel.bl_category = bpy.context.preferences.addons[base_package].preferences.category
	for i in classes:
		bpy.utils.register_class(i)
	bpy.types.VIEW3D_MT_object.append(draw_item)
	bpy.types.OUTLINER_MT_context_menu.append(draw_item)
	bpy.types.OUTLINER_MT_object.append(draw_item)
	bpy.types.OUTLINER_MT_collection.append(draw_item)
	bpy.types.TOPBAR_MT_file_import.append(add_optiploy_link)

def unregister():
	for i in reversed(classes):
		bpy.utils.unregister_class(i)
	bpy.types.VIEW3D_MT_object.remove(draw_item)
	bpy.types.OUTLINER_MT_context_menu.remove(draw_item)
	bpy.types.OUTLINER_MT_object.remove(draw_item)
	bpy.types.OUTLINER_MT_collection.remove(draw_item)
	bpy.types.TOPBAR_MT_file_import.remove(add_optiploy_link)