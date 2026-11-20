# Original sound asset recovery checkpoint

Audio work is paused at the user's explicit priority change to original driving
physics. Do not treat decoded samples or the native audio driver as the completed
original game sound system. No original sounds or converted files are Git inputs.

## Closed work and reproducible tools

`tools/extract_game_audio_assets.py` reads SHA-pinned ATTRIBUTES and ZDIR, recovers
engineaudio field labels from matching DWARF, joins actual pvehicle engineaudio
RefSpec arrays, and extracts source banks by exact archive ranges/hashes. Named
paths are exact source filename-hash matches. A complete top-level header scan
preserves other ABKC/Gnsu banks as explicitly unnamed, without invented identities.
The supplied1363ZDIRrecords contain301ABKC,88Gnsu and9MOIR files. Audio extraction
also includes original MPF/MUS/speech references:414files501163367B total. Three
non-audio duplicate ZDIR keys are present; ambiguous matched audio keys are refused.

`tools/decode_game_audio_assets.py` decodes every original ABK/GIN subsong once
through the existing pinned workspace vgmstream CLI. All389banks decoded:
2663PCM16WAVs122588522B, zero failed banks or streams. Decoder metadata retains
actual rate/channel/sample counts and loop start/end. PCM and WAV hashes are
recorded. No resampling, trimming, synthesized sound or invented GIN loop points.
A GIN WAV is the complete RPM ramp, not a faithful looping engine controller.

`tools/game_audio_event_reference.py` executes the original PPC sound graph
embedded in the original common-menu ABK plus unchanged original DOL AEMS kernels.
Only the original import/static relocation process is applied. Source functions
are allowlisted; writes are constrained to graph state, stack and the actual SND
random-state words. Execution stops at the original SNDplaybank call boundary.
69cases cover23source selectors at three volumes. This verifies sample selection,
not actual DSP playback or every game/AEMS state. Canonical original initial bank
state is used; original runtime controller/event policies remain separate.

Actual common selectors and decoded streams are:

| Intent | Source selector | BNK sample | WAV suffix |
| --- | ---: | ---: | --- |
| Up | 0 | 1 | 5b8b970e_001.wav |
| Left | 2 | 2 | 5b8b970e_002.wav |
| Select | 4 | 3 | 5b8b970e_003.wav |
| Back | 5 | 4 | 5b8b970e_004.wav |
| Wrong | 7 | 5 | 5b8b970e_005.wav |

Down/right/pause selectors1/3/6 reach BNKsample0, which has no admitted decoder
subsong; no replacement aliases are invented as original behavior. The source
PlayUISoundFX800a6624 dispatches0..22 to EAXCommon and23..159 to EAXFrontEnd with
index minus23. The full frontend bank has75decoded subsongs, not yet mapped here.

`tools/build_original_ui_audio.py` exports these five actual clips using the
runtime agent's existing `build_game_audio.encode`, preserving original PCM and
recording original source bank SHA, source graph reference hash, selector, sample
index, original PCM SHA/CRC. Native resident playback is a port adapter; original
full envelope/mix timing is not claimed.

`tools/build_engine_audio_bindings.py` joins actual pvehicle.MODEL text to unique
original ecar.CollectionName text case-insensitively, preserving physical keys and
engineaudio upgrade RefSpec indices. Result:93physical profiles/76ecar IDs,
135sound-upgrade slots, zero missing referenced acceleration GIN files; all63
currently exported roster-physics profiles are covered. Ten source entries with
blank MODEL remain explicitly unbound. Engineaudio has70source collections.
BMW stock and career profiles both reference actual `tvr_cerb`, CarID66; matching
by displayed car name would select the wrong source sound. Source calibration
MinRPM/MaxRPM, volumes and crossover values retain individual field provenance.

## Private outputs

All paths below are under `/workspace/port-research/game-audio`:

- `inventory.json`, `header-inventory.json`, `bank-interfaces.json`.
- `original/<archivehash>.abk/.gin` and other exact source extracts.
- `decoded-manifest.json` and `decoded/<archivehash>_<subsong>.wav`.
- `common-menu-reference.json`:69bounded original selection observations.
- `engine-bindings.json`:full upgrade-indexed source bindings and calibration.
- `native-v1/ui_{accept,back,up,left,wrong}.nag`, `native-v1/manifest.json`:
  five clips145452B total. Stager copies these as `audio/` runtime files.
- Separate agents own `music/native-v1`, `ginsu-native-v1` and native Ginsu
  bindings; do not overwrite their manifests or claim their unfinished work.

Source common bankSHA:
`59ea46087a01a688dcb2f0bedb71795b0931ac1537ea284afe44e7c08a54e234`.
Original BMW acceleration source:
`original/b2a1056e.gin`; main bank `original/ad0559a3.abk` (8decoded subsongs).

## Pending work, not integrated or claimed

Disposable exploratory Siren/Skid/Collision graph probes were copied into private
`in-progress-probes/` before pausing. They are NOT closed reference tooling and
are not runtime assets. Siren type0 appeared to select source bank1553ffcb sample3;
maximal-slip/loads and surface0 appeared to select skid bank2d25da44 sample4.
These probes use explicit platform play/status boundary adapters and still need
proper bounded authored proofs and event-policy review. No siren/skid/impact/horn
NAG export was finalized by this agent.

A further collision-data lead was located but not developed: original supplied
GLOBAL-INGAMEB_VM_NGC.BUN at
`/workspace/attachments/5eb50459-e78b-4b4a-83bf-9026bd60c9f9/GLOBAL-INGAMEB_VM_NGC.BUN`
contains chunk8003b500 at file offset8aab0. Its608collision stitches pair20-byte
0003b502 SND_Stich headers with16-byte-array0003b503 sample references. Original
LoaderSoundStichs800b2c4c and matching DWARF give field layouts. These preserve
actual layered sample IDs/pitch/time offsets for STICH_COLLISION_TYPE enums;
choosing a single collision WAV would not reproduce the original layered event.
No collision cue should be guessed from the global enum as a direct BNK index.

Full original Ginsu rendering, AEMS state/mix/envelopes, police radio sequencing,
frontend-page cue maps, traffic horns, world material-dependent skid/impact cues,
cinematic audio interplay and actual hardware DSP playback remain verification
and integration tasks. No claim of finished game audio or1:1 engine sound.
