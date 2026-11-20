"""Authored DWARF1 fixture: nesting, terminators, repeated names and references."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from mw_debug_info import DebugInfo

def record(tag,attrs):
    return struct.pack('>IH',6+len(attrs),tag)+attrs

def scalar(attr,value):return struct.pack('>HI',attr,value)
def text(name):return b'\0\x38'+name.encode()+b'\0'

class DebugInfoTest(unittest.TestCase):
    def fixture(self,raw):
        # ELF32 BE with only a string section and .debug section.
        names=b'\0.shstrtab\0.debug\0';out=bytearray(0x100+len(raw))
        out[:6]=b'\x7fELF\x01\x02';struct.pack_into('>I',out,32,52)
        struct.pack_into('>HHH',out,46,40,3,1)
        struct.pack_into('>10I',out,92,1,3,0,0,172,len(names),0,0,1,0)
        struct.pack_into('>10I',out,132,11,1,0,0,256,len(raw),0,0,1,0)
        out[172:172+len(names)]=names;out[256:]=raw
        path=Path(self.tmp.name)/'fixture.elf';path.write_bytes(out);return DebugInfo(path)
    def setUp(self):self.tmp=tempfile.TemporaryDirectory()
    def tearDown(self):self.tmp.cleanup()
    def test_struct_members_reference_and_padding(self):
        # Parent ends after member and a four-byte DWARF1 padding record.
        child=record(13,text('rpm')+scalar(0x72,0)+b'\0\x23\0\x06\x04\0\0\0\x10\x07')
        parent=record(19,scalar(0x12,0)+text('Engine')+scalar(0xb6,32))
        end=len(parent)+len(child)+4
        parent=record(19,scalar(0x12,end)+text('Engine')+scalar(0xb6,32))
        with self.fixture(parent+child+struct.pack('>I',4)) as db:
            die=db.find('Engine')[0];self.assertEqual(die.size,32)
            member=db.members(die)[0];self.assertEqual((member['name'],member['offset'],member['type']),('rpm',16,0))
    def test_enum_signed_storage_and_repeat_names(self):
        values=struct.pack('>I',0xffffffff)+b'Invalid\0'+struct.pack('>I',6)+b'Player\0'
        entry=record(4,text('Kind')+struct.pack('>HI',0xf4,len(values))+values)
        with self.fixture(entry+entry) as db:
            self.assertEqual(len(db.find('Kind',tags={4})),2)
            self.assertEqual(db.enum_values(db.find('Kind')[0]),[('Invalid',0xffffffff),('Player',6)])
    def test_truncated_attribute_rejected(self):
        with self.fixture(record(19,b'\0\x38missing-terminator')) as db:
            with self.assertRaises(ValueError):db.die(0)

if __name__=='__main__':unittest.main()
