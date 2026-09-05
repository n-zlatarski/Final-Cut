"""Regression for idle gliding: visible soles, real playback and stage input.

The stage probe removes enemies only inside the test so idle cannot be
interrupted by knockback. No movement or rendering code is replaced.
Optional preview: six seconds of before/after loops, then all four
directions in the actual terrace stage with a magnified view.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_gameplay import Harness, ROOT
import numpy as np
import pygame
import gameplay
from animator import Animator
from game_data import ASSASSIN_ANIM_ROWS, _a_idle_rows
from progression import new_run_state
from sprite_loaders import load_sheet_all_rows

DIRECTIONS = ('down', 'left', 'right', 'up')
ORDER = ('up', 'left', 'down', 'right')
KEYS = dict(zip(ORDER, (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d)))
BG = (19, 23, 32)
WHITE = (235, 239, 246)
DIM = (156, 169, 186)
GREEN = (108, 216, 176)
AMBER = (244, 173, 104)
FONT = pygame.font.SysFont('DejaVu Sans', 22)
SMALL = pygame.font.SysFont('DejaVu Sans', 17)
TITLE = pygame.font.SysFont('DejaVu Sans', 30, bold=True)


def text(surface, value, position, font=FONT, color=WHITE):
    surface.blit(font.render(value, True, color), position)


def sole_position(frame):
    """Read the lowest pale shoe soles, excluding daggers, hands and shirt."""
    rgb = pygame.surfarray.array3d(frame)
    alpha = pygame.surfarray.array_alpha(frame)
    ys = np.arange(frame.get_height())[None, :]
    mask = (rgb.min(axis=2) > 110) & (alpha > 30) & (ys >= 168)
    xs, ys = np.nonzero(mask)
    assert len(xs), 'No visible planted shoe sole'
    floor = int(ys.max())
    bottom_x = xs[ys >= floor - 3]
    return ((int(bottom_x.min()) + int(bottom_x.max())) / 2, floor)


def measure(rows):
    report = {}
    for name, row in zip(DIRECTIONS, rows):
        points = [sole_position(frame) for frame in row]
        report[name] = {
            'sole_positions': points,
            'vertical_travel_px': max(p[1] for p in points) - min(p[1] for p in points),
            'horizontal_center_range_px': max(p[0] for p in points) - min(p[0] for p in points),
        }
    return report


class Preview:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.process = subprocess.Popen([
            'ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo',
            '-pixel_format', 'rgb24', '-video_size', '1280x720',
            '-framerate', '30', '-i', '-', '-an', '-c:v', 'libx264',
            '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p',
            '-threads', '2', '-movflags', '+faststart', str(path)],
            stdin=subprocess.PIPE)
        self.frames = 0

    def write(self, surface):
        self.process.stdin.write(pygame.image.tobytes(surface, 'RGB'))
        self.frames += 1

    def close(self):
        self.process.stdin.close()
        assert self.process.wait(timeout=30) == 0


def comparison(preview, before_rows):
    players = []
    for rows in (before_rows, ASSASSIN_ANIM_ROWS['idle']):
        players.append([Animator({'idle': rows[d] + list(reversed(rows[d]))})
                        for d in (3, 1)])
    for tick in range(360):
        canvas = pygame.Surface((1280, 720))
        canvas.fill(BG)
        text(canvas, 'JINWOO / IDLE ALIGNMENT', (30, 17), TITLE)
        text(canvas, 'Same model and breathing poses. Playback at game speed; pixels enlarged 2x.',
             (30, 59), SMALL, DIM)
        for column, label in enumerate(('BEFORE', 'FIXED')):
            color = AMBER if column == 0 else GREEN
            text(canvas, label, (column * 640 + 295, 94), FONT, color)
            for row, direction in enumerate(('UP', 'LEFT')):
                x, y = 350 + column * 640, 363 + row * 290
                text(canvas, direction, (25 + column * 640, 165 + row * 290), FONT, DIM)
                for gy in range(y - 220, y + 11, 20):
                    pygame.draw.line(canvas, (31, 37, 49), (x - 125, gy), (x + 125, gy))
                pygame.draw.line(canvas, color, (x - 76, y), (x + 76, y))
                frame = players[column][row].get_frame()
                canvas.blit(pygame.transform.scale(frame, (480, 480)), (x - 240, y - 352))
                players[column][row].update(1000 / 60)
        pygame.draw.line(canvas, (53, 62, 77), (639, 96), (639, 695))
        if tick % 2 == 0:
            preview.write(canvas)


class ProbeComplete(Exception):
    pass


class IdleHarness(Harness):
    def __init__(self, preview=None):
        super().__init__('idle')
        self.preview = preview
        self.keys.held = {KEYS[ORDER[0]]}
        self.samples = {d: [] for d in ORDER}
        self.seen = {d: set() for d in ORDER}
        self.walk_seen = set()
        self.soles = {id(f): sole_position(f) for row in _a_idle_rows for f in row}

    def events(self):
        return []

    def present(self, surface):
        # Must be called directly by stage_screen: the locals are the actual
        # hero position, selected direction and sprite being drawn that frame.
        self.latest = sys._getframe(1).f_locals
        self.frames += 1
        phase, step = divmod(self.frames - 1, 240)
        direction = ORDER[phase]
        current = self.latest
        assert current['direction'] == direction
        if step == 0:
            assert current['anim'].current == 'walk'
            self.walk_seen.add(direction)
        else:
            assert current['anim'].current == 'idle'
            assert current['hero_velocity'] == [0.0, 0.0]
            assert current['ox'] == current['oy'] == 0
            frame = current['anim'].get_frame()
            sole_x, sole_y = self.soles[id(frame)]
            self.samples[direction].append({
                'position': list(current['hero_pos']),
                'sole_world': [current['hero_x'] + sole_x, current['hero_y'] + sole_y],
            })
            self.seen[direction].add(current['anim'].frame_idx)
        if self.preview and self.frames % 2 == 0:
            canvas = pygame.Surface((1280, 720))
            canvas.fill(BG)
            text(canvas, f'IN GAME / FACING {direction.upper()}', (28, 20), TITLE)
            text(canvas, 'Movement key released; idle loops continuously.', (28, 64), SMALL, DIM)
            canvas.blit(pygame.transform.scale(surface, (960, 540)), (0, 116))
            x, y = round(current['hero_x']), round(current['hero_y'])
            crop = surface.subsurface(pygame.Rect(x + 65, y + 62, 110, 126))
            canvas.blit(pygame.transform.scale(crop, (220, 252)), (1008, 231))
            text(canvas, '2x CLOSE-UP', (1008, 194), SMALL, GREEN)
            text(canvas, 'Terrace stage / real input and animation state machine',
                 (28, 680), SMALL, DIM)
            self.preview.write(canvas)
        # One movement frame sets each direction; release for the rest of its
        # four-second segment. Two complete idle loops must run after release.
        if self.frames == 960:
            raise ProbeComplete
        self.keys.held = ({KEYS[ORDER[self.frames // 240]]}
                          if self.frames % 240 == 0 else set())


def run(record=None, before=None):
    report = {'status': 'passed', 'directions': measure(ASSASSIN_ANIM_ROWS['idle'])}
    for direction, metrics in report['directions'].items():
        assert metrics['vertical_travel_px'] == 0, (direction, metrics)
        # Pixel shading can change a sole's width by one native pixel. The
        # planted side silhouettes should have no lateral movement at all.
        limit = 0 if direction in ('left', 'right') else 2
        assert metrics['horizontal_center_range_px'] <= limit, (direction, metrics)
    cases = 0
    for direction, row in zip(DIRECTIONS, _a_idle_rows):
        assert len({hashlib.sha256(pygame.image.tobytes(f, 'RGBA')).hexdigest()
                    for f in row}) == 6, 'Breathing animation was frozen'
        for rate in (30, 60, 144):
            player = Animator({'idle': row})
            visited = set()
            for _ in range(6 * rate):
                player.play('idle', frames=row, fps=8)
                player.update(1000 / rate)
                visited.add(player.frame_idx)
                assert sole_position(player.get_frame())[1] == report['directions'][direction]['sole_positions'][0][1]
            assert visited == set(range(12)), (direction, rate, visited)
            cases += 1
    report['playback_cases'] = cases
    preview = Preview(record) if record else None
    try:
        if before:
            before_rows = load_sheet_all_rows(str(before), 6, 4, (240, 240), True)
            report['before'] = measure(before_rows)
            assert report['before']['up']['vertical_travel_px'] > 0, 'Regression baseline did not reproduce'
            assert report['before']['left']['vertical_travel_px'] > 0, 'Regression baseline did not reproduce'
            if preview:
                comparison(preview, before_rows)
        # Only the enemy fixture is removed; movement, playback and rendering
        # are the unmodified production stage loop used in the supplied video.
        with patch.object(gameplay, 'spawn_enemies', return_value=[]), IdleHarness(preview) as harness:
            try:
                gameplay.stage_screen('Assassin', 'Jinwoo', 2, new_run_state())
            except ProbeComplete:
                pass
            assert harness.frames == 960
            assert harness.walk_seen == set(ORDER)
            for direction, samples in harness.samples.items():
                assert len(samples) == 239
                assert len({tuple(s['position']) for s in samples}) == 1, (direction, 'World drift')
                assert len({s['sole_world'][1] for s in samples}) == 1, (direction, 'Visible foot glide')
                assert harness.seen[direction] == set(range(12)), (direction, 'Idle stalled')
        report['stage_probe'] = {'seconds': 16, 'stationary_samples': 956,
                                 'directions': list(ORDER), 'world_position_drift_px': 0,
                                 'vertical_sole_drift_px': 0,
                                 'conditions': 'SDL dummy; terrace stage with no enemies; one movement frame per direction then released input'}
    finally:
        if preview:
            preview.close()
            report['preview_frames'] = preview.frames
    (ROOT / 'tests/jinwoo_idle_qa.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--record', type=Path)
    parser.add_argument('--before', type=Path, help='Previous packed idle.png for an optional comparison')
    args = parser.parse_args()
    run(args.record, args.before)
