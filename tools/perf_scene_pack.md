# Optional packed scene IO checkpoint

The new `mw_scene_pack.h/.c` reader and `perf_scene_pack.py` packer provide one
open archive in place of thousands of individual asset-file opens. They preserve
every selected WSM/WSI/WTX byte; no geometry, texture, material or LOD data is
changed. The current directory renderer remains the default and was not edited.

Measured checkpoint:

| Item | Bytes/count |
| --- | ---: |
| Model/section/texture entries | 13538 /997 /2703 |
| Total entries | 17238 |
| Original payload bytes | 102049292 |
| Archive bytes | 104060544 |
| Resident index bytes | 1103232 |
| Alignment padding | 907892 |
| Largest individual asset | 471664 |

All17238 archived payloads were read through the actual portable C API under
ASan/UBSan and compared byte-for-byte with original files. Six fixture tests
cover deterministic output, overwrite/duplicate rejection, source-change
rollback, header/index CRC/truncation, recomputed-CRC sorting/range/key attacks,
lazy payload CRC, missing/invalid lookup, insufficient buffers and cleanup.

Artifact:
`/workspace/port-research/hardware-optimization/scene-pack/native-checkpoint-v1.mwp`.
Its adjacent JSON contains every key, source path, size, offset, CRC and SHA256.
Archive SHA256 is
`1cb0658c6b6adaf0923e1289a23827fd1edf4ced23c9a9aa7d2b63f34ba5d2b1`.
Source SHA256 is
`58fdd0adb8bdf1ebc3545ee679076c768acb3c52308c4b916ca960b4a0ac5552`.
Scene manifest SHA256 is
`3aaa0b0ae70fc378f2fe49f0808b98ad34f9e2e414da4ed416865092bae889c3`.
This checkpoint predates the pending explicit empty-WSM emission. Repack into a
new output after any export/manifest change; this archive is not the final scene.

## Bounded layout

All integers are unsigned little-endian32 unless stated. The file is limited
to0x7fffffff bytes because the target's ordinary fseek/long interface is signed32.
The index is limited to32768 entries and also to the caller's index-byte budget.

The128-byte header contains:

| Offset | Value |
| --- | --- |
| 0 | MWP1 magic |
| 4 | Version1 |
| 8 /12 | Header128 /entry64 bytes |
| 16 /20 | Entry count /index CRC32 |
| 24 /28 | Aligned payload start /exact file length |
| 32 | Original source SHA256,32 bytes |
| 64 | Scene-manifest SHA256,32 bytes |
| 96 | Header CRC32 with this field zeroed |
| 100..127 | Zero reserved bytes |

Each64-byte index entry contains kind@0, id@4, identity32@8, payload offset@40,
payload bytes@44, payload CRC32@48 and12 zero reserved bytes@52. Entries sort by
numeric(kind,id), then lexicographic identity bytes. Duplicate/unsorted keys are
rejected. Payloads occur in that order at128-byte aligned offsets; gaps contain
deterministic zero padding. Ranges must follow the exact alignment sequence,
remain within the file, and end exactly at file length.

Kinds match the renderer callback:MODEL1, SECTION2, TEXTURE3. Keys are:

- MODEL:original hash from `models/<8hex>.wsm`, identity zero.
- SECTION:original ID from `sections/<decimal>.wsi`, identity zero.
- TEXTURE:hash plus full32-byte identity from
  `textures/<8hex>-<64hexidentity>.wtx`.

Metadata/WST1 and collision assets remain separately directory-owned. A model's
guard identity is still verified by the renderer after reading; it is not
mistaken for the texture identity or substituted for the original model key.

## Reader contract and integration

`mw_scene_pack_open(pack,path,index_budget)` requires a zero/closed output,
opens one FILE and allocates only the bounded raw index. It validates the header,
whole index CRC, sorted keys, reserved fields and all ranges before publishing
the open pack. Failure frees everything and leaves the output zero. `close` is
safe for zero/closed objects. FILE/libc overhead is additional to index bytes.

`find` performs binary search and returns disk size/offset/CRC metadata.
`read` accepts the same kind/id/identity key and caller-owned bounded storage.
NULL destination/capacity0 queries size without validating/loading the payload;
that is a cost query, not a ready asset. A full read checks capacity first,
seeks/reads one entry and verifies its CRC. On any error, bytes is zero and the
caller must discard the destination; staged assets must never be published from
a failed read. The reader allocates no payload buffer and never loads the whole
archive. One FILE means single-thread ownership; it is intentionally blocking.

The backend's read callback can wrap `mw_scene_pack_read` directly with an
explicit result mapping:OK→OK, NOT_FOUND→MISSING, IO→IO, MEMORY→BUDGET,
CAPACITY→CAPACITY, CRC→FORMAT, INVALID→INVALID. During pack-open, a too-small
index budget should surface as a budget failure. Do not cast incompatible
function-pointer types. MODEL/SECTION lookup deliberately ignores the passed
model guard bytes; TEXTURE requires the full identity.

Before choosing an archive, compare its source/manifest fingerprints with the
intended exported scene. The reader exposes both fields; it does not silently
assume an archive matches unrelated directory metadata. Keep the existing
directory provider available. Include the1.1MiB index and FILE overhead in
normal-memory admission outside the renderer arena rather than underreporting
them as free cache capacity. Disk entry bytes do not claim GPU allocation size.

CRC uses a1KiB read-only IEEE0xEDB88320 table to avoid eight bit rounds per payload
byte. Pinned ARMv6K strict compilation passes:2823 bytes text/rodata including the
table, zero data/BSS. CRC still has runtime cost and underlying payload seeks
remain. No3DS SD-latency, startup or FPS improvement is claimed before hardware
measurement. The measured claim is fewer file opens with exact payloads.

For context only, modeled directory allocation is143052800 bytes with4KiB
clusters or588709888 with32KiB clusters, versus the104060544-byte archive plus its
last cluster rounding. Those are arithmetic storage models, not observations of
the user's SD format or actual free space.

## Reproduction

```sh
python tools/perf_scene_pack.py /workspace/port-research/world-streaming/scene-native \
  /workspace/port-research/hardware-optimization/scene-pack/a-new-name.mwp
python -m unittest discover -s tests -p test_perf_scene_pack.py -v
cc -std=c11 -O2 -g -Wall -Wextra -Werror -fsanitize=address,undefined \
  -fno-omit-frame-pointer -no-pie -Iinclude tools/perf_scene_pack_test.c \
  source_bmw/mw_scene_pack.c -o /tmp/mw-scene-pack-native
/tmp/mw-scene-pack-native /path/to/archive.mwp /path/to/original/scene
```

The packer selects assets only from the scene manifest, validates every original
size/SHA while streaming one source at a time, sorts keys deterministically,
refuses existing archive/report outputs, and removes only its newly created
partial archive on failure. A changed source or manifest aborts the operation.
The existing scene/exporter/renderer/main/build files remain untouched.
