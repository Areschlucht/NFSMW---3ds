#!/usr/bin/env bash
set -euo pipefail
stream_project="$(cd -- "$(dirname -- "$0")/.." && pwd)"
stream_audit="${1:-/workspace/port-research/world-streaming/sdk-check}"
mkdir -p "$stream_audit"
exec env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
 docker --host=unix:///var/run/docker.sock run --rm --network none \
 --mount "type=bind,src=$stream_project,dst=/project,readonly" \
 --mount "type=bind,src=$stream_audit,dst=/audit" \
 devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5 \
 bash -euc '
stream_cc=/opt/devkitpro/devkitARM/bin/arm-none-eabi-gcc
stream_flags="-std=gnu11 -O2 -g -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off -march=armv6k -mtune=mpcore -mfloat-abi=hard -mtp=soft -D__3DS__ -I/project/include -I/opt/devkitpro/libctru/include"
for stream_source in source_rockport/streamed_world.c source_rockport/streamed_world_texture.c source_bmw/world_streaming.c source_bmw/world_streaming_scene.c source_bmw/world_visibility.c source_bmw/mw_lod_select.c source_bmw/mw_gekko_math.c; do
 stream_name="${stream_source##*/}"
 "$stream_cc" $stream_flags -c "/project/$stream_source" -o "/audit/${stream_name%.c}.o"
done
printf "%s\n" "int main(void){return 0;}" > /audit/link_probe.c
"$stream_cc" $stream_flags -c /audit/link_probe.c -o /audit/link_probe.o
"$stream_cc" -march=armv6k -mtune=mpcore -mfloat-abi=hard -mtp=soft -specs=3dsx.specs \
 /audit/link_probe.o /audit/streamed_world.o /audit/streamed_world_texture.o \
 /audit/world_streaming.o /audit/world_streaming_scene.o /audit/world_visibility.o \
 /audit/mw_lod_select.o /audit/mw_gekko_math.o \
 -L/opt/devkitpro/libctru/lib -lcitro3d -lctru -lm -Wl,-Map,/audit/link_probe.map -o /audit/link_probe.elf
/opt/devkitpro/devkitARM/bin/arm-none-eabi-size /audit/streamed_world.o /audit/link_probe.elf
'
