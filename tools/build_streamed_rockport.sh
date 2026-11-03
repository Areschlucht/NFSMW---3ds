#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
exec bash "$project_dir/tools/build_rockport.sh" \
 TARGET=nfsmw-rockport-streamed BUILD=build-rockport-streamed \
 APP_TITLE='NFS MW streamed world diagnostic' \
 EXTRA_CFLAGS=-DNFS_STREAMED_WORLD \
 'CFILES=rockport_main.c nfs_scene.c driving_controller.c road_contact.c wheel_motion.c road_pose.c road_map.c world_visibility.c chase_camera.c world_vertex.c world_index.c mw_ui.c mw_color_grade.c streamed_world.c streamed_world_texture.c world_streaming.c world_streaming_scene.c mw_lod_select.c mw_gekko_math.c' "$@"
