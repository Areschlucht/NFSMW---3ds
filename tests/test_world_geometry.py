import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from decode_world import decode_model


def fixture(floating=True,compiled=False):
    data=bytearray()
    offsets={}
    def add(kind,payload,align=1):
        start=len(data);pad=(-(start+8))%align
        data.extend(struct.pack('<II',kind,pad+len(payload))+bytes([0x11])*pad+payload)
        offsets[kind]=start+8+pad
    header=bytearray(176)
    struct.pack_into('<IHH',header,16,0x1234,1,3)
    struct.pack_into('<3f',header,32,0,0,0);struct.pack_into('<3f',header,48,1,1,0)
    struct.pack_into('<16f',header,64,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)
    header[160:168]=b'TRN_TEST'
    add(0x134011,header,16);add(0x134012,struct.pack('<II',123,0))
    container=len(data);data.extend(struct.pack('<II',0x80134100,0))
    draws=(bytes((0x99 if floating else 0x9b,0,3)) if compiled else b'')+bytes((0,0,0,1,1,1,2,2,2))
    draws=draws.ljust(12,b'\0')
    positions=[(0,0,0),(1,0,0),(0,1,0)]
    position_data=b''.join(struct.pack('>3f',*p) if floating else struct.pack('>3h',*(int(v*256) for v in p)) for p in positions)
    co=12+len(position_data);uv=co+12
    blob=draws+position_data+bytes(12)+struct.pack('>6h',0,0,4096,0,0,4096)
    add(0x134800,struct.pack('>4H5I',22,0,1,0,len(blob),12,len(blob)-4,co,uv),16)
    descriptor=bytearray(16);descriptor[8]=3;descriptor[12]=128 if compiled else 0;descriptor[13]=1 if floating else 32
    struct.pack_into('>H',descriptor,14,12)
    add(0x134801,descriptor,16);add(0x134802,blob,32)
    struct.pack_into('<I',data,container+4,len(data)-container-8)
    return data,offsets


class WorldGeometryTests(unittest.TestCase):
    def test_float_fixed_raw_compiled(self):
        for floating in (False,True):
            for compiled in (False,True):
                raw,_=fixture(floating,compiled);m=decode_model(raw,0,len(raw))
                self.assertEqual(m['positions'],[(0,0,0),(1,0,0),(0,1,0)])
                self.assertEqual(len(m['faces']),1)
                self.assertEqual(m['texcoords'],[(0,0),(1,0),(0,1)])

    def test_bad_count_and_attribute_index(self):
        raw,at=fixture();struct.pack_into('<H',raw,at[0x134011]+20,2)
        with self.assertRaisesRegex(ValueError,'Triangle count'):decode_model(raw,0,len(raw))
        raw,at=fixture();raw[at[0x134802]]=250
        with self.assertRaisesRegex(ValueError,'Attribute arrays'):decode_model(raw,0,len(raw))

    def test_original_statistic_opt_in_keeps_source_and_consumed_checks(self):
        raw,at=fixture();struct.pack_into('<H',raw,at[0x134011]+20,7)
        before=bytes(raw)
        m=decode_model(raw,0,len(raw),allow_triangle_statistic_mismatch=True)
        self.assertEqual(bytes(raw),before)
        self.assertEqual(m['declared_triangles'],7)
        self.assertEqual(m['emitted_position_index_triangles'],1)
        self.assertTrue(m['triangle_statistic_mismatch'])
        for corrupt,reason in (
            (lambda d,o:d.__setitem__(o[0x134802],250),'Attribute arrays'),
            (lambda d,o:struct.pack_into('>f',d,o[0x134802]+12,float('nan')),'Invalid decoded position'),
            (lambda d,o:struct.pack_into('>f',d,o[0x134802]+12,20),'stored bounds'),
            (lambda d,o:struct.pack_into('>I',d,o[0x134801],0xffffffff),'Strip exceeds')):
            broken,offsets=fixture();struct.pack_into('<H',broken,offsets[0x134011]+20,7)
            corrupt(broken,offsets)
            with self.assertRaisesRegex(ValueError,reason):
                decode_model(broken,0,len(broken),allow_triangle_statistic_mismatch=True)

    def test_bad_display_primitive_and_size(self):
        raw,at=fixture(compiled=True);raw[at[0x134802]]=0x90
        with self.assertRaisesRegex(ValueError,'primitive'):decode_model(raw,0,len(raw))
        raw,at=fixture();struct.pack_into('>I',raw,at[0x134801],0xffffffff)
        with self.assertRaisesRegex(ValueError,'Strip exceeds'):decode_model(raw,0,len(raw))

    def test_bad_positions(self):
        raw,at=fixture();struct.pack_into('>f',raw,at[0x134802]+12,float('nan'))
        with self.assertRaisesRegex(ValueError,'Invalid decoded position'):decode_model(raw,0,len(raw))
        raw,at=fixture();struct.pack_into('>f',raw,at[0x134802]+12,20)
        with self.assertRaisesRegex(ValueError,'stored bounds'):decode_model(raw,0,len(raw))

    def test_original_rgb_and_uninterpreted_alpha(self):
        raw,at=fixture()
        # Float fixture's color array begins after 12 draw + 36 position bytes.
        raw[at[0x134802]+48:at[0x134802]+52]=bytes((255,128,64,0))
        model=decode_model(raw,0,len(raw))
        self.assertEqual(model['colors'][0],(1,128/255,64/255,1))


if __name__=='__main__':unittest.main()
