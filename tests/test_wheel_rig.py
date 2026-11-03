import math
import struct
import sys
import unittest
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from wheel_rig import encode_rig,inspect_rig


def fixture():
    wheels=[dict(pivot=[.6 if i%2==0 else -.6,-.15,-.3 if i<2 else .3],radius=.33,front=i%2==0) for i in range(4)]
    return encode_rig(wheels,[0,1,2,3,4],123)


def crc(raw):
    struct.pack_into('<I',raw,20,zlib.crc32(raw[32:]))


class WheelRigTests(unittest.TestCase):
    def test_roundtrip_and_front_flags(self):
        wheels,groups=inspect_rig(fixture(),5,123)
        self.assertEqual(groups,[0,1,2,3,4]);self.assertEqual([w['front'] for w in wheels],[True,False,True,False])
        self.assertAlmostEqual(wheels[0]['radius'],.33,places=6)

    def test_mismatched_body_and_batch_count(self):
        for batches,body in ((5,124),(6,123)):
            with self.assertRaises(ValueError):inspect_rig(fixture(),batches,body)

    def test_corruption_and_truncation(self):
        raw=bytearray(fixture());raw[-1]^=1
        for data in (raw,b'',fixture()[:-1]):
            with self.assertRaises(ValueError):inspect_rig(data,5,123)

    def test_invalid_pivot_radius_flags_and_groups(self):
        for offset,fmt,value in ((32,'<f',math.nan),(44,'<f',0),(48,'<I',2),(52,'<I',1),(128+16,'<I',5)):
            raw=bytearray(fixture());struct.pack_into(fmt,raw,offset,value);crc(raw)
            with self.assertRaises(ValueError):inspect_rig(raw,5,123)


if __name__=='__main__':unittest.main()
