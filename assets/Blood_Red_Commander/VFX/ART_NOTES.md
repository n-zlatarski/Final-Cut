# Igris effect textures

Created with the built-in imagegen tool for this game. The original generated
sheet is `Igris_Effects_Source.png`. The runtime atlas is `Igris_Effects.png`:
six frames across, with spark, dash wake, and dust rows. Equal-cell slicing,
nearest-neighbor reduction to 64px cells, and removal of alpha values below
64 remove faint background speckles while preserving the generated alpha.

Sword ribbons and real-position afterimages are drawn by `igris_vfx.py`.

## Generation prompt

Create a production 2D pixel-art VFX sprite atlas for a crimson armored knight game. Brand-new effect textures only: NO character, NO weapon, NO text, NO labels, NO logos, NO ground scene. Wide canvas 1536 x 768, a strict 6-column x 3-row grid with 18 equally sized 256 x 256 cells. No visible grid. Genuinely transparent background. Each effect remains within its own cell with generous transparent margins, same centered origin and fixed scale throughout each row. Draw crisp fine pixel art with stepped edges as if authored at 64 x 64 pixels per cell then enlarged nearest-neighbor. Limited palette: deep burgundy #510f1b, crimson #d62b2e, warm red #f7593f, occasional pale warm sparks #fff0b0; ground fragments muted reddish brown #653a28. No blue/purple, no smooth vector gradients, no blur. ROW 1: six chronological frames of a small sharp sword-contact spark burst, first tight flash, second four bright thin uneven rays, third rays fragmenting, fourth several falling hot embers, fifth just fading fragments, sixth few dim points. ROW 2: six frames of short crimson dash wake streaks moving toward the RIGHT: thin tapered broken red ribbons trail behind toward the LEFT, a few tiny ember pixels, no full-body aura or giant cloud; grow, peak, break up, fade, retaining a stable origin. ROW 3: six frames of a compact low ground dust kick and angular stone chips: compressed puff, small burst of chips, scattered falling chips, dust dissolving, sparse fragments, almost faded. The VFX should feel elegant, quick and readable around a roughly 200 pixel tall in-game knight, with very little visual clutter. Every row must show real temporal progression; do not repeat frames.
