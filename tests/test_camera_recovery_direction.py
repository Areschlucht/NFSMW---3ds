import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
class CameraDirectionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'),'Host C compiler unavailable')
    def test_original_direction_stage_contract(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='camera-direction-') as temporary:
            binary=Path(temporary)/'test'
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(root/'include'),str(root/'tests/test_camera_recovery_direction.c'),str(root/'source_bmw/mw_original_camera_direction.c'),str(root/'source_bmw/mw_gekko_math.c'),'-lm','-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)
