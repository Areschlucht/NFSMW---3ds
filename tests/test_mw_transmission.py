"""Synthetic portable drivetrain regression checks; original data not required."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class TransmissionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'),'host C compiler unavailable')
    def test_portable_state_and_curve_boundaries(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='mw-transmission-test-') as temporary:
            executable=Path(temporary)/'test'
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
                '-fno-fast-math','-ffp-contract=off','-I'+str(root/'include'),
                str(root/'tests/test_mw_transmission.c'),
                str(root/'source_bmw/mw_physics_transmission.c'),
                str(root/'source_bmw/mw_physics_transmission_engine.c'),
                str(root/'source_bmw/mw_physics_transmission_nos.c'),
                str(root/'source_bmw/mw_physics_transmission_auto.c'),
                str(root/'source_bmw/mw_physics_transmission_policy.c'),
                str(root/'source_bmw/mw_physics_transmission_distribution.c'),
                str(root/'source_bmw/mw_physics_engine.c'),'-lm','-o',str(executable)],check=True)
            subprocess.run([str(executable)],check=True)


if __name__=='__main__':unittest.main()
