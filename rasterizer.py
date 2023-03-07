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
import utils

# Low-level rasterization helpers

# Fills height range [y0, y1] of column x with a vertical tiling of the 8-pixel
# pattern defined by fill_mask. Assumes all pixels in the range are currently 0.
#
# NO BOUNDS CHECKING.
@micropython.viper
def fill_or_column_mask_unchecked(
    buf0:ptr8, buf1:ptr8, x:int, y0:int, y1:int, width:int, fill_mask0:int,
    fill_mask1:int):
    # Find y bytes containing the two endpoints, and endpoints mod 8
    yb0 = y0 >> 3
    yb1 = y1 >> 3
    ym0 = y0 & 7
    ym1 = y1 & 7
    i = x + width * yb0
    if yb0 == yb1:
        # Fill falls within one byte. Form mask and apply update.
        mask = (((1 << (ym1 - ym0 + 1)) - 1) << ym0)
        buf0[i] |= mask & fill_mask0
        buf1[i] |= mask & fill_mask1
    else:
        # Fill spans at least two bytes. Handle first endpoint byte, then any
        # fully covered middle bytes, then the final byte.

        # First byte
        mask = ((0xff >> ym0) << ym0)
        buf0[i] |= mask & fill_mask0
        buf1[i] |= mask & fill_mask1
        # Middle bytes
        i_last = x + width * yb1
        i += width
        while i < i_last:
            buf0[i] = fill_mask0
            buf1[i] = fill_mask1
            i += width
        # Final byte
        mask = ((2 << ym1) - 1)
        buf0[i] |= mask & fill_mask0
        buf1[i] |= mask & fill_mask1

# Working state for rasterized lines (rl). All 16-bit packed ints are non-neg.

# TODO: operate on packed s and p in-place in more logic
# TODO: try operating on rl in most logic as ptr16, and only use sp as 32-bit in
# sort?
I_RL_SP = const(0)  # high 16: s; low 16: p
I_RL_SP_B = const(1)  # high 16: s_b; low 16: p_b
I_RL_SP_E = const(2)  # high 16: s_e; low 16: p_e
I_RL_A = const(3)
I_RL_FLAGS = const(4)
I_RL_A_S_A_P = const(5)  # high 16: a_s; low 16: a_p
I_RL_REGION_0_1 = const(6)  # high 16: r0; low 16: r1
I_RL_PAYLOAD_0_1 = const(7)  # high 16: p0; low 16: p1
I_RL_NUM_FIELDS = const(8)  # bits below

RL_FLAG_BIT_SCANLINE_HAS_ENDPOINT = const(0x1)
RL_FLAG_BIT_DELTA_P_IS_POSITIVE = const(0x2)
RL_FLAG_BIT_IS_PAST_EXIT = const(0x4)
RL_FLAG_BIT_A_M_IS_A_P = const(0x8)
RL_FLAG_BIT_CORRECT_ENDPOINTS = const(0x10)
RL_FLAG_SHIFT_MASK_LAYER = const(5)  # TODO: keep in sync w/ num bits above
RL_FLAG_ALL_BITS = const(0x1ff)

RL_NUM_BYTES = const(I_RL_NUM_FIELDS << 2)

# Bias to add to screen-space x or y values to turn them into s and p values
# that can be assumed to be positive and that don't hit the 16-bit sign bit
RL_SP_BIAS = const(0x4000)
# 16-bit sentinel value for p_e to indicate that the p at s=s_e should *not*
# be replaced with the provided p_e
RL_P_E_DONT_CORRECT = const(0x00007fff)
# Can use ints [0, RL_NUM_REGION) as used regions; lower-valued regions draw
# over higher-numbered ones
RL_NUM_REGIONS = const(8)
# Sentinel value that must be set for "unused" regions
# TODO: CRITICAL: keep synced with MGS_REGION_EMPTY
RL_REGION_UNUSED = const(RL_NUM_REGIONS)

# Returns the number of times p should be stepped given an a that may reflect
# having advanced the scanline some number of times
# @micropython.viper
# def calculate_rl_num_steps_p(a:int, a_m:int, a_p:int) -> int:
#     if a < a_m:
#         return 0
#     return ((a - a_m) // a_p) + 1

# Initializes the rasterized line starting at base to describe in each scanline
# the first pixel filled by the Bresenham line from (p_b, s_b) to (p_e, s_e)
# (CRITICAL: s_e >= s_b), or the pixel past the last pixel filled by the
# Bresenham line if is_past_exit. The region arguments describe the up to two
# regions for which this line describes entry or exit of the region (per
# is_past_exit); the payload data allows mapping the rl back to who created it.
#
# After return, the rl reflects the line's state in scanline s_b.
@micropython.viper
def rl_init(base:ptr32, s_b:int, p_b:int, s_e:int, p_e:int, region0:int,
            region1:int, payload0:int, payload1:int, mask_layer:int,
            is_past_exit:bool):
    # Calculate working values and determine slope case
    d_s = s_e - s_b  # better be >= 0
    d_p = p_e - p_b  # will become >= 0
    delta_p_is_positive = bool(True)
    if d_p < 0:
        delta_p_is_positive = bool(False)
        d_p = 0 - d_p  # viper doesn't like unary "-"
    is_steep = bool(d_p > d_s)
    # Prepare output values beyond fn arguments
    p = int(0)
    a = int(0)
    a_s = int(0)
    a_p = int(0)
    a_m_is_a_p = bool(True)
    correct_endpoints = bool(False)
    # Calculate output values by cases
    if d_s == 0:
        # Line is parallel to scanline (including being just a point). Set the p
        # we want in that scanline, and nothing else; this rl will be discarded
        # by increment/set helpers before its other fields can matter.
        if is_past_exit:
            if p_e > p_b:
                p = p_e
            else:
                p = p_b
            p += 1
        else:
            if p_e < p_b:
                p = p_e
            else:
                p = p_b
    elif is_steep:
        # Line can increment p multiple times per s. Some values need to be
        # fiddled with depending on delta_p sign and whether doing past-exit.
        p = p_b
        if not delta_p_is_positive:
            p += 1
        a = d_p
        a_s = 2 * d_p
        a_p = 2 * d_s
        a_m = a_s  # used locally below
        a_m_is_a_p = bool(False)
        # Viper doesn't like bool == bool, because [profanity redacted]
        if (delta_p_is_positive and is_past_exit) or \
           (not delta_p_is_positive and not is_past_exit):
            # Do the aforementioned fiddling and remember it's needed
            correct_endpoints = bool(True)
            # Below specializes a = (a + a_s - n_p(a + a_s) * a_p) from notes
            # given that requiring correction implies:
            # - a_m = a_s, so a + a_s = 3 * a_m / 2 > a_m
            num_steps_p = (a // a_p) + 1
            a += a_s - num_steps_p * a_p
            if delta_p_is_positive:
                p += num_steps_p
                p_e += 1
            else:
                p -= num_steps_p
            # p_e correction required -- to its true value or one past it
            # (handled above)
        else:
            # p_e correction not required in this case
            p_e = int(RL_P_E_DONT_CORRECT)
    else:
        # Line is shallow or horizontal in p as s increases. Other than delta_p
        # itself, required values are unaffected by delta_p sign.
        if is_past_exit:
            p = p_b + 1
        else:
            p = p_b
        a = d_s
        a_s = 2 * d_p
        a_p = 2 * d_s
        a_m_is_a_p = bool(True)
        # p_e correction never required for shallow
        p_e = int(RL_P_E_DONT_CORRECT)
    # Pack flags
    flags = int(RL_FLAG_BIT_SCANLINE_HAS_ENDPOINT)  # always true upon init
    if delta_p_is_positive:
        flags |= int(RL_FLAG_BIT_DELTA_P_IS_POSITIVE)
    if is_past_exit:
        flags |= int(RL_FLAG_BIT_IS_PAST_EXIT)
    if a_m_is_a_p:
        flags |= int(RL_FLAG_BIT_A_M_IS_A_P)
    if correct_endpoints:
        flags |= int(RL_FLAG_BIT_CORRECT_ENDPOINTS)
    flags |= mask_layer << int(RL_FLAG_SHIFT_MASK_LAYER)
    # Write calculated values to rl
    sp = (s_b << 16) | p
    base[int(I_RL_SP)] = sp
    base[int(I_RL_SP_B)] = sp
    base[int(I_RL_SP_E)] = (s_e << 16) | p_e
    base[int(I_RL_A)] = a
    base[int(I_RL_FLAGS)] = flags
    base[int(I_RL_A_S_A_P)] = (a_s << 16) | a_p
    base[int(I_RL_REGION_0_1)] = (region0 << 16) | region1
    base[int(I_RL_PAYLOAD_0_1)] = (payload0 << 16) | payload1

# Updates all of rl's state to reflect being at:
# - s_after, if s_after is in [s_b, s_e]
# - s_b, if s_after is less than s_b
# - *any* s in [s_b, s_e] otherwise (s_after is greater than s_e)
@micropython.viper
def rl_seek_s_to(rl:ptr32, s_after:int):
    s_e = rl[int(I_RL_SP_E)] >> 16
    # Do nothing if trying to seek past scanline s_e
    if s_after > s_e:
        return
    # Don't seek to before s_b
    s_b = rl[int(I_RL_SP_B)] >> 16
    if s_after < s_b:
        s_after = s_b
    # Fetch some parameters of rl
    a_s = rl[int(I_RL_A_S_A_P)] >> 16
    a_p = rl[int(I_RL_A_S_A_P)] & 0xffff
    a_m = a_s
    if bool(rl[int(I_RL_FLAGS)] & int(RL_FLAG_BIT_A_M_IS_A_P)):
        a_m = a_p
    # Reset rl to state it had after rl_init if seeking backwards
    if s_after < (rl[int(I_RL_SP)] >> 16):
        rl[int(I_RL_SP)] = rl[int(I_RL_SP_B)]
        rl[int(I_RL_FLAGS)] |= int(RL_FLAG_BIT_SCANLINE_HAS_ENDPOINT)
        # Calculate and correct if needed the initial a. (The corresponding
        # correction to initial p is baked into sp_b.)
        rl[int(I_RL_A)] = a_m >> 1
        if bool(rl[int(I_RL_FLAGS)] & int(RL_FLAG_BIT_CORRECT_ENDPOINTS)):
            # Below specializes a = (a + a_s - n_p(a + a_s) * a_p) from notes
            # given that requiring correction implies:
            # - a_m = a_s, so a + a_s = 3 * a_m / 2 > a_m
            # TODO: just stash initial a in rl to make reset even cheaper?
            n_p = (rl[int(I_RL_A)] // a_p) + 1
            rl[int(I_RL_A)] += a_s - n_p * a_p
    # Now rl is consistent for some s <= s_after <= s_e. Advance rl if needed.
    s_before = rl[int(I_RL_SP)] >> 16
    if s_after > s_before:
        # Find required number of steps in s and update a, s
        num_steps_s = s_after - s_before
        rl[int(I_RL_A)] += num_steps_s * a_s
        rl[int(I_RL_SP)] += num_steps_s << 16
        # Find required number of steps in p and update a, p if non-zero
        if rl[int(I_RL_A)] >= a_m:
            num_steps_p = ((rl[int(I_RL_A)] - a_m) // a_p) + 1
            rl[int(I_RL_A)] -= num_steps_p * a_p
            if bool(rl[int(I_RL_FLAGS)] & int(RL_FLAG_BIT_DELTA_P_IS_POSITIVE)):
                rl[int(I_RL_SP)] += num_steps_p
            else:
                rl[int(I_RL_SP)] -= num_steps_p
        # Apply updates dependent on being at s_e or not. By conditions above,
        # definitely not at s_b.
        if s_after == s_e:
            # Mark at-endpoint bit
            rl[int(I_RL_FLAGS)] |= int(RL_FLAG_BIT_SCANLINE_HAS_ENDPOINT)
            # Apply sp correction if needed
            # TODO: always calculate desired p_e in init so I can do this
            # unconditionally?
            if bool(rl[int(I_RL_FLAGS)] & int(RL_FLAG_BIT_CORRECT_ENDPOINTS)):
                rl[int(I_RL_SP)] = rl[int(I_RL_SP_E)]
        else:
            # Clear at-endpoint bit
            rl[int(I_RL_FLAGS)] &= \
                (int(RL_FLAG_ALL_BITS) ^ int(RL_FLAG_BIT_SCANLINE_HAS_ENDPOINT))

# Updates rl's state to reflect being one past its prior s, or leaves it
# unchanged if rl is already at its s_e
@micropython.viper
def rl_increment_s(rl:ptr32):
    # Stop if already at end
    if (rl[int(I_RL_SP)] ^ rl[int(I_RL_SP_E)]) < 0x10000:  # s == s_e
        return
    # Get parameters for updating a
    a_s = rl[int(I_RL_A_S_A_P)] >> 16
    a_p = rl[int(I_RL_A_S_A_P)] & 0xffff
    a_m = a_s
    if bool(rl[int(I_RL_FLAGS)] & int(RL_FLAG_BIT_A_M_IS_A_P)):
        a_m = a_p
    # Update a, s to reflect stepping by one in s
    rl[int(I_RL_A)] += a_s
    rl[int(I_RL_SP)] += 0x10000
    # Find required number of steps in p and update a, p if non-zero
    if rl[int(I_RL_A)] >= a_m:
        num_steps_p = ((rl[int(I_RL_A)] - a_m) // a_p) + 1
        rl[int(I_RL_A)] -= num_steps_p * a_p
        if bool(rl[int(I_RL_FLAGS)] & int(RL_FLAG_BIT_DELTA_P_IS_POSITIVE)):
            rl[int(I_RL_SP)] += num_steps_p
        else:
            rl[int(I_RL_SP)] -= num_steps_p
    # Apply updates dependent on being at s_e or not. Having stepped, we're
    # definitely not at s_b.
    if (rl[int(I_RL_SP)] ^ rl[int(I_RL_SP_E)]) < 0x10000:  # s == s_e
        # Mark at-endpoint bit
        rl[int(I_RL_FLAGS)] |= int(RL_FLAG_BIT_SCANLINE_HAS_ENDPOINT)
        # Apply sp correction if needed
        # TODO: always calculate desired p_e in init so I can do this
        # unconditionally?
        if bool(rl[int(I_RL_FLAGS)] & int(RL_FLAG_BIT_CORRECT_ENDPOINTS)):
            rl[int(I_RL_SP)] = rl[int(I_RL_SP_E)]
    else:
        # Clear at-endpoint bit
        rl[int(I_RL_FLAGS)] &= \
            (int(RL_FLAG_ALL_BITS) ^ int(RL_FLAG_BIT_SCANLINE_HAS_ENDPOINT))

# "Payload buffer" -- a framebuffer to rasterize integer values to per pixel

PB_MAX_PIXELS = const(1024)

class PayloadBuffer:
    def __init__(self):
        # Row-major; first element is top-left (like display buffer, but now a
        # full int16 per pixel)
        # TODO: see if this tolerates non-zeroed contents
        self.buffer = array('h', range(PB_MAX_PIXELS))
        for i in range(len(self.buffer)):
            self.buffer[i] = 0
        self.width = 1
        self.height = 1

    @micropython.native
    def set_dimensions(self, width, height):
        if width * height > PB_MAX_PIXELS:
            raise RuntimeError(
                f"setting too-large payload buffer {width}, {height}")
        self.width = width
        self.height = height

    # Fills the current-dimensions buffer with payload
    @micropython.viper
    def fill(self, payload:int):
        buf = ptr16(self.buffer)
        size = int(self.width) * int(self.height)
        for i in range(size):
            buf[i] = payload

    # Sets all pixels for which payload is in [payload_min, payload_max] to
    # color, aligning the payload buffer with (0, 0) of the display. Not fast.
    # @micropython.native
    # def debug_draw_payload_in_range(self, payload_min, payload_max, color,
    #                                 debug_offset_x=0, debug_offset_y=0):
    #     width = self.width
    #     height = self.height
    #     buffer = self.buffer
    #     i = 0
    #     for y in range(height):
    #         for x in range(width):
    #             payload = buffer[i]
    #             i += 1
    #             if payload >= payload_min and payload <= payload_max:
    #                 thumby.display.setPixel(
    #                     x + debug_offset_x, y + debug_offset_y, color)

# Scanline rasterizer

SR_MAX_NUM_RL = const(512)  # max number of rl in a ScanlineRasterizer

# The type of buffer to rasterize to
SR_BUFFER_TYPE_DISPLAY = const(0)
SR_BUFFER_TYPE_PAYLOAD = const(1)

class ScanlineRasterizer:
    def __init__(self, arr_region_fill0, arr_region_fill1):
        self.num_rl = 0
        # Allocate space for max number of rl, sharded b/c of fragmentation
        SHARD_NUM_FIELDS = const(256)
        RL_PER_SHARD = const(SHARD_NUM_FIELDS // I_RL_NUM_FIELDS)
        NUM_SHARDS = const((SR_MAX_NUM_RL + RL_PER_SHARD - 1) // RL_PER_SHARD)
        self.shards = [array('l', range(SHARD_NUM_FIELDS)) \
                       for i in range(NUM_SHARDS)]
        # Get pointers to starts of rl, to be sorted by increasing (s, p)
        self.arr_ptr_rl_sorted = array('P', range(SR_MAX_NUM_RL))
        self._fill_ptrs()

        # Can use RL_REGION_UNUSED sentinel as index
        self.arr_region_insideness = array('l', [0] * (RL_NUM_REGIONS + 1))
        self.arr_region_payload = array('l', [0] * (RL_NUM_REGIONS + 1))
        self.arr_region_fill0 = arr_region_fill0
        self.arr_region_fill1 = arr_region_fill1

    @micropython.viper
    def _fill_ptrs(self):
        arr_ptr_rl_sorted = ptr32(self.arr_ptr_rl_sorted)
        i_shard_next = int(0)
        i_rl_shard = int(RL_PER_SHARD)
        ptr_rl = int(0)
        for i_rl in range(int(SR_MAX_NUM_RL)):
            if i_rl_shard >= int(RL_PER_SHARD):
                i_rl_shard = int(0)
                ptr_rl = int(ptr(self.shards[i_shard_next]))
                i_shard_next += int(1)
            arr_ptr_rl_sorted[i_rl] = ptr_rl
            ptr_rl += int(RL_NUM_BYTES)
            i_rl_shard += int(1)

    # Clears all edges from the rasterizer
    @micropython.native
    def clear_edges(self):
        self.num_rl = 0

    # If I try to assign to self.num_rl from a Viper method, nothing happens.
    # How nice.
    @micropython.native
    def set_num_rl(self, num_rl):
        self.num_rl = num_rl

    # Updates state to reflect having one more rl, and returns the pointer to
    # the start of it
    # TODO: inline helper
    @micropython.viper
    def _allocate_rl(self) -> ptr:
        # Protect against overflow
        num_rl = int(self.num_rl)
        if num_rl == int(SR_MAX_NUM_RL):
            # Out of room -- stomp over last rl
            print("allocating too many rl")
            num_rl -= 1
        # Indicate added rl and return pointer
        self.set_num_rl(num_rl + 1)
        return ptr(self.arr_ptr_rl_sorted[num_rl])

    # Sorts self.arr_ptr_rl_sorted[i_begin:i_end] by the (s,p) of the pointed-to
    # rl values using insertion sort
    @micropython.viper
    def _sort_range_ptr_rl_insertion(self, i_begin:int, i_end:int):
        if i_begin >= i_end:
            return
        arr_ptr_rl_sorted = ptr32(self.arr_ptr_rl_sorted)
        sp_sorted_max = ptr32(arr_ptr_rl_sorted[i_begin])[int(I_RL_SP)]
        i_to_insert = i_begin + 1
        while i_to_insert < i_end:
            sp_to_insert = \
                ptr32(arr_ptr_rl_sorted[i_to_insert])[int(I_RL_SP)]
            if sp_to_insert < sp_sorted_max:
                # Need to swap to-insert into sorted prefix. Perform first swap
                # we know must happen and retain unchanged max sp of prefix.
                i_dest = i_to_insert - 1
                swap = arr_ptr_rl_sorted[i_dest]
                arr_ptr_rl_sorted[i_dest] = arr_ptr_rl_sorted[i_to_insert]
                arr_ptr_rl_sorted[i_to_insert] = swap
                # Continue sorting to-insert
                while i_dest > i_begin:
                    i_prev = i_dest - 1
                    sp_prev = ptr32(arr_ptr_rl_sorted[i_prev])[int(I_RL_SP)]
                    if sp_to_insert < sp_prev:
                        swap = arr_ptr_rl_sorted[i_prev]
                        arr_ptr_rl_sorted[i_prev] = arr_ptr_rl_sorted[i_dest]
                        arr_ptr_rl_sorted[i_dest] = swap
                        i_dest -= 1
                    else:
                        # To-insert is in the correct spot
                        break
            else:
                # To-insert should be new end of sorted prefix. Remember its sp
                # as new max and keep going.
                sp_sorted_max = sp_to_insert
            i_to_insert += 1

    # Sets the eight bytes defining the 8x8 tile to repeat in the specified
    # region
    @micropython.viper
    def set_region_fill_bytes(self, i_region:int, buf0:ptr8, buf1:ptr8):
        dest0 = ptr8(uint(ptr(self.arr_region_fill0)) + 8 * i_region)
        dest1 = ptr8(uint(ptr(self.arr_region_fill1)) + 8 * i_region)
        for i in range(8):
            dest0[i] = buf0[i]
            dest1[i] = buf1[i]

    # Adds a line from (x_b, y_b) to (x_e, y_e) to be rasterized. If region_line
    # is not RL_REGION_UNUSED, the pixels of the line will be rasterized as
    # belonging to that region. If region_fill is not RL_REGION_UNUSED, the
    # pixels of the line and the polygon it helps bound will be rasterized as
    # belonging to that region. (The highest-numbered region at a pixel wins.)
    #
    # If lines make up a filled polygon, the lines should be CCW wound in (+x
    # is right, +y is down) space and should all use the same region_fill, but
    # not all lines need to specify a region_line. Individual lines not part of
    # a polygon can be rasterized with just region_line.
    @micropython.viper
    def add_edge_line_fill(self, x_b:int, y_b:int, x_e:int, y_e:int,
                           region_line:int, region_fill:int, payload_line:int,
                           payload_fill:int, mask_layer:int):
        # TODO: map x,y to s,p differently if doing horizontal scanlines
        s_b = x_b + int(RL_SP_BIAS)
        p_b = y_b + int(RL_SP_BIAS)
        s_e = x_e + int(RL_SP_BIAS)
        p_e = y_e + int(RL_SP_BIAS)

        region_unused = int(RL_REGION_UNUSED)
        has_line = bool(region_line != region_unused)

        # Get line orientation and normalize endpoint order for rl_init
        is_single_scanline = bool(s_e == s_b)
        winding_is_past_exit = bool(s_e > s_b)
        if not winding_is_past_exit:
            swap = s_b
            s_b = s_e
            s_e = swap
            swap = p_b
            p_b = p_e
            p_e = swap

        # Add enter rl if line and/or fill need it, setting regions that need it
        need_enter = has_line
        region_fill_enter = region_unused
        if is_single_scanline or not winding_is_past_exit:
            need_enter = True
            region_fill_enter = region_fill
        if need_enter:
            rl_enter = ptr32(self._allocate_rl())
            rl_init(rl_enter, s_b, p_b, s_e, p_e, region_line,
                    region_fill_enter, payload_line, payload_fill, mask_layer,
                    False)

        # Add past-exit rl likewise if needed
        need_past_exit = has_line
        region_fill_past_exit = region_unused
        if is_single_scanline or winding_is_past_exit:
            need_past_exit = True
            region_fill_past_exit = region_fill
        if need_past_exit:
            rl_past_exit = ptr32(self._allocate_rl())
            rl_init(rl_past_exit, s_b, p_b, s_e, p_e, region_line,
                    region_fill_past_exit, payload_line, payload_fill,
                    mask_layer, True)

    # Fills buffer, an array of type specified by buffer_type and dimensions
    # (x_dim, y_dim), to rasterize the lines, mapping (x_first, y_first) in the
    # space of the vertices provided to the rasterizer to (0, 0) of the buffer.
    @micropython.viper
    def rasterize_to_buffer(self, buf0:ptr, buf1:ptr, buffer_type:int,
                            mask_layer:int, x_first:int, y_first:int, x_dim:int,
                            y_dim:int):
        if buffer_type == int(SR_BUFFER_TYPE_DISPLAY):
            utils.timestamp_add()
        num_rl = int(self.num_rl)
        arr_ptr_rl_sorted = ptr32(self.arr_ptr_rl_sorted)
        arr_region_insideness = ptr32(self.arr_region_insideness)
        arr_region_payload = ptr32(self.arr_region_payload)
        arr_region_fill0 = ptr8(self.arr_region_fill0)
        arr_region_fill1 = ptr8(self.arr_region_fill1)
        region_unused = int(RL_REGION_UNUSED)

        # TODO: handle horizontal scanlines
        buffer_is_payload = bool(buffer_type == int(SR_BUFFER_TYPE_PAYLOAD))
        num_scanlines = x_dim
        len_scanline = y_dim
        s_first = x_first + int(RL_SP_BIAS)
        s_last = s_first + num_scanlines - 1
        p_first = y_first + int(RL_SP_BIAS)
        p_past_last = p_first + len_scanline

        # Ensure all rl containing or strictly past the first scanline reflect
        # being at that scanline or at their own first scanline, respectively
        for i in range(num_rl):
            rl = ptr32(arr_ptr_rl_sorted[i])
            rl_seek_s_to(rl, s_first)
        # Perform initial sort of *all* rl
        self._sort_range_ptr_rl_insertion(0, num_rl)
        if buffer_type == int(SR_BUFFER_TYPE_DISPLAY):
            utils.timestamp_add()
        # Find first occupied scanline past left bound of buffer, and first rl
        # in that scanline
        s = s_first
        i_rl_s_begin = int(0)
        while i_rl_s_begin < num_rl:
            rl_s_begin = ptr32(arr_ptr_rl_sorted[i_rl_s_begin])
            s = rl_s_begin[int(I_RL_SP)] >> 16
            if s >= s_first:
                break
            i_rl_s_begin += 1
        # Indicate no knowledge of where the range of rl at that s ends, to
        # force a scan below
        i_rl_s_end = i_rl_s_begin

        # Main rasterization loop; each iteration handles a unique s that is
        # actually occupied by rl
        while i_rl_s_begin < num_rl:
            # Can stop if past last scanline of screen
            if s > s_last:
                break
            # Find end of the range of rl at this s, if not yet known
            if i_rl_s_end == i_rl_s_begin:
                while i_rl_s_end < num_rl:
                    rl_s_end = ptr32(arr_ptr_rl_sorted[i_rl_s_end])
                    s_end = rl_s_end[int(I_RL_SP)] >> 16
                    if s_end != s:
                        break
                    i_rl_s_end += 1
            # Reset tracking of region insideness and scanline range to flush
            for i in range(int(RL_NUM_REGIONS) + 1):
                arr_region_insideness[i] = 0
                # Don't need to reset arr_region_payload; we only flush spans
                # with >0 insideness, and for those we will have set the payload
                # below
            # (don't draw until a span reaches buffer start or beyond in p)
            p_span_begin = p_first

            # Inspect all rl in scanline, flushing to scanline once each p's
            # effect is fully known
            i_rl_in_s = i_rl_s_begin
            while i_rl_in_s < i_rl_s_end:
                # Get next rl's p
                rl_in_s = ptr32(arr_ptr_rl_sorted[i_rl_in_s])
                p = rl_in_s[int(I_RL_SP)] & 0xffff
                # See if p starts a new span and last span overlapped display
                if p > p_span_begin:
                    # This p ends a span that overlapped display. Clamp span end
                    # with end of screen and draw.
                    clamped_span = bool(p >= p_past_last)
                    if clamped_span:
                        p = p_past_last
                    for i_reg in range(int(RL_NUM_REGIONS)):
                        if arr_region_insideness[i_reg] > 0:
                            if buffer_is_payload:
                                # Write region's payload to span of payload buf
                                x = s - s_first
                                y_begin = p_span_begin - p_first
                                i_pay = x + y_begin * x_dim
                                i_pay_end = i_pay + (p - p_span_begin) * x_dim
                                buf_payload = ptr16(buf0)
                                payload = arr_region_payload[i_reg]
                                while i_pay < i_pay_end:
                                    buf_payload[i_pay] = payload
                                    i_pay += x_dim
                            else:
                                x = s - s_first
                                fill_mask0 = \
                                    arr_region_fill0[8 * i_reg + (x & 0x7)]
                                fill_mask1 = \
                                    arr_region_fill1[8 * i_reg + (x & 0x7)]
                                # TODO: handle horizontal scanlines
                                y0 = p_span_begin - p_first
                                y1 = p - 1 - p_first
                                fill_or_column_mask_unchecked(
                                    buf0, buf1, x, y0, y1, x_dim, fill_mask0,
                                    fill_mask1)
                            break
                    # Track next span to output, or prevent further output if
                    # next span is past screen end
                    if clamped_span:
                        p_span_begin = int(0x7fffffff)
                    else:
                        p_span_begin = p
                # Apply this rl's effect on insideness and payload tracking, if
                # rl is in any of the layers being drawn
                flags = rl_in_s[int(I_RL_FLAGS)]
                if (flags >> int(RL_FLAG_SHIFT_MASK_LAYER)) & mask_layer:
                    is_past_exit = bool(flags & int(RL_FLAG_BIT_IS_PAST_EXIT))
                    at_endpoint = \
                        bool(flags & int(RL_FLAG_BIT_SCANLINE_HAS_ENDPOINT))
                    delta_inside = int(2)
                    if at_endpoint:
                        delta_inside = int(1)
                    if is_past_exit:
                        delta_inside = 0 - delta_inside
                    region_0_1 = rl_in_s[int(I_RL_REGION_0_1)]
                    arr_region_insideness[region_0_1 >> 16] += delta_inside
                    arr_region_insideness[region_0_1 & 0xffff] += delta_inside
                    if buffer_is_payload and not is_past_exit:
                        payload_0_1 = rl_in_s[int(I_RL_PAYLOAD_0_1)]
                        arr_region_payload[region_0_1 >> 16] = payload_0_1 >> 16
                        arr_region_payload[region_0_1 & 0xffff] = \
                            payload_0_1 & 0xffff
                # Advance this rl to next s while we're here; if rl is done, its
                # s won't change
                rl_increment_s(rl_in_s)
                i_rl_in_s += 1
            # The final unique p should have had the effect of returning all
            # insideness to zero, so the last range in need of flushing was the
            # one before reaching that p (i.e., no remainder to flush here)
            # for i in range(int(RL_NUM_REGIONS)):
            #     if arr_region_insideness[i] != 0:
            #         print("WARNING: scanline ended still inside")

            # Have finished processing this s. Advance to the next one.
            s += 1
            # Expand the end of the "current s" rl range to cover any rl that
            # start at the just-incremented s
            while i_rl_s_end < num_rl:
                rl_s_end = ptr32(arr_ptr_rl_sorted[i_rl_s_end])
                s_end = rl_s_end[int(I_RL_SP)] >> 16
                if s_end != s:
                    break
                i_rl_s_end += 1
            # The "current s" rl range now spans all rl at the incremented s,
            # but it may include some rl at the prior s, and those at the new s
            # may be out of order w.r.t. p. Sort the range to put the prior-s
            # rl at the start, and advance the range start past them.
            self._sort_range_ptr_rl_insertion(i_rl_s_begin, i_rl_s_end)
            while i_rl_s_begin < i_rl_s_end:
                rl_s_begin = ptr32(arr_ptr_rl_sorted[i_rl_s_begin])
                s_begin = rl_s_begin[int(I_RL_SP)] >> 16
                if s_begin == s:
                    break
                i_rl_s_begin += 1
            # If all prior-s rl ended at that s, and there are no rl starting at
            # the new s, the range will be empty. If not done with all rl, find
            # the s for the new range -- as an empty range, will scan for its
            # end at the start of the next iter
            if i_rl_s_begin == i_rl_s_end and i_rl_s_begin < num_rl:
                rl_s_begin = ptr32(arr_ptr_rl_sorted[i_rl_s_begin])
                s = rl_s_begin[int(I_RL_SP)] >> 16

        # Retain rl for redraw unless user clears manually to replace them
        if buffer_type == int(SR_BUFFER_TYPE_DISPLAY):
            utils.timestamp_add()

# Drawing filled circles (ball, hole)

# White filled circles in each diameter
list_diameter_circle = [
bytearray(b'\x01'),
bytearray(b'\x03\x03'),
bytearray(b'\x07\x07\x07'),
bytearray(b'\x06\x0f\x0f\x06'),
bytearray(b'\x0e\x1f\x1f\x1f\x0e'),
bytearray(b'\x0c\x1e\x3f\x3f\x1e\x0c'),
bytearray(b'\x1c\x3e\x7f\x7f\x7f\x3e\x1c'),
bytearray(b'\x3c\x7e\xff\xff\xff\xff\x7e\x3c'),
bytearray(b'\
\x38\xfe\xfe\xff\xff\xff\xfe\xfe\x38\
\x00\x00\x00\x01\x01\x01\x00\x00\x00')]
# White outlines in each diameter
list_diameter_circle_line = [
bytearray(b'\x01'),
bytearray(b'\x03\x03'),
bytearray(b'\x07\x05\x07'),
bytearray(b'\x06\x09\x09\x06'),
bytearray(b'\x0e\x11\x11\x11\x0e'),
bytearray(b'\x0c\x12\x21\x21\x12\x0c'),
bytearray(b'\x1c\x22\x41\x41\x41\x22\x1c'),
bytearray(b'\x3c\x42\x81\x81\x81\x81\x42\x3c'),
bytearray(b'\
\x38\xc6\x82\x01\x01\x01\x82\xc6\x38\
\x00\x00\x00\x01\x01\x01\x00\x00\x00')]

scratch_blit = bytearray(18)

# Draws a circle with the specified line and fill color -- BOTH COLORS MUST BE
# ZERO OR ONE (not gray)
@micropython.native
def draw_circle_line_fill(display, xs_center_f10, ys_center_f10, diameter_f10,
                          color_line, color_fill):
    global scratch_blit

    # Choose actual diameter to use
    diameter_max = len(list_diameter_circle)
    diameter = (diameter_f10 + 0x200) >> 10
    if diameter < 1:
        diameter = 1
    elif diameter > diameter_max:
        diameter = diameter_max
    # Find integer coordinates to use for top-left pixel of diameter's sprite
    rad_floor = diameter >> 1
    xs = ((xs_center_f10 + 0x200) >> 10) - rad_floor
    ys = ((ys_center_f10 + 0x200) >> 10) - rad_floor
    # Choose bytes to blit, possibly inverted
    if color_line == color_fill:
        blit_src = list_diameter_circle[diameter - 1]
    else:
        blit_src = list_diameter_circle_line[diameter - 1]
    if color_line:
        blit_to_use = blit_src
    else:
        blit_to_use = scratch_blit
        for i in range(len(blit_src)):
            blit_to_use[i] = blit_src[i] ^ 0xff
    # Blit sprite, with mask if line and fill differ
    if color_line == color_fill:
        key = 1 - color_line
        display.blit(blit_to_use, xs, ys, diameter, diameter, key, 0, 0)
    else:
        key = -1
        display.blitWithMask(blit_to_use, xs, ys, diameter, diameter, key, 0, 0,
                             list_diameter_circle[diameter - 1])
