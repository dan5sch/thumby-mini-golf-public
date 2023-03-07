#!/usr/bin/env python3

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

from bake_chunk_data import *

def bake_lvl1(level_writer, include_slopes):
    # Specify level geometry
    chunk_data = ChunkData()

    verts_fairway = [
        81, 146, 85, 143, 89, 137, 94, 123, 101, 104, 112, 90, 119, 85, 126, 82,
        135, 81, 144, 81, 155, 83, 163, 90, 173, 101, 180, 109, 190, 115,
        200, 117, 212, 117, 223, 115, 231, 111, 236, 104, 238, 96, 238, 75,
        237, 57, 232, 42, 228, 36, 220, 30, 209, 24, 196, 20, 175, 18, 150, 19,
        127, 22, 100, 28, 80, 36, 62, 52, 52, 72, 44, 91, 41, 99, 40, 106,
        40, 130, 42, 137, 50, 143, 56, 146, 68, 147]
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch(verts_fairway, MGS_REGION_WALL)

    verts_sandtrap = [
        142, 62, 132, 63, 123, 66, 113, 71, 110, 77, 110, 85, 112, 90, 119, 85,
        126, 82, 135, 81, 144, 81, 155, 83, 163, 90, 165, 86, 166, 80, 166, 75,
        164, 70, 159, 65, 152, 62]
    chunk_data.add_loop(MGS_REGION_SANDTRAP, 0x1)  # , 0x3)
    chunk_data.loop_add_edge_batch(verts_sandtrap, MGS_REGION_EMPTY)

    verts_sandtrap = [
        211, 48, 220, 48, 228, 46, 232, 42, 228, 36, 220, 30, 209, 24, 196, 20,
        193, 25, 191, 32, 191, 37, 193, 42, 197, 45, 204, 47]
    chunk_data.add_loop(MGS_REGION_SANDTRAP, 0x1)  # , 0x1)
    chunk_data.loop_add_edge_batch(verts_sandtrap, MGS_REGION_EMPTY)

    if include_slopes:
        verts_slope = [
            101, 104, 41, 99, 40, 106, 40, 130, 42, 137, 50, 143, 56, 146,
            68, 147, 81, 146, 85, 143, 89, 137, 94, 123]
        chunk_data.add_loop(MGS_REGION_SLOPE_RIGHT, 0x1)
        chunk_data.loop_add_edge_batch(verts_slope, MGS_REGION_EMPTY)

    # verts_rock = [187, 85, 202, 72, 205, 78, 190, 91]
    # chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x2)
    # chunk_data.loop_add_edge_batch(verts_rock, MGS_REGION_WALL)

    # Serialize it to file
    mask_layer_tee = 0x1
    par = 4 if include_slopes else 3
    if include_slopes:
        xw_hole = 210
        yw_hole = 100
        xw_tee = xw_hole
        yw_tee = yw_hole - 30
    else:
        xw_tee = 68
        yw_tee = 129
        xw_hole = 205
        yw_hole = 88
    level_writer.write_level(chunk_data, mask_layer_tee, par, xw_tee, yw_tee,
                             xw_hole, yw_hole)

def bake_lvl2(level_writer):
    # Specify level geometry
    chunk_data = ChunkData()

    verts_fairway = [
        308, 161, 335, 164, 362, 164,
        375, 162, 383, 159, 388, 155, 391, 145, 391, 118, 390, 99, 387, 82,
        381, 62, 373, 41, 365, 25, 357, 17, 344, 12, 332, 10, 321, 11, 315, 13,
        312, 16, 309, 22, 306, 37, 307, 58, 307, 73, 304, 88, 301, 96, 296, 100,
        289, 101, 277, 101, 257, 98, 238, 92, 219, 83, 207, 75, 199, 67,
        192, 63, 184, 60, 172, 59, 162, 60, 157, 63, 153, 67, 151, 72, 151, 80,
        153, 89, 160, 101, 169, 111, 182, 120, 209, 133, 236, 143, 261, 150]
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch(verts_fairway, MGS_REGION_WALL)

    # CW to make a hole in the above
    verts_rock = [
        344, 96, 350, 100, 357, 106, 360, 112, 362, 121, 361, 129, 359, 134,
        355, 137, 347, 138, 336, 137, 330, 135, 323, 131, 316, 127, 313, 124,
        313, 122, 314, 119, 317, 114, 323, 105, 328, 99, 331, 96, 336, 95]
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch(verts_rock, MGS_REGION_WALL)

    # Serialize it to file
    mask_layer_tee = 0x1
    par = 3
    xw_tee = 182
    yw_tee = 92
    xw_hole = 337
    yw_hole = 61
    level_writer.write_level(chunk_data, mask_layer_tee, par, xw_tee, yw_tee,
                             xw_hole, yw_hole)

def bake_lvl3(level_writer):
    # Specify level geometry
    chunk_data = ChunkData()

    l_u = [151, 45]
    l_d = [149, 56]
    r_u = [229, 70]
    r_d = [227, 82]
    c_u = [190, 56]
    c_d = [191, 70]
    c_l = [173, 63]
    c_r = [204, 63]

    bl1 = [180, 75]
    bl2 = [165, 67]
    bl3 = [165, 59]
    bl4 = [180, 51]
    br1 = [201, 76]
    br2 = [211, 67]
    br3 = [211, 60]
    br4 = [202, 51]

    verts_fair_left_outer = [
        131, 47, 115, 49, 105, 50, 99, 53, 95, 57, 93, 62, 94, 67, 96, 71,
        100, 73, 111, 75, 126, 77, 141, 80, 154, 81, 169, 79]
    verts_fair_left_inner = [
        157, 69, 149, 70, 141, 69, 131, 66, 123, 62, 131, 59, 141, 57]
    # verts_ramp_left_outer = [180, 51, 168, 47]
    # verts_ramp_left_inner = [157, 57, 165, 59]

    verts_fair_right_outer = [
        242, 81, 249, 82, 254, 85, 257, 89, 259, 96, 261, 104, 265, 108,
        271, 110, 277, 110, 283, 107, 287, 101, 289, 88, 288, 75, 285, 65,
        284, 60, 281, 56, 276, 52, 266, 51, 252, 49, 239, 46,
        227, 45, 212, 47]
    verts_fair_right_inner = [
        220, 58, 229, 57, 237, 58, 245, 60, 252, 63, 245, 67, 237, 69]
    # verts_ramp_right_outer = [201, 76, 213, 80]
    # verts_ramp_right_inner = [220, 69, 211, 67]

    # Left fairway before buffer (always visible; trigger top path)
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1, 0x5)
    chunk_data.loop_add_edge_batch(verts_fair_left_outer, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(bl1, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(bl2, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(verts_fair_left_inner, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(l_d, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(l_u, MGS_REGION_WALL)

    # Left fairway buffer (always visible; no trigger)
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch(c_d, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(c_l, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(bl2, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(bl1, MGS_REGION_WALL)

    # Left ramp before buffer (always visible; trigger bottom path)
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1, 0x3)
    chunk_data.loop_add_edge_batch([157, 57], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(bl3, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(bl4, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([168, 47], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(l_u, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(l_d, MGS_REGION_WALL)

    # Left ramp buffer (always visible; no trigger)
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch(c_u, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(bl4, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(bl3, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(c_l, MGS_REGION_EMPTY)

    # Top middle (visible if taking top)
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x4)
    chunk_data.loop_add_edge_batch(c_d, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(c_r, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(c_u, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(c_l, MGS_REGION_EMPTY)

    # Bottom middle (visible if taking bottom)
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x2)
    chunk_data.loop_add_edge_batch(c_d, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(c_r, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(c_u, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(c_l, MGS_REGION_WALL)

    # Right fairway before buffer (always visible; trigger top path)
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1, 0x5)
    chunk_data.loop_add_edge_batch(verts_fair_right_outer, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(br4, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(br3, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(verts_fair_right_inner, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(r_u, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(r_d, MGS_REGION_WALL)

    # Right fairway buffer (always visible; no trigger)
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch(c_u, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(c_r, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(br3, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(br4, MGS_REGION_WALL)

    # Right ramp before buffer (always visible; trigger bottom path)
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1, 0x3)
    chunk_data.loop_add_edge_batch([220, 69], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(br2, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(br1, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([213, 80], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(r_d, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(r_u, MGS_REGION_WALL)

    # Right ramp buffer (always visible; no trigger)
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch(c_d, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(br1, MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch(br2, MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch(c_r, MGS_REGION_EMPTY)

    # Serialize it to file
    mask_layer_tee = 0x5
    par = 3
    xw_tee = 105
    yw_tee = 62
    xw_hole = 275
    yw_hole = 96
    level_writer.write_level(chunk_data, mask_layer_tee, par, xw_tee, yw_tee,
                             xw_hole, yw_hole)

def bake_lvl4(level_writer):
    # Specify level geometry
    chunk_data = ChunkData()

    # Right fairway
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        149, 55, 155, 66, 161, 81, 165, 88, 171, 92, 178, 95, 186, 96,
        193, 94, 198, 90, 201, 85, 202, 78, 200, 69, 195, 56
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([188, 45, 171, 52], MGS_REGION_EMPTY)

    # Sloped middle
    chunk_data.add_loop(MGS_REGION_SLOPE_DOWN, 0x1)
    chunk_data.loop_add_edge_batch([
        188, 45, 176, 31, 161, 20, 139, 11, 121, 10, 98, 15, 84, 23, 75, 31
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([67, 41, 86, 50], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        108, 54, 111, 49, 115, 45, 121, 42, 128, 41, 135, 43, 142, 47
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([149, 55, 171, 52], MGS_REGION_EMPTY)

    # Left fairway
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        67, 41, 55, 57, 48, 69, 45, 77, 43, 86, 44, 93, 47, 99, 52, 105,
        59, 111, 68, 116, 75, 118, 84, 118, 89, 115, 93, 111, 98, 101,
        100, 95, 101, 90, 101, 80, 103, 68, 105, 61
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([108, 54, 86, 50], MGS_REGION_EMPTY)

    # Left sandtrap
    chunk_data.add_loop(MGS_REGION_SANDTRAP, 0x1)
    chunk_data.loop_add_edge_batch([
        55, 57, 48, 69, 45, 77, 43, 86, 44, 93, 47, 99, 52, 105, 57, 100,
        60, 93, 61, 84, 61, 72, 59, 64
    ], MGS_REGION_EMPTY)

    # Right sandtrap
    chunk_data.add_loop(MGS_REGION_SANDTRAP, 0x1)
    chunk_data.loop_add_edge_batch([
        101, 90, 101, 80, 103, 68, 105, 61, 98, 61, 94, 62, 91, 65, 89, 71,
        89, 78, 91, 83, 95, 87
    ], MGS_REGION_EMPTY)

    # Serialize it to file
    mask_layer_tee = 0x1
    par = 2
    xw_tee = 184
    yw_tee = 82
    xw_hole = 80
    yw_hole = 103
    level_writer.write_level(chunk_data, mask_layer_tee, par, xw_tee, yw_tee,
                             xw_hole, yw_hole)

def bake_lvl5(level_writer):
    # Specify level geometry
    chunk_data = ChunkData()

    # Fairway top-left
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        69, 63,
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([81, 57], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        80, 33, 68, 30, 59, 24, 46, 18,
        35, 15, 27, 16, 20, 20, 16, 27, 16, 34, 21, 41, 30, 47, 33, 54, 32, 59
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([27, 63], MGS_REGION_EMPTY)

    # Fairway bottom-right, triggering only above
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1, 0x3)
    chunk_data.loop_add_edge_batch([
        119, 72, 119, 87, 116, 95,
        110, 103, 105, 110, 103, 118, 106, 124, 114, 131, 127, 135, 144, 135,
        162, 132, 171, 126, 176, 118, 177, 107, 176, 91, 172, 78, 163, 63,
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([146, 46], MGS_REGION_EMPTY)

    # Slope down to lower fairway
    chunk_data.add_loop(MGS_REGION_SLOPE_RIGHT, 0x1)
    chunk_data.loop_add_edge_batch([119, 72], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        146, 46, 129, 39, 110, 35, 96, 34,
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([80, 33], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        81, 57, 97, 56, 110, 59, 116, 64,
    ], MGS_REGION_WALL)

    # Downward vortex slope
    chunk_data.add_loop(MGS_REGION_SLOPE_DOWN, 0x1)
    chunk_data.loop_add_edge_batch([69, 63], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([27, 63], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        19, 68, 38, 87, 45, 87
    ], MGS_REGION_EMPTY)

    # Rightward vortex slope
    chunk_data.add_loop(MGS_REGION_SLOPE_RIGHT, 0x1)
    chunk_data.loop_add_edge_batch([
        21, 112, 38, 95, 38, 87
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        19, 68, 13, 78, 11, 89, 13, 100, 16, 108
    ], MGS_REGION_WALL)

    # Upward vortex slope
    chunk_data.add_loop(MGS_REGION_SLOPE_UP, 0x1)
    chunk_data.loop_add_edge_batch([
        21, 112, 31, 115, 45, 116, 55, 115
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        61, 111, 45, 95, 38, 95
    ], MGS_REGION_EMPTY)

    # Leftward vortex slope, lower
    chunk_data.add_loop(MGS_REGION_SLOPE_LEFT, 0x1)
    chunk_data.loop_add_edge_batch([45, 95], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([61, 111, 66, 104], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([68, 95], MGS_REGION_EMPTY)

    # Leftward vortex slope, upper
    chunk_data.add_loop(MGS_REGION_SLOPE_LEFT, 0x1)
    chunk_data.loop_add_edge_batch([69, 63, 45, 87], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        68, 87, 67, 73, 67, 68
    ], MGS_REGION_WALL)

    # Leftward vortex slope, middle, only when above
    chunk_data.add_loop(MGS_REGION_SLOPE_LEFT, 0x2)
    chunk_data.loop_add_edge_batch([45, 95], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([68, 95], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([68, 87, 45, 87], MGS_REGION_EMPTY)

    # Center rightward vortex slope, triggers below
    chunk_data.add_loop(MGS_REGION_SLOPE_RIGHT, 0x1, 0x5)
    chunk_data.loop_add_edge_batch([
        45, 95, 45, 87, 38, 87, 38, 95
    ], MGS_REGION_EMPTY)

    # Rightward vortex chute, only when below
    chunk_data.add_loop(MGS_REGION_SLOPE_RIGHT, 0x4)
    chunk_data.loop_add_edge_batch([45, 95], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([80, 95], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([80, 87], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([45, 87], MGS_REGION_EMPTY)

    # Rightward chute cont.
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x4)
    chunk_data.loop_add_edge_batch([80, 95], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([116, 95], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([119, 87], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([80, 87], MGS_REGION_EMPTY)

    # Top rock
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        140, 79, 143, 74, 149, 70, 155, 70, 157, 75, 155, 79, 151, 81, 148, 85,
        141, 84
    ], MGS_REGION_WALL)

    # Right rock
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        159, 109, 155, 107, 155, 100, 158, 94, 161, 90, 166, 91, 168, 96,
        166, 103, 163, 107
    ], MGS_REGION_WALL)

    # Left rock
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        141, 115, 136, 111, 132, 108, 132, 99, 136, 96, 141, 97, 143, 103,
        146, 107, 146, 113
    ], MGS_REGION_WALL)

    # Serialize it to file
    mask_layer_tee = 0x3
    par = 3
    xw_tee = 26
    yw_tee = 30
    xw_hole = 149
    yw_hole = 93
    level_writer.write_level(chunk_data, mask_layer_tee, par, xw_tee, yw_tee,
                             xw_hole, yw_hole)

def bake_lvl6(level_writer):
    # Specify level geometry
    chunk_data = ChunkData()

    # Starting area of fairway
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        115, 106, 91, 101, 64, 97, 57, 99, 55, 106, 54, 125, 56, 136, 61, 140,
        79, 142
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([115, 146], MGS_REGION_EMPTY)

    # Small section just right of crossing
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([177, 121], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([141, 114], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([141, 151], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([174, 155], MGS_REGION_EMPTY)

    # Main stretch of fairway, not touching crossing; trigger for top
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1, 0x5)
    chunk_data.loop_add_edge_batch([177, 121], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([174, 155, 211, 161], MGS_REGION_WALL)
    # The bounce-off curve
    chunk_data.loop_add_edge_batch([
        # 227, 162, 233, 157, 240, 152, 250, 147, 261, 143,
        241, 163, 245, 157, 250, 152, 256, 147, 263, 143
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        269, 140, 262, 118,
        252, 97, 238, 78, 220, 59, 198, 43, 164, 25, 133, 17, 113, 14, 107, 15,
        103, 18, 101, 22, 101, 27, 106, 43
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([109, 62], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        137, 75, 145, 77, 164, 84, 180, 94, 197, 110, 212, 127
    ], MGS_REGION_WALL)

    # Fairway before slope; trigger for bottom
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1, 0x3)
    chunk_data.loop_add_edge_batch([109, 62], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([113, 84], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([138, 84], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([137, 75], MGS_REGION_EMPTY)

    # Slope above crossing
    chunk_data.add_loop(MGS_REGION_SLOPE_DOWN, 0x1)
    chunk_data.loop_add_edge_batch([115, 106], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([141, 114], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([138, 84], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([113, 84], MGS_REGION_WALL)

    # Crossing, top (fairway)
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x4)
    chunk_data.loop_add_edge_batch([115, 106], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([115, 146], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([141, 151], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([141, 114], MGS_REGION_WALL)

    # Crossing, bottom (slope)
    chunk_data.add_loop(MGS_REGION_SLOPE_DOWN, 0x2)
    chunk_data.loop_add_edge_batch([115, 106], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([115, 146], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([141, 151], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([141, 114], MGS_REGION_EMPTY)

    # Slope below crossing
    chunk_data.add_loop(MGS_REGION_SLOPE_DOWN, 0x1)
    chunk_data.loop_add_edge_batch([115, 160], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([140, 160], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([141, 151], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([115, 146], MGS_REGION_WALL)

    # Down-below fairway
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        115, 160, 114, 194, 113, 205, 113, 223, 118, 235, 129, 245, 146, 252,
        169, 253, 215, 248, 236, 241, 244, 233, 246, 223, 245, 208, 235, 192,
        217, 180, 201, 175, 181, 173, 161, 175, 140, 180
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([140, 160], MGS_REGION_EMPTY)

    # Top-right sandtrap
    chunk_data.add_loop(MGS_REGION_SANDTRAP, 0x1)
    chunk_data.loop_add_edge_batch([
        220, 59, 218, 71, 222, 85, 230, 93, 241, 97, 252, 97, 238, 78
    ], MGS_REGION_EMPTY)

    # Top-left sandtrap
    chunk_data.add_loop(MGS_REGION_SANDTRAP, 0x1)
    chunk_data.loop_add_edge_batch([
        180, 94, 179, 82, 172, 72, 162, 68, 151, 68, 145, 77, 164, 84
    ], MGS_REGION_EMPTY)

    # Bottom sandtrap
    chunk_data.add_loop(MGS_REGION_SANDTRAP, 0x1)
    chunk_data.loop_add_edge_batch([
        186, 232, 193, 231, 196, 227, 195, 218, 192, 209, 184, 202, 172, 195,
        167, 192, 160, 192, 155, 196, 152, 202, 154, 207, 161, 211, 169, 216,
        175, 221, 176, 226, 178, 230
    ], MGS_REGION_EMPTY)

    # Serialize it to file
    mask_layer_tee = 0x5
    par = 5
    xw_tee = 74
    yw_tee = 123
    xw_hole = 217
    yw_hole = 201
    level_writer.write_level(chunk_data, mask_layer_tee, par, xw_tee, yw_tee,
                             xw_hole, yw_hole)

def bake_lvl_bigwater(level_writer):
    # Specify level geometry
    chunk_data = ChunkData()

    # Fairway
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        397, 273, 425, 223, 436, 195, 443, 173, 447, 154, 447, 132, 443, 115,
        432, 94, 419, 78, 406, 69, 394, 64, 365, 60, 337, 58, 311, 60, 271, 69,
        225, 88, 197, 103, 175, 123, 160, 143, 154, 154, 151, 164, 150, 186,
        157, 225, 177, 276, 190, 299, 215, 319, 231, 327, 252, 330, 288, 331,
        318, 327, 341, 319, 366, 305
    ], MGS_REGION_WALL)

    # Water
    chunk_data.add_loop(MGS_REGION_WATER, 0x1)
    chunk_data.loop_add_edge_batch([
        397, 273, 425, 223, 414, 229, 406, 231, 396, 231, 380, 227, 367, 223,
        357, 215, 355, 208, 357, 197, 363, 187, 375, 175, 378, 168, 377, 162,
        371, 153, 362, 148, 352, 147, 323, 148, 287, 155, 235, 171, 206, 184,
        196, 191, 190, 198, 187, 207, 188, 218, 191, 228, 199, 241, 213, 255,
        234, 268, 259, 279, 289, 285, 303, 287, 314, 285, 322, 280, 331, 272,
        341, 261, 348, 257, 359, 255, 368, 257, 386, 265
    ], MGS_REGION_EMPTY)

    # ...actually I don't like this level. Leaving it here for now, but not
    # using.

    # Serialize it to file
    mask_layer_tee = 0x1
    par = 5
    xw_tee = 358
    yw_tee = 276
    xw_hole = 389
    yw_hole = 202
    level_writer.write_level(chunk_data, mask_layer_tee, par, xw_tee, yw_tee,
                             xw_hole, yw_hole)

def bake_lvl_medwater(level_writer):
    # Specify level geometry
    chunk_data = ChunkData()

    # Fairway
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    # v1
    # chunk_data.loop_add_edge_batch([
    #     239, 222, 275, 215, 305, 205, 323, 197, 341, 184, 355, 170, 365, 156,
    #     370, 145, 373, 133, 374, 121, 373, 111, 369, 98, 357, 81, 343, 66,
    #     327, 53, 311, 45, 294, 42, 280, 43, 265, 47, 255, 53, 244, 62, 227, 69,
    #     190, 76, 146, 85, 130, 91, 119, 99, 108, 112, 100, 124, 95, 137,
    #     91, 151, 90, 165, 93, 183, 97, 190, 103, 197, 117, 206, 136, 213,
    #     164, 219, 214, 223
    # ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        239, 222, 275, 215, 305, 205, 323, 197, 341, 184, 355, 170, 365, 156,
        370, 145, 373, 133, 374, 121, 373, 111, 369, 98, 357, 81, 343, 66,
        327, 53, 311, 45, 294, 42, 280, 43, 265, 47, 254, 51, 242, 58, 224, 65,
        190, 76, 153, 83, 136, 89, 119, 99, 104, 111, 94, 122, 86, 135,
        84, 151, 86, 168, 92, 183, 96, 190, 103, 197, 117, 206, 136, 213,
        164, 219, 214, 223
    ], MGS_REGION_WALL)

    # Water
    chunk_data.add_loop(MGS_REGION_WATER, 0x1)
    chunk_data.loop_add_edge_batch([
        239, 222, 275, 215, 305, 205, 297, 201, 287, 192, 280, 181, 276, 170,
        276, 158, 282, 147, 290, 139, 300, 134, 307, 128, 311, 121, 311, 113,
        307, 108, 299, 103, 283, 102, 252, 105, 221, 112, 186, 122, 156, 134,
        129, 148, 125, 152, 123, 157, 124, 163, 129, 167, 141, 172, 162, 173,
        189, 170, 214, 163, 225, 161, 234, 164, 241, 171, 245, 184, 247, 200,
        247, 210, 245, 217
    ], MGS_REGION_EMPTY)

    # Left sandtrap
    chunk_data.add_loop(MGS_REGION_SANDTRAP, 0x1)
    chunk_data.loop_add_edge_batch([
        175, 116, 157, 114, 141, 119, 131, 126, 127, 137, 129, 148, 156, 134,
        186, 122
    ], MGS_REGION_EMPTY)

    # Right sandtrap
    chunk_data.add_loop(MGS_REGION_SANDTRAP, 0x1)
    chunk_data.loop_add_edge_batch([
        340, 80, 341, 99, 345, 116, 356, 134, 370, 145, 373, 133, 374, 121,
        373, 111, 369, 98, 357, 81, 343, 66
    ], MGS_REGION_EMPTY)

    # Serialize it to file
    mask_layer_tee = 0x1
    par = 4
    xw_tee = 225
    yw_tee = 189
    xw_hole = 307
    yw_hole = 170
    level_writer.write_level(chunk_data, mask_layer_tee, par, xw_tee, yw_tee,
                             xw_hole, yw_hole)

def bake_lvl_eddy(level_writer):
    # Specify level geometry
    chunk_data = ChunkData()

    # Uphill fairway
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        133, 184, 132, 170, 131, 147, 127, 123
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        126, 109, 109, 116, 92, 130, 81, 144, 73, 161, 70, 176, 70, 199,
        74, 218, 82, 231, 92, 238, 103, 242, 116, 241, 123, 237, 126, 231,
        128, 214, 128, 198
    ], MGS_REGION_WALL)

    # Slope
    chunk_data.add_loop(MGS_REGION_SLOPE_RIGHT, 0x1)
    chunk_data.loop_add_edge_batch([
        133, 184, 140, 176, 149, 172, 158, 171, 167, 174, 172, 177, 175, 184,
        180, 195, 187, 204, 204, 219, 217, 228, 226, 231, 234, 231, 241, 228,
        247, 222, 250, 215, 249, 206, 247, 200, 242, 195, 239, 190, 239, 186,
        242, 182, 253, 177
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        263, 172, 258, 161, 254, 146
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        253, 131, 236, 144, 217, 153, 201, 154, 197, 151, 197, 144, 201, 137,
        207, 127, 209, 118, 207, 110, 200, 102, 191, 99, 177, 100, 151, 103
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        126, 109, 127, 123, 131, 147, 132, 170
    ], MGS_REGION_EMPTY)

    # Downhill fairway
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        253, 131, 254, 146, 258, 161
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        263, 172, 267, 173, 268, 178, 271, 195, 273, 216, 278, 225, 287, 231,
        300, 234, 316, 232, 329, 223, 338, 208, 343, 180, 342, 155, 336, 135,
        325, 121, 314, 112, 300, 107, 288, 108, 277, 113, 266, 120
    ], MGS_REGION_WALL)

    # Serialize it to file
    mask_layer_tee = 0x1
    par = 3
    xw_tee = 103
    yw_tee = 218
    xw_hole = 306
    yw_hole = 203
    level_writer.write_level(chunk_data, mask_layer_tee, par, xw_tee, yw_tee,
                             xw_hole, yw_hole)

def bake_lvl_highbridge(level_writer):
    # Specify level geometry
    chunk_data = ChunkData()

    # Starting fairway
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([106, 167], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        113, 135, 105, 123
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([93, 106], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        110, 59, 97, 53, 88, 50, 78, 49, 64, 51, 55, 56, 44, 67, 37, 78, 34, 94,
        35, 103, 39, 113, 45, 118, 53, 121, 65, 125, 75, 131, 82, 141, 94, 156
    ], MGS_REGION_WALL)

    # Starting fairway trigger for under bridge
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1, 0x3)
    chunk_data.loop_add_edge_batch([115, 116], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([131, 68], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([110, 59], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([93, 106], MGS_REGION_WALL)

    # Starting fairway past trigger before under bridge
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        136, 124, 146, 100
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([154, 79], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([131, 68], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([115, 116], MGS_REGION_WALL)

    # Slope to enter bridge from start, triggering over bridge
    chunk_data.add_loop(MGS_REGION_SLOPE_LEFT, 0x1, 0x5)
    chunk_data.loop_add_edge_batch([129, 174], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        125, 139, 119, 138
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([113, 135], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        106, 167, 116, 172
    ], MGS_REGION_WALL)

    # Bridge not yet over fairway, start side
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        129, 174, 139, 173, 147, 168, 155, 154
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([163, 137], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        136, 124, 130, 136
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([125, 139], MGS_REGION_EMPTY)

    # Bridge overlapping section, over
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x4)
    chunk_data.loop_add_edge_batch([
        163, 137, 172, 113
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([178, 90], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        154, 79, 146, 100
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([136, 124], MGS_REGION_EMPTY)

    # Bridge overlapping section, under
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x2)
    chunk_data.loop_add_edge_batch([
        163, 137, 172, 113
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([178, 90], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        154, 79, 146, 100
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([136, 124], MGS_REGION_WALL)

    # Bridge past over fairway, end side
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([178, 90], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([187, 67], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        176, 38, 169, 48, 163, 60
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([154, 79], MGS_REGION_EMPTY)

    # Slope to exit bridge, triggering over bridge
    chunk_data.add_loop(MGS_REGION_SLOPE_RIGHT, 0x1, 0x5)
    chunk_data.loop_add_edge_batch([
        187, 67, 193, 58
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([200, 51], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([190, 28], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([176, 38], MGS_REGION_EMPTY)

    # Fairway before trigger past under bridge
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([181, 146], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([203, 102], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        178, 90, 172, 113
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([163, 137], MGS_REGION_WALL)

    # Fairway trigger past bridge for under bridge
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1, 0x3)
    chunk_data.loop_add_edge_batch([197, 158], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([230, 109], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([203, 102], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([181, 146], MGS_REGION_WALL)

    # Far fairway
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        197, 158, 211, 167, 225, 174, 249, 179, 268, 180, 285, 179, 297, 174,
        305, 168, 312, 158, 320, 139, 324, 115, 323, 97, 318, 84, 309, 67,
        298, 53, 287, 43, 274, 35, 259, 29, 241, 25, 222, 22, 201, 24
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([190, 28], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        200, 51, 207, 47, 213, 46, 218, 48, 215, 54, 209, 62, 205, 69, 203, 76,
        206, 83, 213, 89, 224, 92, 253, 93, 271, 91, 284, 90, 288, 91, 289, 95,
        285, 101, 280, 106, 271, 110, 255, 112
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([230, 109], MGS_REGION_EMPTY)

    # Rock in far fairway
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        278, 158, 268, 160, 255, 158, 252, 152, 255, 146, 261, 140, 269, 136,
        286, 131, 291, 133, 292, 136, 290, 144, 286, 152
    ], MGS_REGION_WALL)

    # Serialize it to file
    mask_layer_tee = 0x5
    par = 3
    xw_tee = 60
    yw_tee = 76
    xw_hole = 224
    yw_hole = 76
    level_writer.write_level(chunk_data, mask_layer_tee, par, xw_tee, yw_tee,
                             xw_hole, yw_hole)

def bake_lvl_finale(level_writer):
    # Specify level geometry
    chunk_data = ChunkData()

    # Starting fairway, with parts to be overlapped by water
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([211, 264], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        153, 199, 145, 182, 141, 166, 140, 151
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        143, 137, 111, 139
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        97, 214, 124, 231, 165, 250
    ], MGS_REGION_WALL)

    # First half of first sloped curve
    chunk_data.add_loop(MGS_REGION_SLOPE_RIGHT, 0x1)
    chunk_data.loop_add_edge_batch([
        148, 128, 116, 101, 111, 118, 111, 139
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([143, 137], MGS_REGION_WALL)

    # Second half of first sloped curve
    chunk_data.add_loop(MGS_REGION_SLOPE_DOWN, 0x1)
    chunk_data.loop_add_edge_batch([
        148, 128, 156, 124, 166, 127
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        173, 131, 211, 113, 199,  99, 182, 86, 158, 78, 137, 80, 123, 90,
        116, 101
    ], MGS_REGION_EMPTY)

    # Middle fairway
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        244, 195, 240, 184, 229, 151
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        221, 131, 211, 113
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        173, 131, 181, 140, 191, 155, 201, 173
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([208, 192], MGS_REGION_EMPTY)

    # First half of second sloped curve
    chunk_data.add_loop(MGS_REGION_SLOPE_UP, 0x1)
    chunk_data.loop_add_edge_batch([251, 204], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        244, 195, 208, 192, 218, 212, 227, 224
    ], MGS_REGION_EMPTY)

    # Second half of second sloped curve
    chunk_data.add_loop(MGS_REGION_SLOPE_UP, 0x1)
    chunk_data.loop_add_edge_batch([
        251, 204, 227, 224, 239, 235, 248, 239, 259, 242, 274, 242, 284, 240,
        299, 232
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([314, 209], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([321, 183], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        267, 193, 264, 203, 258, 206
    ], MGS_REGION_WALL)

    # Fairway before uphill to hole
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([320, 146], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        264, 149, 267, 158, 269, 175
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([267, 193], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([321, 183, 321, 164], MGS_REGION_WALL)

    # Uphill to hole
    chunk_data.add_loop(MGS_REGION_SLOPE_DOWN, 0x1)
    chunk_data.loop_add_edge_batch([320, 146], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([316, 124], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        243, 125, 254, 135
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([264, 149], MGS_REGION_EMPTY)

    # Fairway at hole, to be overlapped by water
    chunk_data.add_loop(MGS_REGION_FAIRWAY, 0x1)
    chunk_data.loop_add_edge_batch([
        234, 60, 213, 85
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([234, 114], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([243, 125], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([
        316, 124, 310, 110, 305, 103, 299, 97, 293, 92, 280, 82,
        262, 70
    ], MGS_REGION_WALL)

    # Upper water, to be overlapped by first slope and overlap some fairways
    chunk_data.add_loop(MGS_REGION_WATER, 0x1)
    chunk_data.loop_add_edge_batch([
        234, 60, 211, 56, 175, 56, 139, 63, 108, 80, 81, 106, 66, 138, 54, 179,
        75, 200
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        97, 214, 106, 201, 110, 189, 112, 178, 111, 157, 111, 139, 148, 105,
        211, 113
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([221, 131], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        234, 114, 227, 105, 223, 93, 222, 81, 227, 69
    ], MGS_REGION_EMPTY)

    # Lower water, to be overlapped by second slope and overlap some fairways
    chunk_data.add_loop(MGS_REGION_WATER, 0x1)
    chunk_data.loop_add_edge_batch([
        211, 264, 245, 271, 280, 268, 306, 254, 331, 226
    ], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        314, 209, 267, 226
    ], MGS_REGION_EMPTY)
    chunk_data.loop_add_edge_batch([208, 192], MGS_REGION_WALL)
    chunk_data.loop_add_edge_batch([
        153, 199, 169, 224, 187, 246
    ], MGS_REGION_EMPTY)

    # Serialize it to file
    mask_layer_tee = 0x1
    par = 6
    xw_tee = 133
    yw_tee = 211
    xw_hole = 250
    yw_hole = 98
    level_writer.write_level(chunk_data, mask_layer_tee, par, xw_tee, yw_tee,
                             xw_hole, yw_hole)

def main():
    level_writer = LevelWriter("levels.py", "levels.bin")
    level_writer.write_header()

    bake_lvl1(level_writer, False)
    bake_lvl2(level_writer)
    bake_lvl3(level_writer)
    bake_lvl4(level_writer)
    # bake_lvl5(level_writer)
    bake_lvl6(level_writer)
    bake_lvl_medwater(level_writer)
    bake_lvl_eddy(level_writer)
    bake_lvl_highbridge(level_writer)
    bake_lvl_finale(level_writer)

    level_writer.write_footer()

if __name__ == "__main__":
    main()
