import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from nfs_tpk import parse
from world_materials import world_rgba


def package(alpha_test, blend):
    def chunk(kind, data):
        return struct.pack('<II', kind, len(data)) + data
    info = bytearray(124)
    info[12:16] = b'WALL'
    struct.pack_into('<I', info, 36, 0x1234)
    struct.pack_into('<4I', info, 48, 0, 0, 64, 0)
    struct.pack_into('<2H', info, 68, 4, 4)
    info[85:87] = bytes((alpha_test, blend))
    native = bytes(56) + struct.pack('>I', 6)
    header = chunk(0xb3310000, chunk(0x33310001, bytes(32)) +
                   chunk(0x33310002, struct.pack('<II', 0x1234, 0)) +
                   chunk(0x33310004, info) + chunk(0x33310005, native))
    pixel_start = 8 + len(header) + 8
    base = (pixel_start + 0x87) & ~127
    # Four-by-four GX RGBA8 with zero alpha and nonzero RGB.
    pixels = bytes((0, 20)) * 16 + bytes((40, 60)) * 16
    payload = chunk(0x33320002, bytes(base - pixel_start - 8) + pixels)
    return chunk(0xb3300000, header + chunk(0xb3320000, payload))


class WorldMaterialsTests(unittest.TestCase):
    def test_parser_reads_original_render_settings(self):
        t, = parse(package(2, 0))
        self.assertEqual((t['alpha_test_mode'], t['blend_mode']), (2, 0))
        self.assertEqual(t['rgba'], bytes((20, 40, 60, 0)) * 16)

    def test_solid_wall_retains_rgb_and_ignores_zero_alpha(self):
        t, = parse(package(2, 0))
        converted, _ = world_rgba(t)
        self.assertEqual(converted, bytes((20, 40, 60, 255)) * 16)
        self.assertEqual(t['rgba'], bytes((20, 40, 60, 0)) * 16)

    def test_blended_foliage_retains_source_alpha(self):
        t, = parse(package(0, 1))
        self.assertEqual(world_rgba(t)[0], t['rgba'])

    def test_alpha_test_without_blending_retains_cutouts(self):
        t, = parse(package(1, 0))
        self.assertEqual(world_rgba(t)[0], t['rgba'])

    def test_unimplemented_blend_mode_is_rejected(self):
        t, = parse(package(0, 3))
        with self.assertRaises(ValueError):
            world_rgba(t)

    def test_additive_material_retains_source_alpha(self):
        t, = parse(package(0, 2))
        rgba, rule = world_rgba(t)
        self.assertEqual(rgba, t['rgba'])
        self.assertIn('SRCALPHA/ONE', rule)


if __name__ == '__main__':
    unittest.main()
