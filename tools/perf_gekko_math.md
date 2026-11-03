# Portable Gekko reciprocal estimate and original square-root stages

New isolated runtime files: `include/mw_gekko_math.h` and
`source_bmw/mw_gekko_math.c`. They provide a binary64 reciprocal-square-root
estimate and two distinct original caller stages. No emulator, external reference
source or runtime download is required by the3DS functions.

The helper closes measured precision differences:

- Raw estimate:zero bit mismatches across65536 normalized mantissa cells and
 106195 IEEE754 patterns, including every normal exponent, subnormal powers,
 random lower mantissa bits, signed zeros, infinities and NaN payloads.
- Each original Newton stage:zero float-bit mismatches across85542 finite
 positive/signed-zero inputs against original scalar PPC with the pinned
 reciprocal-estimate oracle.
- LOD producer using the new portable two-refinement callback:all9510 scores
 match the original. Ordinary `sqrtf` differs in85 boundary-focused cases.
- Driving specialist confirms3936 complete contact cases now match original
 force/spin/discrete-state fields exactly;2051 frame and2051 world-force cases
 also match after adopting the helper.
- Collision specialist confirms3666 full body-friction cases now match exactly,
 eliminating all47 previous stick/slide branch mismatches. Further collision
 producer integration is owned by that specialist.

These are bounded reference comparisons, not a proof of every possible program
input or physical hardware timing. Actual frame performance remains to be
measured on3DS. No clocks/cache settings are changed.

## Independent implementation and numeric derivation

`perf_gekko_derive.py` compiles the already checksum-pinned external Dolphin
reference solely as a host test oracle through the existing adapter. It never
parses/copies that implementation. Numeric constants are identified with64
functional queries:the start and next15-bit mantissa tick of each of32 segments,
covering both normalized exponent parities. Every65536 normalized tick is then
checked independently against the inferred piecewise-linear behavior.

The runtime independently extracts IEEE754 sign/exponent/fraction, normalizes
subnormals, selects one of16 segments for the exponent parity, subtracts the
observed decrement times the low11 tick bits, and constructs the result bits.
Lower37 fraction bits do not affect these observed estimate cells. Each segment
has a27-bit-or-smaller observed numeric intercept and16-bit decrement. Numeric
constants and query methodology/provenance are saved in
`hardware-optimization/gekko-math/estimate-validation.json`.

Special cases retain signed infinities for signed zero, zero for positive
infinity, canonical quiet NaN for negative nonzero values, and original NaN
payload/sign with the quiet bit set. FPU exception/status registers are not
emulated. Caller stages are validated on finite positive inputs and signed zero;
arbitrary nonfinite arithmetic/FPSCR modes are outside that validation.

## Distinct original caller arithmetic

`mw_gekko_sqrt_newton1` reproduces80193420..80193454. If input compares equal
to zero, return the input, preserving negative zero. Otherwise:

```text
estimate = original_binary64_frsqrte(input)
reciprocal = round_to_float32(1 / estimate)
sum = round_to_float32(fused(input * estimate + reciprocal))
result = round_to_float32(sum * 0.5)
```

This is used by complete contact normalization and body-friction thresholds.
Do not substitute the two-refinement stage simply because both resemble sqrt.

`mw_gekko_sqrt_newton2` reproduces801916DC..80191738 and the equivalent LOD
sequence802BEBDC..802BEC00. Inputs<=the original float constant
5.00000006675716e-11 return positive zero. Otherwise start with the binary64
estimate and repeat twice:

```text
square = round_to_float32(estimate * estimate)
half = round_to_float32(estimate * 0.5)
residual = fused_float32(1 - input * square)
estimate = round_to_float32(fused(residual * half + estimate))
result = round_to_float32(estimate * input)
```

The initial estimate must retain its binary64 bits; rounding it to float before
the original arithmetic loses information. The implementation uses explicit
float round points and `fma`/`fmaf`, preserving fused operations. Compiler flags
must retain IEEE arithmetic; do not enable fast-math or reassociation.

The LOD module still exposes an explicit sqrt callback and retains `sqrtf` as
its NULL-callback control. Pass an adapter returning
`mw_gekko_sqrt_newton2(squared)` for the measured original boundary behavior.
Physics/contact uses the first stage; ground-normal and LOD use the second.

## ARM cost and validation

Pinned devkitPro ARMv6K hard-float compile passes `-O2 -Wall -Wextra -Werror`.
Object text/rodata totals828 bytes, including the256-byte segment array; data
and BSS are zero. External symbols are `fma` and `fmaf` supplied by existing
libm linkage. This object size excludes any newly pulled libm implementation.
Software fused operations have a cost on this hardware; an actual linked size
and frame benchmark are needed before claiming a speed improvement.

Reproduce cached offline host validation:

```sh
PYTHONPATH=/workspace/toolchains/python-deps python tools/perf_gekko_derive.py
PYTHONPATH=/workspace/toolchains/python-deps python tools/perf_gekko_verify.py
PYTHONPATH=/workspace/toolchains/python-deps python tools/perf_lod_score_verify.py
```

Original PPC is SHA-pinned to the supplied USA executable. The host oracle
intercepts only unsupported `frsqrte` estimates; all contributing original scalar
Newton/fused arithmetic executes unmodified in bounded Unicorn ranges. Raw
estimate special-case verification separately compares exact binary64 result
bits. JSON reports and source hashes are under
`/workspace/port-research/hardware-optimization/gekko-math/`.
