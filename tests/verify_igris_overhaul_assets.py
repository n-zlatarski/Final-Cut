"""Asset isolation, full blade padding and mechanically preserved base poses."""
from pathlib import Path
import hashlib
import json
from PIL import Image
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BOSS=ROOT/'assets/Blood_Red_Commander'
OLD=BOSS/'GameReadyDetail'
NEW=BOSS/'AttackOverhaul/GameReady'
old=json.loads((OLD/'manifest.json').read_text())
new=json.loads((NEW/'manifest.json').read_text())
report={'checks':[]}
for name in ('Idle','Walk','Run','Dash','Hurt','Death'):
    for key in ('sheet','sheet_no_shadow'):
        a=Image.open(OLD/old['animations'][name][key]).convert('RGBA')
        b=Image.open(NEW/new['animations'][name][key]).convert('RGBA')
        for r in range(4):
            for c in range(8):
                source=a.crop((c*128,r*128,(c+1)*128,(r+1)*128))
                frame=b.crop((c*192+32,r*192+32,c*192+160,r*192+160))
                assert source.tobytes()==frame.tobytes(),(name,r,c,key)
report['checks'].append('All 192 non-attack poses, with and without shadows, are byte-identical after removing transparent padding')
all_attacks=[]
for name in ('Attack1','Attack2','Attack3','Run_Attack','Dash_Attack','Ranged_Attack'):
    spec=new['animations'][name]
    source=NEW/spec['source']
    assert hashlib.sha256(source.read_bytes()).hexdigest()==new['source_sha256'][name]
    sheet=Image.open(NEW/spec['sheet_no_shadow']).convert('RGBA')
    for r in range(4):
        for c in range(8):
            im=sheet.crop((c*192,r*192,(c+1)*192,(r+1)*192))
            box=im.getbbox()
            assert box and min(box[:2])>1 and max(box[2:])<190,(name,r,c,box)
            a=np.array(im)
            visible=a[:,:,3]>0
            rgb=a[:,:,:3].astype(float)
            green=visible & (rgb[:,:,1]>rgb[:,:,0]*1.3) & (rgb[:,:,1]>rgb[:,:,2]*1.3) & (rgb[:,:,1]>70)
            assert not green.any(),(name,r,c,'key residue')
            if 0<c<7:all_attacks.append(hashlib.sha256(im.tobytes()).hexdigest())
assert len(set(all_attacks))==144
report['checks'].append('144 core attack poses are unique across all six moves and four directions; all 192 attack cells have clear margins and no green-key residue')
assert new['animations']['Run']['durations_ms']==[125,115,105,105,125,115,105,105]
assert sum(new['animations']['Walk']['durations_ms'])==1050
assert sum(new['animations']['Run']['durations_ms'])==900
report['checks'].append('900 ms run and 1050 ms walk cycles retain longer planted-foot contacts')
fxroot=BOSS/'AttackOverhaul/VFX'
fx=json.loads((fxroot/'manifest.json').read_text())
atlas=Image.open(fxroot/fx['sheet']).convert('RGBA')
assert atlas.size==(768,1152)
assert len(fx['rows'])==9
for row in range(9):
    for c in range(6):
        im=atlas.crop((c*128,row*128,(c+1)*128,(row+1)*128))
        a=np.array(im)
        assert a[:,:,3].max()>128 and (a[:,:,3]==0).mean()>.35
        assert im.getbbox() is not None
report['checks'].append('54 imported attack/VFX frames have real transparency; both projectile strips contain six frames')
for name in ('blood_wave','ground_wave'):
    assert Image.open(fxroot/(name+'.png')).size==(768,128)
report['status']='passed'
(ROOT/'tests/attack_overhaul_qa.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
