#!/usr/bin/env bash
set -euo pipefail
export DISPLAY=:99
xdotool search --onlyvisible --name '^Azahar 2126.2' windowactivate --sync
capture() { xwd -root -silent -out "/state/v017-$1.xwd"; chmod a+r "/state/v017-$1.xwd"; }
key() { xdotool keydown "$1"; sleep "${2:-.25}"; xdotool keyup "$1"; sleep .3; }
touch() { xdotool mousemove --sync "$1" "$2" mousedown 1; sleep .15; xdotool mouseup 1; sleep .35; }
# bottom display origin (352,432), native resolution 320x240.
touch 392 483
key z
capture spawn
touch 482 650
capture help
# A held touch must not repeatedly toggle the panel.
xdotool mousemove --sync 482 650 mousedown 1
sleep 1
capture help-held
xdotool mouseup 1
sleep .3
capture navigation
touch 600 650
capture stats
key a 1.5
capture stats-driving
touch 600 650
capture navigation-driving
key z
capture reset
key a 2
capture driving
xdotool keydown a
key Right .3
xdotool keyup a
capture turning
key s 1
capture braking
key z
xdotool keydown a
sleep 1.35
xdotool keydown Left
key w .35
xdotool keyup Left
xdotool keyup a
capture handbrake-release
key z
key a 6
capture edge
key x 1
capture reverse
key z
capture reset-final
touch 390 650
capture menu
touch 390 515
key x
key z
capture garage
key a 1
capture garage-roll
key z
capture garage-reset
touch 500 650
touch 390 545
capture controls
touch 500 650
capture menu-final
touch 390 576
capture exit
