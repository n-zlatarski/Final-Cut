"""Regression checks for the reported running glitch and new attack effects."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
from entities import Enemy, COMMANDER_ACTIONS
from igris_data import IGRIS_BANK, IGRIS_FRAME_ENDS
from igris_vfx import effect_assets

VECTORS = {'right': (1, 0), 'left': (-1, 0), 'up': (0, -1), 'down': (0, 1)}


def boss():
    e = Enemy('blood_red_commander', 850, 650)
    e.is_boss = True
    e.enemy_detected = True
    return e


def run(baseline=None):
    report = {'checks': [], 'chase_cases': 0}
    run_clip = IGRIS_BANK.clips['Run']
    assert run_clip.total_ms == 900
    assert IGRIS_BANK.clips['Walk'].total_ms == 1050
    for row in run_clip.frames:
        assert len({pygame.image.tobytes(f, 'RGBA') for f in row}) == 8
        heights = [f.get_bounding_rect(min_alpha=128).height for f in row]
        assert min(heights) >= 60 and max(heights) <= 70, heights
        # A half-cycle must actually change the feet, not just the cape.
        a = row[0].subsurface((68, 108, 58, 25))
        b = row[4].subsurface((68, 108, 58, 25))
        assert pygame.image.tobytes(a, 'RGBA') != pygame.image.tobytes(b, 'RGBA')
    report['checks'].append('32 unique run frames at consistent 60-70px projected height; opposite half-strides change the legs')

    for fps in (30, 60, 144):
        for phase in (1, 2, 3):
            for direction, (dx, dy) in VECTORS.items():
                e = boss()
                e.hp = e.max_hp * {1: 1, 2: .6, 3: .3}[phase]
                e.boss_phase = phase
                e._set_anim('run')
                if direction == 'down': e.pos[1] = 400
                if direction == 'up': e.pos[1] = 900
                e.approach_angle = math.atan2(dy, dx)
                frames = set()
                distance = 0
                clock = 0
                for _ in range(math.ceil(fps * 1.05)):
                    before = tuple(e.pos)
                    old_time = e.anim_elapsed_ms
                    target = (e.center()[0]+dx*550, e.center()[1]+dy*550)
                    e.update(1000/fps, target, lambda *a, **k: False, allow_attack=False)
                    assert e.state == 'run' and e.sprite_direction == direction
                    distance += math.dist(before, e.pos)
                    clock += (e.anim_elapsed_ms-old_time) % IGRIS_FRAME_ENDS['run'][-1]
                    frames.add(e.frame_idx)
                assert frames == set(range(8)), (fps, phase, direction, frames)
                assert abs(clock - distance*16/(e.base_speed*1.65)) < .001
                report['chase_cases'] += 1
    report['checks'].append('36 actual AI chases: every direction, all boss phases, 30/60/144 FPS; all poses play and stride rate matches travel')

    e = boss()
    e._set_anim('walk')
    e.anim_elapsed_ms = 417.3
    phase = e.anim_elapsed_ms/IGRIS_FRAME_ENDS['walk'][-1]
    for state in ('run', 'walk', 'run', 'walk'):
        e._set_anim(state)
        assert abs(e.anim_elapsed_ms/IGRIS_FRAME_ENDS[state][-1]-phase) < 1e-10
    e._set_anim('run')
    e.move_direction = 'right'
    for dy in (1.01, .99, 1.06, .97)*5:
        e._face_vector(1, dy)
        assert e.move_direction == 'right'
    e._face_vector(1, 1.3)
    assert e.move_direction == 'down'
    for dx in (1.01, .99, 1.06, .97)*5:
        e._face_vector(dx, 1)
        assert e.move_direction == 'down'
    e._face_vector(-1, 0)
    assert e.move_direction == 'left'
    e.pos[0] = 10000
    e._clamp_position()
    before = e.anim_elapsed_ms
    e._move(1, 0, 16, speed_mult=1.65)
    e._advance_animation(16)
    assert e.anim_elapsed_ms == before
    e._move(0, 0, 16, speed_mult=1.65)
    e._advance_animation(16)
    assert e.anim_elapsed_ms == before
    report['checks'].append('Walk/run preserve stride phase; diagonal steering does not flicker; clear turns respond immediately; blocked movement stops gait advancement')

    # Check rendered cuts in world space, including their vertical depth.
    means = {}
    for direction in VECTORS:
        e = boss()
        e.igris_effects.swing = ('light_combo', direction, .30, (400, 400))
        surface = pygame.Surface((800, 800), pygame.SRCALPHA)
        e.igris_effects._draw_swing(surface, 0, 0)
        mask = pygame.mask.from_surface(surface)
        means[direction] = mask.centroid()
    assert means['right'][0] > 445 and means['left'][0] < 355, means
    assert means['up'][1] < means['down'][1]-20, means
    assert COMMANDER_ACTIONS['light_combo']['hit_times'] == (330, 500)
    assert COMMANDER_ACTIONS['overhead_slash']['hit_times'] == (410,)
    assert sum(IGRIS_BANK.clips['Attack1'].durations_ms) == 780
    assert sum(IGRIS_BANK.clips['Attack2'].durations_ms) == 780
    assert {'forehand','rising_cut','sweep','plunge','rupture','pierce','blood_wave','ground_wave','spark'} <= set(effect_assets())
    report['checks'].append('New cuts follow all four attack directions; two-cut and rising impact events match their newly authored poses')
    if baseline:
        original = json.loads(Path(baseline).read_text())
        protected = [p for p in original if p.startswith(('assets/Assassin/', 'assets/Knight_', 'assets/KnightsVerticalRemake/'))]
        for name in protected:
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == original[name], name
        report['protected_assets'] = len(protected)
        report['checks'].append('All approved Jinwoo and three-knight assets match their pre-change SHA256 hashes')
    report['status'] = 'passed'
    (ROOT/'tests/igris_refinement_qa.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path)
    run(parser.parse_args().baseline)
