import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from material_recovery_carparts import CarParts
from material_recovery_vehicle import texture_hash


def fixture(group=0,count=1):
    def chunk(k,b):return struct.pack('<II',k,len(b))+b
    header=[0]*15;header[2]=6;header[8]=1;header[14]=count
    part=bytearray(16);struct.pack_into('<I',part,0,texture_hash('PAINT'))
    struct.pack_into('<HHH',part,8,0,group,0xffff)
    body=b''.join((chunk(0x34603,struct.pack('<15I',*header)),chunk(0x34606,b'PAINT\0\0\0'),
        chunk(0x3460c,struct.pack('<2H',1,0)),chunk(0x34605,struct.pack('<II',texture_hash('RED'),183)),
        chunk(0x3460a,b''),chunk(0x3460b,b''),chunk(0x34604,part)))
    return chunk(0x80034602,body)


class CarPartRecoveryTests(unittest.TestCase):
    def test_original_word_order_and_attribute_indirection(self):
        db=CarParts(fixture());p=db.part(texture_hash('PAINT'))
        self.assertEqual(p['name'],'PAINT');self.assertEqual(db.value(p,'RED'),183)
        self.assertIsNone(db.value(p,'GLOSS'))
        self.assertEqual(p['fields'][texture_hash('RED')]['original_bytes'],struct.pack('<II',texture_hash('RED'),183).hex())

    def test_invalid_group_and_count_rejected(self):
        db=CarParts(fixture(group=2))
        with self.assertRaises(ValueError):db.part(texture_hash('PAINT'))
        with self.assertRaises(ValueError):CarParts(fixture(count=2))
        with self.assertRaises(ValueError):CarParts(fixture()[:-1])
        with self.assertRaises(ValueError):CarParts(fixture()).part(0x12345678)


if __name__=='__main__':unittest.main()
