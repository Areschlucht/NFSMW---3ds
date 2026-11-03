#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
exec env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
 docker --host=unix:///var/run/docker.sock run --rm --network none --user "$(id -u):$(id -g)" \
 --mount "type=bind,src=$project_dir,dst=/project" -w /project \
 devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5 \
 make -j2 TARGET=nfsmw-rockport BUILD=build-rockport 'SOURCES=source_rockport source_bmw' \
 'CFILES=rockport_main.c nfs_scene.c driving_controller.c road_contact.c wheel_motion.c road_pose.c road_map.c world_visibility.c chase_camera.c world_vertex.c world_index.c mw_ui.c mw_color_grade.c' \
 'PICAFILES=rockport_vshader.v.pica world_vshader.v.pica' \
 'LIBS=-lcitro2d -lcitro3d -lctru -lm' APP_TITLE='NFS MW Rockport Prototype v0.18 dev' \
 APP_DESCRIPTION='Original Colonial roads and scenery' APP_AUTHOR='NFS MW 3DS research' "$@"
