import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from fit_bmw_wheels import fit_circle,fit_wheels


class WheelFitTests(unittest.TestCase):
    def test_rims_face_outward_and_radius_ignores_quad_diagonal(self):
        angles=np.linspace(.2,np.pi-.2,50);points=[]
        for side in (1,-1):
            for x in (1.5,-1.2):
                points.extend((x+.4*np.cos(a),side*.9,.2+.4*np.sin(a)) for a in angles)
        tire={'positions':[(-.3,0,-.3),(.3,0,.3),(-.3,.3,-.3),(.3,.3,.3)]}
        wheels,_=fit_wheels({'positions':points},tire)
        for wheel,side in zip(wheels,(1,1,-1,-1)):
            self.assertAlmostEqual(wheel['wheel_radius'],.3)
            # First two points are the rim, last two are the inboard back face.
            self.assertGreater(side*wheel['positions'][0][1],side*wheel['positions'][2][1])
            self.assertAlmostEqual(side*wheel['positions'][0][1],.89)

    def test_known_arch_with_outliers(self):
        angles=np.linspace(.12,np.pi-.12,40)
        points=np.column_stack((1.5+.4*np.cos(angles),.2+.4*np.sin(angles)))
        points=np.vstack((points,[[1.1,.69],[1.8,.3],[1.25,.28],[1.71,.68]]))
        center,radius,selected,rms=fit_circle(points,1)
        np.testing.assert_allclose(center,[1.5,.2],atol=1e-8)
        self.assertAlmostEqual(radius,.4);self.assertLess(rms,1e-8)
        self.assertEqual(sum(selected),40)

    def test_insufficient_or_nonfinite(self):
        for points in ([],[[1,2]]*8,[[float('nan'),1]]*20):
            with self.assertRaises(ValueError):fit_circle(points,1)

    def test_no_supported_circle(self):
        points=np.column_stack((np.linspace(1,2,30),np.ones(30)*.3))
        with self.assertRaises(ValueError):fit_circle(points,1)


if __name__=='__main__':unittest.main()
