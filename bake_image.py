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

import sys
import png

def repr_bytearray_all_escaped(b):
    return "bytearray(b'" + "".join([f"\\x{x:02x}" for x in b]) + "')"

# An image encoded as a row-major one byte per pixel byte array, with each byte
# holding a [0, 3] value as used by thumbyGrayscale
class GrayImage:
    def __init__(self, filename=None):
        width, height, rows, info = png.Reader(filename=filename).asRGBA8()
        self.width = width
        self.height = height
        # Get 0-255 values of each pixel
        bytes_value = bytearray()
        for row in rows:
            bytes_value.extend(row[::4])
        # Map values to colors
        key = sorted(list(set(bytes_value)))
        if len(key) not in (2, 4):
            raise ValueError("image does not have 2 or 4 colors")
        if len(key) == 4:
            key_new = [key[0], key[3], key[1], key[2]]
            key = key_new
        self.colors = bytearray([key.index(v) for v in bytes_value])

    # Returns the color of pixel (x,y) or 0 if out of range
    def pixel_color_or_zero(self, x, y):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return 0
        return self.colors[y * self.width + x]

    # Returns Thumby-style VLSB bytes encoding the image
    def to_vlsb(self):
        out0 = bytearray()
        out1 = bytearray()
        for y_top in range(0, self.height, 8):
            for x in range(self.width):
                byte0 = 0
                byte1 = 0
                for i in range(8):
                    color = self.pixel_color_or_zero(x, y_top + i)
                    byte0 |= (color & 0x1) << i
                    byte1 |= (color >> 1) << i
                out0.append(byte0)
                out1.append(byte1)
        return out0, out1

def print_png_vlsb(filename):
    image = GrayImage(filename=filename)
    print("width =", image.width)
    print("height =", image.height)
    out0, out1 = image.to_vlsb()
    print("bytes0 =", repr_bytearray_all_escaped(out0))
    print("bytes1 =", repr_bytearray_all_escaped(out1))

def main():
    if len(sys.argv) != 2:
        sys.stderr.write(f"usage: {sys.argv[0]} file.png\n")
        sys.exit(1)
    print_png_vlsb(sys.argv[1])

if __name__ == "__main__":
    main()
