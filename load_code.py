import bpy
from . import base_package
from collections import defaultdict
import traceback

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
		bpy.types.NodeTree,
		#bpy.types.Action
		#bpy.types.ShaderNodeTree,
		#bpy.types.GeometryNodeTree,
		#bpy.types.Image,

		# do NOT add images to this lol
		# i think it actually just makes a copy of the image. bad for optimization

)

def get_collection_dimensions(objs):
	from math import inf
	from mathutils import Vector, Matrix
	min_coords = Vector((inf, inf, inf))
	max_coords = Vector((-inf, -inf, -inf))

	for obj in objs:
		if obj.hide_viewport: continue
		if not obj.type == 'MESH': continue
		#print(obj)
		for corner in obj.bound_box:
			world_corner = obj.matrix_world @ Vector(corner)
			min_coords = Vector(map(min, min_coords, world_corner))
			max_coords = Vector(map(max, max_coords, world_corner))
		#print(min_coords, max_coords)

	b = min_coords
	c = max_coords
	mid_vector = Vector(((b[0]+c[0])/2, (b[1] + c[1])/2, b[2]))
	return Matrix.Translation(mid_vector)

def load_data(op: bpy.types.Operator, context: bpy.types.Context, scene_viewlayer, *, post_process=False, ind_prefs=None, obj:bpy.types.Object=None, col:bpy.types.Collection=None, ):
	from typing import Dict, Set
	from bpy.types import ID

	prefs = context.preferences.addons[base_package].preferences
	scene, view_layer = scene_viewlayer
	scene: bpy.types.Scene
	view_layer: bpy.types.ViewLayer
	active_collection = view_layer.active_layer_collection.collection
	scene_objs = None
	scene_cols = None

	bone_shapes = set()
	arms = set()
	map_to_do = {}
	gatherings = {
		'override': list(),
		'linked': list()
	}
	id_user_level_map = dict() # stores the levels where a data-block is used
	prime_override = dict() # stores the first overridden copy of a linked ID
	id_needs_copy = defaultdict(set) # stores what IDs need copies of other IDs, to be injected into the level map later
	blend_data = context.blend_data
	
	# localizing
	def remap():
		for linked, local in list(map_to_do.items()):
			linked.user_remap(local)
		map_to_do.clear()
	# localizing
	def clean_remap(TYPE):
		for ID in filter(lambda a: isinstance(a, TYPE), gatherings['override']):
			if getattr(ID, 'optiploy_id_behavior', 'DO_NOTHING') == 'PREFER_OVERRIDE':
				continue
			map_to_do[ID] = ID.make_local()
		remap()
		for ID in filter(lambda a: isinstance(a, TYPE), gatherings['linked']):
			if getattr(ID, 'optiploy_id_behavior', 'DO_NOTHING') == 'PREFER_OVERRIDE':
				continue
			if getattr(ID, 'optiploy_id_behavior', 'DO_NOTHING') == 'STAY_LINKED':
				continue
			map_to_do[ID] = ID.make_local()
		remap()
	# used by aggressive overrider
	def get_id_reference_map() -> Dict[ID, Set[ID]]:
		"""Return a dictionary of direct datablock references for every datablock in the blend file."""
		inv_map = {}
		for key, values in blend_data.user_map().items():
			for value in values:
				if value == key:
					# So an object is not considered to be referencing itself.
					continue
				inv_map.setdefault(value, set()).add(key)
		return inv_map

	# build a hierarchy of IDs that are being used by the current ID
	# aggressive overrider
	ref_map: Dict[ID, Set[ID]]
	def inv_build_using_hierarchy(id: ID, level, line=[]):
		if getattr(id, 'optiploy_id_behavior', 'DO_NOTHING') == 'STAY_LINKED':
			return

		if isinstance(id, bpy.types.Object) and isinstance(getattr(id, 'data', None), bpy.types.Armature):
			arms.add(id)
			bone_shapes.update(set(bone.custom_shape for bone in id.pose.bones))

		if id_user_level_map.get(id, -1) >= level:
			return

		if not isinstance(id, bpy.types.Key):
			id_user_level_map[id] = level
			line = list(line)
			line.append(id)
		else:
			id_user_level_map[id.user] = level
			line = list(line)
			line.append(id.user)

		#input((ref, level+1, line + [ref]))

		OP_keep = list() # to store used collections or objects outside of the scene.
		for ref in ref_map.get(id, []):
			if (ref in bone_shapes) and (id in arms or isinstance(id, (bpy.types.Collection, bpy.types.Scene))):
				continue
			if getattr(id.override_library, 'reference', None) == ref:
				continue
			if getattr(ref, 'optiploy_id_behavior', 'DO_NOTHING') == 'STAY_LINKED':
				continue

			# example use case: if the bone shape collection is for some reason referenced, and outside of the scene collection, then don't process it!
			# if the collection is truly necessary, it would be a child a the main collection
			if isinstance(ref, bpy.types.Collection) and not (ref in scene_cols) and not (getattr(id.override_library, 'reference', None) == ref):
				OP_keep.append(ref)
				continue

			# to minimize the amount of data overridden/localized, don't process object references if the object referenced is outside of the scene collection
			# if the object is truly necessary, it would be linked to the main collection or its child
			if isinstance(ref, bpy.types.Object) and (not ref in scene_objs) and (not getattr(id.override_library, 'reference', None) == ref): 
				OP_keep.append(ref)
				if (not isinstance(ref, bpy.types.Object)) and (not isinstance(id, bpy.types.Object)):
					continue
			
			#print((ref, level+1, line + [ref]))
			
			if ref in line:
				# DO NOT ALLOW further recursion if we have already completed Mesh->Shape Key or Shape Key->Mesh
				# In the overrider, they are the same, and to go further is pointless.
				if isinstance(ref, bpy.types.Key) and isinstance(id, bpy.types.Mesh):
					continue
				if isinstance(ref, bpy.types.Mesh) and isinstance(id, bpy.types.Key):
					continue
				if (id in ref_map.get(ref, [])):
					id_needs_copy[id].add(ref)
					id_needs_copy[ref].discard(id)
				continue

			inv_build_using_hierarchy(id=ref, level=level+1, line=line)

		if OP_keep: id['OP_keep'] = OP_keep
	
	# necessary overrider
	def override_order(reference):
		additional = set()
		for id, num in id_user_level_map.items():
			copies_needed = id_needs_copy[id]
			for copy in copies_needed:
				additional.add((copy, num-1))

		rev_l = reversed(
			sorted(
				list(id_user_level_map.items()) + list(additional),
				key=lambda a: a[1]
			)
		)

		#rev_l = list(rev_l)
		#print(rev_l)

		for ID, _ in rev_l:
			ID: bpy.types.ID
			# if all users of an ID are linked when we attempt to override the ID, nothing will happen.
			# so we have to force a local user to use it so we get something in return.
			if isinstance(ID, bpy.types.Key):
				ID = ID.user
			scene['test_prop'] = ID
			possible_override = ID.override_create(remap_local_usages=True)
			del scene['test_prop']
			if possible_override != None:
				first = prime_override.setdefault(ID, possible_override)
				possible_override.user_remap(first)
				# if shape keys are using the owner mesh block via a driver or something, it won't get updated with a new overridden mesh.
				# therefore, make a duplicate mesh just once per mesh if shape keys are present, and remap the duplicate to the new.
				if getattr(ID, 'shape_keys', None) and possible_override == first:
					duplicate_for_shape_keys = ID.override_create(remap_local_usages=True)
					duplicate_for_shape_keys.user_remap(first)
					blend_data.batch_remove({duplicate_for_shape_keys})
				if first != possible_override:
					#if isinstance(possible_override, bpy.types.Mesh) and (getattr(possible_override, 'shape_keys', None) != None):
					#	blend_data.batch_remove({possible_override.shape_keys})
					blend_data.batch_remove({possible_override})

			if ID == reference:
				old, spawned = ID, possible_override
		return spawned
	
	# build a hierarchy of IDs that are using the current ID
	# necessary overrider
	def build_user_hierarchy(id, level=0, line:list=[], last=None):
		if id_user_level_map.get(id, -1) >= level: return
		if not isinstance(id, bpy.types.Key):
			id_user_level_map[id] = level
			line = list(line)
			line.append(id)
		else:
			id_user_level_map[id.user] = level
			line = list(line)
			line.append(id.user)
		
		users = user_map.get(id, [])
		# refs is the list of IDs that are using the given ID
		for user in users:
			if user == id: continue
			if getattr(user, 'library', None) == None: continue
			
			
			#print((user, level+1, line + [user]))

			# if the reference has already been processed, then there is a circular reference loop and we need to handle it.
			# we will make a duplicate specifically for the referencer. when the duplicated reference gets overridden,
			# we will immediately replace it with the original overridden reference to maintain the circular reference loop.
			if user in line:
				# DO NOT ALLOW further recursion if we have already completed Mesh->Shape Key or Shape Key->Mesh
				# In the overrider, they are the same, and to go further is pointless.
				if isinstance(user, bpy.types.Key) and isinstance(id, bpy.types.Mesh):
					continue
				if isinstance(user, bpy.types.Mesh) and isinstance(id, bpy.types.Key):
					continue
				id_needs_copy[user].add(id)
				id_needs_copy[id].discard(user)
				continue

			build_user_hierarchy(user, level + 1, line, id)

	user_map = blend_data.user_map()

	'''
	NECESSARY OVERRIDER

	Override the bare minimum to ensure the import works.
	It will override the objects/collections, then override the IDs that use those objects/collections, then the IDs that use those IDs, etc.

	There are two ways of doing this:
	Using BPY (Stable importer)
		This was the first implementation of performing necessary overriding. It uses the "override_hierarchy_create" function
		on the top most collection to automatically override the objects and collections.
		This works fine, but when you want to actually edit the objects and collections, you can't do anything until you
		localize them. When you do localize them, you break the hierarchy, which causes Blender to panic and rework the hierarchy.
		This lengthens the spawning time depending on how many objects are associated with the import. 1 localize = 1 panic

		Despite all the panicking, Blender is able to compensate perfectly well, and everything works as expected. Along with the
		longer spawning time, it absolutely FLOODS the console with errors. I don't like that.

	Using recursion (Fast importer)
		We will be precise and override everything in a specific order, an order discovered through recursion.
		It's like a pythonic implementation of the "override_hierarchy_create" function. It's very difficult to explain how it works
		other than using the word "recursion". Relationship between data-blocks can be very complicated.

	The reference map used here gives us a list of what IDs are using an ID.

	Example: (!> = "used by")
	obj_tex_coord !> Material !> Mesh !> Object
	Override order:
	Object > Mesh > Material > obj_tex_coord
	
	'''

	if obj:
		if not obj in list(view_layer.objects):
			col_to_link = active_collection if (prefs.objects_to_active_collection and not (active_collection.library or active_collection.override_library)) else scene.collection
			col_to_link.objects.link(obj)
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
				col_to_link.objects.link(parent)
			build_user_hierarchy(obj, 0, [])
			spawned = override_order(obj)

	if col:
		if not col in scene.collection.children_recursive:
			col_to_link = active_collection if (prefs.objects_to_active_collection and not (active_collection.library or active_collection.override_library)) else scene.collection
			col_to_link.children.link(col)
		if ind_prefs.importer == 'STABLE':
			col_users = blend_data.user_map(subset=[col])[col]
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
			build_user_hierarchy(col, 0, [])
			for object in list(col.all_objects):
				if object.parent: continue
				build_user_hierarchy(object, 0, [])
			spawned = override_order(col)

			#from bpy_extras import id_map_utils
			#personal_ref_map = id_map_utils.get_id_reference_map()
			#all_ids = id_map_utils.get_all_referenced_ids(col, personal_ref_map)
			#for id in all_ids:
			#	if id.optiploy_id_behavior != 'ALWAYS_OVERRIDE': continue
			#	print(id)
			#	build_user_hierarchy(id, 0, [])

	'''
	END NECESSARY OVERRIDER
	'''
			
	id_user_level_map.clear()
	id_needs_copy.clear()

	'''
	AGGRESSIVE OVERRIDER

	The philosophy of this whole thing is to override as much as possible, but with exceptions.

	If we override as much as possible, then we can change localize settings for future imports without it affecting prior imports in the project.
	This is, in my opinion, accomplishing expected behavior.

	As for the exceptions:
	Do not process referenced ID if:
		the referenced ID is a Collection and it is outside the viewlayer
		the referenced ID is an Object, the referencer is an Object, and the referenced ID is outside the viewlayer
		the referenced ID is a bone shape object, and the referencer is an armature. (a gatherer is ran to gather all bone shapes in an armature to perform this check)
		^ For this to work, the bone shapes NEED to be outside of the viewlayer. Otherwise, they risk being caught in the necessary overrider and getting localized when they aren't needed

		the referenced ID is the override library reference for the referencer ID
		the referenced ID is set to STAY_LINKED via optiploy_id_behavior
		the referenced ID is already in the "line", or tree. In which case, make note that the referencer wants a copy of the referenced ID to be injected into the level map later
	If the referenced ID is a shape key block, force it to be interpreted as a mesh block.
	
	The reference map used here gives us a list of what IDs an ID is using.

	Example: (-> = "is using")
	Object -> Geometry Node Group -> Mesh -> Material
	Override order:
	Object > Geometry Node Group > Mesh > Material

	'''

	scene_objs = tuple(scene.collection.all_objects)
	scene_cols = tuple(scene.collection.children_recursive)

	ref_map = get_id_reference_map()
	inv_build_using_hierarchy(spawned, 0, [])

	additional = set()
	for id, num in id_user_level_map.items():
		copies_needed = id_needs_copy[id]
		for copy in copies_needed:
			additional.add((copy, num+1))

	sorted_refs = sorted(
		list(id_user_level_map.items()) + list(additional),
		key=lambda a: a[1]
		)
	
	#sorted_refs = list(sorted_refs)
	#print(sorted_refs)
	
	#if False:#prefs.aggressive_overriding:
	for ID, _ in filter(lambda a: getattr(a[0], 'library', None) != None, sorted_refs):
		if isinstance(ID, bpy.types.Key):
			ID = ID.user
		if isinstance(ID, override_support):
			possible_override = ID.override_create(remap_local_usages=True)
			if possible_override != None:
				first = prime_override.setdefault(ID, possible_override)
				possible_override.user_remap(first)
				if getattr(ID, 'shape_keys', None) and possible_override == first:
					duplicate_for_shape_keys = ID.override_create(remap_local_usages=True)
					duplicate_for_shape_keys.user_remap(first)
					blend_data.batch_remove({duplicate_for_shape_keys})
				if first != possible_override:
					#if isinstance(possible_override, bpy.types.Mesh) and (getattr(possible_override, 'shape_keys', None) != None):
					#	blend_data.batch_remove({possible_override.shape_keys})
					blend_data.batch_remove({possible_override})
				ID = first
		if ID in gatherings['linked']: continue
		gatherings['linked'].append(ID)
	#else:
	#	[gatherings['linked'].append(ID) for ID in filter(lambda a: getattr(a, 'library', None) != None, sorted_refs)]

	for ID, _ in filter(lambda a: getattr(a[0], 'override_library', None) != None, sorted_refs):
		if ID.override_library.reference in gatherings['linked']:
			gatherings['linked'].remove(ID.override_library.reference)
		if ID in gatherings['override']: continue
		gatherings['override'].append(ID)

	'''
	END AGGRESSIVE OVERRIDER
	'''

	#return {'FINISHED'}
		
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
	if ind_prefs.localize_actions:
		clean_remap(bpy.types.Action)
	
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
		if hasattr(bpy.types, 'GreasePencilv3'):
			clean_remap(bpy.types.GreasePencilv3)

	if getattr(op, 'do_storage_benchmark', False):
		return spawned
	#return {'FINISHED'}
	from mathutils import Matrix

	if col:
		if prefs.placement_type == 'BY_ORIGIN':
			for object in spawned.all_objects:
				if object.parent: continue
				object.location = scene.cursor.location
		elif prefs.placement_type == 'BY_BOUNDS':
			view_layer.update()
			center = get_collection_dimensions(spawned.all_objects)
			for object in spawned.all_objects:
				if object.parent: continue
				if any([con.type == 'CHILD_OF' for con in object.constraints]): continue
				object.matrix_world = Matrix.Translation(scene.cursor.location) @ center.inverted() @ object.matrix_world

	if obj and prefs.to_cursor:
		top = spawned
		if prefs.placement_type == 'BY_ORIGIN':
			while top.parent != None:
				top = top.parent
			top.location = scene.cursor.location
		elif prefs.placement_type == 'BY_BOUNDS':
			view_layer.update()
			all_objs = [top]
			while top.parent != None:
				top = top.parent
				all_objs.append(top)
			center = get_collection_dimensions(all_objs)
			top.matrix_world = Matrix.Translation(scene.cursor.location) @ center.inverted() @ object.matrix_world

	context.scene['new_spawn'] = spawned # assign the newly spawned item to a globally accessible variable, giving developers the opportunity to further modify data in the scripts execution stage
	scene['optiploy_last_spawned'] = spawned
	context.scene['optiploy_last_spawned'] = spawned

	if prefs.execute_scripts:
		script_exec_failed = False
		for text in filter(lambda a: isinstance(a, bpy.types.Text), gatherings['linked']):
			try:
				text.as_module()
			except Exception as err:
				script_exec_failed = True
				print(f'{repr(text)}: Failed to execute! Reason:')
				traceback.print_exc()
				op.report({'ERROR'}, f'{text.name}: {type(err).__name__}: {err}')
				print('\n')

		if script_exec_failed:
			op.report({'ERROR'}, 'Script(s) failed to execute. Read console for information!')

	scn = scene

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
	additional.clear()
	prime_override.clear()
	bone_shapes.clear()
	del sorted_refs, map_to_do, gatherings

	bpy.data.orphans_purge(True, False, True)
	return {'FINISHED'}

