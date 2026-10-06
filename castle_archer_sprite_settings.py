"""Read Castle Archer sprite dimensions, scale, frame counts and bow release positions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'assets/Castle_Archer'
BANK = json.loads((ROOT / 'manifest.json').read_text())
SCALE = BANK['scale']
CELL_SIZE = BANK['cell_size'][0]
PIVOT = tuple(round(value*SCALE) for value in BANK['pivot'])
FRAME_COUNTS = {name: spec['frames_per_direction']
                for name, spec in BANK['animations'].items()}
RELEASE_FRAME = BANK['attack_release_frame']

# Native-pixel bow grips relative to the ground pivot, on the release pose.
# Projectiles start here instead of inside the enemy's torso.
BOW_SOCKETS = {'down': (15, -66), 'left': (-40, -71),
               'right': (42, -72), 'up': (-14, -87)}
