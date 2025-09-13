import bpy, os
from . import base_package
from bpy.types import Operator
from bpy.props import (StringProperty, IntProperty, CollectionProperty, BoolProperty, EnumProperty)
from .load_code import load_data
from bpy.utils import register_classes_factory
from pathlib import Path
from .panel import options, options_icons, extra_types, extra_types_icons, draw_options, textBox

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

	do_storage_benchmark: BoolProperty(default=False)
	compress_append: BoolProperty(default=False, name='Compress Append Result', description='Choose to compress the result after loading the traditional way via appending')
	compress_optiploy: BoolProperty(default=True, name='Compress OptiPloy Result', description='Choose to compress the result after loading via OptiPloy')

	_time = None

	def invoke(self, context, event):
		if not self.do_storage_benchmark:
			return super().invoke(context, event)
		return context.window_manager.invoke_props_dialog(self)

	def get_prefs(self, context):
		prefs = context.preferences.addons[base_package].preferences
		blend = self.blend
		folder = self.folder

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
		return prefs, entry

	def load_test(self, context):
		obj = self.object
		col = self.collection
		prefs, entry = self.get_prefs(context)
		test_path = os.path.join(os.path.dirname(__file__), 'test.blend')
		temp = bpy.data

		if (was_saved := temp.is_saved):
			re_open = temp.filepath
			bpy.ops.wm.save_mainfile()

		bpy.ops.wm.read_homefile(app_template="")

		with temp.libraries.load(entry.filepath) as (f, t):
			if obj:
				t.objects = [obj]
			if col:
				t.collections = [col]
		item = (t.objects or t.collections)[0]
		temp.libraries.write(test_path, {item}, compress=self.compress_append)
		old_size = os.path.getsize(test_path)
		
		bpy.ops.wm.read_homefile(app_template="")

		with temp.libraries.load(entry.filepath, link=True) as (f, t):
			if obj:
				t.objects = [obj]
			if col:
				t.collections = [col]
		scn = temp.scenes.new('scn')
		item = (t.objects or t.collections)[0]

		if obj:
			spawned = load_data(self, context, [scn, scn.view_layers[0]], ind_prefs=prefs, obj=item)
		if col:
			spawned = load_data(self, context, [scn, scn.view_layers[0]], ind_prefs=prefs, col=item)

		temp.libraries.write(test_path, {spawned}, compress=self.compress_optiploy)
		new_size = os.path.getsize(test_path)
		os.remove(test_path)
		if was_saved:
			bpy.ops.wm.open_mainfile(filepath=re_open)
		else:
			bpy.ops.wm.read_homefile(app_template="")

		def format_size(size_in_bytes):
			"""
			Convert size in bytes to a human-readable format.
			"""
			for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
				if size_in_bytes < 1024.0:
					return f"{size_in_bytes:.2f} {unit}"
				size_in_bytes /= 1024.0
		
		self.report({'INFO'}, f'From {format_size(old_size)} to {format_size(new_size)} with OptiPloy')

		return {'FINISHED'}

	def execute(self, context):
		if not self.activate: return {'CANCELLED'}
		if self.do_storage_benchmark:
			return self.load_test(context)
		prefs = context.preferences.addons[base_package].preferences
		obj = self.object
		col = self.collection

		
		prefs, entry = self.get_prefs(context)

		if not os.path.exists(entry.filepath):
			self.report({'ERROR'}, f"{entry.filepath} doesn't exist!")
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
		
		import_scene = bpy.data.scenes.get(self.scene, None) or context.scene
		view_layer = getattr(import_scene, 'view_layers', [context.view_layer])[0] if self.scene else context.view_layer

		scene_viewlayer = [import_scene, view_layer]
		
		self.report({'WARNING'}, 'What? Neither object nor collection was specified for an import!')
		return {'CANCELLED'}
	
	def draw(self, context):
		sentences = f'''This is for checking how much storage you save with OptiPloy.
This process requires a clean slate.
{"This file has NOT been saved, and you will lose progress if you continue." if not bpy.data.is_saved else "This file will be saved, and then re-opened."}
Continue? '''.split('\n')
		icons = f'DISK_DRIVE,ERROR,{"ERROR" if not bpy.data.is_saved else "CHECKMARK"},QUESTION'.split(',')
		sizes = '56,56,56,56'.split(',')
		for sentence, icon, size in zip(sentences, icons, sizes):
			textBox(self.layout, sentence, icon, int(size))
		self.layout.prop(self, 'compress_append')
		self.layout.prop(self, 'compress_optiploy')
	
class SPAWNER_OT_POST_OPTIMIZE(mod_saver):
	bl_idname = 'spawner.post_optimize'
	bl_label = 'Optimize with OptiPloy'
	bl_description = 'Optimize the selected linked objects with OptiPloy'

	bl_options = {'UNDO'}

	def execute(self, context):

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
		
		# we cannot effectively localize objects if the collection they are in is not localized
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
		self.category_name = 'New Category'

		if (event.ctrl + event.shift + event.alt) > 1:
			return {'CANCELLED'}

		if event.ctrl:
			return {'FINISHED'}
		
		if event.shift:
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

class SPAWNER_OT_link(Operator):
	bl_idname = 'spawner.link'
	bl_label = 'Import with OptiPloy'
	bl_description = 'Link collections/objects, then optimize with OptiPloy'

	bl_options = {'UNDO'}

	filemode: IntProperty(default=1, options={'HIDDEN'})
	files: CollectionProperty(name='File paths', type=bpy.types.OperatorFileListElement)
	directory: StringProperty()
	#filter_glob: StringProperty(default='*.blend', options={'HIDDEN'})
	filter_blender: BoolProperty(default=True, options={'HIDDEN'})
	filter_folder: BoolProperty(default=True, options={'HIDDEN'})
	filter_blenlib: BoolProperty(default=True, options={'HIDDEN'})

	relative_import: BoolProperty(name='Relative Import', description='Write the paths to the libraries in relative format', default=True)

	localize_collections:   BoolProperty(name='Localize collections', description='Fully localize new collections. Will not include new objects from the source .blend file',default=True, options=set())
	localize_objects:	   BoolProperty(default=True, name='Localize objects', options=set())
	localize_meshes:		BoolProperty(default=False, name='Localize mesh data', options=set())
	localize_materials:	 BoolProperty(default=False, name='Localize materials', options=set())
	localize_node_groups:   BoolProperty(default=False, name='Localize node groups', options=set())
	localize_images:		BoolProperty(default=False, name='Localize images', options=set())
	localize_armatures:	 BoolProperty(default=False, name='Localize armatures', options=set())
	localize_actions:	   BoolProperty(default=True, name='Localize actions', options=set())

	localize_lights:		BoolProperty(default=False, name='Localize lights', options=set())
	localize_cameras:	   BoolProperty(default=False, name='Localize cameras', options=set())
	localize_curves:		BoolProperty(default=False, name='Localize curves', options=set())
	localize_text_curves:   BoolProperty(default=False, name='Localize text curves', options=set())
	localize_metaballs:	 BoolProperty(default=False, name='Localize metaballs', options=set())
	localize_surface_curves:BoolProperty(default=False, name='Localize surface curves', options=set())
	localize_volumes:	   BoolProperty(default=False, name='Localize volumes', options=set())
	localize_grease_pencil: BoolProperty(default=False, name='Localize grease pencil', options=set())

	importer: StringProperty(default='FAST', options={'HIDDEN'})

	def invoke(self, context, event):
		prefs = context.preferences.addons[base_package].preferences
		props = context.scene.optiploy_props

		[setattr(self, prop, getattr(prefs, prop)) for prop in [*options, *extra_types]]

		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		prefs = context.preferences.addons[base_package].preferences
		layout = self.layout
		layout.prop(prefs, 'to_cursor')
		layout.prop(self, 'relative_import')
		box = layout.box()
		box.label(text='Localize Options', icon='UNLINKED')
		col = box.column()
		draw_options(self, col, options, options_icons)
		box = layout.box()
		box.label(text='Localize Extra', icon='PLUS')
		col = box.column()
		draw_options(self, col, extra_types, extra_types_icons)
		

	def execute(self, context):
		directory_parts = Path(self.directory).parts
		if not ('.blend' in directory_parts[-2]):
			self.report({'ERROR'}, 'Invalid file selection!')
			return {'CANCELLED'}
		if not (directory_parts[-1] in {'Object', 'Collection'}):
			self.report({'ERROR'}, 'OptiPloy can only link Objects & Collections!')
			return {'CANCELLED'}
		blend_path = os.path.join('', *directory_parts[:-1])
		import_type = 'OBJECT' if directory_parts[-1] == 'Object' else 'COLLECTION'
		import_files = list(map(lambda a: a.name, self.files))

		try:
			with bpy.data.libraries.load(blend_path, link=True, relative=self.relative_import) as (f, t):
				if import_type == 'OBJECT':
					t.objects = import_files
				else:
					t.collections = import_files
		except:
			self.report({'ERROR'}, 'The .blend file you are trying to access is corrupt!')
			return {'CANCELLED'}
		
		scene_viewlayer = [context.scene, context.view_layer]

		if import_type == 'OBJECT':
			for item in t.objects:
				if not item: continue
				load_data(self, context, scene_viewlayer, ind_prefs=self, obj=item)
		if import_type == 'COLLECTION':

			filtered_collections = set(t.collections)
			filtered_collections.discard(None)
			[filtered_collections.discard(child) for col in list(filtered_collections) for child in col.children_recursive]

			for item in filtered_collections:
				if not item: continue
				load_data(self, context, scene_viewlayer, ind_prefs=self, col=item)
		
		return {'FINISHED'}
	
classes = [
	SPAWNER_OT_link,
	SPAWNER_OT_genericText,
	SPAWNER_OT_open_blend,
	SPAWNER_OT_open_folder,
	SPAWNER_OT_POST_OPTIMIZE,
	SPAWNER_OT_SPAWNER,
]

r, ur = register_classes_factory(classes)

def register():
	r()
def unregister():
	ur()