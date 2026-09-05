"""Short pixel sword trails, contact sparks and motion-based dash effects.

Effects use the boss's animation clock and world-space feet. This module never
changes movement, damage or hitboxes. Texture frames are generated artwork;
sword ribbons follow each authored swing in a small pixel canvas.
"""
from bisect import bisect_right
from collections import deque
from functools import lru_cache
from itertools import accumulate
import json
import math
from pathlib import Path

import pygame


DIRECTIONS = {'right': (1, 0), 'left': (-1, 0), 'down': (0, 1), 'up': (0, -1)}
FX_PIXEL = 2
LAYER_SIZE = 256
ORIGIN = (128, 176)


@lru_cache(maxsize=1)
def effect_assets():
    root = Path(__file__).resolve().parent / 'assets/Blood_Red_Commander/VFX'
    spec = json.loads((root/'manifest.json').read_text())
    atlas = pygame.image.load(str(root/'Igris_Effects.png')).convert_alpha()
    cw, ch = spec['cell_size']
    cols, rows = spec['grid']
    if atlas.get_size() != (cw*cols, ch*rows):
        raise ValueError('Igris VFX atlas dimensions do not match its manifest')
    return {
        name: {
            'frames': tuple(atlas.subsurface((i*cw, row*ch, cw, ch)).copy()
                            for i in range(cols)),
            'ends': tuple(accumulate(spec['durations_ms'][name])),
            'origin': tuple(spec['origins'][name]),
        }
        for row, name in enumerate(spec['rows'])
    }


@lru_cache(maxsize=128)
def texture_frame(kind, index, angle=0):
    data = effect_assets()[kind]
    # Center a texture's authored pivot before rotation, so its apparent
    # origin stays fixed when used for left/up/down movement.
    source = data['frames'][index]
    tile = pygame.Surface((96, 96), pygame.SRCALPHA)
    tile.blit(source, (48-data['origin'][0], 48-data['origin'][1]))
    if angle:
        tile = pygame.transform.rotate(tile, angle)
    return pygame.transform.scale(tile, (tile.get_width()*2, tile.get_height()*2))


def pixel_point(x, y):
    return (round(ORIGIN[0]+x/FX_PIXEL), round(ORIGIN[1]+y/FX_PIXEL))


def ribbon(surface, points, width, alpha):
    """Tapered burgundy/red/cream ribbon on a 2px grid; no smooth glow."""
    if len(points) < 2 or alpha <= 0:
        return
    for i in range(1, len(points)):
        t = i / (len(points)-1)
        taper = max(.2, math.sin(t*math.pi*.92))
        w = max(1, round(width*taper/FX_PIXEL))
        a = round(alpha*(.28+.72*t))
        start, end = points[i-1], points[i]
        pygame.draw.line(surface, (75, 7, 27, a), start, end, w+3)
        pygame.draw.line(surface, (214, 24, 49, a), start, end, w+1)
        pygame.draw.line(surface, (255, 97, 74, min(255, a+20)), start, end, max(1, w-1))
        if t > .48:
            pygame.draw.line(surface, (255, 229, 188, a), start, end, 1)


class IgrisEffects:
    def __init__(self):
        effect_assets()
        self.echoes = deque(maxlen=5)
        self.bursts = []
        self.previous_feet = None
        self.dash_accumulator = 0.0
        self.action_id = None
        self.emitted = set()
        self.swing = None
        self.wake = None
        self._layer = pygame.Surface((LAYER_SIZE, LAYER_SIZE), pygame.SRCALPHA)

    def clear(self):
        self.echoes.clear()
        self.bursts.clear()
        self.swing = None
        self.wake = None
        self.previous_feet = None
        self.dash_accumulator = 0
        self.action_id = None
        self.emitted.clear()

    def _burst(self, kind, position, *, angle=0, opacity=210):
        self.bursts.append({'kind': kind, 'position': tuple(position),
                            'age': 0., 'angle': angle, 'opacity': opacity})
        self.bursts = self.bursts[-18:]

    def contact(self, enemy, *, position=None, hit=False, ground=False):
        """Called at the actual strike event; contact sparks require a hit."""
        if enemy.dead or enemy.combat_state == 'hurt':
            return
        if hit and position is not None:
            self._burst('spark', position, opacity=240)
        if ground:
            dx, dy = DIRECTIONS[enemy.attack_direction]
            fx, fy = enemy.feet()
            self._burst('dust', (fx+dx*82, fy+dy*46), opacity=220)

    def update(self, enemy, dt, cfg):
        if enemy.dead or enemy.combat_state == 'hurt':
            self.clear()
            return
        for echo in self.echoes:
            echo['age'] += dt
        while self.echoes and self.echoes[0]['age'] >= 190:
            self.echoes.popleft()
        for burst in self.bursts:
            burst['age'] += dt
        self.bursts[:] = [b for b in self.bursts
                         if b['age'] < effect_assets()[b['kind']]['ends'][-1]]
        self.swing = None
        self.wake = None
        feet = tuple(enemy.feet())
        if not enemy.is_committed or cfg is None:
            self.previous_feet = feet
            self.dash_accumulator = 0
            return
        token = enemy.attack_count
        if token != self.action_id:
            self.action_id = token
            self.emitted.clear()
            self.dash_accumulator = 0
            self.previous_feet = feet
        action = enemy.boss_action
        time = enemy.anim_elapsed_ms
        direction = enemy.attack_direction
        if cfg['hit_times']:
            start = cfg['windup']
            duration = 190 if action == 'ground_slam' else 160
            age = time-start
            if 0 <= age < duration:
                self.swing = (action, direction, age/duration, feet)
        moving_dash = action in ('shadow_dash', 'dash_attack')
        start, end = cfg['move_window']
        if moving_dash and start <= time < end:
            dx, dy = enemy.attack_direction_vec
            angle = round(-math.degrees(math.atan2(dy, dx))/15)*15
            self.wake = (feet, angle, min(239., (time-start)*1.10))
            if 'takeoff' not in self.emitted:
                self._burst('dust', feet, opacity=145)
                self.emitted.add('takeoff')
            previous = self.previous_feet or feet
            distance = math.dist(previous, feet)
            self.dash_accumulator += dt
            if dt > 0 and distance > .5:
                frame = enemy._frames()[int(enemy.frame_idx)].copy()
                frame.fill((255, 80, 100, 255), special_flags=pygame.BLEND_RGBA_MULT)
                # Store real sampled positions; a direction change never flips
                # an old afterimage or drags it along with the current sprite.
                while self.dash_accumulator >= 32:
                    self.dash_accumulator -= 32
                    mix = max(0., min(1., 1-self.dash_accumulator/max(1., dt)))
                    pos = (previous[0]+(feet[0]-previous[0])*mix,
                           previous[1]+(feet[1]-previous[1])*mix)
                    self.echoes.append({'frame': frame, 'feet': pos, 'age': self.dash_accumulator})
            else:
                self.dash_accumulator = 0
        elif moving_dash and time >= end and 'takeoff' in self.emitted and 'landing' not in self.emitted:
            self._burst('dust', feet, opacity=105)
            self.emitted.add('landing')
        self.previous_feet = feet

    def _texture(self, surface, kind, age, position, ox, oy, *, angle=0, opacity=210):
        data = effect_assets()[kind]
        index = min(bisect_right(data['ends'], age), len(data['frames'])-1)
        tile = texture_frame(kind, index, angle).copy()
        tile.set_alpha(opacity)
        rect = tile.get_rect(center=(round(position[0]+ox), round(position[1]+oy)))
        surface.blit(tile, rect)

    def _draw_swing(self, surface, ox, oy):
        if not self.swing:
            return
        action, direction, t, feet = self.swing
        dx, dy = DIRECTIONS[direction]
        sx, sy = -dy, dx
        layer = self._layer
        layer.fill((0, 0, 0, 0))
        alpha = round(238 * min(1., (1-t)*1.65))
        # Fore/aft reach is compressed for top-down views, just as in the
        # directional character drawings; the trail stays at sword height.
        def project(forward, side=0, height=96):
            return pixel_point(dx*forward+sx*side,
                               (dy*forward+sy*side)*.48-height)
        if action in ('light_combo', 'ranged_thrust', 'run_attack'):
            radius = 125 if action == 'run_attack' else 110
            sweep = min(1., .30+t*2.6)
            begin = -1.05 + max(0., t-.42)*1.2
            end = -1.05 + sweep*2.32
            height = 86 if action == 'run_attack' else 100
            points = [project(8+math.cos(a)*radius, math.sin(a)*radius*.80, height)
                      for a in (begin+(end-begin)*i/27 for i in range(28))]
            ribbon(layer, points, 18 if action == 'run_attack' else 15, alpha)
            # A short parallel remnant makes the cut feel fast without
            # filling the whole area in front of the knight.
            if t > .2:
                ribbon(layer, [(x-2*dx, y+3) for x, y in points[5:23]], 3, round(alpha*.38))
        elif action == 'overhead_slash':
            reveal = min(1., .28+t*2.8)
            points = []
            for i in range(28):
                u = reveal*i/27
                forward = (1-u)**2*62 + 2*(1-u)*u*180 + u*u*(-38)
                height = (1-u)**2*30 + 2*(1-u)*u*140 + u*u*223
                points.append(project(forward, -16+30*u, height))
            ribbon(layer, points, 16, alpha)
        elif action == 'ground_slam':
            reveal = min(1., .30+t*2.9)
            points = []
            for i in range(24):
                u = reveal*i/23
                forward = -32+96*u
                height = 223*(1-u)**.70
                points.append(project(forward, 8*math.sin(u*math.pi), height))
            ribbon(layer, points, 18, alpha)
        elif action == 'dash_attack':
            reach = 125+min(1., t*3)*83
            points = [project(20+(reach-20)*i/22, 0, 88) for i in range(23)]
            ribbon(layer, points, 9, alpha)
            for side in (-12, 12):
                points = [project(38+(reach-60)*i/17, side, 88) for i in range(18)]
                ribbon(layer, points, 3, round(alpha*.5))
        expanded = pygame.transform.scale(layer, (LAYER_SIZE*FX_PIXEL, LAYER_SIZE*FX_PIXEL))
        surface.blit(expanded, (round(feet[0]+ox)-ORIGIN[0]*FX_PIXEL,
                                round(feet[1]+oy)-ORIGIN[1]*FX_PIXEL))

    def draw_back(self, surface, ox, oy):
        for echo in self.echoes:
            fade = max(0., 1-echo['age']/190)
            frame = echo['frame'].copy()
            frame.set_alpha(round(88*fade**1.4))
            fx, fy = echo['feet']
            surface.blit(frame, (round(fx+ox)-192, round(fy+oy)-288))
        if self.wake:
            feet, angle, age = self.wake
            dx, dy = math.cos(math.radians(-angle)), math.sin(math.radians(-angle))
            self._texture(surface, 'dash_wake', age,
                          (feet[0]-dx*25, feet[1]-75-dy*18), ox, oy,
                          angle=angle, opacity=185)
        for b in self.bursts:
            if b['kind'] == 'dust':
                self._texture(surface, b['kind'], b['age'], b['position'], ox, oy,
                              angle=b['angle'], opacity=b['opacity'])
        if self.swing and self.swing[1] == 'up':
            self._draw_swing(surface, ox, oy)

    def draw_front(self, surface, ox, oy):
        if self.swing and self.swing[1] != 'up':
            self._draw_swing(surface, ox, oy)
        for b in self.bursts:
            if b['kind'] != 'dust':
                self._texture(surface, b['kind'], b['age'], b['position'], ox, oy,
                              angle=b['angle'], opacity=b['opacity'])
