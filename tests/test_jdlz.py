import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from nfs_jdlz import decompress


def stream(body,size):
    return b'JDLZ\x02\x10\0\0'+struct.pack('<II',size,16+len(body))+body


class JdlzTests(unittest.TestCase):
    def test_literals(self):
        self.assertEqual(decompress(stream(b'\0\0ABC',3)),b'ABC')

    def test_overlap_short_distance(self):
        self.assertEqual(decompress(stream(b'\2\1A\0\0',4)),b'AAAA')

    def test_long_distance(self):
        literals=b'ABCDEFGHIJKLMNOPQ'
        body=b'\0\0'+literals[:8]+b'\0'+literals[8:16]+b'\2'+literals[16:]+b'\0\0'
        self.assertEqual(decompress(stream(body,20)),literals+b'ABC')

    def test_bad_backref(self):
        with self.assertRaises(ValueError):decompress(stream(b'\1\1\0\0',3))
        with self.assertRaises(ValueError):decompress(stream(b'\2\1A\0\0',2))

    def test_reserved_flag_tail(self):
        self.assertEqual(decompress(stream(b'\0\0ABC\0\xff',3)),b'ABC')
        with self.assertRaises(ValueError):decompress(stream(b'\0\0ABC\0\xff\xff',3))

    def test_truncation_and_limits(self):
        body=b'\2\1A\0\0'
        for i in range(len(body)):
            with self.assertRaises(ValueError):decompress(stream(body[:i],4))
        with self.assertRaises(ValueError):decompress(stream(body,4),max_output=3)
        with self.assertRaises(ValueError):decompress(stream(body,4)+b'X')


if __name__=='__main__':unittest.main()
