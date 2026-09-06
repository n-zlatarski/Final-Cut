"""Exercise real menus/stage_screen with scripted input and optional MP4 capture.

The recording is a playback test: scripted HP changes expose every boss phase.
No test hooks or invulnerability are installed in the shipped game loop.
"""
import argparse
from contextlib import ExitStack
import json
import math
import os
import random
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
import gameplay
import screens
import video
from game_data import STAGES
from progression import new_run_state

QA = ROOT/'tests/screenshots'
QA.mkdir(parents=True, exist_ok=True)


def key_event(key, text=''):
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=text)


class Keys:
    held = set()
    def __getitem__(self, key):
        return key in self.held


class Harness:
    def __init__(self, mode, record=None):
        self.mode = mode
        self.now = 10000.0
        self.frames = 0
        self.keys = Keys()
        self.latest = {}
        self.once = set()
        self.states = set()
        self.directions = set()
        self.phases = set()
        self.hero_states = set()
        self.writer = None
        self.death_started = None
        self.exit_time = None
        self.boss_spawned = False
        self.record = record
        self.recorded_frames = 0
        if record:
            self.writer = subprocess.Popen([
                'ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo',
                '-pixel_format', 'rgb24', '-video_size', '1920x1080',
                '-framerate', '30', '-i', '-', '-an', '-c:v', 'libx264',
                '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p',
                '-threads', '2', '-movflags', '+faststart', str(record)], stdin=subprocess.PIPE)

    def tick(self, *_):
        self.now += 1000 / 60
        return 1000 / 60

    def get_time(self):
        return 1000 / 60

    def capture(self, surface, name):
        pygame.image.save(surface, QA/name)

    def present(self, surface):
        self.frames += 1
        self.latest = sys._getframe(1).f_locals
        assert self.frames < 2700, (self.mode, 'timed out')
        if self.mode in ('name', 'pause', 'options'):
            if self.frames == 2:
                self.capture(surface, self.mode+'.png')
            return
        state, enemies = self.latest['state'], self.latest['enemies']
        if self.mode == 'campaign':
            if self.frames == 2:
                self.capture(surface, f"stage_{self.latest['stage_idx']+1}.png")
                for e in enemies:
                    e.take_damage(10000, stagger=1000)
            for e in enemies:
                if e.is_boss:
                    self.boss_spawned = True
                    if not e.dead:
                        e.take_damage(10000)
                        self.death_started = self.now
            if state['exit_unlocked']:
                assert all(e.dead_done for e in enemies)
                if self.death_started is not None:
                    assert self.now - self.death_started >= 2060
                self.latest['hero_pos'][0] = self.latest['STAGE_EXIT_X']
            return
        t = self.frames / 60
        e = next(e for e in enemies if e.is_boss)
        self.states.add(e.state)
        self.directions.add(e.sprite_direction)
        self.phases.add(e.boss_phase)
        self.hero_states.add(self.latest['anim'].current)
        self.keys.held = set()
        hx, hy = self.latest['hero_center']()
        ex, ey = e.center()
        if 2.5 <= t < 5.5:
            self.keys.held = {pygame.K_d, pygame.K_LSHIFT}
        elif t >= 5.5 and not e.dead:
            angle = math.pi + (t-5.5) * .42
            radius = 165 if t < 24 else 90
            target = (ex + math.cos(angle)*radius, ey + math.sin(angle)*radius*.75)
            dx, dy = target[0]-hx, target[1]-hy
            if abs(dx) > 9:
                self.keys.held.add(pygame.K_d if dx > 0 else pygame.K_a)
            if abs(dy) > 9:
                self.keys.held.add(pygame.K_s if dy > 0 else pygame.K_w)
        for threshold, ratio in ((9, .62), (16, .30)):
            if t >= threshold and threshold not in self.once:
                e.take_damage(max(0, e.hp-int(e.max_hp*ratio)), stagger=0)
                self.once.add(threshold)
        if t >= 23 and 'hurt' not in self.once:
            e.take_damage(1, stagger=1000)
            self.once.add('hurt')
        if t >= 32 and not e.dead:
            e.take_damage(10000)
        if e.dead and self.death_started is None:
            self.death_started = self.now
        if state['exit_unlocked']:
            assert self.now-self.death_started >= 2060
            if self.exit_time is None:
                self.exit_time = t
            if t >= max(35, self.exit_time+1):
                self.latest['hero_pos'][0] = self.latest['STAGE_EXIT_X']
        for moment in (2, 7, 11, 18, 23.2, 33, 36):
            tag = f'shot_{moment}'
            if t >= moment and tag not in self.once:
                self.capture(surface, f'boss_{moment}.png')
                self.once.add(tag)
        if self.writer and self.frames % 2 == 0:
            self.writer.stdin.write(pygame.image.tobytes(surface, 'RGB'))
            self.recorded_frames += 1

    def events(self):
        if self.mode == 'name' and self.frames == 1:
            return [key_event(pygame.K_j, 'J'), key_event(pygame.K_i, 'i'), key_event(pygame.K_n, 'n')]
        if self.mode == 'name' and self.frames >= 2:
            return [key_event(pygame.K_RETURN)]
        if self.mode in ('pause', 'options') and self.frames >= 2:
            return [key_event(pygame.K_ESCAPE)]
        if self.mode == 'campaign' and self.latest.get('state', {}).get('result') == 'cleared':
            return [key_event(pygame.K_RETURN)]
        if self.mode == 'fight':
            t = self.frames/60
            if t >= 37 and self.latest.get('state', {}).get('result') == 'cleared':
                return [key_event(pygame.K_RETURN)]
            if 24 <= t < 32 and self.frames % 40 == 0:
                return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0))]
            if self.frames in (int(12.5*60), int(20.5*60), int(26.5*60)):
                return [key_event(pygame.K_SPACE)]
        return []

    def __enter__(self):
        self.stack = ExitStack()
        for obj, attr, replacement in (
            (pygame.time, 'get_ticks', lambda: int(self.now)),
            (pygame.key, 'get_pressed', lambda: self.keys),
            (pygame.event, 'get', self.events),
            (video, 'present', self.present),
            (screens, 'clock', self), (gameplay, 'clock', self),
        ):
            self.stack.enter_context(patch.object(obj, attr, replacement))
        return self

    def __exit__(self, *args):
        self.stack.close()
        if self.writer:
            self.writer.stdin.close()
            assert self.writer.wait(timeout=30) == 0
            probe=json.loads(subprocess.check_output([
                'ffprobe','-v','error','-select_streams','v:0',
                '-show_entries','stream=nb_frames','-of','json',str(self.record)]))
            assert int(probe['streams'][0]['nb_frames']) == self.recorded_frames > 0


def run(record=None):
    random.seed(20260905)
    report = {'checks': []}
    with Harness('name'):
        assert screens.name_input_screen() == 'Jin'
    with Harness('pause'):
        assert screens.pause_menu() == 'Resume'
    with Harness('options'):
        screens.options_menu()
    report['checks'].append('Name entry, pause/resume and options render and accept input')
    for index in range(len(STAGES)):
        with Harness('campaign') as h:
            result = gameplay.stage_screen('Assassin', 'Jin', index, new_run_state())
            assert result == ('finished' if index == 3 else 'next')
            if index == 3:
                assert h.boss_spawned
    report['checks'].append('All four stages load; wave deaths, throne boss spawn, full boss death, exit unlock and final result progress correctly')
    state = new_run_state()
    state['bonus_health'] = 1000
    with Harness('fight', record) as h:
        result = gameplay.stage_screen('Assassin', 'Jin', 3, state, boss_only=True)
        assert result == 'finished'
        assert {'idle', 'idle_alert', 'walk', 'run', 'attack', 'overhead_slash',
                'ground_slam', 'ranged_thrust', 'dash', 'dash_attack',
                'run_attack', 'hurt', 'dead'} <= h.states, h.states
        assert h.directions == {'left', 'right', 'up', 'down'}, h.directions
        assert h.phases == {1, 2, 3}
        assert {'idle', 'walk', 'run', 'dash', 'attack_1', 'attack_2', 'attack_3'} <= h.hero_states, h.hero_states
        report.update(boss_states=sorted(h.states), boss_directions=sorted(h.directions),
                      boss_phases=sorted(h.phases), hero_states=sorted(h.hero_states),
                      fight_seconds=round(h.frames/60, 2),
                      conditions='SDL dummy video/audio; scripted inputs, HP phase transitions and stagger; extra player health for uninterrupted coverage')
    report['checks'].append('Actual boss-only stage runs through all Igris states and phases, player movement/attacks/dodges, corpse hold and HUNT COMPLETE')
    report['status'] = 'passed'
    (ROOT/'tests/gameplay_qa.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    pygame.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    run(args.record)
