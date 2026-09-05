"""Import generated vertical walking poses in the three original Craftpix palettes.

Optional build dependencies: Pillow, numpy, scipy. Runtime needs pygame only.
No poses are painted or interpolated here: source drawings are sliced,
registered, ordered through a full stride, and sampled at the original scale.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
PACK = ASSETS / 'KnightsVerticalRemake'
CELL = 128
PIVOT = (64, 127)
HEIGHT = 64
# The generated sheet is a pose bank. Order by actual leading boot and
# passing pose, rather than treating its presentation order as playback.
ORDERS = {'down': [0, 7, 5, 6, 4, 3, 1, 2],
          'up': [8, 19, 16, 18, 11, 9, 17, 10]}


def original_palettes():
    maps = [{}, {}, {}]
    for filename in ('Idle.png', 'Walk.png'):
        originals = [np.asarray(Image.open(ASSETS / f'Knight_{k}' / filename).convert('RGBA'))
                     for k in (1, 2, 3)]
        solid = originals[0][:, :, 3] > 127
        for k, original in enumerate(originals):
            # Craftpix uses the same character drawings for these three
            # variants. Recover their exact authored color correspondence.
            assert np.array_equal(original[:, :, 3], originals[0][:, :, 3])
            for base, target in zip(originals[0][:, :, :3][solid], original[:, :, :3][solid]):
                key, value = tuple(map(int, base)), tuple(map(int, target))
                assert maps[k].get(key, value) == value
                maps[k][key] = value
    colors = sorted(maps[0])
    palette = Image.new('P', (1, 1))
    palette.putpalette([v for rgb in colors for v in rgb] + [0] * (768 - len(colors) * 3))
    return colors, maps, palette


def slice_source(name, row_count, palette):
    path = PACK / 'source' / f'{name}.png'
    rgb = np.asarray(Image.open(path).convert('RGB'))
    r, g, b = [rgb[:, :, i].astype(float) for i in range(3)]
    green = (g > 80) & (g > r * 1.3 + 15) & (g > b * 1.3 + 15)
    band_rows = np.nonzero(green.sum(axis=1) > rgb.shape[1] / 2)[0]
    top, bottom = int(band_rows.min()), int(band_rows.max() + 1)
    mask = ~green
    # The corrected strip has white outside its green art board.
    mask[:top] = False
    mask[bottom:] = False
    labels, _ = ndi.label(mask, np.ones((3, 3)))
    areas = np.bincount(labels.ravel())
    objects = ndi.find_objects(labels)
    bodies = []
    for label in np.flatnonzero(areas > 2000):
        if not label:
            continue
        yy, xx = objects[label - 1]
        row = min(row_count - 1, int(((yy.start + yy.stop) / 2 - top) / (bottom - top) * row_count))
        bodies.append((row, xx.start, int(label), (xx.start, yy.start, xx.stop, yy.stop)))
    bodies.sort()
    assert len(bodies) == row_count * 4
    scale = HEIGHT / float(np.median([box[3] - box[1] for _, _, _, box in bodies]))
    frames, records = [], []
    for row in range(row_count):
        items = [item for item in bodies if item[0] == row]
        assert len(items) == 4
        ground = float(np.median([box[3] for _, _, _, box in items])) - 1
        for col, (_, _, label, box) in enumerate(items):
            x0, y0, x1, y1 = box
            owned = labels == label
            _, head_x = np.nonzero(owned[y0:y0 + round((y1 - y0) * .16)])
            center_x = (float(head_x.min()) + float(head_x.max())) / 2
            cut = rgb[y0:y1, x0:x1].copy()
            cut[:, :, 1] = np.minimum(cut[:, :, 1], np.maximum(cut[:, :, 0], cut[:, :, 2]))
            image = Image.fromarray(np.dstack((cut, owned[y0:y1, x0:x1].astype(np.uint8) * 255)))
            coeff = (1 / scale, 0, center_x - x0 - PIVOT[0] / scale,
                     0, 1 / scale, ground - y0 - PIVOT[1] / scale)
            frame = image.transform((CELL, CELL), Image.Transform.AFFINE,
                                    coeff, Image.Resampling.NEAREST)
            alpha = frame.getchannel('A')
            frame = frame.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE).convert('RGBA')
            frame.putalpha(alpha)
            box = frame.getbbox()
            assert box and box[0] >= 8 and box[2] <= CELL - 8
            assert 62 <= box[3] - box[1] <= 65, (name, row, col, box)
            frames.append(frame)
            records.append({'source': path.name, 'row': row, 'column': col,
                            'scale': scale, 'source_anchor': [center_x, ground],
                            'pixel_bounds': list(box)})
    return frames, records


def build():
    colors, maps, palette = original_palettes()
    master, records = slice_source('walk_master', 4, palette)
    correction, correction_records = slice_source('up_second_half', 1, palette)
    master += correction
    records += correction_records
    output = {}
    for k in (1, 2, 3):
        for direction, order in ORDERS.items():
            atlas = Image.new('RGBA', (CELL * 8, CELL))
            for col, index in enumerate(order):
                frame = master[index].copy()
                pixels = np.asarray(frame).copy()
                original = pixels[:, :, :3].copy()
                for color in colors:
                    match = np.all(original == color, axis=2)
                    pixels[match, :3] = maps[k - 1][color]
                frame = Image.fromarray(pixels)
                atlas.alpha_composite(frame, (col * CELL, 0))
            path = ASSETS / f'Knight_{k}' / f'Walk_{direction.title()}.png'
            atlas.save(path)
            output[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        'character_types': ['knight1', 'knight2', 'knight3'],
        'cell_size': [CELL, CELL], 'frames_per_direction': 8,
        'directions': ['down', 'up'], 'native_standing_height': HEIGHT,
        'native_ground_pivot': list(PIVOT), 'playback_fps': 8,
        'palette_colors': len(colors),
        'palette_source': 'Exact aligned colors from each original Craftpix Idle.png and Walk.png',
        'source_frame_order': ORDERS, 'source_frames': records,
        'output_sha256': output,
        'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted((PACK / 'source').glob('*.png'))},
    }
    (PACK / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Built six vertical walk strips: 48 frames; original three palettes.')


if __name__ == '__main__':
    build()
