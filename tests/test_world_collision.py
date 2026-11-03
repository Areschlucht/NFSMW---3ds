import math
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from map_recovery_dol import DolImage
from world_collision import packages, inventory
from map_recovery_collision_manifest import manifest


def collision_fixture():
    root = bytearray(288)
    root[:16] = b'CARPP\0\0\1' + struct.pack('>II', 0, 1)
    root[16:32] = b'Arti' + struct.pack('>III', 0x48000000, 3, 1)
    struct.pack_into('>4sIII', root, 32, b'Name', 0x40000004, 0, 48)
    struct.pack_into('>4sIII', root, 48, b'ca\0\0', 0xc0000080, 1, 48)
    struct.pack_into('>4sIII', root, 64, b'ci\0\0', 0xc0000040, 1, 160)
    asset = 96
    struct.pack_into('>4H2BHI', root, asset, 1, 48, 1, 32, 0, 1, 4, 0x12340000)
    struct.pack_into('>3fHH', root, asset + 16, 1, 2, 3, 128, 16)
    for i, (xyz, extra) in enumerate([((0, 0, 0), 3), ((128, 0, 0), 1), ((0, 0, 128), 8)]):
        struct.pack_into('>3hH', root, asset + 32 + i * 8, *xyz, extra)
    struct.pack_into('>3f2BH4f', root, asset + 64, 0, 0, 0, 0, 2, 0x347c, 3, 4, 0, 1 / 3)
    struct.pack_into('>I', root, asset + 96, 0x19db2f1e)
    instance = 224
    struct.pack_into('>3f', root, instance, 1, 0, 0)
    struct.pack_into('>f', root, instance + 12, 3)
    struct.pack_into('>f', root, instance + 20, 4)
    struct.pack_into('>3f', root, instance + 32, 0, 0, 1)
    struct.pack_into('>f', root, instance + 44, 1)
    struct.pack_into('>4f', root, instance + 48, -100, -2, -200, 1)
    payload = bytes([0x11]) * 8 + struct.pack('<4I', len(root), 101, 0, 0) + root
    return bytearray(struct.pack('<II', 0x3b801, len(payload)) + payload)


class OriginalCollisionTests(unittest.TestCase):
    def test_content_aliases_keep_physical_ranges_and_true_point_bounds(self):
        fixture = collision_fixture()
        report = manifest(fixture + fixture)
        self.assertEqual(report['totals']['physical_packages'], 2)
        self.assertEqual(report['totals']['unique_packages'], 1)
        unique, = report['unique_packages']
        self.assertEqual(unique['source_offsets'], [0, len(fixture)])
        self.assertEqual(unique['native_source_point_bounds'], [[100, 2, 200], [103, 6, 204]])
        self.assertEqual(unique['viewer_source_point_bounds'], [[200, 2, 100], [204, 6, 103]])
        self.assertEqual(unique['material_primitive_counts'], {'19db2f1e': 2})

    def test_mixed_wall_mesh_geometry_and_raw_metadata(self):
        package, = packages(collision_fixture())
        asset = package['assets'][0]
        self.assertEqual(asset['materials'], [0x19db2f1e])
        self.assertEqual(asset['raw_token'], 0x12340000)
        self.assertEqual(asset['parts'][0]['vertices'], [[1, 2, 3], [2, 2, 3], [1, 2, 4]])
        self.assertEqual(asset['parts'][0]['flags'], 1)
        self.assertEqual(asset['parts'][0]['triangles'][0]['attributes'], 8)
        self.assertEqual(asset['walls'][0]['flags'], 2)
        self.assertEqual(asset['walls'][0]['unknown_u16'], 0x347c)
        self.assertEqual(package['instances'][0]['world_to_local_translation'], [-100, -2, -200])
        totals = inventory(collision_fixture())['totals']
        self.assertEqual(totals, dict(packs=1, assets=1, instances=1, quantized_parts=1, triangle_candidates=1, wall_records=1))

    def test_bad_version_and_duplicate_directory(self):
        for address, value in [(36, b'P\0\0\2'), (96, b'ca\0\0')]:
            raw = collision_fixture();raw[address:address + 4] = value
            with self.assertRaises(ValueError):list(packages(raw))

    def test_short_or_out_of_parent_resource(self):
        raw = collision_fixture()
        with self.assertRaises(ValueError):list(packages(raw[:-1]))
        struct.pack_into('>I', raw, 80 + 12, 0)
        with self.assertRaises(ValueError):list(packages(raw))

    def test_quantized_pointer_count_material_radius(self):
        for address, value, fmt in [(158, 0, '>H'), (166, 65535, '>H'), (182, 1, '>B'), (156, 0, '>H')]:
            raw = collision_fixture();struct.pack_into(fmt, raw, address, value)
            with self.assertRaises(ValueError):list(packages(raw))

    def test_wall_geometry_and_instance_reference(self):
        for address, value, fmt in [(220, 0.0, '>f'), (282, 1, '>H'), (144, math.nan, '>f')]:
            raw = collision_fixture();struct.pack_into(fmt, raw, address, value)
            with self.assertRaises(ValueError):list(packages(raw))


def dol_fixture():
    raw = bytearray(0x120)
    for i, offset, address in [(0, 0x100, 0x80003100), (7, 0x110, 0x804fedc0)]:
        struct.pack_into('>I', raw, i * 4, offset)
        struct.pack_into('>I', raw, 0x48 + i * 4, address)
        struct.pack_into('>I', raw, 0x90 + i * 4, 16)
    raw[0x100:] = b'TEXT' + bytes(12) + b'DATA' + bytes(12)
    return raw


class DolMappingTests(unittest.TestCase):
    def test_nonuniform_virtual_mapping(self):
        image = DolImage(dol_fixture())
        self.assertEqual(image.read(0x80003100, 4), b'TEXT')
        self.assertEqual(image.read(0x804fedc0, 4), b'DATA')
        with self.assertRaises(ValueError):image.read(0x8000310c, 8)

    def test_bad_header_and_overlaps(self):
        with self.assertRaises(ValueError):DolImage(bytes(32))
        for at, value in [(7 * 4, 0x108), (0x48 + 7 * 4, 0x80003108), (0x90, 99999)]:
            raw = dol_fixture();struct.pack_into('>I', raw, at, value)
            with self.assertRaises(ValueError):DolImage(raw)


if __name__ == '__main__':
    unittest.main()
