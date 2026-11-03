import random
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from world_collision import instance_matrix, transform_point, inverse_affine
from map_recovery_ps_reference import point_transform_reference


def load(d, a, offset=0, single=False):
    return (56 << 26) | (d << 21) | (a << 16) | (single << 15) | offset


def arithmetic(d, a, b, c, xo):
    return (4 << 26) | (d << 21) | (a << 16) | (b << 11) | (c << 6) | (xo << 1)


def independent_program():
    # Synthetic row-affine program with different register allocation/order to
    # the original. Encoded public Gekko operations, no original game code.
    words = [load(1, 3), load(2, 3, 8, True)]
    for dest, offset in ((3, 0), (4, 8)):
        words += [load(5, 4, offset), arithmetic(dest, 5, 0, 1, 12),
                  load(5, 4, offset + 16), arithmetic(dest, 5, dest, 1, 15),
                  load(5, 4, offset + 32), arithmetic(dest, 5, dest, 2, 14),
                  load(5, 4, offset + 48), arithmetic(dest, dest, 5, 0, 21)]
    words += [(60 << 26) | (3 << 21) | (5 << 16),
              (60 << 26) | (4 << 21) | (5 << 16) | (1 << 15) | 8, 0x4e800020]
    return struct.pack(f'>{len(words)}I', *words)


class CollisionTransformTests(unittest.TestCase):
    def test_direction_and_inverse_translation(self):
        instance = dict(raw_10=0, basis_x=[1, 0, 0], basis_z=[0, 0, 1],
                        world_to_local_translation=[-100, -2, -200])
        matrix = instance_matrix(instance)
        self.assertEqual(transform_point([102, 5, 204], matrix), [2, 3, 4])
        self.assertEqual(transform_point([2, 3, 4], inverse_affine(matrix)), [102, 5, 204])
        instance['raw_10'] = 1
        with self.assertRaises(ValueError):instance_matrix(instance)

    def test_scaled_reflected_sheared_inverse(self):
        matrix = [-2, .25, 0, 0, 0, 3, 0, 0, .5, 0, 4, 0, 5, -9, 2, 1]
        for point in ([0, 0, 0], [1, 2, 3], [-500, 2.5, 900]):
            result = transform_point(transform_point(point, matrix), inverse_affine(matrix))
            for a, b in zip(point, result):self.assertAlmostEqual(a, b)
        matrix[:3] = [0, 0, 0]
        with self.assertRaises(ValueError):inverse_affine(matrix)

    def test_bounded_paired_reference_against_affine(self):
        rng = random.Random(2005)
        program = independent_program()
        for _ in range(100):
            matrix = [rng.randint(-20, 20) / 8 if i % 4 != 3 else 0 for i in range(16)]
            matrix[15] = 1
            point = [rng.randint(-100, 100) / 8 for _ in range(3)]
            self.assertEqual(point_transform_reference(program, point, matrix), transform_point(point, matrix))

    def test_reference_rejects_invalid_instructions_memory_budget(self):
        matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        for code in (b'\0'*4, struct.pack('>I', load(0, 3, 12)), independent_program()[:-4], b'\0'*132):
            with self.assertRaises(ValueError):point_transform_reference(code, [1, 2, 3], matrix)


if __name__ == '__main__':unittest.main()
