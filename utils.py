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

from array import array
from time import ticks_ms
from os import remove

# Status bools and other vars. Set soon after import then left unchanged.
game_name = None
loaded_save = False
use_gray = False
is_emulator = False
save_data = None

try:
    import emulator
    is_emulator = True
except ImportError:
    pass

# Profiling

MAX_TIMESTAMP_MS = const(8)
MAX_TIMESTAMP_RESETS_SINCE_UPDATE = const(5)  # 1 to always update
arr_timestamp_ms = array('l', [0] * MAX_TIMESTAMP_MS)
num_timestamp_ms = 0
num_timestamp_resets_since_update = MAX_TIMESTAMP_RESETS_SINCE_UPDATE - 1

@micropython.native
def timestamp_add():
    global num_timestamp_ms
    global num_timestamp_resets_since_update
    ts = ticks_ms()
    if num_timestamp_resets_since_update == 0 and \
       num_timestamp_ms < MAX_TIMESTAMP_MS:
        arr_timestamp_ms[num_timestamp_ms] = ts
        num_timestamp_ms += 1

@micropython.native
def timestamp_reset():
    global num_timestamp_ms
    global num_timestamp_resets_since_update
    num_timestamp_resets_since_update += 1
    if num_timestamp_resets_since_update >= \
       int(MAX_TIMESTAMP_RESETS_SINCE_UPDATE):
        # Actually reset and record new timestamps
        num_timestamp_resets_since_update = 0
        num_timestamp_ms = 0

def timestamp_display(display):
    # Blank out bottom of screen
    height_bytes = display.height >> 3
    i_start = (height_bytes - 1) * display.width
    buf0 = display.display.buffer
    buf1 = display.display.shading
    for i in range(i_start, i_start + display.width):
        buf0[i] = 0
        buf1[i] = 0
    y = 32
    x = 1
    # display.drawText(f"{free_min}", x, y, 1)
    for i in range(1, num_timestamp_ms):
        delta_ms = arr_timestamp_ms[i] - arr_timestamp_ms[i - 1]
        display.drawText(f"{delta_ms}", x, y, 1)
        x += 13

# Save / load machinery

# bytes: version #, use_gray, i_level, arr_level_strokes (9)
bytes_save_default = \
    bytearray(b'\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    # bytearray(b'\x01\x01\x08\x01\x02\x01\x02\x02\x02\x02\x00\x00')

def get_save_name():
    return "/Saves/" + game_name + ".bin"

def delete_save():
    try:
        remove(get_save_name())
    except:
        pass

def write_save_bytes(bytes_save):
    try:
        with open(get_save_name(), "wb") as f_obj:
            f_obj.write(bytes_save)
    except:
        pass

def read_save_bytes(bytes_save):
    try:
        with open(get_save_name(), "rb") as f_obj:
            bytes_save[0] = 0
            f_obj.readinto(bytes_save)
            if bytes_save[0] != bytes_save_default[0]:
                raise ValueError  # old save format -- ignore
            return True
    except:
        # Bad or no save (includes being in emulator) -- return default save
        bytes_save[:] = bytes_save_default
        return False

class SaveData:
    def __init__(self):
        # Do one-time load
        global loaded_save
        global use_gray
        self._bytes_save = bytearray(len(bytes_save_default))
        loaded_save = read_save_bytes(self._bytes_save)
        # Initialize contents from load
        self.load_as_gray = bool(self._bytes_save[1])
        self.i_level = self._bytes_save[2]
        self.arr_level_strokes = memoryview(self._bytes_save)[3:]

        use_gray = self.load_as_gray

    def save(self):
        # Preserve save format number at [0]
        self._bytes_save[1] = int(self.load_as_gray)
        self._bytes_save[2] = self.i_level
        # arr_level_strokes is memoryview at [3:]
        write_save_bytes(self._bytes_save)
