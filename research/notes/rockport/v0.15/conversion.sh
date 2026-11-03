#!/usr/bin/env bash
set -euo pipefail
cd /workspace/NFSMW---3ds
samples=/workspace/port-research/rockport/samples
args=()
for name in STREAML2RA-first24MiB.BUN STREAML2RA-sectors141-160.BUN STREAML2RA-sectors1141-1160.BUN STREAML2RA-sectors161-176.BUN STREAML2RA-sectors1161-1176.BUN; do
    args+=(--texture-bundle "$samples/$name" --scenery-bundle "$samples/$name")
done
args+=(--texture-bundle /workspace/attachments/85875135-c339-4aea-9553-be7e652717b8/GLOBAL-GLOBALB.BUN)
python tools/build_rockport_scene.py "$samples/STREAML2RA-sectors141-160.BUN" "$samples/L2RA.BUN" /workspace/port-research/rockport/scene-v0.15 "${args[@]}" --cell-size 64 --scenery-radius 350 --scenery-textures 128 --scenery-triangles 24000 --free-drive --complete-scenery --center-spawn --extra-sector 160 --world-range 161 "$samples/STREAML2RA-sectors161-176.BUN" --extra-sector 163 --extra-sector 164 --extra-sector 165 --extra-sector 168 --extra-sector 169 --extra-sector 170
