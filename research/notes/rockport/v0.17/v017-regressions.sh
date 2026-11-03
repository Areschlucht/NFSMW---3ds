#!/bin/bash
set -euo pipefail
sources='source_bmw/nfs_scene.c source_bmw/driving_controller.c source_bmw/road_contact.c source_bmw/wheel_motion.c source_bmw/road_pose.c source_bmw/road_map.c source_bmw/world_visibility.c source_bmw/chase_camera.c source_bmw/world_vertex.c source_bmw/world_index.c'
world=/workspace/port-research/rockport/scene-v0.15/road.nrd
car=/workspace/port-research/bmw/scene-v0.9
for name in driving_controller chase_camera world_visibility road_grid road_pose road_map wheel_motion; do
 cc -std=c11 -O2 -Wall -Wextra -Werror -fsanitize=address,undefined -Iinclude "tests/test_$name.c" $sources -lm -o "/tmp/v017-$name"
 case "$name" in
 road_grid) "/tmp/v017-$name" "$world" ;;
 road_pose) "/tmp/v017-$name" "$world" "$car/wheels.nwa" "$car/body.nfm" ;;
 road_map) "/tmp/v017-$name" "$world" /workspace/port-research/rockport/v0.17/map-reference.ppm ;;
 wheel_motion) "/tmp/v017-$name" "$car/wheels.nwa" "$car/body.nfm" ;;
 *) "/tmp/v017-$name" ;;
 esac
done
