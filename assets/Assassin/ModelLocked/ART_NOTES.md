# Approved Jinwoo attack model

The user-approved source is `source/approved_attack1_right.png`. Its four
interior poses form right-facing Attack 1. Exact original PixelRemake guard
frames provide stationary attack entry and exit.

Nine clips contain 264 body frames: six poses in each direction for three
standing combos, three moving combos and dash attack; twelve per direction
for Q and E. Moving clips are shared by walking and sprinting, using actual
world movement. All four directions are authored separately.

The builder keys the exterior matte, slices complete figures, uses one scale
per directional sequence, and maps to the original 28-color body palette.
Crouching or raised arms never determine independent pose scales. Cells are
120 x 120 with native feet pivot (60,88); the game draws at exact 2x
nearest-neighbor scale. Actual pale boot soles align to the corresponding
approved idle sole level. Generated shadow thickness cannot lift the feet.

Complete generated correction poses fix left-facing Q/E contacts and rear
thrust occlusion. A separate down dash sequence retains the front view.
Two interchanged moving Attack 1 contact cells are swapped. Moving Attack 3
uses the standing rear contact as its planted braking pose. The manifest
records selections; original generated images and source hashes are included.
No body parts are procedurally painted or composited.

The previous separately generated pixel effect bank is retained. Runtime
mapping uses waist trails for Attack 1, rising arcs for Attack 2, and an exact
vertical reflection of paired streaks for the descending Twin Rake. Q/E
echoes, contact sparks and blue wakes remain separate from the body.
Cut trails begin at the contact pose, with the Twin Rake placed beside the
lowered daggers. Away-facing rake effects draw behind the coat.

Idle, walk, run, ordinary dash, hurt, death and portrait bytes remain in
PixelRemake unchanged. Igris and knight source files are also unchanged.
Pose clocks retain previous damage times, recovery, costs and cooldowns.

Rebuild from the project root:

```bash
python tools/build_jinwoo_model_locked.py
```

Optional art dependencies: Pillow, numpy and scipy. Gameplay only needs the
packages listed in the root requirements file.
