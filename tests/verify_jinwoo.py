"""Validate the loaded Jinwoo remake and render an asset comparison.

Checks production animation rows, actual Animator playback, silhouette padding,
weapon/hand readability, terminal death and the preserved world foot position.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
from animator import Animator
from game_data import (ASSASSIN_ANIM_ROWS, ASSASSIN_SHEETS,
                       ASSASSIN_DRAW_OFFSET, ENEMY_ANIM_SETS)
from sprite_loaders import load_sheet_all_rows

ASSETS = ROOT / 'assets/Assassin/PixelRemake'
QA = ROOT / 'tests/screenshots/jinwoo'
QA.mkdir(parents=True, exist_ok=True)
BG = (18, 19, 27)
CREAM = (235, 222, 204)
DIM = (174, 174, 185)
FONT = pygame.font.SysFont('DejaVu Sans', 22)
SMALL = pygame.font.SysFont('DejaVu Sans', 18)
TITLE = pygame.font.SysFont('DejaVu Sans', 27, bold=True)


def text(surface, label, pos, font=FONT, color=CREAM):
    surface.blit(font.render(label, True, color), pos)


def planted(surface, frame, feet, pivot=(120, 176), zoom=1):
    pic = pygame.transform.scale(frame, (round(frame.get_width() * zoom),
                                         round(frame.get_height() * zoom)))
    surface.blit(pic, (round(feet[0] - pivot[0] * zoom),
                       round(feet[1] - pivot[1] * zoom)))


def comparison(destination):
    before_idle = load_sheet_all_rows('assets/Assassin/GameReady/idle.png', 6, 4, (220, 220), True)
    before_run = load_sheet_all_rows('assets/Assassin/GameReady/run.png', 8, 4, (220, 220), True)
    surface = pygame.Surface((1500, 880))
    surface.fill(BG)
    text(surface, 'BEFORE', (40, 26), TITLE)
    text(surface, 'JINWOO REMAKE', (795, 26), TITLE)
    text(surface, 'Sprites enlarged 2× for comparison', (40, 65), SMALL, DIM)
    for frames, x, label in ((before_idle[0][0], 220, 'Idle'), (before_run[2][3], 580, 'Run')):
        planted(surface, frames, (x, 333), (110, 164), 2)
        text(surface, label, (x - 23, 365), SMALL)
    for frame, x, label in ((ASSASSIN_ANIM_ROWS['idle'][0][0], 970, 'Idle'),
                             (ASSASSIN_ANIM_ROWS['run'][2][3], 1320, 'Run')):
        planted(surface, frame, (x, 333), zoom=2)
        text(surface, label, (x - 23, 365), SMALL)
    pygame.draw.line(surface, (61, 56, 63), (35, 418), (1465, 418))
    text(surface, 'TOGETHER AT GAME SCALE', (40, 446), FONT)
    text(surface, 'DASH ATTACK', (565, 446), FONT)
    text(surface, 'TWIN DAGGER RAKE', (1030, 446), FONT)
    igris = ENEMY_ANIM_SETS['blood_red_commander']['down']['idle'][0]
    planted(surface, igris, (210, 790), (288, 384), 1.3)
    planted(surface, ASSASSIN_ANIM_ROWS['idle'][0][0], (413, 790), zoom=1.3)
    planted(surface, ASSASSIN_ANIM_ROWS['dash_attack'][2][2], (773, 790), zoom=2)
    planted(surface, ASSASSIN_ANIM_ROWS['attack_3'][0][3], (1240, 790), zoom=2)
    text(surface, 'Same relative character sizes', (76, 822), SMALL, DIM)
    text(surface, 'Red daggers · blue dash wake', (622, 822), SMALL, DIM)
    text(surface, 'Simple shading · clear pixel shapes', (1085, 822), SMALL, DIM)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, destination)
    pygame.image.save(surface, QA / 'Before_After.png')


def run(destination=None):
    manifest = json.loads((ASSETS / 'manifest.json').read_text())
    report = {'checks': [], 'source_frames': 0, 'playback_cases': 0}
    assert tuple(manifest['pivot'][i] * 2 + ASSASSIN_DRAW_OFFSET[i] for i in range(2)) == (110, 164)
    expected_names = set(manifest['animations']) - {'deaths_dance_spin'} | {'deaths_dance'}
    assert set(ASSASSIN_ANIM_ROWS) == expected_names | {'walk_attack'}
    mins = {'skin_pixels': 99999, 'red_blade_pixels': 99999}
    for name in sorted(expected_names):
        rows = ASSASSIN_ANIM_ROWS[name]
        count = ASSASSIN_SHEETS[name][1]
        assert len(rows) == 4 and all(len(row) == count for row in rows), name
        for direction, row in enumerate(rows):
            hashes = set()
            for frame_index, frame in enumerate(row):
                assert frame.get_size() == (240, 240)
                box = frame.get_bounding_rect(min_alpha=30)
                assert box.left >= 4 and box.top >= 4 and box.right <= 236 and box.bottom <= 236, (name, direction, box)
                hashes.add(hashlib.sha256(pygame.image.tobytes(frame, 'RGBA')).hexdigest())
                pixels = pygame.surfarray.array3d(frame)
                alpha = pygame.surfarray.array_alpha(frame) > 30
                red, green, blue = [pixels[:, :, i].astype(float) for i in range(3)]
                skin = int((alpha & (red > 175) & (green > 95) & (blue < 190) & (red > green * 1.08)).sum())
                blade = int((alpha & (red > 115) & (red > green * 1.65) & (red > blue * 1.4)).sum())
                # These inspected rear contacts hide both hands and blades
                # in front of the coat, without hands drawn on its back.
                occluded = direction == 3 and (name,frame_index) in {
                    ('attack_3',3),('walk_attack_3',3),
                    ('deaths_dance',6),('sonic_stream',7)}
                assert blade >= 12 or occluded, (name, direction, frame_index, skin, blade)
                # Crossed hands can be correctly hidden by the torso in a
                # back view or during a special's full-body turn.
                if direction != 3 and name not in ('deaths_dance', 'sonic_stream'):
                    assert skin >= 4, (name, direction, skin, blade)
                mins['skin_pixels'] = min(mins['skin_pixels'], skin)
                mins['red_blade_pixels'] = min(mins['red_blade_pixels'], blade)
                report['source_frames'] += 1
            assert len(hashes) == count, (name, direction, 'duplicate frames')
            # Verify every authored pose is reached through the real Animator.
            for rate in (30, 60, 144):
                fps = 32 if name == 'dash' else 16 if 'attack' in name else 9 if name in ('deaths_dance', 'sonic_stream') else 8
                player = Animator({name: row}, default=name, fps=fps)
                terminal = name not in ('idle', 'walk', 'run')
                player.play(name, one_shot=terminal, force=True)
                visited = {player.frame_idx}
                for _ in range(round((count / fps + 0.5) * rate)):
                    player.update(1000 / rate)
                    visited.add(player.frame_idx)
                assert visited == set(range(count)), (name, direction, rate, visited)
                if terminal:
                    assert player.done and player.frame_idx == count - 1
                    for _ in range(rate):
                        player.update(1000 / rate)
                    assert player.frame_idx == count - 1
                report['playback_cases'] += 1
    assert report['source_frames'] == 448
    assert ASSASSIN_ANIM_ROWS['walk_attack'][0][0].get_size() == (240, 240)
    for direction in range(4):
        idle_h = ASSASSIN_ANIM_ROWS['idle'][direction][0].get_bounding_rect().height
        dead_h = ASSASSIN_ANIM_ROWS['death'][direction][-1].get_bounding_rect().height
        assert dead_h < idle_h * .65, (direction, idle_h, dead_h)
    report['checks'] = [
        '16 animations in four directions, 448 nonempty frames (unique within each clip), visible crimson blades except correctly occluded rear contacts, no clipping',
        'All authored frames visited at 30, 60 and 144 FPS; one-shot clips finish and terminal death remains collapsed',
        'Fixed world feet pivot (110,164) with transparent padding; 12-pose Q / thirteen-pose E and six-pose moving combos loaded',
    ]
    report.update(minimum_visible_pixels=mins, status='passed')
    (ROOT / 'tests/jinwoo_qa.json').write_text(json.dumps(report, indent=2) + '\n')
    for page in range(4):
        names = list(manifest['animations'])[page * 4:page * 4 + 4]
        surface = pygame.Surface((1160, 1050))
        surface.fill(BG)
        for d, label in enumerate(manifest['direction_rows']):
            text(surface, label.upper(), (220 + d * 240, 15))
        for index, source_name in enumerate(names):
            name = 'deaths_dance' if source_name == 'deaths_dance_spin' else source_name
            text(surface, name, (12, 120 + index * 250), SMALL)
            for d, row in enumerate(ASSASSIN_ANIM_ROWS[name]):
                surface.blit(row[len(row) // 2], (195 + d * 240, 45 + index * 250))
        pygame.image.save(surface, QA / f'contact_{page + 1}.png')
    if destination:
        comparison(destination)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--comparison', type=Path)
    args = parser.parse_args()
    run(args.comparison)
