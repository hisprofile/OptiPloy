So many lines, so little time.

I'm not sure why I do what I do.

This thing was supposed to be the "scanning" process of the addon. It would launch a new instance of Blender,
connect to the previous instance over a socket, then have the new instance scan and transmit data about the added .blend entries.
Seemingly impossible and very difficult, but doable!

I struggle with perfectionism and being the best I can be. I taunt myself with my own imagination. I think about how cool it would be
to have that useless feature, but no one cares about that! I am genuinely the only one who cares. Everyone else wants a working product.
But no. I have to fulfil my own goals for my own sake. Fulfil them because I think I'll get praise.
I will lose sleep chasing what's in my head.

Consciousness is different from person to person. What a curse it was to give it to humanity at all.

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
