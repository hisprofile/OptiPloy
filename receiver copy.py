import bpy
import asyncio
from asyncio.exceptions import *

write_queue = asyncio.Queue()
last_msg = [None]
#client = None
server = None
close = False

def tag(*args, **kwargs):
    print('CLIENT: ', end='')
    print(*args, **kwargs)

async def writer_task(w:asyncio.StreamWriter):
    while True:
        msg: str = await write_queue.get()
        msg += '\n'
        w.write(msg.encode())
        tag(f'sending {msg}')

async def reader_task(r:asyncio.StreamReader):
    global server
    global close
    while True:
        #try:
        #try:
        msg: bytes = await r.readuntil(b'\n')
        #except IncompleteReadError:
        #    continue
        #except ConnectionResetError:
        #    return
        msg = msg.decode().strip('\n')
        tag(f'got {msg}!')
        #except IncompleteReadError:
        #    continue
        
        last_msg[0] = msg
        if msg == 'SERVER_CLOSE':
            tag('closing client!')
            server.close()
            close = True
            return
        
        if msg == 'hello!':
            print(bpy.context)
            print(bpy.context.scene)

async def client_init(host, port):
    global server
    while True:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            break
        except (ConnectionRefusedError, OSError):
            return
            #await asyncio.sleep(1)

    print('connected to main instance!')
    server = writer
    global close
    while True:
        #try:
        #try:
        msg: bytes = await reader.readuntil(b'\n')
        #except IncompleteReadError:
        #    continue
        #except ConnectionResetError:
        #    return
        msg = msg.decode().strip('\n')
        tag(f'got {msg}!')
        #except IncompleteReadError:
        #    continue
        
        last_msg[0] = msg
        if msg == 'SERVER_CLOSE':
            tag('closing client!')
            server.close()
            close = True
            return
        
        if msg == 'hello!':
            print(bpy.context)
            print(bpy.context.scene)
    #await reader_task(reader)
    #r_task = asyncio.create_task(reader_task(reader))
    #w_task = asyncio.create_task(writer_task(writer))
    
    
    print('disconnected from main instance.')

def server_start(host, port):
    print('attempting to connect to server...')
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client_init('127.0.0.1', 29504))
    print('shutting down blender.')
    bpy.ops.wm.quit_blender()

server_start(0, 0)