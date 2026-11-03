#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
image='devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5'
exec env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS \
    -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
    docker --host=unix:///var/run/docker.sock run --rm --network none \
    --user "$(id -u):$(id -g)" \
    --mount "type=bind,src=$project_dir,dst=/project" -w /project \
    "$image" make -j2 TARGET=nfsmw-brake-viewer \
    APP_TITLE='NFS MW GPU Viewer v0.3' \
    APP_DESCRIPTION='PICA200 brake model viewer' \
    APP_AUTHOR='NFS MW 3DS research' "$@"
