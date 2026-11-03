import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from vehicle_attributes import VehicleAttributes, chunks, unpack
from vehicle_vlt_hash import vlt_hash as h


def fixture():
    """Independent tiny mixed-endian GC database; contains no game data."""
    b=bytearray(256)
    struct.pack_into('>II',b,0,0x53747245,32)
    b[8:20]=b'default\0bmw\0'
    name=b'EA::Reflection::Float\0';b[32:32+len(name)]=name
    typ=h('EA::Reflection::Float');cls=h('pvehicle')
    for i,(key,offset,capacity,flags) in enumerate([('MASS',0,1,6),('TORQUE',4,3,7),('FRONT_AXLE',0,1,4)]):
        struct.pack_into('>IIHHHBB',b,64+i*16,h(key),typ,offset,4,capacity,flags,2)
    for at,mass in [(128,1300),(160,1350)]:
        struct.pack_into('>f4H3f',b,at,mass,3,3,4,0,170,251,340)
    v=bytearray()
    def chunk(tag,data):
        at=len(v);v.extend(struct.pack('>II',int.from_bytes(tag,'big'),8+len(data))+data);return at+8
    chunk(b'DepN',b'');chunk(b'StrN',b'')
    database=struct.pack('>5I',1,0,1,0,4)
    schema=struct.pack('>7I',cls,3,3,0,24,0,2)
    parent=struct.pack('>8I',h('default'),cls,0,1,0,1,1,0)+struct.pack('>I',typ)+struct.pack('>I f H BB',h('FRONT_AXLE'),1.43,0,32,0)
    child=struct.pack('>8I',h('bmw'),cls,h('default'),0,0,0,0,0)
    data=chunk(b'DatN',database+schema+parent+child)
    records=[(h('database'),0xcbbc628f,0,20,data),(cls,0x5e970cbc,0,28,data+20),(h('default'),0x8e112eb7,0,len(parent),data+48),(h('bmw'),0x8e112eb7,0,len(child),data+48+len(parent))]
    chunk(b'ExpN',struct.pack('>I',4)+b''.join(struct.pack('>5I',*x) for x in records))
    fixes=[(0,2,0,0),(data+12,3,1,32),(data+20+12,3,1,64),(data+48+28,3,1,128),(data+48+len(parent)+28,3,1,160),(0,0,0,0)]
    chunk(b'PtrN',b''.join(struct.pack('>IHHI',*x) for x in fixes))
    raw=bytearray(384+len(v));raw[:4]=b'VPAK';struct.pack_into('<8I',raw,4,1,64,3,0,len(b),len(v),128,384)
    raw[128:384]=b;raw[384:]=v
    return raw,dict(bin=128,vlt=384,data=data)


def dependent_fixture():
    raw,at=fixture();bin_size,vlt_size,bin_offset,vlt_offset=struct.unpack_from('<4I',raw,20)
    binary=bytes(raw[bin_offset:bin_offset+bin_size]);vlt=bytes(raw[vlt_offset:vlt_offset+vlt_size]);directory=chunks(vlt)
    start,end=directory[0x4578704e];child_export=bytes(vlt[start+4+3*20:start+4+4*20])
    rebuilt=bytearray()
    for tag,(start,end) in directory.items():
        data=struct.pack('>I',1)+child_export if tag==0x4578704e else bytes(vlt[start:end])
        rebuilt.extend(struct.pack('>II',tag,len(data)+8)+data)
    # Variant9 permits a64-byte boundary which is not128 aligned.
    result=bytearray(448+len(rebuilt));result[:128]=raw[:128]
    struct.pack_into('<I',result,12,9);struct.pack_into('<I',result,24,len(rebuilt));struct.pack_into('<I',result,32,448)
    result[128:384]=binary;result[448:]=rebuilt;struct.pack_into('>f',result,128+160,1400)
    return result


class AttributeTests(unittest.TestCase):
    def test_required_array_optional_inheritance_and_original_provenance(self):
        raw,_=fixture();before=bytes(raw);db=VehicleAttributes(raw)
        row=db.find('pvehicle','bmw');mass=db.field_value(row,'MASS');torque=db.field_value(row,'TORQUE')
        self.assertEqual(mass['value'],1350);self.assertEqual(mass['file_offset'],288)
        self.assertEqual(torque['value']['values'],[170,251,340]);self.assertEqual(torque['value']['count'],3)
        self.assertAlmostEqual(db.field_value(row,'FRONT_AXLE')['value'],1.43,places=6)
        self.assertEqual(db.field_value(row,'FRONT_AXLE')['source_collection'],h('default'))
        with self.assertRaises(KeyError):db.field_value(row,'FRONT_AXLE',False)
        self.assertEqual(bytes(raw),before)
        self.assertEqual(mass['original_bytes'],struct.pack('>f',1350).hex())
        self.assertEqual(len(db.fixups),4)

    def test_corrupt_streams_and_gc_abi_rejected(self):
        raw,at=fixture()
        for location,fmt,value in [(4,'<I',2),(32,'<I',128),(at['vlt']+at['data']+20+24,'>I',1),(at['vlt']+at['data']+48+46,'>H',0x0020),(at['vlt']+at['data']+48+48+8,'>I',h('bmw'))]:
            bad=bytearray(raw);struct.pack_into(fmt,bad,location,value)
            with self.subTest(location=location):
                with self.assertRaises(ValueError):VehicleAttributes(bad)
        with self.assertRaises(ValueError):VehicleAttributes(raw[:-1])

    def test_dependent_schema_cross_file_inheritance_and_provenance(self):
        base_raw,_=fixture();base=VehicleAttributes(base_raw);raw=dependent_fixture()
        with self.assertRaises(ValueError):VehicleAttributes(raw)
        db=VehicleAttributes(raw,dependency=base);row=db.find('pvehicle','bmw')
        self.assertEqual(db.variant,9);self.assertEqual(db.field_value(row,'MASS')['value'],1400)
        own=db.field_value(row,'MASS');inherited=db.field_value(row,'FRONT_AXLE')
        self.assertEqual(own['source_sha256'],db.sha256);self.assertEqual(inherited['source_sha256'],base.sha256)
        self.assertNotEqual(own['source_sha256'],inherited['source_sha256'])
        self.assertAlmostEqual(inherited['value'],1.43,places=6)
        self.assertEqual(db.field_value(row,'TORQUE')['value']['values'],[170,251,340])

    def test_typed_array_count_and_layout_span_rejected(self):
        raw,_=fixture();db=VehicleAttributes(raw);row=db.find('pvehicle','bmw')
        struct.pack_into('>H',db.bin,166,4)
        with self.assertRaises(ValueError):db.field_value(row,'TORQUE')
        db=VehicleAttributes(raw);db.classes[h('pvehicle')]['base_size']=20
        with self.assertRaises(ValueError):db.field_value(db.find('pvehicle','bmw'),'TORQUE')

if __name__=='__main__':unittest.main()
