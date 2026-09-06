# Igris attack overhaul — 6 September 2026

Generated character poses and effects use built-in Imagegen with the approved
slender crimson Igris sprite reference. Imagegen supplied the artwork; the
importer only removes the green key, registers frames, maps the character
palette, mirrors the left view, and packs fixed cells. It does not repaint
body parts or synthesize attacks from the previous attacks.

## Retained generation brief

Match the approved Igris model: slim crimson plate armor, dark red cape and
long red helmet plume, dark gold trim, tiny cyan visor, one heavy sword.
Readable moderately detailed pixel art, clean silhouette, no realistic
shading. Keep body proportions, equipment and scale consistent. Each
character sheet has eight chronological poses in three rows: right profile,
down/front, up/back. Plain green background, no labels, grid, baked VFX,
ground shadows or extra weapons. Leave space around the whole sword/cape.

| Source | Motion brief |
| --- | --- |
| Twin_Cut.png | Guard; rear-shoulder chamber; loaded blade; diagonal descending cut; reverse low chamber; rising reverse cut; follow-through; guard |
| Rising_Cleave.png | Guard; low blade; deep crouch; begin rise; full rising strike; high follow-through; retrieve; guard |
| Execution_Plunge.png | Guard; overhead lift; high loaded blade; downward chop; kneeling ground stab; low hold; rise; guard |
| Advancing_Sweep.png | Forward run; purposeful step/chamber; brake wide; load; long horizontal sweep; across-body follow-through; retrieve; guard |
| Dash_Pierce.png | Low aimed blade; coil; launch; stretched lunge; full thrust; brake; rise; guard |
| Blood_Wave.png | Guard; chest lift; high rear chamber; begin chop; forward release; follow-through; retrieve; guard |

The approved guard replaces frame 1 of standing attacks and frame 8 of all
attacks. Frames 2–7 are newly generated attack poses. The right row mirrors
about the exact feet pivot to form the left row. Source boot/stance
landmarks and one scale per direction are retained in the importer and
`alignment.json`. Sword tips below the boots are excluded from registration.
No frame is independently fitted to its bounding box.

Effects use transparent six-column, three-row atlases. Cuts/force rows run
birth, build, peak, breakup, trailing fragments, final embers. The two
traveling waves retain their full shape across a six-frame loop. Dark
burgundy and crimson dominate; thin ivory cores identify the cutting edge.
No character, text, background rectangle or continuous idle aura.

- VFX_Cuts.png: descending forehand, ascending reverse cut, broad horizontal sweep.
- VFX_Force.png: execution blade, low rupture ring/stone chips, narrow rightward pierce.
- VFX_Waves.png: rightward blood blade, low rightward ground wave, contact spark.

The generated source files and approved reference are retained under
`source/`. Character imports use the approved 32-color palette; VFX retain
the generated colors/alpha with faint isolated noise removed. Effect frames
share row scale and origin so growth/decay does not cause size-fitting drift.
Ground effects use a contact origin; projectile strips recenter that origin.

Rebuild with `python tools/build_igris_attack_overhaul.py` from the game folder.
The generated manifests record source hashes, durations, origins and bounds.
