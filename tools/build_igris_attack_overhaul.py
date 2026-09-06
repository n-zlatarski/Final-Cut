"""Import generated attack art; only key, register, palette-map and slice.

Run with Pillow, numpy and scipy installed. The game itself only needs pygame.
Source landmarks are inspected boot/stance centers, never a sword/cape bbox.
One scale per direction preserves crouches, lunges and raised weapon reach.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
BOSS = ROOT / 'assets/Blood_Red_Commander'
OUT = BOSS / 'AttackOverhaul'
SOURCE = OUT / 'source'
OLD = BOSS / 'GameReadyDetail'
BANK = OUT / 'GameReady'
CELL = 192
PIVOT = (96, 128)
DIRECTIONS = ('down', 'left', 'right', 'up')

# Rows in the source artwork are right, down, up. Ground landmarks deliberately
# exclude sword tips below the boots. Moving attacks preserve the authored lean.
ATTACKS = {
    'Attack1': dict(source='Twin_Cut', name='Twin Cut',
        durations=[80, 110, 140, 50, 120, 50, 110, 120],
        height=[184, 195, 193], ground=[[246]*8, [485,484,485,484,484,484,484,485], [722]*8],
        x=[[137,380,646,848,1151,1415,1680,1901],
           [129,395,624,874,1168,1415,1679,1920],
           [133,371,627,901,1175,1412,1662,1891]]),
    'Attack2': dict(source='Rising_Cleave', name='Rising Cleave',
        durations=[80, 100, 170, 60, 60, 90, 110, 110],
        height=[177,182,179], ground=[[260,258,258,258,258,258,258,260], [505]*8, [747]*8],
        x=[[105,360,635,873,1150,1415,1655,1914],
           [110,360,630,884,1150,1411,1650,1910],
           [112,365,615,884,1150,1414,1670,1920]]),
    'Attack3': dict(source='Execution_Plunge', name='Execution Plunge',
        durations=[90, 140, 220, 65, 85, 120, 130, 120],
        height=[203,200,206], ground=[[304]*8, [588,591,591,591,594,597,588,588], [858]*8],
        x=[[114,343,587,775,1020,1230,1440,1671],
           [110,334,557,770,1008,1228,1451,1663],
           [112,340,555,772,1003,1223,1448,1660]]),
    'Run_Attack': dict(source='Advancing_Sweep', name='Advancing Sweep',
        durations=[95, 95, 130, 90, 65, 95, 110, 120],
        height=[176,179,181], ground=[[252]*8, [489]*8, [720]*8],
        x=[[152,392,666,913,1175,1446,1685,1905],
           [164,414,657,914,1163,1422,1687,1910],
           [166,400,655,914,1160,1451,1685,1910]]),
    'Dash_Attack': dict(source='Dash_Pierce', name='Dash Pierce',
        durations=[100, 150, 50, 55, 60, 100, 115, 130],
        height=[188,188,181],
        ground=[[233,233,230,233,233,233,236,236],
                [449,450,451,450,459,461,458,465],
                [716,715,721,721,720,719,715,722]],
        x=[[116,344,574,836,1138,1459,1740,1944],
           [112,334,596,884,1158,1443,1720,1949],
           [125,370,610,883,1150,1408,1722,1940]]),
    'Ranged_Attack': dict(source='Blood_Wave', name='Blood Wave',
        durations=[85, 130, 200, 65, 65, 95, 110, 125],
        height=[187,193,193],
        ground=[[262,259,259,259,259,259,259,262],
                [506,506,500,506,509,509,509,509],
                [742,742,734,734,730,730,737,742]],
        x=[[124,379,619,870,1157,1425,1706,1965],
           [130,375,620,870,1158,1433,1700,1950],
           [120,365,609,850,1161,1440,1695,1940]]),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keyed(path):
    a = np.array(Image.open(path).convert('RGBA'))
    rgb = a[:,:,:3].astype(float)
    green = (rgb[:,:,1] > rgb[:,:,0]*1.3) & (rgb[:,:,1] > rgb[:,:,2]*1.3) & (rgb[:,:,1] > 70)
    a[green,3] = 0
    edge = ndi.binary_dilation(green) & ~green
    a[:,:,1][edge] = np.minimum(a[:,:,1][edge], np.maximum(a[:,:,0][edge],a[:,:,2][edge]))
    a[a[:,:,3] == 0] = 0
    return a


def main_bodies(a):
    labels, _ = ndi.label(a[:,:,3] > 0)
    areas = np.bincount(labels.ravel())
    objects = ndi.find_objects(labels)
    bodies = []
    for label in np.flatnonzero(areas > 1000):
        if label:
            yy,xx = objects[label-1]
            bodies.append((int(label),(xx.start,yy.start,xx.stop,yy.stop)))
    assert len(bodies) == 24, len(bodies)
    bodies.sort(key=lambda b: (b[1][1]+b[1][3])/2)
    ordered = [b for row in range(3) for b in sorted(bodies[row*8:(row+1)*8], key=lambda b:b[1][0])]
    return labels,ordered


def padded(image):
    out = Image.new('RGBA',(CELL,CELL))
    out.alpha_composite(image,(32,32))
    return out


def mirror(image):
    out = Image.new('RGBA',(CELL,CELL))
    out.alpha_composite(image.transpose(Image.Transpose.FLIP_LEFT_RIGHT),(1,0))
    return out


def old_frames(spec, key):
    sheet = Image.open(OLD/spec[key]).convert('RGBA')
    return [[padded(sheet.crop((c*128,r*128,(c+1)*128,(r+1)*128))) for c in range(8)] for r in range(4)]


def save_rows(rows, path):
    sheet = Image.new('RGBA',(CELL*8,CELL*4))
    for r,row in enumerate(rows):
        for c,frame in enumerate(row):
            sheet.alpha_composite(frame,(c*CELL,r*CELL))
    path.parent.mkdir(parents=True,exist_ok=True)
    sheet.save(path)


def build_characters():
    old = json.loads((OLD/'manifest.json').read_text())
    manifest = deepcopy(old)
    manifest.update(cell_size=[CELL,CELL], pivot=list(PIVOT), source_sha256={}, art_fixes=[])
    colors = [tuple(bytes.fromhex(c[1:])) for c in old['palette']]
    pal = Image.new('P',(1,1))
    pal.putpalette([v for c in colors+[colors[0]]*(256-len(colors)) for v in c])
    shadow = padded(Image.open(BOSS/'RunRefinement/source/shadow.png').convert('RGBA'))
    idle = old_frames(old['animations']['Idle'],'sheet_no_shadow')
    metrics = {}
    for name in list(old['animations'])+['Ranged_Attack']:
        if name not in ATTACKS:
            spec = deepcopy(old['animations'][name])
            for key in ('sheet','sheet_no_shadow'):
                save_rows(old_frames(spec,key),BANK/spec[key])
            if name == 'Run':
                spec['durations_ms'] = [125,115,105,105,125,115,105,105]
            elif name == 'Walk':
                spec['durations_ms'] = [140,130,125,130,140,130,125,130]
            spec['source'] = '../../GameReadyDetail/manifest.json'
            manifest['animations'][name] = spec
            continue
        cfg = ATTACKS[name]
        path = SOURCE/(cfg['source']+'.png')
        a = keyed(path)
        labels,bodies = main_bodies(a)
        rows,report = [],[]
        for r in range(3):
            frames = []
            scale = 67/cfg['height'][r]
            for c in range(8):
                label,(x0,y0,x1,y1) = bodies[r*8+c]
                cut = a[y0:y1,x0:x1].copy()
                cut[:,:,3] = (labels[y0:y1,x0:x1] == label).astype('uint8')*255
                ax,ay = cfg['x'][r][c],cfg['ground'][r][c]
                coeff = (1/scale,0,ax-x0-PIVOT[0]/scale,0,1/scale,ay-y0-(PIVOT[1]+2)/scale)
                frame = Image.fromarray(cut).transform((CELL,CELL),Image.Transform.AFFINE,coeff,Image.Resampling.NEAREST)
                alpha = frame.getchannel('A')
                frame = frame.convert('RGB').quantize(palette=pal,dither=Image.Dither.NONE).convert('RGBA')
                frame.putalpha(alpha)
                box = frame.getbbox()
                assert box and min(box[:2])>1 and max(box[2:])<CELL-1,(name,r,c,box)
                frames.append(frame)
                report.append(dict(direction=('right','down','up')[r],frame=c,anchor=[ax,ay],scale=scale,bounds=box))
            rows.append(frames)
        rows = [rows[1],[mirror(f) for f in rows[0]],rows[0],rows[2]]
        for r in range(4):
            # Exact approved guard at entry/exit prevents a model/hand pop.
            if name not in ('Run_Attack','Dash_Attack'):
                rows[r][0] = idle[r][0].copy()
            rows[r][7] = idle[r][1].copy()
        spec = dict(sheet=f'sheets/Igris_{name}_with_shadow.png',
                    sheet_no_shadow=f'sheets_no_shadow/Igris_{name}.png',
                    frames_per_direction=8,durations_ms=cfg['durations'],loop=False,terminal=False,
                    display_name=cfg['name'],source=f'../source/{cfg["source"]}.png',
                    scales_by_direction={d:67/cfg['height'][r] for d,r in (('right',0),('left',0),('down',1),('up',2))})
        save_rows(rows,BANK/spec['sheet_no_shadow'])
        shaded = []
        for row in rows:
            shaded.append([])
            for frame in row:
                tile = shadow.copy()
                tile.alpha_composite(frame)
                shaded[-1].append(tile)
        save_rows(shaded,BANK/spec['sheet'])
        manifest['animations'][name] = spec
        manifest['source_sha256'][name] = digest(path)
        metrics[name] = report
    manifest['art_fixes'] = [dict(change='Six new eight-frame attacks; one source scale per direction; inspected stance landmarks; guard reuse; fixed padding for full weapon reach.')]
    (BANK/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'alignment.json').write_text(json.dumps(dict(cell_size=[CELL,CELL],pivot=PIVOT,metrics=metrics),indent=2)+'\n')


def build_effects():
    groups = [
        ('VFX_Cuts',[('forehand',168),('rising_cut',450),('sweep',728)]),
        ('VFX_Force',[('plunge',180),('rupture',555),('pierce',731)]),
        ('VFX_Waves',[('blood_wave',180),('ground_wave',555),('spark',750)]),
    ]
    fxdir = OUT/'VFX'
    fxdir.mkdir(exist_ok=True)
    atlas = Image.new('RGBA',(128*6,128*9))
    names,origins,scales = [],{},{}
    for group,rows in groups:
        a = keyed(SOURCE/(group+'.png'))
        a[a[:,:,3]<48] = 0
        labels,_ = ndi.label(a[:,:,3]>0)
        owner = np.full(labels.shape,-1,dtype=np.int8)
        centers_x = np.array([150,446,740,1036,1332,1628])
        centers_y = np.array([y for _,y in rows])
        for label,slices in enumerate(ndi.find_objects(labels),1):
            if slices is None:
                continue
            yy,xx = slices
            local = labels[slices] == label
            y,x = np.nonzero(local)
            if len(x)<3:
                continue
            c = int(np.argmin(abs(centers_x-(x.mean()+xx.start))))
            r = int(np.argmin(abs(centers_y-(y.mean()+yy.start))))
            owner[slices][local] = r*6+c
        for r,(name,cy) in enumerate(rows):
            index = len(names)
            names.append(name)
            scale = .30 if name=='plunge' else .32
            origin = (64,96) if name in ('rupture','ground_wave') else (64,64)
            scales[name],origins[name] = scale,origin
            strip = Image.new('RGBA',(128*6,128))
            for c,cx in enumerate(centers_x):
                cut = a.copy()
                cut[:,:,3][owner != r*6+c] = 0
                frame = Image.fromarray(cut).transform((128,128),Image.Transform.AFFINE,
                    (1/scale,0,cx-origin[0]/scale,0,1/scale,cy-origin[1]/scale),Image.Resampling.NEAREST)
                assert frame.getbbox(),(name,c)
                atlas.alpha_composite(frame,(c*128,index*128))
                strip.alpha_composite(frame,(c*128,0))
            if name in ('blood_wave','ground_wave'):
                # Projectile collision point uses the same centered origin.
                if name=='ground_wave':
                    shifted = Image.new('RGBA',strip.size)
                    shifted.alpha_composite(strip,(0,-32))
                    strip = shifted
                strip.save(fxdir/(name+'.png'))
    atlas.save(fxdir/'Igris_Attacks.png')
    durations = {n:([25,35,65,80,100,115] if n=='rupture' else [20,30,45,45,50,60]) for n in names}
    durations['spark'] = [20,25,30,40,45,60]
    spec = dict(sheet='Igris_Attacks.png',cell_size=[128,128],grid=[6,9],rows=names,
                origins=origins,durations_ms=durations,scales=scales,
                source_sha256={n:digest(SOURCE/(n+'.png')) for n,_ in groups})
    (fxdir/'manifest.json').write_text(json.dumps(spec,indent=2)+'\n')


if __name__ == '__main__':
    build_characters()
    build_effects()
    print('Built 384 character frames and 54 effect frames with fixed pivots.')
