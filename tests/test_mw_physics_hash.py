import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from vehicle_vlt_hash import vlt_hash


class VltHashTests(unittest.TestCase):
    def test_original_executable_class_id_vectors(self):
        # Verified by bounded emulation of the supplied Speed.dol wrapper,
        # and independently present in its generated class-key functions.
        vectors = {'engine':0xf1f5fbc7, 'chassis':0xafa210f0, 'tires':0xbd38d1ca,
                   'brakes':0x36350867, 'transmission':0x07a7a3e5,
                   'rigidbodyspecs':0x7c90bb38, 'induction':0xc92a0142,
                   'nos':0xb1669f64, 'EngineRacer':0xb2809518, 'SuspensionRacer':0x6209e06a}
        for name, expected in vectors.items():
            with self.subTest(name=name): self.assertEqual(vlt_hash(name), expected)

    def test_string_semantics(self):
        self.assertEqual(vlt_hash(''), 0)
        self.assertEqual(vlt_hash(b'engine'), vlt_hash('engine'))
        self.assertNotEqual(vlt_hash('Engine'), vlt_hash('engine'))
        self.assertNotEqual(vlt_hash('0x12345678'), 0x12345678)
        with self.assertRaises(ValueError): vlt_hash('engine\0')


if __name__ == '__main__': unittest.main()
