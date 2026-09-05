"""Small Pygame sprite player with fixed feet pivots and time-based playback.

No movement, collision or damage decisions are made by this module.
The game supplies the world-space feet position and chooses actions.
"""
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
import json
import math
import pygame


@dataclass(frozen=True)
class Clip:
    frames: tuple
    durations_ms: tuple
    loop: bool
    terminal: bool = False

    @property
    def total_ms(self):
        return sum(self.durations_ms)


class IgrisAnimator:
    def __init__(self, asset_dir=None, with_shadow=True):
        self.root = Path(asset_dir or Path(__file__).resolve().parent)
        self.manifest = json.loads((self.root / 'manifest.json').read_text())
        self.cell_size = tuple(self.manifest['cell_size'])
        self.pivot = tuple(self.manifest['pivot'])
        self.directions = tuple(self.manifest['direction_rows'])
        self.clips = {}
        self._scaled = {}
        cw,ch = self.cell_size
        for name, spec in self.manifest['animations'].items():
            file = spec['sheet' if with_shadow else 'sheet_no_shadow']
            sheet = pygame.image.load(str(self.root / file))
            if pygame.display.get_surface() is not None:
                sheet = sheet.convert_alpha()
            count = spec['frames_per_direction']
            if sheet.get_size() != (cw*count, ch*len(self.directions)):
                raise ValueError(f'{name}: atlas size does not match the manifest')
            durations = tuple(spec['durations_ms'])
            if len(durations) != count or any(d<=0 for d in durations):
                raise ValueError(f'{name}: invalid frame durations')
            rows = tuple(tuple(sheet.subsurface((c*cw,r*ch,cw,ch)).copy()
                               for c in range(count)) for r in range(len(self.directions)))
            self.clips[name] = Clip(rows, durations, spec['loop'], spec.get('terminal',False))
        # Alert idle reuses only neutral/breathing poses; no search glances.
        for name,spec in self.manifest.get('variants',{}).items():
            source=self.clips[spec['source']]
            indices=tuple(spec['frame_indices'])
            durations=tuple(spec['durations_ms'])
            if len(indices)!=len(durations) or any(d<=0 for d in durations):
                raise ValueError(f'{name}: invalid variant durations')
            self.clips[name]=Clip(
                tuple(tuple(row[i] for i in indices) for row in source.frames),
                durations,spec['loop'])
        self.name = 'Idle'
        self.direction = 'down'
        self.elapsed_ms = 0.0
        self.finished = False

    @property
    def clip(self):
        return self.clips[self.name]

    @property
    def frame_index(self):
        cumulative=[]
        total=0
        for ms in self.clip.durations_ms:
            total+=ms
            cumulative.append(total)
        return min(bisect_right(cumulative,self.elapsed_ms),len(cumulative)-1)

    @property
    def frame(self):
        return self.clip.frames[self.directions.index(self.direction)][self.frame_index]

    def play(self, name, direction=None, *, restart=False, force=False):
        """Repeated calls and direction changes do not restart the same clip.

        Death locks until reset() or explicit force=True. Normal one-shot clips
        hold their last pose until the game's state machine selects another clip.
        """
        if name not in self.clips:
            raise KeyError(f'Unknown Igris animation: {name}')
        direction = direction or self.direction
        if direction not in self.directions:
            raise ValueError(f'Unknown direction: {direction}')
        if self.clip.terminal and name != self.name and not force:
            return False
        if name != self.name or restart:
            self.name = name
            self.elapsed_ms = 0.0
            self.finished = False
        self.direction = direction
        return True

    def play_idle(self, enemy_detected=False, direction=None):
        return self.play('Idle_Alert' if enemy_detected else 'Idle',direction)

    def update(self, dt_seconds):
        dt=float(dt_seconds)
        if not math.isfinite(dt) or dt<0:
            raise ValueError('dt_seconds must be finite and nonnegative')
        if self.finished:
            return
        self.elapsed_ms += dt*1000.0
        total=self.clip.total_ms
        if self.clip.loop:
            self.elapsed_ms %= total
        elif self.elapsed_ms >= total:
            self.elapsed_ms = float(total)
            self.finished = True

    def reset(self, direction='down'):
        self.play('Idle',direction,restart=True,force=True)

    def draw(self, surface, feet_position, scale=1):
        """Blit using the stable feet pivot. scale must be a positive integer."""
        if not isinstance(scale,int) or scale<1:
            raise ValueError('Use a positive integer scale for crisp pixels')
        image=self.frame
        if scale!=1:
            key=(self.name,self.direction,self.frame_index,scale)
            if key not in self._scaled:
                self._scaled[key]=pygame.transform.scale(image,
                    (self.cell_size[0]*scale,self.cell_size[1]*scale))
            image=self._scaled[key]
        pos=(round(feet_position[0])-self.pivot[0]*scale,
             round(feet_position[1])-self.pivot[1]*scale)
        return surface.blit(image,pos)
