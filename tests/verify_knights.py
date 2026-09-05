"""Check vertical stride artwork, hit timing and mobile knight recovery.

Optional recording shows the six real loaded loops followed by actual
terrace combat. Only test inputs, enemy placement and extra player health
are scripted; production movement, attacks and animation code are used.
"""
import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import math
from pathlib import Path
import random
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_gameplay import Harness, ROOT
from verify_jinwoo_idle import Preview
import numpy as np
import pygame
import gameplay
from entities import Enemy
from game_data import ENEMY_TYPES, ENEMY_ANIM_SETS, ENEMY_CROP_REGIONS, ENEMY_SCALE_FACTORS
from progression import new_run_state

KNIGHTS = ('knight1', 'knight2', 'knight3')
FONT = pygame.font.SysFont('DejaVu Sans', 21)
TITLE = pygame.font.SysFont('DejaVu Sans', 30, bold=True)
SMALL = pygame.font.SysFont('DejaVu Sans', 17)


def text(surface, value, position, font=FONT, color=(229, 235, 245)):
    surface.blit(font.render(value, True, color), position)


def verify_art():
    result = {}
    silhouettes = {}
    for k, name in enumerate(KNIGHTS, 1):
        originals = [pygame.image.load(ROOT / f'assets/Knight_{k}/{f}')
                     for f in ('Idle.png', 'Walk.png')]
        colors = set()
        for image in originals:
            rgb = pygame.surfarray.array3d(image)
            alpha = pygame.surfarray.array_alpha(image)
            colors.update(map(tuple, rgb[alpha > 127]))
        for direction in ('down', 'up'):
            sheet = pygame.image.load(ROOT / f'assets/Knight_{k}/Walk_{direction.title()}.png')
            assert sheet.get_size() == (1024, 128)
            frames = [sheet.subsurface((i * 128, 0, 128, 128)) for i in range(8)]
            assert len({hashlib.sha256(pygame.image.tobytes(f, 'RGBA')).hexdigest() for f in frames}) == 8
            soles, heads, heights = [], [], []
            for i, frame in enumerate(frames):
                rgb = pygame.surfarray.array3d(frame)
                alpha = pygame.surfarray.array_alpha(frame)
                assert set(np.unique(alpha)) <= {0, 255}
                assert set(map(tuple, rgb[alpha > 127])) <= colors
                key = (direction, i)
                if k == 1:
                    silhouettes[key] = alpha
                else:
                    assert np.array_equal(alpha, silhouettes[key]), 'Variant changed body geometry'
                box = frame.get_bounding_rect()
                assert box.left >= 8 and box.right <= 120
                assert 62 <= box.height <= 65
                heights.append(box.height)
                xs, _ = np.nonzero(alpha[:, box.top:box.top + 9] > 127)
                heads.append((int(xs.min()) + int(xs.max())) / 2)
                xs, _ = np.nonzero(alpha[50:78, 120:] > 127)
                soles.append(float(xs.mean() + 50))
            assert max(heads) - min(heads) <= 2, (name, direction, heads)
            assert abs(soles[4] - soles[0]) >= 4, (name, direction, 'No opposite step')
            midpoint = (soles[0] + soles[4]) / 2
            signs = [s > midpoint for s in soles]
            assert sum(signs[i] != signs[(i + 1) % 8] for i in range(8)) == 2, 'Foot changes side more than once per step'
            assert max(abs(soles[i] - soles[(i + 1) % 8]) for i in range(8)) < 5
            assert len(ENEMY_ANIM_SETS[name][direction]['walk']) == 8
            for rate in (30, 60, 144):
                enemy = Enemy(name, 600, 600)
                enemy._set_anim('walk')
                enemy.move_direction = direction
                seen = set()
                for _ in range(3 * rate):
                    enemy._advance_animation(1000 / rate)
                    seen.add(int(enemy.frame_idx))
                assert seen == set(range(8)), (name, direction, rate, seen)
            result[f'{name}_{direction}'] = {'frames': 8, 'body_heights': heights,
                                            'leading_foot_centers': soles,
                                            'helmet_center_range_px': max(heads) - min(heads)}
    return result


def combat_trace(cls, name, rate, direction):
    random.seed(735)
    enemy = cls(name, 700, 560)
    enemy.attack_cd = 0
    dt = 1000 / rate
    seen = set()
    hits = []
    records = []
    vec = {'left': (-80, 0), 'right': (80, 0), 'up': (0, -80), 'down': (0, 80)}[direction]
    for tick in range(4 * rate):
        center = enemy.center()
        target = (center[0] + vec[0], center[1] + vec[1])
        had_hits = len(hits)
        old_pos = tuple(enemy.pos)
        enemy.update(dt, target, lambda *args, **kwargs: hits.append(tick * dt))
        if enemy.state == 'attack':
            seen.add(int(enemy.frame_idx))
        records.append({'time': tick * dt, 'phase': enemy.combat_state,
                        'state': enemy.state, 'frame': int(enemy.frame_idx),
                        'moved': math.dist(old_pos, enemy.pos), 'attacks': enemy.attack_count,
                        'hit': len(hits) > had_hits})
    longest = run = 0.0
    for row in records:
        run = run + dt if row['state'] == 'attack' and row['frame'] == 4 else 0.0
        longest = max(longest, run)
    return enemy, records, seen, hits, longest


def verify_combat():
    report = []
    for name in KNIGHTS:
        for rate in (30, 60, 144):
            for direction in ('left', 'right', 'up', 'down'):
                enemy, records, seen, hits, hold = combat_trace(Enemy, name, rate, direction)
                assert seen == set(range(5)), (name, rate, seen)
                resolved_attacks = enemy.attack_count - (enemy.combat_state == 'windup')
                assert len(hits) == resolved_attacks, (name, 'Missing or repeated hit')
                hit_attacks = [r['attacks'] for r in records if r['hit']]
                assert len(hit_attacks) == len(set(hit_attacks)), 'Multiple hits from one strike'
                assert all(r['frame'] == 4 and r['state'] == 'attack' for r in records if r['hit'])
                recovery = [r for r in records if r['phase'] == 'recover']
                assert recovery and all(r['state'] == 'walk' for r in recovery)
                for previous, current in zip(records, records[1:]):
                    if previous['phase'] == current['phase'] == 'recover':
                        assert current['moved'] > 0, (name, rate, 'Stationary recovery')
                        assert current['attacks'] == previous['attacks'], 'Attack during recovery'
                assert hold <= 125 + 1000 / rate + .001, (name, rate, hold)
                starts = [r['time'] for i, r in enumerate(records)
                          if r['phase'] == 'windup' and (i == 0 or records[i-1]['phase'] != 'windup')]
                minimum = enemy.windup_ms + 125 + enemy.recovery_ms + enemy.attack_cooldown
                assert all(b - a >= minimum - .001 for a, b in zip(starts, starts[1:])), 'Attack rate increased'
                report.append({'knight': name, 'rate': rate, 'direction': direction,
                               'hits': len(hits), 'last_slash_hold_ms': round(hold, 2),
                               'recovery_movement_px': round(sum(r['moved'] for r in recovery), 2)})
    return report


def baseline_checks(path):
    loader = importlib.machinery.SourceFileLoader('knight_baseline_entities', str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    result = {'before_last_slash_hold_ms': {}, 'other_enemies_unchanged': []}
    for name in KNIGHTS:
        _, _, _, _, hold = combat_trace(module.Enemy, name, 60, 'right')
        result['before_last_slash_hold_ms'][name] = round(hold, 2)
        assert hold > 300
    for name in sorted(set(ENEMY_TYPES) - set(KNIGHTS)):
        traces = []
        for cls in (module.Enemy, Enemy):
            random.seed(963)
            enemy = cls(name, 700, 560)
            enemy.attack_cd = 0
            trace = []
            for tick in range(480):
                center = enemy.center()
                target = (center[0] + (330 if enemy.ranged else 90), center[1] + 20)
                enemy.update(1000 / 60, target, lambda *a, **kw: None,
                             spawn_projectile=lambda *a, **kw: None)
                trace.append((enemy.combat_state, enemy.state, enemy.frame_idx,
                              tuple(enemy.pos), enemy.attack_count, enemy.attack_cd))
            traces.append(trace)
        assert traces[0] == traces[1], (name, 'Unrelated enemy behavior changed')
        result['other_enemies_unchanged'].append(name)
    return result


def showcase(preview):
    actors = []
    for name in KNIGHTS:
        pair = []
        for direction in ('down', 'up'):
            enemy = Enemy(name, 600, 600)
            enemy._set_anim('walk')
            enemy.move_direction = direction
            pair.append(enemy)
        actors.append(pair)
    for tick in range(480):
        canvas = pygame.Surface((1280, 720))
        canvas.fill((23, 28, 38))
        text(canvas, 'KNIGHTS / VERTICAL WALK REMAKE', (28, 18), TITLE)
        text(canvas, 'Eight poses per direction / original armor palettes / playback at game speed',
             (28, 62), SMALL, (166, 178, 196))
        for col, pair in enumerate(actors):
            x = 230 + col * 410
            name = KNIGHTS[col]
            text(canvas, ENEMY_TYPES[name]['name'], (x - 91, 102))
            scale = ENEMY_SCALE_FACTORS[name]
            crop = ENEMY_CROP_REGIONS[name]
            pivot = ((64 - crop.x) * scale, (127 - crop.y) * scale)
            for row, enemy in enumerate(pair):
                y = 362 + row * 300
                text(canvas, ('DOWN', 'UP')[row], (x - 24, y + 16), SMALL, (117, 214, 180))
                frame = enemy._frames()[int(enemy.frame_idx)]
                canvas.blit(frame, (round(x - pivot[0]), round(y - pivot[1])))
                enemy._advance_animation(1000 / 60)
        if tick % 2 == 0:
            preview.write(canvas)
        if tick == 1:
            pygame.image.save(canvas, ROOT / 'tests/screenshots/knights_walks.png')


class StageDone(Exception):
    pass


class KnightsHarness(Harness):
    def __init__(self, preview):
        super().__init__('knights')
        self.preview = preview
        self.states_seen = {name: set() for name in KNIGHTS}
        self.recovery_motion = {name: 0.0 for name in KNIGHTS}
        self.last_positions = {}

    def events(self):
        return []

    def present(self, surface):
        self.latest = sys._getframe(1).f_locals
        self.frames += 1
        current = self.latest
        if self.frames == 1:
            current['hero_pos'][:] = [850, 630]
            current['previous_hero_pos'][:] = current['hero_pos']
        for enemy in current['enemies']:
            self.states_seen[enemy.etype].add((enemy.combat_state, enemy.state))
            if enemy.combat_state == 'recover':
                assert enemy.state == 'walk'
                old = self.last_positions.get(enemy.etype, tuple(enemy.pos))
                self.recovery_motion[enemy.etype] += math.dist(old, enemy.pos)
            self.last_positions[enemy.etype] = tuple(enemy.pos)
        t = self.frames / 60
        self.keys.held = ({pygame.K_w} if 3 <= t < 4.5 else
                          {pygame.K_s} if 4.5 <= t < 6.5 else set())
        if self.preview and self.frames % 2 == 0:
            canvas = pygame.transform.scale(surface, (1280, 720))
            bar = pygame.Surface((1280, 51), pygame.SRCALPHA)
            bar.fill((9, 13, 20, 224))
            canvas.blit(bar, (0, 669))
            text(canvas, 'IN GAME / Knights resume footwork after the swing; the next attack still has its cooldown.',
                 (23, 683), SMALL)
            self.preview.write(canvas)
        if self.frames == 1080:
            raise StageDone


def run(record=None, baseline=None):
    report = {'art': verify_art(), 'combat_cases': verify_combat()}
    if baseline:
        report['baseline'] = baseline_checks(baseline)
    preview = Preview(record) if record else None
    try:
        if preview:
            showcase(preview)
        def spawn(_):
            return [Enemy('knight1', 650, 390), Enemy('knight2', 990, 650), Enemy('knight3', 790, 810)]
        state = new_run_state()
        state['bonus_health'] = 1000
        with patch.object(gameplay, 'spawn_enemies', side_effect=spawn), KnightsHarness(preview) as harness:
            try:
                gameplay.stage_screen('Assassin', 'Jinwoo', 2, state)
            except StageDone:
                pass
            assert harness.frames == 1080
            for name in KNIGHTS:
                assert {('windup', 'attack'), ('active', 'attack'), ('recover', 'walk')} <= harness.states_seen[name]
                assert harness.recovery_motion[name] > 20, (name, harness.recovery_motion)
            report['stage_probe'] = {'seconds': 18, 'recovery_movement_px': harness.recovery_motion,
                                     'conditions': 'Real terrace gameplay, three knight placements, scripted movement, extra test player health'}
    finally:
        if preview:
            preview.close()
    report['status'] = 'passed'
    (ROOT / 'tests/knights_qa.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'walk_strips': len(report['art']),
                      'combat_cases': len(report['combat_cases']),
                      'baseline': report.get('baseline'), 'stage_probe': report['stage_probe']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--record', type=Path)
    parser.add_argument('--baseline', type=Path, help='Optional pre-fix entities.py for behavior comparison')
    args = parser.parse_args()
    run(args.record, args.baseline)
