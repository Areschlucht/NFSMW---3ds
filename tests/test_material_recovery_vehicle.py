import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from material_recovery_vehicle import texture_hash, light_targets, sources, vinyl_request_path, report


class VehicleMaterialRecoveryTests(unittest.TestCase):
    def test_known_runtime_names_and_supplied_texture_keys(self):
        self.assertEqual(texture_hash('BMWM3GTRE46_SKIN1'), 0xde3ad3c6)
        self.assertEqual(texture_hash('HEADLIGHT_LEFT'), 0xa7e6ea53)
        self.assertEqual(texture_hash('TEXTURE_NAME'), 0x10c98090)
        self.assertEqual(texture_hash('BMWM3GTRE46_KIT00_HEADLIGHT_ON'), 0xe626da6d)
        self.assertEqual(texture_hash('BMWM3GTRE46_KIT00_BRAKELIGHT_OFF'), 0x051ae6de)
        self.assertNotEqual(texture_hash('headlight_left'), texture_hash('HEADLIGHT_LEFT'))

    def test_seeded_hash_is_original_concatenation(self):
        self.assertEqual(texture_hash('_GLASS_ON', texture_hash('BMWM3GTRE46_KIT00_HEADLIGHT')), 0xea977c66)

    def test_headlight_on_and_actual_window_target_override(self):
        result = light_targets('BMWM3GTRE46', window_front_target=0x12345678)
        self.assertEqual(result['HEADLIGHT_LEFT'], 0xe626da6d)
        self.assertEqual(result['HEADLIGHT_RIGHT'], 0xe626da6d)
        self.assertEqual(result['HEADLIGHT_GLASS_LEFT'], 0x12345678)
        self.assertEqual(result['HEADLIGHT_GLASS_RIGHT'], 0x12345678)

    def test_brake_suppression_and_side_only_override(self):
        result = light_targets('BMWM3GTRE46', window_front_target=0,
                               flags_1608=8|16|32, flags_160c=16)
        self.assertEqual(result['BRAKELIGHT_LEFT'], 0x938c73a0)
        self.assertEqual(result['BRAKELIGHT_RIGHT'], 0x051ae6de)
        self.assertEqual(result['BRAKELIGHT_CENTRE'], 0x938c73a0)
        forced = light_targets('BMWM3GTRE46', window_front_target=0, force_side_lights=1)
        self.assertEqual(forced['BRAKELIGHT_LEFT'], 0x938c73a0)
        self.assertEqual(forced['BRAKELIGHT_RIGHT'], 0x938c73a0)
        self.assertEqual(forced['BRAKELIGHT_CENTRE'], 0x051ae6de)

    def test_part_texture_name_override_and_zero_fallback(self):
        head, _ = sources('BMWM3GTRE46', headlight_seed=texture_hash('CUSTOM_HEAD'))
        self.assertEqual(head['_ON'], texture_hash('CUSTOM_HEAD_ON'))
        self.assertEqual(sources('BMWM3GTRE46', 0, 0), sources('BMWM3GTRE46'))

    def test_invalid_words_and_names(self):
        for text in ('BAD\0NAME', '☃'):
            with self.assertRaises(ValueError):texture_hash(text)
        with self.assertRaises(ValueError):texture_hash('NAME', -1)
        with self.assertRaises(ValueError):light_targets('BMWM3GTRE46', window_front_target=1<<32)

    def test_original_vinyl_loader_branch(self):
        self.assertIsNone(vinyl_request_path('BMWM3GTRE46', 0, 1))
        self.assertEqual(vinyl_request_path('BMWM3GTRE46', 1), r'CARS\BMWM3GTRE46\VINYLS.BIN')
        self.assertEqual(vinyl_request_path('BMWM3GTRE46', 2), r'CARS\BMWM3GTRE46\PREVINYL.BIN')
        self.assertEqual(vinyl_request_path('BMWM3GTRE46', 1, 1), r'CARS\BMWM3GTRE46\PREVINYL.BIN')
        self.assertEqual(vinyl_request_path('BMWM3GTRE46', 255), r'CARS\BMWM3GTRE46\VINYLS.BIN')
        with self.assertRaises(ValueError):vinyl_request_path('BMWM3GTRE46', 256)

    def test_version_specific_report_rejects_other_executable(self):
        class Other:
            data = b'not the pinned USA DOL'
        with self.assertRaises(ValueError):report(Other())


if __name__ == '__main__':
    unittest.main()
