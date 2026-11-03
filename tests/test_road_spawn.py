import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from road_spawn import choose_spawn,RoadSampler


def road():
    return [[[-5,0,-100],[5,0,-100],[5,0,20]],[[-5,0,-100],[5,0,20],[-5,0,20]]]


class SpawnTests(unittest.TestCase):
    def test_original_centerline_and_supported_direction(self):
        network={'nodes':[[-50,0,0],[10,0,0]],'segments':[[0,1]]}
        point,heading,report=choose_spawn([3,.1,0],network,road())
        self.assertEqual(point,[0,0,0]);self.assertAlmostEqual(heading,3.141592653589793)
        self.assertEqual(report['forward_run_m'],20);self.assertEqual(report['reverse_run_m'],100)

    def test_missing_or_different_deck_is_rejected(self):
        network={'nodes':[[-50,10,0],[10,10,0]],'segments':[[0,1]]}
        with self.assertRaises(ValueError):choose_spawn([0,10,0],network,road())
        with self.assertRaises(ValueError):choose_spawn([100,0,0],network,road())

    def test_height_and_gap_stop(self):
        sampler=RoadSampler(road());self.assertEqual(sampler.height(0,0,0),0)
        self.assertIsNone(sampler.height(10,0,0));self.assertIsNone(sampler.height(0,0,10))
        self.assertEqual(sampler.run([0,0,0],0),20)


if __name__=='__main__':unittest.main()
