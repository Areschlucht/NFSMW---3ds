#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
if [ "$#" -lt 5 ] || [ "$#" -gt 6 ]; then
 echo 'Usage: test_free_roam.sh world.mwp world-streaming.bin world.nwc road.nrd exploration.nws [free-roam.nfd for region test]' >&2
 exit 2
fi
work="$(mktemp -d /tmp/nfsmw-free-roam.XXXXXX)"
trap 'rm -rf -- "$work"' EXIT
cc -std=c11 -O1 -g -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off \
 -fsanitize=address,undefined -fno-omit-frame-pointer -no-pie -Iinclude -Itests/world_streaming_mock \
 ${FREE_ROAM_TEST_SOURCE:-tests/test_free_roam_drive.c} tests/world_streaming_mock/citro3d.c source_rockport/streamed_world.c \
 source_rockport/streamed_world_texture.c source_rockport/streamed_world_pack.c \
 source_bmw/mw_scene_pack.c source_bmw/world_streaming.c source_bmw/world_streaming_scene.c \
 source_bmw/world_visibility.c source_bmw/mw_lod_select.c source_bmw/mw_gekko_math.c \
 source_bmw/streamed_drive.c source_bmw/world_collision_runtime.c source_bmw/world_collision_query.c \
 source_bmw/road_contact.c source_bmw/driving_controller.c source_bmw/chase_camera.c source_bmw/mw_world_state.c source_bmw/mw_free_roam.c \
 -lm -o "$work/drive"
if [ "$#" -eq 6 ]; then
 "$work/drive" "$1" "$2" "$3" "$5" "$6"
else
 "$work/drive" "$@"
fi
