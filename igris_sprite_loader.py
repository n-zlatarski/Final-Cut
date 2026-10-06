"""Load and validate Igris sprite sheets, frame durations and animation variants."""
from dataclasses import dataclass
from pathlib import Path
import json
import pygame


@dataclass(frozen=True)
class Clip:
    frames: tuple
    durations_ms: tuple
    loop: bool


class IgrisSpriteLoader:
    def __init__(self, asset_dir=None):
        self.root = Path(asset_dir or Path(__file__).resolve().parent)
        self.manifest = json.loads((self.root / 'manifest.json').read_text())
        self.cell_size = tuple(self.manifest['cell_size'])
        self.pivot = tuple(self.manifest['pivot'])
        self.directions = tuple(self.manifest['direction_rows'])
        self.clips = {}
        cw,ch = self.cell_size
        for name, spec in self.manifest['animations'].items():
            file = spec['sheet']
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
            self.clips[name] = Clip(rows, durations, spec['loop'])
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
