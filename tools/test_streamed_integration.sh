#!/usr/bin/env bash
# Host ASan/UBSan integration checks using private converted source assets.
set -euo pipefail
if [ "$#" -ne 6 ]; then
 echo 'Usage: test_streamed_integration.sh scene-directory metadata.wst collision.nwc road.nrd body.nfm scene.mwp' >&2
 exit 2
fi
cd -- "$(dirname -- "$0")/.."
stream_test_dir="$(mktemp -d /tmp/nfsmw-stream-tests.XXXXXX)"
trap 'rm -rf -- "$stream_test_dir"' EXIT
cc_bin="${CC:-cc}"
flags=(-std=c11 -O1 -g -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off
 -fsanitize=address,undefined -fno-omit-frame-pointer -no-pie -Iinclude -Itests/world_streaming_mock)
sources=(tests/world_streaming_mock/citro3d.c source_rockport/streamed_world.c
 source_rockport/streamed_world_texture.c source_rockport/streamed_world_pack.c
 source_bmw/mw_scene_pack.c source_bmw/world_streaming.c source_bmw/world_streaming_scene.c
 source_bmw/world_visibility.c source_bmw/mw_lod_select.c source_bmw/mw_gekko_math.c
 source_bmw/streamed_drive.c source_bmw/world_collision_runtime.c source_bmw/world_collision_query.c
 source_bmw/road_contact.c source_bmw/driving_controller.c source_bmw/chase_camera.c
 source_bmw/road_pose.c source_bmw/wheel_motion.c)
objects=()
for source in "${sources[@]}"; do
 object="$stream_test_dir/$(basename "${source%.c}").o"
 "$cc_bin" "${flags[@]}" -c "$source" -o "$object"
 objects+=("$object")
done
run_test(){
 local name="$1";shift
 "$cc_bin" "${flags[@]}" "tests/$name.c" "${objects[@]}" -lm -o "$stream_test_dir/$name"
 "$stream_test_dir/$name" "$@"
}
run_test test_world_streaming_scene
run_test test_streamed_world_runtime "$1" "$2"
run_test test_streamed_world_boot "$1" "$2"
run_test test_streamed_world_rollback "$1" "$2"
run_test test_road_pose
"$cc_bin" "${flags[@]}" tests/test_mw_ui_texture.c source_bmw/mw_ui_texture.c -o "$stream_test_dir/ui-texture"
"$stream_test_dir/ui-texture"
run_test test_driving_controller
run_test test_streamed_world_drive "$6" "$2" "$3" "$4" --pack
"$cc_bin" "${flags[@]}" tests/test_scene_normals.c source_bmw/nfs_scene.c -lm -o "$stream_test_dir/normals"
"$stream_test_dir/normals" "$5"
"$cc_bin" "${flags[@]}" tools/perf_scene_pack_test.c source_bmw/mw_scene_pack.c -o "$stream_test_dir/archive"
"$stream_test_dir/archive" "$6" "$1"
