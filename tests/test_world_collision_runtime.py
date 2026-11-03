import hashlib
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from world_collision import packages
from world_collision_pack import pack
from test_world_collision import collision_fixture


def source_fixture():
    first=collision_fixture();first[183]=0;struct.pack_into('>H',first,280,71);struct.pack_into('>f',first,300,5)
    second=bytearray(first);struct.pack_into('<I',second,20,102);struct.pack_into('>3f',second,304,-110,-2,-200)
    stream=first+second+first
    relations=[dict(section_id=section,collision_id=p['id'],collision_offset=p['source_offset'],bytes=p['source_bytes'],sha256=hashlib.sha256(stream[p['source_offset']:p['source_offset']+p['source_bytes']]).hexdigest()) for section,p in zip((141,142,143),packages(stream))]
    return stream,dict(source_sha256=hashlib.sha256(stream).hexdigest(),relations=relations)


class RuntimeCollisionTests(unittest.TestCase):
    def test_pack_preserves_original_bytes_and_physical_aliases(self):
        stream,containment=source_fixture();raw,report=pack(stream,containment)
        self.assertEqual(len(report['packages']),2)
        self.assertEqual([a['package_index'] for a in report['associations']],[0,1,0])
        at=report['packages'][0]['offset'];asset=struct.unpack_from('<I',raw,at+16)[0]
        self.assertEqual(raw[at+16+32:at+16+96],stream[256:320])
        self.assertEqual(raw[at+asset:at+asset+128],stream[128:256])
        # Runtime data is reproducible and never replaces source material hashes.
        self.assertEqual(pack(stream,containment)[0],raw)

    def test_pack_rejects_missing_wrong_source_or_nonidentity_data(self):
        stream,containment=source_fixture()
        for edit in ('hash','missing','range'):
            broken=json.loads(json.dumps(containment))
            if edit=='hash':broken['source_sha256']='00'*32
            elif edit=='missing':broken['relations'].pop()
            else:broken['relations'][0]['bytes']-=1
            with self.assertRaises(ValueError):pack(stream,broken)
        broken=bytearray(stream);struct.pack_into('>f',broken,256,.5)
        containment['source_sha256']=hashlib.sha256(broken).hexdigest()
        containment['relations'][0]['sha256']=hashlib.sha256(broken[:320]).hexdigest()
        with self.assertRaises(ValueError):pack(broken,containment)

    @unittest.skipUnless(shutil.which('cc'),'host C compiler unavailable')
    def test_bounded_runtime_activation_queries_aliases_cache_and_corruption(self):
        stream,containment=source_fixture();raw,report=pack(stream,containment)
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory);good=directory/'good.nwc';good.write_bytes(raw)
            badcrc=bytearray(raw);badcrc[-1]^=1
            badpayload=bytearray(raw);start=report['packages'][0]['offset'];size=report['packages'][0]['bytes'];struct.pack_into('<I',badpayload,start+16,0)
            struct.pack_into('<I',badpayload,64+16,zlib.crc32(badpayload[start:start+size]))
            badheader=bytearray(raw);assoc=struct.unpack_from('<I',raw,20)[0];struct.pack_into('<I',badheader,assoc+4,512)
            paths=[good]
            for name,data in (('badcrc',badcrc),('badpayload',badpayload),('badheader',badheader)):
                path=directory/(name+'.nwc');path.write_bytes(data);paths.append(path)
            executable=directory/'runtime-test'
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'include'),str(ROOT/'source_bmw/world_collision_query.c'),str(ROOT/'source_bmw/mw_gekko_math.c'),str(ROOT/'source_bmw/world_collision_runtime.c'),str(ROOT/'tests/test_world_collision_runtime.c'),'-lm','-o',str(executable)],check=True)
            subprocess.run([str(executable),*[str(p) for p in paths]],check=True)


if __name__=='__main__':unittest.main()
