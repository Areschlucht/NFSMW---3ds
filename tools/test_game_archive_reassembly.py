#!/usr/bin/env python3
"""Small deterministic corruption tests for archive reassembly integrity."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import reassemble_game_archives as reader


class ReassemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'output'
        self.data = bytes(range(251)) * 17
        self.addCleanup(patch.stopall)
        patch.object(reader, 'SIZES', (len(self.data),) * 4).start()
        patch.object(reader, 'PART_BYTES', 1024).start()
        parts = []
        for i, offset in enumerate(range(0, len(self.data), 1024)):
            block = self.data[offset:offset + 1024]
            name = f'ZZDATA1.BIN.part{i:02d}.bin'
            (self.root / name).write_bytes(block)
            parts.append({'File': name, 'Offset': offset, 'Bytes': len(block),
                          'SHA256': hashlib.sha256(block).hexdigest()})
        self.manifest = {'Schema': 1, 'Source': 'ZZDATA1.BIN', 'Bytes': len(self.data),
                         'SHA256': hashlib.sha256(self.data).hexdigest(),
                         'ZdirSHA256': reader.ZDIR_SHA, 'PartBytes': 1024, 'Parts': parts}
        self.save()

    def save(self):
        (self.root / 'ZZDATA1.BIN.parts.json').write_text(json.dumps(self.manifest))

    def test_exact_reassembly_and_no_overwrite(self):
        reader.assemble(self.root, self.output, 1)
        self.assertEqual((self.output / 'ZZDATA1.BIN').read_bytes(), self.data)
        with self.assertRaises(ValueError):
            reader.assemble(self.root, self.output, 1)
        self.assertEqual((self.output / 'ZZDATA1.BIN').read_bytes(), self.data)

    def test_corrupt_piece_cannot_publish_archive(self):
        part = self.root / self.manifest['Parts'][0]['File']
        part.write_bytes(b'x' * 1024)
        with self.assertRaisesRegex(ValueError, 'Piece hash mismatch'):
            reader.assemble(self.root, self.output, 1)
        self.assertFalse((self.output / 'ZZDATA1.BIN').exists())

    def test_wrong_whole_hash_cannot_publish_archive(self):
        self.manifest['SHA256'] = '0' * 64
        self.save()
        with self.assertRaisesRegex(ValueError, 'archive hash mismatch'):
            reader.assemble(self.root, self.output, 1)
        self.assertFalse((self.output / 'ZZDATA1.BIN').exists())

    def test_parent_path_rejected(self):
        self.manifest['Parts'][0]['File'] = '../elsewhere.bin'
        self.save()
        with self.assertRaisesRegex(ValueError, 'piece name/offset/size'):
            reader.plan(self.root, 1)
        self.assertFalse(self.output.exists())

    def test_missing_piece_rejected_before_writing(self):
        (self.root / self.manifest['Parts'][0]['File']).rename(self.root / 'saved.bin')
        with self.assertRaisesRegex(ValueError, 'Missing or invalid piece'):
            reader.assemble(self.root, self.output, 1)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
