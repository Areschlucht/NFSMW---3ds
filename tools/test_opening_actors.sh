#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 4 ]]; then
  echo "Usage: $0 opening-opponents.nro opening-pursuit.npp events.nre road-network.mwt" >&2
  exit 2
fi
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
test_binary="$(mktemp "${TMPDIR:-/tmp}/nfsmw-opening-actors.XXXXXXXX")"
trap 'rm -f -- "$test_binary"' EXIT
"${CC:-cc}" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
 -fsanitize=address,undefined -fno-omit-frame-pointer -no-pie \
 -I"$project_dir/include" "$project_dir/tests/test_opening_actors.c" \
 "$project_dir/source_bmw/mw_opening_actors.c" \
 "$project_dir/source_bmw/mw_race_ai.c" "$project_dir/source_bmw/mw_pursuit.c" \
 "$project_dir/source_bmw/mw_traffic.c" "$project_dir/source_bmw/mw_event_catalog.c" \
 "$project_dir/source_bmw/mw_race_progress.c" "$project_dir/source_bmw/mw_playable_race.c" \
 "$project_dir/source_bmw/mw_race_session.c" "$project_dir/source_bmw/mw_alias.c" \
 "$project_dir/source_bmw/mw_story_tutorial.c" "$project_dir/source_bmw/driving_controller.c" \
 -lm -o "$test_binary"
"$test_binary" "$@"
