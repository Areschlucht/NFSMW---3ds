# Native game audio and complete music-segment conversion

`mw_audio_stream` reads source-bound NAG1 native PCM packets. A 128-byte header
validates rate/channel/frame/loop ranges and the CRC table before publication;
each 4096-frame payload block must pass its CRC before it can be submitted.
Payload remains lossless signed16LE stereo: original mono is duplicated without
resampling. Cached effects/engine loops validate all selected blocks up front.
The source SHA records the original bank or exact source segment; per-file
manifests retain original stream indices, offsets and decoder provenance.

`tools/build_music_audio.py` converts all 53 actual MW_MUSIC descriptors in the
supplied full MUS/MPF pair. The private native-v1 manifest and packets are under
`/workspace/port-research/game-audio/music/native-v1`. Total122,294,176frames at
24kHz, 489,303,584native bytes. Source clips vary from subsecond transitions to
several-minute tracks. Descriptor order is an explicit native sequential-play
policy, not the original PathFinder interpreter, not a recovered radio playlist
and not a verified title/artist map. Original interactive music banks1..4 are
not silently folded into this menu/licensed bank.

FFmpeg decoded segment001 23samples short. The converter instead uses the
existing private vgmstream decoder's EA-XA path; all53 decoded frame counts now
match their original SCHl declarations exactly. No fabricated silence repairs
truncated output. Conversion never loops, fades or resamples source songs.

`mw_game_audio` borrows the already-tested movie audio three-buffer worker for
music/channel0. It exclusively owns NDSP while active. Channels1 and2..6 are
engine and five cached effects. Parent must stop it before starting movie or
story speech, then restart the desired music segment afterward. This restart is
a native presentation policy, not sample-exact original music resumption.
The main update performs bounded queue/state work only, with no file reads.
Music's worker reads/CRC-checks three fixed4096-frame buffers; effect loads occur
only at scene/model load time, never on repeated UI or collision events.

Unknown DSP availability produces an explicit muted state. Muted playback is
never counted as issued PCM, and cached effects/engine playback refuse it.
Pause freezes all admitted channels. Stop first joins any engine worker, clears
all game channels, then stops/joins music and releases its NDSP owner before
freeing sample memory. Failed/corrupt payloads are not submitted.

Two distinct engine APIs avoid treating an entire GIN ramp as an idle loop.
The small cached-loop API requires actual source loop bounds and source reference
RPM; it rejects uncalibrated/preview loops and nonfinite or unknown engine RPM.
The original Ginsu packet renderer can instead attach through
`mw_game_audio_engine_stream_start`: a dedicated worker invokes its bounded,
allocation-free PCM callback into three512-frame mono buffers on channel1.
The worker owns synth state; main passes actual RPM/load through a lock.
Inputs derived by guessing RPM from planar vehicle speed are not source RPM.
The transport does not invent Ginsu selection/crossfade behavior: that algorithm
is recovered separately. Starting one engine transport excludes the other.

Host strict C11, ASan and UBSan tests cover actual original music EOF/sample
counts, cached effect replay and replacement guards, source-calibration gates,
pause, NDSP release/reacquisition, muted status, delayed payload corruption,
engine callback buffering/disable/worker failure and owner cleanup. An explicit
TEST-ONLY loop/calibration fixture exercises the transport; it is not staged as
original engine audio. The mock callback copies source PCM and does not establish
original Ginsu synthesis parity or actual hardware sound quality.


`mw_ginsu_audio` loads a bounded NGI1 CRC wrapper around an immutable original
compressed GIN bank, checks optional selected-bank SHA identity, rate/sample
counts and payload CRC, then supplies the queue callback. Stop/join the worker
before closing the bank. Calibration now uses the separately recovered source helper: clamp source
audio-RPM to1000..10000, then the original float-FMA mapping into the selected
engineaudio MinRPM/MaxRPM. Below the bank minimum, source grain frequency clamps
to that minimum and NDSP pitch uses requested/minimum. Calibration is mandatory
before the worker starts. `mw_ginsu_audio_frequency` gives the main thread the
same immutable mapping for `mw_game_audio_engine_stream_rate`; it never reads
worker-owned synth state. Actual CarSoundRealtime audio-RPM/LFO/load providers
remain distinct from simply guessing RPM from vehicle speed.

The original60ms transition call is retained. Starting directly at current
calibrated frequency is explicitly a native warm-start policy: exact original
constructor position, two initial zero packets, queue/control cadence and
complete HybridMotor gain/Doppler/shift/deceleration selection are not all
ported. Numeric original synthesis evidence must not be presented as complete
VehicleSFX timing or layer parity. A strict sanitizer adapter test compares eight
complete512-frame outputs/state against the actual direct source-core calls and
checks calibration/startup/selected-bank/payload rejection.


Source-metadata siren/skid/ambience loops can use `load_loop`; native preview
loop flags are refused, and `stop_effect` clears a specific admitted source loop.
These transport APIs do not invent source event thresholds or spatial mix.
