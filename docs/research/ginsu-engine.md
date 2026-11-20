# Original Ginsu engine synthesis

`mw_ginsu.[ch]` implements the original bank tables, compressed EA-XAS sample
reader and cycle-aligned packet synthesis. It does not repeat the complete
recorded acceleration sweep or synthesize a replacement engine tone.

Private banks and verification report live under `/workspace/port-research/game-audio`.
`tools/build_ginsu_audio.py` verifies the original inventory identities and wraps
88 supplied GIN banks in CRC-protected NGI1 packets. It also emits NGB1 bindings
for103 original physical vehicle profiles and preserves the complete source
attributes in a private JSON manifest. The career BMW and ordinary BMW both use
original engineaudio `tvr_cerb`; their acceleration bank is `b2a1056e.ngi`.

## Source bank and numeric core

The matching debug executable identifies `GinsuDataLayout`: magic/version/flags
at0/4/6, minimum/maximum frequency at8/12, segment/cycle/sample counts at16/20/24,
sample rate at28. All supplied banks use immutable little-endian `Gnsu20` data.
A segment table contains `segCount+1` signed sample offsets; the cycle table has
`cycleCount+1`. Compressed samples follow both tables,19bytes per32samples.
No original code or lookup tables are embedded in the port. The ordinary EA-XAS
predictor coefficients are written as numeric constants; its nibble residuals
are computed arithmetically instead of copying the original decoder's table.

Recovered original methods:

| Method | Original address | Native behavior |
| --- | --- | --- |
| BindToData |800eae74 |Validated bank fields, tables and minimum cycle period |
| FrequencyToSample |800eafc8 |Uniform frequency segments, sample interpolation, source rounding |
| CycleToSample |800eb178 |Cycle-position interpolation and endpoint clamping |
| CyclePeriod |800eb308 |Adjacent-cycle period interpolation with endpoint formulas |
| SampleToCycle |800eb564 |Monotonic table inversion; bounded native binary search |
| DecodeBlock |800ead1c |32float EA-XAS samples with original two FMAs per residual |
| GetSamples |800eb8d0 |Original truncation and signed16 saturation |
| HandlePacketRelease |800eb9f0 |Cycle-aligned jumps, no-jump interval, linear overlap, PCM packet |
| SetSynthData |800ec2b4 |Original11ms packet/no-jump,0.5ms overlap sizes |
| StartSynthesis |800ec478 |Initial numeric playback/current/target/countdown state |
| UpdateFrequency |800ec5ec |Target sample and `floor(milliseconds /11)+1` countdown |

The source24000Hz packet is264samples with12overlap samples;36000Hz uses396/18.
The native queue adapter retains unconsumed packet tails, so an arbitrary512frame
NDSP buffer does not cause extra jumps or discard samples. The complete original
packet's numeric body is compared through800ec134, before platform sound packet
submission. Reference paired-single ABI spills use the existing Gekko hooks;
no source decoder, mapping, jump selection or overlap arithmetic is substituted.
Original platform packet submission, locking and initial two silent packets are
outside this numeric comparison.

## RPM calibration is required

The GIN input is **not raw physical engine RPM**. At800be830..800be878,
`SFXCTL_HybridMotor::UpdateParams` calls `SFXCTL_Engine::GetEngRPM`800c9d1c, which
loads the audio controller's `m_fEng_RPM` at114. It clamps that value to1000..10000,
then applies these original float operations:

```
scale = float((engineaudio.MaxRPM - engineaudio.MinRPM) * 0.00011111111234640703)
requested = fma(float(clamp(audioRPM,1000,10000)-1000), scale, engineaudio.MinRPM)
```

The matching engineaudio layout confirms MinRPM/MaxRPM offsets98/9c. SetEngineParams
copies the resulting `m_GinsuScaledRPM` from the HybridMotor to CARSFX_GinsuEngine.
SingleGinsu clamps requested frequency below the actual bank minimum, while
setting a separate playback pitch ratio `requested / bankMinimum`. Otherwise the
ratio is1. Its800dbc0c call supplies60milliseconds to UpdateFrequency.
`mw_ginsu_engine_frequency` implements and differentially verifies both numeric
fragments. Callers must also apply the returned low-end ratio to transport rate.

The physical engine alone is not the entire original audio controller. Source
shift/transition/clutch behavior, RPM LFOs, redline overlays, Doppler and controller
feedback remain separate producer inputs. Using a recovered physical engine RPM
as the ordinary input is an explicitly limited native adapter until those audio
controller layers are connected. A bicycle speed-derived invented RPM is not
an original source producer.

## Bindings and integration

NGB1 selects by the original physical profile, with optional visual MODEL guard.
It exposes actual acceleration/deceleration NGI filenames, engineaudio identity,
calibration RPM limits and original volume fields. It never chooses one variant
by guessing from a display name. The current binary stock selection uses source
engineaudio RefSpec index0; all original RefSpec variants remain in the private
manifest. Modifications/upgrade selection must supply their actual source index.

NGI1 has a96byte header containing total/raw sizes, header and payload CRCs,
rate/sample count and the original GIN SHA256. NGB1 contains its own CRC plus
attribute/DOL identity hashes. Raw source code and debug metadata are not staged.
`mw_ginsu_bank_open` borrows immutable GIN bytes and allocates nothing; a synth
state keeps only one32float decoded block and a bounded PCM packet. Application
file loading, NDSP channel ownership, worker synchronization and gain policy
belong to the audio runtime, not this portable numeric core.

## Validation and boundaries

`tools/ginsu_engine_reference.py` runs unchanged original mapping/decoder routines
and the complete packet numeric body against native C. The report records exact
PCM samples, all five integer synthesis fields and current-cycle float bits.
It covers the complete supplied bank corpus, varied calibrated frequencies and
stateful packet transitions. Counts in the private report are authoritative.

`tools/test_ginsu.sh` runs strict C11 ASan/UBSan tests with the actual BMW bank and
bindings: source identities,103profile lookup, arbitrary queue chunk equivalence,
in-place packet output, malformed packets and failed-fetch rollback. A visual
legacy approximation is never used to generate engine audio samples.

Original full HybridMotor acceleration/deceleration gain selection, dual-bank
mixing, AEMS bank graphs, spatial attenuation and source startup/transport timing
are not established by these numeric-core checks. Do not describe the complete
in-game soundscape as1:1 based only on this component.
