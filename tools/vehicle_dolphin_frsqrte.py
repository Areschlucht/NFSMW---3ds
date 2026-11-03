#!/usr/bin/env python3
"""Offline adapter to checksum-pinned Dolphin reciprocal-square-root reference.

Builds the actual external GPL-2.0-or-later reference sources in a temporary
host-only library. No Dolphin source or lookup data is copied into this tool
or into the 3DS executable. Caller supplies the downloaded reference directory.
This is emulator reference evidence, not a replacement for hardware validation.
"""
import ctypes
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

COMMIT='86d554802d7560acf12b5c5a2b3acb344069b5ce'
SOURCES={
 'FloatUtils.cpp':'e7bcd6a48701a361a84a9c0dfbf2ddb0c5c5219a1370838c05f99a5e8dff9dbb',
 'FloatUtils.h':'8aad8c06eac7e14ac2876ddd56edc0562d28cd8c906ca6bfd9c72808810dbbe5',
 'CommonTypes.h':'b714ae37337b4f9cd6e1863073bdd92fda8648e606c91657b104fdc856199b94',
}

class DolphinFrsqrteReference:
    def __init__(self,directory):
        directory=Path(directory)
        for name,expected in SOURCES.items():
            if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=expected:raise ValueError('Unexpected Dolphin reference source: '+name)
        self.temporary=tempfile.TemporaryDirectory(prefix='mw-offline-dolphin-frsqrte-')
        root=Path(self.temporary.name);common=root/'Common';common.mkdir()
        for name in SOURCES:shutil.copyfile(directory/name,common/name)
        wrapper=root/'adapter.cpp'
        wrapper.write_text('#include "Common/FloatUtils.h"\nextern "C" double mw_offline_dolphin_frsqrte(double x){return Common::ApproximateReciprocalSquareRoot(x);}\n')
        library=root/'reference.so'
        subprocess.run(['c++','-std=c++20','-O2','-fno-fast-math','-shared','-fPIC','-I'+str(root),str(common/'FloatUtils.cpp'),str(wrapper),'-o',str(library)],check=True)
        self.library=ctypes.CDLL(str(library));self.function=self.library.mw_offline_dolphin_frsqrte
        self.function.argtypes=[ctypes.c_double];self.function.restype=ctypes.c_double

    def estimate(self,value):return self.function(value)
    def close(self):self.temporary.cleanup()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
