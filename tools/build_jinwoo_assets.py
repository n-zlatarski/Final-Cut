"""Slice generated Jinwoo art, align its ground anchors, and pack pixel atlases.

Optional art-build dependency: Pillow, numpy and scipy. Not needed to play.
Source images are preserved verbatim; no animation poses are synthesized.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/Assassin/PixelRemake'
SOURCE = OUT / 'source_atlases'
CELL = 120
PIVOT = (60, 88)
BODY_HEIGHT = 54
DIRECTIONS = ['down', 'left', 'right', 'up']
COUNTS = {
    'idle': 6, 'walk': 6, 'run': 8,
    'attack_1': 6, 'attack_2': 6, 'attack_3': 6,
    'walk_attack_1': 6, 'walk_attack_2': 6, 'walk_attack_3': 6,
    'run_attack': 8, 'dash': 7, 'dash_attack': 6,
    'deaths_dance_spin': 10, 'sonic_stream': 11, 'hurt': 5, 'death': 7,
}
COLORS = [
    '#080b12', '#10121d', '#171b2b', '#22273c', '#30364d', '#444c64',
    '#5c6680', '#79859a', '#929caf', '#b5bac7', '#d6d9df', '#f1efeb',
    '#4a2530', '#703543', '#985347', '#bd7759', '#e4a47b', '#f8c89a',
    '#ffe0b1', '#482126', '#711e2e', '#9d2236', '#cb2b41', '#ee4352',
    '#ff746c', '#715235', '#a37a49', '#d0a26b',
    '#15568d', '#238fc2', '#48cde6', '#bbf4fb',
]
RGB_COLORS = [tuple(bytes.fromhex(c[1:])) for c in COLORS]
PAL = Image.new('P', (1, 1))
PAL.putpalette([v for rgb in RGB_COLORS * 8 for v in rgb])


def extract(path, count, *, fixed_idle_grid=False):
    rgb = np.asarray(Image.open(path).convert('RGB')).copy()
    h, w = rgb.shape[:2]
    r, g, b = [rgb[:, :, i].astype(float) for i in range(3)]
    green = (g > 40) & (g > r * 1.3 + 8) & (g > b * 1.3 + 8)
    mask = ~green
    labels, _ = ndi.label(mask, structure=np.ones((3, 3)))
    areas = np.bincount(labels.ravel())
    objects = ndi.find_objects(labels)
    rows = [[] for _ in DIRECTIONS]
    for label in np.flatnonzero(areas > 1000):
        if label == 0:
            continue
        yy, xx = objects[label - 1]
        row = min(3, max(0, int((yy.start + yy.stop) / 2 / (h / 4))))
        rows[row].append((int(label), (xx.start, yy.start, xx.stop, yy.stop)))
    for row, bodies in enumerate(rows):
        bodies.sort(key=lambda item: item[1][0])
        assert len(bodies) == count, (path.name, row, len(bodies), count)
    idle_ground = []
    if fixed_idle_grid:
        # These idle poses already share a source grid and planted feet.
        # Detect one floor for the WHOLE direction, only within the bottom
        # 5% of the standing figure. A per-frame widest-dark-row search can
        # mistake the back-view boots for the shadow and move the whole body.
        # Shared X/Y anchors also keep nearest-neighbor sampling on one phase.
        dark = rgb.max(axis=2) < 27
        for bodies in rows:
            bottom = int(np.median([box[3] for _, box in bodies]))
            height = bodies[0][1][3] - bodies[0][1][1]
            top = bottom - max(4, round(height * .05))
            widths = dark[top:bottom].sum(axis=1)
            assert widths.max() >= 15 * count, (path.name, 'idle ground')
            idle_ground.append(top + int(widths.argmax()))
    owner = np.zeros(labels.shape, dtype=np.int16)
    flat = []
    for row, bodies in enumerate(rows):
        for col, (label, box) in enumerate(bodies):
            owner[labels == label] = len(flat) + 1
            flat.append(dict(row=row, column=col, body_box=list(box)))
    orphan = mask & (owner == 0)
    if orphan.any():
        nearest = ndi.distance_transform_edt(owner == 0, return_distances=False,
                                            return_indices=True)
        owner[orphan] = owner[tuple(nearest)][orphan]
    raw = []
    for index, item in enumerate(flat):
        owned = owner == index + 1
        yy, xx = np.nonzero(owned)
        box = (int(xx.min()), int(yy.min()), int(xx.max() + 1), int(yy.max() + 1))
        row = item['row']
        first = rows[row][0][1]
        if fixed_idle_grid:
            ax = (item['column'] + .5) * w / count
            ay = idle_ground[row]
            method = 'fixed_idle_grid_and_shared_ground'
        else:
            baseline = first[3] - 4
            ygrid = np.arange(h)[:, None]
            # Generated low lunges can put a planted shadow several source
            # pixels above neutral. Preserve that and genuinely airborne poses.
            band = owned & (ygrid >= baseline - 27) & (ygrid <= baseline + 18)
            dark = band & (rgb[:, :, :3].max(axis=2) < 27)
            widths = dark.sum(axis=1)
            best = int(widths.argmax())
            if widths[best] >= 15:
                xpoints = np.nonzero(dark[best])[0]
                ax = (float(xpoints[0]) + float(xpoints[-1])) / 2
                ay = best
                method = 'ground_shadow'
            else:
                bx0, by0, bx1, by1 = item['body_box']
                ax = (bx0 + bx1) / 2
                ay = baseline
                method = 'row_ground_for_airborne_pose'
        x0, y0, x1, y1 = box
        cut = rgb[y0:y1, x0:x1].copy()
        cut[:, :, 1] = np.minimum(cut[:, :, 1], np.maximum(cut[:, :, 0], cut[:, :, 2]))
        alpha = owned[y0:y1, x0:x1].astype(np.uint8) * 255
        item.update(image=Image.fromarray(np.dstack((cut, alpha))), box=list(box),
                    anchor=[ax, ay], anchor_method=method,
                    reference_height=first[3] - first[1])
        raw.append(item)
    return raw


def build():
    (OUT / 'sheets').mkdir(parents=True, exist_ok=True)
    records = []
    manifests = {}
    for name, count in COUNTS.items():
        path = SOURCE / (name + '.png')
        raw = extract(path, count, fixed_idle_grid=name == 'idle')
        atlas = Image.new('RGBA', (CELL * count, CELL * 4))
        scales = [BODY_HEIGHT / raw[row * count]['reference_height'] for row in range(4)]
        for item in raw:
            row, col = item['row'], item['column']
            scale = scales[row]
            ax, ay = item['anchor']
            x0, y0, x1, y1 = item['box']
            coeff = (1 / scale, 0, ax - x0 - PIVOT[0] / scale,
                     0, 1 / scale, ay - y0 - PIVOT[1] / scale)
            frame = item['image'].transform((CELL, CELL), Image.Transform.AFFINE,
                                            coeff, Image.Resampling.NEAREST)
            alpha = frame.getchannel('A')
            frame = frame.convert('RGB').quantize(palette=PAL, dither=Image.Dither.NONE).convert('RGBA')
            frame.putalpha(alpha)
            bounds = frame.getbbox()
            assert bounds and min(bounds[:2]) >= 2 and max(bounds[2:]) <= CELL - 2, (name, row, col, bounds)
            atlas.alpha_composite(frame, (col * CELL, row * CELL))
            records.append({k: v for k, v in item.items() if k != 'image'} | {
                'animation': name, 'scale': scale, 'pixel_bounds': list(bounds),
                'sha256': hashlib.sha256(frame.tobytes()).hexdigest(),
            })
        atlas.save(OUT / 'sheets' / (name + '.png'))
        manifests[name] = {'sheet': 'sheets/' + name + '.png', 'frames_per_direction': count,
                           'scale_by_direction': dict(zip(DIRECTIONS, scales))}
        if name == 'idle':
            manifests[name]['alignment'] = 'fixed source grid; one ground anchor per direction'
        print(name, len(raw), 'frames', [round(x, 4) for x in scales], flush=True)
    # Legacy preview callers refer to the first moving attack by this alias.
    (OUT / 'sheets/walk_attack.png').write_bytes((OUT / 'sheets/walk_attack_1.png').read_bytes())
    idle = Image.open(OUT / 'sheets/idle.png').convert('RGBA').crop((0, 0, CELL, CELL))
    portrait = Image.new('RGBA', (80, 80), (18, 21, 33, 255))
    portrait.alpha_composite(idle.crop((40, 29, 80, 69)).resize((80, 80), Image.Resampling.NEAREST))
    portrait.convert('RGB').save(OUT / 'sungjinwoo.png')
    manifest = {'format_version': 1, 'character': 'Sung Jinwoo',
                'style_reference': 'Approved Igris GameReadyDetail model',
                'cell_size': [CELL, CELL], 'display_size': [240, 240],
                'draw_offset': [-10, -12], 'world_pivot_from_hero_position': [110, 164],
                'pivot': list(PIVOT), 'standing_height_px': BODY_HEIGHT,
                'direction_rows': DIRECTIONS, 'palette': COLORS, 'animations': manifests,
                'aliases': {'walk_attack': 'walk_attack_1'},
                'source_sha256': {name: hashlib.sha256((SOURCE / (name + '.png')).read_bytes()).hexdigest() for name in COUNTS}}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (OUT / 'frame_metrics.json').write_text(json.dumps(records, indent=2) + '\n')
    print('Complete:', len(records), 'frames')


if __name__ == '__main__':
    build()
