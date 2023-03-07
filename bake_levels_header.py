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

class LevelInfo:
    def __init__(self, offset_bytes, num_chunks, mask_layer_tee, par, xw_tee,
                 yw_tee, xw_hole, yw_hole):
        self.offset_bytes = offset_bytes
        self.num_chunks = num_chunks
        self.mask_layer_tee = mask_layer_tee
        self.par = par
        self.xw_tee = xw_tee
        self.yw_tee = yw_tee
        self.xw_hole = xw_hole
        self.yw_hole = yw_hole

