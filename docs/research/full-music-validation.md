# Complete music stream validation

2026-11-03. Original data and decoded audio stay private. This is an extraction,
format and desktop decoder checkpoint; it changes no 3DS audio runtime.

## Actual newly available source

`tools/extract_music_streams.py` verifies the original ZDIR SHA, looks up unique
MPF/MUS directory records by original path hash, and checks source archive sizes
and SHA-256 values against the verified input receipts. It extracts all five MPF
maps and five complete MUS banks using bounded 1-MiB copies. Existing output must
be identical; it is not overwritten. Full MUS entries total 236,887,040 bytes.
The matching header checksum word validates each MPF/MUS pairing.

All 1,363 MPF descriptor locations point to complete `SCHl` -> `SCCl` -> `SCDl`
blocks -> `SCEl` segments within their descriptor's original source bounds.
The complete set contains 46,305 SCDl blocks. This is a segment inventory, not a
recovered playlist, song count or proof of original node-transition behaviour.

| Map | Complete segments | SCDl blocks | Actual header properties |
| --- | ---: | ---: | --- |
| MW_MUSIC | 53 | 25,497 | GSTR/version3, stereo24kHz |
| MW_MUS_1 | 383 | 4,512 | GSTR/version3, stereo24kHz |
| MW_MUS_2 | 283 | 4,448 | GSTR/version3, stereo24kHz |
| MW_MUS_3 | 327 | 5,665 | GSTR/version3, stereo24kHz |
| MW_MUS_4 | 317 | 6,183 | GSTR/version3, stereo24kHz |

Every segment has the same explicit channel/rate/version profile and no codec
override patch. This broader evidence concerns these five banks only, not engine,
speech, effects or video audio. Five independent full-segment FFprobe results
identify `adpcm_ea_r3` with two channels at 24,000 Hz.

## Timing correction and unresolved decoder tail

All MPF durations equal **floor(samples * 1000 / sample_rate)** from their complete
SCHl headers. Nearest rounding, used for the earlier one-prefix comparison, does
not generalize: the differences range from -0.958 ms to zero. Use integer sample
counts for scheduling; do not accumulate rounded descriptor milliseconds.

Installed FFmpeg successfully decoded the first complete segment of each bank
with `-xerror`, as PCM16 WAV. All rates/channels match the headers. Results:

| Bank | Declared PCM frames | FFmpeg frames | Difference |
| --- | ---: | ---: | ---: |
| MW_MUSIC | 720,384 | 720,384 | 0 |
| MW_MUS_1 | 36,000 | 35,980 | -20 |
| MW_MUS_2 | 41,142 | 41,132 | -10 |
| MW_MUS_3 | 82,286 | 82,264 | -22 |
| MW_MUS_4 | 95,996 | 95,984 | -12 |

Decoded counts align to complete 28-sample ADPCM frames. This observation does
not recover the original decoder's tail handling. Do not silently pad, shorten
music timelines or claim sample-exact native decoding from this desktop test.
Resolve decoder boundary/trim semantics before timing-sensitive transitions.
No subjective listening, hardware playback or full-bank PCM decode was performed.

## Private usable artifacts and reproduction

Files live under `/workspace/port-research/full-music/`:

- `MW_MUSIC.MUS`, `MW_MUS_1.MUS` through `MW_MUS_4.MUS`, matching MPFs.
- Five `*-first.schl` complete source clips and `*-first.wav` decoded PCM clips.
  `MW_MUSIC-first.wav` is a complete 30.016-second test clip.
- `validation.json`: source ranges, hashes, all segment bounds/properties,
  block counts, decoder identities, PCM hashes and explicit frame discrepancies.
- `summary.json`: compact per-bank counts and representative decode results.

```sh
PYTHONPATH=tools python tools/extract_music_streams.py \
  --archives /workspace/port-research/original-archives \
  --zdir /workspace/attachments/41a22a72-053b-4186-8317-657b711d1119/ZDIR.BIN \
  --output /workspace/port-research/full-music \
  --decode-first --check-rejections
```

All descriptor, header, duration and block bounds checks passed. Twenty corrupted
actual-header variants (truncation, bad magic, unsupported version, zero channels)
were rejected. Syntax compilation and targeted whitespace checks pass. No external
code was downloaded or copied for this checkpoint.

## Runtime gates

A pair of 4,096-frame stereo PCM16 buffers costs 32 KiB and holds about 341 ms in
total at 24 kHz, before codec state, compressed queues or crossfade voices. That
is a budget example, not a hardware-tested configuration. Use bounded async reads,
validated segment seeks and DSP submission; do not load the 131.6-MB MW_MUSIC bank
into RAM. Offline conversion remains an option once original trim behaviour is
understood. Preserve original sample timing and PathFinder event/node/router
semantics, licensed track selection, pursuit state, ducking, pause/Speedbreaker
and save/transition rules. Profile audio CPU/SD stalls alongside the renderer.
