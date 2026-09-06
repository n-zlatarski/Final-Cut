"""Slice generated run/VFX art onto fixed grids, without repainting poses.

Requires Pillow, numpy and scipy. Run from any working directory.
Character frames use one scale per source, a shared contact plane per row,
and helmet registration; neither a moving boot nor the cape defines a pivot.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
BOSS = ROOT / 'assets/Blood_Red_Commander'
SOURCE = BOSS / 'RunRefinement/source'
BANK = BOSS / 'GameReadyDetail'
PIVOT = (64, 96)
CELL = 128


def keyed(path):
    image = Image.open(path).convert('RGBA')
    a = np.array(image)
    rgb = a[:, :, :3].astype(float)
    green = ((rgb[:, :, 1] > rgb[:, :, 0] * 1.3)
             & (rgb[:, :, 1] > rgb[:, :, 2] * 1.3)
             & (rgb[:, :, 1] > 70))
    a[green, 3] = 0
    # Remove only green key contamination, retaining the cyan visor.
    edge = ndi.binary_dilation(green) & ~green
    a[:, :, 1][edge] = np.minimum(a[:, :, 1][edge],
                                  np.maximum(a[:, :, 0][edge], a[:, :, 2][edge]))
    return Image.fromarray(a)


def run_frames(name, rows, scale, ground, rear=False):
    image = keyed(SOURCE / f'{name}.png')
    array = np.array(image)
    labels, _ = ndi.label(array[:, :, 3] > 0)
    areas = np.bincount(labels.ravel())
    objects = ndi.find_objects(labels)
    bodies = []
    for label in np.flatnonzero(areas > 1000):
        if label:
            yy, xx = objects[label - 1]
            bodies.append((int(label), (xx.start, yy.start, xx.stop, yy.stop)))
    assert len(bodies) == rows * 4, (name, len(bodies))
    bodies.sort(key=lambda item: (round((item[1][1] + item[1][3]) / 2 / (image.height / rows)), item[1][0]))
    # Use each actual horizontal row, rather than assuming the generator's
    # occupied rows have exactly the same spacing as its nominal cells.
    bodies = sorted(bodies, key=lambda item: item[1][1])
    bodies = [item for row in range(rows)
              for item in sorted(bodies[row * 4:(row + 1) * 4], key=lambda item: item[1][0])]
    palette = json.loads((BANK / 'manifest.json').read_text())['palette']
    pal = Image.new('P', (1, 1))
    colors = [tuple(bytes.fromhex(c[1:])) for c in palette]
    pal.putpalette([v for c in colors + [colors[0]] * (256 - len(colors)) for v in c])
    # Existing shadow is already approved and shares the same world pivot.
    shadow = Image.open(SOURCE / 'shadow.png').convert('RGBA')
    frames, metrics = [], []
    for i, (label, box) in enumerate(bodies):
        if name == 'run_vertical' and i >= 8:
            break  # Rear cycle has its own corrected source.
        row = i // 4
        x0, y0, x1, y1 = box
        cut = array[y0:y1, x0:x1].copy()
        cut[:, :, 3] = (labels[y0:y1, x0:x1] == label).astype('uint8') * 255
        if rear:
            # The neck/helmet column below the plume. These source-space
            # landmarks were inspected against the eight generated poses.
            ax = [278, 787, 1298, 1810, 276, 788, 1298, 1808][i]
        else:
            rgb = cut[:, :, :3].astype(int)
            visor = ((rgb[:, :, 2] > rgb[:, :, 0] * 1.22)
                     & (rgb[:, :, 1] > rgb[:, :, 0] * 1.20)
                     & (rgb[:, :, 2] > 90) & (cut[:, :, 3] > 0))
            vy, vx = np.nonzero(visor)
            assert len(vx) >= 4, (name, i, 'missing visor landmark')
            ax = float(np.median(vx)) + x0
            if name == 'run_side':
                ax -= 69  # Preserve the authored forward lean around the hips.
        ay = ground[row]
        coeff = (1 / scale, 0, ax - x0 - PIVOT[0] / scale,
                 0, 1 / scale, ay - y0 - 98 / scale)
        frame = Image.fromarray(cut).transform((CELL, CELL), Image.Transform.AFFINE,
                                             coeff, Image.Resampling.NEAREST)
        alpha = frame.getchannel('A')
        frame = frame.convert('RGB').quantize(palette=pal, dither=Image.Dither.NONE).convert('RGBA')
        frame.putalpha(alpha)
        with_shadow = shadow.copy()
        with_shadow.alpha_composite(frame)
        frames.append((frame, with_shadow))
        metrics.append(dict(source=name, source_frame=i, anchor=[ax, ay], scale=scale,
                            bounds=list(frame.getbbox()), sha256=hashlib.sha256(frame.tobytes()).hexdigest()))
    return frames, metrics


def build_run():
    side, sm = run_frames('run_side', 2, 64 / 313, [406, 802])
    vertical, vm = run_frames('run_vertical', 4, 67 / 239, [264, 533, 798, 1059])
    rear, rm = run_frames('run_rear', 2, 67 / 330, [360, 728], rear=True)
    # Put the rear contact/passing poses in the same two-step phase order.
    rear_order = [3, 2, 5, 1, 4, 7, 6, 0]
    directions = {
        'down': vertical[:8],
        'left': [(f.transpose(Image.Transpose.FLIP_LEFT_RIGHT), s.transpose(Image.Transpose.FLIP_LEFT_RIGHT)) for f, s in side],
        'right': side,
        'up': [rear[i] for i in rear_order],
    }
    # Mirroring a 128px cell has a half-pixel center; shift the mirrored
    # drawing one pixel so both sides retain the exact x=64 pivot.
    fixed_left = []
    for pair in directions['left']:
        result = []
        for image in pair:
            shifted = Image.new('RGBA', (CELL, CELL))
            shifted.alpha_composite(image, (1, 0))
            result.append(shifted)
        fixed_left.append(tuple(result))
    directions['left'] = fixed_left
    for variant, folder, suffix in ((0, 'sheets_no_shadow', ''), (1, 'sheets', '_with_shadow')):
        sheet = Image.new('RGBA', (CELL * 8, CELL * 4))
        for row, direction in enumerate(('down', 'left', 'right', 'up')):
            for col, pair in enumerate(directions[direction]):
                sheet.alpha_composite(pair[variant], (col * CELL, row * CELL))
        sheet.save(BANK / folder / f'Igris_Run{suffix}.png')
    spec = json.loads((BANK / 'manifest.json').read_text())
    spec['animations']['Run']['durations_ms'] = [75, 65, 65, 65, 75, 65, 65, 65]
    spec['animations']['Run']['scales_by_direction'] = dict(down=67 / 239, left=64 / 313, right=64 / 313, up=67 / 330)
    spec['animations']['Run']['source'] = '../RunRefinement/manifest.json'
    # Sharper release and longer anticipation/follow-through, preserving
    # impact times, active-window ends, total action length and game balance.
    spec['animations']['Attack1']['durations_ms'] = [45, 60, 105, 35, 80, 90, 70, 55]
    spec['animations']['Attack2']['durations_ms'] = [45, 65, 130, 45, 80, 100, 75, 75]
    spec['source_sha256']['Run'] = hashlib.sha256(b''.join((SOURCE / name).read_bytes() for name in ('run_side.png', 'run_vertical.png', 'run_rear.png'))).hexdigest()
    spec['art_fixes'] = [f for f in spec.get('art_fixes', []) if f.get('animation') != 'Run']
    spec['art_fixes'].append(dict(animation='Run', change='New alternating contact/passing poses; helmet registration, fixed source scales and shared floor; left mirrors right about feet pivot.'))
    (BANK / 'manifest.json').write_text(json.dumps(spec, indent=2) + '\n')
    report = dict(cell_size=[CELL, CELL], pivot=list(PIVOT), directions=['down', 'left', 'right', 'up'],
                  rear_order=rear_order, metrics=sm + vm[:8] + rm,
                  source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.png')})
    (BOSS / 'RunRefinement/manifest.json').write_text(json.dumps(report, indent=2) + '\n')


def build_effects():
    folder = BOSS / 'VFX'
    source = keyed(folder / 'Crimson_Attacks_Source.png')
    array = np.array(source)
    labels, _ = ndi.label(array[:, :, 3] > 0)
    centers_x = [132, 386, 640, 904, 1160, 1416]
    centers_y = [155, 405, 670, 874]
    owner = np.full(labels.shape, -1, dtype=np.int8)
    for label, slices in enumerate(ndi.find_objects(labels), 1):
        if slices is None:
            continue
        yy, xx = slices
        local = labels[slices] == label
        y, x = np.nonzero(local)
        if len(x) < 3:
            continue
        cx, cy = float(x.mean() + xx.start), float(y.mean() + yy.start)
        col = int(np.argmin(np.abs(np.array(centers_x) - cx)))
        row = int(np.argmin(np.abs(np.array(centers_y) - cy)))
        owner[slices][local] = row * 6 + col
    atlas = Image.new('RGBA', (128 * 6, 128 * 4))
    scale = .34
    for row, cy in enumerate(centers_y):
        for col, cx in enumerate(centers_x):
            tile = array.copy()
            tile[:, :, 3] = (owner == row * 6 + col).astype('uint8') * 255
            frame = Image.fromarray(tile).transform((128, 128), Image.Transform.AFFINE,
                   (1 / scale, 0, cx - 64 / scale, 0, 1 / scale, cy - 64 / scale), Image.Resampling.NEAREST)
            assert frame.getbbox() is not None, (row, col)
            atlas.alpha_composite(frame, (col * 128, row * 128))
    atlas.save(folder / 'Crimson_Attacks.png')
    names = ['sword_cut', 'finisher_cut', 'slam_impact', 'spark']
    spec = dict(sheet='Crimson_Attacks.png', cell_size=[128, 128], grid=[6, 4], rows=names,
                durations_ms=dict(sword_cut=[20, 25, 40, 40, 35, 40],
                                  finisher_cut=[20, 25, 45, 40, 40, 45],
                                  slam_impact=[25, 35, 60, 65, 85, 90],
                                  spark=[15, 25, 30, 40, 45, 60]),
                origins={name: [64, 64] for name in names},
                source_sha256=hashlib.sha256((folder / 'Crimson_Attacks_Source.png').read_bytes()).hexdigest())
    (folder / 'crimson_manifest.json').write_text(json.dumps(spec, indent=2) + '\n')


if __name__ == '__main__':
    build_run()
    build_effects()
    print('Built 32 run frames and 24 attack-effect frames with fixed pivots.')
