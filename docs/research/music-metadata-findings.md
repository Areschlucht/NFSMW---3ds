# USA GameCube music metadata checkpoint

2026-11-03. This is validated input research, not an audio-enabled game build.
No runtime files were changed. Original engine profiles, speech/dispatch and
other sound banks are separate work; these music files do not supply them.

## Confirmed container and original consumer

All five newly supplied MPFs have `PFDx` magic, version/subversion bytes `05 01`
and big-endian numeric fields. In the supplied SHA-pinned USA DOL:

- `803755F8..80375608` loads and compares the `PFDx` magic.
- `8037560C..8037561C` masks the next word's upper half and requires `0501`.
- `80375698..80375740` resolves header offsets `14..34` against the file base.

These instructions support the actual target reader and relative-table scheme.
They do not recover the entire PathFinder interpreter, music selection logic,
node transition rules, or event ownership. DOL constant references and the
reader-window digest are reproducibly recorded by the inspector.

Table interpretations are additionally cross-checked against vgmstream's open
source EA MPF/SCHl readers. All ten observed section offsets are four-byte aligned,
ordered and within the file; the final offset equals its exact length. Each
16-bit node pointer is multiplied by four and bounds-checked. Each eight-byte
sample descriptor consists of an offset in 128-byte units and duration in ms.
The one track per file has no RAM subbank in these observations. Every sample
offset is increasing and inside the separately verified original MUS archive
entry size.

| MPF stem | Nodes | Sections | Events | Routers | Variables | Streamed descriptors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MW_MUSIC | 192 | 4 | 58 | 0 | 4 | 53 |
| MW_MUS_1 | 423 | 2 | 14 | 26 | 2 | 383 |
| MW_MUS_2 | 324 | 2 | 15 | 34 | 2 | 283 |
| MW_MUS_3 | 369 | 2 | 14 | 33 | 2 | 327 |
| MW_MUS_4 | 356 | 2 | 13 | 28 | 2 | 317 |

These are node/event/segment counts, not song counts or a recovered playlist.
Do not identify each descriptor as a full song, hardcode a linear playlist from
its order, or assign all event states meanings from their numeric counts.

## Existing archive sample now has a verified role

The already supplied `ZZDATA3-first64KiB.bin` starts at the directory range for
`SOUND\\PFData\\MW_Music.mus`. Its first word `b3f1409f` matches the checksum word
in the MPF's track record. This validates the pair's stored identifier; the
algorithm that generates that word is not recovered.

The first MPF descriptor stores offset `2`, hence byte `0x100`. That location
in the existing sample contains `SCHl`. Its 36-byte header has `GSTR` generic
platform identity, version patch 3, two channels, 24,000 Hz, and 720,384 samples.
That is 30.016 seconds, exactly matching the descriptor's 30,016 ms duration.
The blocks use little-endian lengths despite the MPF's big-endian tables.
Codec identity must not be inferred from GameCube platform alone.

The generic header has no explicit codec override; the generic EA-XA default
with version 3 is corroborated independently by installed FFprobe identifying
`adpcm_ea_r3`, stereo 24 kHz. The supplied prefix contains 14 complete EA blocks
and part of the next SCDl block at byte 62,572 (declared size 5,152; only 2,964
bytes remain). Excluding that incomplete block, FFmpeg successfully decoded
57,624 stereo PCM frames, or 2.401 seconds. The PCM has nonzero audio samples.
No subjective listening, full-song decode or 3DS playback was performed.

Private validation output and PCM remain under
`/workspace/port-research/music-metadata/`; original/decoded audio is not added
to Git. Complete-block PCM SHA256:
`44df2def8ce71a1bd4f6b60bb1a02204e7b5c330298146360afa8db6241c6beb`.

This one header does not establish the codecs or channel/sample rates of every
music segment, other music bank, engine sound, voice, video or sound effect.
FFprobe's duration estimate on a truncated prefix is not the original clip
length; retain the explicit SCHl/MPF declaration separately.

## Reproduction and checks

```
PYTHONPATH=tools python tools/music_metadata_inspect.py \
  --input-directory /workspace/port-research/whole-game-metadata-20261103 \
  --stream-prefix /workspace/attachments/9000cbfa-0457-401a-bbd0-c31ee2bdb51c/ZZDATA3-first64KiB.bin \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --check-rejections \
  --output /workspace/port-research/music-metadata/inspection.json
```

All five actual maps, 1,664 node pointers and 1,363 sample descriptors pass
structural/range checks. Twenty malformed input variations are rejected:
truncated headers, bad magic, inconsistent final offsets and out-of-range node
pointers for every map. Checks do not execute original music nodes. The tool
emits hashes/counts and bounded descriptors, not original song data.

The complete-block decode is a separate local FFmpeg validation, not something
the Python inspector performs. Private `prefix-decode-validation.json` records
frame count, PCM hash and explicit limits.

## Integration gates

1. Recover node/event/section/router semantics from their original consumers,
   including game-state producers, transitions, bar boundaries, licensed music
   choice, pursuit intensity, pause and Speedbreaker behaviour.
2. Check actual SCHl headers at descriptor locations in the remaining streams;
   acquire only the necessary slices/full banks as needed, keeping archive
   identity and checksum provenance. Do not request the same known header again.
3. Implement bounded async reads, validated segment seeking, codec state and
   transition buffering. Convert original audio offline when appropriate; do not
   load the 131,595,008-byte MW_Music.mus entry into 3DS RAM. Stereo 24 kHz PCM16
   consumes 96,000 bytes/second before buffering/mixing overhead.
4. Integrate voice limits, gain/ducking and priorities with effects, per-car
   engine layers and speech. Benchmark audio CPU use and streaming stalls on
   hardware before choosing buffer sizes and simultaneous voice counts.
5. Compare actual selection/transitions and timings with the original game,
   then verify sustained 3DS playback, scene changes and CPU/GPU timing together.

## External implementation references

Reviewed via the configured proxy; local copies are private reference material.
No external source code was copied into the authored inspector.

- [vgmstream EA MPF/MUS reader](https://github.com/vgmstream/vgmstream/blob/master/src/meta/ea_schl_map_mpf_mus.c),
  consulted file SHA256 `fd3df08712049452de3cb34209d7d5fc46b5ef754e37340cd0db50865a4220e1`.
- [vgmstream EA SCHl reader](https://github.com/vgmstream/vgmstream/blob/master/src/meta/ea_schl.c),
  consulted file SHA256 `21374532f3eb6c16b35f9a7a0377e15d37cc791f3a7133f63aabc0ac0f282094`.

Master links can change; digests identify the inspected copies. External codec
format knowledge supplements, rather than replaces, original-consumer recovery.
