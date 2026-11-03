import math
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from perf_world_index_audit import read_scene, encode, merged_runs, cache_misses, native_attribute_opportunity


def fixture(batches=None, bad_color=False):
    vertices = [(0., 0., 0., 0., 1., 0., 0., -.25, .1, .2, .3, 1.),
                (.1, 0., 0., 0., 1., 0., 1., .25, .2, .3, .4, 1.),
                (0., .1, 0., 0., 1., 0., 0., .75, .3, .4, .5, 1.)] * 2
    if bad_color:
        vertices[0] = (*vertices[0][:8], math.nan, *vertices[0][9:])
    textures = [(1, 8, 8, 0), (2, 8, 8, 1)]
    batches = batches or [(0, 3, 0, 0), (3, 3, 1, 0)]
    payload = b''.join(struct.pack('<4I', *t) for t in textures+batches)
    payload += b''.join(struct.pack('<12f', *v) for v in vertices)
    return struct.pack('<4s7I', b'NFM1', 2, 6, 2, 2, len(payload), zlib.crc32(payload), 0) + payload


class PerfWorldIndexTests(unittest.TestCase):
    def read(self, raw):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'world.nfm'
            path.write_bytes(raw)
            return read_scene(path)

    def test_exact_order_across_distinct_materials(self):
        scene = self.read(fixture())
        unique, indices = encode(scene['vertices'])
        self.assertEqual(len(unique), 3)
        self.assertEqual(indices, [0, 1, 2, 0, 1, 2])
        self.assertEqual(b''.join(unique[i] for i in indices), b''.join(scene['vertices']))
        self.assertEqual(struct.unpack_from('<f', unique[0], 16)[0], 1.25)
        self.assertEqual(merged_runs(scene['batches'], scene['textures'], [1, 1]), [(0, 3, 0), (3, 3, 1)])

    def test_crc_nonfinite_and_batch_coverage_rejected(self):
        broken = bytearray(fixture());broken[-1] ^= 1
        for raw in (broken, fixture(bad_color=True), fixture(batches=[(0, 3, 0, 0), (4, 3, 1, 0)])):
            with self.assertRaises(ValueError):
                self.read(raw)

    def test_visibility_gap_is_not_merged_into_draw(self):
        textures = [(1, 8, 8, 0)]
        batches = [(0, 3, 0, 0), (3, 3, 0, 0), (6, 3, 0, 0)]
        self.assertEqual(merged_runs(batches, textures, [1, 0, 1]), [(0, 3, 0), (6, 3, 0)])
        self.assertEqual(merged_runs(batches, textures, [1, 1, 1]), [(0, 9, 0)])

    def test_cache_model_resets_at_each_actual_draw(self):
        indices = [0, 1, 2, 0, 1, 2]
        for policy in ('fifo', 'lru'):
            self.assertEqual(cache_misses(indices, [(0, 6, 0)], 3, policy), 3)
            self.assertEqual(cache_misses(indices, [(0, 3, 0), (3, 3, 1)], 3, policy), 6)

    def test_u16_boundary_and_overflow(self):
        vertices = [struct.pack('<I', i)+bytes(32) for i in range(65536)]
        unique, indices = encode(vertices+[vertices[0], vertices[1]])
        self.assertEqual(len(unique), 65536)
        self.assertEqual(indices[65535], 65535)
        with self.assertRaises(ValueError):
            encode(vertices+[vertices[0], struct.pack('<I', 65536)+bytes(32)])

    def test_native_attribute_opportunity_requires_exact_reconstruction(self):
        raw = struct.pack('<5f', .1, .2, .3, 3/4096, 1-7/4096)+struct.pack('<4f', 1/255, 128/255, 254/255, 1)
        report = native_attribute_opportunity([raw]*3)
        self.assertEqual(report['exact_rgba8_reconstructable'], 3)
        self.assertEqual(report['exact_original_s16_q12_uv_reconstructable'], 3)
        self.assertEqual(report['proposed_gpu_bytes_with_u16'], 26)
        changed = raw[:20]+struct.pack('<f', .1)+raw[24:]
        self.assertIsNone(native_attribute_opportunity([changed]*3)['unique_compact_records'])


if __name__ == '__main__':
    unittest.main()
