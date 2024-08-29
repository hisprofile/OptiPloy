from multiprocessing import Pool
import bpy
import os
import asyncio
import threading
import random
import logging
import pickle
from asyncio.exceptions import *
import sys

from bpy.types import (UIList, Panel, Operator,
                       Mesh, Object, Material,
                       Armature, NodeGroup, Image,
                       Collection, Text)

from bpy.props import *

from typing import Dict, Set
import bpy
from bpy.types import ID

logger = logging.getLogger('optiploy_receiver')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(name)s]-[%(levelname)s]: %(message)s')
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(formatter)
logger.addHandler(sh)

folder = os.path.dirname(__file__)

write_queue = asyncio.Queue()
last_msg = [None]
#client = None
server = None
close = False
incoming_job = False

port_list = [
    29504,
    *[[random.seed(a), random.randrange(1024, 65535)][1] for a in range(20)]
]

def tag(*args, **kwargs):
    print('CLIENT: ', end='')
    print(*args, **kwargs)

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
    ref_map: Dict[ID, Set[ID]], id: ID, referenced_ids: Set, visited: Set
):
    """Recursively populate referenced_ids with IDs referenced by id."""
    if id in visited:
        # Avoid infinite recursion from circular references.
        return
    visited.add(id)
    for ref in ref_map.get(id, []):
        referenced_ids.add(ref)
        recursive_get_referenced_ids(
            ref_map=ref_map, id=ref, referenced_ids=referenced_ids, visited=visited
        )


def get_all_referenced_ids(id: ID, ref_map: Dict[ID, Set[ID]]) -> Set[ID]:
    """Return a set of IDs directly or indirectly referenced by id."""
    referenced_ids = set()
    recursive_get_referenced_ids(
        ref_map=ref_map, id=id, referenced_ids=referenced_ids, visited=set()
    )
    return referenced_ids

def load_data(ind_prefs: dict, *, obj=None, col=None):
    context = bpy.context
    #col: bpy.types.Collection = bpy.data.collections[col]

    activeCol = context.scene.collection

    map_to_do = {}

    def recursive(d_block):
        user_map = bpy.data.user_map(subset=[d_block])
        IDs = user_map[d_block]
        map_to_do[d_block] = d_block.make_local()
        
        for ID in IDs:
            if map_to_do.get(ID): continue
            #if getattr(ID, 'override_library') != None: continue
            recursive(ID)
        return d_block
    
    filepath = ind_prefs['filepath']

    
    oldTXTs = {*bpy.data.texts}
    
        
    with bpy.data.libraries.load(filepath, link=True, relative=True) as (From, To):
        if obj:
            To.objects = [obj]
        if col:
            To.collections = [col]

    oldOBJs = {*bpy.data.objects}
    oldMesh = {*bpy.data.meshes}
    oldMats = {*bpy.data.materials}
    oldNGs = {*bpy.data.node_groups}
    oldIMGs = {*bpy.data.images}
    oldARMs = {*bpy.data.armatures}
    oldCols = {*bpy.data.collections}

    gather_collections = set()
    gather_objects = set()
    gather_meshes = set()
    gather_materials = set()
    gather_node_groups = set()
    gather_armatures = set()
    gather_images = set()
    gather_texts = set()

    if obj:
        obj: bpy.types.Object = To.objects[0]
        obj = obj.override_create(remap_local_usages=True)
        activeCol.objects.link(obj)
        id_ref = get_id_reference_map()
        id_ref = get_all_referenced_ids(obj, id_ref)

        for ID in id_ref:
            if isinstance(ID, Collection):
                gather_collections.add(ID)
            if isinstance(ID, Object):
                gather_objects.add(ID)
            if isinstance(ID, Mesh):
                gather_meshes.add(ID)
            if isinstance(ID, Material):
                gather_materials.add(ID)
            if isinstance(ID, NodeGroup):
                gather_node_groups.add(ID)
            if isinstance(ID, Image):
                gather_images.add(ID)
            if isinstance(ID, Armature):
                gather_armatures.add(ID)
            if isinstance(ID, Text):
                gather_texts.add(ID)

        if obj.parent != None:
            obj.parent.override_create(remap_local_usages=True)
            activeCol.objects.link(obj.parent)
        
        if ind_prefs.localize_objects:
            obj.make_local()
            if obj.parent: obj.parent.make_local()

    if col:
        col: bpy.types.Collection = To.collections[0]
        context.scene.collection.children.link(col)
        new_col = col.override_hierarchy_create(context.scene, context.view_layer, reference=None, do_fully_editable=True)
        context.scene.collection.children.unlink(col)
        col = new_col
        id_ref = get_id_reference_map()
        id_ref = get_all_referenced_ids(col, id_ref)

        for ID in id_ref:
            if isinstance(ID, Collection):
                gather_collections.add(ID)
            if isinstance(ID, Object):
                gather_objects.add(ID)
            if isinstance(ID, Mesh):
                gather_meshes.add(ID)
            if isinstance(ID, Material):
                gather_materials.add(ID)
            if isinstance(ID, NodeGroup):
                gather_node_groups.add(ID)
            if isinstance(ID, Image):
                gather_images.add(ID)
            if isinstance(ID, Armature):
                gather_armatures.add(ID)
            if isinstance(ID, Text):
                gather_texts.add(ID)

        #for object in col.all_objects:
        #    if (object.type != 'MESH') or (object.data == None):
        #        continue
        #    gather_meshes.add(object.data)
        gather_meshes_new = set()

        '''for mesh in gather_meshes:
            new_mesh = mesh.override_create(remap_local_usages=True)
            #gather_meshes.remove(mesh)
            gather_meshes_new.add(new_mesh)
        gather_meshes = gather_meshes_new'''

        if ind_prefs['localize_collections']:
            recursive(col)
            for cc in gather_collections:
                recursive(cc)

        if ind_prefs['localize_objects']:
            for object in col.objects:
                recursive(object)

            for colChild in col.children_recursive:
                for object in colChild.objects:
                    recursive(object)

            # EXCEPTION_ACCESS_VIOLATION when accessing col.all_objects

    if ind_prefs['localize_meshes']:
        for mesh in gather_meshes:
            recursive(mesh)
            #mesh.make_local()
    else:
        mesh: Mesh
        for mesh in gather_meshes:
            mesh.override_create(remap_local_usages=True)

    if ind_prefs['localize_materials']:
        for material in gather_materials:
            recursive(material)

    if ind_prefs['localize_node_groups']:
        for node_group in gather_node_groups:
            recursive(node_group)
    
    if ind_prefs['localize_images']:
        for image in gather_images:
            recursive(image)

    if ind_prefs['localize_armatures']:
        for armature in gather_armatures:
            recursive(armature)
    else:
        armature: Armature
        for armature in gather_armatures:
            armature.override_create(remap_local_usages=True)

    for linked, local in list(map_to_do.items()):
        linked.user_remap(local)

    print('objs removed:', bpy.data.orphans_purge(True, True, True))

    bpy.data.libraries.write(os.path.join(folder, 'temp.blend'), {col}, path_remap='ABSOLUTE', compress=True)

    for attr_name in dir(bpy.data):
        attr = getattr(bpy.data, attr_name)
        if not isinstance(attr, bpy.types.bpy_prop_collection):
            continue
        if attr_name in {'workspaces', 'window_managers', 'screens'}:
            continue
        if attr == bpy.data.scenes:
            attr: bpy.types.bpy_prop_collection[bpy.types.Scene]
            #bpy.data.batch_remove(attr[1:])
            for scn in attr:
                if scn == context.scene:
                    continue
                attr.remove(scn)
            continue
        else:
            bpy.data.batch_remove(attr[:])

        #print(len(attr), attr_name)

        #bpy.context.window.screen.scene
        bpy.context.window.scene = bpy.data.scenes[0]
        #print(len(attr))
    context.view_layer.update()
    #context.scene.collection.children.link(new_col)

async def read_message(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        msg: bytes = await reader.readline()
    except IncompleteReadError:
        return False
    except (ConnectionResetError, OSError):
        logger.warning('Server closed unexpectedly. Exiting client.')
        server.close()
        server = None
        return False
    
    if not msg:
        logger.info('Received zero-length message. Assuming server is closing.')
        writer.close()
        return False
    return msg

async def client_init():
    global server
    global incoming_job

    #try:
    #    reader, writer = await asyncio.open_connection('127.0.0.1', 29504)
    #    server = writer
    #except (ConnectionRefusedError, OSError):
    #    return

    for port in port_list:
        logger.info(f'Attempting to connect to server on port {port}')
        try:
            reader, writer = await asyncio.open_connection('127.0.0.1', port)
            try:
                msg = await asyncio.wait_for(reader.readline(), 0.1)
            except TimeoutError:
                logger.info(f'Attempt connection to port {port}, but received no handshake!')
                writer.close()
                continue
            except IncompleteReadError:
                writer.close()
                return
            msg = msg.decode().strip()
            if msg == 'OPTIPLOY_SYN':
                writer.write('OPTIPLOY_ACK\n'.encode())
                break
            elif msg == 'SERVER_CLOSE':
                return
            continue
        except (ConnectionRefusedError, OSError):
            continue
    else:
        logger.error('Unable to connect to OptiPloy\'s transmitter! This should not be possible!')
        return
    server = writer
    
    logger.info('Connected to main instance!')
    server = writer
    global close
    while True:
        msg = await read_message(reader, writer)
        if not msg:
            return

        msg = msg.decode().strip()
        tag(f'got {msg}!')
        
        last_msg[0] = msg
        if msg == 'SERVER_CLOSE':
            logger.info('Received server closing. Exiting client.')
            server.close()
            close = True
            return
        
        if msg == 'INCOMING_JOB':
            msg = await read_message(reader, writer)
            print('penis', msg)
            if not msg:
                return
            prefs_dict: dict = pickle.loads(msg)
            #print(prefs_dict)
            obj = prefs_dict.get('obj')
            col = prefs_dict.get('col')
            path = prefs_dict['filepath']

            load_data(prefs_dict, obj=obj, col=col)

            server.write(b'JOB_FINISHED\n')
            continue

        if msg == 'NOTED':
            server.write(b'ACKNOWLEDGED\n')

        if msg == 'hello!':
            #server.close()
            print(bpy.context)
            print(bpy.context.view_layer)
            print(bpy.context.scene)
            pass

def server_start(host=0, port=0):
    #print('attempting to connect to server...')
    if server:
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client_init())
    logger.info('Shutting down blender.')
    bpy.ops.wm.quit_blender()

server_start(0, 0)