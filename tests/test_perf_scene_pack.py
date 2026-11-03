"""Meaningful format/failure gates for optional immutable scene archives."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from perf_scene_pack import pack

class ScenePackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='mw-pack-tests-');cls.base=Path(cls.temp.name);cls.binary=cls.base/'native'
        subprocess.run(['cc','-std=c11','-O2','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie','-I'+str(ROOT/'include'),str(ROOT/'tools/perf_scene_pack_test.c'),str(ROOT/'source_bmw/mw_scene_pack.c'),'-o',str(cls.binary)],check=True)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=self.base);self.dir=Path(self.tmp.name);self.scene=self.dir/'scene';self.scene.mkdir()
        manifest={'source_sha256':'11'*32,'models':{},'sections':[],'textures':{}}
        entries=[(1,12,None,129),(1,4,None,128),(2,101,None,500),(2,2,None,1),(3,8,'22'*32,256),(3,8,'12'*32,257)]
        for kind,identifier,identity,size in entries:
            path=(f'models/{identifier:08x}.wsm' if kind==1 else f'sections/{identifier}.wsi' if kind==2 else f'textures/{identifier:08x}-{identity}.wtx')
            data=bytes((i*17+kind+identifier)&255 for i in range(size));file=self.scene/path;file.parent.mkdir(exist_ok=True);file.write_bytes(data)
            row={'path':path,'bytes':size,'sha256':hashlib.sha256(data).hexdigest()}
            if kind==1:manifest['models'][str(identifier)]=row
            elif kind==2:manifest['sections'].append(row)
            else:manifest['textures'][identity]=row
        self.manifest=manifest;(self.scene/'manifest.json').write_text(json.dumps(manifest));self.archive=self.dir/'scene.mwp';pack(self.scene,self.archive)
    def tearDown(self):self.tmp.cleanup()
    def invoke(self,*args):subprocess.run([str(self.binary),*map(str,args)],check=True,capture_output=True)
    def mutated(self,name,mutation,fix_index=False,fix_header=False):
        data=bytearray(self.archive.read_bytes());mutation(data)
        if fix_index:
            count=struct.unpack_from('<I',data,16)[0];struct.pack_into('<I',data,20,zlib.crc32(data[128:128+count*64]));fix_header=True
        if fix_header:
            struct.pack_into('<I',data,96,0);struct.pack_into('<I',data,96,zlib.crc32(data[:128]))
        path=self.dir/name;path.write_bytes(data);return path
    def test_exact_and_deterministic(self):
        self.invoke(self.archive,self.scene);other=self.dir/'other.mwp';pack(self.scene,other);self.assertEqual(self.archive.read_bytes(),other.read_bytes())
    def test_explicit_boot_provider_bank_included(self):
        data=b'boot-provider-bank';path=self.scene/'sections/0.wsi';path.write_bytes(data)
        self.manifest['global_banks']=[{'path':'sections/0.wsi','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}]
        (self.scene/'manifest.json').write_text(json.dumps(self.manifest))
        output=self.dir/'boot.mwp';report=pack(self.scene,output)
        self.assertEqual(report['kind_counts']['2'],3)
        self.invoke(output,self.scene)
    def test_refuse_overwrite_and_duplicate_key(self):
        with self.assertRaises(FileExistsError):pack(self.scene,self.archive)
        self.manifest['sections'].append(self.manifest['sections'][0]);(self.scene/'manifest.json').write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError,'Duplicate'):pack(self.scene,self.dir/'duplicate.mwp')
    def test_changed_source_rejected_and_partial_removed(self):
        path=self.scene/'models/0000000c.wsm';path.write_bytes(bytes(path.stat().st_size));output=self.dir/'bad.mwp'
        with self.assertRaisesRegex(ValueError,'SHA'):pack(self.scene,output)
        self.assertFalse(output.exists())
    def test_header_index_crc_and_truncation(self):
        for name,mut in [('header',lambda d:d.__setitem__(32,d[32]^1)),('index',lambda d:d.__setitem__(136,d[136]^1)),('truncated',lambda d:d.__delitem__(slice(-1,None)))]:
            self.invoke('--reject-open',self.mutated(name,mut))
    def test_duplicate_sorted_and_range_checks_after_valid_crc(self):
        mutations=[('duplicate',lambda d:d.__setitem__(slice(192,232),d[128:168])),
                   ('unsorted',lambda d:d.__setitem__(slice(128,192),d[192:256])),
                   ('offset',lambda d:struct.pack_into('<I',d,168,0xfffffff0)),
                   ('size',lambda d:struct.pack_into('<I',d,172,0xffffffff)),
                   ('reserved',lambda d:d.__setitem__(180,1)),
                   ('wrong_identity',lambda d:d.__setitem__(136,1)),
                   ('kind',lambda d:struct.pack_into('<I',d,128,4))]
        for name,mut in mutations:self.invoke('--reject-open',self.mutated(name,mut,fix_index=True))
    def test_lazy_payload_crc(self):
        offset=struct.unpack_from('<I',self.archive.read_bytes(),168)[0]
        bad=self.mutated('payload',lambda d:d.__setitem__(offset,d[offset]^1));self.invoke('--reject-read',bad)

if __name__=='__main__':unittest.main()
