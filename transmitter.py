So many lines, so little time.

import bpy, asyncio

from bpy.props import *
from bpy.types import Operator, Panel

msgQ = asyncio.Queue()

async def Reader(R: asyncio.StreamReader):
    while True:
        msg = R.readuntil('\n')
        print(f'received {msg}')

async def Writer(W: asyncio.StreamWriter):
    while True:
        msg = msgQ.get()
        print(f'sent {msg}')

async def client_callback(R: asyncio.StreamReader, W: asyncio.StreamWriter) -> None:
    asyncio.gather()

def start_async_server():
    import asyncio

class SPAWNER_OT_transmitter(Operator):
    bl_idname = 'spawner.begin_scan'
    bl_label = 'Begin Scanning'

    def execute(self, context):
