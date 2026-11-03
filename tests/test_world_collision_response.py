import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class BodyResponseTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'),'host C compiler unavailable')
    def test_original_tangent_stages_and_threshold_model(self):
        with tempfile.TemporaryDirectory() as directory:
            executable=Path(directory)/'body-response'
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I'+str(ROOT/'include'),str(ROOT/'source_bmw/mw_body_collision.c'),str(ROOT/'source_bmw/mw_gekko_math.c'),str(ROOT/'tests/test_world_collision_response.c'),'-lm','-o',str(executable)],check=True)
            subprocess.run([str(executable)],check=True)
    @unittest.skipUnless(shutil.which('cc'),'host C compiler unavailable')
    def test_original_iterative_body_response(self):
        with tempfile.TemporaryDirectory() as directory:
            executable=Path(directory)/'body-core'
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I'+str(ROOT/'include'),str(ROOT/'source_bmw/mw_body_collision_response.c'),str(ROOT/'source_bmw/mw_body_collision.c'),str(ROOT/'source_bmw/mw_gekko_math.c'),str(ROOT/'tests/test_world_collision_body_core.c'),'-lm','-o',str(executable)],check=True)
            subprocess.run([str(executable)],check=True)
    @unittest.skipUnless(shutil.which('cc'),'host C compiler unavailable')
    def test_original_compound_shape_bounds_masks_and_capacity(self):
        with tempfile.TemporaryDirectory() as directory:
            executable=Path(directory)/'body-shapes'
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'include'),str(ROOT/'source_bmw/mw_body_collision_shapes.c'),str(ROOT/'tests/test_world_collision_shapes.c'),'-lm','-o',str(executable)],check=True)
            subprocess.run([str(executable)],check=True)
if __name__=='__main__':unittest.main()
