#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
exec bash "$project_dir/tools/build_rockport.sh" \
 TARGET=nfsmw-rockport-streamed BUILD=build-rockport-streamed \
 APP_TITLE='NFS MW streamed world diagnostic' \
 'EXTRA_CFLAGS=-DNFS_STREAMED_WORLD -ffp-contract=off' \
 'CFILES=rockport_main.c mw_opening_actors.c mw_race_ai.c mw_pursuit.c mw_career.c mw_playable_race.c mw_cinema.c mw_movie.c mw_movie_audio.c mw_story_audio.c mw_story_speech.c mw_story_services.c mw_nis.c mw_opening_cinema.c mw_nis_director.c mw_nis_actor.c mw_nis_actions.c mw_nis_pose.c mw_chase_source.c mw_original_camera_direction.c mw_original_camera_cubic.c mw_original_camera_tuning.c mw_original_camera_profile.c vehicle_index.c mw_vehicle_catalog.c mw_traffic.c mw_menu_layout.c mw_menu_icons.c mw_destination_icons.c mw_free_roam.c mw_frontend_top.c mw_world_state.c mw_alias.c mw_event_catalog.c mw_race_progress.c mw_story_tutorial.c mw_race_session.c nfs_scene.c driving_controller.c road_contact.c wheel_motion.c road_pose.c road_map.c world_visibility.c chase_camera.c world_vertex.c world_index.c mw_ui.c mw_ui_texture.c mw_color_grade.c streamed_world.c streamed_world_texture.c world_streaming.c world_streaming_scene.c mw_lod_select.c mw_gekko_math.c streamed_drive.c world_collision_runtime.c world_collision_query.c mw_scene_pack.c streamed_world_pack.c' "$@"
