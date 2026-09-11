"""Pack slash-only E and blue dash FX; all character poses stay unchanged."""
from pathlib import Path
import copy
import hashlib
import json
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PREVIOUS=ROOT/'assets/Assassin/VideoMatch'
OUT=ROOT/'assets/Assassin/AbilityPolish'
E_POSES=(0,1,2,3,4,5,6,11)
BLUE_COLORS=('071c52','103798','155ee8','188eff','28c9ff','8defff','edffff')

def build():
    (OUT/'sheets').mkdir(parents=True,exist_ok=True)
    (OUT/'VFX').mkdir(exist_ok=True)
    m=copy.deepcopy(json.loads((PREVIOUS/'manifest.json').read_text()))
    for group in ('animations','vfx'):
        for spec in m[group].values():spec['sheet']='../VideoMatch/'+spec['sheet']
    old=Image.open(PREVIOUS/'sheets/sonic_stream.png').convert('RGBA')
    sheet=Image.new('RGBA',(len(E_POSES)*120,480))
    for r in range(4):
        for c,i in enumerate(E_POSES):
            sheet.paste(old.crop((i*120,r*120,(i+1)*120,(r+1)*120)),(c*120,r*120))
    sheet.save(OUT/'sheets/sonic_stream.png')
    m['animations']['sonic_stream'].update(sheet='sheets/sonic_stream.png',
        frames_per_direction=8,source_sheet='../VideoMatch/sheets/sonic_stream.png',source_columns=list(E_POSES))
    m['animations']['sonic_stream'].pop('pose_corrections',None)
    source=OUT/'source/blue_dash_fx.png'
    art=Image.open(source).convert('RGBA');assert art.size==(1536,1024)
    colors=[tuple(bytes.fromhex(c)) for c in BLUE_COLORS]
    pal=Image.new('P',(1,1));pal.putpalette([v for rgb in (colors*37)[:256] for v in rgb])
    records=[]
    specs=(('blue_dash_burst',220,77,False),('blue_dash_stream',164,48,True),
           ('blue_dash_cut',128,48,True),('blue_dash_sparks',122,48,True))
    for r,(name,source_y,target_y,directional) in enumerate(specs):
        size,scale=96,.32;packed=Image.new('RGBA',(6*size,size))
        for c in range(6):
            a=np.array(art.crop((c*256,r*256,(c+1)*256,(r+1)*256)))
            a[:,:,3]=np.where(a[:,:,3]>=192,255,0).astype('uint8')
            tile=Image.fromarray(a)
            coeff=(1/scale,0,128-48/scale,0,1/scale,source_y-target_y/scale)
            f=tile.transform((size,size),Image.Transform.AFFINE,coeff,Image.Resampling.NEAREST)
            alpha=f.getchannel('A')
            f=f.convert('RGB').quantize(palette=pal,dither=Image.Dither.NONE).convert('RGBA');f.putalpha(alpha)
            box=f.getbbox();assert box and min(box[:2])>=2 and max(box[2:])<=size-2,(name,c,box)
            packed.paste(f,(c*size,0))
            records.append(dict(effect=name,frame=c,bounds=list(box),sha256=hashlib.sha256(f.tobytes()).hexdigest()))
        packed.save(OUT/'VFX'/f'{name}.png')
        m['vfx'][name]=dict(sheet=f'VFX/{name}.png',frames=6,cell_size=[size,size],anchor=[48,target_y],
            directional=directional,scale=1 if name=='blue_dash_sparks' else 2,ground=name=='blue_dash_burst')
    for name in ('thrown_dagger','sonic_blast'):m['vfx'].pop(name,None)
    m.update(version=2,previous_bank='../VideoMatch',
        q_motion='advancing spin, aerial turn, one centered eruption 96px ahead of landing',
        e_motion='short forward entry, five rapid slashes, immediate recovery',
        blue_dash_palette=list(BLUE_COLORS),
        source_sha256={'blue_dash_fx.png':hashlib.sha256(source.read_bytes()).hexdigest()},
        previous_source_manifest='../VideoMatch/manifest.json')
    (OUT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    (OUT/'frame_metrics.json').write_text(json.dumps(records,indent=2)+'\n')
    print('Packed 32 E poses and 24 blue FX frames')

if __name__=='__main__':build()
