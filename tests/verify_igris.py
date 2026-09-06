"""Headless checks of the actual Enemy loader, combat clock and rendering."""
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
from game_data import ENEMY_TYPES, ENEMY_ANIM_SETS
from igris_data import IGRIS_BANK, IGRIS_DURATIONS, IGRIS_FRAME_ENDS, IGRIS_PIVOT, IGRIS_STATE_CLIPS

DIRECTIONS = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1)}
report = {'action_cases': 0, 'render_cases': 0, 'checks': []}


def boss():
    e = Enemy('blood_red_commander', 850, 630)
    e.is_boss = True
    return e


def check_actions():
    for phase in (1, 2, 3):
        for action, cfg in COMMANDER_ACTIONS.items():
            for direction, (dx, dy) in DIRECTIONS.items():
                for step in (1000 / 30, 1000 / 60, 1000 / 144, 250):
                    e = boss()
                    e.boss_phase = phase
                    e.hp = e.max_hp * {1: 1, 2: .5, 3: .25}[phase]
                    e._commander_sequence = lambda: (action,)
                    center = e.center()
                    target = (center[0] + dx * 190, center[1] + dy * 190)
                    e._begin_attack(target, (0, 0))
                    assert e.sprite_direction == direction
                    hits, projectiles = [], []
                    def hit(damage, **kwargs):
                        hits.append((e.frame_idx, e.anim_elapsed_ms, damage))
                    def projectile(enemy, point, **kwargs):
                        projectiles.append((e.frame_idx, kwargs['kind']))
                    frames = {e.frame_idx}
                    elapsed = 0
                    while e.is_committed:
                        e.update(step, target, hit, projectile)
                        elapsed += step
                        if e.is_committed:
                            assert e.sprite_direction == direction
                            frames.add(e.frame_idx)
                        assert elapsed < 2000
                    assert [v[0] for v in hits] == list(cfg['hit_frames']), (action, direction, hits)
                    assert [v[1] for v in hits] == list(cfg['hit_times'])
                    assert [v[0] for v in projectiles] == [v[0] for v in cfg.get('projectile_frames', ())]
                    assert [v[1] for v in projectiles] == [v[1] for v in cfg.get('projectile_frames', ())]
                    expected = sum(IGRIS_DURATIONS[cfg['state']]) / e.boss_playback_rate
                    assert expected - .0001 <= elapsed <= expected + step + .0001
                    if step < 40:
                        assert frames == set(range(8)), (action, direction, step, frames)
                    report['action_cases'] += 1
    report['checks'].append('All 7 actions: exact impact frames, one hit/projectile per event, all directions/phases; 30/60/144 FPS and 250ms spikes')


def check_rendering():
    e = boss()
    e.pos[:] = [360, 480]
    canvas = pygame.Surface((1100, 1000), pygame.SRCALPHA)
    expected = canvas.copy()
    for direction in DIRECTIONS:
        for state in IGRIS_STATE_CLIPS:
            e.state = state
            e.sprite_direction = direction
            for frame_index, frame in enumerate(e._frames()):
                assert frame.get_size() == (576, 576)
                assert frame.get_bounding_rect().width > 0
                e.frame_idx = frame_index
                canvas.fill((0, 0, 0, 0))
                expected.fill((0, 0, 0, 0))
                feet = e.feet()
                expected.blit(frame, (round(feet[0]) - IGRIS_PIVOT[0],
                                      round(feet[1]) - IGRIS_PIVOT[1]))
                e.draw(canvas, 0, 0)
                assert pygame.image.tobytes(canvas, 'RGBA') == pygame.image.tobytes(expected, 'RGBA')
                report['render_cases'] += 1
    assert e.display == (205, 205)
    report['checks'].append('Every loaded frame uses the fixed feet pivot on a 576px render canvas; padded render size is separate from body geometry')


def check_lifecycle():
    e = boss()
    distant = (e.center()[0] - 1200, e.center()[1])
    e.update(900, distant, lambda *a, **k: None)
    assert e.state == 'idle' and not e.enemy_detected and e.anim_elapsed_ms == 900
    e.update(3000, distant, lambda *a, **k: None)
    assert e.anim_elapsed_ms == (3900 % 2450)
    target = (e.center()[0] - 550, e.center()[1])
    e.update(100, target, lambda *a, **k: None, allow_attack=False)
    assert e.state == 'run' and e.sprite_direction == 'left'
    e.guard_timer = 180
    e.update(30, e.center(), lambda *a, **k: None)
    assert e.state == 'idle_alert'
    e._set_anim('walk')
    e._advance_animation(250)
    phase = e.anim_elapsed_ms
    for direction in DIRECTIONS:
        e.move_direction = direction
        e._set_anim('walk')
        e._advance_animation(0)
        assert e.anim_elapsed_ms == phase and e.sprite_direction == direction
    e.sprite_direction = 'up'
    e.take_damage(130, stagger=1000)
    for _ in range(14):
        e.update(30, target, lambda *a, **k: None)
        assert e.state == 'hurt' and e.sprite_direction == 'up'
    assert e.frame_idx == 7 and e.boss_phase == 2
    e.update(30, target, lambda *a, **k: None)
    assert e.combat_state == 'approach'
    e.sprite_direction = 'down'
    e.take_damage(10000)
    for _ in range(205):
        e.update(10, target, lambda *a, **k: (_ for _ in ()).throw(AssertionError('dead boss dealt damage')))
        assert e.state == 'dead' and e.sprite_direction == 'down' and not e.dead_done
    e.update(10, target, lambda *a, **k: None)
    assert e.dead_done and e.frame_idx == 7
    position = tuple(e.feet())
    e._set_anim('walk')
    e.update(10000, target, lambda *a, **k: None)
    assert e.state == 'dead' and e.frame_idx == 7 and tuple(e.feet()) == position
    report['checks'].append('Search/alert idle, run detection, direction changes without phase reset, full hurt across HP phase changes, terminal death at 2060ms')


def check_phase_and_bounds():
    e = boss()
    target = (e.center()[0] + 190, e.center()[1])
    e._begin_attack(target, (0, 0))
    e.update(80, target, lambda *a, **k: None)
    e.take_damage(125, stagger=0)
    e.update(10, (target[0] - 380, target[1]), lambda *a, **k: None)
    assert e.boss_phase == 2 and e.is_committed and e.sprite_direction == 'right'
    assert e.anim_elapsed_ms == 90 and e.boss_playback_rate == 1
    e.pos[:] = [-10000, -10000]
    e._clamp_position()
    assert e.feet()[1] >= 560
    e.pos[:] = [10000, 10000]
    e._clamp_position()
    assert e.feet()[1] <= 1080
    for etype in ENEMY_TYPES:
        other = Enemy(etype, 600, 600)
        other.update(30, (900, 700), lambda *a, **k: None)
        assert len(other._frames()) > 0
    report['checks'].append('Committed moves survive phase/target changes; arena floor clamps; every other enemy still loads and updates')


if __name__ == '__main__':
    check_actions()
    check_rendering()
    check_lifecycle()
    check_phase_and_bounds()
    report['status'] = 'passed'
    (ROOT/'tests/igris_qa.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    pygame.quit()
