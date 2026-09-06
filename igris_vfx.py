"""Generated crimson attack effects, synchronized to authored impact frames.

No idle aura. World-space contact bursts require accepted damage; dash ghosts
sample actual travel. All clocks pause with the game and clear on hurt/death.
"""
from bisect import bisect_right
from collections import deque
from functools import lru_cache
from itertools import accumulate
import json
import math
from pathlib import Path

import pygame
from igris_data import IGRIS_PIVOT

DIRECTIONS = {'right':(1,0), 'left':(-1,0), 'down':(0,1), 'up':(0,-1)}
STROKES = {
    'light_combo': ('forehand','rising_cut'),
    'overhead_slash': ('rising_cut',),
    'ground_slam': ('plunge',),
    'run_attack': ('sweep',),
    'dash_attack': ('pierce',),
    'ranged_thrust': ('forehand',),
}


@lru_cache(maxsize=1)
def effect_assets():
    root = Path(__file__).resolve().parent/'assets/Blood_Red_Commander'
    assets = {}
    # Small contact dust remains useful for takeoff/landing; every attack
    # texture, ground impact and projectile belongs to the new generated set.
    for folder, selected in ((root/'VFX', {'dust'}),
                             (root/'AttackOverhaul/VFX', None)):
        spec = json.loads((folder/'manifest.json').read_text())
        atlas = pygame.image.load(str(folder/spec.get('sheet','Igris_Effects.png'))).convert_alpha()
        cw,ch = spec['cell_size']
        cols,rows = spec['grid']
        assert atlas.get_size() == (cw*cols,ch*rows)
        for row,name in enumerate(spec['rows']):
            if selected is not None and name not in selected:
                continue
            assets[name] = dict(frames=tuple(atlas.subsurface((i*cw,row*ch,cw,ch)).copy() for i in range(cols)),
                ends=tuple(accumulate(spec['durations_ms'][name])), origin=tuple(spec['origins'][name]))
    return assets


@lru_cache(maxsize=256)
def texture_frame(kind,index,angle=0):
    data = effect_assets()[kind]
    source = data['frames'][index]
    size = max(source.get_size())*2
    tile = pygame.Surface((size,size),pygame.SRCALPHA)
    tile.blit(source,(size//2-data['origin'][0],size//2-data['origin'][1]))
    if angle:
        tile = pygame.transform.rotate(tile,angle)
    scale = 3 if kind in ('rupture','sweep') else 2
    return pygame.transform.scale(tile,(tile.get_width()*scale,tile.get_height()*scale))


@lru_cache(maxsize=256)
def sword_texture(kind,index,direction):
    tile = texture_frame(kind,index)
    if direction == 'left' or (direction == 'up' and kind == 'forehand'):
        tile = pygame.transform.flip(tile,True,False)
    if kind == 'pierce' and direction in ('up','down'):
        tile = pygame.transform.rotate(tile,90 if direction=='up' else -90)
        tile = pygame.transform.scale(tile,(tile.get_width(),round(tile.get_height()*.65)))
    return tile


class IgrisEffects:
    def __init__(self):
        effect_assets()
        self.echoes = deque(maxlen=4)
        self.bursts = []
        self.previous_feet = None
        self.dash_accumulator = 0.
        self.action_id = None
        self.emitted = set()
        self.swing = None
        self.swing_kind = 'forehand'
        self.wake = None

    def clear(self):
        self.echoes.clear()
        self.bursts.clear()
        self.swing = self.wake = None
        self.previous_feet = None
        self.dash_accumulator = 0.
        self.action_id = None
        self.emitted.clear()

    def _burst(self,kind,position,*,angle=0,opacity=230):
        self.bursts.append(dict(kind=kind,position=tuple(position),age=0.,angle=angle,opacity=opacity))
        self.bursts = self.bursts[-18:]

    def contact(self,enemy,*,position=None,hit=False,ground=False):
        if enemy.dead or enemy.combat_state=='hurt':
            return
        if hit and position is not None:
            self._burst('spark',position,opacity=250)
        if ground:
            dx,dy = DIRECTIONS[enemy.attack_direction]
            fx,fy = enemy.feet()
            self._burst('rupture',(fx+dx*65,fy+(10 if dy>0 else -24 if dy<0 else 0)),opacity=255)

    def update(self,enemy,dt,cfg):
        if enemy.dead or enemy.combat_state=='hurt':
            self.clear()
            return
        for echo in self.echoes:
            echo['age'] += dt
        while self.echoes and self.echoes[0]['age']>=190:
            self.echoes.popleft()
        for burst in self.bursts:
            burst['age'] += dt
        self.bursts[:] = [b for b in self.bursts if b['age']<effect_assets()[b['kind']]['ends'][-1]]
        self.swing = self.wake = None
        feet = tuple(enemy.feet())
        if not enemy.is_committed or cfg is None:
            self.previous_feet = feet
            self.dash_accumulator = 0.
            return
        if enemy.attack_count != self.action_id:
            self.action_id = enemy.attack_count
            self.emitted.clear()
            self.dash_accumulator = 0.
            self.previous_feet = feet
        action,time,direction = enemy.boss_action,enemy.anim_elapsed_ms,enemy.attack_direction
        # Each cut gets its own birth/peak/decay window. Twin Cut reverses the
        # second trail and never treats the two physical strikes as one sweep.
        for i,hit_time in enumerate(cfg['hit_times']):
            start = cfg['windup'] if action in ('ground_slam','dash_attack') else hit_time
            duration = 205 if action=='ground_slam' else 185 if action=='dash_attack' else 160
            if start <= time < start+duration:
                self.swing = (action,direction,(time-start)/duration,feet)
                self.swing_kind = STROKES[action][i]
        moving_dash = action in ('shadow_dash','dash_attack')
        start,end = cfg['move_window']
        if moving_dash and start <= time < end:
            dx,dy = enemy.attack_direction_vec
            angle = round(-math.degrees(math.atan2(dy,dx))/15)*15
            self.wake = (feet,angle,min(175.,(time-start)*1.2))
            if 'takeoff' not in self.emitted:
                self._burst('dust',feet,opacity=135)
                self.emitted.add('takeoff')
            previous = self.previous_feet or feet
            distance = math.dist(previous,feet)
            self.dash_accumulator += dt
            if dt>0 and distance>.5:
                frame = enemy._frames()[int(enemy.frame_idx)].copy()
                frame.fill((255,70,85,255),special_flags=pygame.BLEND_RGBA_MULT)
                while self.dash_accumulator>=40:
                    self.dash_accumulator-=40
                    mix=max(0.,min(1.,1-self.dash_accumulator/max(1.,dt)))
                    pos=tuple(previous[i]+(feet[i]-previous[i])*mix for i in (0,1))
                    self.echoes.append(dict(frame=frame,feet=pos,age=self.dash_accumulator))
            else:
                self.dash_accumulator=0.
        elif moving_dash and time>=end and 'takeoff' in self.emitted and 'landing' not in self.emitted:
            self._burst('dust',feet,opacity=105)
            self.emitted.add('landing')
        self.previous_feet=feet

    def _texture(self,surface,kind,age,position,ox,oy,*,angle=0,opacity=230):
        data=effect_assets()[kind]
        index=min(bisect_right(data['ends'],age),len(data['frames'])-1)
        tile=texture_frame(kind,index,angle)
        if opacity!=255:
            tile=tile.copy()
            tile.set_alpha(opacity)
        surface.blit(tile,tile.get_rect(center=(round(position[0]+ox),round(position[1]+oy))))

    def _draw_swing(self,surface,ox,oy):
        if not self.swing:
            return
        action,direction,t,feet=self.swing
        kind=self.swing_kind
        data=effect_assets()[kind]
        index=min(bisect_right(data['ends'],t*data['ends'][-1]),len(data['frames'])-1)
        tile=sword_texture(kind,index,direction)
        if action=='overhead_slash' and direction=='up':
            tile=pygame.transform.flip(tile,True,False)
        dx,dy=DIRECTIONS[direction]
        if kind=='sweep':
            x,y=dx*35,-82+dy*12
        elif kind=='plunge':
            x,y=dx*65,-95+dy*12
        elif kind=='pierce':
            x,y=dx*140,-90+dy*70
        elif kind=='rising_cut':
            x,y=(dx*68 if dx else 18),-138+(16 if dy>0 else -8 if dy<0 else 0)
            if action=='overhead_slash' and direction=='up':
                x=-18
        else:
            x,y=(dx*76 if dx else 26*dy),-96+(18 if dy>0 else -12 if dy<0 else 0)
        surface.blit(tile,tile.get_rect(center=(round(feet[0]+x+ox),round(feet[1]+y+oy))))

    def draw_back(self,surface,ox,oy):
        for echo in self.echoes:
            fade=max(0.,1-echo['age']/190)
            frame=echo['frame'].copy()
            frame.set_alpha(round(72*fade**1.4))
            fx,fy=echo['feet']
            surface.blit(frame,(round(fx+ox)-IGRIS_PIVOT[0],round(fy+oy)-IGRIS_PIVOT[1]))
        if self.wake:
            feet,angle,age=self.wake
            dx,dy=math.cos(math.radians(-angle)),math.sin(math.radians(-angle))
            self._texture(surface,'pierce',age,(feet[0]-dx*58,feet[1]-76-dy*28),ox,oy,angle=angle,opacity=150)
        for b in self.bursts:
            if b['kind'] in ('dust','rupture'):
                self._texture(surface,b['kind'],b['age'],b['position'],ox,oy,angle=b['angle'],opacity=b['opacity'])
        if self.swing and self.swing[1]=='up':
            self._draw_swing(surface,ox,oy)

    def draw_front(self,surface,ox,oy):
        if self.swing and self.swing[1]!='up':
            self._draw_swing(surface,ox,oy)
        for b in self.bursts:
            if b['kind'] not in ('dust','rupture'):
                self._texture(surface,b['kind'],b['age'],b['position'],ox,oy,angle=b['angle'],opacity=b['opacity'])
