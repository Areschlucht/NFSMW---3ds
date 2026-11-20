#!/usr/bin/env bash
# Args are genuine source-derived music/effect plus an explicitly test-only
# loop+calibration packet. Test fixture must never be staged as game audio.
set -euo pipefail
if [[ $# != 3 ]]; then
 echo 'Usage: test_game_audio.sh music.nag effect.nag TEST-ONLY-calibrated-loop.nag' >&2
 exit 2
fi
cd -- "$(dirname -- "$0")/.."
game_audio_binary="$(mktemp /tmp/nfsmw-game-audio.XXXXXXXX)"
trap 'rm -f -- "$game_audio_binary"' EXIT
"${CC:-cc}" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -ffp-contract=off \
 -DMW_MOVIE_NO_JPEG -fsanitize=address,undefined -fno-omit-frame-pointer -no-pie \
 -Iinclude -Itests/game_audio_mock tests/test_game_audio.c tests/game_audio_mock/3ds.c \
 source_bmw/mw_audio_stream.c source_bmw/mw_movie.c source_rockport/mw_movie_audio.c \
 source_rockport/mw_game_audio.c -lm -pthread -o "$game_audio_binary"
"$game_audio_binary" "$@"
