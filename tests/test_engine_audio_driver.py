#!/usr/bin/env python3
"""Run the native engine-audio composition contract against six private NVRs.

This compares the wrapper with the already source-compared engine core. It is
not a new original-PPC/whole-car trajectory comparison or an audio listening test.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile

MODULES = (
    'mw_engine_audio_driver mw_vehicle_runtime mw_vehicle_dynamics '
    'mw_original_vehicle_mechanical mw_original_power mw_original_rigid_body '
    'mw_physics_transmission_engine mw_physics_transmission '
    'mw_physics_transmission_policy mw_physics_transmission_auto '
    'mw_physics_transmission_nos mw_physics_engine mw_original_player_input '
    'mw_physics_grip mw_physics_brakes mw_physics_tires mw_physics_ground '
    'mw_physics_suspension mw_physics_contact_frame mw_physics_contact_geometry '
    'mw_physics_contact_scale mw_physics_contact mw_physics_lateral '
    'mw_physics_friction mw_physics_transmission_distribution mw_gekko_math '
    'mw_story_services'
).split()
PROFILES = ('bmwm3gtre46', 'm3gtre46careerstart', 'cobaltss', 'gti', 'is300', 'punto')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profiles', type=Path)
    parser.add_argument('--cc', default='cc')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='nfsmw-engine-audio-') as folder:
        executable = Path(folder)/'test'
        subprocess.run([
            args.cc, '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
            '-pedantic', '-fno-fast-math', '-ffp-contract=off',
            '-ffunction-sections', '-fdata-sections', '-fsanitize=address,undefined',
            '-fno-omit-frame-pointer', '-no-pie', '-I'+str(root/'include'),
            str(root/'tests/test_engine_audio_driver.c'),
            *[str(root/'source_bmw'/(name+'.c')) for name in MODULES],
            '-Wl,--gc-sections', '-lm', '-o', str(executable),
        ], check=True)
        for name in PROFILES:
            print(name, flush=True)
            subprocess.run([str(executable), str(args.profiles/(name+'.nvr'))], check=True)


if __name__ == '__main__':
    main()
