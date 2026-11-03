import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from inspect_map_samples import chunk_headers, directory_records, inspect_samples, name_hash


def chunk(kind, payload):
    return struct.pack('<II', kind, len(payload)) + payload


class MapSampleTests(unittest.TestCase):
    def test_known_filename_hashes(self):
        self.assertEqual(name_hash(r'TRACKS\L2RA.BUN'), 0xa7539b87)
        self.assertEqual(name_hash(r'tracks\l2ra\trackmaps.bin'), 0x0d83357d)

    def test_valid_directory(self):
        row = struct.pack('<6I', 1, 1, 137187, 291120, 982848, 0)
        self.assertEqual(directory_records(row)[0][2] * 2048, 280958976)

    def test_bad_directory(self):
        for fields in ((1, 4, 0, 0, 1, 0), (1, 1, 0, 0, 1, 0),
                       (1, 0, 200000, 200000, 1, 0)):
            with self.assertRaises(ValueError):
                directory_records(struct.pack('<6I', *fields))
        for data in (b'', b'\0' * 23, struct.pack('<12I', 2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0)):
            with self.assertRaises(ValueError):
                directory_records(data)

    def test_nested_and_opaque(self):
        raw = chunk(0x80134000, chunk(0x123, b'abcd')) + chunk(0x80001234, b'opaque')
        rows = chunk_headers(raw)
        self.assertEqual(rows[0]['children'][0]['offset'], 8)
        self.assertNotIn('children', rows[1])

    def test_prefix_payload_and_header(self):
        raw = chunk(0x80134000, chunk(0x123, b'abcd'))
        rows = chunk_headers(raw[:18], len(raw))
        self.assertEqual(rows[0]['children'][0]['status'], 'prefix_ends_in_payload')
        rows = chunk_headers(raw[:10], len(raw))
        self.assertEqual(rows[0]['children'][0]['status'], 'prefix_ends_in_header')

    def test_reject_logical_overrun_even_with_prefix(self):
        with self.assertRaises(ValueError):
            chunk_headers(struct.pack('<II', 1, 100), 20)
        raw = chunk(0x80134000, struct.pack('<II', 1, 100))
        with self.assertRaises(ValueError):
            chunk_headers(raw)

    def test_bounds_and_budget(self):
        for raw in (b'a', chunk(1, b'') + b'x'):
            with self.assertRaises(ValueError):
                chunk_headers(raw)
        with self.assertRaises(ValueError):
            chunk_headers(chunk(1, b'') * 2, max_chunks=1)
        with self.assertRaises(ValueError):
            chunk_headers(b'1234', 3)

    def test_sample_report_and_length_mismatch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            name = r'TRACKS\L2RA.BUN'
            data = chunk(1, b'12345678')
            zdir = root / 'ZDIR.BIN'
            zdir.write_bytes(struct.pack('<6I', name_hash(name), 0, 0, 0, len(data), 0))
            sample = root / 'sample.bin'
            sample.write_bytes(data[:10])
            with patch('inspect_map_samples.SAMPLES', (('sample.bin', name, 10),)):
                report = inspect_samples(root, zdir)['samples'][0]
                self.assertTrue(report['is_prefix'])
                self.assertEqual(report['chunks'][0]['status'], 'prefix_ends_in_payload')
                self.assertEqual(sample.read_bytes(), data[:10])
                sample.write_bytes(data[:9])
                with self.assertRaisesRegex(ValueError, 'expected 10 bytes'):
                    inspect_samples(root, zdir)

    def test_ambiguous_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            name = r'TRACKS\L2RA.BUN'
            zdir = root / 'ZDIR.BIN'
            zdir.write_bytes(struct.pack('<6I', name_hash(name), 0, 0, 0, 8, 0) * 2)
            with patch('inspect_map_samples.SAMPLES', (('sample.bin', name, None),)):
                with self.assertRaisesRegex(ValueError, 'got 2'):
                    inspect_samples(root, zdir)


if __name__ == '__main__':
    unittest.main()
