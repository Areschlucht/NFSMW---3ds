# Source route selection and race session lifecycle

The initial source phase used host checks only. The user subsequently authorized
a preview build and emulator screenshots; see race-menu-preview-validation.md.
No release ZIP or physical hardware test was performed. The app source now connects its Quick Race page to recovered course data and
Alias-bound preparation. Races remain explicitly unavailable to start.

## Original names and bounded data

The original frontend derives a language key from fieldA78403EC using TRACKNAME_,
replaces dots with underscores, then applies the original uppercase hash.
The pinned English chunk resolves175 of277 source definitions. Other names stay
missing; no invented titles or filename-based mode classification are supplied.
See race-display-text.md for284 original comparisons and malformed-input checks.

NRE1/version3 adds a display-title string offset in each64-byte event record.
The native reader still accepts version2 and returns an empty title there.
The new private pack is `/workspace/port-research/race-story/events-v3.nre`
(138,094 bytes). Source data and media stay outside Git. A future authorized
installation must place this pack at `sdmc:/3ds/nfsmw-rockport/events.nre`.
The existing app installation/release ZIP has not been changed.

The app treats the pack as optional during development: absent data retains an
unavailable Quick Race page; present but unreadable/malformed data is an error.
A complete validated catalog stays alive until shutdown. Both title strings and
spatial/reference data are borrowed without per-frame allocation or disk reads.
The full body font renders localized names; it is not replaced by a title atlas
that lacks lowercase glyphs. Built-in fallback text also accepts lowercase.

## Preparation lifecycle

`mw_race_session.[ch]` prepares original P2P/circuit courses against a selected
valid Alias and a controlled actor identity. It copies exact ordered keys into
owned fixed storage and preserves source start transforms. Caller code must not
move a prepared session, whose route borrows that owned storage. Other source
mode rules remain unsupported rather than silently behaving as circuit races.

The lifecycle is Loading -> Ready -> Running -> Finished, with Pause/Resume and
Cancel. All three admissions (render, collision, original event activation) must
be confirmed before Ready. Countdown/intro completion remains a caller action;
there is no guessed countdown duration or auto-skip. Only the controlled actor's
authoritative trigger-entry notifications can advance the route. Paused, loading,
finished, cancelled, wrong-actor and out-of-order notifications cannot advance it.
No career reward, win, unlock or persisted career completion is invented.

The source UI lists79 localized preparation candidates from82 supported source
courses. Selecting one prepares the session and shows a race-setup page with its
original name and an explicit unavailable message. There is no Start button until
missing runtime admissions and physical trigger integration are implemented.
Back cancels preparation. These are candidate browsing/source preparation, not a
recovered original Quick Race eligibility, ordering or career-unlock list. Intro
and template ownership must still be filtered by the original mode consumers.

Host ASan/UBSan tests pass82 complete lifecycle simulations, pause-safe timing,
loading admission failures, wrong-actor suppression, one-shot finish/cancel,
Alias validation and transactional prepare failure. Both v2/v3 catalogs pass the
existing216-route test. Every79-item list window and preparation heading renders
within guarded framebuffer bounds. These are host inputs, not driven races.

## Collision reference correction

The old14/160 aligned-box discrepancies are explained by an original directed
contact-generation routine rather than symmetric overlap. The independent model
matches2,320 original queries on1,160 aligned pairs; source tie order X/Z/Y matters.
See race-gate-reference-resolution.md. Rotated queries, actual vehicle providers,
swept motion and notification scheduling remain open, so no guessed symmetric
SAT or point/radius detector was installed in the driving loop.

## Legitimate career district barriers

The user confirmed progression locks while playing the GameCube version through
Nintendont. Career district restrictions must remain, independently of inactive
race-only arrow walls. Original profile-bin selection resets old barrier state
before applying the selected bin's source plan. See career-region-gates.md.
Absent groups in a new bin must not be interpreted as retaining the old plan.
The original plan data is not replaced by guessed geographic thresholds, and
source flag0x400 must not be reduced to a visibility Boolean. Collision ownership
and the per-Alias original career-state producers remain integration work.
