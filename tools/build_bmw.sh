#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
exec env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
 docker --host=unix:///var/run/docker.sock run --rm --network none --user "$(id -u):$(id -g)" \
 --mount "type=bind,src=$project_dir,dst=/project" -w /project \
 devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5 \
 make -j2 TARGET=nfsmw-bmw-viewer BUILD=build-bmw SOURCES=source_bmw \
 'LIBS=-lcitro2d -lcitro3d -lctru -lm' APP_TITLE='NFS MW Menu Prototype v0.5' \
 APP_DESCRIPTION='Menus and recovered BMW garage' APP_AUTHOR='NFS MW 3DS research' "$@"
