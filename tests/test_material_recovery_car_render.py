import struct
import sys
import unittest
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from material_recovery_car_render import viewer_normal,reference_scene,material_catalog
from material_recovery_vehicle import texture_hash


class CarRenderRecoveryTests(unittest.TestCase):
    def test_basis_and_left_wheel_rotation_preserve_orientation(self):
        self.assertEqual(viewer_normal((1,2,3)),(1,3,-2))
        self.assertEqual(viewer_normal((1,2,3),1),(-1,3,2))
        self.assertEqual(viewer_normal((1,2,3),-1),(1,3,-2))
        with self.assertRaises(ValueError):viewer_normal((1,2,3),0)

    def test_reference_crc_and_schema_bounds(self):
        payload=struct.pack('<4I',0x1234,8,8,0)+struct.pack('<4I',0,1,0,0)+struct.pack('<8f',0,0,0,0,1,0,.5,.5)
        header=struct.pack('<4s7I',b'NFM1',1,1,1,1,len(payload),zlib.crc32(payload),0)
        self.assertEqual(reference_scene(header+payload)['vertex_count'],1)
        damaged=bytearray(header+payload);damaged[-1]^=1
        with self.assertRaises(ValueError):reference_scene(damaged)
        with self.assertRaises(ValueError):reference_scene(header+payload+b'\0')

    def test_material_name_hash_and_raw_field_offsets(self):
        record=bytearray(168);struct.pack_into('<5I',record,0,1,3,3,texture_hash('TEST'),3)
        record[20:25]=b'TEST\0';struct.pack_into('<f',record,48,.75)
        chunk=struct.pack('<II',0x135200,168)+record
        material=material_catalog(chunk)[texture_hash('TEST')]
        self.assertEqual(material['fields'][0]['offset'],'30')
        self.assertEqual(material['fields'][0]['value'],.75)
        record[20]=ord('B')
        with self.assertRaises(ValueError):material_catalog(struct.pack('<II',0x135200,168)+record)


if __name__=='__main__':unittest.main()
