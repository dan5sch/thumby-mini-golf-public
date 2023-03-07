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
import math

import utils
from rasterizer import *

# Misc math helpers

@micropython.native
def sqrt_int(x):
    return int(math.sqrt(x))

# Helpers to deal with angles expressed as an integer number of degrees wrapped
# to [0, 360) -- "wrapped degrees" or "wd". Interpreted as an angle from +x in
# the direction of +y, for the +x and +y of Thumby display space.

@micropython.viper
def wd_init(angle_degrees:int) -> int:
    return angle_degrees % 360

COEFF_DEGREES_TO_RADIANS = const(0.01745329251)
COEFF_RADIANS_TO_DEGREES = const(57.2957795130)

# Returns the sin of the wrapped-degrees angle in fixed point
# TODO: lookup table?
@micropython.native
def sin_wd_f10(wd):
    return int(math.sin(wd * COEFF_DEGREES_TO_RADIANS) * 1024)

@micropython.native
def cos_wd_f10(wd):
    return int(math.cos(wd * COEFF_DEGREES_TO_RADIANS) * 1024)

# Returns the angle of the edge's normal, oriented inwards if the edge is on the
# CCW-wound perimeter of a polygon
@micropython.native
def normal_inward_wd(x_b, y_b, x_e, y_e):
    return wd_init(
        int(math.atan2(y_e - y_b, x_e - x_b) * COEFF_RADIANS_TO_DEGREES) - 90)

# Returns true if an object with velocity at the specified angle would hit the
# edge side that a normal of angle normal_wd extends outward from
@micropython.viper
def velocity_hits_normal_wd(v_angle_wd:int, normal_wd:int) -> bool:
    diff = v_angle_wd - normal_wd
    if diff < 0:
        diff = 0 - diff
    return diff > 90 and diff < 270

# Returns the angle of the velocity of an object after reflecting off a surface
# with the indicated normal, assuming velocity_hits_normal_wd()
@micropython.viper
def reflect_velocity_about_normal_wd(v_angle_wd:int, normal_wd:int) -> int:
    # Just use mod, whatever
    return ((normal_wd << 1) - v_angle_wd - 180) % 360

# Returns the effective normal to use for reflecting velocity at the endpoint
# between the edges with the two specified normals, if the object touches both
# edges and velocity_hits_normal_wd() for both normals
@micropython.viper
def get_endpoint_normal_wd(normal0_wd:int, normal1_wd:int) -> int:
    # Just use mod again
    # Find wd to add to normal0's angle to get normal1
    zero_to_one_wd = (normal1_wd - normal0_wd) % 360
    # Return angle of half vector for shorter arc between 0 and 1
    if zero_to_one_wd < 180:
        return (normal0_wd + (zero_to_one_wd >> 1)) % 360
    else:
        return (normal0_wd + (zero_to_one_wd >> 1) + 180) % 360

# Serializable representation of scene geometry

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
        self.num_chunks = 0
        # Derived edge normal data for collision detection / response
        self.arr_chunk_normal_wd = array('h', range(MAX_NUM_CHUNKS))
        # AABB
        self.xw_lo = 0
        self.yw_lo = 0
        self.xw_hi = 0
        self.yw_hi = 0

    @micropython.native
    def _update_derived(self):
        # Update edge normals, AABB
        xw_lo = 1 << 20
        yw_lo = 1 << 20
        xw_hi = -xw_lo
        yw_hi = -yw_lo
        for i_chunk in range(self.num_chunks):
            if self.chunk_is_loop(i_chunk):
                continue
            xw_b, yw_b, xw_e, yw_e = \
                self.chunk_edge_get_endpoints(i_chunk)
            xw_lo = min(xw_lo, xw_b)
            xw_hi = max(xw_hi, xw_b)
            yw_lo = min(yw_lo, yw_b)
            yw_hi = max(yw_hi, yw_b)
            self.arr_chunk_normal_wd[i_chunk] = \
                normal_inward_wd(xw_b, yw_b, xw_e, yw_e)
        self.xw_lo = xw_lo
        self.yw_lo = yw_lo
        self.xw_hi = xw_hi
        self.yw_hi = yw_hi

    def load_level(self, level, file_name):
        with open(file_name, "rb") as f:
            f.seek(level.offset_bytes)
            f.readinto(self.arr_chunk_data)
            self.num_chunks = level.num_chunks
        self._update_derived()

    @micropython.native
    def chunk_is_loop(self, i_chunk):
        if i_chunk >= self.num_chunks:
            raise RuntimeError("chunk index out of range")
        return bool(self.arr_chunk_data[(i_chunk << 2) + \
                        I_CHUNK_IF_LOOP_MASK_TRIGGER_LAYER])

    @micropython.native
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

# Transforming and rasterizing ChunkData

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

# Bit to OR with non-wall region numbers to form the payload values for those
# regions. For wall edges, will use the edges' chunk indices as the payload.
MGS_PAYLOAD_BIT_NON_WALL = const(1 << 11)
MGS_PAYLOAD_MASK_LOW = const(MGS_PAYLOAD_BIT_NON_WALL - 1)
# Shift to apply to trigger mask to OR it with region payload, for regions that
# are layer-mask reset triggers
MGS_PAYLOAD_SHIFT_MASK_TRIGGER = const(12)

# Fill patterns for different slope directions -- successive CW in world space
# starting with +x
fill_bytes_src_directions0 = bytearray(b'\
\x00\x55\x22\x00\x00\x55\x22\x00\
\x00\x44\x66\x00\x00\x44\x66\x00\
\x22\x44\x22\x00\x22\x44\x22\x00\
\x66\x44\x00\x00\x66\x44\x00\x00\
\x22\x55\x00\x00\x22\x55\x00\x00\
\x33\x11\x00\x00\x33\x11\x00\x00\
\x22\x11\x22\x00\x22\x11\x22\x00\
\x00\x11\x33\x00\x00\x11\x33\x00')
fill_bytes_src_directions1 = bytearray(b'\
\xff\xff\xff\xff\xff\xff\xff\xff\
\xff\xff\xff\xff\xff\xff\xff\xff\
\xff\xff\xff\xff\xff\xff\xff\xff\
\xff\xff\xff\xff\xff\xff\xff\xff\
\xff\xff\xff\xff\xff\xff\xff\xff\
\xff\xff\xff\xff\xff\xff\xff\xff\
\xff\xff\xff\xff\xff\xff\xff\xff\
\xff\xff\xff\xff\xff\xff\xff\xff')

# Fill patterns for frames of water animation
fill_bytes_src_water0 = bytearray(b'\
\x21\x12\x10\x20\x02\x01\x02\x22\
\x02\x20\x20\x12\x11\x22\x02\x01\
\x00\x02\x01\x22\x22\x12\x11\x22\
\x12\x21\x02\x02\x00\x22\x21\x12')
fill_bytes_src_water1 = bytearray(b'\
\x74\xaa\x45\xaa\x57\xaa\x57\xaa\
\xaa\x75\xaa\x47\xaa\x77\xaa\x54\
\x55\xaa\x54\xaa\x77\xaa\x44\xaa\
\xaa\x74\xaa\x57\xaa\x77\xaa\x47')

# Fill patters for regions -- indexed by MGS_REGION_*. Slopes are redundant.
fill_bytes_src_regions_bw = bytearray(b'\
\xff\xff\xff\xff\xff\xff\xff\xff\
\x00\x55\x22\x00\x00\x55\x22\x00\
\x22\x44\x22\x00\x22\x44\x22\x00\
\x22\x55\x00\x00\x22\x55\x00\x00\
\x22\x11\x22\x00\x22\x11\x22\x00\
\xef\xfd\xb7\xfe\xef\x7f\xfb\xbf\
\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00')
fill_bytes_src_regions0 = bytearray(b'\
\xff\xff\xff\xff\xff\xff\xff\xff\
\x00\x55\x22\x00\x00\x55\x22\x00\
\x22\x44\x22\x00\x22\x44\x22\x00\
\x22\x55\x00\x00\x22\x55\x00\x00\
\x22\x11\x22\x00\x22\x11\x22\x00\
\xff\xff\xff\xff\xff\xff\xff\xff\
\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00')
# B&W version of regions
fill_bytes_src_regions1 = bytearray(b'\
\x00\x00\x00\x00\x00\x00\x00\x00\
\xff\xff\xff\xff\xff\xff\xff\xff\
\xff\xff\xff\xff\xff\xff\xff\xff\
\xff\xff\xff\xff\xff\xff\xff\xff\
\xff\xff\xff\xff\xff\xff\xff\xff\
\xff\xff\xff\xff\xff\xff\xff\xff\
\x00\x00\x00\x00\x00\x00\x00\x00\
\xff\xff\xff\xff\xff\xff\xff\xff')

# Fill arrays updated per frame from the above and used by actual draw logic
fill_bytes_draw_regions0 = bytearray(len(fill_bytes_src_regions0))
fill_bytes_draw_regions1 = bytearray(len(fill_bytes_src_regions0))

# Fills ptr_fill_bytes_dst with the fill pattern from ptr_fill_bytes_src shifted
# by the delta in x and y with wrapping
@micropython.viper
def copy_fill_bytes_shift(ptr_fill_bytes_src:ptr8, ptr_fill_bytes_dst:ptr8,
                          delta_x:int, delta_y:int):
    delta_x = delta_x & 0x7
    delta_y = delta_y & 0x7
    # Copy src fill to dst, performing x shift
    for i_src in range(int(8)):
        ptr_fill_bytes_dst[(i_src + delta_x) & 0x7] = ptr_fill_bytes_src[i_src]
    # Apply y shift to each fill byte of dst
    for i_dst in range(int(8)):
        shifted = ptr_fill_bytes_dst[i_dst] << delta_y
        ptr_fill_bytes_dst[i_dst] = (shifted | (shifted >> 8)) & 0xff

# Overwrites contents of fill_bytes_draw_regions* to appropriate fill patterns
# given the cumulative x and y deltas relative to the fills in fill_bytes_src_*,
# the camera angle, and the value of utils.use_gray
list_mgs_region_non_slope = [MGS_REGION_WALL, MGS_REGION_SANDTRAP,
                             MGS_REGION_FAIRWAY]
@micropython.viper
def set_fill_bytes_draw(delta_x:int, delta_y:int, angle_wd:int):
    # Get appropriate source and destination arrays
    if utils.use_gray:
        src_regions0 = ptr8(fill_bytes_src_regions0)
    else:
        src_regions0 = ptr8(fill_bytes_src_regions_bw)
    src_regions1 = ptr8(fill_bytes_src_regions1)
    src_directions0 = ptr8(fill_bytes_src_directions0)
    src_directions1 = ptr8(fill_bytes_src_directions1)
    dst_regions0 = ptr8(fill_bytes_draw_regions0)
    dst_regions1 = ptr8(fill_bytes_draw_regions1)
    src_water0 = ptr8(fill_bytes_src_water0)
    src_water1 = ptr8(fill_bytes_src_water1)

    # Copy non-slope region fills, applying delta
    for i_region in list_mgs_region_non_slope:
        off_bytes = int(i_region) << 3
        src = ptr8(int(src_regions0) + off_bytes)
        dst = ptr8(int(dst_regions0) + off_bytes)
        copy_fill_bytes_shift(src, dst, delta_x, delta_y)
        src = ptr8(int(src_regions1) + off_bytes)
        dst = ptr8(int(dst_regions1) + off_bytes)
        copy_fill_bytes_shift(src, dst, delta_x, delta_y)
    # Copy appropriate water frame, applying delta
    i_water = (int(utils.ticks_ms()) >> 8) & 0x3
    off_bytes_water = i_water << 3
    off_bytes_region = int(MGS_REGION_WATER) << 3
    src = ptr8(int(src_water0) + off_bytes_water)
    dst = ptr8(int(dst_regions0) + off_bytes_region)
    copy_fill_bytes_shift(src, dst, delta_x, delta_y)
    src = ptr8(int(src_water1) + off_bytes_water)
    dst = ptr8(int(dst_regions1) + off_bytes_region)
    copy_fill_bytes_shift(src, dst, delta_x, delta_y)
    # Copy appropriate source direction to each slope region fill, w/ delta
    i_off_dir = ((angle_wd + 22) // 45)
    for i_dir in range(int(4)):
        off_bytes_direction = (((i_dir << 1) + i_off_dir) & 0x7) << 3
        off_bytes_region = (int(MGS_REGION_SLOPE_RIGHT) + i_dir) << 3
        src = ptr8(int(src_directions0) + off_bytes_direction)
        dst = ptr8(int(dst_regions0) + off_bytes_region)
        copy_fill_bytes_shift(src, dst, delta_x, delta_y)
        src = ptr8(int(src_directions1) + off_bytes_direction)
        dst = ptr8(int(dst_regions1) + off_bytes_region)
        copy_fill_bytes_shift(src, dst, delta_x, delta_y)

class TransformedRasterizer:
    def __init__(self, chunk_data):
        self.rasterizer = ScanlineRasterizer(fill_bytes_draw_regions0,
                                             fill_bytes_draw_regions1)
        # Whether to re-specify geometry to rasterizer before next draw
        self.update_rasterizer_geometry = True
        # Not owned; can be replaced
        self.chunk_data = chunk_data
        # Amount to scale world about (0,0)
        self.scale_f10 = 1 << 10
        self.inv_scale_f10 = 1 << 10
        # Amount to rotate world about (0,0)
        self.angle_wd = 0
        self.cos_f10 = 1 << 10
        self.sin_f10 = 0
        # After scale and rotation, amount to translate screen-space geometry
        self.translate_screen_x = 0
        self.translate_screen_y = 0
        # State for deciding how to translate fill patterns
        self.xw_last_draw_f10 = 0
        self.yw_last_draw_f10 = 0
        self.xs_last_draw = 0
        self.ys_last_draw = 0
        self.xw_next_draw_f10 = 0
        self.yw_next_draw_f10 = 0
        self.delta_x_accum = 0
        self.delta_y_accum = 0

    @micropython.native
    def set_chunk_data(self, chunk_data):
        self.chunk_data = chunk_data
        self.update_rasterizer_geometry = True

    @micropython.viper
    def world_to_screen_f10(self, x_world_f10:int, y_world_f10:int):
        scale_f10 = int(self.scale_f10)
        cos_f10 = int(self.cos_f10)
        sin_f10 = int(self.sin_f10)

        # scale -> f10
        x_f10 = (x_world_f10 * scale_f10 + 0x200) >> 10
        y_f10 = (y_world_f10 * scale_f10 + 0x200) >> 10
        # rotate -> f20
        x_f20 = x_f10 * cos_f10 - y_f10 * sin_f10
        y_f20 = x_f10 * sin_f10 + y_f10 * cos_f10
        # translate -> f10
        return ((x_f20 + 0x200) >> 10) + (int(self.translate_screen_x) << 10), \
               ((y_f20 + 0x200) >> 10) + (int(self.translate_screen_y) << 10)

    @micropython.viper
    def screen_to_world_f10(self, x_screen_f10:int, y_screen_f10:int):
        inv_scale_f10 = int(self.inv_scale_f10)
        cos_f10 = int(self.cos_f10)
        sin_f10 = int(self.sin_f10)

        # translate -> f10
        x_f10 = x_screen_f10 - (int(self.translate_screen_x) << 10)
        y_f10 = y_screen_f10 - (int(self.translate_screen_y) << 10)
        # rotate -> f20
        x_f20 = y_f10 * sin_f10 + x_f10 * cos_f10
        y_f20 = y_f10 * cos_f10 - x_f10 * sin_f10
        # scale -> f10
        return (((x_f20 + 0x200) >> 10) * inv_scale_f10 + 0x200) >> 10, \
               (((y_f20 + 0x200) >> 10) * inv_scale_f10 + 0x200) >> 10

    @micropython.native
    def get_scale_f10(self):
        return self.scale_f10

    @micropython.native
    def set_scale_f10(self, scale_f10):
        self.update_rasterizer_geometry = True
        self.scale_f10 = scale_f10
        self.inv_scale_f10 = (0x100000 // scale_f10)

    @micropython.native
    def get_angle_wd(self):
        return self.angle_wd

    @micropython.native
    def set_angle_wd(self, angle_degrees):
        self.update_rasterizer_geometry = True
        self.angle_wd = wd_init(angle_degrees)
        self.cos_f10 = cos_wd_f10(self.angle_wd)
        self.sin_f10 = sin_wd_f10(self.angle_wd)

    @micropython.native
    def set_translate_screen(self, x, y):
        # do NOT force update to rasterizer geometry
        self.translate_screen_x = x
        self.translate_screen_y = y

    @micropython.native
    def add_to_translate_screen(self, delta_x, delta_y):
        # do NOT force update to rasterizer geometry
        self.translate_screen_x += delta_x
        self.translate_screen_y += delta_y

    # Sets screen-space translation such that, with the other transforms held
    # constant, point (xw, yw) in world space maps to (xs, ys) in screen space
    @micropython.native
    def set_translate_map_world_to_screen_f10(self, xw_f10, yw_f10, xs_f10,
                                              ys_f10):
        # do NOT force update to rasterizer geometry
        # Stash world-space coords as next ones to drive fill translate
        self.xw_next_draw_f10 = xw_f10
        self.yw_next_draw_f10 = yw_f10
        # Get screen-space coordinates corresponding to (xw, yw) under current
        # translation
        xs_actual_f10, ys_actual_f10 = self.world_to_screen_f10(xw_f10, yw_f10)
        xs_actual = (xs_actual_f10 + 0x200) >> 10
        ys_actual = (ys_actual_f10 + 0x200) >> 10
        # Modify translation as needed so (xw, yw) maps to (xs, ys) instead
        xs_desired = (xs_f10 + 0x200) >> 10
        ys_desired = (ys_f10 + 0x200) >> 10
        self.translate_screen_x += xs_desired - xs_actual
        self.translate_screen_y += ys_desired - ys_actual

    # Clears the rasterizer and fills it with all scene geometry using the
    # current transform EXCEPT FOR the screen-space translate
    @micropython.viper
    def _set_rasterizer_geometry(self):
        rasterizer = self.rasterizer
        rasterizer.clear_edges()
        arr_chunk_data = ptr16(self.chunk_data.arr_chunk_data)
        # Will achieve translation w/ rasterizer's window
        # maybe_translate_screen_x = int(self.translate_screen_x)
        # maybe_translate_screen_y = int(self.translate_screen_y)
        maybe_translate_screen_x = int(0)
        maybe_translate_screen_y = int(0)
        scale_f10 = int(self.scale_f10)
        cos_f10 = int(self.cos_f10)
        sin_f10 = int(self.sin_f10)

        # Transform edges and add to rasterizer
        # TODO: restructure as single loop over successive chunks, and dedup the
        # x, y transform logic, using the back-links?
        i_acd_end = int(I_CHUNK_NUM_FIELDS) * int(self.chunk_data.num_chunks)
        i_acd_loop = int(0)
        while i_acd_loop < i_acd_end:
            # Fetch loop parameters and skip past if empty
            mask_trigger_layer = arr_chunk_data[i_acd_loop + \
                int(I_CHUNK_IF_LOOP_MASK_TRIGGER_LAYER)]
            mask_trigger = mask_trigger_layer >> 8
            mask_layer = mask_trigger_layer & 0xff
            region_fill = \
                arr_chunk_data[i_acd_loop + int(I_CHUNK_LOOP_REGION_FILL)]
            payload_fill = region_fill | int(MGS_PAYLOAD_BIT_NON_WALL) | \
                (mask_trigger << int(MGS_PAYLOAD_SHIFT_MASK_TRIGGER))
            num_edges_loop = \
                arr_chunk_data[i_acd_loop + int(I_CHUNK_LOOP_NUM_EDGES)]
            if num_edges_loop == 0:
                # Skip empty loop
                i_acd_loop += int(I_CHUNK_NUM_FIELDS)
                continue
            # Fetch last edge's parameters and transform its start vertex
            i_acd_edge_last = \
                i_acd_loop + int(I_CHUNK_NUM_FIELDS) * num_edges_loop

            # Get x and y, propagating sign bit because Viper sucks
            x = arr_chunk_data[i_acd_edge_last + int(I_CHUNK_EDGE_X_B)]
            x = (x << 16) >> 16
            y = arr_chunk_data[i_acd_edge_last + int(I_CHUNK_EDGE_Y_B)]
            y = (y << 16) >> 16
            # scale -> f10
            x *= scale_f10
            y *= scale_f10
            # rotate -> f20
            x_b = x * cos_f10 - y * sin_f10
            y_b = x * sin_f10 + y * cos_f10
            # back to int and translate if needed
            x_b = ((x_b + 0x80000) >> 20) + maybe_translate_screen_x
            y_b = ((y_b + 0x80000) >> 20) + maybe_translate_screen_y

            region_line = \
                arr_chunk_data[i_acd_edge_last + int(I_CHUNK_EDGE_REGION_LINE)]
            payload_line = i_acd_edge_last >> 2
            # Add edge *ending* at each edge in loop
            i_acd_edge = i_acd_loop + int(I_CHUNK_NUM_FIELDS)
            i_acd_loop = i_acd_edge_last + int(I_CHUNK_NUM_FIELDS)
            while i_acd_edge < i_acd_loop:
                # Get x and y, propagating sign bit because Viper sucks
                x = arr_chunk_data[i_acd_edge + int(I_CHUNK_EDGE_X_B)]
                x = (x << 16) >> 16
                y = arr_chunk_data[i_acd_edge + int(I_CHUNK_EDGE_Y_B)]
                y = (y << 16) >> 16
                # scale -> f10
                x *= scale_f10
                y *= scale_f10
                # rotate -> f20
                x_e = x * cos_f10 - y * sin_f10
                y_e = x * sin_f10 + y * cos_f10
                # back to int and translate if needed
                x_e = ((x_e + 0x80000) >> 20) + maybe_translate_screen_x
                y_e = ((y_e + 0x80000) >> 20) + maybe_translate_screen_y

                rasterizer.add_edge_line_fill(x_b, y_b, x_e, y_e, region_line,
                                              region_fill, payload_line,
                                              payload_fill, mask_layer)
                x_b = x_e
                y_b = y_e
                region_line = \
                    arr_chunk_data[i_acd_edge + int(I_CHUNK_EDGE_REGION_LINE)]
                payload_line = i_acd_edge >> 2
                i_acd_edge += int(I_CHUNK_NUM_FIELDS)
            # (Already advanced loop index to next loop above)

    @micropython.native
    def _maybe_update_rasterizer_geometry(self):
        if self.update_rasterizer_geometry:
            self._set_rasterizer_geometry()
            self.update_rasterizer_geometry = False

    @micropython.native
    def _update_fill_patterns(self):
        # See how much last-draw world point moved on screen
        xs_f10, ys_f10 = \
            self.world_to_screen_f10(
                self.xw_last_draw_f10, self.yw_last_draw_f10)
        # Translate fill per that delta
        self.delta_x_accum += ((xs_f10 + 0x200) >> 10) - self.xs_last_draw
        self.delta_y_accum += ((ys_f10 + 0x200) >> 10) - self.ys_last_draw
        self.delta_x_accum &= 0x7
        self.delta_y_accum &= 0x7
        set_fill_bytes_draw(self.delta_x_accum, self.delta_y_accum,
                            self.angle_wd)
        # Stash upcoming draw's world and screen points as last draw
        self.xw_last_draw_f10 = self.xw_next_draw_f10
        self.yw_last_draw_f10 = self.yw_next_draw_f10
        xs_f10, ys_f10 = \
            self.world_to_screen_f10(
                self.xw_last_draw_f10, self.yw_last_draw_f10)
        self.xs_last_draw = (xs_f10 + 0x200) >> 10
        self.ys_last_draw = (ys_f10 + 0x200) >> 10

    # Rasterizes all scene geometry to the display such that (0, 0) in the
    # current transform's screen space maps to the top left of the display
    @micropython.native
    def rasterize_to_display(self, display, mask_layer, debug_offset_x=0,
                             debug_offset_y=0):
        self._maybe_update_rasterizer_geometry()
        self._update_fill_patterns()
        # Rasterize edges, applying final screen-space translate via window
        # TODO: clear display here first?
        self.rasterizer.rasterize_to_buffer(
            display.display.buffer, display.display.shading,
            SR_BUFFER_TYPE_DISPLAY, mask_layer,
            -self.translate_screen_x - debug_offset_x,
            -self.translate_screen_y - debug_offset_y,
            display.width, display.height)

    # Rasterizes all scene geometry to the payload buffer such that (0, 0) in
    # the current transform's screen space maps to the top left of thte payload
    # buffer
    @micropython.native
    def rasterize_payload(self, payload_buffer, mask_layer):
        self._maybe_update_rasterizer_geometry()
        # Rasterize edges, applying final screen-space translate via window
        payload_buffer.fill(MGS_REGION_EMPTY | MGS_PAYLOAD_BIT_NON_WALL)
        self.rasterizer.rasterize_to_buffer(
            payload_buffer.buffer, payload_buffer.buffer,
            SR_BUFFER_TYPE_PAYLOAD, mask_layer, -self.translate_screen_x,
            -self.translate_screen_y, payload_buffer.width,
            payload_buffer.height)

    # Draws the edge corresponding to i_chunk to the screen using thumby.display
    # using the current transform
    @micropython.native
    def debug_draw_edge_chunk(self, display, i_chunk, color, debug_offset_x=0,
                              debug_offset_y=0):
        # Confirm chunk is in-range edge chunk
        if i_chunk >= self.chunk_data.num_chunks or \
           self.chunk_data.chunk_is_loop(i_chunk):
            return
        # Get world-space endpoints from chunk
        xw_b, yw_b, xw_e, yw_e = \
            self.chunk_data.chunk_edge_get_endpoints(i_chunk)
        # Transform endpoints to screen space
        xs_b_f10, ys_b_f10 = self.world_to_screen_f10(xw_b << 10, yw_b << 10)
        xs_e_f10, ys_e_f10 = self.world_to_screen_f10(xw_e << 10, yw_e << 10)
        xs_b = ((xs_b_f10 + 0x200) >> 10) + debug_offset_x
        ys_b = ((ys_b_f10 + 0x200) >> 10) + debug_offset_y
        xs_e = ((xs_e_f10 + 0x200) >> 10) + debug_offset_x
        ys_e = ((ys_e_f10 + 0x200) >> 10) + debug_offset_y
        # Rasterize screen-space line
        display.drawLine(xs_b, ys_b, xs_e, ys_e, color)

# Ball (and hole) state and physics logic

# Constants describing ball dimensions -- diameter assumed odd
BALL_DIAMETER = const(5)
BALL_RADIUS_FLOOR = const(2)

# Constants describing hole -- diameter assumed odd
BALL_HOLE_DIAMETER = const(9)
BALL_HOLE_RADIUS_FLOOR = const(4)
BALL_HOLE_RADIUS_SQ_F20 = const(21233664)
BALL_HOLE_SLOW_F20 = const(10240)
BALL_HOLE_ANG_DEFLECT = const(60)
BALL_HOLE_MAX_SPEED_ENTER_F10 = const(110)

# Friction coefficients. Units? What units?
BALL_COEFF_GRASS_F20 = const(15)
BALL_COEFF_SAND_F20 = const(100)
BALL_SUBTR_WALL_F20 = const(24000)
BALL_COEFF_SLOPE_F20 = const(128)

# Constants for classifying ball as stopped
BALL_COEFF_A = const(3)
BALL_DELTA_W_STOPPED_F10 = const(1024)
BALL_MS_BEFORE_STOPPED = const(500)
BALL_MS_BEFORE_SINK = const(100)

# The physics state of a golf ball. Operates on outside state describing the
# scene geometry and an outside rasterizer for collision detection.
class BallState:
    def __init__(self):
        # Location (world space, fixed precision)
        self.xw_f10 = 0
        self.yw_f10 = 0
        # Velocity, as angle (wrapped degrees) and speed (world units per ms)
        self.v_angle_wd = 0
        self.v_w_per_ms_f20 = 0
        # The chunk indices of the up to two edges the ball collided with during
        # the last timestep, or -1
        self.maybe_i_chunk_contact0 = -1
        self.maybe_i_chunk_contact1 = -1
        # The layer(s) currently occupied by the ball / to be drawn
        self.mask_layer = 0xf
        # Tracking water contact and resetting to position before
        self.water_ms = 0
        self.in_water = False
        self.xw_last_shot_f10 = 0
        self.yw_last_shot_f10 = 0
        # Location of hole
        self.xw_hole_f10 = 0
        self.yw_hole_f10 = 0
        self.on_sand = False
        # Status of ball relative to hole
        self.in_hole = False
        self.ignore_hole_line = False
        # Done-moving tracking
        self.is_stopped = False
        self.ms_below_stop_threshold = 0
        self.xw_exp_avg_f10 = 0
        self.yw_exp_avg_f10 = 0

    def update_last_shot(self):
        self.xw_last_shot_f10 = self.xw_f10
        self.yw_last_shot_f10 = self.yw_f10

    def move_to_last_shot(self):
        self.xw_f10 = self.xw_last_shot_f10
        self.yw_f10 = self.yw_last_shot_f10
        self._reset_ball()

    @micropython.native
    def set_mask_layer(self, mask_layer):
        self.mask_layer = mask_layer

    @micropython.native
    def _set_on_sand(self, on_sand):
        self.on_sand = on_sand

    @micropython.native
    def _set_water_status(self, water_ms):
        self.water_ms = water_ms
        if water_ms > BALL_MS_BEFORE_SINK:
            self.in_water = True
            self.is_stopped = True

    @micropython.native
    def _reset_is_stopped(self):
        self.is_stopped = False
        self.ms_below_stop_threshold = 0
        # Bias exp avg away from ball to prolong animation
        self.xw_exp_avg_f10 = self.xw_f10 + 4096
        self.yw_exp_avg_f10 = self.yw_f10 + 4096

    @micropython.native
    def _reset_ball(self):
        self.maybe_i_chunk_contact0 = -1
        self.maybe_i_chunk_contact1 = -1
        self.in_hole = False
        self.ignore_hole_line = False
        self.is_stopped = False
        self.ms_below_stop_threshold = 0
        # TODO: bias initial values away from ball pos itself if needed
        self.xw_exp_avg_f10 = self.xw_f10
        self.yw_exp_avg_f10 = self.yw_f10
        self.water_ms = 0
        self.in_water = False
        self.xw_last_shot_f10 = self.xw_f10
        self.yw_last_shot_f10 = self.yw_f10

    @micropython.native
    def _set_location_f10(self, xw_f10, yw_f10):
        self.xw_f10 = xw_f10
        self.yw_f10 = yw_f10

    @micropython.native
    def reset_location_f10(self, xw_f10, yw_f10):
        self._set_location_f10(xw_f10, yw_f10)
        self.on_sand = False
        self._reset_ball()

    @micropython.native
    def _set_hole_status(self, in_hole, ignore_hole_line):
        self.in_hole = in_hole
        self.ignore_hole_line = ignore_hole_line

    @micropython.native
    def set_location_hole_f10(self, xw_hole_f10, yw_hole_f10):
        self.xw_hole_f10 = xw_hole_f10
        self.yw_hole_f10 = yw_hole_f10
        self._set_hole_status(False, False)

    @micropython.native
    def _set_velocity_wd_f20(self, angle_wd, w_per_ms_f20):
        self.v_angle_wd = wd_init(angle_wd)
        self.v_w_per_ms_f20 = w_per_ms_f20

    @micropython.native
    def reset_velocity_wd_f20(self, angle_wd, w_per_ms_f20):
        self._set_velocity_wd_f20(angle_wd, w_per_ms_f20)
        self._reset_ball()

    @micropython.native
    def _set_velocity_vector_f10(self, xw_per_ms_f10, yw_per_ms_f10):
        if xw_per_ms_f10 == 0 and yw_per_ms_f10 == 0:
            # Preserve old orientation and zero out speed
            self._set_velocity_wd_f20(self.v_angle_wd, 0)
            return
        angle_degrees = int(math.atan2(yw_per_ms_f10, xw_per_ms_f10)
            * COEFF_RADIANS_TO_DEGREES + 0.5)
        angle_wd = angle_degrees % 360
        norm_squared_f20 = \
            xw_per_ms_f10 * xw_per_ms_f10 + yw_per_ms_f10 * yw_per_ms_f10
        # TODO: cap speed?
        w_per_ms_f20 = int(math.sqrt(norm_squared_f20)) << 10
        self._set_velocity_wd_f20(angle_wd, w_per_ms_f20)

    @micropython.native
    def _set_maybe_i_chunk_contact(self, maybe_i_chunk_contact0,
                                   maybe_i_chunk_contact1):
        self.maybe_i_chunk_contact0 = maybe_i_chunk_contact0
        self.maybe_i_chunk_contact1 = maybe_i_chunk_contact1

    @micropython.native
    def location_after_delta_ms_f10(self, delta_ms):
        v_angle_wd = self.v_angle_wd
        v_w_per_ms_f10 = (self.v_w_per_ms_f20 + 0x200) >> 10

        delta_w_f10 = v_w_per_ms_f10 * delta_ms

        delta_xw_f10 = (cos_wd_f10(v_angle_wd) * delta_w_f10 + 0x200) >> 10
        delta_yw_f10 = (sin_wd_f10(v_angle_wd) * delta_w_f10 + 0x200) >> 10

        return self.xw_f10 + delta_xw_f10, self.yw_f10 + delta_yw_f10

    # Returns true if this helper has handled the timestep
    @micropython.viper
    def _maybe_advance_to_hole_interaction(self, delta_ms:int) -> bool:
        # Fetch parameters
        xw_f10 = int(self.xw_f10)
        yw_f10 = int(self.yw_f10)
        xw_hole_f10 = int(self.xw_hole_f10)
        yw_hole_f10 = int(self.yw_hole_f10)
        v_angle_wd = int(self.v_angle_wd)
        v_w_per_ms_f20 = int(self.v_w_per_ms_f20)
        in_hole = bool(self.in_hole)
        ignore_hole_line = bool(self.ignore_hole_line)
        # Early out if already in hole
        if in_hole:
            # Animate ball towards hole center -- is-stopped detection will
            # eventually fire and stop this
            a_f10 = int(BALL_COEFF_A) * delta_ms
            xw_f10 = \
                (a_f10 * xw_hole_f10 + (1024 - a_f10) * xw_f10 + 0x200) >> 10
            yw_f10 = \
                (a_f10 * yw_hole_f10 + (1024 - a_f10) * yw_f10 + 0x200) >> 10
            self._set_location_f10(xw_f10, yw_f10)
            return True  # timestep handled

        # Get per-axis distances to hole for case selection below
        abs_delta_xw_to_hole_f10 = xw_hole_f10 - xw_f10
        if abs_delta_xw_to_hole_f10 < 0:
            abs_delta_xw_to_hole_f10 = 0 - abs_delta_xw_to_hole_f10
        abs_delta_yw_to_hole_f10 = yw_hole_f10 - yw_f10
        if abs_delta_yw_to_hole_f10 < 0:
            abs_delta_yw_to_hole_f10 = 0 - abs_delta_yw_to_hole_f10

        # Consider effect of distance of ball *start* to hole
        hole_radius_f10 = int(BALL_HOLE_DIAMETER) << 9
        w_range_f10 = (v_w_per_ms_f20 * delta_ms + 0x200) >> 10
        if abs_delta_xw_to_hole_f10 > hole_radius_f10 or \
           abs_delta_yw_to_hole_f10 > hole_radius_f10:
            # Not starting near hole. Re-enable ball-line intersection logic.
            ignore_hole_line = bool(False)
            self._set_hole_status(in_hole, ignore_hole_line)
            # Exit early if ball can't reach hole in timestep
            if abs_delta_xw_to_hole_f10 - w_range_f10 > hole_radius_f10 or\
               abs_delta_yw_to_hole_f10 - w_range_f10 > hole_radius_f10:
                return False  # timestep not handled
        elif v_w_per_ms_f20 < int(BALL_HOLE_SLOW_F20):
            # Ball is close to hole and moving slowly. Allow it to roll into
            # hole if past the lip.
            dist_w_sq_to_hole_f20 = \
                abs_delta_xw_to_hole_f10 * abs_delta_xw_to_hole_f10 +\
                abs_delta_yw_to_hole_f10 * abs_delta_yw_to_hole_f10
            if dist_w_sq_to_hole_f20 < int(BALL_HOLE_RADIUS_SQ_F20):
                in_hole = bool(True)
                self._set_hole_status(in_hole, ignore_hole_line)
                self._reset_is_stopped()  # allow anim. to hole center to play
                return True  # timestep handled

        # TODO: include test against slow below?
        if ignore_hole_line or v_w_per_ms_f20 < int(BALL_HOLE_SLOW_F20):
            # Continuing to ignore a past "hole line" interaction, or moving
            # slowly enough that the roll-in case above should handle the ball
            # once close enough
            return False  # timestep not handled

        # Ball is moving too fast to roll in unconditionally and is newly close
        # to hole. Inspect intersection with "hole line" and possibly interact
        # with hole accordingly.

        # Calculate signed distance to hole line intersection
        vx_unit_f10 = int(cos_wd_f10(v_angle_wd))
        vy_unit_f10 = int(sin_wd_f10(v_angle_wd))
        dist_signed_w_to_intersect_f10 = \
            ((xw_hole_f10 - xw_f10) * vx_unit_f10 + \
            (yw_hole_f10 - yw_f10) * vy_unit_f10 + 0x200) >> 10
        # Stop if intersection is behind us or too far for timestep
        if dist_signed_w_to_intersect_f10 < 0 or \
           dist_signed_w_to_intersect_f10 > w_range_f10:
            return False  # timestep not handled
        # Get ball position at intersection
        xw_f10 += (dist_signed_w_to_intersect_f10 * vx_unit_f10 + 0x200) >> 10
        yw_f10 += (dist_signed_w_to_intersect_f10 * vy_unit_f10 + 0x200) >> 10
        # Stop if intersection position is too far from hole
        abs_delta_xw_to_hole_f10 = xw_hole_f10 - xw_f10
        if abs_delta_xw_to_hole_f10 < 0:
            abs_delta_xw_to_hole_f10 = 0 - abs_delta_xw_to_hole_f10
        abs_delta_yw_to_hole_f10 = yw_hole_f10 - yw_f10
        if abs_delta_yw_to_hole_f10 < 0:
            abs_delta_yw_to_hole_f10 = 0 - abs_delta_yw_to_hole_f10
        if abs_delta_xw_to_hole_f10 > hole_radius_f10 or \
           abs_delta_yw_to_hole_f10 > hole_radius_f10:
            return False  # timestep not handled
        # Find distance of intersection to hole and stop if it's outside hole
        dist_w_sq_to_hole_f20 = \
            abs_delta_xw_to_hole_f10 * abs_delta_xw_to_hole_f10 + \
            abs_delta_yw_to_hole_f10 * abs_delta_yw_to_hole_f10
        if dist_w_sq_to_hole_f20 > int(BALL_HOLE_RADIUS_SQ_F20):
            return False  # timestep not handled
        # Ball intersects hole line within hole -- helper will own this
        # timestep. Advance ball to intersection and update velocity per grass
        # friction.
        self._set_location_f10(xw_f10, yw_f10)
        self._set_maybe_i_chunk_contact(-1, -1)
        ignore_hole_line = True
        self._set_hole_status(in_hole, ignore_hole_line)
        ms_sand = (dist_signed_w_to_intersect_f10 * delta_ms) // w_range_f10
        v_w_per_ms_f20 -= int(BALL_COEFF_SAND_F20) * ms_sand
        if v_w_per_ms_f20 < 0:
            v_w_per_ms_f20 = int(0)
        self._set_velocity_wd_f20(v_angle_wd, v_w_per_ms_f20)

        # Decide whether ball deflects or enters as a function of distance and
        # speed
        frac_max_entry_speed_f10 = \
            v_w_per_ms_f20 // int(BALL_HOLE_MAX_SPEED_ENTER_F10)
        dist_w_to_hole_f10 = int(sqrt_int(dist_w_sq_to_hole_f20))
        frac_towards_center_f10 = \
            1024 - ((dist_w_to_hole_f10 << 1) // int(BALL_HOLE_DIAMETER))
        # See if ball is close enough to hole center to enter (impossible once
        # past max entry speed)
        if frac_towards_center_f10 > frac_max_entry_speed_f10:
            # Mark ball as entering hole
            in_hole = bool(True)
            self._set_hole_status(in_hole, ignore_hole_line)
            self._reset_is_stopped()  # allow animation to hole center to play
            return True  # timestep handled
        # Ball will skip over hole. Decide how much (if any) to deflect
        frac_deflection_f10 = 1024 - (frac_max_entry_speed_f10 << 1) + \
            frac_towards_center_f10
        if frac_deflection_f10 < 0:
            # No deflection -- too far towards edge of hole
            return True  # timestep handled
        # Find correct sign and apply deflection
        delta_ang_deflect = \
            (frac_deflection_f10 * int(BALL_HOLE_ANG_DEFLECT) + 0x200) >> 10
        dot = vy_unit_f10 * (xw_f10 - xw_hole_f10) - \
              vx_unit_f10 * (yw_f10 - yw_hole_f10)
        if dot > 0:
            v_angle_wd = int(wd_init(v_angle_wd + delta_ang_deflect))
        else:
            v_angle_wd = int(wd_init(v_angle_wd - delta_ang_deflect))
        self._set_velocity_wd_f20(v_angle_wd, v_w_per_ms_f20)
        return True  # timestep handled

    @micropython.viper
    def _advance_to_collision_axis_aligned(self, delta_ms:int,
                                           rasterizer_collision, payload_buffer,
                                           arr_chunk_normal_wd:ptr16):
        mask_layer = int(self.mask_layer)
        xw_f10 = int(self.xw_f10)
        yw_f10 = int(self.yw_f10)
        v_angle_wd = int(self.v_angle_wd)
        v_w_per_ms_f20 = int(self.v_w_per_ms_f20)
        pb = ptr16(payload_buffer.buffer)
        # TODO: restrict delta_ms if too large? In what way, and where?
        # Calculate world distance traveled in delta_ms at current velocity, as
        # f10 for applying step and as int to bound collision detection work
        delta_w_f10 = (v_w_per_ms_f20 * delta_ms + 0x200) >> 10
        delta_w = (delta_w_f10 + 0x200) >> 10
        # Set payload buffer size to receive axis-aligned rasterization
        payload_dim_y = delta_w + 1 + 3 * int(BALL_RADIUS_FLOOR)
        payload_buffer.set_dimensions(int(BALL_DIAMETER), payload_dim_y)
        # Set rasterizer transform to align movement direction to +y in output
        # and center ball in top of payload buffer
        rasterizer_collision.set_scale_f10(1024)
        rasterizer_collision.set_angle_wd(wd_init(90 - v_angle_wd))
        rasterizer_collision.set_translate_map_world_to_screen_f10(
            xw_f10, yw_f10, int(BALL_RADIUS_FLOOR) << 10,
            int(BALL_RADIUS_FLOOR) << 10)
        # Rasterize collision data for ball's current layer(s)
        rasterizer_collision.rasterize_payload(payload_buffer, mask_layer)

        # Track how much of the timestep is spent in contact with different
        # surfaces (for friction/slopes), splitting up the ball's time into
        # delta_w + 1 buckets corresponding to the starting footprint and then
        # each additional row it reaches over delta_ms
        count_grass = int(0)
        count_sand = int(0)
        count_water = int(0)
        touch_grass = bool(False)
        touch_sand = bool(False)
        count_water_row = int(0)
        signed_count_slope_x = int(0)
        signed_count_slope_y = int(0)
        signed_incr_slope_x = int(0)
        signed_incr_slope_y = int(0)
        # Check entire current ball footprint for up to two edges that current
        # velocity would collide with (plus at most one it wouldn't collide
        # with), then advance through towards ball's footprint after delta_ms
        # until first edge the current velocity would collide with, then up to
        # BALL_RADIUS_FLOOR more rows to look for an additional such edge if
        # one is found
        m_i_chunk_scan_noncollide = int(-1)
        m_i_chunk_scan_collide0 = int(-1)
        m_i_chunk_scan_collide1 = int(-1)
        i_row = int(0)
        i_payload_row_start = int(0)
        i_row_end_scan = int(BALL_DIAMETER) + delta_w  # past last to scan
        w_to_step = int(delta_w)  # or less if collision is found
        w_to_step_f10 = delta_w_f10
        # TODO: count water contact and handle water somehow
        while i_row < i_row_end_scan:
            # Check current row
            for i_off in range(int(BALL_DIAMETER)):
                maybe_i_chunk = pb[i_payload_row_start + i_off]
                if maybe_i_chunk & int(MGS_PAYLOAD_BIT_NON_WALL):
                    # Track contact with relevant regions
                    region = maybe_i_chunk & int(MGS_PAYLOAD_MASK_LOW)
                    if region == int(MGS_REGION_FAIRWAY):
                        touch_grass = bool(True)
                    elif region == int(MGS_REGION_WATER):
                        count_water_row += 1
                    elif region == int(MGS_REGION_SANDTRAP):
                        touch_sand = bool(True)
                    elif region == int(MGS_REGION_SLOPE_UP):
                        signed_incr_slope_y = int(-1)
                        touch_grass = bool(True)
                    elif region == int(MGS_REGION_SLOPE_DOWN):
                        signed_incr_slope_y = int(1)
                        touch_grass = bool(True)
                    elif region == int(MGS_REGION_SLOPE_LEFT):
                        signed_incr_slope_x = int(-1)
                        touch_grass = bool(True)
                    elif region == int(MGS_REGION_SLOPE_RIGHT):
                        signed_incr_slope_x = int(1)
                        touch_grass = bool(True)
                    # Update mask_layer if this is a trigger (last wins)
                    mask_trigger = \
                        maybe_i_chunk >> int(MGS_PAYLOAD_SHIFT_MASK_TRIGGER)
                    if mask_trigger:
                        mask_layer = mask_trigger
                    continue  # Done processing non-edge
                # Determine if edge is collision
                normal_wd = arr_chunk_normal_wd[maybe_i_chunk]
                if velocity_hits_normal_wd(v_angle_wd, normal_wd):
                    # Edge is collision. Proceed by cases of what we've seen.
                    if m_i_chunk_scan_collide0 < 0:
                        # First observed collision. Remember it and set w step,
                        # scan end
                        m_i_chunk_scan_collide0 = maybe_i_chunk
                        if i_row <= int(BALL_DIAMETER):
                            # Edge was in or one past ball starting footprint.
                            # Don't advance ball, but check up to rad_floor rows
                            # past ball footprint for edges to consider in
                            # collision response.
                            w_to_step = 0
                            w_to_step_f10 = 0
                            i_row_end_scan = \
                                int(BALL_DIAMETER) + int(BALL_RADIUS_FLOOR)
                        else:
                            # Ball made it past starting footprint without
                            # collision. Advance ball to last non-collision
                            # footprint, and check rad_floor rows past current
                            # for edges.
                            w_to_step = i_row - int(BALL_DIAMETER)
                            w_to_step_f10 = w_to_step << 10
                            i_row_end_scan = i_row + int(BALL_RADIUS_FLOOR) + 1
                    elif maybe_i_chunk != m_i_chunk_scan_collide0 and \
                         m_i_chunk_scan_collide1 < 0:
                        # Second unique observed collision. Remember it.
                        m_i_chunk_scan_collide1 = maybe_i_chunk
                else:
                    # Remember non-collision contacted edge if didn't have one
                    if m_i_chunk_scan_noncollide < 0:
                        m_i_chunk_scan_noncollide = maybe_i_chunk
            # Update region contact counts, treating entire starting footprint
            # as one bucket and then individual successive rows
            if i_row >= int(BALL_DIAMETER) - 1 and \
               (i_row - int(BALL_DIAMETER)) < w_to_step:
                # Ball's ending footprint will include or be past this row.
                # Update region counts
                if touch_grass:
                    count_grass += 1
                    touch_grass = bool(False)
                if touch_sand:
                    count_sand += 1
                    touch_sand = bool(False)
                if count_water_row > int(BALL_RADIUS_FLOOR):
                    count_water += 1
                count_water_row = 0
                signed_count_slope_x += signed_incr_slope_x
                signed_count_slope_y += signed_incr_slope_y
                signed_incr_slope_x = int(0)
                signed_incr_slope_y = int(0)
            # Advance to next row
            i_row += 1
            i_payload_row_start += int(BALL_DIAMETER)

        # Select up to two edges to say the ball collided with, favoring edges
        # opposing the current velocity
        # TODO: if w step is 0, consider retaining edges from previous physics
        # step if there's room?
        maybe_i_chunk_contact0 = m_i_chunk_scan_collide0
        maybe_i_chunk_contact1 = m_i_chunk_scan_collide1
        if maybe_i_chunk_contact0 >= 0 and maybe_i_chunk_contact1 < 0:
            # May still be -1
            maybe_i_chunk_contact1 = m_i_chunk_scan_noncollide
        # Advance ball's position to delta_ms or first collision and indicate
        # the edges collided with, if any
        self._set_maybe_i_chunk_contact(maybe_i_chunk_contact0,
                                        maybe_i_chunk_contact1)
        if w_to_step_f10 > 0:
            xw_f10 += \
                (int(cos_wd_f10(v_angle_wd)) * w_to_step_f10 + 0x200) >> 10
            yw_f10 += \
                (int(sin_wd_f10(v_angle_wd)) * w_to_step_f10 + 0x200) >> 10
            self._set_location_f10(xw_f10, yw_f10)
        # Translate per-region counts into approximate number of ms in contact
        # with each region, and update velocity per friction
        denom = delta_w + 1
        ms_grass = (delta_ms * count_grass) // denom
        ms_sand = (delta_ms * count_sand) // denom
        v_w_per_ms_f20 -= int(BALL_COEFF_GRASS_F20) * ms_grass
        v_w_per_ms_f20 -= int(BALL_COEFF_SAND_F20) * ms_sand
        if v_w_per_ms_f20 < 0:
            v_w_per_ms_f20 = int(0)
        self._set_velocity_wd_f20(v_angle_wd, v_w_per_ms_f20)
        # After friction, apply effect of any slope contact to velocity
        self.set_mask_layer(mask_layer)
        if signed_count_slope_x != 0 or signed_count_slope_y != 0:
            # Convert angle and updated velocity to vector
            w_per_ms_f10 = (v_w_per_ms_f20 + 0x200) >> 10
            xw_per_ms_f10 = \
                (int(cos_wd_f10(v_angle_wd)) * w_per_ms_f10 + 0x200) >> 10
            yw_per_ms_f10 = \
                (int(sin_wd_f10(v_angle_wd)) * w_per_ms_f10 + 0x200) >> 10
            # Add effect of slopes to vector
            signed_ms_slope_x = (delta_ms * signed_count_slope_x) // denom
            signed_ms_slope_y = (delta_ms * signed_count_slope_y) // denom
            xw_per_ms_f10 += \
                (signed_ms_slope_x * int(BALL_COEFF_SLOPE_F20) + 0x200) >> 10
            yw_per_ms_f10 += \
                (signed_ms_slope_y * int(BALL_COEFF_SLOPE_F20) + 0x200) >> 10
            # Translate vector back to (angle, speed) for ball
            self._set_velocity_vector_f10(xw_per_ms_f10, yw_per_ms_f10)
        # B&W sand hack
        self._set_on_sand(count_sand > 0)
        # Handle water interaction. Ball *position* won't make perfect sense,
        # but meh. Helper handles in_water, is_stopped.
        if count_water == denom:
            # Ball was in water for entire frame -- add to existing ms
            self._set_water_status(int(self.water_ms) + delta_ms)
        else:
            # Ball was in water for part of frame -- reset tracking
            water_ms = (delta_ms * count_water) // denom
            self._set_water_status(water_ms)

    @micropython.viper
    def _maybe_resolve_collision(self, arr_chunk_normal_wd:ptr16):
        # Find which of the up to two specified contact edges count as
        # collisions given the current ball velocity angle
        v_angle_wd = int(self.v_angle_wd)
        v_w_per_ms_f20 = int(self.v_w_per_ms_f20)
        maybe_i_chunk_contact0 = int(self.maybe_i_chunk_contact0)
        maybe_i_chunk_contact1 = int(self.maybe_i_chunk_contact1)
        normal0_wd = int(0)
        normal1_wd = int(0)
        is_collision0 = bool(False)
        is_collision1 = bool(False)
        if maybe_i_chunk_contact0 >= 0:
            normal0_wd = arr_chunk_normal_wd[maybe_i_chunk_contact0]
            is_collision0 = bool(
                velocity_hits_normal_wd(v_angle_wd, normal0_wd))
        if maybe_i_chunk_contact1 >= 0:
            normal1_wd = arr_chunk_normal_wd[maybe_i_chunk_contact1]
            is_collision1 = bool(
                velocity_hits_normal_wd(v_angle_wd, normal1_wd))
        # Reduce speed for any collision
        if is_collision0 or is_collision1:
            v_w_per_ms_f20 -= int(BALL_SUBTR_WALL_F20)
            if v_w_per_ms_f20 < 0:
                v_w_per_ms_f20 = 0
        # Proceed by cases for reflection
        if is_collision0 and is_collision1:
            # Reflect about endpoint normal of the two edges
            v_angle_wd = int(reflect_velocity_about_normal_wd(
                v_angle_wd, get_endpoint_normal_wd(normal0_wd, normal1_wd)))
            self._set_velocity_wd_f20(v_angle_wd, v_w_per_ms_f20)
        elif is_collision0:
            # Reflect about 0's normal
            v_angle_wd = int(reflect_velocity_about_normal_wd(
                v_angle_wd, normal0_wd))
            self._set_velocity_wd_f20(v_angle_wd, v_w_per_ms_f20)
        elif is_collision1:
            # Reflect about 1's normal
            v_angle_wd = int(reflect_velocity_about_normal_wd(
                v_angle_wd, normal1_wd))
            self._set_velocity_wd_f20(v_angle_wd, v_w_per_ms_f20)
        # Else, nothing to do

    @micropython.native
    def _update_stopped_tracking(self, delta_ms):
        xw_f10 = self.xw_f10
        yw_f10 = self.yw_f10
        xw_exp_avg_f10 = self.xw_exp_avg_f10
        yw_exp_avg_f10 = self.yw_exp_avg_f10
        ms_below_stop_threshold = self.ms_below_stop_threshold
        # Update exp avg of ball position, weighted by timestep duration
        # exp_avg = a * x + (1.0 - a) * exp_avg
        # a = ms_per_frame / 1000
        a_f10 = int(BALL_COEFF_A) * delta_ms
        xw_exp_avg_f10 = \
            (a_f10 * xw_f10 + (1024 - a_f10) * xw_exp_avg_f10 + 0x200) >> 10
        yw_exp_avg_f10 = \
            (a_f10 * yw_f10 + (1024 - a_f10) * yw_exp_avg_f10 + 0x200) >> 10
        # Test if avg is far from ball position
        abs_diff_xw_f10 = xw_f10 - xw_exp_avg_f10
        if abs_diff_xw_f10 < 0:
            abs_diff_xw_f10 = -abs_diff_xw_f10
        abs_diff_yw_f10 = yw_f10 - yw_exp_avg_f10
        if abs_diff_yw_f10 < 0:
            abs_diff_yw_f10 = -abs_diff_yw_f10
        if abs_diff_xw_f10 < int(BALL_DELTA_W_STOPPED_F10) and \
           abs_diff_yw_f10 < int(BALL_DELTA_W_STOPPED_F10):
            # Ball is near avg. Increment ms and mark stopped after long enough.
            ms_below_stop_threshold += delta_ms
            if ms_below_stop_threshold > int(BALL_MS_BEFORE_STOPPED):
                self.is_stopped = True
        else:
            # Reset time since near avg
            ms_below_stop_threshold = 0
        # Flush out updates
        self.xw_exp_avg_f10 = xw_exp_avg_f10
        self.yw_exp_avg_f10 = yw_exp_avg_f10
        self.ms_below_stop_threshold = ms_below_stop_threshold

    # Advances the ball by a timestep of delta_ms per the level geometry.
    # Resolves up to one collision, leaving the ball in the state it should have
    # immediately after bouncing.
    @micropython.native
    def advance(self, delta_ms, rasterizer_collision, payload_buffer,
                arr_chunk_normal_wd):
        # Do nothing if stopped
        if self.is_stopped:
            return
        # Try handling timestep as hole interaction if close to it
        handled_by_hole = self._maybe_advance_to_hole_interaction(delta_ms)
        if not handled_by_hole:
            # No hole interaction. Handle timestep according to rasterized
            # scene and resolve any resulting collision
            self._advance_to_collision_axis_aligned(
                delta_ms, rasterizer_collision, payload_buffer,
                arr_chunk_normal_wd)
            self._maybe_resolve_collision(arr_chunk_normal_wd)
        # Update tracking of stopped-ness and maybe mark stopped
        self._update_stopped_tracking(delta_ms)

    # Draws the ball to the display using the *transform* of the rasterizer
    @micropython.native
    def draw_ball(self, display, transformed_rasterizer, color,
                  debug_offset_x=0, debug_offset_y=0):
        xs_f10, ys_f10 = transformed_rasterizer.world_to_screen_f10(
            self.xw_f10, self.yw_f10)
        color_line = 1
        color_fill = 0 if not utils.use_gray and self.on_sand else 1
        draw_circle_line_fill(display, xs_f10, ys_f10,
                              transformed_rasterizer.scale_f10 * BALL_DIAMETER,
                              color_line, color_fill)

    @micropython.native
    def draw_hole(self, display, transformed_rasterizer, color,
                  debug_offset_x=0, debug_offset_y=0):
        xs_f10, ys_f10 = transformed_rasterizer.world_to_screen_f10(
            self.xw_hole_f10, self.yw_hole_f10)
        color_line = 0 if utils.use_gray else 1
        color_fill = 0
        draw_circle_line_fill(
            display, xs_f10, ys_f10,
            transformed_rasterizer.scale_f10 * BALL_HOLE_DIAMETER, color_line,
            color_fill)

    # Draws a line from the ball's location to its location delta_ms in the
    # future per velocity using the *transform* of the rasterizer
    @micropython.native
    def draw_velocity(self, display, delta_ms, transformed_rasterizer, color,
                      debug_offset_x=0, debug_offset_y=0):
        xw_f10 = self.xw_f10
        yw_f10 = self.yw_f10
        xs_f10, ys_f10 = transformed_rasterizer.world_to_screen_f10(
            xw_f10, yw_f10)
        xs_b = ((xs_f10 + 0x200) >> 10) + debug_offset_x
        ys_b = ((ys_f10 + 0x200) >> 10) + debug_offset_y

        xw_f10, yw_f10 = self.location_after_delta_ms_f10(delta_ms)
        xs_f10, ys_f10 = transformed_rasterizer.world_to_screen_f10(
            xw_f10, yw_f10)
        xs_e = ((xs_f10 + 0x200) >> 10) + debug_offset_x
        ys_e = ((ys_f10 + 0x200) >> 10) + debug_offset_y

        display.drawLine(xs_b, ys_b, xs_e, ys_e, color)

    # Visualizes the ball exp avg for is-stopped tracking
    # TODO: remove?
    @micropython.native
    def draw_exp_avg(self, display, transformed_rasterizer, debug_offset_x=0,
                     debug_offset_y=0):
        xs_f10, ys_f10 = transformed_rasterizer.world_to_screen_f10(
            self.xw_exp_avg_f10, self.yw_exp_avg_f10)
        xs = ((xs_f10 + 0x200) >> 10) + debug_offset_x
        ys = ((ys_f10 + 0x200) >> 10) + debug_offset_y
        display.drawRectangle(xs - 1, ys - 1, 3, 3, 1)
        display.setPixel(xs, ys, 0)
