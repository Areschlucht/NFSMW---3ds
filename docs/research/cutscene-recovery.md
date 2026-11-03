# Original GameCube cutscene source recovery

2026-11-03. No game build or SDK compilation was performed. This checkpoint
recovers original media and source references; it does not add a 3DS video player,
pretend that all story transitions work, or publish original media to GitHub.

## Complete matched media inventory

`tools/cutscene_inventory.py` verifies the USA DOL/ZDIR SHA, validates all directory
ranges, checks used source archives against the completed collection receipts,
and scans indexed entry headers. All **32 actual MVhd movie entries** hash-match
original DOL stems with the literal suffix **`_english_ntsc.vp6`**. Their total
size is **382,938,628 bytes**, in ZZDATA0 and ZZDATA1. Existing outputs must remain
byte-identical. No original file is edited.

The 32 identified entries are:

- All 15 `blacklist_01` through `blacklist_15` clips.
- Nine story clips: `storyfmv_bla134`, `bus12`, `cro06_coh06a`, `her136`, `pin11`,
  `rap30`, `raz08`, `saf25`, `rac01` (each full name retains the `storyfmv_` prefix).
- Five tutorials: drag, tollbooth, bounty, pursuit and speedtrap.
- Attract movie, EA logo and PSA.

Six DOL stems have no matching source directory entry under the observed suffix:
`intro_movie`, `sprint_tutorial`, `storyfmv_dda01`, `storyfmv_epi138`,
`storyfmv_pol17_mot21`, `storyfmv_roc02`. Keep these as absent matches, not invented
movies, replacements, or proof that their original code paths are reachable.
There are no remaining unidentified MVhd entries in this supplied directory.
Other formats/code paths are not ruled out simply by this magic scan.

## Actual container and independent probe results

Every matched file is **EA Multimedia**, with `MVhd` containing `06PV`, rather
than a raw standalone VP6 elementary stream. All 32 probe as:

- VP6 video, **640 x 448**, YUV420P.
- Stored rate **982047 / 32767** (approximately 29.9706 frames/s). Preserve this
  rational rather than silently replacing it with exact30 or30000/1001.
- Stereo **32,000 Hz EA ADPCM R3** audio. This differs from the previously
  recovered24-kHz music banks; a single global audio-rate assumption is wrong.

The scanner walks the entire indexed movie payload with little-endian EA block
lengths, accepting only the observed `MVhd`, `MV0K`, `MV0F`, `SCHl`, `SCCl`,
`SCDl`, `SCEl` structure. All blocks fit their original bounds. It finds **484
video keyframe blocks**, **38,552 other video-frame blocks**, and **39,193 audio
blocks**. Per-movie video block counts exactly match MVhd's declared frame count;
each movie has one SCHl and one SCEl. Declared durations range from3.069674s to
188.684844s. Uninterpreted MVhd fields are retained as values, not assigned names.

FFprobe independently confirms the codec/dimensions/rates for every extracted
movie. Complete EA-logo and Blacklist15 movies additionally decode successfully
with FFmpeg `-xerror`, both video and audio, to a null sink. This is desktop codec
validation, not a measured 3DS playback budget or proof of full-game A/V timing.

A short private preview decoded from the original Razor clip is available at:

`/workspace/port-research/cutscenes/story-raz08-six-second-preview.mp4`

It is a **phone preview**, 6.005884s,480x336 H.264/AAC,713,053bytes; it is not an
original asset, original codec, runtime cutscene conversion choice or3DS player.
An initial input-side seek (`-ss5` before `-i`) caused VP6 decode failure.
Decoding from the source start then trimming output succeeds. Preserve this
stateful/keyframe-seeking limitation; do not claim arbitrary random access works.

## Original filename and name-table consumers

Original routine **80132BD0..80132C7C** constructs filenames with:

- Region `_ntsc` at803E1314 or `_pal` at803E131C.
- Language format `_%s` at803E1324, fed through original language lookup8015C288.
- Extension `.vp6` at803E1328.
- Format `%sMOVIES\\%s%s%s%s` at803E1330.

The observed English NTSC archive names independently match that scheme. The
language and region selectors still need their complete surrounding producers
before a portable frontend should construct every path unconditionally.

The original table at **8041BA7C** contains38 records of8bytes: a MOVIES-prefixed
stem pointer and a second scalar. Routine **801365A0..80136650** explicitly
scans indices0 through0x25 atstride8, compares the supplied name, and returns a
selected second scalar. The exported original table index is **not** an invented
chronological story position or verified gameplay event ID. The second scalar's
role is intentionally left uninterpreted; no volume/priority claim is assigned
from plausible numeric values alone.

`MNotifyMovieFinished` has a concrete materialized string reference at8017F9D0.
This is a completion-hook lead, not recovered start/skip/complete/abort/save
semantics. The separate race/story exporter must establish the actual event
references and progression conditions. A movie directory is not a story graph.

## Reproduce and validation

```sh
PYTHONPATH=tools python tools/cutscene_inventory.py \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --zdir /workspace/attachments/41a22a72-053b-4186-8317-657b711d1119/ZDIR.BIN \
  --archives /workspace/port-research/original-archives \
  --receipts docs/research/archive-receipts.json \
  --output /workspace/port-research/cutscenes --probe --check-rejections
```

The private inventory includes every source range, archive/payload SHA, literal
DOL address, original table entry, actual block count and independent FFprobe
properties. Five corrupt header/codec/dimension/frame-count/block-size variants
are rejected. Source-derived video/audio and transcoded previews remain private.
The authored script and this report are the only owned source/document changes.

Next integration requirements: explicit event-to-movie ownership and completion
transitions; bounded decoder/demux buffering; original rational video timestamps
and32-kHz audio clock; supported keyframe/state restore; screen scaling/letterbox
policy based on actual original display behaviour; skip/pause/error handling;
and target-hardware memory/CPU/DSP measurements. Do not make a player that loads a
61-MB source movie or all decoded frames into 3DS memory. The no-build instruction
is still in force; this checkpoint does not require a hardware test from the user.
