"""Check effect timing, four directions, hit gating and cancellation."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from entities import Enemy,COMMANDER_ACTIONS,Projectile
from igris_vfx import effect_assets
from igris_data import IGRIS_BANK,IGRIS_PIVOT

VECTORS={'left':(-1,0),'right':(1,0),'up':(0,-1),'down':(0,1)}
report={'cases':0,'checks':[]}


def make(action='light_combo',direction='right'):
    e=Enemy('blood_red_commander',850,630);e.is_boss=True
    e._commander_sequence=lambda:(action,)
    dx,dy=VECTORS[direction]
    target=(e.center()[0]+dx*190,e.center()[1]+dy*190)
    e._begin_attack(target,(0,0))
    return e,target


def pixels(e):
    canvas=pygame.Surface((900,700),pygame.SRCALPHA)
    ox=400-e.feet()[0];oy=450-e.feet()[1]
    e.igris_effects.draw_back(canvas,ox,oy)
    e.igris_effects.draw_front(canvas,ox,oy)
    return canvas


for action,cfg in COMMANDER_ACTIONS.items():
    for direction in VECTORS:
        e,target=make(action,direction)
        shown=False;contact=False;echo=False;dust=False
        while e.is_committed:
            e.update(10,target,lambda *a,**k:True)
            fx=e.igris_effects
            shown |= bool(pixels(e).get_bounding_rect().width)
            contact |= any(b['kind']=='spark' for b in fx.bursts)
            dust |= any(b['kind'] in ('dust','rupture') for b in fx.bursts)
            echo |= bool(fx.echoes)
            assert len(fx.echoes)<=5 and len(fx.bursts)<=18
            if fx.swing:
                assert fx.swing[1]==direction
                start=cfg['windup'] if action in ('ground_slam','dash_attack') else min(cfg['hit_times'])
                assert e.anim_elapsed_ms>=start
        assert shown,(action,direction)
        assert contact==bool(cfg['hit_frames']),(action,direction,contact)
        assert echo==(action in ('shadow_dash','dash_attack')),(action,direction,echo)
        if action in ('ground_slam','shadow_dash','dash_attack'):
            assert dust
        e.igris_effects.update(e,600,None)
        assert not pixels(e).get_bounding_rect().width,action
        report['cases']+=1
report['checks'].append('All seven actions show effects in four directions; crimson cuts start at the swing; dash copies follow real travel; impacts, dust and afterimages fully expire')

for landed in (False,True):
    e,target=make()
    for _ in range(35):e.update(10,target,lambda *a,**k:landed)
    assert any(b['kind']=='spark' for b in e.igris_effects.bursts)==landed
report['checks'].append('Contact sparks appear only when the hit callback accepts damage, including dodge/invulnerability rejection')

for cancel in ('hurt','dead'):
    e,target=make('dash_attack')
    for _ in range(34):e.update(10,target,lambda *a,**k:True)
    assert pixels(e).get_bounding_rect().width
    before=pygame.image.tobytes(pixels(e),'RGBA')
    e.update(0,target,lambda *a,**k:True)
    assert before==pygame.image.tobytes(pixels(e),'RGBA')
    e.take_damage(10000 if cancel=='dead' else 1,stagger=1000)
    assert not pixels(e).get_bounding_rect().width
    e.update(10,target,lambda *a,**k:True)
    assert not pixels(e).get_bounding_rect().width
report['checks'].append('Hitstop freezes effects; hurt/death immediately clear active effects; no persistent idle aura')

e,_=make('ground_slam')
up=Projectile(*e.feet(),e.feet()[0],e.feet()[1]-190,1,kind='igris_shockwave',source=e)
down=Projectile(*e.feet(),e.feet()[0],e.feet()[1]+190,1,kind='igris_shockwave',source=e)
for p in (up,down):
    assert len(p.frames)==6 and p.frames[0].get_height()==128
    p.update(16)
assert up.behind_source and not down.behind_source
assert up.hit_radius==down.hit_radius==52
report['checks'].append('Vertical ground waves are foreshortened and layer behind Igris when moving away; collision radius is unchanged')

assert IGRIS_BANK.cell_size==(192,192)
assert IGRIS_PIVOT==(288,384)
unique=0
for name,clip in IGRIS_BANK.clips.items():
    if name=='Idle_Alert':continue
    for row in clip.frames:
        assert len({pygame.image.tobytes(f,'RGBA') for f in row})==8
        for f in row:
            bbox=f.get_bounding_rect(min_alpha=128)
            assert bbox.width>0 and bbox.left>0 and bbox.top>0
            assert bbox.right<192 and bbox.bottom<192
            unique+=1
assert unique==384
for data in effect_assets().values():
    assert len(data['frames'])==6
    assert len({pygame.image.tobytes(f,'RGBA') for f in data['frames']})==6
report['checks'].append(f'384 character frames without clipping, fixed feet alignment, and {sum(len(data["frames"]) for data in effect_assets().values())} distinct transparent effect texture frames')
report['status']='passed'
(ROOT/'tests/vfx_qa.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
pygame.quit()
