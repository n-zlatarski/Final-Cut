# Knight vertical walk remake

Only `Knight_1`, `Knight_2`, and `Knight_3`'s `Walk_Up.png` and
`Walk_Down.png` are replaced. Their original Craftpix side walks, idle,
attacks, hurt and death files are preserved.

The source art was created with the built-in image generation tool, using
the original Craftpix neutral and side-walk frames as the model/style
reference. The original three variants have identical body pixels and
alpha masks with a consistent color correspondence. The importer uses
that exact correspondence to apply each knight's original palette to the
same new walk motion; it does not invent alternate costumes or geometry.

The square `source/walk_master.png` is a pose bank, not playback order.
Its first two rows provide the eight down poses. Its third row and the
separately corrected `source/up_second_half.png` provide the eight up
poses; the unused fourth row of the square bank has a reversed back strap.
The corrected strip keeps that strap running toward the same shoulder.

The import script orders these drawings by the actual leading foot and
passing pose. It aligns helmet centers, uses one floor per source row,
samples a shared 64-pixel standing scale, removes chroma green, and maps
colors to the original palette. No joints or poses are drawn, interpolated
or mirrored by the script. The final six strips contain 48 frames in
128-pixel cells, playing at the original 8 FPS.

## Final square pose-bank prompt

```text
Use case: stylized-concept. Create a production 2D coarse pixel-art WALK animation atlas of EXACTLY the silver-grey Craftpix medieval soldier in the input. Match the simple flat pixel shapes, slim limbs and small adult helmet; about64 native pixels tall, enlarged pixel blocks, NOT detailed illustration. Same grey rounded shoulder/leg plate armor, pale scarf collar, brown diagonal leather chest strap, brown waist tunic, black joints, kettle helmet with short brim and dark visor, slim straight silver sword in anatomical RIGHT hand and small steel round/oval shield with dark red emblem in anatomical LEFT hand. No plume, no cape, no skin.

CRITICAL LAYOUT: SQUARE image with FOUR columns by FOUR rows =16 sprites, equal square cells, plain flat bright GREEN #00ff00 background, no text or labels or checkers or shadows. Each cell contains the entire figure at the same scale with large green margins. Root position and head size consistent. This square arrangement is two eight-frame walks split into halves. Frame numbering below is for instructions only, do not print numbers.

ROW1: four FRONT-facing DOWN-walk poses, first half. 1 anatomical RIGHT boot on viewer LEFT extended toward camera/down with straight shin, LEFT boot on viewer RIGHT behind with bent knee. 2 viewer LEFT foot planted under weight, viewer RIGHT heel lifts behind. 3 viewer LEFT leg straight under pelvis supporting body; viewer RIGHT knee bends and swings past, BOTH FEET CLOSE TOGETHER in a narrow passing pose. 4 viewer RIGHT lower leg unfolds toward viewer/down, viewer LEFT heel begins lifting.
ROW2: four FRONT-facing DOWN-walk poses, OPPOSITE half. 5 anatomical LEFT boot on viewer RIGHT extended toward camera/down with straight shin, RIGHT boot on viewer LEFT behind with bent knee. 6 viewer RIGHT foot planted under weight, viewer LEFT heel lifts behind. 7 viewer RIGHT leg straight under pelvis supporting body; viewer LEFT knee bends and swings past, BOTH FEET CLOSE TOGETHER in a narrow passing pose. 8 viewer LEFT lower leg unfolds toward viewer/down, viewer RIGHT heel begins lifting. THESE ROW2 LEGS MUST BE THE OPPOSITE OF ROW1, while the sword and shield stay on their original sides. Sword is always viewer LEFT, shield always viewer RIGHT in the first two rows.

ROW3: four BACK-facing UP-walk poses first half. 9 viewer LEFT leg extended back toward viewer with heel on ground; viewer RIGHT leg bent forward away. 10 left leg bearing weight with right heel raised. 11 narrow passing pose: left leg supports, bent right knee/boot passes close alongside. 12 right leg reaches away while left heel lifts.
ROW4: four BACK-facing UP-walk poses OPPOSITE half. 13 viewer RIGHT leg extended back toward viewer with heel on ground; viewer LEFT leg bent forward away. 14 right leg bearing weight with left heel raised. 15 narrow passing pose: right leg supports, bent left knee/boot passes close alongside. 16 left leg reaches away while right heel lifts. ROW4 LEGS MUST BE OPPOSITE OF ROW3. Back rows show rear of helmet and armor with no face or visor, shield carried on viewer LEFT showing dark leather inner straps within a grey steel rim, sword on viewer RIGHT. Never swap equipment arms.

This is restrained WALKING, not high-knee marching or running. Natural foreshortened steps: clear alternation of boots, weight transfers, opposite knees, contact versus passing, tiny shoulder counter-rotation, head bob at most ONE native pixel. Keep torso height and width, sword, helmet and shield dimensions identical. No copied standing poses moved vertically. No attack swings or trails. Original crisp square 16-bit pixels and simple three-tone steel, low detail exactly like input.
```

## Corrected rear strip prompt

Input: a crop of the square pose bank's fourth row.

```text
Use case: precise-object-edit. Edit these FOUR back-view walking knight sprites. Keep all four poses pixel-for-pixel as close as possible. The brown strap currently slopes down to the RIGHT like a backslash. REVERSE ONLY THE DIAGONAL STRAP, so it slopes UP to the RIGHT like a forward slash (/). It must connect the UPPER RIGHT SHOULDER beside the SWORD ARM, to the LOWER LEFT WAIST beside the SHIELD ARM. Brown diagonal line / on all four backs. Paint the old wrong diagonal area back to the existing grey armor. Do not move or mirror the body or the whole sprite. Shield remains viewer LEFT. Sword remains viewer RIGHT. Preserve every leg pose, helmet, white scarf, belt, green background, exact scale and four-column one-row layout. No new details, no checkerboard, no labels.
```
