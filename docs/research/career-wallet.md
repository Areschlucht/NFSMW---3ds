# Source cash reset, opening prizes and wallet award conditions

This pass traces actual original consumers rather than assuming a30000 starting
balance. It adds only `tools/career_wallet_reference.py` and this report. Source
game data, application/runtime code and saves are not edited.

## Actual wallet and initial reset

The original frontend cash label is bound at8012F0C4..8012F0F4. It resolves
`CASH_DATA`, obtains the active frontend profile through manager8041C484+20 and
formats the unsigned integer at profile+F0. This is not a race actor's floating
cash accumulator.

The new-career caller at8013C494 passes profile+E4 to8015FE1C; its first call is
the reset8015FCD4. The bounded prefix8015FCE4..8015FD14 writes:

- Career subobject+0C, which is profile+F0:0.
- Career subobject+08:16, the original intro bin.
- The shown base fields and counters:0.

Four original reset fixtures with prior balances0,1,30000 andFFFFFFFF all produce
cash0 and bin16. This is a proof of the reset consumer and its actual caller,
not a claim that every later callback in the complete original new-career flow
leaves cash unchanged.

No literal or memory-based30000 starting allowance is introduced.

## Exact original prize field

The original current-event getter801A4F3C reads its cached packed scalar when
available; its raw attribute fallback801A503C..801A506C requests fieldD8BAA07B.
The exact VLT hash label is **CashValue**. The source reader checks all five
opening fields against their pinned GAMEPLAY byte ranges and float32 bytes:

| Original event | CashValue |
| --- | ---: |
| 16_2_1_d_day_intro | 0 |
| 16_1_0_partial_dday | 0 |
| 16_2_2_sprint | 10000 |
| 16_2_3_sprint | 10000 |
| 16_1_1_circuit | 10000 |

This is a consumer-backed value binding, unlike interpreting fields from their
numeric values alone. The similarly named CashReward field is not substituted.

## Winner award is conditional

`Game.NotifyRaceFinished` is registered to801C3924. Its wallet-award portion
801C3A48..801C3B28 requires:

1. Racer+10 equals1. That is a1-based ranking: the original ranking loop at
   8019E030..8019E044 invokes setter801A26D0 with loop index+1.
2. The actor supplies local controller index0 or1 through the original interface.
   The reference explicitly supplies this external identity.
3. Current manager+46A8 is clear. The original code sets this per-event cash latch
   before continuing; a repeated finish cannot pay again while it remains set.
4. Current manager mode+1AA8 equals2, the career branch observed here.

The selected profile receives the current event's CashValue after original
`fctiwz` truncation. The reference executes the actual raw-attribute getter and
addition. Attribute lookup, event identity, actor interfaces and prior completion
query are explicit inputs; no original instruction bytes are patched. A returned
previously-completed result is queried before this award but is not itself the
cash gate in this local window. Do not replace the per-event cash latch with a
global rule that no repeated original race can ever pay again.

Three legitimate wins in the three source10000-prize courses therefore total
30000 after a zero reset. **This does not prove the exact original first-car-lot
balance after the scripted Razor loss.** The forced-loss behavior and later story
callbacks are distinct from a native flow that requires those three wins. Native
progression must describe any such flow adaptation honestly.

Lua `Game.AwardCash` is a different path: registration801BF918..801BF934 points
to801C5598, which reaches801C55B8 and801A26D8. The latter adds a float to the
selected racer+134 accumulator. It does not directly increment profile+F0. Treating
both as wallet awards would create an incorrect duplicate accounting path.

## Debit and optional bonus

Original8015FDF8 consumes the career subobject and an unsigned amount. It clamps
cash to0 when the amount exceeds the current balance; otherwise it subtracts.
Thirty original input pairs, including unsigned boundaries, match this behavior.
This leaf is not an affordability/purchase-success predicate: original outer
frontend purchase checks and garage ownership mutation remain separate.

Original801602A0 sets bit2 in career subobject+04. A nonzero second argument also
adds10000 at+0C, preserving unsigned wrapping. Ten original bonus fixtures pass.
The original external detection/caller ordering that chooses that argument has
not been recovered here. **Do not automatically grant this bonus.**

## Verification and reuse

`/workspace/port-research/opening-career/wallet-verification.json` preserves source
digests, original code-window digests, all five source fields and the limitations.
The script passes164 bounded original PPC cases: four reset fixtures,30 debits,
10 optional-bonus fixtures and120 combinations of opening event, rank, mode,
cash-latch state and local controller index.

The source payload and executable are SHA-pinned. All emulated writes are confined
to private fixture/stack memory. Out-of-window execution and instruction-budget
exhaustion fail. These are bounded modeled-original checks, not a complete
GameCube playthrough, save conversion or a3DS performance measurement.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps python tools/career_wallet_reference.py \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --gameplay /workspace/port-research/whole-game-metadata-20261103/GLOBAL-GAMEPLAY-at267364352.BIN \
 --catalog /workspace/port-research/race-story/catalog.json \
 --output /workspace/port-research/opening-career/wallet-verification.json
```
