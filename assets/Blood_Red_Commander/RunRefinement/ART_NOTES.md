# Igris run and attack refinement

The recording showed a run cycle that reused almost the same supporting-leg
pose through both half-strides, with abrupt flight poses. The replacement uses
distinct contact and passing poses, one scale per source sheet and a common
floor for each source row. Helmet landmarks register the body independently of
the moving cape, plume and feet. Left is mirrored around the exact existing
feet pivot. Only Run artwork changes; the approved idle, walk, dash, attack,
hurt and death drawings remain intact.

Runtime fixes retain normalized gait phase across walk/run transitions, apply
a small directional dead band while steering near diagonals, and advance gait
by actual distance traveled. Faster boss phases therefore move the legs faster;
a blocked movement tick does not keep running on the spot.

Attack1 and Attack2 have stronger anticipation and faster release. The impact
timestamps, active-window ends and total durations stay unchanged. Generated
crimson cuts, a diagonal finisher, ground-impact ring and contact flash are
layered and timed by igris_vfx.py. Contact flashes require an accepted hit;
ground impact requires the slam event. Hurt/death cancel effects immediately.
There is no idle aura. Damage, attack ranges, cooldowns and boss sequencing
are unchanged.

## Source and build

Artwork was created/edited with the built-in Imagegen tool. The script
tools/build_igris_refinement.py performs only chroma removal, slicing, palette
mapping, fixed transforms, mirroring and atlas packing. It does not paint
character poses. The native cells remain 128x128, pivot (64,96), with the
approved 384x384 render canvas and 90% width.

Run sources are source/run_side.png, source/run_vertical.png (front eight
frames only), and source/run_rear.png. source/shadow.png is the original shadow
extracted from an airborne run frame. The rear order is in manifest.json.
Effects are in ../VFX/Crimson_Attacks_Source.png and Crimson_Attacks.png.
The final prompts below preserve the complete generation/edit instructions.

## Side run prompt

undefined

## Front and rear run prompt

undefined

## Rear pose correction prompt

Use case: precise-object-edit. Edit ONLY the lower-body leg and boot poses of these eight back-facing red knight sprites into a complete chronological running cycle. Keep every helmet, plume, cape, armor design, sword, arm, background, and body scale unchanged. Exact FOUR columns by TWO rows, all eight face AWAY from viewer. The existing strip incorrectly keeps the same foot extended almost every frame. Correct it with eight visibly distinct running poses. ORDER left-to-right top then bottom: Frame1 LEFT boot (screen left) planted lower, RIGHT knee bent with right boot raised behind. Frame2 LEFT boot pushing off at the toe, RIGHT leg swinging past left, ankles close together under hips. Frame3 RIGHT leg stretching downward for landing while LEFT knee is folding backward, right lower than left. Frame4 RIGHT boot planted on the ground, LEFT boot raised, legs separated. Frame5 RIGHT leg under body straight bearing weight, LEFT knee bent. Frame6 RIGHT boot pushing off, LEFT leg swinging past right, ankles close together. Frame7 LEFT leg extending down for landing, RIGHT knee folded with right boot raised. Frame8 LEFT boot down at ground, RIGHT boot raised and folding up. Exaggerate these differences enough to read at 64px sprite height: clearly alternate which boot reaches the floor, include TWO passing poses with feet near each other and TWO push-off poses. Only two anatomically connected legs per sprite. Slight two-step body bounce allowed by translating upper body a few pixels, but do not redesign or recolor anything. Maintain each character's upper body center and stable ground baseline per row. Background perfectly solid chroma green #00FF00. No numbers, labels, effects, shadows or grid.

## Attack VFX prompt

undefined

## VFX background cleanup prompt

undefined

