import subprocess
import tempfile
import unittest
from pathlib import Path

class PortableScalarTests(unittest.TestCase):
    def test_original_scalar_regressions(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='mw-scalar-tests-') as directory:
            output=Path(directory)/'scalars'
            sources=['source_bmw/mw_physics_engine.c','source_bmw/mw_physics_tires.c','source_bmw/mw_physics_brakes.c','source_bmw/mw_physics_drivetrain.c','source_bmw/mw_physics_grip.c','source_bmw/mw_physics_lateral.c','source_bmw/mw_physics_friction.c','source_bmw/mw_physics_contact.c','source_bmw/mw_physics_contact_scale.c','source_bmw/mw_physics_contact_frame.c','source_bmw/mw_physics_contact_geometry.c','source_bmw/mw_physics_ground.c','source_bmw/mw_physics_suspension.c','source_bmw/mw_gekko_math.c','tests/test_mw_physics_scalars.c']
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-I'+str(root/'include'),*[str(root/s) for s in sources],'-lm','-o',str(output)],check=True)
            subprocess.run([str(output)],check=True)

if __name__=='__main__':unittest.main()
