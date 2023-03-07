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

# A cpython version of ChunkData to initialize and serialize geometry

from array import array
from bake_levels_header import *

def const(x):
    return x

# Relevant "constants" grabbed from micropython
# TODO: KEEP THESE IN SYNC with micropython!

# Can use ints [0, RL_NUM_REGION) as used regions; lower-valued regions draw
# over higher-numbered ones
RL_NUM_REGIONS = const(8)
# Sentinel value that must be set for "unused" regions
# TODO: CRITICAL: keep synced with MGS_REGION_EMPTY
RL_REGION_UNUSED = const(RL_NUM_REGIONS)

MAX_NUM_CHUNKS = const(192)

# First field; found in both chunk types; 0 iff chunk is edge
I_CHUNK_IF_LOOP_MASK_TRIGGER_LAYER = const(0)
# Remaining fields for loop headers
I_CHUNK_LOOP_REGION_FILL = const(1)
I_CHUNK_LOOP_NUM_EDGES = const(2)
I_CHUNK_LOOP_LAST_LOOP = const(3)  # index (start 0, +1 per chunk) of prev loop
# Remaining fields for edges
I_CHUNK_EDGE_X_B = const(1)
I_CHUNK_EDGE_Y_B = const(2)
I_CHUNK_EDGE_REGION_LINE = const(3)
I_CHUNK_NUM_FIELDS = const(4)  # hard-coded below too (bit shifts)

# Regions to use for level geometry -- lower numbers draw over higher
MGS_REGION_WALL = const(0)
MGS_REGION_SLOPE_RIGHT = const(1)
MGS_REGION_SLOPE_DOWN = const(2)
MGS_REGION_SLOPE_LEFT = const(3)
MGS_REGION_SLOPE_UP = const(4)
MGS_REGION_SANDTRAP = const(5)
MGS_REGION_WATER = const(6)
MGS_REGION_FAIRWAY = const(7)
# TODO CRITICAL: keep synced with RL_REGION_UNUSED in rasterizer
MGS_REGION_EMPTY = const(8)

class ChunkData:
    def __init__(self):
        # "Chunks" of geometry data -- each describes a loop of edges, or an
        # edge in the current loop. The final chunk is always a loop of zero
        # edges, pointing back to the previous loop.
        # TODO: see if this tolerates non-zeroed contents
        self.arr_chunk_data = \
            array('h', range(I_CHUNK_NUM_FIELDS * MAX_NUM_CHUNKS))
        for i in range(len(self.arr_chunk_data)):
            self.arr_chunk_data[i] = 0
        self.num_chunks = 0  # not yet in valid state
        self.i_acd_last_loop = 0  # not counting the empty loop at the end
        # Put chunks into valid initial state
        self.clear_geometry()

    # Returns the index into self.arr_chunk_data of the valid zero-edge loop
    # chunk that should be extended to start a new loop or replaced to add an
    # edge to the current loop. Additionally, appends the required zero-edge
    # loop chunk beyond the returned index. This is gross.
    def _get_i_acd_next_chunk(self):
        if self.num_chunks >= MAX_NUM_CHUNKS:
            raise RuntimeError("too many chunks")
        # Append a *second* terminating empty loop, pointing to the same loop as
        # the prior terminating loop
        i_acd_loop = self.num_chunks << 2
        self.num_chunks += 1
        self.arr_chunk_data[i_acd_loop + I_CHUNK_IF_LOOP_MASK_TRIGGER_LAYER] = 1
        self.arr_chunk_data[i_acd_loop + I_CHUNK_LOOP_REGION_FILL] = \
            RL_REGION_UNUSED
        self.arr_chunk_data[i_acd_loop + I_CHUNK_LOOP_NUM_EDGES] = 0
        self.arr_chunk_data[i_acd_loop + I_CHUNK_LOOP_LAST_LOOP] = \
            self.i_acd_last_loop >> 2
        # Return index of former terminating chunk -- it remains a well-formed
        # empty loop pointing to previous loop
        return i_acd_loop - I_CHUNK_NUM_FIELDS

    # Removes all geometry from the chunk array and puts it in a valid state
    def clear_geometry(self):
        self.num_chunks = 0
        self._get_i_acd_next_chunk()

    # Adds a new loop of edges, to be filled as the specified region
    def add_loop(self, region_fill, mask_layer, mask_trigger=0x00):
        if mask_layer <= 0 or mask_trigger < 0 or mask_layer > 0xf or \
           mask_trigger > 0xf:
            raise RuntimeError("bad layer/trigger masks")
        # Add another empty loop past the current empty loop, and get the index
        # of the current empty loop
        i_acd_loop = self._get_i_acd_next_chunk()
        # We now have two empty loops, both pointing to the last legit loop. The
        # second will get overwritten with a chunk; complete the first as the
        # new last legit loop, whose edge count we'll start incrementing.
        self.arr_chunk_data[i_acd_loop + I_CHUNK_IF_LOOP_MASK_TRIGGER_LAYER] = \
            (mask_trigger << 8) | mask_layer
        self.arr_chunk_data[i_acd_loop + I_CHUNK_LOOP_REGION_FILL] = region_fill
        self.i_acd_last_loop = i_acd_loop

    # Adds an edge to the most recently added loop, to extend from the specified
    # vertex to the next vertex added (or to the start of the loop if done), and
    # to be drawn as the specified region (or empty).
    def loop_add_edge(self, x, y, region_line, offset_x=0, offset_y=0):
        i_acd_edge = self._get_i_acd_next_chunk()
        self.arr_chunk_data[self.i_acd_last_loop + I_CHUNK_LOOP_NUM_EDGES] += 1
        self.arr_chunk_data[i_acd_edge + I_CHUNK_IF_LOOP_MASK_TRIGGER_LAYER] = 0
        self.arr_chunk_data[i_acd_edge + I_CHUNK_EDGE_X_B] = x + offset_x
        self.arr_chunk_data[i_acd_edge + I_CHUNK_EDGE_Y_B] = y + offset_y
        self.arr_chunk_data[i_acd_edge + I_CHUNK_EDGE_REGION_LINE] = region_line

    # Adds each pair of values in list_x_y as an edge-start vertex using
    # loop_add_edge(), specifying region_line for all of them
    def loop_add_edge_batch(self, list_x_y, region_line, offset_x=0,
                            offset_y=0):
        if len(list_x_y) % 2 != 0:
            raise RuntimeError("odd-length list_x_y")
        for i in range(0, len(list_x_y), 2):
            self.loop_add_edge(list_x_y[i], list_x_y[i + 1], region_line,
                               offset_x, offset_y)

    def chunk_is_loop(self, i_chunk):
        if i_chunk >= self.num_chunks:
            raise RuntimeError("chunk index out of range")
        return bool(self.arr_chunk_data[(i_chunk << 2) + \
                        I_CHUNK_IF_LOOP_MASK_TRIGGER_LAYER])

    def chunk_edge_get_endpoints(self, i_chunk):
        # Confirm i_chunk is in-range and an edge
        if i_chunk >= self.num_chunks:
            raise RuntimeError("chunk index out of range")
        arr_chunk_data = self.arr_chunk_data
        i_acd_chunk = i_chunk << 2
        if bool(arr_chunk_data[i_acd_chunk + \
                    I_CHUNK_IF_LOOP_MASK_TRIGGER_LAYER]):
            raise RuntimeError("chunk is not an edge")
        # Fetch begin vertex
        x_b = (arr_chunk_data[i_acd_chunk + I_CHUNK_EDGE_X_B] << 16) >> 16
        y_b = (arr_chunk_data[i_acd_chunk + I_CHUNK_EDGE_Y_B] << 16) >> 16
        # Find endpoint's edge chunk, looping back if needed
        i_acd_chunk += I_CHUNK_NUM_FIELDS
        if bool(arr_chunk_data[i_acd_chunk + \
                    I_CHUNK_IF_LOOP_MASK_TRIGGER_LAYER]):
            i_chunk_edge = \
                arr_chunk_data[i_acd_chunk + I_CHUNK_LOOP_LAST_LOOP] + 1
            i_acd_chunk = i_chunk_edge << 2
        # Fetch end vertex
        x_e = (arr_chunk_data[i_acd_chunk + I_CHUNK_EDGE_X_B] << 16) >> 16
        y_e = (arr_chunk_data[i_acd_chunk + I_CHUNK_EDGE_Y_B] << 16) >> 16
        return x_b, y_b, x_e, y_e

    # Returns the byte offset of the start of the serialization of this data
    def append_to_file(self, f):
        offset_start_bytes = f.tell()
        shorts_to_write = self.num_chunks * I_CHUNK_NUM_FIELDS
        self.arr_chunk_data[:shorts_to_write].tofile(f)
        print(f"Wrote {self.num_chunks} chunks.")
        return offset_start_bytes

# Gross. Meh.
class LevelWriter:
    def __init__(self, name_py, name_bin):
        # Open files
        self.file_py = open(name_py, "w")
        self.file_bin = open(name_bin, "wb")

    def write_header(self):
        with open("bake_levels_header.py", "r") as f_header:
            self.file_py.write(f_header.read())
        print("levels = [", file=self.file_py)

    def write_footer(self):
        print("]", file=self.file_py)
        self.file_py.close()
        self.file_bin.close()

    def write_level(self, chunk_data, mask_layer_tee, par, xw_tee, yw_tee,
                    xw_hole, yw_hole):
        num_chunks = chunk_data.num_chunks
        offset_bytes = chunk_data.append_to_file(self.file_bin)
        level_info = LevelInfo(offset_bytes, num_chunks, mask_layer_tee, par,
                               xw_tee, yw_tee, xw_hole, yw_hole)
        print(f"    LevelInfo({offset_bytes}, {num_chunks}, {mask_layer_tee}, "
              f"{par}, {xw_tee}, {yw_tee}, {xw_hole}, {yw_hole}),",
              file=self.file_py)
