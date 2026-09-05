# Sung Jinwoo pixel remake

All character art was made with the built-in image generation tool using the approved Igris style and the generated Jinwoo Idle model. The original game assets remain in `../GameReady/`. Source PNGs are unchanged generated outputs. The art-build script only removes the green background, slices, aligns ground pivots, samples one common pixel scale per row, and maps colors to the shared palette.

The 16 animations retain the game's existing frame counts and combat clocks. Direction rows: down, left, right, up. Igris, class balance, red combat effects, and special skill timing are preserved. Short blue wakes are included in Jinwoo's new dash art.

## Generation prompts

Idle alignment correction (2026-09-05): the six poses in each direction
now use their fixed source-grid centers and a shared floor detected only
in the bottom 5% of the standing figure. The previous per-frame search
occasionally selected the up-facing boots instead of the ground shadow,
introducing vertical glide; slight shadow changes also shifted the left
idle. Generated source art, scales, palette and breathing timing are
unchanged. Other animation sheets keep their existing action anchors.

### idle

```text
Use case: style-transfer.
Asset: production 2D pixel-art sprite animation atlas for Sung Jinwoo, the player assassin in a Pygame action RPG.
Image 1 is ONLY the approved Igris pixel-art STYLE reference: match the simple crisp clustered pixels, restrained shading and slim grown-up proportions. Do not copy his armor, red costume, helmet or sword.
Image 2 is the old Jinwoo identity and idle motion reference. Remake every figure in this atlas to match Image 1's pixel-art treatment, with less fine detail and less oversized/chibi head proportions.

Character invariants: recognizable Sung Jinwoo, young adult Korean male with short messy black hair, small face, slim athletic adult silhouette about six heads tall; long open dark navy-black hooded coat with only a few slate-blue pixel highlights, plain pale grey shirt, black pants, dark shoes with a small pale sole. TWO matching curved blood-red daggers with dark red blade core and one clean red edge highlight, short dark grips and tiny muted brass guards. Clearly visible skin-tone hands fully grip each hilt. No old or additional weapons. Same hair, face, outfit, height, dagger design and proportions in every frame.

Exactly SIX evenly spaced columns and FOUR evenly spaced rows, 24 complete separate figures; readable strict rectangular cell layout. All bodies fit completely inside their cells with ample clear padding. Each row uses the same foot baseline; every figure has a tiny flat dark oval ground shadow beneath the feet to anchor slicing.
Row 1: entire body and feet facing directly DOWN toward camera, six subtle breathing idle phases, daggers lowered.
Row 2: entire body and feet facing LEFT in profile, six subtle breathing phases, daggers lowered.
Row 3: entire body and feet facing RIGHT in profile, six subtle breathing phases, daggers lowered.
Row 4: entire body and feet facing UP away from camera, show BACK of hair and coat, six subtle breathing phases, daggers lowered.
Loop progression: relaxed chest, inhale, slight shoulder rise, exhale, settle, return. Only 1-2 logical pixels of body breathing and coat tip movement; genuine subtle frame progression without large bouncing.

True chunky 16-bit game pixel art, character designed at about 50-60 pixels tall then enlarged with nearest-neighbor. Crisp square pixel clusters, one shared small 24-32 color palette; broad two- or three-tone cloth regions, very simple face, no fabric texture, no tiny laces, no outlines of every fold, no antialiasing, no gradients, no painterly light.
Flat exact bright chroma green #00ff00 background across every margin and cell, no scenery, no grid lines, no labels, no title, no effects, no aura. Landscape atlas aspect 3:2.
```

### walk

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Image 1 defines the NEW simple pixel-art character. Image 2 is ONLY the walking leg/arm POSE reference. Redraw its 24 motion poses as the new character from Image 1, with the chunky pixels and simple shading of Image 1.
Animation WALK: SIX columns by FOUR rows (24 sprites). The six poses MUST alternate these silhouettes visibly:
1. wide split-leg stride, LEFT leg in front, RIGHT leg behind;
2. front foot bearing weight, rear heel lifting;
3. narrow passing pose with legs nearly together, rear foot lifted beside standing ankle;
4. wide split-leg stride, RIGHT leg in front, LEFT leg behind (opposite arm swing to frame 1);
5. opposite foot bearing weight, opposite heel lifting;
6. narrow passing pose again, other foot lifted beside standing ankle.
Frames 1 and 4 have a visibly wider stance than frames 3 and 6. Do not keep feet spread in all six frames. Each actual hand swings with its opposite leg while retaining its dagger. Row 2 faces LEFT in every frame; row 3 RIGHT in every frame; row1 DOWN, row4 UP. Head height and body proportions consistent, coat hem slightly sways. This is calm walking, no effects or speed lines. Bright green background, tiny grounded black oval shadows.
```

### run

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Image 1 is the exact new model and chunky pixel style. Image 2 supplies ONLY the run motion, never its old smooth shading or round head.
Animation RUN. EIGHT columns by FOUR rows, 32 full-body sprites, landscape 2:1 atlas. Eight-phase cyclic run with distinct contact, compression, passing, airborne, opposite contact, opposite compression, opposite passing, opposite airborne poses. Long clear alternating strides, strong 15-degree forward torso lean and athletic bent elbows, both red daggers held securely low, coat streaming backward. Small natural vertical bounce with matching head size in all frames; do not slide copies of a still pose. Row1 runs DOWN toward camera, Row2 runs LEFT, Row3 RIGHT, Row4 runs UP away showing back. All eight poses in each row follow that exact direction. No motion trails or VFX baked into the body.
```

### attack_1

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Animation ATTACK 1: quick leading horizontal dagger cut. SIX columns by FOUR rows, 24 complete figures, landscape 3:2 atlas. Each row is one complete six-phase standing attack in that row's facing direction:
1 neutral ready with daggers low,
2 knees bend, leading dagger draws back near opposite shoulder,
3 fast outward forward slash starts and torso twists,
4 maximum strike extension with leading blade/hand reaching toward the enemy IN THE ROW'S FACING DIRECTION, rear hand and its dagger held close to ribs,
5 follow-through and retract arm,
6 recover to the original neutral stance.
Visible anticipation, contact pose and recovery; feet grounded with small weight transfer and coat swing. Keep two red curved dagger blades physically attached to two visible hands. Lead dagger is short, not a long sword. NO drawn slash arcs or magical effects, only character and actual blades. Row2 ONLY left-facing attacks with extended weapon to image LEFT at contact. Row3 ONLY right-facing attacks with weapon extended RIGHT at contact. Row1 extends toward viewer and row4 away from viewer. All figures maintain same anatomy and clothing, even during crouch.
```

### attack_2

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Animation ATTACK 2: low reverse diagonal rising slash with the OTHER dagger, distinctly different from a straight arm thrust. SIX columns by FOUR rows, 24 full figures, landscape 3:2 atlas.
Six phases: (1) neutral daggers low; (2) low crouch twisting the torso to load the rear arm behind the hip; (3) rear dagger sweeps from low beside the knee diagonally up across the front of the torso; (4) rising slash reaches full extension at shoulder height with the rear arm forward and the opposite hand protecting the waist; (5) twisting follow-through with coat flare and bent knees; (6) recover neutral.
The path is LOW to HIGH, a reverse diagonal slash. Both short curved red daggers always gripped by two visible hands. No drawn effect arcs or sparks. The body must visibly crouch and rotate, with no changes to head size or body proportions. All contact poses row2 thrust/slash toward LEFT, row3 toward RIGHT; row1 faces front attacking downward toward camera, row4 faces BACK attacking away. Same exact NEW chunky pixel character as reference, same small color palette.
```

### attack_3

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Animation ATTACK 3: heavy two-dagger X-cut combo finisher. SIX columns by FOUR rows, 24 whole-body sprites, landscape 3:2 atlas. Same exact model as reference.
Six sequential DIFFERENT body poses: 1 neutral daggers low; 2 deep wide stance preparing BOTH arms; 3 BOTH hands and red blades crossed in a clear X in front of upper chest, compressed stance; 4 powerful outward cut with BOTH arms opening in a wide V and knees braced, torso lunging a little in the row direction; 5 low follow-through, arms extended apart at waist height with coat tails flared; 6 stand and return neutral with blades lowered.
Keep two actual short crimson daggers attached to the hands in all frames, recognizable single continuous blade silhouettes. No effects, no extra blades, no duplicated arms. This finisher must look different from a single-arm thrust or rising slash. Row2 faces and attacks LEFT the entire sequence; Row3 RIGHT; Row1 faces DOWN toward the viewer, Row4 UP away showing the back and the corresponding foreshortened arm action. Ground shadows and foot baselines consistent.
```

### walk_attack_1

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Image 1 is the new character identity. Image 2 is its leading-cut attack to adapt.
Animation WALK ATTACK 1. SIX columns by FOUR rows, 24 sprites, landscape 3:2. Redraw Image 2's six attack phases with continuous WALKING LEG MOTION: 
1 stepping stance with left foot ahead and daggers low;
2 weight shifts onto front foot as leading dagger is drawn back;
3 other knee passes forward while arm begins the horizontal cut;
4 opposite foot lands in front as leading dagger fully extends toward the row direction;
5 trailing foot lifts during follow-through and coat swings;
6 ready walking stride with daggers low.
These must be NEW moving attack poses, visibly stepping rather than standing with planted wide legs in every column. Keep the leading horizontal dagger swing and same anatomy of Image 2. Four exact action directions down,left,right,up. Two daggers and two visible gripping hands in every pose. No effect arcs or speed trails. Same pixel detail and small palette as Image 1.
```

### walk_attack_2

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Image 1 is the new character identity. Image 2 is the reverse rising slash to adapt.
Animation WALK ATTACK 2. SIX columns by FOUR rows, 24 sprites, landscape 3:2. Same six-phase reverse LOW-to-HIGH dagger slash as Image 2, but with walking steps instead of a planted stance:
1 left-foot stride and daggers low,
2 lowered torso loads rear dagger, one planted foot and other heel raised,
3 other knee passes forward as the rear dagger rises diagonally across torso,
4 opposite foot steps ahead as the diagonal slash reaches upper shoulder level,
5 follow-through with the trailing foot lifted, torso untwisting,
6 neutral walking stride ready for next combo.
Visible moving legs, alternating feet, small arm recovery and coat swing. Maintain both dagger designs and both hands from Image 1. Actual body height and head size stay identical even when crouching. Row1 down, row2 LEFT, row3 RIGHT, row4 up; never reverse facing mid-row. No VFX, no lines, no extra weapons.
```

### walk_attack_3

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Image 1 is the new character model. Image 2 is the two-dagger X-cut animation to adapt.
Animation WALK ATTACK 3. SIX columns by FOUR rows, 24 sprites, landscape 3:2.
Six sequential poses: 1 walking stride with low blades; 2 stepping forward with compressed knee stance and arms preparing both blades; 3 knees passing while BOTH daggers cross in X in front of upper chest; 4 opposite foot plants ahead as BOTH arms cut outward into wide V, forceful weight transfer; 5 trailing foot lifts through low follow-through with arms apart; 6 return to ready walking stride.
Preserve Image 2's heavy crossed-dagger body action, but give the legs clear step progression throughout. Never hold the same planted stance in all frames. The model's head, hands, coat and red daggers must be exactly like Image 1, rendered with its restrained pixel detail. Row1 faces down toward viewer, row2 LEFT, row3 RIGHT, row4 away UP. No VFX, no extra arms or weapons, no body scale changes.
```

### run_attack

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Animation RUN ATTACK. EIGHT columns by FOUR rows, 32 sprites, landscape 2:1. A lunging dagger cut while sprinting: 
1 upright ready gait and low daggers; 2 front knee lifts and torso starts leaning; 3 fast forward bound, rear dagger drawn back; 4 planted forward stride as lead dagger slices forward at waist-to-chest height; 5 maximum low lunge with forward hand and short red dagger fully extended toward enemy, second dagger guarding near chest; 6 follow-through with coat streaming and other knee advancing; 7 braking step and retract blades; 8 return to ready running stance.
Every frame has a clearly different pose. Match the same small head, simple broad coat colors and red blade shape as reference. Four exact directional rows down,LEFT,RIGHT,up. Row2 full lunge and weapon reach to LEFT; row3 to RIGHT; row4 head/back facing away. No magic trails or speed-line effects in this character atlas. Feet and shadow stay within each cell even in stretched lunges.
```

### dash

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Animation DASH, an evasive movement with daggers held close, NOT an attack. SEVEN columns by FOUR rows, 28 sprites, landscape 7:4 atlas.
Seven phases: (1) upright ready neutral; (2) knees compress and body coils; (3) push off strongly in facing direction; (4) low stretched fast travel pose with coat streaming behind; (5) leading foot reaches ahead to brake; (6) legs absorb landing, torso rises; (7) ready stance.
Only frames 3,4,5 have a FEW clean electric BLUE/cyan pixel wake streaks immediately BEHIND the coat, fading by phase 6; no giant aura or circles. The real daggers stay BLOOD RED, never blue. The character and two hands stay visible.
Direction is strict: row1 whole body faces camera and dashes straight DOWN, both shoulders and face visible with foreshortened bent torso, wake ABOVE/behind; row2 ONLY LEFT profiles and dash LEFT, wake to RIGHT; row3 ONLY RIGHT profiles and dash RIGHT, wake to LEFT; row4 shows BACK and dashes straight UP, wake BELOW/behind. Do not draw sideways profile lunges in row1 or row4. Keep head and body same scale as reference and preserve the tiny shadow ground anchors. Each complete body and all short streaks fit fully inside its equal cell.
```

### dash_attack

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Animation DASH ATTACK. SIX columns by FOUR rows, 24 sprites, landscape 3:2 atlas.
Six phases: 1 upright ready neutral; 2 compact low windup with daggers held behind shoulders; 3 explosive forward launch with a short blue/cyan wake BEHIND coat; 4 maximum forward DAGGER THRUST, one red dagger and its gripping hand ahead of body, other red dagger guarding near ribs, fast stretched pose; 5 braking low step and dagger retracts, blue wake fading; 6 return to neutral stance.
Two daggers always BLOOD RED with tiny brass guards, visible skin-tone hands. Blue only for a FEW short pixel dash streaks behind the coat in phases3-5, never recolor the daggers. No red giant arcs or drawn duplicate weapons.
DIRECTION CRITICAL: row1 directly DOWN toward viewer, frontal foreshortened crouch/lunge with both shoulders visible, thrust dagger projects DOWN in the image and head remains centered above legs, never a sideways profile. Row2 dashes and thrusts LEFT with wake to RIGHT. Row3 dashes and thrusts RIGHT with wake LEFT. Row4 directly UP away from viewer showing BACK of head/hood, forward hand and dagger reach UP, wake under the feet, never sideways. Every whole sprite and all small streaks inside padded equal cells, source body and head same size as reference.
```

### deaths_dance_spin

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Image 1 is the EXACT new pixel character. Image 2 is ONLY choreography guidance for Death's Dance; do not copy its fine detail or old face.
Animation DEATH'S DANCE, a fast full-body spinning two-dagger special. Exactly TEN columns by FOUR rows =40 complete sprites, landscape 5:2 atlas. Count all ten distinct phases in each row:
1 upright ready with both daggers low,
2 crouched compressed windup with both red blades crossing near chest,
3 explosive forward bound, coat trails behind,
4 first quarter-turn, arms extending blades out,
5 next quarter-turn, body and hips visibly rotate,
6 back-facing half-turn with coat spread by rotation,
7 opposite quarter-turn, continued circular cut,
8 finish rotation back toward travel direction, crossed blades retract,
9 low landing/skid with one knee bent and one hand low still holding its dagger,
10 recovered ready stance.
For this SPIN animation ONLY, mid-spin phases 4-7 naturally rotate the body through front, side and back views; the start, launch, landing and end direction must be DOWN in row1, LEFT row2, RIGHT row3, UP row4. Do not merely reuse one side view throughout the spin. Front-facing travel rows use foreshortened forward motion, never a sideways lunge.
Each cell contains one body, two arms, two legs and two actual short crimson daggers only. No detached slash arcs, no big energy or ghost copies, because those are drawn separately by the game. Maintain source model head size and proportions across all rotating poses; no weapon, hand or coat clipping. Tiny ground oval anchor in every cell.
```

### sonic_stream

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Image 1 is the exact new simple pixel character. Image 2 is ONLY choreography/pose guidance for Sonic Stream; NEVER copy its detailed shading, old head, or noisy weapons.
Animation SONIC STREAM, a fast chained two-dagger barrage with overhead finisher. Exactly ELEVEN columns by FOUR rows =44 complete separate sprites. Wide landscape 11:4 atlas. Count eleven columns, not ten.
Eleven poses in each row, in order:
1 upright neutral ready, low blades;
2 crouched windup with daggers pulled back;
3 explosive low forward launch;
4 extended forward travel cut;
5 rising crossing dagger cut;
6 reverse crossing cut, opposite torso rotation;
7 wide outward double cut;
8 raise both dagger hands above the head for finisher;
9 powerful downward crossing cut, knees bend;
10 low landing/braking crouch, blades near ground;
11 recover upright neutral.
Only one body and TWO short crimson daggers per cell, both held by visible hands, no extra floating weapons, arcs, ghost bodies or magic effects; the game draws the separate effects.
All first four forward travel poses and final three finisher/recovery poses face DOWN in row1 with a foreshortened frontal body, LEFT row2, RIGHT row3, UP row4 with the back of the coat; no accidental side view in down/up travel. Mid-combo torso turns in poses5-7 are natural but feet keep facing the row's action direction. Preserve same model size, small head, outfit and simple pixel density as Image1. Generous complete-body padding and tiny shadow under every sprite.
```

### hurt

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Animation HURT. Exactly FIVE columns by FOUR rows, 20 sprites, landscape 5:4 atlas. Five sequential recoil and recovery poses: 1 neutral standing ready; 2 sharp flinch with chest drawn back and knees giving a little; 3 deepest recoil, shoulders hunched, head lowered, arms tense but both dagger grips still visible; 4 regain balance and raise torso; 5 return to ready.
Keep both red daggers firmly held, whole head and body same actual scale even when hunching. Four exact directional rows: DOWN facing front, LEFT, RIGHT, UP showing back. No red flash drawn into the sheet; game handles the hit tint. No blood, wounds, dismemberment, stars, text or impact effects. Only the complete character and tiny ground shadow; consistent foot baselines and simple pixel palette.
```

### death

```text
Use case: stylized-concept. Production 2D pixel-art sprite animation atlas for Sung Jinwoo. The provided image is the EXACT approved character model; maintain its face, hair, adult slim build, proportions, dark navy-black long open coat, pale grey shirt, black pants, pale shoe soles, and TWO matching curved crimson-red daggers. Clear visible skin hands must grip both short dark hilts with tiny muted brass guards in EVERY pose. Match its blocky 16-bit pixels and restrained 24-32 color palette exactly, no extra texture or detail. No chibi enlargement, costume changes, armor, duplicate limbs or extra weapons.
Flat bright chroma green #00ff00 background; tiny flat black oval ground shadow below each sprite at a consistent feet baseline. No title, text, panels, grid lines or scenery. All figures fully contained with generous padding, each occupies an equal cell and maintains identical body scale. Actual changing joint poses across frames, not copies translated through the cell. Four direction rows: first DOWN facing camera with body and feet toward viewer; second LEFT full left-facing body and left-moving attacks; third RIGHT full right-facing body and right-moving attacks; fourth UP with BACK of head and coat facing camera and action traveling away. Strict direction for entire sequence, no accidental row reversal. Crisp square pixel clusters, no gradients or antialiasing.
Animation DEATH. Exactly SEVEN columns by FOUR rows =28 complete sprites, landscape 7:4 atlas. Non-graphic defeat collapse, no blood or injuries.
Seven clear sequential poses: 1 upright neutral with daggers low; 2 exhausted stagger, bent knees and slumped shoulders; 3 drops onto one knee, coat settling; 4 both knees buckle and torso falls forward/sideways, arms move down; 5 body contacts ground, legs extend; 6 settles onto side with head low, whole body horizontal and coat spread on the ground; 7 final motionless fallen pose, completely collapsed, stays on ground, not rising or disappearing.
Two short crimson daggers remain beside the visible hands as he falls, not floating, no extra weapons. Ground contact plane remains on the same row baseline. Preserve original body proportions and size; foreshorten instead of shrinking fallen poses. Each cell has generous width so the full horizontal fallen body and daggers never clip.
Direction rows start DOWN facing camera, LEFT, RIGHT, UP facing away; falls keep the corresponding viewed side/front/back of the character, no arbitrary different costumes or hair. Same chunky simple pixel style and limited colors as reference; green empty background, flat small ground shadow.
```

### run_attack_fix

```text
Use case: precise-object-edit. Edit this existing Sung Jinwoo pixel sprite atlas. It is an EIGHT-column FOUR-row RUN ATTACK. Preserve the exact same art style, character, colors, grid, body size, all shadows and bright green background.
Fix ONLY the fifth column in row 1 and the fifth column in row 4; preserve every other sprite exactly.
Row1 column5 currently incorrectly turns into a left-facing profile lunge. Replace it with a foreshortened FORWARD lunge directly DOWN TOWARD CAMERA: centered front-facing black hair and face, both shoulders visible, pale shirt visible, bent knees under the body, coat opening on both sides, one visible hand and red dagger thrusting toward viewer down the image. Absolutely no sideways profile or horizontal lean.
Row4 column5 currently incorrectly turns to a right-facing profile. Replace it with a foreshortened lunge directly UP AWAY FROM CAMERA: BACK of black hair centered above the coat, back panel and hood visible, no face or shirt, arms reaching upward away, bent legs below, short red dagger visible above the forward hand. Absolutely no sideways profile or horizontal lean.
Maintain the original row1 and row4 foot-shadow baselines and reference head size. There are exactly two short red daggers, held by the two hands. Do not add effects, words, labels or change any other sprite.
```

### sonic_stream_fix

```text
Use case: precise-object-edit. Edit the supplied Sung Jinwoo SONIC STREAM sprite atlas. Preserve ELEVEN columns and FOUR rows, all character scale, pixel style, green background, ground shadows and model. Correct ONLY these FOUR cells, leave every other sprite exactly unchanged:
- Row2 column4: currently leans/thrusts RIGHT. Redraw it as a LEFT-facing low travel attack, black-haired head at the LEFT front of the body, coat streams to the RIGHT, leading short red dagger extends LEFT from visible gripping hand. Same scale and grounded baseline.
- Row3 column8: currently shows the BACK while lifting both daggers overhead. Redraw the same overhead anticipation with the whole body facing RIGHT in profile, right-facing face visible, a little pale shirt visible in profile, both red daggers held above head by two hands.
- Row1 column10: currently faces a sideways profile in landing crouch. Redraw it as a FRONT-facing landing crouch directly facing DOWN toward viewer, centered head/front hair, two shoulders visible, bent knees below and daggers held low beside the hands.
- Row4 column10: currently shows a RIGHT-facing profile. Redraw the landing crouch directly facing UP away from viewer, BACK of head, hood and coat facing camera, no face or shirt visible, bent legs below and hands with red daggers down at either side.
Keep all corrected hands attached and blade count exactly two. Same anatomy, simple navy coat and red curved dagger design as original. No new effects or labels.
```
