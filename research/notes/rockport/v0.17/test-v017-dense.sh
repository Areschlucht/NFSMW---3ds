#!/bin/bash
set -euo pipefail
dock() { env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host=unix:///var/run/docker.sock "$@"; }
state=/workspace/toolchains/azahar/state
road="$state/data/azahar-emu/sdmc/3ds/nfsmw-rockport/road.nrd"
original=/workspace/port-research/rockport/scene-v0.15/road.nrd
kill_app() { dock exec nfsmw-emulator-v2 bash -lc 'pkill -KILL -f "^/emulator/AppRun.wrapped -w /project/nfsmw-rockport(-reference|-indexed)?[.]3dsx$" || true'; }
trap 'kill_app; cp "$original" "$road"' EXIT
kill_app
cp /workspace/port-research/rockport/v0.17/dense-road.nrd "$road"
for binary in nfsmw-rockport nfsmw-rockport-reference; do
 dock exec -d nfsmw-emulator-v2 bash -lc "export DISPLAY=:99 LANG=C.UTF-8 QT_QPA_PLATFORM=xcb XDG_CONFIG_HOME=/state/config XDG_DATA_HOME=/state/data XDG_CACHE_HOME=/state/cache LIBGL_ALWAYS_SOFTWARE=1; exec /emulator/AppRun -w /project/$binary.3dsx > /state/azahar-v017-dense-$binary.log 2>&1"
 sleep 15
 dock exec nfsmw-emulator-v2 bash -lc "export DISPLAY=:99; xdotool search --onlyvisible --name '^Azahar 2126.2' windowactivate --sync; xdotool keydown a; sleep .25; xdotool keyup a; sleep .5; xdotool keydown z; sleep .25; xdotool keyup z; sleep .5; xwd -root -silent -out /state/v017-dense-$binary.xwd; chmod a+r /state/v017-dense-$binary.xwd"
 kill_app
done
