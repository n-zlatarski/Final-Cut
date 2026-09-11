# Jinwoo video-reference remake

This bank implements the user's supplied Q and E videos and replaces the
three auto-attacks. See the root README for inputs, timings and validation.

## Reference interpretation

- Q, `source/references/Sung_Jinwoo_Q.mp4`: advancing spin, airborne turn,
  ground strike, three eruptions. Convert purple effects to crimson red.
- E, `source/references/Sung_Jinwoo_E.mp4`: entry, five quick slashes,
  backstep, throwing release, one fiery impact explosion.
- Model, `source/references/approved_idle.png`: approved slim dark coat,
  spiky black hair, pale shirt and soles, short crimson curved daggers.

## Source organization

The 17 generated PNGs contain three standing combo sheets, three separately
drawn moving combo sheets, four directional Q sheets, four directional E
sheets, one pose-correction sheet, one slash-effects sheet and one ability-
effects sheet. All are retained unchanged. `source/source_recovery.json`
records their saved identities; `manifest.json` records their SHA-256 hashes.

Attack rows read down, left, right, up; six poses per row. Directional Q/E
sources contain twelve poses, read across two rows of six. The correction
sheet has six poses across two rows of three. Its approved guard poses set
scale for the replacement down-facing E release, two rear rising-cut poses
and one rear E overhead pose. The blade is absent from the throwing hand
on the release pose. Rear actions preserve appropriate torso occlusion.

## Import and alignment

The builder removes the green matte, associates small detached details
with their nearest body, quantizes into the existing body palette and
resamples using nearest-neighbor. Both soles establish horizontal placement;
one raised heel cannot drag the whole frame sideways. Each directional
sequence keeps one scale derived from its starting guard. Actual pale-sole
pixels establish the vertical floor after packing. Approved idle entry and
exit poses are copied exactly for standing attacks and Q/E.

Native cells are 120 by 120, with pivot (60,88). Runtime scales by exactly 2.
Soles are at native Y87 except left at Y86, matching approved idle. Q pose
indices 5 and 6 intentionally rise 10 and 17 native pixels. All other poses
stay on that direction's ground plane. Moving combo variants use complete
stepping poses. The preserved dash-click strip comes from ModelLocked.

New FX use binary alpha and compact red palettes. E fire adds three orange
colors. Slashes use 64px cells at 2x; spin ring and ground FX use 96px cells
at 3x. The thrown dagger uses a 64px cell at 1x, matching the held blade.
The ring is split into rear and front halves. Eruptions and blast retain
upright ground anchors for every facing. Projectile position interpolates
between release and the fixed impact point over 200ms of simulation time.

## Review

Packed contact boards are in `tests/artifacts/jinwoo/video_match_*.png`.
`frame_metrics.json` retains source bounds and scales; `packed_frame_metrics.json`
retains the final frame bounds and hashes. `tests/jinwoo_alignment_qa.json`
measures the exported soles, including the deliberate aerial exceptions.
The full game ZIP includes the animation and real-stage playback checks.
