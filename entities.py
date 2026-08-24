"""Projectiles and role-based enemy combat AI."""
import math
import random

import pygame

from settings import WIDTH, HEIGHT, GOLD_DIM, CREAM
from sprite_loaders import vamp_dir_frames
from game_data import (
    ENEMY_TYPES, ENEMY_ANIM_SETS, ENEMY_CANVAS_SIZE,
    VAMPIRE_ANIMS, VAMPIRE_STATS, VAMPIRE_DISPLAY, ARROW_IMG,
)


class Projectile:
    SPEED = 9
    MAX_LIFETIME = 3000

    def __init__(self, x, y, target_x, target_y, dmg, kind="arrow"):
        self.pos = [float(x), float(y)]
        dx, dy = target_x - x, target_y - y
        dist = max(1.0, math.hypot(dx, dy))
        speed = 6.5 if kind == "magic_orb" else self.SPEED
        self.vel = [speed * dx / dist, speed * dy / dist]
        self.dmg = dmg
        self.kind = kind
        self.hit_radius = 42 if kind == "magic_orb" else 34
        self.alive = True
        self.age = 0
        self.trail = []
        if kind == "magic_orb":
            self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(self.image, (13, 25, 58, 150), (16, 16), 15)
            pygame.draw.circle(self.image, (20, 92, 192, 230), (16, 16), 11)
            pygame.draw.circle(self.image, (48, 190, 255, 255), (16, 16), 7)
            pygame.draw.circle(self.image, (228, 252, 255, 255), (13, 12), 3)
        else:
            angle = -math.degrees(math.atan2(dy, dx))
            self.image = pygame.transform.rotate(ARROW_IMG, angle)

    def update(self, dt):
        step = dt / 16.0
        self.pos[0] += self.vel[0] * step
        self.pos[1] += self.vel[1] * step
        self.age += dt
        if self.kind == "magic_orb":
            self.trail.append((self.pos[0], self.pos[1], self.age))
            self.trail = self.trail[-7:]
        if self.age > self.MAX_LIFETIME:
            self.alive = False
        if not (-100 <= self.pos[0] <= WIDTH + 100 and
                -100 <= self.pos[1] <= HEIGHT + 100):
            self.alive = False

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
        self.directional = etype == "vampire"
        cfg = VAMPIRE_STATS if self.directional else ENEMY_TYPES[etype]
        self.cfg = cfg
        self.name = cfg.get("name", etype.replace("_", " ").title())
        self.role = cfg.get("role", "fighter")
        self.pos = [float(x), float(y)]

        if self.directional:
            self.display = VAMPIRE_DISPLAY
            self.anchor_height = self.display[1]
            self.render_offset_y = 0
            self.direction = "down"
        else:
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
        self.attack_cd = random.randint(180, 650)
        self.phase_timer = 0.0
        self.current_windup = self.windup_ms
        self.current_attack_range = self.atk_range
        self.attack_target = self.center()
        self.attack_direction_vec = (1.0, 0.0)
        self.attack_count = 0
        self.heavy_attack = False
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
        if self.directional:
            rows = VAMPIRE_ANIMS.get(self.state, VAMPIRE_ANIMS["idle"])
            return vamp_dir_frames(rows, self.direction)
        vertical_direction = None
        if self.state == "walk":
            vertical_direction = self.move_direction
        elif self.state == "attack":
            vertical_direction = self.attack_direction
        if vertical_direction in ("up", "down"):
            vertical = ENEMY_ANIM_SETS[self.etype].get(vertical_direction)
            if vertical and self.state in vertical:
                return vertical[self.state]
        side = self.attack_direction if (
            self.state == "attack" and self.attack_direction in ("left", "right")
        ) else ("left" if self.facing_left else "right")
        anims = ENEMY_ANIM_SETS[self.etype][side]
        return anims.get(self.state, anims["idle"])

    def _set_anim(self, state, reset=False):
        if self.state != state or reset:
            self.state = state
            self.frame_idx = 0.0

    def center(self):
        height = self.display[1] if self.directional else self.anchor_height
        return (self.pos[0] + self.display[0] / 2,
                self.pos[1] + height / 2)

    def feet(self):
        height = self.display[1] if self.directional else self.anchor_height
        return (self.pos[0] + self.display[0] / 2,
                self.pos[1] + height * 0.82)

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
        self.flash_timer = self.FLASH_DURATION
        self.poise -= stagger
        self.poise_delay = 1300
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.combat_state = "dead"
            self._set_anim("dead", reset=True)
            return actual, True
        if self.poise <= 0:
            self.poise = float(self.poise_max)
            self.combat_state = "hurt"
            self.hurt_timer = self.HURT_DURATION + (90 if self.role == "tank" else 0)
            self._set_anim("hurt", reset=True)
        return actual, False

    def _face_vector(self, dx, dy, attack=False):
        if abs(dx) < 1 and abs(dy) < 1:
            return
        if self.directional:
            if abs(dx) > abs(dy):
                self.direction = "left" if dx < 0 else "right"
            else:
                self.direction = "up" if dy < 0 else "down"
            return
        direction = ("left" if dx < 0 else "right") if abs(dx) >= abs(dy) \
            else ("up" if dy < 0 else "down")
        if attack:
            self.attack_direction = direction
        else:
            self.move_direction = direction
        if direction in ("left", "right"):
            self.facing_left = direction == "left"

    def _move(self, vx, vy, dt, speed_mult=1.0):
        mag = math.hypot(vx, vy)
        if mag <= 0.001:
            return
        vx, vy = vx / mag, vy / mag
        self._face_vector(vx, vy, attack=False)
        step = self.speed * speed_mult * dt / 16.0
        self.pos[0] += vx * step
        self.pos[1] += vy * step
        max_x = WIDTH - self.display[0]
        max_y = HEIGHT - self.anchor_height * 0.72
        min_y = self.ARENA_TOP - self.anchor_height * 0.35
        self.pos[0] = max(8, min(max_x - 8, self.pos[0]))
        self.pos[1] = max(min_y, min(max_y, self.pos[1]))

    def _begin_attack(self, hero_center, hero_velocity):
        hx, hy = hero_center
        lead = self.cfg.get("projectile_lead", 0) if self.ranged else 0
        self.attack_target = (hx + hero_velocity[0] * lead,
                              hy + hero_velocity[1] * lead)
        ex, ey = self.center()
        dx, dy = self.attack_target[0] - ex, self.attack_target[1] - ey
        dist = max(1.0, math.hypot(dx, dy))
        self.attack_direction_vec = (dx / dist, dy / dist)
        self._face_vector(dx, dy, attack=True)
        self.attack_count += 1
        self.heavy_attack = self.is_boss and (
            self.attack_count % 3 == 0 or self.boss_phase == 3
        )
        windup_mult = 1.38 if self.heavy_attack else 1.0
        self.current_windup = self.windup_ms * windup_mult
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
        if dist > 1:
            dot = ((dx / dist) * self.attack_direction_vec[0] +
                   (dy / dist) * self.attack_direction_vec[1])
            arc_limit = -0.35 if self.role in ("tank", "bruiser") else -0.05
            if dot < arc_limit:
                return
        dmg = random.randint(*self.dmg_range)
        if self.heavy_attack:
            dmg = int(dmg * 1.45)
        on_hit_hero(dmg, source=self, heavy=self.heavy_attack)

    def _update_committed(self, dt, hero_center, on_hit_hero, spawn_projectile):
        self.phase_timer -= dt
        if self.combat_state == "windup":
            if self.role == "hunter" and self.warning_progress > 0.48:
                self._move(*self.attack_direction_vec, dt,
                           speed_mult=self.cfg.get("lunge_speed", 4.5) / max(0.1, self.speed))
            if self.phase_timer <= 0:
                self.combat_state = "active"
                self.phase_timer = 125 if not self.heavy_attack else 175
                self._resolve_attack(hero_center, on_hit_hero, spawn_projectile)
        elif self.combat_state == "active" and self.phase_timer <= 0:
            self.combat_state = "recover"
            self.phase_timer = self.recovery_ms * (1.18 if self.heavy_attack else 1.0)
        elif self.combat_state == "recover" and self.phase_timer <= 0:
            self.combat_state = "approach"
            self.attack_cd = self.attack_cooldown
            self.approach_angle += random.uniform(-0.8, 0.8)
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
        if dist <= self.atk_range and self.attack_cd <= 0 and allow_attack:
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
        self._set_anim("run" if self.directional and self.boss_phase >= 2 else "walk")
        self._move(vx, vy, dt, speed_mult=1.08 if self.role == "aggressor" else 1.0)

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
            self.combat_state = "approach"
            self.attack_cd = 360
            self._set_anim("idle", reset=True)
        self.speed = self.base_speed * (1.0 + 0.16 * (self.boss_phase - 1))
        self.windup_ms = self.cfg.get("windup", 520) * (1.0 - 0.08 * (self.boss_phase - 1))
        self.attack_cooldown = self.cfg.get("attack_cooldown", 1050) * (
            1.0 - 0.13 * (self.boss_phase - 1)
        )

    def update(self, dt, hero_center, on_hit_hero, spawn_projectile=None,
               other_positions=None, allow_attack=True, hero_velocity=(0, 0)):
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

        if self.dead:
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
            return

        self.attack_cd = max(0, self.attack_cd - dt)
        if self.poise_delay > 0:
            self.poise_delay -= dt
        else:
            self.poise = min(self.poise_max, self.poise + dt * self.poise_max / 2400)

        ex, ey = self.center()
        hx, hy = hero_center
        self._face_vector(hx - ex, hy - ey, attack=self.is_committed)

        if self.is_committed:
            self._update_committed(dt, hero_center, on_hit_hero, spawn_projectile)
        elif self.ranged:
            self._update_ranged(dt, hero_center, allow_attack,
                                other_positions, hero_velocity)
        else:
            self._update_melee(dt, hero_center, allow_attack,
                               other_positions, hero_velocity)
        self._advance_animation(dt)

    def _advance_animation(self, dt):
        frames = self._frames()
        self.frame_idx += dt * self.FPS / 1000
        if self.frame_idx >= len(frames):
            if self.is_committed or self.combat_state in ("hurt", "dead"):
                self.frame_idx = len(frames) - 1
            else:
                self.frame_idx = 0

    def _draw_telegraph(self, screen, ox, oy):
        if self.combat_state != "windup":
            return
        progress = self.warning_progress
        pulse = 0.72 + math.sin(progress * math.pi * 7) * 0.16
        alpha = int((70 + 150 * progress) * pulse)
        ex, ey = self.feet()
        ex += ox
        ey += oy
        color = (255, 64, 72) if not self.heavy_attack else (255, 174, 72)
        if self.ranged:
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
        frames = self._frames()
        idx = min(int(self.frame_idx), len(frames) - 1)
        frame = frames[idx]
        x = self.pos[0] + ox
        logical_y = self.pos[1] + oy
        y = logical_y if self.directional else logical_y + self.render_offset_y
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
