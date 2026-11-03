#!/bin/bash
set -euo pipefail
cc -std=c11 -O2 -Wall -Wextra -Werror -fsanitize=address,undefined -Iinclude tools/ui_preview.c source_bmw/mw_ui.c -lm -o /tmp/ui-preview-v017
mkdir -p /workspace/port-research/rockport/v0.17/ui
/tmp/ui-preview-v017 /workspace/port-research/rockport/v0.16/map-reference.ppm /workspace/port-research/rockport/v0.17/ui
cc -std=c11 -O2 -Wall -Wextra -Werror -fsanitize=address,undefined -Iinclude tests/test_world_index.c source_bmw/world_index.c source_bmw/world_vertex.c source_bmw/nfs_scene.c -lm -o /tmp/world-index-v017
/tmp/world-index-v017 /workspace/port-research/rockport/scene-v0.15/world.nfm
