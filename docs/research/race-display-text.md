# Original race display-name lookup and supplied English text

Read-only recovery. No shared runtime edits, SDK build, game-data edits or commit
were performed by this task. The parent integrates the resulting private mapping.

## Actual original frontend consumer

Frontend callers `80126628`, `801276FC` and `8015B2F4` invoke `801630FC` with the
literal `TRACKNAME_` and an event reference. The function follows this chain:

1. `801A5158` obtains the event's display ID. Its attribute path queries original
   field `A78403EC`; the rich exported source values are IDs such as `10.2.1`.
   A cached event-record path also exists; it is not separately emulated here.
2. `801630FC` uses the original `%s%s` format to concatenate prefix and ID into
   a 64-byte temporary buffer.
3. `801630CC` replaces every dot in that bounded buffer with underscore.
4. `80183B54` computes the initial-`FFFFFFFF`, multiply-by-33 string hash.
   It calls actual ASCII uppercase helper `80183768` per character.
5. Caller `8012663C`/`8015B308` passes that key into the frontend text setter.

Thus `10.2.1` becomes `TRACKNAME_10_2_1`, not `TRACKNAME_10.2.1`. The latter
unmodified-dot candidate resolves none of the source definitions in this sample.
The normalization is proven by the original consumer, not guessed from matches.

## Language payload and exact results

The supplied `english-textonly.bin` is SHA-pinned to
`fda4935491869ddaa3eba335c3425aa9cbc8fcbd82a58a20f7334ecbbbd8fa4a`.
Chunk `00039000` contains 4,464 sorted unique language keys. Table offset is
6,172 and string-region offset is 41,884, both file-relative. Original header
pointers are payload-relative. Every string offset and NUL boundary is checked.
The parser preserves raw bytes; only matched race/menu labels verified as ASCII
are decoded, rather than asserting a code page for every shared language string.

The source catalog contains 277 definitions, including templates/challenges.
**175** computed keys resolve exact English race labels. **102** stay missing;
these include absent IDs, challenge IDs and special/unmatched source identifiers.
No title is invented and no numeric-ID fallback is silently presented as original.
Examples of actual source lookup results:

| Original ID | English label |
| --- | --- |
| 16.2.1 | Riverfront & Marina |
| 16.2.2 | Financial & Shipyard |
| 16.2.3 | Waterfront & Century |
| 1.1.1 | Hastings |
| 1.1.2 | Clubhouse |
| 1.2.4 | Industrial & Bristol |

The private full map is
`/workspace/port-research/race-story/display-text.json`. Each `events` row has
`event_key`, `source_event_name`, `source_id`, `language_key`, `status` and,
when `status == matched`, `display_text` plus exact language-table/string offsets.
Source-ID field provenance is retained. `recover(english_bytes, dol_bytes,
catalog, verify_original=False, frontend_directory=None)` is callable by an
exporter; no per-title guesses or output-path instructions are executed.

## Original execution and structural checks

`NameReference` executes original `801630FC`, dot substitution, hash loop and
uppercase helper with instruction/write whitelists and a finite budget. Only
the event-ID getter and bounded formatting of two ASCII strings are supplied
synthetically. This does not verify truncation, arbitrary printf behaviour,
original field inheritance/caching or non-ASCII lookup behaviour.

All 277 actual source IDs plus seven selected edge/case variations match the
portable key calculation: **284 original execution comparisons**. Eight malformed
language variants are rejected independently of the whole-file SHA pin: truncated
header, wrong chunk, wrong size, excessive count, table out of bounds, duplicate
key, offset inside a string and unterminated final string. Mutation checks first
validate the real pinned source, then disable only the SHA pin to reach structural
checks on the deliberately altered bytes.

## Menu evidence boundary

The English table includes shared Xbox/PC/network strings; presence does not prove
GameCube visibility. Exact lower-case `alias manager` key `1B76F2CE` occurs in
actual `MC_ProfileManager.fng` at byte27,048 and `MC_DeleteProfile.fng` at29,056,
in little-endian form. The tool reports these literal-key candidates and FNG
hashes, not a fully recovered localization-object binding. Equivalent literal
scans did not find the common main-menu labels in `MainMenu.fng`/`MainMenu_Sub`;
they can be supplied dynamically. Exact original main-menu ordering is still
unproved and must not be inferred from English table order.

## Reproduce

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/race_display_text.py \
  --english /workspace/attachments/7105c248-eeef-4074-b13e-03b151a4727e/english-textonly.bin \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --catalog /workspace/port-research/race-story/catalog.json \
  --frontend-directory /workspace/port-research/frontend-flow \
  --verify-original --check-rejections \
  --output /workspace/port-research/race-story/display-text.json
```

Language payloads, full mapping and decoded original layouts remain private.
