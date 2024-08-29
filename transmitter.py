import asyncio
import threading
import bpy
import time
from asyncio.exceptions import *
import atexit
import random
import logging
import sys
from . import tx_rx

from typing import Set

logger = logging.getLogger('optiploy_transmitter')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(name)s]-[%(levelname)s]: %(message)s')

if not logger.hasHandlers():
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(sh)


write_queue = None #asyncio.Queue()
last_msg = [None]
client = None
server = None
loop = None

tasks: Set[asyncio.Task] = set()

port_list = [
    29504,
    *[[random.seed(a), random.randrange(1024, 65535)][1] for a in range(20)]
]


def tag(*args, **kwargs):
    print('SERVER: ', end='')
    print(*args, **kwargs)

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

async def writer_task():
    while True:
        print('harp!')
        await asyncio.sleep(0.01)
        msg: str = await write_queue.get()
        if msg == '':
            continue
        msg += '\n'
        tag(f'writing {msg}')
        client.write(msg.encode())

async def write_to_this_hoe(msg:str):
    if client == None:
        return
    msg = f'{msg}\n'
    msg = msg.encode()
    client.write(msg)

def write(msg):
    if client == None:
        return
    #print(msg, type(msg))
    if type(msg) == str:
        msg = f'{msg}\n'
        msg = msg.encode()
        client.write(msg)
        return
    client.write(msg)
    client.write(b'\n')
    return
    #print(msg)
    

def put_to_queue(item):
    async def _(item):
        await write_queue.put(item)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_(item))

async def writerr():
    while True:
        if client:
            client.write('hello!\n'.encode())
        await asyncio.sleep(5)

'''def write(msg:str):
    # will not send a consistent stream of messages
    if client == None:
        return
    msg = f'{msg}\n'
    msg = msg.encode()
    print(msg)
    client.write(msg)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.sleep(0.01))'''

async def clock():
    try:
        while True:
            await asyncio.sleep(0.01)
    except (CancelledError, OSError):
        return

async def rw_callback(reader:asyncio.StreamReader, writer:asyncio.StreamWriter):
    global client
    if client != None:
        logger.warning('Received new client, but client already exists. Closing new client')
        writer.write('SERVER_CLOSE\n'.encode())
        await writer.drain()
        writer.close()
        return
    
    writer.write('OPTIPLOY_SYN\n'.encode())
    try:
        msg = await asyncio.wait_for(reader.readline(), 0.1)
    except TimeoutError:
        #logger.info(f'Attempt connection to port {port}, but received no reply!')
        writer.close()
        return
    msg = msg.decode().strip()
    if msg != 'OPTIPLOY_ACK':
        writer.close()
        return
    
    client = writer
    logger.info('Client has connected!')
    tasks.add(asyncio.create_task(clock()))
    #print('task created.')
    while True:
        try:
            msg: bytes = await reader.readline()
            if not msg:
                if not client:
                    # Client set to None through stop_server()
                    # This code block was entered after both receiving a
                    # zero-length message, and the client having been set to None.
                    for task in tasks:
                        task.cancel()
                        await task
                    tasks.clear()
                    return
                client.close()
                logger.warning('Received zero-length message.')
                raise ConnectionResetError
        except IncompleteReadError:
            continue
        
        except ConnectionResetError:
            '''
            Caused by receiving a zero-length message despite client not being None,
            or the client crashing. The client should not call to close the connection.
            '''
            logger.warning('Client unexpectedly closed. Starting new client.')
            last_msg[0] = 'CLIENT_CLOSE'
            client = None
            for task in tasks:
                task.cancel()
                await task
            tasks.clear()
            print('calling!')
            tx_rx.register()
            return
        
        tag(f'got {msg}!')
        msg = msg.decode().strip('\n')
        last_msg[0] = msg

#@atexit.register
def stop_server():
    logger.info('Server closing.')
    global server
    global client

    if hasattr(server, 'close'):
        if hasattr(client, 'close'):
            pass
            try:
                client.close()
            except OSError:
                print('found it')
            
            client = None
        
        #if server.is_serving():
        try:
            server.close()
        except TypeError:
            print('it happened AGAIN')
            pass
    server = None
    loop = asyncio.get_event_loop()
    return

async def main():
    global server
    for port in port_list:
        try:
            temp_server = await asyncio.start_server(rw_callback, '127.0.0.1', port)
            logger.info(f'Server running on port {port}')
            server = temp_server
            break
        except OSError:
            continue
    else:
        logger.error('Unable to find a suitable port for server. How is that possible?')
        return
    #server = await asyncio.start_server(rw_callback, '127.0.0.1', 29504)
    async with server:
        #try:
        #    await server.serve_forever()
        #except (CancelledError, OSError):
        #    return
        await server.start_serving()
        await server.wait_closed()
    return

def start_server():
    logger.info('Starting server')
    #print('starting server...')
    if server != None:
        return
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    #asyncio.run(main())
    print('server has now been closed.')

def register():
    #return
    print(f'RESET!!!!!!!!!!!!!!!!!!!!!')
    print(random.random())
    if bpy.app.background:
        return
    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()
    print('bro')

def unregister():
    print('unregister transmitter!!!')
    #return
    if server == None:
        return
    stop_server()

#if __name__ == '__main__':
#    start_server()
    # debugging purposes
#register()
#start_server()