# Original positive float-power branches

Original8031CEC0 is a **single-precision powf** implementation. Its initial
argument inspection uses stfs/32-bit fields; exponent2 directly performs fmuls,
and nonnegative exponent.5 calls original sqrtf8031D704. Treating this function
as binary64 pow caused18 downstream mechanical force-call mismatches in3072
bounded cases, even when the final output was eventually rounded to float.

`mw_original_power.c` now implements the verified finite positive/signed-zero
domain for exponents0,.5,1,2. The square-root branch translates the original
integer restoring algorithm: normalize significand/exponent, adjust odd exponent,
perform25 bounded root-bit iterations and apply the last-bit nearest/even rule.
It uses neither host sqrt/pow nor reciprocal estimates. Square uses one rounded
single multiplication. Identity preserves signed zero; sqrt/pow.5 produces+0.
This is authored portable arithmetic, with no executable/code payload embedded.

Unsupported exponents, negative bases and nonfinite input/results fail without
modifying output. The mechanical callback adapter returns NaN on unsupported
domains so the caller rejects. There is no hidden host-libm fallback and no claim
that this small API implements negative-base, fractional-general-exponent or
exception-producing branches of the full original function.

## Verification

`tools/vehicle_power_reference.py` executes the unchanged source powf and sqrtf
windows using the SHA-pinned original DOL. All8276 cases match:7779 finite
results are float-bit identical and497 nonfinite square results are rejected
without output changes. Inputs cover signed zero, subnormal/normal boundaries,
adjacent values around1, largest finite values and2048 deterministic random
positive float encodings at each supported exponent.

Private report:
`/workspace/port-research/driving-runtime/power-verification.json`.
No game code bytes are bundled with it. The report retains source-window digests.
The test establishes the reference's default floating-state outputs, not original
game FPSCR/traps or hardware-wide denormal policy.

The native C ASan/UBSan test independently compares4096 positive square roots to
correctly rounded host sqrtf, verifies float-square rounding/overflow rejection,
checks signed-zero branches and ensures unsupported input leaves output intact.
The updated mechanical comparison also tests its no-callback native default,
which closes the prior18-case binary64-libm discrepancy on the3072-case set.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/vehicle_power_reference.py \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --output /workspace/port-research/driving-runtime/power-verification.json
```

Native test: compile tests/test_vehicle_power.c and source_bmw/mw_original_power.c
with strict C11 warnings, sanitizers and `-lm`. No SDK build, live controller or
original game file is modified by this subtask.


## General positive branch extension

The native implementation now accepts finite nonnegative bases and exponents
0..2, covering all six original stock suspension SHOCK_DIGRESSION-derived
exponents (.7,.8,1-float(.8),.75,.5). The original logarithm/exponential kernel
is evaluated in source instruction order, with explicit single FMA where used.
The source split CP high/low constants and high-part construction differ from
later public fdlibm versions; substituting those newer constants is incorrect.
The fdlibm algorithm reference is attributed with its Sun permission notice.

The extended unmodified-original comparison passes23485 cases:22246 finite
float-bit matches and1239 nonfinite-result rejections. This includes the exact
source IS300 exponent1-float(.8), signed zero, all positive float exponent
ranges, original root/square fast paths and original scalbn underflow calls.
`0x721602c3 ^ float(.7)` must return0x62e85d41. Unsupported exponent or nonfinite
output remains a rejection, with no libm power fallback. Runtime wraps even
caller-supplied suspension math to reject any invalid output transactionally.

Only scalbnf is used for final subnormal scaling; source-reference tests exercise
this path. This extension is not a negative-base/negative-or-large-exponent
implementation or an FPSCR exception emulator.
