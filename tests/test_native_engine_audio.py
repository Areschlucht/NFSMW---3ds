#!/usr/bin/env python3
"""ASan/UBSan integration of native audio adapter with real private NWC assets."""
import argparse
from pathlib import Path
import subprocess
import tempfile
from test_engine_audio_driver import MODULES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('--cc', default='cc')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    modules = MODULES+['mw_native_engine_audio', 'nfs_scene', 'road_contact',
                      'driving_controller', 'wheel_motion', 'streamed_drive',
                      'world_collision_runtime', 'world_collision_query', 'mw_world_state']
    with tempfile.TemporaryDirectory(prefix='nfsmw-native-engine-audio-') as folder:
        executable = Path(folder)/'test'
        # Existing NWC code uses pre-C23 qualified array conversions accepted by
        # the project compiler; owned adapter separately passes -pedantic.
        subprocess.run([
            args.cc, '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
            '-fno-fast-math', '-ffp-contract=off', '-ffunction-sections',
            '-fdata-sections', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
            '-no-pie', '-I'+str(root/'include'), str(root/'tests/test_native_engine_audio.c'),
            *[str(root/'source_bmw'/(name+'.c')) for name in modules],
            '-Wl,--gc-sections', '-lm', '-o', str(executable),
        ], check=True)
        subprocess.run([str(executable), str(args.profile), str(args.runtime)], check=True)


if __name__ == '__main__':
    main()
