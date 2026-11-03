import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
class CameraTuningTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'),'Host C compiler unavailable')
    def test_padding_aliasing_and_transactional_failure(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='camera-tuning-') as temporary:
            binary=Path(temporary)/'test'
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I'+str(root/'include'),str(root/'tests/test_camera_recovery_tuning.c'),str(root/'source_bmw/mw_original_camera_tuning.c'),'-lm','-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)
