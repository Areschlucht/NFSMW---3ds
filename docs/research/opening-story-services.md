# Original opening phone and engine services

The source phone clip is recovered, and a small native engine-sabotage producer is
available. These are source-backed dependencies of the opening career script;
a request must not itself be treated as its eventual notification.

## Original debug ELF and shared reader

The supplied USA archives contain an unstripped original PowerPC debug ELF.
ZDIR entry `e658a8f0`, archive 3, offset 240877568, length 105374584;
SHA-256 `6ee16d55d92ad1b337a9b655989c32b2976f95e7c64e148cf83f482c613f79f7`.
All nine initialized ELF sections are byte-identical to the corresponding ranges
of the pinned USA Speed.dol (including sections grouped together by the DOL).
The original ELF remains private:
`/workspace/port-research/opening-story-services/original-debug.elf`.

`tools/mw_debug_info.py` is an authored mmap reader for its ELF32 big-endian
symbols and DWARF 1 entries. `DebugInfo(path).find(name, tags={2,19})` returns
matching classes/structs; `members(entry)` returns names, concrete offsets and
referenced type DIE offsets; `die(offset)`, `children(entry)`, `enum_values(entry)`
and `symbols(substring)` support targeted follow-up. DIE references are relative
to `.debug`. Compilation units can repeat types. Scope references remain raw
`attrs[20]`; the reader does not invent namespace-qualified names. Four-byte
padding DIEs are skipped. Unsupported/truncated forms are rejected.
No original source or full debug dump is emitted to Git.

`tests/test_mw_debug_info.py` uses a fully authored miniature ELF fixture to test
nested member offsets, references, padding, repeated enums and malformed data.
The story verifier separately confirms actual original types and ELF/DOL identity.

## Engine sabotage

Original script binding `Game_SabotageEngine(ISimable*, float)`, `801c6038`,
forwards to `EngineRacer::Sabotage(float)` at `802552d4`.
DWARF names `EngineRacer.mBlown` at `1a8` and `mSabotage` at `1ac`;
class size 432. This closes the meaning of the original final-race argument 5:
it is a delay added to **simulation time**, not a wall-clock or guessed story timer.

The source refuses to schedule when a positive deadline already exists, when
`delay <= 9.999999974752427e-7f`, or when the engine is already blown. Otherwise
it stores `Sim::GetTime() + delay`. `Sim::GetTime` is `802782fc`, reading float
`8049896c`. The engine tick at `802580f8` compares deadline minus that clock;
when it reaches zero, it clears the deadline and invokes the engine Blow method.
`EngineRacer::Blow`, `80255360`, changes `mBlown` once, clears the deadline to
**zero**, and constructs an actual `EEngineBlown` event. Its consumer ultimately
produces `MNotifyEngineBlown`. Repeated calls do not create repeated blow events.

`include/mw_story_services.h` / `source_bmw/mw_story_services.c` implement that
finite-input schedule/transition. `mw_story_engine_tick` returns 1 only on the
actual one-time blow. Dispatch the career notification only for that return;
the career script's separate one-second transition timer begins afterward.
The caller must use simulation time and pause it with simulation. Reset on actor
replacement/restart. Invalid native nonfinite inputs are rejected explicitly.
ASan/UBSan tests cover scheduling, deadline boundaries, pause-like repeated
clock values, pending/blown rescheduling rejection and one-time notification.

While waiting, the original engine also applies a 12 Hz RPM ripple:
`rpm = fma(sinf(float(float(remaining * 12) * 6.2831854820251465)), rpm * .5, rpm)`.
The constants and `sinf` symbol are original. The small service does not itself
apply this effect, torque loss, visual effects or the complete mechanical engine;
those belong to the actual engine integration.

## Opening phone selector and source audio

`ECellCall(10)` in driving dispatches to `MiscSpeech::SMSCellCall`, `802ad6ac`,
then the speech scheduler. `MiscSpeech::MapSMSToSPCHEnums`, `802ad828`, maps
SMS 10 to `Csis::CellCallStruct{0x00010000, 1}`. DWARF confirms the eight-byte
struct members `cell_call_bucket` at 0 and `cell_call_number` at 4.
`mw_story_cell_selector` implements all 17 actual source intervals, IDs 10–105;
invalid IDs leave caller output unchanged.

English `audiosystem` collection `dcf256e2` in original ATTRIBUTES selects the
actual paths `Sound\Speech\copspeech_en.{evt,csi,idx,big}`. Path hashes are
resolved against the pinned ZDIR; these are not guessed filenames.

| Source | ZDIR key | Archive | Offset | Bytes |
| --- | --- | --- | --- | --- |
| `.evt` | f9f11de1 | 1 | 337123328 | 15547 |
| `.csi` | f9f114f1 | 1 | 337117184 | 5136 |
| `.idx` | f9f12c97 | 1 | 301217792 | 76976 |
| `.big` | f9f10f64 | 2 | 0 | 179979776 |

Actual EVT event 204 (`cc`) begins at `1a58`; its sole sentence at `1a68`
references its sole phrase at `1a74`, direct bank 425 (`01a9`) with two filters.
IDX bank-table entry 0, key `01000000`, points to its header at `2488`;
80 samples carry original bucket/call filter indices. Unchanged source
`iSPCH_MatchSample`, `8037ebb0`, tested over all 80 samples, admits exactly
**sample 73** for the original SMS 10 mask pair. Unchanged
`iSPCH_GetSampleSizeData`, `80381420`, yields offset **6670336**, size **55040**
inside the actual English `.big`. The extracted original SCHl stream SHA-256 is
`a11bf14413e8d8aa3560df81f0932be090e4237523f030a94b7f2e55c860810a`.

The codec is EA MicroTalk (10:1), unsupported by system FFmpeg revision2=4.
A private build of vgmstream revision
`24ffd6ce3e1f34fdebf9f5316d18ad2e162838ce` decodes it without substituting audio.
Its CLI recognizes the extracted stream with `.asf` extension. Native-ready PCM:

- `/workspace/port-research/opening-story-services/cellcall10.pcm`
- Signed 16-bit little-endian, mono, 22050 Hz.
- **245803 samples, 491606 bytes, 11.147528344671201 seconds.**
- SHA-256 `91bdfd4259961d80a73ebc83498dfb4042e9708098fd49fab787d56c106ba458`.

These are source/decoder counts, not an invented clip duration. Original assets
and decoded PCM remain private and must not be committed as authored source.

## Actual phone notification timing

Original `GameSpeech::IssuePlayback(ScheduledSpeechEvent*)`, `802909c8`, checks
that the event ID is `cc` and posts `MNotifyCellCallStarted` at `80290b54`, before
issuing individual stream requests. This is a **speech playback producer**;
no manual answer-button requirement was found on this driving dispatch path.
The native adapter should load the verified clip, successfully admit playback,
then emit CallStarted once. The original opening script's 8-second then 3-second
steps run from that notification. Completion should follow actual playback
completion; queueing an unavailable asset is not completion.

The source also contains an explicit disabled-speech bypass in
`ScheduleSpeechPartII` (`8028a244..8028a2d0`), which delivers both Started and
Complete for event `cc`. Its preceding guards reference `IsSpeechEnabled`,
`Speech::Manager.m_speechMode`, and `g_pEAXSound`/sound configuration. This is
not permission to silently synthesize notifications for a failed native audio
service. The recovered real clip allows implementing actual playback instead.

## Reproducible verification

`tools/opening_story_services.py --dol ... --elf ... --output <private>/verified.json`
executes unchanged PPC selector, schedule and tick windows against the portable
C service (112 selector inputs, seven scheduling cases, five tick cases).
With `--archives ... --zdir ... --attributes ...`, it additionally reopens the
actual speech paths and executes original event lookup, all 80 sample filters
and sample bounds. Add `--decoder <vgmstream-cli>` for the actual WAV and native
PCM outputs. `--attributes` must identify the supplied original USA ATTRIBUTES;
no source data is bundled in the tool.

This evidence closes phone identity/audio and engine scheduling. It does not
claim full original speech interruption/priority behavior, complete sound mixing,
all phone UI rendering, or 1:1 engine damage physics.

## Native speech packet and 3DS queue integration

`tools/build_opening_speech.py` accepts only the pinned recovered original mono
PCM and duplicates each sample to left/right, with no resampling or frame count
change. It emits NVS1 version 1: 96-byte header, 61 CRC entries for 4096-frame
stereo PCM blocks, zero padding to byte 352, then 245803 stereo frames.
Header fields fix SMS 10, 22050 Hz, two channels, original selector pair and the
original SCHl SHA-256. The header and CRC index each have their own CRC.

Verified private packet:
`/workspace/port-research/opening-story-services/cellcall10-v1.nvs`, 983564 bytes,
SHA-256 `230f9bf633b020699a1ad0e7a80c9b0f105ecf90e086b79eabe64f3cf63675de`.
(The earlier development `cellcall10.nvs` lacks its index and is rejected by the
loader; use the explicitly versioned `-v1` packet.)

`mw_story_speech_open` strictly validates the original source identity, fixed
bounds, CRC index and padding before publishing a borrowed audio-only `MwMovie`
view. Its video handle is null and frames are zero; this is not a fake video.
`mw_movie_audio_block` validates PCM bytes on worker reads before NDSP submission.
Only the speech file is opened, and ownership ends through `mw_movie_close`.

`MwStoryAudio` embeds that stable view and the existing three-buffer movie audio
queue. Initialize zero and keep its address stable while active. Call
`mw_story_audio_start(audio,path,10)` automatically for the opening CALL_REQUEST,
then `update` each frame. `issued_playback` becomes true after real CRC-verified
PCM submission; the parent career caller should latch that once as CallStarted.
It never reports issued playback when `muted` is true or queue failure occurred.
DSP unavailability remains an explicit muted clock fallback, requiring a visible
caller policy; it is not successful original audio. `finished` reports queue
end (or explicit muted clock end), so callers should also inspect `muted` when
distinguishing real completion. `pause` forwards to the actual queue. `stop`
joins its worker, releases NDSP, closes the speech file and is repeat-safe.
Speech owns channel 0 and DSP for its lifetime; stop before starting a movie.
No new manual answer button is required by this source-backed opening flow.

The ASan/UBSan host test links the existing queue with an owned 22050-Hz mock,
checks every one of the 245803 original mono samples against both output
channels, and covers asynchronous admission, pause/resume, sample-clock EOF,
explicit muted fallback, corrupted first block (never queued), transactional
loader failure and recomputed-header-CRC attacks on source/frame identity.
This validates portable data/queue behavior; it is not a 3DS hardware audio test.
