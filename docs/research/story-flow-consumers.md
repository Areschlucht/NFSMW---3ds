# Original story and movie-consumer checkpoint

This pass changes only an authored reference tool and this report. No SDK build,
application/runtime edit, source asset edit or commit was performed.

## Career movie fields: keep the current evidence boundary

The recovered gameplay data really contains IntroMovie (`f572ede8`) and
OutroMovie (`b70268c0`) candidate fields. Their actual movie strings and route
ownership remain valid source evidence. However, the conservative DOL constant
scan found neither field hash materialized, and neither hash is present as a
literal big/little-endian word in the supplied DOL. This negative result does
not prove a field is unused: generic data/script/reflection consumers may avoid
literal hash constants. It also does not justify implementing unconditional
"load event -> play IntroMovie -> race -> play OutroMovie" as recovered original
behaviour. The concrete story consumers and their success/skip/failure gating
remain open.

Likewise, pre-rendered FMV and in-engine NIS are distinct systems. The existing
IntroNis/finish-scene names must not be treated as absent `.vp6` movies or silently
replaced with the similarly named FMVs.

## What the linked-event field actually does in recovered code

The original linked field `64273c71` is materialized at `8019F400..8019F408` and
queried through `80057250` at `8019F40C`, after obtaining the current event's
attribute object via `801A6EB0`. The result pointer is checked, then its first
word is compared with zero at `8019F420..8019F428`.

A zero result takes the alternate path at `8019F42C`; a nonzero result branches
to `8019F438`. The surrounding function `8019F3A8` is performing event cleanup:
its subsequent path zeros manager fields `+1AA4`, `+1AA0` and `+1AAC`. This local
consumer does not set the field's target as a new active event. The exported
partial_dday -> sprint -> sprint -> circuit associations are real source
references, but they must not be labelled proven automatic-success transitions.
The test alone does not establish the linked field's complete semantics.

## Concrete original once-only tutorial producer

`801C65E8..801C6780` provides a useful movie producer with directly traceable
control flow. Its outer preconditions are:

- Global manager at `8041D30C` is non-null.
- Global word `8041ED94` is zero.
- Manager field `+1AA8` equals two.
- Local-player interface lookup `8003CB4C(1)` is non-null.
- The current event at manager `+1AAC` is non-null.

The local-player interface selects a profile record through a virtual getter.
The event getter `801A7320` then returns a numeric type. The selector window
`801C6688..801C6710` uses these exact original cases:

| Event-type return | Profile `+E8` once bit | Original movie stem |
| ---: | ---: | --- |
| 2 | `0x0040` | `drag_tutorial` at `803EEB9C` |
| 5 | `0x0080` | `speedtrap_tutorial` at `803EEBAC` |
| 4 | `0x0100` | `tollbooth_tutorial` at `803EEBC0` |

If the matching once bit is already set, the selector returns no movie. Otherwise
it sets that bit before selecting the original stem. Other event types return no
movie and preserve the profile flags. A selected stem is passed into `801DFB1C`
after state-object lookup `801EB8D0(12)`. This is concrete tutorial selection,
not proof of career IntroMovie/OutroMovie playback.

If no tutorial was selected, `801C6734..801C676C` immediately constructs and
submits an `MNotifyMovieFinished` message rather than waiting for nonexistent
playback. Do not apply this observation to failures after an actual decoder
start; that path has not been established.

## Completion message is not a complete playback outcome

`8017F9A8..8017FA08` lazily hashes the literal `MNotifyMovieFinished`, caches the
result and writes it into the output message. Its six direct call sites are
`8015BBF0`, `8015C16C`, `801C6748`, `801E8708`, `801F2B58` and `80282ECC`.

Both routines `8015BBC0` and `8015C13C` construct/submit this message, then reset
movie-related frontend state. Their presence means that the message name alone
cannot distinguish successful playback, user skip, cancellation or absent-movie
fallback. Original callback registration and each path's caller still need
recovery. A portable completion enum must keep outcomes separate until their
original state consumers are proven.

## Bounded verification

`tools/story_flow_reference.py` pins the USA DOL SHA and executes only
`801C6688..801C6710`. Its event-type getter is explicitly stubbed with a supplied
return value; all other code stays original. It permits only the original write
to profile `+E8`, rejects execution outside the window, checks the actual tutorial
strings at their original addresses, and records code-range SHA-256 values.

480 combinations of event type and profile flags matched the independent scalar
selector. Each newly selected tutorial was additionally retried with the source
once bit set and correctly suppressed. These comparisons prove the bounded
consumer, not the outer preconditions, concrete virtual profile producer or full
movie state machine.

Reproduce from the project root:

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/story_flow_reference.py \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --output /workspace/port-research/story-flow/verification.json
```

Private disassembly windows and verification reports remain under
`/workspace/port-research/story-flow/`. The next gate is locating actual data-driven
career movie consumers and callback registrations before binding original story
transitions to the 3DS event controller. No guessed chronology, generic immediate
story completion or fabricated movie was introduced.
