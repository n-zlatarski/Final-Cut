# Ability polish

E uses unchanged approved VideoMatch source poses 0,1,2,3,4,5,6,11 in each
of the four direction rows. The backstep and throwing poses are excluded.
There is no body rescaling, redrawing or change to the original pose pixels.
Q and the dash-attack body sheet are referenced unchanged; only their
runtime timing and effects are adjusted. See README for the exact timings.

The new blue effects were generated with the built-in image-generation tool.
Saved source: Electric-blue dash attack sprite sheet.png, Library identity
libfile_cb469256d6bc8191844181fb9fe47cc5. Its exact bytes are retained here as
source/blue_dash_fx.png, with SHA-256 recorded in manifest.json.

The 1536x1024 source has six columns and four rows: dash ground burst,
rightward slipstream, forward crossing slash and impact sparks. Import
preserves the source alpha, thresholds it at 192 to remove the soft fringe,
then downsamples using nearest-neighbor and seven blue palette colors.
Every output cell is 96x96 with one scale and origin per row. The ground
burst keeps an explicit foot anchor. Runtime uses exact 2x scaling except
small impact sparks at 1x. No blue rectangles or soft matte are retained.

Blue body lighting and narrow edge highlights are temporary runtime layers
on a copy of the actual pose. Afterimages contain previous actual poses at
sampled world positions. Wall dashes emit one takeoff burst but no moving
trail when there is no movement. Takeoff, trail and landing effects expire
within their animation; hurt clears all active skill effects.

The earlier VideoMatch reference choreography and art notes remain as source
history. AbilityPolish is the active runtime bank for this revision.
