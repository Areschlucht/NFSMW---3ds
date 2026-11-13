# Bounded original-movie preparation and playback helpers

This checkpoint prepares the supplied original GameCube movies for a native3DS
player and provides the portable reader/JPEG conversion plus an asynchronous
NDSP queue helper. It does not implement the parent's movie screen, career event
policy or in-engine NIS renderer. No target build or physical3DS playback test
was performed by this subtask. Original and converted media remain private.

## Available original and prepared media

The supplied original source includes all32 matched movies; no new upload was
needed. Original files are EA Multimedia containing VP6 640x448 at the exact
982047/32767 frame rate, plus stereo32kHz EA ADPCM R3. See cutscene-recovery.md.

Eight candidate opening-story/boot clips have complete native conversions under
`/workspace/port-research/career-movies/native-v1/`:

| Stem | Original video frames | Native bytes | PCM stereo frames |
| --- | ---: | ---: | ---: |
| ealogo | 92 | 789460 | 120484 |
| storyfmv_pin11 | 1520 | 22518320 | 1634976 |
| storyfmv_rac01 | 1516 | 24362536 | 1587180 |
| storyfmv_bus12 | 4677 | 79856340 | 5005308 |
| storyfmv_cro06_coh06a | 5655 | 97353340 | 6075384 |
| storyfmv_raz08 | 4368 | 81955800 | 4647580 |
| storyfmv_saf25 | 1279 | 21872608 | 1364272 |
| storyfmv_rap30 | 1956 | 28722072 | 2094736 |

Totals:357430476 bytes,21063 video frames and22529920 PCM stereo frames.
This is availability, not a chronological story playlist. Actual source event
references include pin11/bus12 on16_2_1_d_day_intro, rac01 onpartial_dday,
cro06_coh06a on16_2_2_sprint, and raz08 on16_2_3_sprint. Source IntroNis and other
in-engine renders are separate systems and are not replaced by these files.

## Conversion and the EA demux tail correction

`tools/build_career_movies.py` validates the pinned original inventory and each
complete original movie SHA before invoking the installed FFmpeg. It decodes
video from the start, retains the exact source frame count/rational timing,
scales to320x224 (exactly half the stored dimensions) using Lanczos, and encodes
independent baseline JPEG frames at quality82. PCM is stereo signed16 little
endian at the unchanged32kHz source rate. These are offline conversions, not a
native VP6/EA ADPCM decoder or sample-exact original audio implementation.

FFmpeg's original EA demux stops at SCEl, an audio-end tag. In rac01 there are
**27 actual original video blocks after that tag**, and in raz08 there are13.
The direct original-file path decoded1489/1516 rac01 frames despite successful
exit. The converter rejected that mismatch instead of silently reducing duration.
It now copies the original MVhd/MV0K/MV0F blocks byte-for-byte into a temporary
video-only EA container, then decodes all1516/4368 respective source frames.
Original files and video payloads are unchanged; no repeated or synthetic frames
are added. The conversion receipt retains the copied-block SHA and tail count.
The original game's own multiplex scheduling remains a separate fidelity question.

The entire independently decoded PCM track is retained without trimming/padding.
For example EA-logo video lasts3069674us while decoded audio lasts3765125us;
rac01 video lasts50582887us while decoded audio lasts49599375us. The new player
container uses the maximum duration and holds the last image during a longer
audio tail. Original source completion/skip policy and original decoder tail
semantics are not established by this portable policy.

## NVM1 bounded format

All numbers are little endian. Header is128 bytes:

| Offset | Value |
| ---: | --- |
| 0 | NVM1 magic; version1 at4 |
| 8 | Exact complete file size, limited to signed32-bit seek range |
| 12 | CRC32 of header16..127 |
| 16/20 | Width320/height224 |
| 24/28 | Source frame-rate numerator982047/denominator32767 |
| 32 | Frame count,1..65535 |
| 36/40 | Frame index offset128/stride16 |
| 44/48 | Audio CRC-table offset/count |
| 52 | JPEG-data start,16-byte aligned after both indexes |
| 56 | Contiguous PCM start,4-byte aligned |
| 60 | PCM stereo-frame count |
| 64/68 | Sample rate32000/channels2 |
| 72 | Maximum JPEG size, at most65536 |
| 76 | Combined video-index/audio-CRC-table CRC32 |
| 80..111 | Original movie SHA256 |
| 112 | Audio block size4096 stereo frames |
| 116..127 | Reserved zero |

Each16-byte frame entry is offset, JPEG byte count, JPEG CRC32, reserved0.
Entries are contiguous in source order with0..3 padding bytes after each JPEG.
The audio CRC table has one32-bit CRC per4096-frame block, with a possibly short
final block. PCM follows all JPEGs and ends at exact file size. The complete
frame index is validated sequentially on open, without allocating or loading
the movie payload. Separate video/audio FILE handles allow the audio worker's
seeks to proceed independently of main-thread image reads.

## Parent integration API

`include/mw_movie.h` / `source_bmw/mw_movie.c` supply:

- open/close, frame metadata and bounded JPEG read, each successful read CRC checked;
- PCM-block read with exact frame count and block CRC;
- exact rational frame selection by microseconds or audio sample count;
- video duration and max(video,audio) presentation duration;
- strict baseline320x224 JPEG to linear RGB565 using libjpeg;
- row-major RGB565 to512x256 tiled RGBA8 texture conversion.

JPEG warnings (including truncated input) fail decoding; dimensions, components
and progressive mode are checked before output. Caller scratch may be dirty on
decode/read failure. Upload only a successful completed image. The decoder uses
fast integer IDCT and non-fancy chroma upsampling as explicit target-performance
choices; pixel identity with another desktop/JPEG decoder is not claimed.

The cached SDK already includes libjpeg. Add `/opt/devkitpro/portlibs/3ds` to the
Makefile LIBDIRS/include/library paths and link `-ljpeg`; the existing Makefile
only lists CTRULIB. No download is needed. For a C2D movie image, use a320x224
subtexture of512x256 and place it at(40,8) on the400x240 top screen. This preserves
the stored aspect ratio; an original display-aspect correction remains separate.
Movie images already contain their original film grading; do not apply the
world's additional yellow-filter TEV pass to this image.

`include/mw_movie_audio.h` / `source_rockport/mw_movie_audio.c` supply the3DS-only
audio helper. `start` owns channel0/ndspInit until `stop`; keep the borrowed
MwMovie stationary and open until stop has joined its worker. Three16KiB linear
PCM buffers hold up to384ms. A16KiB-stack worker performs all PCM reads/CRC checks,
sleeping on LightEvent when no empty slot exists. The main-thread `update` only
checks completed wave buffers and queues ready buffers in exact source order;
it performs no file IO, decode, blocking sleeps or whole-movie allocation.

`played_samples` combines completed-buffer bases with the current NDSP sequence
and sample position, retries a changed sequence and preserves a monotonic clock.
`elapsed_us` uses DSP samples, then a wall-clock tail after actual audio EOF if
the video is longer. Pause freezes playback/tails; stop wakes/joins the worker
before clearing NDSP and freeing linear memory. Stop can wait for an in-flight
bounded file read; it is not advertised as a hard real-time operation.

If ndspInit fails, `muted_fallback` is explicitly true and the clock uses paused
wall time. This lets video remain viewable; callers must disclose the unavailable
sound rather than report successful audio playback. PCM IO/CRC failure makes
update return false, and the failed buffer is never queued. Completion/skip
events are the career controller's decision, not inferred from an absent audio
device or a timer with an empty movie.

## Host verification and target limits

ASan/UBSan tests decode all92 EA-logo JPEGs using actual host libjpeg62 and read
every120484 PCM frame. All131072 tiled texture texels are compared independently.
Exact source-rational boundary clocks, UINT64_MAX clamps, truncations, header and
index CRC/structure corruption, JPEG warning rejection, payload CRC failures and
guarded output buffers pass. A reader-only build can define MW_MOVIE_NO_JPEG.

The NDSP helper has a pthread-based SDK mock, not a device substitute. It tests
three-buffer FIFO, sample clocks, pause/longer-video tails, explicit muted
fallback,12 stop-during-prefill cycles and CRC failure without submission under
ASan/UBSan. These do not establish actual firmware availability or hardware DSP
sample reporting.

`tools/verify_movie_assets.c` checks all eight complete files: every index,
every JPEG/PCM payload CRC and681 sampled JPEG decodes pass. Private SHA receipts
are summarized in movie-native-validation.json. Main buffers cost65536 encoded
bytes +143360 RGB565 bytes +524288 GPU bytes +49152 PCM bytes +16384 worker stack,
plus libjpeg, stdio and NDSP internals. Actual old/New3DS CPU, SD throughput,
cache/upload stalls and audio/video synchronization still require emulator and
hardware validation by the parent integration. No target performance claim is
inferred from desktop decoding.

```sh
python tools/build_career_movies.py \
 --input-directory /workspace/port-research/cutscenes \
 --inventory /workspace/port-research/cutscenes/inventory.json \
 --output /workspace/port-research/career-movies/native-v1
```

Existing native outputs must match their recorded source/quality/output digest;
they are never silently overwritten. Raw original media, converted NVMs and
source-frame screenshots must not be committed as runtime game payloads.
