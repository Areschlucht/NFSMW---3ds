# Whole-game fidelity requirements

Current scope agreed with the user, 2026-11-03. This supersedes earlier prototype
preferences; it does not describe features already implemented in v0.18.

Target the USA GameCube release of Need for Speed Most Wanted (2005). Preserve
original behaviour and content, with deliberate adaptations for 3DS controls,
two screens, storage and hardware limits. Do not substitute a map viewer for a
complete game, or claim 1:1 fidelity from recovered parameters alone.

Required systems:

- Original boot/legal/loading sequence, iconic Press Start screen, frontend style,
  profiles, career, Quick Race, Challenge Series, garages, shops and save/load.
- Career introduction, Blacklist progression, race unlocks, rewards, story calls,
  cutscenes and ending; original event routes, rules, countdowns and results.
- Original city, section streaming, district locks, race-specific barriers,
  visibility, collision, traffic, police, pursuit breakers and breakable objects.
  Race barriers must not become arbitrary free-roam walls. Activation must govern
  rendering and collision together, preserving legitimate career restrictions.
- Original vehicle roster and variants, customization, damage, drivetrain,
  handling, tires, handbrake, nitrous, Speedbreaker and camera behaviour. Recover
  both numerical parameters and their original consumers and state transitions.
- Original material appearance, reflections, fog, sky, lighting and effects.
  Original-style warm visual treatment is mandatory by default with no filter
  disable option. Earlier optional/neutral prototype settings are superseded.
  A yellow multiplication is not evidence of matching the original render chain.
- Working vehicle lighting for the BMW and every imported car: original lamp
  geometry, texture aliases, headlamp/brake/reverse states where present, damage
  effects, and applicable emergency lights. Preserve original per-car differences.
- Complete sound: individual car engine profiles, RPM/load/accel/coast/shift and
  induction/exhaust layers; tires/surfaces, impacts, breakables, ambience, traffic,
  police, menu effects, speech/calls, cutscene audio, EA Trax and pursuit music.
  Recover original bank sharing and mixing rules rather than one generic loop.
- A stable bottom display and readable original-style HUD/frontend adapted to two
  screens. Profile crowded views on hardware; avoid relying on boosted CPU mode
  to conceal excess draw submission, transparency or streaming costs.

The user reports approximately 15 FPS near arrow walls even in New 3DS enhanced
mode. Fix correctness and measure rendering cost before adding expensive effects.
Old 3DS remains a feasibility target; emulator performance does not certify it.

Track each subsystem as input available, schema recovered, consumer recovered,
integrated, compared with the original, and hardware verified. No invented
completion percentages. See docs/research/whole-game-audit.md for current evidence.
