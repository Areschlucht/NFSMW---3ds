import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_rockport_scene import sector_samples, world_samples


class WorldSectorTests(unittest.TestCase):
    def setUp(self):
        self.sections = [dict(id=141, offset=8192, bytes=8),
                         dict(id=142, offset=10240, bytes=12),
                         dict(id=160, offset=12288, bytes=16)]
        self.data = b'A'*8 + bytes(2040) + b'B'*12 + bytes(2036) + b'C'*16

    def test_noncontiguous_selection_preserves_alignment_and_omits_gap(self):
        samples = sector_samples(self.data, self.sections, [160, 141])
        self.assertEqual(samples, [(141, 0, b'A'*8), (160, 4096, b'C'*16)])

    def test_selected_sector_must_be_complete(self):
        with self.assertRaises(ValueError):
            sector_samples(self.data[:-1], self.sections, [141, 160])
        # An unused truncated sector does not prevent the existing slice.
        self.assertEqual(sector_samples(self.data[:-1], self.sections, [141])[0][2], b'A'*8)

    def test_bad_selection(self):
        for ids in ([], [141, 141], [999]):
            with self.assertRaises(ValueError):
                sector_samples(self.data, self.sections, ids)

    def test_backwards_or_misaligned_ranges(self):
        for offset in (6144, 8193):
            bad = [self.sections[0], dict(id=160, offset=offset, bytes=8)]
            with self.assertRaises(ValueError):
                sector_samples(self.data, bad, [160])

    def test_separate_source_ranges_need_no_synthetic_padding(self):
        result = world_samples([(141, b'A'*8), (160, b'C'*16)], self.sections, [160, 141])
        self.assertEqual(result, [(141, 8192, b'A'*8), (160, 12288, b'C'*16)])
        with self.assertRaises(ValueError):
            world_samples([(141, b'A'*8)], self.sections, [160])

    def test_overlapping_sources_must_agree(self):
        self.assertEqual(len(world_samples([(141, self.data), (160, b'C'*16)], self.sections, [160])), 1)
        with self.assertRaises(ValueError):
            world_samples([(141, self.data), (160, b'D'*16)], self.sections, [160])


if __name__ == '__main__':
    unittest.main()
