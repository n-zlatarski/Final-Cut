# Ten-cut E flurry

This bank extends E using the approved Jinwoo model and existing red effects.
No source pose was repainted, resized, shifted or generated again.

Each direction contains 13 frames in the same 120 × 120 cell and uses the
existing pivot, render offset and exact 2× nearest-neighbor body scale.
Direction rows remain down, left, right, up. The packed sheet is 1560 × 480.

| Destination frame | VideoMatch source animation | Source column |
| --- | --- | --- |
| 0–6 | sonic_stream | 0–6 |
| 7 | attack_1 | 3 |
| 8 | attack_2 | 3 |
| 9 | attack_3 | 3 |
| 10 | attack_2 | 4 |
| 11 | attack_3 | 4 |
| 12 | sonic_stream | 11 |

Frames 2–11 are the ten contact poses. Each is a distinct approved pose;
the last is a crossed-dagger finisher. Frames 0, 1 and 12 provide guard,
forward entry and recovery. Timing is defined in jinwoo_data.py.

The runtime layers a main and offhand trail on every cut, with a third
trail on the finisher: 21 effect layers per cast. Existing rising_cut,
flame_cut, sweep_cut and cross_finish strips provide the red/ivory palette.
Only these effect textures are scaled for the larger finishing cross;
character frames retain their original scale. Short red pose echoes use
the actual displayed frame at its sampled world position.

The extra E effects add one forward spark fan per cut, with five sparks
on ordinary cuts and nine on the finisher. These use code-drawn pixels at
native resolution and exact 2× scaling, with a warm-white, coral and crimson
palette. A larger copy of the approved contact strip adds the finishing
flash. The 21 slash layers, ten spark bursts and one finishing flash total
32 effect layers per cast; all expire by the end of E's recovery. Timing,
damage, movement and body artwork are unchanged by this effects pass.

Other animations and effects resolve through the previous AbilityPolish
bank. Rebuild this bank with tools/build_jinwoo_e_flurry.py (Pillow).
frame_metrics.json records the 52 source mappings, bounds and frame hashes.
