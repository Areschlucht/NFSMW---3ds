import struct
import sys
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from gc_texture import banner_rgba, png_rgba, rgb5a3, tiled_rgb5a3, tiled_rgb565, indexed, cmpr, rgba8


class GameCubeTextureTests(unittest.TestCase):
    def test_rgb565_opaque_big_endian_golden_pixels_and_tiles(self):
        source=b''.join(struct.pack('>H',value)*16 for value in (0xf800,0x07e0,0x001f,0x8410))
        expected_rows=[]
        for y in range(8):
            left,right=((255,0,0,255),(0,255,0,255)) if y<4 else ((0,0,255,255),(132,130,132,255))
            expected_rows.append(bytes(left)*4+bytes(right)*4)
        self.assertEqual(tiled_rgb565(source,8,8),b''.join(expected_rows))
        # Green's sixth bit is significant; RGB5A3/palette conversion is wrong.
        self.assertEqual(tiled_rgb565(struct.pack('>H',0x0020)*16,4,4),bytes((0,4,0,255))*16)
        for data,w,h in ((bytes(31),4,4),(bytes(32),3,4),(bytes(32),4,0)):
            with self.assertRaises(ValueError):
                tiled_rgb565(data,w,h)

    def test_rgba8_planes_and_tiles(self):
        tile=bytearray(64)
        for i in range(16):
            tile[i*2:i*2+2]=bytes((100+i,10+i))
            tile[32+i*2:34+i*2]=bytes((30+i,50+i))
        output=rgba8(bytes(tile)+bytes(64),8,4)
        self.assertEqual(output[:4],bytes((10,30,50,100)))
        self.assertEqual(output[12:16],bytes((13,33,53,103)))
        self.assertEqual(output[16:32],bytes(16))
        self.assertEqual(output[32:36],bytes((14,34,54,104)))
        with self.assertRaises(ValueError):rgba8(bytes(63),4,4)

    def test_pixel_vectors(self):
        expected = {
            0x8000: (0, 0, 0, 255), 0xffff: (255, 255, 255, 255),
            0xfc00: (255, 0, 0, 255), 0x83e0: (0, 255, 0, 255),
            0x801f: (0, 0, 255, 255), 0x0f00: (255, 0, 0, 0),
            0x7f00: (255, 0, 0, 255), 0x4567: (85, 102, 119, 146),
            0xbe07: (123, 132, 57, 255),
        }
        for value, rgba in expected.items():
            with self.subTest(value=value):
                self.assertEqual(rgb5a3(value), rgba)

    def test_alpha_levels(self):
        self.assertEqual([rgb5a3(a << 12)[3] for a in range(8)],
                         [0, 36, 73, 109, 146, 182, 219, 255])

    def test_tile_order(self):
        # Four 4x4 solid-color tiles must become four quadrants, not stripes.
        source = b''.join(struct.pack('>H', color) * 16 for color in
                          (0xfc00, 0x83e0, 0x801f, 0xffe0))
        rgba = tiled_rgb5a3(source, 8, 8)
        for y in range(8):
            for x in range(8):
                expected = ((255, 0, 0, 255) if x < 4 else (0, 255, 0, 255)) if y < 4 else (
                    (0, 0, 255, 255) if x < 4 else (255, 255, 0, 255))
                self.assertEqual(tuple(rgba[(y*8+x)*4:(y*8+x+1)*4]), expected)

    def test_bad_inputs(self):
        for dimensions in ((0, 4), (-4, 4), (3, 4), (4, 5)):
            with self.assertRaises(ValueError):
                tiled_rgb5a3(b'', *dimensions)
        with self.assertRaises(ValueError):
            tiled_rgb5a3(b'\0' * 31, 4, 4)
        for data in (b'', b'BNR1', b'BNR1' + b'\0' * 6496):
            with self.assertRaises(ValueError):
                banner_rgba(data)

    def test_png_integrity(self):
        expected = bytes([255, 0, 0, 255, 0, 0, 255, 127])
        data = png_rgba(expected, 2, 1)
        self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
        pos, kinds, pixels = 8, [], b''
        while pos < len(data):
            length = struct.unpack_from('>I', data, pos)[0]
            kind, payload = data[pos+4:pos+8], data[pos+8:pos+8+length]
            crc = struct.unpack_from('>I', data, pos+8+length)[0]
            self.assertEqual(crc, zlib.crc32(kind+payload) & 0xffffffff)
            kinds.append(kind)
            if kind == b'IDAT':
                pixels += zlib.decompress(payload)
            pos += 12 + length
        self.assertEqual(kinds, [b'IHDR', b'IDAT', b'IEND'])
        self.assertEqual(pixels, b'\0' + expected)

    def test_c4_indices(self):
        palette=struct.pack('>HH',0xfc00,0x83e0)
        rgba=indexed(b'\x01'*32,8,8,palette,4)
        self.assertEqual(rgba,bytes((255,0,0,255,0,255,0,255))*32)
        with self.assertRaises(ValueError): indexed(b'\xff'*32,8,8,palette,4)

    def test_c8_tile_rows(self):
        palette=struct.pack('>HH',0xfc00,0x801f)
        rgba=indexed(b'\0'*32+b'\1'*32,8,8,palette,8)
        self.assertEqual(rgba[:128],bytes((255,0,0,255))*32)
        self.assertEqual(rgba[128:],bytes((0,0,255,255))*32)

    def test_cmpr_subblocks(self):
        blocks=b''.join(struct.pack('>HH4B',color,0,0,0,0,0)
                        for color in (0xf800,0x07e0,0x001f,0xffff))
        rgba=cmpr(blocks,8,8)
        for x,y,color in ((0,0,(255,0,0,255)),(4,0,(0,255,0,255)),
                          (0,4,(0,0,255,255)),(4,4,(255,255,255,255))):
            self.assertEqual(tuple(rgba[(y*8+x)*4:(y*8+x+1)*4]),color)

    def test_cmpr_interpolation_alpha(self):
        block=struct.pack('>HH4B',0xf800,0x001f,0x1b,0x1b,0x1b,0x1b)
        rgba=cmpr(block*4,8,8)
        self.assertEqual(rgba[:16],bytes((255,0,0,255,0,0,255,255,170,0,85,255,85,0,170,255)))
        transparent=struct.pack('>HH4B',0,0xffff,255,255,255,255)
        self.assertEqual(cmpr(transparent*4,8,8),bytes(8*8*4))


if __name__ == '__main__':
    unittest.main()
