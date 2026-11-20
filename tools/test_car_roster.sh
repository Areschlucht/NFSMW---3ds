#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then echo 'Usage: test_car_roster.sh private-native-roster-directory' >&2; exit 2; fi
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
roster_dir="$(cd -- "$1" && pwd)"
work="$(mktemp -d /tmp/nfsmw-car-roster.XXXXXXXX)"
trap 'rm -rf -- "$work"' EXIT
flags=(-std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer -no-pie -I"$project_dir/include")
"${CC:-cc}" "${flags[@]}" "$project_dir/tests/test_car_roster.c" "$project_dir/source_bmw/mw_vehicle_catalog.c" "$project_dir/source_bmw/nfs_scene.c" "$project_dir/source_bmw/wheel_motion.c" -lm -o "$work/roster"
"$work/roster" "$roster_dir"
"${CC:-cc}" "${flags[@]}" "$project_dir/tests/test_vehicle_index.c" "$project_dir/source_bmw/vehicle_index.c" "$project_dir/source_bmw/nfs_scene.c" "$project_dir/source_bmw/wheel_motion.c" -lm -o "$work/index"
mapfile -t car_dirs < <(python3 - "$roster_dir" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
for car in json.loads((p/'catalog.json').read_text())['cars']:print(p/car['id'])
PY
)
"$work/index" "${car_dirs[@]}"
