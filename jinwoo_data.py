"""Authored pose timing for Jinwoo's new dagger attacks (milliseconds).

Only these attacks use a shared simulation clock. Locomotion and other
characters continue through the existing Animator unchanged.
"""
from bisect import bisect_right
from itertools import accumulate
import json
from pathlib import Path

BANK_PATH = Path(__file__).resolve().parent / 'assets/Assassin/EFlurry'
BANK = json.loads((BANK_PATH / 'manifest.json').read_text())
ATTACK_FRAME_MS = {
    'attack_1': (40, 50, 60, 65, 70, 65),
    'attack_2': (45, 60, 75, 75, 65, 70),
    'attack_3': (45, 65, 95, 85, 85, 80),
    'dash_attack': (40, 50, 46, 55, 60, 69),
    'deaths_dance': (70, 110, 120, 140, 160, 190, 150, 130, 70, 70, 100, 100),
    'sonic_stream': (45, 95, 65, 65, 65, 65, 65, 65, 65, 65, 65, 100, 100),
}
FRAME_STARTS = {name: (0, *accumulate(times)) for name, times in ATTACK_FRAME_MS.items()}


def frame_at(name, elapsed_ms):
    starts = FRAME_STARTS[name]
    return min(len(starts)-2, max(0, bisect_right(starts, elapsed_ms)-1))


def duration(name):
    return FRAME_STARTS[name][-1]


def animation_overrides():
    result = {name: (str(BANK_PATH / spec['sheet']), spec['frames_per_direction'], 4)
              for name, spec in BANK['animations'].items()}
    for alias, target in BANK['aliases'].items():
        result[alias] = result[target]
    return result
