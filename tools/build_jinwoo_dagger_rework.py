"""Slice generated dagger art, retain shared scale and pack aligned RGBA sheets.
No procedural body drawing. Source images and exact prompts are retained.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from build_jinwoo_assets import CELL, PIVOT, BODY_HEIGHT, DIRECTIONS, COLORS, PAL

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/Assassin/DaggerRework'
SOURCE = OUT / 'source'
OLD = ROOT / 'assets/Assassin/PixelRemake'
SOURCES = {
    'attack_1': 'quick_cut', 'attack_2': 'cross_cut', 'attack_3': 'lunge_finish',
    'walk_attack_1': 'quick_cut_moving', 'walk_attack_2': 'cross_cut_moving',
    'walk_attack_3': 'lunge_finish_moving', 'dash_attack': 'dash_strike',
}
FX_NAMES = {
    'blade_fx': ('quick_arc', 'cross_slash', 'lunge_streak'),
    'dance_fx': ('dance_cut', 'echo_cut', 'contact'),
    'stream_fx': ('blue_wake', 'stabbing_trail', 'piercing_wave'),
}
FX_CELL = 64
BODY_PAL = Image.new('P', (1, 1))
body_colors = [tuple(bytes.fromhex(c[1:])) for c in COLORS[:28]]
BODY_PAL.putpalette([v for rgb in (body_colors*10)[:256] for v in rgb])

def cut_bodies(path, count, columns):
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
    assert len(objects) == count, (path.name, 'connected bodies', len(objects))
    # Sort by physical row, then X. Overhead daggers may cross the nominal
    # cell boundary, so never crop the character using a rigid source grid.
    objects.sort(key=lambda x: (x[1][1] + x[1][3]) / 2)
    ordered = []
    for start in range(0, len(objects), columns):
        ordered.extend(sorted(objects[start:start + columns], key=lambda x: x[1][0]))
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
        band = dark[max(0, floor - max(4, round((floor-y0+1)*.10))):floor + 1]
        sole_x = np.nonzero(band)[1]
        ax = float(sole_x.min() + sole_x.max()) / 2
        cut = rgb[y0:y1, x0:x1].copy()
        cut[:, :, 1] = np.minimum(cut[:, :, 1], np.maximum(cut[:, :, 0], cut[:, :, 2]))
        alpha = owned[y0:y1, x0:x1].astype('uint8') * 255
        items.append(dict(image=Image.fromarray(np.dstack((cut, alpha))),
                          box=[x0, y0, x1, y1], anchor=[ax, floor],
                          source_index=index, body_height=floor-y0+1))
    return items


def quantize(im, palette=PAL):
    alpha = im.getchannel('A')
    im = im.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE).convert('RGBA')
    im.putalpha(alpha)
    return im


def build():
    (OUT/'sheets').mkdir(exist_ok=True)
    (OUT/'VFX').mkdir(exist_ok=True)
    idle = Image.open(OLD/'sheets/idle.png').convert('RGBA')
    neutral = {d: [idle.crop((c*CELL,r*CELL,(c+1)*CELL,(r+1)*CELL))
                   for c in (0,1)] for r,d in enumerate(DIRECTIONS)}
    records, clips, built = [], {}, {}

    def align(item, scale, facing):
        ax,ay = item['anchor']; x0,y0,_,_ = item['box']
        coeff = (1/scale,0,ax-x0-PIVOT[0]/scale,
                 0,1/scale,ay-y0-PIVOT[1]/scale)
        body = quantize(item['image'].transform((CELL,CELL),
            Image.Transform.AFFINE,coeff,Image.Resampling.NEAREST), BODY_PAL)
        frame = Image.new('RGBA',(CELL,CELL))
        frame.alpha_composite(neutral[facing][0].crop((0,88,CELL,90)),(0,88))
        frame.alpha_composite(body)
        return frame

    def make_row(name, facing, items, source):
        # One scale for a whole directional sequence. Crouching and raised
        # weapons never cause per-pose rescaling. Dash starts in a crouch.
        ref = items[-1] if name == 'dash_attack' else items[0]
        scale = BODY_HEIGHT/ref['body_height']
        frames=[]
        for col,item in enumerate(items):
            frame=align(item,scale,facing)
            guard=(not name.startswith('walk_') and col==len(items)-1) or (
                name not in ('dash_attack',) and not name.startswith('walk_') and col==0)
            if guard:
                frame=neutral[facing][int(col!=0)].copy()
            frames.append(frame)
            records.append({k:v for k,v in item.items() if k!='image'} | {
                'animation':name,'direction':facing,'frame':col,'scale':scale,
                'source':source,'approved_guard':guard})
        return frames, scale

    for name,source in SOURCES.items():
        raw=cut_bodies(SOURCE/(source+'.png'),32,8)
        built[name]={}; scales={}
        for row,facing in enumerate(DIRECTIONS):
            built[name][facing],scales[facing]=make_row(
                name,facing,raw[row*8:(row+1)*8],source+'.png')
        clips[name]={'sheet':f'sheets/{name}.png','frames_per_direction':8,
                     'source':source+'.png','scale_by_direction':scales}
        print(name,32,'frames',flush=True)

    for name in ('deaths_dance','sonic_stream'):
        built[name]={}; scales={}
        for facing in DIRECTIONS:
            source=f'{name}_{facing}.png'
            raw=cut_bodies(SOURCE/source,12,6)
            built[name][facing],scales[facing]=make_row(name,facing,raw,source)
        clips[name]={'sheet':f'sheets/{name}.png','frames_per_direction':12,
            'sources':{d:f'{name}_{d}.png' for d in DIRECTIONS},
            'scale_by_direction':scales}
        print(name,48,'frames',flush=True)

    # Two independently generated corrections fix rear-view occlusion.
    # Select entire authored poses; no body-part compositing or painting.
    corrections=cut_bodies(SOURCE/'rear_corrections.png',3,3)
    scale=BODY_HEIGHT/corrections[0]['body_height']
    for name,index,source_index in [('walk_attack_2',4,1),('deaths_dance',7,2)]:
        built[name]['up'][index]=align(corrections[source_index],scale,'up')
        clips[name]['pose_selections']={f'up:{index}':f'rear_corrections.png:{source_index}'}

    metrics=[]
    for name,rows in built.items():
        count=len(rows['down'])
        sheet=Image.new('RGBA',(CELL*count,CELL*4))
        for r,d in enumerate(DIRECTIONS):
            for c,frame in enumerate(rows[d]):
                box=frame.getbbox()
                assert box and min(box[:2])>=3 and max(box[2:])<=CELL-3,(name,d,c,box)
                sheet.alpha_composite(frame,(c*CELL,r*CELL))
                metrics.append(dict(animation=name,direction=d,frame=c,
                    pixel_bounds=box,sha256=hashlib.sha256(frame.tobytes()).hexdigest()))
        sheet.save(OUT/'sheets'/f'{name}.png')

    vfx={}
    for source,names in FX_NAMES.items():
        im=Image.open(SOURCE/(source+'.png')).convert('RGBA'); w,h=im.size
        for row,name in enumerate(names):
            sheet=Image.new('RGBA',(FX_CELL*6,FX_CELL))
            for col in range(6):
                frame=im.crop((round(col*w/6),round(row*h/3),
                    round((col+1)*w/6),round((row+1)*h/3)))
                a=np.array(frame)
                r,g,b=[a[:,:,i].astype(float) for i in range(3)]
                key=(g>40)&(g>r*1.3+8)&(g>b*1.3+8)
                a[:,:,3]=np.where(key|(a[:,:,3]<100),0,255)
                # Uniform inset preserves growth/fade and leaves the actor
                # readable. Never normalize each effect's occupied bounds.
                small=quantize(Image.fromarray(a).resize((48,48),Image.Resampling.NEAREST))
                assert small.getbbox(),(name,col,'empty')
                sheet.alpha_composite(small,(col*FX_CELL+8,8))
            sheet.save(OUT/'VFX'/f'{name}.png')
            vfx[name]={'sheet':f'VFX/{name}.png','frames':6,
                       'cell_size':[FX_CELL,FX_CELL],'pivot':[32,32]}
    manifest={'version':1,'character':'Sung Jinwoo','cell_size':[CELL,CELL],
        'pivot':list(PIVOT),'standing_height_px':BODY_HEIGHT,
        'display_size':[240,240],'draw_offset':[-10,-12],
        'direction_rows':DIRECTIONS,'palette':COLORS,'animations':clips,
        'aliases':{'walk_attack':'walk_attack_1','run_attack':'walk_attack_1'},
        'vfx':vfx,'preserves':'All PixelRemake idle, locomotion, hurt, death and portrait files',
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.png')}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'frame_metrics.json').write_text(json.dumps(records,indent=2)+'\n')
    (OUT/'packed_frame_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    qa=ROOT/'tests/artifacts/jinwoo';qa.mkdir(parents=True,exist_ok=True)
    for d in DIRECTIONS:
        board=Image.new('RGB',(1920,len(built)*180),'#202536')
        draw=ImageDraw.Draw(board)
        for row,(name,rows) in enumerate(built.items()):
            draw.text((5,row*180+2),name,fill='#e7e5e5')
            for col,frame in enumerate(rows[d]):
                pic=frame.crop((20,15,100,95)).resize((160,160),Image.Resampling.NEAREST)
                board.paste(pic,(col*160,row*180+20),pic)
        board.save(qa/f'dagger_{d}.png')
    print('Built',len(metrics),'body frames and 54 effects',flush=True)


if __name__=='__main__':
    build()

