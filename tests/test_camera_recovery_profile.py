import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

class CameraProfileTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'),'Host C compiler unavailable')
    def test_original_profile_cache_contract(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='camera-profile-') as temporary:
            binary=Path(temporary)/'test'
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(root/'include'),str(root/'tests/test_camera_recovery_profile.c'),str(root/'source_bmw/mw_original_camera_profile.c'),'-lm','-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)
