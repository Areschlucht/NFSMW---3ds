import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from material_recovery_presets import KIND,STRIDE,preset_payload,report


def fixture():
    p=bytearray(STRIDE)
    p[8:18]=b'TESTMODEL\0'
    p[0x28:0x32]=b'TESTPRESET'
    struct.pack_into('<I',p,0x60,0x12345678)
    struct.pack_into('<I',p,0x60+138*4,0xdeadbeef)
    return bytes(p)


class PresetRecoveryTests(unittest.TestCase):
    def test_schema_endian_boundaries_and_provenance(self):
        p=fixture();r=preset_payload(p,file_offset=8)[0]
        self.assertEqual(r['model_name'],'TESTMODEL')
        self.assertEqual(r['preset_name'],'TESTPRESET')
        self.assertEqual(r['part_keys'][0],'12345678')
        self.assertEqual(r['part_keys'][-1],'deadbeef')
        self.assertEqual(len(r['part_keys']),139)
        self.assertEqual(r['file_offset'],8)

    def test_chunk_bounds_and_opaque_unknown_chunks(self):
        p=fixture();data=struct.pack('<II',KIND,len(p))+p
        self.assertEqual(len(report(data)['records']),1)
        self.assertEqual(report(struct.pack('<II',0xffffffff,len(data))+data)['records'],[])
        for malformed in (data[:-1],data+b'\0',struct.pack('<II',KIND,STRIDE-1)+p[:-1]):
            with self.assertRaises(ValueError):report(malformed)

    def test_rejects_unterminated_names_and_partial_records(self):
        p=bytearray(fixture());p[8:0x28]=b'A'*32
        with self.assertRaises(ValueError):preset_payload(p)
        with self.assertRaises(ValueError):preset_payload(fixture()[:-1])


if __name__=='__main__':unittest.main()
