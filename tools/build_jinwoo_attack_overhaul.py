"""Mechanically slice generated art; retain fixed body scale and planted roots.

Optional build dependencies: Pillow, numpy, scipy. No procedural pose drawing.
Approved idle/locomotion assets are inputs only and are never overwritten.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from build_jinwoo_assets import CELL, PIVOT, BODY_HEIGHT, DIRECTIONS, COLORS, PAL

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/Assassin/AttackOverhaul'
SOURCE = OUT / 'source'
OLD = ROOT / 'assets/Assassin/PixelRemake'
SOURCES = {
    'attack_1': ('carving_sweep', 6),
    'attack_2': ('reverse_rake', 6),
    'attack_3': ('fang_plunge', 6),
    'walk_attack_1': ('carving_sweep_moving', 6),
    'walk_attack_2': ('reverse_rake_moving', 6),
    'walk_attack_3': ('fang_plunge_moving', 6),
    'deaths_dance': ('deaths_dance', 12),
    'sonic_stream': ('sonic_stream', 12),
}
FX_NAMES = {
    'blade_fx': ('carving_arc', 'reverse_arc', 'fang_cut'),
    'dance_fx': ('scissor_cut', 'ground_fissure', 'contact'),
    'stream_fx': ('blue_wake', 'barrage_cut', 'twin_wave'),
}
FX_CELL = 96


def cut_bodies(path, count):
    rgb = np.array(Image.open(path).convert('RGB'))
    r, g, b = [rgb[:, :, i].astype(float) for i in range(3)]
    mask = ~((g > 40) & (g > r * 1.3 + 8) & (g > b * 1.3 + 8))
    labels, _ = ndi.label(mask, structure=np.ones((3, 3)))
    areas = np.bincount(labels.ravel())
    boxes = ndi.find_objects(labels)
    objects = []
    for index in np.flatnonzero(areas > 900):
        if index:
            yy, xx = boxes[index - 1]
            objects.append((int(index), (xx.start, yy.start, xx.stop, yy.stop)))
    assert len(objects) == count * 3, (path.name, 'connected bodies', len(objects))
    # Sort by physical row, then X. Overhead daggers may cross the nominal
    # cell boundary, so never crop the character using a rigid source grid.
    objects.sort(key=lambda x: (x[1][1] + x[1][3]) / 2)
    ordered = []
    for start in range(0, len(objects), 6):
        ordered.extend(sorted(objects[start:start + 6], key=lambda x: x[1][0]))
    owner = np.zeros(labels.shape, dtype=np.int16)
    for index, (label, _) in enumerate(ordered):
        owner[labels == label] = index + 1
    orphan = mask & (owner == 0)
    if orphan.any():
        near = ndi.distance_transform_edt(owner == 0, return_distances=False,
                                         return_indices=True)
        owner[orphan] = owner[tuple(near)][orphan]
    items = []
    for index, (_, body_box) in enumerate(ordered):
        owned = owner == index + 1
        yy, xx = np.nonzero(owned)
        x0, y0, x1, y1 = int(xx.min()), int(yy.min()), int(xx.max()+1), int(yy.max()+1)
        # A boot/coat base is dark, unlike the red downward dagger tips.
        dark = owned & (rgb.max(axis=2) < 65)
        floor = int(np.nonzero(dark)[0].max())
        band = dark[max(0, floor - 3):floor + 1]
        sole_x = np.nonzero(band)[1]
        ax = float(sole_x.min() + sole_x.max()) / 2
        cut = rgb[y0:y1, x0:x1].copy()
        cut[:, :, 1] = np.minimum(cut[:, :, 1], np.maximum(cut[:, :, 0], cut[:, :, 2]))
        alpha = owned[y0:y1, x0:x1].astype('uint8') * 255
        items.append(dict(image=Image.fromarray(np.dstack((cut, alpha))),
                          box=[x0, y0, x1, y1], anchor=[ax, floor],
                          source_index=index, body_height=floor-y0+1))
    return items


def quantize(im):
    alpha = im.getchannel('A')
    im = im.convert('RGB').quantize(palette=PAL, dither=Image.Dither.NONE).convert('RGBA')
    im.putalpha(alpha)
    return im


def mirror_at_pivot(im):
    result = Image.new('RGBA', (CELL, CELL))
    result.alpha_composite(im.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (1, 0))
    return result


def build():
    (OUT/'sheets').mkdir(exist_ok=True)
    (OUT/'VFX').mkdir(exist_ok=True)
    idle = Image.open(OLD/'sheets/idle.png').convert('RGBA')
    neutral = [[idle.crop((col*CELL, row*CELL, (col+1)*CELL, (row+1)*CELL))
                for col in (0, 1)] for row in range(4)]
    records, clips, built = [], {}, {}
    for name, (source, count) in SOURCES.items():
        raw = cut_bodies(SOURCE/(source+'.png'), count)
        rows = {}
        scales = {}
        for src_row, facing in enumerate(('right', 'down', 'up')):
            items = raw[src_row*count:(src_row+1)*count]
            # One scale per whole sequence, from its unarmed-height neutral.
            # Overhead blades and crouches do NOT alter body size.
            scale = BODY_HEIGHT / items[0]['body_height']
            scales[facing] = scale
            frames = []
            dst_row = DIRECTIONS.index(facing)
            for col, item in enumerate(items):
                ax, ay = item['anchor']; x0, y0, _, _ = item['box']
                coeff = (1/scale, 0, ax-x0-PIVOT[0]/scale,
                         0, 1/scale, ay-y0-PIVOT[1]/scale)
                frame = quantize(item['image'].transform((CELL, CELL),
                    Image.Transform.AFFINE, coeff, Image.Resampling.NEAREST))
                # Reuse the approved two-pixel ground shadow below the soles.
                ground = Image.new('RGBA', (CELL, CELL))
                ground.alpha_composite(neutral[dst_row][0].crop((0,88,CELL,90)), (0,88))
                ground.alpha_composite(frame)
                frame = ground
                # Exact approved entry/exit silhouette for stationary skills.
                # Pose selection is recorded; no body parts are repainted.
                if not name.startswith('walk_') and col in (0, count-1):
                    frame = neutral[dst_row][int(col != 0)].copy()
                bounds = frame.getbbox()
                assert bounds and min(bounds[:2]) >= 3 and max(bounds[2:]) <= CELL-3, (name, facing, col, bounds)
                frames.append(frame)
                records.append({k: v for k, v in item.items() if k != 'image'} | {
                    'animation': name, 'direction': facing, 'frame': col,
                    'scale': scale, 'pixel_bounds': bounds,
                    'approved_guard': not name.startswith('walk_') and col in (0, count-1),
                    'sha256': hashlib.sha256(frame.tobytes()).hexdigest()})
            rows[facing] = frames
        rows['left'] = [mirror_at_pivot(f) for f in rows['right']]
        if not name.startswith('walk_'):
            rows['left'][0], rows['left'][-1] = [im.copy() for im in neutral[1]]
        built[name] = rows
        clips[name] = {'sheet': f'sheets/{name}.png', 'frames_per_direction': count,
                       'source': source+'.png', 'scale_by_direction': scales}
        print(name, count*4, 'frames', flush=True)
    # Two generated E cells had incorrect choreography after the direction
    # correction: a raised arm during retrieval and a neutral rear finisher.
    # Select complete, correctly posed frames from the new generated bank.
    # No anatomical fragments or procedural body poses are synthesized.
    built['sonic_stream']['down'][10] = built['deaths_dance']['down'][10].copy()
    built['sonic_stream']['up'][7] = built['attack_3']['up'][3].copy()
    clips['sonic_stream']['pose_selections'] = {
        'down:10': 'deaths_dance/down:10', 'up:7': 'attack_3/up:3'}
    # Dash+LMB uses the new E entry and cut with the same 136ms contact beat.
    built['dash_attack'] = {d: [built['sonic_stream'][d][i].copy()
                              for i in (0, 1, 2, 3, 10, 11)] for d in DIRECTIONS}
    clips['dash_attack'] = {'sheet': 'sheets/dash_attack.png', 'frames_per_direction': 6,
                            'derived_from': 'sonic_stream', 'source_indices': [0,1,2,3,10,11]}
    packed_metrics=[]
    for name, rows in built.items():
        count = len(rows['down'])
        sheet = Image.new('RGBA', (CELL*count, CELL*4))
        for r, d in enumerate(DIRECTIONS):
            for c, im in enumerate(rows[d]):
                sheet.alpha_composite(im, (c*CELL, r*CELL))
                packed_metrics.append(dict(animation=name,direction=d,frame=c,
                    pixel_bounds=im.getbbox(),
                    sha256=hashlib.sha256(im.tobytes()).hexdigest()))
        sheet.save(OUT/'sheets'/f'{name}.png')
    vfx = {}
    for source, names in FX_NAMES.items():
        im = Image.open(SOURCE/(source+'.png')).convert('RGBA')
        w, h = im.size
        for row, name in enumerate(names):
            sheet = Image.new('RGBA', (FX_CELL*6, FX_CELL))
            for col in range(6):
                frame = im.crop((round(col*w/6), round(row*h/3),
                                 round((col+1)*w/6), round((row+1)*h/3)))
                a = np.array(frame)
                r,g,b = [a[:,:,i].astype(float) for i in range(3)]
                key = (g>40)&(g>r*1.3+8)&(g>b*1.3+8)
                a[:,:,3] = np.where(key | (a[:,:,3]<100), 0, 255)
                frame = quantize(Image.fromarray(a).resize((FX_CELL,FX_CELL), Image.Resampling.NEAREST))
                assert frame.getbbox(), (name, col, 'empty')
                sheet.alpha_composite(frame, (col*FX_CELL, 0))
            sheet.save(OUT/'VFX'/f'{name}.png')
            vfx[name] = {'sheet': f'VFX/{name}.png', 'frames': 6,
                          'cell_size': [FX_CELL, FX_CELL],
                          'pivot': [48, 66] if name == 'ground_fissure' else [48,48]}
    manifest = {'version': 1, 'character': 'Sung Jinwoo', 'cell_size': [CELL,CELL],
        'pivot': list(PIVOT), 'standing_height_px': BODY_HEIGHT,
        'display_size': [240,240], 'draw_offset': [-10,-12],
        'direction_rows': DIRECTIONS, 'palette': COLORS, 'animations': clips,
        'aliases': {'walk_attack':'walk_attack_1', 'run_attack':'walk_attack_1'},
        'vfx': vfx, 'preserves': 'All PixelRemake locomotion, idle, hurt and death files',
        'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in SOURCE.glob('*.png')}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'frame_metrics.json').write_text(json.dumps(records,indent=2)+'\n')
    (OUT/'packed_frame_metrics.json').write_text(json.dumps(packed_metrics,indent=2)+'\n')
    # Native 2x contact board, with the approved guard alongside every action.
    board = Image.new('RGB', (1200, len(built)*155), '#202536')
    draw = ImageDraw.Draw(board)
    for row,(name,rows) in enumerate(built.items()):
        draw.text((12,row*155+3),name,fill='#e7e5e5')
        indices = list(range(6)) if len(rows['right'])==6 else [0,2,4,6,8,10]
        for col,index in enumerate(indices):
            f=rows['right'][index].crop((22,18,101,95)).resize((158,154),Image.Resampling.NEAREST)
            board.paste(f,(col*195+30,row*155+8),f)
    (ROOT/'tests/artifacts/jinwoo').mkdir(parents=True,exist_ok=True)
    board.save(ROOT/'tests/artifacts/jinwoo/new_attacks_contact.png')
    print('Built', sum(len(v['down'])*4 for v in built.values()), 'body frames and 54 effects')


if __name__ == '__main__':
    build()
