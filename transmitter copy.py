import asyncio
import threading
import bpy
import time
from asyncio.exceptions import *
import atexit

write_queue = None #asyncio.Queue()
last_msg = [None]
client = None
server = None
loop = None

def tag(*args, **kwargs):
    print('SERVER: ', end='')
    print(*args, **kwargs)

def write(msg:str):
    if client == None:
        return
    msg = msg + '\n'
    msg = msg.encode()
    print(msg)
    client.write(msg)
    asyncio.run(client.drain())

async def writer_task(w:asyncio.StreamWriter):
    while True:
        msg: str = await write_queue.get()
        msg += '\n'
        tag(f'writing {msg}')
        w.write(msg.encode())

async def reader_task(r:asyncio.StreamReader):
    while True:
        try:
            msg: bytes = await r.readuntil(b'\n')
        except IncompleteReadError:
            if client == None:
                return
            continue
        tag(f'got {msg}!')
        msg = msg.decode().strip('\n')
        last_msg[0] = msg

async def rw_callback(reader:asyncio.StreamReader, writer:asyncio.StreamWriter):
    global client
    global write_queue
    if client != None:
        writer.write('SERVER_CLOSE\n'.encode())
        writer.close()
        return
    client = writer
    print('client has connected!', client)
    while True:
        try:
            msg: bytes = await reader.readuntil(b'\n')
        except IncompleteReadError:
            if client == None:
                return
            continue
        tag(f'got {msg}!')
        msg = msg.decode().strip('\n')
        last_msg[0] = msg
    #await reader_task(reader)

#@atexit.register
def stop_server():
    print('server CLOSE')
    global server
    global client
    if server:
        if client:
            client.write('SERVER_CLOSE\n'.encode())
            client.close()
            client = None

        server.close()
    server = None

async def main():
    global server
    server = await asyncio.start_server(rw_callback, '127.0.0.1', '29504')
    async with server:
        await server.start_serving()
        await server.wait_closed()
        #while True:
        #try:
        #    print('running server!')
        #    #await server.
        #    await server.serve_forever()
        #except asyncio.exceptions.CancelledError:
        #    print('server closing.')
        #    return

def start_server():
    print('starting server...')
    if server != None:
        return
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    print('server has now been closed.')
    #asyncio.run(main())

def register():
    #return
    if bpy.app.background:
        return
    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()

#atexit.register()

def unregister():
    print('unregister transmitter!!!')
    #return
    if server == None:
        return
    stop_server()