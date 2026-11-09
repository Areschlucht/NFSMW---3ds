#!/usr/bin/env python3
"""Host-compile only the portable selector and compare with original PPC."""
import argparse
import ctypes
import json
from pathlib import Path
import subprocess
import tempfile
from story_flow_reference import Original

class Decision(ctypes.Structure):
    _fields_=[('movie_stem',ctypes.c_char_p),('profile_flags',ctypes.c_uint32)]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();reference=Original(a.dol.read_bytes());root=Path(__file__).resolve().parents[1];cases=0
    with tempfile.TemporaryDirectory(prefix='mw-story-host-') as temporary:
        library=Path(temporary)/'selector.so'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-shared','-fPIC',
            '-I'+str(root/'include'),str(root/'source_bmw/mw_story_tutorial.c'),'-o',str(library)],check=True)
        function=ctypes.CDLL(str(library)).mw_story_tutorial_select
        function.argtypes=[ctypes.c_int32,ctypes.c_uint32,ctypes.POINTER(Decision)];function.restype=ctypes.c_bool
        assert not function(2,0,None)
        for event in range(-2,13):
            for bits in range(8):
                low=((bits&1)*0x40)|((bits&2)*0x40)|((bits&4)*0x40)
                for unrelated in (0,1,0xfffffe3f,0x80000000):
                    flags=low|unrelated;address,expected_flags=reference.tutorial(event,flags)
                    out=Decision();assert function(event,flags,ctypes.byref(out))
                    expected=reference.image.c_string(address).encode() if address else None
                    assert out.movie_stem==expected and out.profile_flags==expected_flags
                    if expected:
                        again=Decision();assert function(event,out.profile_flags,ctypes.byref(again))
                        assert again.movie_stem is None and again.profile_flags==expected_flags
                    cases+=1
    result={'native_original_ppc_matches':cases,'limits':['Host compilation of a portable component only; no SDK/app build',
        'Original outer player/manager/event preconditions are caller responsibilities',
        'No movie player or career transition is implemented by this selector']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
