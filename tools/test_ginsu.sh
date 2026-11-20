#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 2 ]]; then
 echo 'Usage: test_ginsu.sh original-bmw.gin bindings.ngb' >&2
 exit 2
fi
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
program="$(mktemp /tmp/nfsmw-ginsu-test.XXXXXXXX)"
trap 'rm -f -- "$program"' EXIT
"${CC:-cc}" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fno-fast-math -ffp-contract=off \
 -fsanitize=address,undefined -fno-omit-frame-pointer -no-pie -I"$project_dir/include" \
 "$project_dir/tests/test_ginsu.c" "$project_dir/source_bmw/mw_ginsu.c" \
 "$project_dir/source_bmw/mw_ginsu_bindings.c" -lm -o "$program"
"$program" "$@"
