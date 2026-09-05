"""Exercise the remake in the actual game, including both special skills.

Scripted inputs, bonus health and reduced test-only player damage keep the
boss present long enough to show all attacks. Runtime balance is unchanged.
"""
import argparse
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_gameplay import Harness, ROOT, key_event
import pygame
import gameplay
import screens
from game_data import ASSASSIN_ANIM_ROWS, STAGES
from progression import new_run_state


class JinwooHarness(Harness):
    def __init__(self, mode='fight', record=None):
        super().__init__(mode, record)
        self.clips = set()
        self.hero_directions = set()

    def events(self):
        if not self.latest:
            return []
        if self.mode in ('name', 'pause', 'options', 'campaign'):
            return super().events()
        anim = self.latest['anim']
        self.hero_directions.add(self.latest['direction'])
        selected = anim.anims[anim.current]
        matched = False
        for name, rows in ASSASSIN_ANIM_ROWS.items():
            if any(selected is row for row in rows):
                self.clips.add(name)
                matched = True
        if not matched:
            self.clips.add(anim.current)
        if self.mode == 'loss':
            self.keys.held = set()
            if self.frames == 5:
                assert self.latest['hurt_hero'](100000)
            if self.frames == 180:
                assert self.latest['state']['result'] == 'lose'
                assert anim.current == 'death' and anim.done
                assert anim.frame_idx == 6
                self.capture(gameplay.screen, 'jinwoo/death_in_game.png')
                return [key_event(pygame.K_RETURN)]
            return []
        events = super().events()
        if 24 <= self.frames / 60 < 26:
            self.keys.held = set()
        elif 27 <= self.frames / 60 < 32:
            # Keep a movement key held through the moving combo. The generic
            # chase controller sometimes stops on its target during hit 2.
            square = (pygame.K_a, pygame.K_w, pygame.K_d, pygame.K_s)
            self.keys.held = {square[int((self.frames / 60 - 27) / 0.9) % 4]}
        # A running strike, both skills, a buffered dash strike, and the
        # existing harness's complete standing and moving LMB combo chain.
        keys = {420: pygame.K_q, 840: pygame.K_r, 900: pygame.K_e,
                1200: pygame.K_r}
        if self.frames in keys:
            events.append(key_event(keys[self.frames]))
        if self.frames in (210, 753):
            events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
        if self.frames in (480, 960, 1470, 1740):
            self.capture(gameplay.screen, f'jinwoo/gameplay_{self.frames}.png')
        return events


def run(record=None):
    random.seed(20260905)
    report = {'checks': []}
    with Harness('name'):
        assert screens.name_input_screen() == 'Jin'
    with Harness('pause'):
        assert screens.pause_menu() == 'Resume'
    with Harness('options'):
        screens.options_menu()
    for stage in range(len(STAGES)):
        with Harness('campaign') as harness:
            result = gameplay.stage_screen('Assassin', 'Jin', stage, new_run_state())
            assert result == ('finished' if stage == 3 else 'next')
            if stage == 3:
                assert harness.boss_spawned
    report['checks'].append('Real name entry, pause/options, all four campaign rooms, boss spawn, terminal boss death and exit progression')
    state = new_run_state()
    state.update(bonus_health=1000, bonus_stamina=200, damage_mult=.25)
    with JinwooHarness('fight', record) as harness:
        assert gameplay.stage_screen('Assassin', 'Jin', 3, state, boss_only=True) == 'finished'
        required = {'idle', 'walk', 'run', 'run_attack', 'dash', 'dash_attack',
                    'deaths_dance', 'sonic_stream', 'attack_1', 'attack_2', 'attack_3',
                    'walk_attack_1', 'walk_attack_2', 'walk_attack_3'}
        assert required <= harness.clips, sorted(harness.clips)
        assert harness.hero_directions == {'down', 'left', 'right', 'up'}
        report.update(loaded_clips_in_game=sorted(harness.clips),
                      hero_directions=sorted(harness.hero_directions),
                      boss_phases=sorted(harness.phases),
                      fight_seconds=round(harness.frames / 60, 2))
    with JinwooHarness('loss') as harness:
        assert gameplay.stage_screen('Assassin', 'Jin', 3, new_run_state(), boss_only=True) == 'retry'
        assert 'death' in harness.clips
    report['checks'] += [
        'Real movement, running attack, all three standing/moving combo clips, dash and buffered dash attack, Q Deaths Dance and E Sonic Stream',
        'Player defeat triggers the seven-frame collapse, holds its final pose, and supports Retry stage',
    ]
    report.update(status='passed', conditions='SDL dummy video/audio, scripted input and boss HP/stagger transitions; bonus fighter health/stamina and 25% test-only fighter damage for continuous coverage')
    (ROOT / 'tests/jinwoo_gameplay_qa.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    run(args.record)
