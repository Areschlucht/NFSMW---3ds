# Audio and complete vehicle-roster pass

User asked to continue adding all original game sounds and cars while away.
This is an integration checkpoint, not a claim every sound/car is finished.

## Roster

Private expanded assets: /workspace/port-research/all-native-cars/v3. It contains
69 verified native NFM/NWA models and1213verifiedtexturebindings,318144triangles.
Original package coverage83; blocked cases are retained with reasons, never
replaced by placeholder cars. RootBMW remains available separately. Source
PlayerUsable metadata identifies35expandedplayer models plus the originalBMW.

NVCversion2 uses row20bit0 for actual pvehicle.PlayerUsable; it does NOT award
ownership/unlocks or invent a frontend price/key. Old NVC1 remains readable.
Native bounds now admit actual trucks up to16m halfextent (observed6.636m).
Stager merges expanded models with the integrated12openingmodels taking priority,
adds PlayerUsable provenance, and generates source-bound origin/FEstance/wheels.
Root has a catalog-driven CAR VIEWER under main MY CARS: A views;Y drives in
explicit unlocked exploration. Safehouse MY CARS still shows the owned car.
The current car uses the existing native planar driving backend, not newly
claimed original handling for every vehicle. Original dynamic profiles are six.

## Audio

Private inputs/outputs: /workspace/port-research/game-audio. All320ABK/GINbanks
were decoded to2305WAVstreams, with original sample counts/rates/loop metadata.
Original engineaudio collections70 and physicalvehicle bindings103 are recovered.
Both supplied BMW profiles actually bind the TVRnamed source bank; names must
not be used to guess engine identity. GIN ramps are NOT ordinary looping clips.

All53MW_MUSIC descriptors converted to native NAG1 under game-audio/music/native-v1:
122294176sourceframes,489303584B, no resampling/padding. vgmstream preserves
samples FFmpeg truncated. Sequential segment order and restart-after-cinema
are explicit native playback policies, not recovered PathFinder playlist logic.
Song titles/artists and dynamic chase score interpretation remain unclosed.

Root game-audio integration shares channel0/NDSP ownership with movies/phone
by stopping music BEFORE admitting either. L skips to the next source segment.
SD/decode/CRC work lives in the existing bounded three-buffer worker, not event
callbacks. Cached verified menu effects use accept/back/up/left/wrong; source
Down/Right dummy behavior must not be relabelled as UP. Actual UI bank graph
functions and unchanged original AEMS kernels resolve event-to-sample bindings.

Game audio remains explicitly unavailable when NDSP fails; emulator currently
lacks its DSP input, so queue/mock tests must not be described as audible hardware
verification. The new engine-only driver uses verified EngineRacer at60Hz and
requires source contact/wheel/owner/settings producers. It refuses invented RPM
from planar speed. A real Ginsu grain core/metadata and the actual source RPM
producer integration are separate gates, not solved by decoding an entire ramp.

## Work ownership and next steps

Root owns rockport_main, staging, SDK integration and GitHub backup.
Audio runtime agent owns mw_game_audio/audio_stream + music exporter/tests.
Audio assets agent owns bank extraction/decoding and original event bindings.
Ginsu agent owns pure original grain metadata/player recovery.
Roster agent owns full converter/coverage and remaining DB9/Cayman recovery.
Engine audio-driver agent completed provider-gated sixprofile tests.

Run SDK build and native asset tests after integration. Verify car browser,
large models, car changes, movie/phone yield, next-track and failure behavior.
Do not publish original archives, decoded PCM, converted game models or binaries
in the source backup. Private runtime staging is not a release ZIP.
