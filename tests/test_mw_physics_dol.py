import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from vehicle_dol import DolImage


def fixture():
    data = bytearray(0x220)
    for index, offset, address, size in [(0, 0x100, 0x80003100, 0x20), (10, 0x200, 0x803fb49c, 0x20)]:
        for base, value in [(0, offset), (0x48, address), (0x90, size)]:
            struct.pack_into('>I', data, base+index*4, value)
    struct.pack_into('>I', data, 0xe0, 0x80003100)
    struct.pack_into('>3I', data, 0x100, 0x3c608040, 0x3863b49c, 0x4e800020)
    data[0x200:0x210] = b'SuspensionRacer\0'
    return data


class DolMappingTests(unittest.TestCase):
    def test_section_mapping_and_cross_boundary_rejection(self):
        image = DolImage(fixture())
        self.assertEqual(image.file_offset(0x803fb49c), 0x200)
        self.assertEqual(image.address(0x200), 0x803fb49c)
        self.assertEqual(image.c_string(0x803fb49c), 'SuspensionRacer')
        with self.assertRaises(ValueError): image.file_offset(0x803fb49c, executable=True)
        with self.assertRaises(ValueError): image.read(0x8000311e, 4)
        with self.assertRaises(ValueError): image.read(0x80500000, 4)

    def test_signed_low_half_xref_and_clobber(self):
        raw = fixture();image = DolImage(raw)
        refs = image.constant_xrefs([0x803fb49c])
        self.assertEqual(refs, [dict(instruction=0x80003104, origin=0x80003100, target=0x803fb49c, register=3)])
        struct.pack_into('>3I', raw, 0x100, 0x3c608040, 0x80640000, 0x3863b49c)
        self.assertEqual(DolImage(raw).constant_xrefs([0x803fb49c]), [])

    def test_invalid_headers_and_ranges(self):
        with self.assertRaises(ValueError): DolImage(bytes(255))
        data = fixture();struct.pack_into('>I', data, 0x90+10*4, 1000)
        with self.assertRaises(ValueError): DolImage(data)
        data = fixture();struct.pack_into('>I', data, 0x48+10*4, 0x80003104)
        with self.assertRaises(ValueError): DolImage(data)
        data = fixture();struct.pack_into('>I', data, 0xe0, 0x803fb49c)
        with self.assertRaises(ValueError): DolImage(data)
        image = DolImage(fixture())
        for size in (0, -1):
            with self.assertRaises(ValueError): image.read(0x80003100, size)


if __name__ == '__main__': unittest.main()
