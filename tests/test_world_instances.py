import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from world_instances import complete_prefix,read_instances,place_instance,transform_points


def fixture(index=0):
    data=bytearray(struct.pack('<II',0x80034100,0))
    obj=bytearray(72);obj[:8]=b'XB_TEST\0';struct.pack_into('<3I',obj,28,0x11111111,0x22222222,0)
    data.extend(struct.pack('<II',0x34102,len(obj))+obj)
    pad=(-(len(data)+8))%16
    node=bytearray(64)
    struct.pack_into('<6f',node,0,9,20,30,10,21,30)
    struct.pack_into('<H',node,28,0xffff)  # Not the object index.
    struct.pack_into('<3f',node,32,10,20,30)
    struct.pack_into('<9h',node,44,0,8192,0,-8192,0,0,0,0,8192)
    struct.pack_into('<H',node,62,index)
    data.extend(struct.pack('<II',0x34103,pad+64)+b'\x11'*pad+node)
    struct.pack_into('<I',data,4,len(data)-8)
    return data


class InstanceTests(unittest.TestCase):
    def test_tail_index_alignment_and_lod_fallback(self):
        instances=read_instances(fixture())
        self.assertEqual(len(instances),1)
        model={'hash':'22222222','positions':[(0,0,0),(1,0,0),(0,1,0)]}
        placed=place_instance(instances[0],{'22222222':model})
        self.assertEqual(placed['positions'],[(10,20,30),(10,21,30),(9,20,30)])
        self.assertEqual(placed['instance_bounds_error'],0)

    def test_bad_index(self):
        with self.assertRaisesRegex(ValueError,'object index'):read_instances(fixture(1))

    def test_missing_or_misplaced_model(self):
        instance=read_instances(fixture())[0]
        self.assertIsNone(place_instance(instance,{}))
        self.assertIsNone(place_instance(instance,{'11111111':{'positions':[(100,0,0)]}}))

    def test_prefix_discards_cut_chunk(self):
        whole=bytes(fixture());self.assertEqual(complete_prefix(whole+b'ab'),whole)
        self.assertEqual(complete_prefix(whole+struct.pack('<II',123,100)+b'abc'),whole)

    def test_transform_rejects_nonfinite(self):
        with self.assertRaises(ValueError):transform_points([(0,0,0)],[1]*9,[float('nan'),0,0])
        with self.assertRaises(ValueError):transform_points([(0,0,0)],[1],[0,0,0])


if __name__=='__main__':unittest.main()
