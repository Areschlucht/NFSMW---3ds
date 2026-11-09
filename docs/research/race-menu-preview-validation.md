# Authorized preview build and actual emulator captures

After the source checkpoint, the user explicitly requested a build and screenshots.
The pinned SDK compiled/linked `nfsmw-race-menu-preview.3dsx` successfully. This is
an emulator preview, not a complete-game release or a physical3DS validation.

The existing private SD installation was backed up before overlaying the new
preview executable and events-v3.nre as events.nre. The actual running Azahar
session successfully reached Press Start, Alias Manager, software-keyboard Alias
creation, main menu, original-named course selection, unavailable preparation,
return-to-menu and existing streamed-world driving. The created Alias save's full
CRC, selected ID and monotonic ID header were checked independently. Five idle
menu captures have identical bottom-screen pixels. This is not proof that every
reported hardware flicker or applet issue is resolved.

During software-keyboard return the emulator logged its unimplemented
ConfigureNew3DSCPU service warning; the application resumed, saved the Alias and
continued navigation. No emulator service was patched or game result fabricated.
The old failed duplicate launch was stopped; existing input/cache data retained.
No hardware performance claims are inferred from emulator counters.

`docs/previews/race-menu/` contains actual captures, cropped at native screen
resolution from the1024x768 emulator desktop: rectangle400x480 at(312,192).
The top400x240 display and centered bottom320x240 display retain their pixels.
No scene rendering, visual enhancement or generated game imagery was substituted.

- main-menu.png: selected test Alias and new frontend source running.
- course-selection.png: original localized route labels; preparation candidates,
  not proof of original Quick Race eligibility or unlock state.
- free-roam.png: existing original-city rendering and provisional driving.

Public screenshots are documentation captures, not raw original texture/movie
assets. Original archives, media, converted assets, SD backups and executable
artifacts remain private. Private full captures, input hashes and verification:
`/workspace/port-research/race-menu-preview-20261109`.

Racing, story playback, complete career persistence, correct dynamic barrier
activation/collision, all vehicle integration and original materials/handling
remain unfinished. In particular the visible race-only arrows in free roam are
still the known prototype bug, distinct from the legitimate recovered career
region locks. No release ZIP or public binary release was published.
