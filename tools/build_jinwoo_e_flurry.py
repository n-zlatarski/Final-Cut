"""Assemble a longer E from approved, aligned poses without repainting them."""
from pathlib import Path
import copy
import hashlib
import json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PREVIOUS=ROOT/'assets/Assassin/AbilityPolish'
ART=ROOT/'assets/Assassin/VideoMatch'
OUT=ROOT/'assets/Assassin/EFlurry'
POSES=([('sonic_stream',i) for i in range(7)]+
       [('attack_1',3),('attack_2',3),('attack_3',3),('attack_2',4),('attack_3',4),('sonic_stream',11)])

def build():
    (OUT/'sheets').mkdir(parents=True,exist_ok=True)
    m=copy.deepcopy(json.loads((PREVIOUS/'manifest.json').read_text()))
    for group in ('animations','vfx'):
        for spec in m[group].values():spec['sheet']='../AbilityPolish/'+spec['sheet']
    inputs={n:Image.open(ART/'sheets'/f'{n}.png').convert('RGBA') for n,_ in POSES}
    sheet=Image.new('RGBA',(len(POSES)*120,480));metrics=[]
    for r,d in enumerate(m['direction_rows']):
        hashes=set()
        for c,(name,i) in enumerate(POSES):
            f=inputs[name].crop((i*120,r*120,(i+1)*120,(r+1)*120))
            digest=hashlib.sha256(f.tobytes()).hexdigest()
            assert digest not in hashes,(d,c,'duplicate pose')
            hashes.add(digest);sheet.paste(f,(c*120,r*120))
            metrics.append(dict(direction=d,frame=c,source=f'../VideoMatch/sheets/{name}.png',
                source_column=i,bounds=f.getbbox(),sha256=digest))
    sheet.save(OUT/'sheets/sonic_stream.png')
    m['animations']['sonic_stream'].update(sheet='sheets/sonic_stream.png',frames_per_direction=len(POSES),
        pose_sources=[dict(animation=n,column=i) for n,i in POSES])
    for name in ('source_sheet','source_columns'):m['animations']['sonic_stream'].pop(name,None)
    m.update(version=3,previous_bank='../AbilityPolish',e_motion='short forward entry, ten rapid slashes, larger cross-cut finisher',
        previous_source_manifest='../AbilityPolish/manifest.json',source_sha256={})
    (OUT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    (OUT/'frame_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    print('Packed 52 E frames: guard, entry, ten distinct cuts and recovery per facing')

if __name__=='__main__':build()
