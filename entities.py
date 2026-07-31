"""
Projectile and Enemy game objects.
"""
import pygame
import random
import math
from settings import WIDTH, HEIGHT
from sprite_loaders import dir_frames, vamp_dir_frames
from game_data import (
    ENEMY_TYPES, ENEMY_ANIM_SETS, ENEMY_CANVAS_SIZE,
    VAMPIRE_ANIMS, VAMPIRE_STATS, VAMPIRE_DISPLAY, ARROW_IMG,
)

class Projectile:
    SPEED = 9
    MAX_LIFETIME = 3000

    def __init__(self, x, y, target_x, target_y, dmg):
        self.pos = [x, y]
        dx, dy = target_x - x, target_y - y
        dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
        self.vel = [self.SPEED * dx / dist, self.SPEED * dy / dist]
        self.dmg = dmg
        self.alive = True
        self.age = 0
        angle = -math.degrees(math.atan2(dy, dx))
        self.image = pygame.transform.rotate(ARROW_IMG, angle)

    def update(self, dt):
        self.pos[0] += self.vel[0] * (dt / 16.0)
        self.pos[1] += self.vel[1] * (dt / 16.0)
        self.age += dt
        if self.age > self.MAX_LIFETIME:
            self.alive = False
        if not (-100 <= self.pos[0] <= WIDTH + 100 and -100 <= self.pos[1] <= HEIGHT + 100):
            self.alive = False

    def draw(self, screen, ox, oy):
        rect = self.image.get_rect(
            center=(self.pos[0] + ox, self.pos[1] + oy))
        screen.blit(self.image, rect)


class Enemy:
    ATTACK_RANGE = 110
    ATTACK_COOLDOWN = 1000
    FPS = 8
    HURT_DURATION = 300

    def __init__(self, etype, x, y):
        self.etype = etype
        self.pos = [x, y]
        self.directional = (etype == "vampire")
        if self.directional:
            self.display = VAMPIRE_DISPLAY
            self.hp = VAMPIRE_STATS["hp"]
            self.max_hp = VAMPIRE_STATS["hp"]
            self.dmg_range = VAMPIRE_STATS["dmg"]
            self.speed = VAMPIRE_STATS["speed"]
            self.direction = "down"
            self.ranged = False
            self.atk_range = self.ATTACK_RANGE
        else:
            cfg = ENEMY_TYPES[etype]
            self.display = ENEMY_CANVAS_SIZE[etype]
            self.hp = cfg["hp"]
            self.max_hp = cfg["hp"]
            self.dmg_range = cfg["dmg"]
            self.speed = cfg["speed"]
            self.facing_left = True
            self.ranged = cfg.get("ranged", False)
            self.atk_range = cfg.get("atk_range", self.ATTACK_RANGE)
        self.state = "idle"
        self.frame_idx = 0.0
        self.attack_cd = random.randint(0, 400)
        self.hurt_timer = 0
        self.dead = False
        self.dead_done = False
        self.is_boss = False
        # A fixed random angle around the hero this enemy tries to circle
        # to, instead of every enemy beelining to the exact same point.
        self.approach_angle = random.uniform(0, 2 * math.pi)
        # Knockback: a short-lived slide applied on hit, independent of
        # the enemy's own AI movement.
        self.knock_vel = [0.0, 0.0]
        self.knock_timer = 0
        self.KNOCK_DURATION = 220
        # Brief white flash on any hit, independent of the longer hurt stagger.
        self.flash_timer = 0
        self.FLASH_DURATION = 90

    def set_stats(self, hp, dmg_range):
        self.hp = hp
        self.max_hp = hp
        self.dmg_range = dmg_range

    def _frames(self):
        if self.directional:
            rows = VAMPIRE_ANIMS.get(self.state, VAMPIRE_ANIMS["idle"])
            return vamp_dir_frames(rows, self.direction)
        side = "left" if self.facing_left else "right"
        anims = ENEMY_ANIM_SETS[self.etype][side]
        return anims.get(self.state, anims["idle"])

    def center(self):
        return (self.pos[0] + self.display[0] / 2, self.pos[1] + self.display[1] / 2)

    def apply_knockback(self, dirx, diry, force):
        # Bosses shrug off knockback almost entirely -- shoving a boss
        # around the screen would feel cheap, not powerful.
        if self.is_boss:
            force *= 0.15
        self.knock_vel = [dirx * force, diry * force]
        self.knock_timer = self.KNOCK_DURATION

    def take_damage(self, dmg):
        if self.dead:
            return
        self.hp -= dmg
        self.flash_timer = self.FLASH_DURATION
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.state = "dead"
            self.frame_idx = 0
        else:
            self.state = "hurt"
            self.hurt_timer = self.HURT_DURATION
            self.frame_idx = 0

    def update(self, dt, hero_center, on_hit_hero, spawn_projectile=None, other_positions=None):
        if self.flash_timer > 0:
            self.flash_timer -= dt

        if self.knock_timer > 0 and not self.dead:
            self.pos[0] += self.knock_vel[0] * (dt / 16.0)
            self.pos[1] += self.knock_vel[1] * (dt / 16.0)
            self.knock_timer -= dt
            # Exponential-ish decay so the slide eases out instead of
            # stopping dead or sliding forever.
            decay = max(0.0, 1 - (dt / self.KNOCK_DURATION))
            self.knock_vel[0] *= decay
            self.knock_vel[1] *= decay

        if self.dead:
            frames = self._frames()
            self.frame_idx += dt * self.FPS / 1000
            if self.frame_idx >= len(frames):
                self.frame_idx = len(frames) - 1
                self.dead_done = True
            return

        if self.hurt_timer > 0:
            self.hurt_timer -= dt
            frames = self._frames()
            self.frame_idx += dt * self.FPS / 1000
            if self.frame_idx >= len(frames):
                self.frame_idx = 0
            if self.hurt_timer <= 0:
                self.state = "idle"
            return

        ex, ey = self.center()
        hx, hy = hero_center
        dx, dy = hx - ex, hy - ey
        dist = (dx * dx + dy * dy) ** 0.5
        if dist > 4:
            if self.directional:
                if abs(dx) > abs(dy):
                    self.direction = "left" if dx < 0 else "right"
                else:
                    self.direction = "up" if dy < 0 else "down"
            else:
                self.facing_left = dx < 0

        if self.attack_cd > 0:
            self.attack_cd -= dt

        if dist <= self.atk_range:
            self.state = "attack"
            if self.attack_cd <= 0:
                self.attack_cd = self.ATTACK_COOLDOWN
                if self.ranged and spawn_projectile is not None:
                    spawn_projectile(self, hero_center)
                elif not self.ranged:
                    on_hit_hero(random.randint(*self.dmg_range))
        else:
            self.state = "walk"
            # Head for a point around the hero (this enemy's own angle)
            # rather than the hero's exact position, so several enemies
            # spread out instead of stacking on the same spot.
            stand_radius = max(40, self.atk_range * 0.7)
            tx = hx + stand_radius * math.cos(self.approach_angle)
            ty = hy + stand_radius * math.sin(self.approach_angle)
            mdx, mdy = tx - ex, ty - ey
            mdist = (mdx * mdx + mdy * mdy) ** 0.5
            if mdist > 2:
                vx, vy = mdx / mdist, mdy / mdist
            else:
                vx, vy = 0.0, 0.0
            # Separation: nudge away from any other enemy that's crowding in
            if other_positions:
                for (ox, oy) in other_positions:
                    sdx, sdy = ex - ox, ey - oy
                    sd = (sdx * sdx + sdy * sdy) ** 0.5
                    if 0 < sd < 70:
                        push = (70 - sd) / 70
                        vx += (sdx / sd) * push
                        vy += (sdy / sd) * push
                vnorm = (vx * vx + vy * vy) ** 0.5
                if vnorm > 0:
                    vx, vy = vx / vnorm, vy / vnorm
            self.pos[0] += self.speed * vx
            self.pos[1] += self.speed * vy

        frames = self._frames()
        self.frame_idx += dt * self.FPS / 1000
        if self.frame_idx >= len(frames):
            self.frame_idx = 0

    def draw(self, screen, ox, oy):
        frames = self._frames()
        idx = min(int(self.frame_idx), len(frames) - 1)
        frame = frames[idx]
        x, y = self.pos[0] + ox, self.pos[1] + oy
        screen.blit(frame, (x, y))
        if self.flash_timer > 0:
            mask = pygame.mask.from_surface(frame)
            flash_alpha = int(220 * min(1.0, self.flash_timer / self.FLASH_DURATION))
            flash_img = mask.to_surface(
                setcolor=(255, 255, 255, flash_alpha),
                unsetcolor=(0, 0, 0, 0))
            screen.blit(flash_img, (x, y))
        if not self.dead and not self.is_boss:
            bar_w = 64
            bar_x = x + self.display[0] / 2 - bar_w / 2
            bar_y = y - 14
            pygame.draw.rect(screen, (30, 10, 10), (bar_x, bar_y, bar_w, 6))
            fill_w = int(bar_w * self.hp / self.max_hp)
            pygame.draw.rect(screen, (200, 50, 50),
                             (bar_x, bar_y, fill_w, 6))

