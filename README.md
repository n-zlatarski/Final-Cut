# Final Cut — Igris animation integration

## Play

Install Python 3.12, then open a terminal in this folder:

```bash
python -m pip install -r requirements.txt
python main.py
```

For a direct throne-room boss fight:

```bash
python main.py --igris
```

Enter your fighter's name to begin. WASD moves, Shift runs, Space dashes,
and left click attacks. Q / right click uses Death's Dance, E uses Sonic
Stream, R restores stamina, and Escape opens the pause menu.

## Igris

The throne-room boss now uses the prepared 11-animation pixel-art set.
All animations have down, left, right and up views. The normal campaign
still brings him in after the throne-room guards are defeated.

| Setting | Value |
| --- | --- |
| Source frame | 128 × 128 RGBA pixels |
| Each atlas | 8 columns × 4 rows, 1,024 × 512 pixels |
| Direction order | Down, left, right, up |
| Feet pivot in the source cell | (64, 96) |
| In-game rendering | Edge-refined pixel scaling, 384 × 384 padded canvas |
| Silhouette width | 90% of the previous build, centered on the feet pivot |
| Standing body height | Approximately 200 game pixels, including plume |
| Logical body geometry | 205 × 205, independent of render padding |
| Frame timing | Per-frame milliseconds in the manifest |

The sprite's feet stay anchored through animation and direction changes.
All poses keep the same render scale; attack and death poses retain their
full transparent padding. The sheets include their pixel ground shadow.

Igris keeps the approximately 10% slimmer silhouette and 200-pixel height.
The finer 128-pixel import retains more armor, helmet and cape detail from
the original artwork than the previous 96-pixel import.
One Scale2x pass refines the large pixel steps before the final resize.
It retains the original palette, armor, cape and animation drawings. The
same adjustment is applied once when loading every frame, including hurt
and death. Combat timing and the fixed feet pivot are preserved.

Igris breathes and looks around outside detection range. Once he detects
the fighter, his guard idle omits the search glances. He walks nearby and
runs when closing a larger gap. His move rotation includes all three sword
attacks, a dash, a running attack and a dash attack. Later phases retain the
travelling shockwave and crescent from this game build.

| Animation | In-game use | Base duration | Contact/release frame* |
| --- | --- | ---: | ---: |
| Idle | Undetected breathing and search glances | 2,450 ms loop | — |
| Walk | Approach / circle the fighter | 830 ms loop | — |
| Run | Close a larger gap | 540 ms loop | — |
| Dash | Reposition without dealing damage | 425 ms | — |
| Run_Attack | Advancing sweep | 550 ms | 4 |
| Dash_Attack | Lunging thrust | 495 ms | 5 |
| Attack1 | Horizontal cut / later-phase crescent release | 540 ms | 4 |
| Attack2 | Rising cut | 615 ms | 4 |
| Attack3 | Heavy overhead cut and shockwave | 880 ms | 5 |
| Hurt | Poise-break recoil and recovery | 450 ms | — |
| Death | Collapse, then terminal corpse hold | 2,060 ms | — |

*Frames in this table count from 1. Code uses zero-based frame indices.
Attack1 replaces the previous repeated hits with one hit matching the
single visible cut; its damage combines the previous three light hits.
Later boss phases speed up the whole attack timeline consistently.

Animation, hit events, projectile release and dash travel share the same
clock. Target or HP phase changes cannot flip or restart a committed move.
Hurt plays to completion even when damage crosses a phase threshold.
Death holds its final frame, and the stage exit waits for the full collapse.

`assets/Blood_Red_Commander/GameReadyDetail/manifest.json` describes the source
frames. `igris_data.py` maps clips to the game's enemy states, and
`entities.py` defines the boss rotation and frame-based contact events.
The original supplied assets are included for reference; the new loader
selects the GameReadyDetail Igris sheets.

## Sword and dash effects

Each sword move has its own short crimson trail: horizontal cuts, a rising
cut, a heavy overhead strike, a running sweep, and a dash thrust. Trails
follow the locked attack direction and use the existing animation clock.

Successful hits add a small spark burst at contact. Dodged or invulnerable
hits do not produce contact sparks. The heavy strike also kicks up ground
fragments at its landing point. Dashes leave up to five short-lived copies
at real movement positions, a red wake, and small takeoff/landing dust.

The effects fade quickly and clear immediately on stagger or death. There
is no persistent idle aura. Effects are visual; movement, attack timing,
damage, collision ranges and the three boss phases remain as before.

`igris_vfx.py` draws the directional sword trails and manages effect
lifetimes. `assets/Blood_Red_Commander/VFX/` contains 18 sliced transparent
texture frames in a 6 × 3 atlas, the generated source, and its art notes.
The source character atlases and their approved duplicate-sword repair are
retained. The finer import uses the same palette and authored poses.

## Verification

Tested with Python 3.12.13, pygame-ce 2.5.8 / SDL 2.32.10 using SDL's dummy
video and audio drivers. These are automated playback and game-flow tests;
desktop fullscreen, controller feel and live audio need checking on the
target machine.

```bash
python tests/verify_igris.py
python tests/verify_gameplay.py
python tests/verify_igris_vfx.py
```

The first check covers 336 action cases: all seven boss actions, four
directions, three HP phases, and 30 / 60 / 144 FPS plus 250 ms update spikes.
It verifies contact frames, single event delivery, fixed pivot rendering,
direction continuity, detection idle, stagger, and terminal death. It also
checks that every other enemy type still loads and updates.

The second check executes the real menu and stage functions with scripted
input. It checks all four rooms, the throne-room boss spawn, final death
completion, exit unlock, and the final result screen. It then exercises
all Igris states and directions in a direct boss fight.

The effects check covers all seven actions in four directions, damage
acceptance, hitstop, lifetime limits and clearing on stagger/death. It also
checks 352 distinct unclipped character frames and all 18 effect textures.

Reports are in `tests/igris_qa.json`, `tests/gameplay_qa.json`,
`tests/vfx_qa.json`, and `tests/appearance_qa.json`.
Screenshots are in `tests/screenshots/`.

To record the same scripted boss playback (requires FFmpeg on PATH):

```bash
python tests/verify_gameplay.py --record Igris_Gameplay.mp4
```

The recording uses extra fighter health and scripted boss HP/stagger
changes to expose all phases without interruptions. Those conditions exist
only in the test script. Normal campaign and `--igris` play use regular stats.
