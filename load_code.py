import bpy
from . import base_package
from collections import defaultdict

def load_data(op: bpy.types.Operator, context: bpy.types.Context, scene_viewlayer, *, post_process=False, ind_prefs=None, obj:bpy.types.Object=None, col:bpy.types.Collection=None, ):
	from typing import Dict, Set
	from bpy.types import ID

	prefs = context.preferences.addons[base_package].preferences
	props = context.scene.optiploy_props
	scene, view_layer = scene_viewlayer
	scene: bpy.types.Scene
	view_layer: bpy.types.ViewLayer
	activeCol = view_layer.active_layer_collection.collection

	bone_shapes = set()
	arms = set()
	map_to_do = {}
	gatherings = {
		'override': list(),
		'linked': list()
	}
	rev_leveled_map = dict()
	refd_by = defaultdict(set)
	
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
		ref_map: Dict[ID, Set[ID]], id: ID, referenced_ids: Set, visited: Set, level#, line=[]
	):
		"""Recursively populate referenced_ids with IDs referenced by id."""
		if id in visited:
			# Avoid infinite recursion from circular references.
			return
		visited.add(id)

		if isinstance(id, bpy.types.Object) and isinstance(getattr(id, 'data', None), bpy.types.Armature):
			arms.add(id)
			bone_shapes.update(set(bone.custom_shape for bone in id.pose.bones))
		#line = list(line)
		#if isinstance(id, bpy.types.Collection): input((id, line, level))
		OP_keep = list()
		for ref in ref_map.get(id, []):
			if (ref in bone_shapes) and (id in arms):
				continue
			if id in refd_by[ref]:
				# if the current ID was already referenced by its reference, then don't process it.
				continue

			if isinstance(ref, bpy.types.Collection) and not (ref in tuple(scene.collection.children_recursive)) and not (getattr(id.override_library, 'reference', None) == ref): 
				OP_keep.append(ref)
				continue

			refd_by[id].add(ref)
			rev_leveled_map[ref] = max(rev_leveled_map.get(ref, -1), level)

			if isinstance(ref, bpy.types.Object) and not (ref in tuple(view_layer.objects)) and not (getattr(id.override_library, 'reference', None) == ref): 
				OP_keep.append(ref)
				if (not isinstance(ref, bpy.types.Object)) or (not isinstance(id, bpy.types.Object)): continue

			referenced_ids.add(ref)
			recursive_get_referenced_ids(
				ref_map=ref_map, id=ref, referenced_ids=referenced_ids, visited=visited, level=level+1#, line=line
			)
		if OP_keep: id['OP_keep'] = OP_keep

	def get_all_referenced_ids(id: ID, ref_map: Dict[ID, Set[ID]]) -> Set[ID]:
		"""Return a set of IDs directly or indirectly referenced by id."""
		referenced_ids = set()
		rev_leveled_map[id] = 0
		recursive_get_referenced_ids(
			ref_map=ref_map, id=id, referenced_ids=referenced_ids, visited=set(), level=0#, line=[id]
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
		bpy.types.NodeTree
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

		for ID, _ in rev_l:
			ID: bpy.types.ID
			scene['test_prop'] = ID
			possible_override = ID.override_create(remap_local_usages=True)
			del scene['test_prop']
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

		UPDATE 4 may 27 2025:
		i talked with dotflare this time about one of their problems. there was an issue in the way objects and collections
		are handled if they are indirectly referenced by the import. if they are used, they are prone to getting deleted
		because they have no users. somehow. so i attach them to the ID that uses those objects to keep them from getting
		deleted.

		'''
		
		if rev_leveled_map.get(ID, -1) >= level: return
		if type(ID) != bpy.types.Key:
			rev_leveled_map[ID] = level
		line = list(line)
		line.append(ID)
		
		refs = bpy.data.user_map().get(ID, [])
		# refs is the list of IDs that are using the given ID
		#if isinstance(ID, bpy.types.Object): input((ID.name, line))
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
			col_to_link = activeCol if prefs.objects_to_active_collection else scene.collection
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
			rev_leveled_map[obj] = 0
			recurse2(obj, 1)
			spawned = override_order(obj)
			override_order(obj)
			rev_leveled_map.clear()
			refd_by.clear()

	if col:
		if not col in scene.collection.children_recursive:
			col_to_link = activeCol if prefs.collections_to_active_collection else scene.collection
			col_to_link.children.link(col)
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

	#return {'FINISHED'}

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
				drivers = getattr(getattr(getattr(possible_override, 'shape_keys', None),'animation_data', None),'drivers', None)
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
		clean_remap(bpy.types.GreasePencilv3)

	if getattr(op, 'do_storage_benchmark', False):
		return spawned

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
	additional.clear()
	bone_shapes.clear()
	del sorted_refs, map_to_do, gatherings

	bpy.data.orphans_purge(True, False, True)
	return {'FINISHED'}

