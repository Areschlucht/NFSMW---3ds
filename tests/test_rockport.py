import math
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from nfs_rockport import road_network, streaming_sections


def graph_fixture():
    data = bytearray(192)
    data[:16] = b'CARPX\0\0\3' + struct.pack('>II', 0, 1)
    node = bytearray(64)
    for i in range(2):
        struct.pack_into('>3fH', node, i * 32, i * 10.0, 5.0, 20.0, i)
        node[i * 32 + 16] = 1
        struct.pack_into('>7H', node, i * 32 + 18, 0, *([0xaaaa] * 6))
    segment = bytearray(22)
    struct.pack_into('>2H', segment, 0, 0, 1)
    for tag, index, payload, count in (
        (b'CGcn', 4, b'', 0), (b'CGrd', 5, b'', 0), (b'RNhd', 7, b'', 0),
        (b'RNnd', 8, node, 2), (b'RNpf', 9, b'', 0),
        (b'RNrd', 10, b'', 0), (b'RNsg', 11, segment, 1),
    ):
        at = index * 16
        struct.pack_into('>4sIII', data, at, tag, 0x40000000 | len(payload), count, len(data) - at)
        data.extend(payload)
    return bytearray(b'\x11' * 8) + data


def section(identifier=141, offset=2048, size=16):
    values = [0] * 23
    values[2], values[4], values[5] = identifier, 1, offset
    values[6:9] = [size] * 3
    return struct.pack('<23I', *values)


class RockportTests(unittest.TestCase):
    def test_graph_positions_and_reciprocity(self):
        graph = road_network(graph_fixture())
        self.assertEqual(graph['nodes'], [[0, 5, 20], [10, 5, 20]])
        self.assertEqual(graph['segments'], [[0, 1]])
        self.assertEqual(graph['adjacency_references'], 2)

    def test_bad_graph(self):
        # Offsets include the eight-byte outer padding.
        for at, fmt, value in ((8 + 192, '>f', math.nan),
                               (8 + 192 + 12, '>H', 1),
                               (8 + 192 + 16, '>B', 8),
                               (8 + 192 + 18, '>H', 1),
                               (8 + 256 + 2, '>H', 2),
                               (8 + 256 + 8, '>H', 1)):
            with self.subTest(at=at):
                data = graph_fixture()
                struct.pack_into(fmt, data, at, value)
                with self.assertRaises(ValueError):
                    road_network(data)

    def test_table_pointer_and_overlap(self):
        data = graph_fixture()
        struct.pack_into('>I', data, 8 + 128 + 12, 0xffffffff)
        with self.assertRaises(ValueError):
            road_network(data)
        data = graph_fixture()
        struct.pack_into('>I', data, 8 + 176 + 12, 192 - 176)
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            road_network(data)

    def test_truncated_graph(self):
        for size in (0, 8, 199, 250):
            with self.assertRaises(ValueError):
                road_network(graph_fixture()[:size])

    def test_section_ranges(self):
        self.assertEqual(streaming_sections(section(), 4096), [dict(id=141, offset=2048, bytes=16)])
        for data in (b'', section()[:-1], section(offset=1), section(size=4096),
                     section() + section(), section() + section(identifier=142)):
            with self.assertRaises(ValueError):
                streaming_sections(data, 4096)


if __name__ == '__main__':
    unittest.main()
