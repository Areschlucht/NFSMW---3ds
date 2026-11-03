import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from material_recovery_world_banks import texture_keys,memory_entries


def chunk(kind,payload):return struct.pack('<II',kind,len(payload))+payload


def texture_bank():
    header=chunk(0x33310001,struct.pack('<I',1)+b'TEST'.ljust(28,b'\0'))
    header+=chunk(0x33310002,struct.pack('<4I',0x7e2734a8,0,0x12345678,3))
    meta=chunk(0xb3310000,header);pixels=chunk(0xb3320000,b'P'*128)
    full=chunk(0xb3300000,meta+pixels)
    return full,full[:8+len(meta)]


class WorldBankRecoveryTests(unittest.TestCase):
    def test_full_and_sparse_tpk_keys_preserve_provenance(self):
        full,sparse=texture_bank();a=texture_keys(full);b=texture_keys(sparse,len(full))
        self.assertEqual([r['hash'] for r in a],['7e2734a8','12345678'])
        self.assertEqual(a[1]['reference_word1'],'00000003')
        self.assertTrue(all(r['package_complete'] for r in a))
        self.assertTrue(all(not r['package_complete'] for r in b))
        self.assertEqual([r['hash'] for r in a],[r['hash'] for r in b])
        self.assertEqual(a[0]['package_name'],'TEST')

    def test_sparse_memory_entry_remains_header_evidence(self):
        full,sparse=texture_bank();raw=struct.pack('<4I',0,0,0x53219999,1)
        raw+=struct.pack('<5I',0xaabbccdd,36,len(full),len(sparse),0x123000)+sparse
        r=memory_entries(raw)[0]
        self.assertEqual(r['key'],'aabbccdd');self.assertEqual(len(r['textures']),2)
        self.assertFalse(r['textures'][0]['package_complete'])
        with self.assertRaises(ValueError):memory_entries(raw[:-1])

    def test_no_scan_of_opaque_payloads_or_partial_keys(self):
        full,sparse=texture_bank()
        self.assertEqual(texture_keys(chunk(0xdeadbeef,full)),[])
        with self.assertRaises(ValueError):texture_keys(sparse[:-1],len(full))
        with self.assertRaises(ValueError):texture_keys(full,len(full)-1)


if __name__=='__main__':unittest.main()
