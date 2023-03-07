# TinyGolf
# Copyright Daniel Schroeder 2023
#
# This file is part of TinyGolf.
#
# TinyGolf is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# TinyGolf is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# TinyGolf. If not, see <https://www.gnu.org/licenses/>.

GAME_NAME = "TinyGolf"
GAME_DIR = "/Games/" + GAME_NAME

import gc

# Keeping the GC happy
free_min = gc.mem_free()

def gc_poke():
    global free_min
    free_now = gc.mem_free()
    print("free before poke:", free_now)
    if free_now < free_min:
        free_min = free_now
    gc.collect()
    print("free after poke:", gc.mem_free())

gc_poke()

# Allow loading local modules
from sys import path
path.append(GAME_DIR)

# Load utils and save data to know what graphics to use
import utils
utils.game_name = GAME_NAME
utils.save_data = utils.SaveData()  # sets loaded_save, use_gray
# TODO: remove?
print(f"is_emulator: {utils.is_emulator}")
print(f"use_gray: {utils.use_gray}")
print(f"loaded_save: {utils.loaded_save}")
gc_poke()

# Load graphics
if utils.use_gray:
    import thumbyGrayscale
    graphics = thumbyGrayscale
else:
    import thumbyGraphics
    graphics = thumbyGraphics
    graphics.display.display.shading = bytearray(360)
# Push out loading message
graphics.display.setFPS(30)
graphics.display.fill(0)
graphics.display.drawText(" Loading... ", 0, 15, 1)
graphics.display.update()
gc_poke()

# Load modules used by my modules
from array import array
import math
gc_poke()
import time
gc_poke()
import thumbyHardware
gc_poke()

# Load my remaining modules
gc_poke()
import rasterizer
gc_poke()
import scene
import levels
gc_poke()
import game_state
gc_poke()

# Initialize large state

# import micropython
# gc_poke()
# micropython.mem_info(True)

# TODO: change TR init to not even take chunk_data?
tr_display = scene.TransformedRasterizer(None)
tr_payload = scene.TransformedRasterizer(None)
chunk_data = scene.ChunkData()
payload = rasterizer.PayloadBuffer()

mgs = game_state.MicroGolfState(GAME_DIR, chunk_data, tr_display, tr_payload,
                                graphics.display, payload, scene.BallState())
gc_poke()

# micropython.mem_info(True)

if utils.loaded_save or utils.is_emulator:
    mgs.frame_handler = game_state.FrameHandlerAttract(mgs)
else:
    mgs.frame_handler = \
        game_state.FrameHandlerMenuScreen(game_state.menulist_gfx_choose)
# mgs.frame_handler = game_state.FrameHandlerLevelStart(mgs)
while True:
    mgs.run_frame()
