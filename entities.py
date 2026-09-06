"""Projectiles and role-based enemy combat AI."""
import math
import random
from bisect import bisect_right

import pygame

from settings import WIDTH, HEIGHT, GOLD_DIM, CREAM
from game_data import (
    ENEMY_TYPES, ENEMY_ANIM_SETS, ENEMY_CANVAS_SIZE,
    ARROW_IMG, IGRIS_CRESCENT_FRAMES, IGRIS_SHOCKWAVE_FRAMES,
)
from igris_data import IGRIS_DURATIONS, IGRIS_FRAME_ENDS, IGRIS_LOOP_STATES, IGRIS_PIVOT
from igris_vfx import IgrisEffects


COMMANDER_STATES = (
    "attack", "dash", "overhead_slash", "ground_slam",
    "ranged_thrust", "run_attack", "dash_attack",
)

COMMANDER_ACTIONS = {
    "light_combo": dict(
        state="attack", active_frames=(3, 6), hit_frames=(3, 5),
        attack_range=235, damage=0.54, cooldown=460, heavy=False, dash_speed=0,
    ),
    "shadow_dash": dict(
        state="dash", active_frames=(2, 6), hit_frames=(), move_frames=(2, 6),
        attack_range=230, damage=0.0,
        cooldown=320, heavy=False, dash_speed=15.2,
    ),
    "overhead_slash": dict(
        state="overhead_slash", active_frames=(3, 6), hit_frames=(4,),
        attack_range=255, damage=1.30,
        cooldown=620, heavy=True, dash_speed=0,
    ),
    "ground_slam": dict(
        state="ground_slam", active_frames=(3, 6), hit_frames=(4,),
        attack_range=235, damage=1.05,
        projectile_frames=((4, "igris_shockwave", 0.78),),
        cooldown=720, heavy=True, dash_speed=0,
    ),
    "ranged_thrust": dict(
        state="ranged_thrust", active_frames=(3, 6), hit_frames=(4,),
        attack_range=220, damage=0.58,
        projectile_frames=((4, "igris_crescent", 0.84),),
        cooldown=660, heavy=False, dash_speed=0,
    ),
    "run_attack": dict(
        state="run_attack", active_frames=(3, 6), hit_frames=(4,),
        move_frames=(0, 4), attack_range=235, damage=0.95,
        cooldown=520, heavy=False, dash_speed=5.4,
    ),
    "dash_attack": dict(
        state="dash_attack", active_frames=(3, 6), hit_frames=(4,),
        move_frames=(2, 5), attack_range=235, damage=1.10,
        cooldown=580, heavy=True, dash_speed=15.2,
    ),
}

# Derive every boundary from the same frame durations used to draw the sprite.
# Frame numbers are zero-based; end frames are exclusive.
for _action in COMMANDER_ACTIONS.values():
    _durations = IGRIS_DURATIONS[_action["state"]]
    _starts = (0, *IGRIS_FRAME_ENDS[_action["state"]])
    _start, _end = _action["active_frames"]
    _action["windup"] = _starts[_start]
    _action["active"] = _starts[_end] - _starts[_start]
    _action["recovery"] = sum(_durations) - _starts[_end]
    _action["hit_times"] = tuple(_starts[i] for i in _action["hit_frames"])
    _action["hits"] = tuple((ms - _starts[_start]) / _action["active"]
                            for ms in _action["hit_times"])
    _action["projectile_times"] = tuple(
        (_starts[i], kind, damage) for i, kind, damage
        in _action.get("projectile_frames", ()))
    _action["move_window"] = tuple(_starts[i] for i in _action.get("move_frames", (0, 0)))


class Projectile:
    SPEED = 9
    MAX_LIFETIME = 3000

    def __init__(self, x, y, target_x, target_y, dmg, kind="arrow",
                 source=None, heavy=False):
        self.pos = [float(x), float(y)]
        dx, dy = target_x - x, target_y - y
        dist = max(1.0, math.hypot(dx, dy))
        if kind == "magic_orb":
            speed = 6.5
        elif kind == "igris_shockwave":
            speed = 7.8
        elif kind == "igris_crescent":
            speed = 12.5
        else:
            speed = self.SPEED
        self.vel = [speed * dx / dist, speed * dy / dist]
        self.dmg = dmg
        self.kind = kind
        self.source = source
        self.heavy = heavy
        self.hit_radius = {
            "magic_orb": 42,
            "igris_shockwave": 52,
            "igris_crescent": 76,
        }.get(kind, 34)
        self.max_lifetime = {
            "igris_shockwave": 1350,
            "igris_crescent": 1700,
        }.get(kind, self.MAX_LIFETIME)
        self.alive = True
        self.age = 0
        self.trail = []
        self.frames = []
        if kind == "magic_orb":
            self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(self.image, (13, 25, 58, 150), (16, 16), 15)
            pygame.draw.circle(self.image, (20, 92, 192, 230), (16, 16), 11)
            pygame.draw.circle(self.image, (48, 190, 255, 255), (16, 16), 7)
            pygame.draw.circle(self.image, (228, 252, 255, 255), (13, 12), 3)
        elif kind in ("igris_shockwave", "igris_crescent"):
            angle = -math.degrees(math.atan2(dy, dx))
            source_frames = (
                IGRIS_CRESCENT_FRAMES if kind == "igris_crescent"
                else IGRIS_SHOCKWAVE_FRAMES
            )
            self.frames = [
                pygame.transform.rotate(frame, angle)
                for frame in source_frames
            ]
            if kind == "igris_shockwave":
                # Ground effects stay flat in the arena's perspective even
                # when traveling vertically; rotation must not make a wall.
                depth_scale = 1.0 - .5 * abs(math.sin(math.radians(angle)))
                self.frames = [pygame.transform.scale(frame,
                    (frame.get_width(), max(1, round(frame.get_height()*depth_scale))))
                    for frame in self.frames]
            self.image = self.frames[0]
        else:
            angle = -math.degrees(math.atan2(dy, dx))
            self.image = pygame.transform.rotate(ARROW_IMG, angle)

    def update(self, dt):
        step = dt / 16.0
        self.pos[0] += self.vel[0] * step
        self.pos[1] += self.vel[1] * step
        self.age += dt
        if self.frames:
            frame_index = int(self.age * 12 / 1000) % len(self.frames)
            self.image = self.frames[frame_index]
        if self.kind in ("magic_orb", "igris_shockwave", "igris_crescent"):
            self.trail.append((self.pos[0], self.pos[1], self.age))
            trail_length = {
                "magic_orb": 7,
                "igris_shockwave": 3,
                "igris_crescent": 3,
            }[self.kind]
            self.trail = self.trail[-trail_length:]
        if self.age > self.max_lifetime:
            self.alive = False
        if not (-100 <= self.pos[0] <= WIDTH + 100 and
                -100 <= self.pos[1] <= HEIGHT + 100):
            self.alive = False

    @property
    def behind_source(self):
        return (self.kind == "igris_shockwave" and self.source is not None
                and self.pos[1] < self.source.feet()[1])

    def draw(self, screen, ox, oy):
        if self.kind == "magic_orb":
            for i, (tx, ty, _) in enumerate(self.trail):
                radius = max(2, int(5 * (i + 1) / max(1, len(self.trail))))
                alpha = int(18 + 75 * (i + 1) / max(1, len(self.trail)))
                glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (40, 145, 255, alpha),
                                   (radius * 2, radius * 2), radius)
                screen.blit(glow, (int(tx + ox - radius * 2),
                                   int(ty + oy - radius * 2)))
        elif self.kind in ("igris_shockwave", "igris_crescent"):
            for index, (tx, ty, _) in enumerate(self.trail[:-1]):
                echo = self.image.copy()
                echo.set_alpha(24 + index * 20)
                rect = echo.get_rect(center=(tx + ox, ty + oy))
                screen.blit(echo, rect)
        rect = self.image.get_rect(center=(self.pos[0] + ox, self.pos[1] + oy))
        screen.blit(self.image, rect)


class Enemy:
    FPS = 8
    HURT_DURATION = 320
    KNOCK_DURATION = 220
    FLASH_DURATION = 90
    ARENA_TOP = HEIGHT - 720

    def __init__(self, etype, x, y):
        self.etype = etype
        cfg = ENEMY_TYPES[etype]
        self.cfg = cfg
        self.name = cfg.get("name", etype.replace("_", " ").title())
        self.role = cfg.get("role", "fighter")
        self.igris_effects = IgrisEffects() if self.role == "commander" else None
        self.pos = [float(x), float(y)]

        self.display = ENEMY_CANVAS_SIZE[etype]
        self.anchor_height = cfg.get("anchor_height", self.display[1])
        self.render_offset_y = self.anchor_height - self.display[1]
        self.facing_left = True
        self.move_direction = "left"
        self.attack_direction = "left"

        self.hp = cfg["hp"]
        self.max_hp = cfg["hp"]
        self.dmg_range = cfg["dmg"]
        self.base_speed = cfg["speed"]
        self.speed = self.base_speed
        self.ranged = cfg.get("ranged", False)
        self.atk_range = cfg.get("atk_range", 116)
        self.preferred_range = cfg.get("preferred_range", self.atk_range * 0.72)
        self.min_range = cfg.get("min_range", 0)
        self.attack_cooldown = cfg.get("attack_cooldown", 1000)
        self.windup_ms = cfg.get("windup", 440)
        self.recovery_ms = cfg.get("recovery", 460)
        self.poise_max = cfg.get("poise", 45)
        self.poise = float(self.poise_max)
        self.poise_delay = 0

        self.state = "idle"          # sprite animation state
        self.combat_state = "approach"  # decision state
        self.frame_idx = 0.0
        self.anim_elapsed_ms = 0.0
        self.sprite_direction = "left"
        self.enemy_detected = False
        self.guard_timer = 0.0
        self.boss_playback_rate = 1.0
        self._commander_clock_advanced = False
        self._commander_locomotion_ms = None
        self.attack_cd = random.randint(180, 650)
        self.phase_timer = 0.0
        self.current_windup = self.windup_ms
        self.current_recovery = self.recovery_ms
        self.current_attack_range = self.atk_range
        self.attack_target = self.center()
        self.attack_direction_vec = (1.0, 0.0)
        self.attack_count = 0
        self.heavy_attack = False
        self.boss_action = "light_combo"
        self.boss_action_elapsed = 0.0
        self.boss_hit_index = -1
        self.boss_hits_resolved = set()
        self.boss_projectiles_resolved = set()
        self.hurt_timer = 0
        self.dead = False
        self.dead_done = False
        self.is_boss = False
        self.boss_phase = 1
        self.phase_flash = 0

        self.approach_angle = random.uniform(0, math.tau)
        self.strafe_dir = random.choice((-1, 1))
        self.strafe_timer = random.randint(700, 1500)
        self.knock_vel = [0.0, 0.0]
        self.knock_timer = 0
        self.flash_timer = 0

    @property
    def is_committed(self):
        return self.combat_state in ("windup", "active", "recover")

    @property
    def warning_progress(self):
        if self.combat_state != "windup" or self.current_windup <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - self.phase_timer / self.current_windup))

    def set_stats(self, hp, dmg_range):
        self.hp = hp
        self.max_hp = hp
        self.dmg_range = dmg_range

    def _frames(self):
        if self.role == "commander":
            return ENEMY_ANIM_SETS[self.etype][self.sprite_direction][self.state]
        vertical_direction = None
        if self.state == "walk":
            vertical_direction = self.move_direction
        elif self.state in COMMANDER_STATES:
            vertical_direction = self.attack_direction
        if vertical_direction in ("up", "down"):
            vertical = ENEMY_ANIM_SETS[self.etype].get(vertical_direction)
            if vertical and self.state in vertical:
                return vertical[self.state]
        side = self.attack_direction if (
            self.state in COMMANDER_STATES
            and self.attack_direction in ("left", "right")
        ) else ("left" if self.facing_left else "right")
        anims = ENEMY_ANIM_SETS[self.etype][side]
        return anims.get(self.state, anims["idle"])

    def _set_anim(self, state, reset=False):
        if self.role == "commander" and self.dead and state != "dead":
            return
        if self.state != state or reset:
            gait_phase = None
            if (self.role == "commander" and not reset
                    and self.state in ("walk", "run") and state in ("walk", "run")):
                gait_phase = self.anim_elapsed_ms / IGRIS_FRAME_ENDS[self.state][-1]
            self.state = state
            self.frame_idx = 0.0
            self.anim_elapsed_ms = (gait_phase * IGRIS_FRAME_ENDS[state][-1]
                                    if gait_phase is not None else 0.0)
        if self.role == "commander" and state not in ("hurt", "dead"):
            self.sprite_direction = (self.attack_direction if state in COMMANDER_STATES
                                     else self.move_direction)

    def center(self):
        return (self.pos[0] + self.display[0] / 2,
                self.pos[1] + self.anchor_height / 2)

    def feet(self):
        return (self.pos[0] + self.display[0] / 2,
                self.pos[1] + self.anchor_height * 0.82)

    def apply_knockback(self, dirx, diry, force):
        if self.is_boss:
            force *= 0.12
        self.knock_vel = [dirx * force, diry * force]
        self.knock_timer = self.KNOCK_DURATION

    def take_damage(self, dmg, stagger=24):
        """Return (actual_damage, killed_now)."""
        if self.dead:
            return 0, False
        actual = min(self.hp, max(0, int(dmg)))
        self.hp -= actual
        if self.role == "commander" and actual:
            self.enemy_detected = True
        self.flash_timer = self.FLASH_DURATION
        self.poise -= stagger
        self.poise_delay = 1300
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.combat_state = "dead"
            self._set_anim("dead", reset=True)
            if self.igris_effects:
                self.igris_effects.clear()
            return actual, True
        if self.poise <= 0:
            self.poise = float(self.poise_max)
            self.combat_state = "hurt"
            self.hurt_timer = self.HURT_DURATION + (90 if self.role == "tank" else 0)
            if self.role == "commander":
                self.hurt_timer = sum(IGRIS_DURATIONS["hurt"])
            self._set_anim("hurt", reset=True)
            if self.igris_effects:
                self.igris_effects.clear()
        return actual, False

    def _face_vector(self, dx, dy, attack=False):
        if abs(dx) < 0.001 and abs(dy) < 0.001:
            return
        direction = ("left" if dx < 0 else "right") if abs(dx) >= abs(dy) \
            else ("up" if dy < 0 else "down")
        if self.role == "commander" and not attack and self.state in ("walk", "run"):
            # Keep a small angular dead band around diagonals. Small steering
            # changes must not flicker between a profile and a front/back row.
            if self.move_direction in ("left", "right") and abs(dy) < abs(dx) * 1.20:
                direction = "left" if dx < 0 else "right"
            elif self.move_direction in ("up", "down") and abs(dx) < abs(dy) * 1.20:
                direction = "up" if dy < 0 else "down"
        if attack:
            self.attack_direction = direction
        else:
            self.move_direction = direction
        if direction in ("left", "right"):
            self.facing_left = direction == "left"

    def _move(self, vx, vy, dt, speed_mult=1.0):
        before = tuple(self.pos)
        mag = math.hypot(vx, vy)
        if mag <= 0.001:
            if self.role == "commander" and self.state in ("walk", "run"):
                self._commander_locomotion_ms = 0.0
            return
        vx, vy = vx / mag, vy / mag
        self._face_vector(vx, vy, attack=False)
        step = self.speed * speed_mult * dt / 16.0
        self.pos[0] += vx * step
        self.pos[1] += vy * step
        self._clamp_position()
        if self.role == "commander" and self.state in ("walk", "run"):
            reference_speed = self.base_speed * (1.65 if self.state == "run" else 1.0)
            self._commander_locomotion_ms = math.dist(before, self.pos) * 16.0 / max(.01, reference_speed)

    def _clamp_position(self):
        max_x = WIDTH - self.display[0]
        max_y = HEIGHT - self.anchor_height * 0.72
        min_y = self.ARENA_TOP - self.anchor_height * 0.35
        if self.role == "commander":
            min_y = self.cfg["floor_top"] - self.anchor_height * 0.82
            max_y = HEIGHT - self.anchor_height * 0.82
        self.pos[0] = max(8, min(max_x - 8, self.pos[0]))
        self.pos[1] = max(min_y, min(max_y, self.pos[1]))

    def _commander_sequence(self):
        if self.boss_phase == 1:
            return (
                "light_combo", "overhead_slash", "shadow_dash",
                "run_attack", "dash_attack",
            )
        if self.boss_phase == 2:
            return (
                "light_combo", "ground_slam", "shadow_dash",
                "overhead_slash", "run_attack", "dash_attack",
            )
        return (
            "ranged_thrust", "shadow_dash", "light_combo",
            "ground_slam", "overhead_slash", "run_attack", "dash_attack",
        )

    def _next_commander_action(self):
        sequence = self._commander_sequence()
        return sequence[self.attack_count % len(sequence)]

    def _begin_attack(self, hero_center, hero_velocity):
        hx, hy = hero_center
        is_commander = self.role == "commander"
        lead = self.cfg.get("projectile_lead", 0) if self.ranged else (4 if is_commander else 0)
        self.attack_target = (hx + hero_velocity[0] * lead,
                              hy + hero_velocity[1] * lead)
        ex, ey = self.center()
        dx, dy = self.attack_target[0] - ex, self.attack_target[1] - ey
        dist = max(1.0, math.hypot(dx, dy))
        self.attack_direction_vec = (dx / dist, dy / dist)
        self._face_vector(dx, dy, attack=True)
        self.attack_count += 1
        if is_commander:
            # Phase-specific rotation keeps the dash as a deliberate connector
            # between sword attacks instead of letting it replace the move set.
            sequence = self._commander_sequence()
            action = sequence[(self.attack_count - 1) % len(sequence)]
            action_cfg = COMMANDER_ACTIONS[action]
            phase_speed = 1.0 - 0.055 * (self.boss_phase - 1)
            self.boss_playback_rate = 1.0 / phase_speed
            self._commander_clock_advanced = True
            self.boss_action = action
            self.current_windup = action_cfg["windup"] * phase_speed
            self.current_recovery = action_cfg["recovery"] * phase_speed
            self.current_attack_range = action_cfg["attack_range"]
            self.heavy_attack = action_cfg["heavy"]
            self.boss_action_elapsed = 0.0
            self.boss_hit_index = -1
            self.boss_hits_resolved.clear()
            self.boss_projectiles_resolved.clear()
            self.phase_timer = self.current_windup
            self.combat_state = "windup"
            self._set_anim(action_cfg["state"], reset=True)
            return
        self.heavy_attack = self.is_boss and (
            self.attack_count % 3 == 0 or self.boss_phase == 3
        )
        windup_mult = 1.38 if self.heavy_attack else 1.0
        self.current_windup = self.windup_ms * windup_mult
        self.current_recovery = self.recovery_ms * (1.18 if self.heavy_attack else 1.0)
        self.current_attack_range = self.atk_range * (1.42 if self.heavy_attack else 1.0)
        self.phase_timer = self.current_windup
        self.combat_state = "windup"
        self._set_anim("attack", reset=True)

    def _resolve_attack(self, hero_center, on_hit_hero, spawn_projectile):
        if self.ranged:
            if spawn_projectile is not None:
                spawn_projectile(self, self.attack_target)
            return
        ex, ey = self.center()
        hx, hy = hero_center
        dx, dy = hx - ex, hy - ey
        dist = math.hypot(dx, dy)
        if dist > self.current_attack_range + 16:
            return
        action_cfg = COMMANDER_ACTIONS.get(self.boss_action, {}) \
            if self.role == "commander" else {}
        if dist > 1 and not action_cfg.get("full_circle", False):
            dot = ((dx / dist) * self.attack_direction_vec[0] +
                   (dy / dist) * self.attack_direction_vec[1])
            arc_limit = -0.35 if self.role in ("tank", "bruiser") else -0.05
            if dot < arc_limit:
                return
        dmg = random.randint(*self.dmg_range)
        if self.role == "commander":
            dmg = max(1, int(dmg * action_cfg.get("damage", 1.0)))
        elif self.heavy_attack:
            dmg = int(dmg * 1.45)
        final_hit = self.boss_hit_index == len(action_cfg.get("hits", ())) - 1
        landed = on_hit_hero(
            dmg,
            source=self,
            heavy=self.heavy_attack and final_hit,
        )
        if self.igris_effects and landed is not False:
            self.igris_effects.contact(self, position=hero_center, hit=True)

    def _boss_dash_step(self, dt, speed_mult=1.0):
        action_cfg = COMMANDER_ACTIONS.get(self.boss_action, {})
        speed = action_cfg.get("dash_speed", 0) * speed_mult
        if speed <= 0:
            return
        step = speed * dt / 16.0
        self.pos[0] += self.attack_direction_vec[0] * step
        self.pos[1] += self.attack_direction_vec[1] * step
        self._clamp_position()

    def _update_commander_action(self, dt, hero_center, on_hit_hero, spawn_projectile):
        cfg = COMMANDER_ACTIONS[self.boss_action]
        total = sum(IGRIS_DURATIONS[cfg["state"]])
        before = self.anim_elapsed_ms
        after = min(total, before + dt * self.boss_playback_rate)
        self._commander_clock_advanced = True
        move_start, move_end = cfg["move_window"]

        def travel(start, end):
            overlap = max(0.0, min(end, move_end) - max(start, move_start))
            if overlap:
                self._boss_dash_step(overlap / self.boss_playback_rate)

        events = [(ms, "hit", i) for i, ms in enumerate(cfg["hit_times"])
                  if i not in self.boss_hits_resolved and before < ms <= after]
        events += [(spec[0], "projectile", i)
                   for i, spec in enumerate(cfg["projectile_times"])
                   if i not in self.boss_projectiles_resolved and before < spec[0] <= after]
        cursor = before
        for moment, kind, index in sorted(events):
            # Resolve at the position and sword frame of the event, even if a
            # slow render tick crosses several animation/phase boundaries.
            travel(cursor, moment)
            cursor = moment
            self.anim_elapsed_ms = moment
            self._advance_animation(0)
            if kind == "hit":
                self.boss_hits_resolved.add(index)
                self.boss_hit_index = index
                self._resolve_attack(hero_center, on_hit_hero, spawn_projectile)
                if self.boss_action == "ground_slam":
                    self.igris_effects.contact(self, ground=True)
            else:
                self.boss_projectiles_resolved.add(index)
                _, projectile_kind, damage = cfg["projectile_times"][index]
                if spawn_projectile is not None:
                    spawn_projectile(self, self.attack_target,
                                     kind=projectile_kind, damage_mult=damage)
        travel(cursor, after)
        self.anim_elapsed_ms = after
        self.boss_action_elapsed = max(0.0, after - cfg["windup"])
        if after < cfg["windup"]:
            self.combat_state = "windup"
            boundary = cfg["windup"]
        elif after < cfg["windup"] + cfg["active"]:
            self.combat_state = "active"
            boundary = cfg["windup"] + cfg["active"]
        else:
            self.combat_state = "recover"
            boundary = total
        self.phase_timer = (boundary - after) / self.boss_playback_rate
        if after >= total:
            self.combat_state = "approach"
            self.attack_cd = cfg["cooldown"]
            self.guard_timer = 180
            self.move_direction = self.attack_direction
            self._set_anim("idle_alert", reset=True)

    def _update_committed(self, dt, hero_center, on_hit_hero, spawn_projectile,
                          other_positions=None, hero_velocity=(0, 0)):
        if self.role == "commander":
            self._update_commander_action(dt, hero_center, on_hit_hero, spawn_projectile)
            return
        self.phase_timer -= dt
        if self.combat_state == "windup":
            if self.role == "hunter" and self.warning_progress > 0.48:
                self._move(*self.attack_direction_vec, dt,
                           speed_mult=self.cfg.get("lunge_speed", 4.5) / max(0.1, self.speed))
            if self.phase_timer <= 0:
                self.combat_state = "active"
                self.phase_timer = 125 if not self.heavy_attack else 175
                self._resolve_attack(hero_center, on_hit_hero, spawn_projectile)
        elif self.combat_state == "active":
            if self.phase_timer <= 0:
                self.combat_state = "recover"
                self.phase_timer = self.current_recovery
                if self.cfg.get("mobile_recovery"):
                    # The Craftpix strike ends on its slash pose. Resume
                    # animated footwork immediately after the active window;
                    # recovery still blocks another attack for its full time.
                    self._update_melee(0, hero_center, False, other_positions,
                                       hero_velocity)
        elif self.combat_state == "recover":
            if self.cfg.get("mobile_recovery"):
                self._update_melee(dt, hero_center, False, other_positions,
                                   hero_velocity)
            if self.phase_timer <= 0:
                self.combat_state = "approach"
                self.attack_cd = self.attack_cooldown
                self.approach_angle += random.uniform(-0.8, 0.8)
                if not self.cfg.get("mobile_recovery"):
                    self._set_anim("idle", reset=True)

    def _separation(self, vx, vy, other_positions):
        ex, ey = self.center()
        if other_positions:
            for ox, oy in other_positions:
                dx, dy = ex - ox, ey - oy
                dist = math.hypot(dx, dy)
                if 0 < dist < 82:
                    push = (82 - dist) / 82
                    vx += dx / dist * push * 1.2
                    vy += dy / dist * push * 1.2
        return vx, vy

    def _update_melee(self, dt, hero_center, allow_attack, other_positions,
                      hero_velocity):
        ex, ey = self.center()
        hx, hy = hero_center
        dx, dy = hx - ex, hy - ey
        dist = max(1.0, math.hypot(dx, dy))
        if self.role == "commander":
            if not self.enemy_detected:
                self._set_anim("idle")
                return
            if self.guard_timer > 0:
                self.guard_timer = max(0, self.guard_timer - dt)
                self._set_anim("idle_alert")
                return
            next_action = self._next_commander_action()
            if next_action == "ranged_thrust":
                trigger_range = 420
            elif next_action == "shadow_dash":
                trigger_range = 310
            elif next_action in ("run_attack", "dash_attack"):
                trigger_range = 300
            else:
                trigger_range = self.cfg.get("engage_range", self.atk_range)
        else:
            trigger_range = self.atk_range
        if dist <= trigger_range and self.attack_cd <= 0 and allow_attack:
            self._begin_attack(hero_center, hero_velocity)
            return

        if dist > self.atk_range * 0.82:
            stand = self.atk_range * (0.52 if self.role == "hunter" else 0.66)
            tx = hx + math.cos(self.approach_angle) * stand
            ty = hy + math.sin(self.approach_angle) * stand * 0.65
            vx, vy = tx - ex, ty - ey
        else:
            # Wait for an attack slot while orbiting instead of piling into the
            # hero. This makes groups look intentional and keeps attacks readable.
            vx = -dy / dist * self.strafe_dir
            vy = dx / dist * self.strafe_dir * 0.55
        vx, vy = self._separation(vx, vy, other_positions)
        running = self.role == "commander" and dist > (320 if self.state == "run" else 410)
        self._set_anim("run" if running else "walk")
        self._move(vx, vy, dt, speed_mult=1.65 if running else
                   1.08 if self.role == "aggressor" else 1.0)

    def _update_ranged(self, dt, hero_center, allow_attack, other_positions,
                       hero_velocity):
        ex, ey = self.center()
        hx, hy = hero_center
        dx, dy = hx - ex, hy - ey
        dist = max(1.0, math.hypot(dx, dy))
        self.strafe_timer -= dt
        if self.strafe_timer <= 0:
            self.strafe_dir *= -1
            self.strafe_timer = random.randint(850, 1600)

        if dist < self.min_range:
            vx, vy = -dx / dist, -dy / dist
            vx += (-dy / dist) * self.strafe_dir * 0.45
            vy += (dx / dist) * self.strafe_dir * 0.32
        elif dist > self.atk_range:
            vx, vy = dx / dist, dy / dist
        elif self.attack_cd <= 0 and allow_attack:
            self._begin_attack(hero_center, hero_velocity)
            return
        else:
            radial = (dist - self.preferred_range) / max(1, self.preferred_range)
            vx = dx / dist * radial + (-dy / dist) * self.strafe_dir * 0.72
            vy = dy / dist * radial + (dx / dist) * self.strafe_dir * 0.46
        vx, vy = self._separation(vx, vy, other_positions)
        self._set_anim("walk")
        self._move(vx, vy, dt, speed_mult=0.82)

    def _update_boss_phase(self):
        if not self.is_boss or self.dead:
            return
        ratio = self.hp / max(1, self.max_hp)
        new_phase = 3 if ratio <= 0.34 else 2 if ratio <= 0.67 else 1
        if new_phase != self.boss_phase:
            self.boss_phase = new_phase
            self.phase_flash = 1100
            # A phase change must not cut off an authored strike or stagger.
            if self.role != "commander" or not (
                    self.is_committed or self.combat_state == "hurt"):
                self.combat_state = "approach"
                self.attack_cd = 360
                self._set_anim("idle_alert" if self.role == "commander" else "idle", reset=True)
        self.speed = self.base_speed * (1.0 + 0.16 * (self.boss_phase - 1))
        self.windup_ms = self.cfg.get("windup", 520) * (1.0 - 0.08 * (self.boss_phase - 1))
        self.attack_cooldown = self.cfg.get("attack_cooldown", 1050) * (
            1.0 - 0.13 * (self.boss_phase - 1)
        )

    def update(self, dt, hero_center, on_hit_hero, spawn_projectile=None,
               other_positions=None, allow_attack=True, hero_velocity=(0, 0)):
        self._commander_clock_advanced = False
        self.flash_timer = max(0, self.flash_timer - dt)
        self.phase_flash = max(0, self.phase_flash - dt)
        self._update_boss_phase()

        if self.knock_timer > 0 and not self.dead:
            self.pos[0] += self.knock_vel[0] * dt / 16.0
            self.pos[1] += self.knock_vel[1] * dt / 16.0
            self.knock_timer -= dt
            decay = max(0.0, 1 - dt / self.KNOCK_DURATION)
            self.knock_vel[0] *= decay
            self.knock_vel[1] *= decay
            if self.role == "commander":
                self._clamp_position()

        if self.dead:
            if self.role == "commander":
                self._advance_animation(dt)
                self.dead_done = self.anim_elapsed_ms >= IGRIS_FRAME_ENDS["dead"][-1]
                self.igris_effects.update(self, dt, None)
                return
            frames = self._frames()
            self.frame_idx += dt * self.FPS / 1000
            if self.frame_idx >= len(frames):
                self.frame_idx = len(frames) - 1
                self.dead_done = True
            return

        if self.combat_state == "hurt":
            self.hurt_timer -= dt
            if self.hurt_timer <= 0:
                self.combat_state = "approach"
                self._set_anim("idle", reset=True)
            self._advance_animation(dt)
            if self.igris_effects:
                self.igris_effects.update(self, dt, None)
            return

        self.attack_cd = max(0, self.attack_cd - dt)
        if self.poise_delay > 0:
            self.poise_delay -= dt
        else:
            self.poise = min(self.poise_max, self.poise + dt * self.poise_max / 2400)

        ex, ey = self.center()
        hx, hy = hero_center
        if self.role == "commander":
            radius = self.cfg["forget_range"] if self.enemy_detected else self.cfg["detection_range"]
            self.enemy_detected = math.hypot(hx - ex, hy - ey) <= radius
        # Lock the selected attack direction for the full authored move.
        # Switching directional sheets mid-combo looks like a skipped frame.
        if (not self.is_committed and (self.role != "commander" or self.enemy_detected)
                and not (self.role == "commander" and self.state in ("walk", "run"))):
            self._face_vector(hx - ex, hy - ey, attack=False)

        if self.is_committed:
            self._update_committed(dt, hero_center, on_hit_hero, spawn_projectile,
                                   other_positions, hero_velocity)
        elif self.ranged:
            self._update_ranged(dt, hero_center, allow_attack,
                                other_positions, hero_velocity)
        else:
            self._update_melee(dt, hero_center, allow_attack,
                               other_positions, hero_velocity)
        self._advance_animation(dt)
        if self.igris_effects:
            self.igris_effects.update(self, dt, COMMANDER_ACTIONS.get(self.boss_action))

    def _advance_animation(self, dt):
        if self.role == "commander":
            if not self.is_committed and not self._commander_clock_advanced:
                motion_ms = getattr(self, "_commander_locomotion_ms", None)
                self.anim_elapsed_ms += (motion_ms if motion_ms is not None
                                        and self.state in ("walk", "run") else dt)
            self._commander_locomotion_ms = None
            ends = IGRIS_FRAME_ENDS[self.state]
            if self.state in IGRIS_LOOP_STATES:
                self.anim_elapsed_ms %= ends[-1]
            else:
                self.anim_elapsed_ms = min(self.anim_elapsed_ms, ends[-1])
            self.frame_idx = min(bisect_right(ends, self.anim_elapsed_ms), len(ends) - 1)
            if self.state not in ("hurt", "dead"):
                self.sprite_direction = (self.attack_direction if self.is_committed
                                         else self.move_direction)
            return
        frames = self._frames()
        hit_frame = self.cfg.get("attack_hit_frame")
        if hit_frame is not None and self.state == "attack" and self.is_committed:
            # Keep anticipation frames on the windup clock and show the
            # actual slash when damage resolves. A fixed 8 FPS previously
            # exhausted this five-frame strip long before recovery finished.
            if self.combat_state == "windup":
                progress = 1.0 - self.phase_timer / max(1, self.current_windup)
                self.frame_idx = min(hit_frame - 1, max(0, int(progress * hit_frame)))
            else:
                self.frame_idx = min(hit_frame, len(frames) - 1)
            return
        self.frame_idx += dt * self._state_fps() / 1000
        if self.frame_idx >= len(frames):
            if ((self.is_committed and self.state not in ("idle", "walk", "run"))
                    or self.combat_state in ("hurt", "dead")):
                self.frame_idx = len(frames) - 1
            else:
                self.frame_idx = 0

    def _state_fps(self):
        if (self.role == "commander" and self.is_committed and
                self.state in COMMANDER_STATES):
            active_ms = COMMANDER_ACTIONS[self.boss_action]["active"]
            action_ms = max(
                1.0, self.current_windup + active_ms + self.current_recovery)
            return len(self._frames()) * 1000.0 / action_ms
        if self.role == "commander" and self.state == "walk":
            return 10
        return self.FPS

    def _draw_telegraph(self, screen, ox, oy):
        if self.combat_state != "windup":
            return
        # Igris's authored anticipation frames are his telegraph. Avoid smooth
        # runtime circles/lines that clash with the coarse pixel-art effects.
        if self.role == "commander":
            return
        progress = self.warning_progress
        pulse = 0.72 + math.sin(progress * math.pi * 7) * 0.16
        alpha = int((70 + 150 * progress) * pulse)
        ex, ey = self.feet()
        ex += ox
        ey += oy
        if self.role == "commander":
            color = (244, 26, 48) if not self.heavy_attack else (255, 70, 66)
        else:
            color = (255, 64, 72) if not self.heavy_attack else (255, 174, 72)
        if (self.role == "commander" and
                COMMANDER_ACTIONS[self.boss_action]["dash_speed"] > 0):
            tx = self.attack_target[0] + ox
            ty = self.attack_target[1] + oy
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            special_color = (226, 18, 42)
            width = 4 if self.boss_action == "shadow_dash" else 3
            pygame.draw.line(overlay, (*special_color, max(35, alpha // 2)),
                             (int(ex), int(ey)), (int(tx), int(ty)), width)
            radius = 26
            pygame.draw.circle(overlay, (*special_color, alpha),
                               (int(tx), int(ty)), radius, 3)
            pygame.draw.circle(overlay, (255, 78, 76, max(20, alpha // 5)),
                               (int(tx), int(ty)), max(3, radius - 5))
            screen.blit(overlay, (0, 0))
            return
        commander_projectile = (
            self.role == "commander"
            and COMMANDER_ACTIONS[self.boss_action].get("projectiles")
        )
        if self.ranged or commander_projectile:
            tx, ty = self.attack_target[0] + ox, self.attack_target[1] + oy
            radius = int(24 + 12 * progress)
            left = int(min(ex, tx) - radius - 8)
            top = int(min(ey, ty) - radius - 8)
            right = int(max(ex, tx) + radius + 8)
            bottom = int(max(ey, ty) + radius + 8)
            overlay = pygame.Surface((max(1, right - left), max(1, bottom - top)),
                                     pygame.SRCALPHA)
            pygame.draw.line(overlay, (*color, max(30, alpha // 2)),
                             (int(ex - left), int(ey - top)),
                             (int(tx - left), int(ty - top)), 2)
            pygame.draw.circle(overlay, (*color, alpha),
                               (int(tx - left), int(ty - top)), radius, 3)
            pygame.draw.circle(overlay, (*color, max(18, alpha // 5)),
                               (int(tx - left), int(ty - top)), max(3, radius - 4))
            screen.blit(overlay, (left, top))
        else:
            radius = int(self.current_attack_range)
            surf_w = radius * 2 + 16
            surf_h = int(radius * 0.72) + 16
            overlay = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
            rect = pygame.Rect(8, 8, radius * 2, int(radius * 0.72))
            pygame.draw.ellipse(overlay, (*color, max(18, alpha // 5)), rect)
            pygame.draw.arc(overlay, (*color, alpha), rect, 0, math.tau,
                            3 if progress < 0.8 else 5)
            screen.blit(overlay, (int(ex - radius - 8),
                                  int(ey - radius * 0.36 - 8)))

    def draw(self, screen, ox, oy):
        self._draw_telegraph(screen, ox, oy)
        if self.igris_effects:
            self.igris_effects.draw_back(screen, ox, oy)
        frames = self._frames()
        idx = min(int(self.frame_idx), len(frames) - 1)
        frame = frames[idx]
        x = self.pos[0] + ox
        logical_y = self.pos[1] + oy
        y = logical_y + self.render_offset_y
        if self.role == "commander":
            feet_x, feet_y = self.feet()
            x = round(feet_x + ox) - IGRIS_PIVOT[0]
            y = round(feet_y + oy) - IGRIS_PIVOT[1]
        screen.blit(frame, (x, y))

        if self.flash_timer > 0 or self.phase_flash > 0:
            mask = pygame.mask.from_surface(frame)
            if self.phase_flash > 0:
                phase_col = (190, 30, 64, int(150 * self.phase_flash / 1100))
            else:
                phase_col = (255, 255, 255,
                             int(220 * self.flash_timer / self.FLASH_DURATION))
            flash_img = mask.to_surface(setcolor=phase_col,
                                        unsetcolor=(0, 0, 0, 0))
            screen.blit(flash_img, (x, y))

        if self.igris_effects:
            self.igris_effects.draw_front(screen, ox, oy)

        if not self.dead and not self.is_boss and (
            self.hp < self.max_hp or self.combat_state == "windup"
        ):
            bar_w = 72
            bar_x = x + self.display[0] / 2 - bar_w / 2
            bar_y = logical_y - 18
            pygame.draw.rect(screen, (8, 7, 9), (bar_x - 1, bar_y - 1, bar_w + 2, 9),
                             border_radius=3)
            fill_w = int(bar_w * self.hp / max(1, self.max_hp))
            if fill_w:
                pygame.draw.rect(screen, (190, 44, 52),
                                 (bar_x, bar_y, fill_w, 6), border_radius=2)
            pygame.draw.rect(screen, GOLD_DIM, (bar_x, bar_y, bar_w, 6), 1,
                             border_radius=2)
            if self.poise < self.poise_max:
                poise_w = int(bar_w * self.poise / max(1, self.poise_max))
                pygame.draw.rect(screen, (205, 172, 92),
                                 (bar_x, bar_y + 8, poise_w, 2))
