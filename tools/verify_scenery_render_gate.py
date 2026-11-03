#!/usr/bin/env python3
"""Compare the renderer's portable flag gate with bounded original PPC execution."""
import argparse
import ctypes
import json
from pathlib import Path
import subprocess
import tempfile
from scenery_flag_reference import Reference

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dol',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    ref=Reference(a.dol.read_bytes());count=0
    with tempfile.TemporaryDirectory(prefix='mw-render-gate-') as directory:
        library=Path(directory)/'gate.so'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-shared','-fPIC',
                        '-I'+str(root/'include'),str(root/'source_bmw/mw_lod_select.c'),
                        '-lm','-o',str(library)],check=True)
        lib=ctypes.CDLL(str(library));gate=lib.mw_lod_instance_visible
        gate.argtypes=[ctypes.c_uint32,ctypes.c_uint32];gate.restype=ctypes.c_bool
        for high in (0,0x00800000,0xffff0000):
            for flags in range(256):
                for context in (0,0x10,0x20,0x60,0xff,0x1810):
                    assert gate(high|flags,context)==(not ref.render(high|flags,context))
                    count+=1
    result={'original_ppc_matches':count,'default_prototype_context':0,
            'limits':['Original normal contexts include0x10, but production prototype retains0 until collision/event ownership is recovered',
                      'This comparison checks the consumer, not the full scenery activation state machine']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
