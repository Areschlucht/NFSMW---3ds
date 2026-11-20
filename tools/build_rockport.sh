#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
exec env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
 docker --host=unix:///var/run/docker.sock run --rm --network none --user "$(id -u):$(id -g)" \
 --mount "type=bind,src=$project_dir,dst=/project" -w /project \
 devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5 \
 make -j2 TARGET=nfsmw-rockport BUILD=build-rockport 'SOURCES=source_rockport source_bmw' \
 'CFILES=rockport_main.c mw_opening_actors.c mw_race_ai.c mw_pursuit.c mw_career.c mw_playable_race.c mw_cinema.c mw_movie.c mw_movie_audio.c mw_story_audio.c mw_story_speech.c mw_story_services.c mw_nis.c mw_opening_cinema.c mw_nis_director.c mw_nis_actor.c mw_nis_actions.c mw_nis_pose.c mw_chase_source.c mw_original_camera_direction.c mw_original_camera_cubic.c mw_original_camera_tuning.c mw_original_camera_profile.c vehicle_index.c mw_vehicle_catalog.c mw_traffic.c mw_menu_layout.c mw_menu_icons.c mw_destination_icons.c mw_free_roam.c mw_frontend_top.c mw_world_state.c mw_alias.c mw_event_catalog.c mw_race_progress.c mw_story_tutorial.c mw_race_session.c nfs_scene.c driving_controller.c road_contact.c wheel_motion.c road_pose.c road_map.c world_visibility.c chase_camera.c world_vertex.c world_index.c mw_ui.c mw_ui_texture.c mw_color_grade.c' \
 'PICAFILES=rockport_vshader.v.pica world_vshader.v.pica' \
 'LIBS=-lcitro2d -lcitro3d -lctru -ljpeg -lm' APP_TITLE='NFS MW Rockport Prototype v0.18 dev' \
 APP_DESCRIPTION='Original Colonial roads and scenery' APP_AUTHOR='NFS MW 3DS research' "$@"
