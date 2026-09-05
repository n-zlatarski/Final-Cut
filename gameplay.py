"""
The main fight screen: enemy/stage setup, the hero update+render
loop, combat resolution, and the HUD.
"""
import pygame
import sys
import random
import math
import video
from settings import *
from ui import (
    draw_text, draw_panel, draw_stat_bar, draw_ornate_frame,
    draw_segmented_bar, draw_keycap, draw_vignette, draw_corner_marks,
)
from audio import play_music
from animator import Animator
from sprite_loaders import dir_frames
from entities import Enemy, Projectile
from game_data import (
    STAGES, ENEMY_TYPES, CLASS_STATS, portrait_imgs, STAGE_BGS,
    ASSASSIN_DRAW_OFFSET,
    warrior_anims, _w_idle_rows, _w_walk_rows, _w_run_rows, _w_atk_rows,
    _w_run_atk_rows, _w_walk_atk_rows, _w_hurt_rows, _w_death_rows,
    assassin_anims, _a_idle_rows, _a_walk_rows, _a_run_rows,
    _a_atk1_rows, _a_atk2_rows, _a_atk3_rows, _a_walk_atk_rows,
    _a_deaths_dance_rows, _a_deaths_dance_fx, _a_sonic_stream_rows,
    _a_run_atk_rows, _a_dash_rows, _a_dash_atk_rows,
    _a_hurt_rows, _a_death_rows,
)
from screens import pause_menu, options_menu

def spawn_enemies(stage):
    enemies = []
    mult = stage.get("wave_mult", 1.0)
    slots = [
        (WIDTH - 750, HEIGHT - 620),
        (WIDTH - 520, HEIGHT - 500),
        (WIDTH - 750, HEIGHT - 350),
        (WIDTH - 390, HEIGHT - 690),
    ]
    for i, etype in enumerate(stage["enemies"]):
        cfg = ENEMY_TYPES[etype]
        sx, sy = slots[i % len(slots)]
        sx += random.randint(-30, 30)
        sy += random.randint(-30, 30)
        e = Enemy(etype, sx, sy)
        e.set_stats(int(cfg["hp"] * mult),
                    (int(cfg["dmg"][0] * mult), int(cfg["dmg"][1] * mult)))
        enemies.append(e)
    return enemies


def spawn_boss(stage):
    boss_type = stage["boss"]
    cfg = ENEMY_TYPES[boss_type]
    mult = stage.get("wave_mult", 1.0)
    boss = Enemy(boss_type, WIDTH - 640, HEIGHT - 520)
    boss.set_stats(int(cfg["hp"] * mult),
                   (int(cfg["dmg"][0] * mult), int(cfg["dmg"][1] * mult)))
    boss.is_boss = True
    return boss


def stage_screen(hero_class, hero_name, stage_idx, run_state=None, *, boss_only=False):
    stage = STAGES[stage_idx]
    bg_img = STAGE_BGS[stage["bg"]]
    play_music(stage["bg"])

    if run_state is None:
        run_state = {
            "damage_mult": 1.0, "bonus_health": 0, "bonus_stamina": 0,
            "crit_bonus": 0.0, "dash_cooldown_mult": 1.0,
            "special_cooldown_mult": 1.0, "heal_on_kill": 0,
            "boons": [], "last_summary": {},
        }

    stats = CLASS_STATS[hero_class]
    hero_hp = stats["health"] + run_state.get("bonus_health", 0)
    hero_max_hp = hero_hp
    stamina = stats["stamina"] + run_state.get("bonus_stamina", 0)
    max_stamina = stamina
    damage_mult = run_state.get("damage_mult", 1.0)

    # Class-specific combat tuning.  The Assassin art contains more frames
    # than the Warrior and is meant to feel quick, so its animation speeds and
    # recovery windows are matched to the supplied sprite sheets instead of
    # reusing the Warrior timing values.
    is_assassin = hero_class == "Assassin"
    RUN_ATK_COOLDOWN = 1200
    ATTACK_RANGE = 158 if is_assassin else 170
    last_attack_time = 0
    last_run_atk_time = 0

    # ── 3-hit combo ──
    if is_assassin:
        COMBO_STEPS = [
            # V7 makes the approved three-hit dagger chain a little snappier
            # without returning to the old blink-and-you-miss-it 20+ FPS
            # timing.  Recovery tracks the new six-frame animation duration.
            {"dmg": (14, 24), "knockback": 4,  "recovery": 380, "fps": 16, "range": ATTACK_RANGE},
            {"dmg": (17, 28), "knockback": 6,  "recovery": 380, "fps": 16, "range": ATTACK_RANGE + 5},
            {"dmg": (28, 42), "knockback": 11, "recovery": 520, "fps": 13, "range": ATTACK_RANGE + 18},
        ]
        COMBO_WINDOW = 700
    else:
        COMBO_STEPS = [
            {"dmg": (15, 28), "knockback": 6,  "recovery": 260, "fps": 14, "range": ATTACK_RANGE},
            {"dmg": (20, 34), "knockback": 9,  "recovery": 300, "fps": 14, "range": ATTACK_RANGE},
            {"dmg": (35, 55), "knockback": 16, "recovery": 500, "fps": 11, "range": ATTACK_RANGE + 25},
        ]
        COMBO_WINDOW = 550

    # ── dash ──
    # Assassin dash sheet = 7 frames.  32 fps is ~219 ms, so the movement
    # duration below finishes almost exactly with the final animation frame.
    DASH_ANIM_FPS = 32 if is_assassin else 20
    DASH_ATTACK_FPS = 22 if is_assassin else 18
    DASH_SPEED = 17 if is_assassin else 16
    DASH_DURATION = 215 if is_assassin else 160
    DASH_COOLDOWN = int((420 if is_assassin else 500) *
                        run_state.get("dash_cooldown_mult", 1.0))
    DASH_STAMINA_COST = 18 if is_assassin else 20
    DASH_ATTACK_BUFFER = 170 if is_assassin else 150
    DIR_VECS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}
    last_dash_time = 0
    FACING_COS_THRESHOLD = math.cos(math.radians(100))

    # ── critical hits ──
    CRIT_CHANCE = min(0.65, (0.24 if is_assassin else 0.18) +
                      run_state.get("crit_bonus", 0.0))
    CRIT_MULT = 1.8

    # One readable class ability rather than another hidden damage modifier.
    SPECIAL_NAME = stats["special"]
    SPECIAL_COOLDOWN = int((7200 if is_assassin else 8200) *
                           run_state.get("special_cooldown_mult", 1.0))
    SPECIAL_COST = 52 if is_assassin else 58
    FOCUS_COOLDOWN = 2600
    FOCUS_RESTORE = 72 if is_assassin else 64
    DEATHS_DANCE_DURATION = 1120
    DEATHS_DANCE_TRAVEL_END = 560
    DEATHS_DANCE_TRAVEL_SPEED = 8.2
    DEATHS_DANCE_SPIN_TIMES = (155, 335, 515)
    DEATHS_DANCE_ERUPTION_TIMES = (690, 845, 1000)
    SONIC_STREAM_NAME = "Sonic Stream"
    SONIC_STREAM_COOLDOWN = int(
        9200 * run_state.get("special_cooldown_mult", 1.0)
    )
    SONIC_STREAM_COST = 60
    SONIC_STREAM_DURATION = 1320
    SONIC_STREAM_DASH_END = 310
    SONIC_STREAM_DASH_SPEED = 13.4
    SONIC_STREAM_HIT_TIMES = (330, 475, 620, 765, 910)
    SONIC_STREAM_WAVE_TIMES = (1010, 1125, 1240)

    # ── hitstop / enemy flash / sword trail ──
    HITSTOP_HIT = 45 if is_assassin else 55
    HITSTOP_FINISHER = 80 if is_assassin else 100
    _trail_base = None
    _assassin_trail_cache = {}

    direction = "right"
    if hero_class == "Assassin":
        anim = Animator(assassin_anims.copy(), default="idle", fps=8)
        idle_rows, walk_rows, run_rows = _a_idle_rows, _a_walk_rows, _a_run_rows
        atk_combo_rows = (_a_atk1_rows, _a_atk2_rows, _a_atk3_rows)
        walk_atk_rows = _a_walk_atk_rows
        sonic_stream_rows = _a_sonic_stream_rows
        run_atk_rows = _a_run_atk_rows
        dash_rows, dash_attack_rows = _a_dash_rows, _a_dash_atk_rows
        hurt_rows, death_rows = _a_hurt_rows, _a_death_rows
    else:
        anim = Animator(warrior_anims.copy(), default="idle", fps=8)
        idle_rows, walk_rows, run_rows = _w_idle_rows, _w_walk_rows, _w_run_rows
        atk_combo_rows = (_w_atk_rows, _w_atk_rows, _w_atk_rows)
        sonic_stream_rows = _w_atk_rows
        run_atk_rows = _w_run_atk_rows
        dash_rows, dash_attack_rows = _w_run_rows, _w_atk_rows
        walk_atk_rows = (_w_walk_atk_rows, _w_walk_atk_rows, _w_walk_atk_rows)
        hurt_rows, death_rows = _w_hurt_rows, _w_death_rows

    last_time = pygame.time.get_ticks()
    log = []

    def add_log(msg, color=WHITE):
        log.append((msg, color))
        if len(log) > 5:
            log.pop(0)

    def play_dir(anim_name, rows_or_frames, one_shot=False, force=False, fps=None):
        frames = dir_frames(rows_or_frames, direction)
        anim.play(anim_name, frames=frames,
                  one_shot=one_shot, force=force, fps=fps)

    state = {
        "hero_hp": hero_hp,
        "stamina": stamina,
        "result":  None,
        "shake":   0,
        "boss_spawned": False,
        "exit_unlocked": False,
        "combo_index": 0,
        # Combo progression follows successful attack INPUTS, not successful
        # hits.  The old last_hit_time reset meant swinging at empty space
        # could replay hit 1 forever instead of reaching attacks 2 and 3.
        "last_combo_time": -100000,
        "last_hit_time": 0,
        "current_recovery": 0,
        # Hits that have been "thrown" by a swing but haven't landed yet --
        # damage/knockback applies when the sword is actually mid-swing,
        # not the instant you click.
        "pending_hits": [],
        "dashing": False,
        "dash_dir": (0, 0),
        "dash_end_time": 0,
        "dash_finished_at": -100000,
        "hitstop": 0,
        "slashes": [],
        "assassin_sparks": [],
        "shockwaves": [],
        "deaths_dance": None,
        "sonic_stream": None,
        "eruption_fx": [],
        "floaters": [],
        "buffered_attack_until": 0,
        "invulnerable_until": 0,
        "dash_started_at": -100000,
        "evaded_this_dash": False,
        "last_special_time": -100000,
        "last_sonic_stream_time": -100000,
        "last_focus_time": -100000,
        "damage_flash": 0,
        "low_hp_pulse": 0,
        "hit_streak": 0,
        "last_streak_time": -100000,
        "best_streak": 0,
        "stage_started_at": pygame.time.get_ticks(),
        "stage_intro_until": pygame.time.get_ticks() + 2100,
        "stats": {
            "damage_dealt": 0,
            "damage_taken": 0,
            "kills": 0,
            "crits": 0,
            "attacks": 0,
            "hits": 0,
            "dodges": 0,
        },
    }

    hero_pos = [120, HEIGHT - 450]
    previous_hero_pos = list(hero_pos)
    hero_velocity = [0.0, 0.0]
    enemies = spawn_enemies(stage)
    if boss_only:
        enemies = [spawn_boss(stage)]
        state["boss_spawned"] = True
        play_music("boss")
    projectiles = []

    def add_floater(text, pos, color=CREAM, size="small", life=720):
        state["floaters"].append({
            "text": str(text), "pos": [float(pos[0]), float(pos[1])],
            "color": color, "size": size, "start": pygame.time.get_ticks(),
            "life": life,
        })

    def save_stage_summary():
        elapsed = max(0, pygame.time.get_ticks() - state["stage_started_at"])
        minutes, seconds = divmod(elapsed // 1000, 60)
        run_state["last_summary"] = {
            "time": f"{minutes:02d}:{seconds:02d}",
            "damage_dealt": state["stats"]["damage_dealt"],
            "damage_taken": state["stats"]["damage_taken"],
            "kills": state["stats"]["kills"],
            "best_combo": state["best_streak"],
            "crits": state["stats"]["crits"],
            "dodges": state["stats"]["dodges"],
        }

    # After combat, reaching the true right edge advances silently.  There is
    # no exit marker or combat-time barrier; the player remains free to move
    # around the entire room.
    STAGE_EXIT_X = WIDTH - DISPLAY_SIZE[0]

    FEET_OFFSET = {
        "Warrior": 115,
        "Assassin": 166,
    }
    # Clamp by the hero's feet at the first walkable row of this background.
    # A shared value let Jinwoo stand inside the forest fence, castle/terrace
    # railings, and the throne platform because those props sit at different Y
    # positions in each image.
    TOP_BORDER_Y = stage["floor_top"]
    WALK_SPEED = 3.4 if is_assassin else 3
    RUN_SPEED = 4.7 if is_assassin else 4
    _portrait = portrait_imgs.get(hero_class)
    hud_portrait = (pygame.transform.smoothscale(_portrait, (92, 92))
                    if _portrait is not None else None)

    # Locomotion animations need their own explicit rates. Attack playback
    # temporarily raises Animator.fps (16/16/13 for Jinwoo's combo), so leaving
    # idle/run at fps=None lets the previous action leak its timing into the
    # next movement state. The rebuilt walk uses six genuinely distinct gait
    # phases, so it can use the same natural 8 FPS cadence as the Swordsman.
    IDLE_ANIM_FPS = 8
    WALK_ANIM_FPS = 8
    RUN_ANIM_FPS = 8

    # The Assassin's front/back walk art has much subtler leg travel than its
    # side-facing rows. Keep the established vertical cadence. The new artwork
    # supplies its own planted/passing poses without a second artificial bob.
    ASSASSIN_VERTICAL_WALK_FPS = 10

    # Once sprint drains the bar completely, holding Shift must not immediately
    # consume the tiny amount regenerated on the next frame.  Without this
    # latch the state oscillates RUN -> WALK -> RUN -> WALK at zero stamina.
    # Require a Shift release and a small recovery buffer before sprint can be
    # armed again.
    SPRINT_RESUME_STAMINA = 5.0
    state["sprint_exhausted"] = False

    def hero_center():
        return (hero_pos[0] + DISPLAY_SIZE[0] / 2, hero_pos[1] + DISPLAY_SIZE[1] / 2)

    def hurt_hero(dmg, source=None, heavy=False):
        now = pygame.time.get_ticks()
        if state["result"]:
            return False
        if state["dashing"] or now < state["invulnerable_until"]:
            if state["dashing"] and not state["evaded_this_dash"]:
                state["evaded_this_dash"] = True
                state["stats"]["dodges"] += 1
                state["stamina"] = min(max_stamina, state["stamina"] + 10)
                add_floater("PERFECT EVADE", hero_center(), (126, 205, 255),
                            size="medium", life=850)
            return False
        state["hero_hp"] -= dmg
        state["stats"]["damage_taken"] += dmg
        commander_combo = (
            source is not None and getattr(source, "role", None) == "commander"
            and getattr(source, "boss_action", None) in {
                "light_combo", "overhead_slash", "ground_slam",
                "ranged_thrust",
            }
        )
        state["invulnerable_until"] = now + (
            95 if commander_combo else 620 if heavy else 480
        )
        state["damage_flash"] = 280 if heavy else 190
        state["shake"] = 12 if heavy else 7
        state["hit_streak"] = 0
        add_floater(f"-{dmg}", hero_center(), COL_DANGER,
                    size="medium" if heavy else "small")
        add_log(f"Took {dmg} damage", RED)
        if source is not None:
            sx, sy = source.center()
            hx, hy = hero_center()
            dx, dy = hx - sx, hy - sy
            dist = max(1.0, math.hypot(dx, dy))
            force = 22 if heavy else 11
            hero_pos[0] = max(0, min(STAGE_EXIT_X,
                                    hero_pos[0] + dx / dist * force))
            knocked_y = hero_pos[1] + dy / dist * force * 0.65
            hero_pos[1] = max(
                TOP_BORDER_Y - FEET_OFFSET[hero_class],
                min(HEIGHT - FEET_OFFSET[hero_class], knocked_y),
            )
        if state["hero_hp"] <= 0:
            state["hero_hp"] = 0
            state["result"] = "lose"
            save_stage_summary()
            play_dir("death", death_rows, one_shot=True, force=True, fps=9)
            state["death_played"] = True
        else:
            play_dir("hurt", hurt_rows, one_shot=True, force=True, fps=12)
        return True

    def try_dash():
        nonlocal last_dash_time
        now = pygame.time.get_ticks()
        if (state["result"] or state["dashing"]
                or state.get("deaths_dance") or state.get("sonic_stream")):
            return
        if now - last_dash_time < DASH_COOLDOWN:
            return
        if state["stamina"] < DASH_STAMINA_COST:
            add_log("Not enough stamina to dash!", YELLOW)
            return
        state["stamina"] -= DASH_STAMINA_COST
        last_dash_time = now
        state["dashing"] = True
        state["dash_started_at"] = now
        state["evaded_this_dash"] = False
        state["dash_dir"] = DIR_VECS.get(direction, (1, 0))
        state["dash_end_time"] = now + DASH_DURATION
        state["invulnerable_until"] = state["dash_end_time"] + 70
        play_dir("dash", dash_rows, one_shot=True, force=True, fps=DASH_ANIM_FPS)

    def is_dash_attack_window():
        now = pygame.time.get_ticks()
        return state["dashing"] or (now - state["dash_finished_at"] <= DASH_ATTACK_BUFFER)

    def roll_crit(dmg, force_crit=False):
        if force_crit or random.random() < CRIT_CHANCE:
            return int(dmg * CRIT_MULT), True
        return dmg, False

    def do_dash_attack():
        nonlocal last_attack_time
        now = pygame.time.get_ticks()
        dmg = int(random.randint(28, 42) * damage_mult)
        dmg, crit = roll_crit(dmg)
        state["stats"]["attacks"] += 1
        last_attack_time = now
        state["current_recovery"] = 310 if is_assassin else 260
        state["combo_index"] = 0
        state["last_combo_time"] = -100000
        # Assassin dash-strikes keep the momentum of the dash that triggered
        # them.  Previously this line unconditionally stopped dashing, which
        # is why pressing attack made Jinwoo travel only a tiny distance.
        # Warrior behavior stays unchanged.
        if not is_assassin:
            state["dashing"] = False
        play_dir("dash_attack", dash_attack_rows, one_shot=True, force=True, fps=DASH_ATTACK_FPS)
        if hero_class == "Warrior":
            spawn_slash(direction, duration=220)
        queue_hit(dmg, knockback=12, atk_range=ATTACK_RANGE + 15, fps=DASH_ATTACK_FPS,
                  facing=direction, crit=crit)
        add_log("Dash Strike!", GOLD)

    def get_trail_surface():
        nonlocal _trail_base
        if _trail_base is None:
            size = 140
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            rect = pygame.Rect(14, 14, size - 28, size - 28)
            # A few concentric arcs, each fainter/thinner than the last,
            # to fake a motion-blur swoosh without needing sprite frames.
            for i in range(5):
                alpha = max(30, 210 - i * 40)
                width = max(1, 6 - i)
                pygame.draw.arc(surf, (255, 235, 190, alpha), rect,
                                math.radians(-55), math.radians(55), width)
                rect = rect.inflate(-6, -6)
            _trail_base = surf
        return _trail_base

    def get_assassin_trail_surface(combo_step):
        """Load the richer PNG dagger VFX while keeping v10 combat behavior.

        The original v10 procedural trail remains below as a fallback if an
        effect asset is ever missing from a copied install.
        """
        if combo_step in _assassin_trail_cache:
            return _assassin_trail_cache[combo_step]

        vfx_path = f"assets/Assassin/VFX/slash_hit{combo_step}.png"
        try:
            surf = pygame.image.load(vfx_path).convert_alpha()
            _assassin_trail_cache[combo_step] = surf
            return surf
        except Exception as exc:
            print(f"FAILED to load {vfx_path}: {exc}; using v10 fallback trail")

        size = 190
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        slash_a = [(31, 146), (51, 134), (74, 116),
                   (98, 94), (121, 69), (145, 40), (157, 26)]
        slash_b = [(31, 42), (52, 54), (75, 72),
                   (100, 94), (124, 119), (146, 145), (157, 160)]

        def draw_dagger_stroke(points, strength=1.0):
            # Soft outer aura -> v9 crimson trail -> hot blade core.
            pygame.draw.lines(surf, (105, 0, 26, int(30 * strength)),
                              False, points, 19)
            glow_alpha = int(62 * strength)
            red_alpha = int(225 * strength)
            core_alpha = int(245 * strength)
            pygame.draw.lines(surf, (150, 0, 24, glow_alpha),
                              False, points, 13)
            pygame.draw.lines(surf, (235, 16, 43, red_alpha),
                              False, points, 6)
            pygame.draw.lines(surf, (255, 96, 110, core_alpha),
                              False, points, 3)
            pygame.draw.aalines(surf, (255, 244, 244, core_alpha),
                                False, points)
            # Three narrow echoes add speed/energy without turning the trail
            # into an opaque hoop.
            for shift, alpha in ((7, 92), (13, 54), (19, 28)):
                echo = [(x - shift, y) for x, y in points]
                pygame.draw.aalines(surf, (220, 10, 40, alpha),
                                    False, echo)

        if combo_step == 1:
            draw_dagger_stroke(slash_a)
            for px, py in ((148, 37), (157, 29), (164, 23)):
                pygame.draw.circle(surf, (255, 50, 72, 170), (px, py), 2)
        elif combo_step == 2:
            draw_dagger_stroke(slash_b)
            for px, py in ((148, 147), (158, 156), (166, 164)):
                pygame.draw.circle(surf, (255, 50, 72, 170), (px, py), 2)
        else:
            # Finisher uses both physical dagger paths, but keeps the trails
            # narrow so the character remains readable through the impact.
            draw_dagger_stroke(slash_a, 1.0)
            draw_dagger_stroke(slash_b, 1.0)
            # Compact impact bloom at the crossing point.  It fades/rotates
            # with the trails, so it remains directional and never covers the
            # whole character.
            pygame.draw.circle(surf, (140, 0, 28, 55), (99, 94), 22)
            pygame.draw.circle(surf, (245, 16, 48, 110), (99, 94), 12)
            pygame.draw.circle(surf, (255, 220, 220, 225), (99, 94), 4)
            for px, py in ((161, 28), (166, 38), (162, 151), (169, 160)):
                pygame.draw.circle(surf, (255, 45, 70, 150), (px, py), 3)
                pygame.draw.circle(surf, (255, 235, 235, 230), (px, py), 1)

        _assassin_trail_cache[combo_step] = surf
        return surf

    def spawn_slash(facing, duration=200):
        hx, hy = hero_center()
        dirx, diry = DIR_VECS.get(facing, (1, 0))
        pos = (hx + dirx * 55, hy + diry * 55)
        angle = {"right": 0, "left": 180, "up": 90, "down": 270}.get(facing, 0)
        state["slashes"].append({
            "pos": pos, "angle": angle,
            "start": pygame.time.get_ticks(), "duration": duration,
        })

    def spawn_assassin_sparks(pos, facing, combo_step):
        """Emit a small directional burst around each dagger impact."""
        dirx, diry = DIR_VECS.get(facing, (1, 0))
        sidex, sidey = -diry, dirx
        count = {1: 8, 2: 12, 3: 22}.get(combo_step, 8)
        now = pygame.time.get_ticks()
        for _ in range(count):
            forward = random.uniform(1.4, 3.2 if combo_step < 3 else 4.4)
            side = random.uniform(-2.0, 2.0) * (1.25 if combo_step == 3 else 1.0)
            state["assassin_sparks"].append({
                "pos": (pos[0] + random.uniform(-8, 8),
                        pos[1] + random.uniform(-8, 8)),
                "vel": (dirx * forward + sidex * side,
                        diry * forward + sidey * side),
                "start": now,
                "life": random.randint(190, 270 if combo_step < 3 else 340),
                "radius": random.choice((1, 1, 2, 2, 3 if combo_step == 3 else 2)),
            })

    def spawn_assassin_slash(facing, combo_step, duration=180):
        """Place the red dagger effect in front of the actual facing vector."""
        hx, hy = hero_center()
        dirx, diry = DIR_VECS.get(facing, (1, 0))
        offset = 72 if combo_step == 3 else 64
        pos = (hx + dirx * offset, hy + diry * offset)
        angle = {"right": 0, "left": 180, "up": 90, "down": 270}.get(facing, 0)
        state["slashes"].append({
            "kind": "assassin",
            "combo_step": combo_step,
            "pos": pos,
            "angle": angle,
            "start": pygame.time.get_ticks(),
            "duration": duration,
        })
        spawn_assassin_sparks(pos, facing, combo_step)

    def do_attack(is_moving, is_sprinting):
        nonlocal last_attack_time
        now = pygame.time.get_ticks()

        if state.get("deaths_dance") or state.get("sonic_stream"):
            return

        if is_dash_attack_window():
            do_dash_attack()
            return

        # ── normal 3-hit combo ──
        if now - last_attack_time < state["current_recovery"]:
            return  # still recovering from the last swing

        # Waited too long since the previous light-attack input? Reset to hit
        # 1. This deliberately does not depend on whether the swing connected.
        if now - state["last_combo_time"] > COMBO_WINDOW:
            state["combo_index"] = 0

        combo_index = state["combo_index"]
        step = COMBO_STEPS[combo_index]
        dmg = int(random.randint(*step["dmg"]) * damage_mult)
        dmg, crit = roll_crit(dmg)
        state["stats"]["attacks"] += 1
        last_attack_time = now
        state["current_recovery"] = step["recovery"]
        state["last_combo_time"] = now

        visual_fps = step["fps"]
        if is_assassin:
            # The remake shares one model across standing and moving poses.
            # Select the matching legs while retaining the combo's existing
            # damage, hit delay, recovery and unrestricted movement.
            if is_moving and is_sprinting:
                anim_name, rows = "run_attack", run_atk_rows
                # Eight running poses occupy the same time as six combo poses;
                # the fifth running pose coincides with the existing hit time.
                visual_fps *= len(dir_frames(rows, direction)) / len(
                    dir_frames(atk_combo_rows[combo_index], direction))
            else:
                anim_name = f"attack_{combo_index + 1}"
                rows = (walk_atk_rows if is_moving else atk_combo_rows)[combo_index]
        elif is_moving and is_sprinting:
            anim_name, rows = "run_attack", run_atk_rows
        elif is_moving:
            anim_name, rows = "walk_attack", walk_atk_rows[combo_index]
        else:
            anim_name, rows = "attack", atk_combo_rows[combo_index]
        play_dir(anim_name, rows, one_shot=True, force=True, fps=visual_fps)
        if hero_class == "Warrior":
            spawn_slash(direction, duration=260 if combo_index == 2 else 190)

        queue_hit(dmg, knockback=step["knockback"],
                  atk_range=step["range"], fps=step["fps"],
                  combo_step=combo_index + 1, facing=direction, crit=crit)

        state["combo_index"] = (combo_index + 1) % len(COMBO_STEPS)

    def request_attack(is_moving, is_sprinting):
        """Keep clicks made near the end of recovery instead of dropping them."""
        if state.get("deaths_dance") or state.get("sonic_stream"):
            return
        now = pygame.time.get_ticks()
        if is_dash_attack_window():
            do_attack(is_moving, is_sprinting)
            return
        remaining = (last_attack_time + state["current_recovery"]) - now
        if remaining > 0:
            if remaining <= 190:
                state["buffered_attack_until"] = now + 260
            return
        do_attack(is_moving, is_sprinting)

    def try_focus():
        now = pygame.time.get_ticks()
        if now - state["last_focus_time"] < FOCUS_COOLDOWN:
            return
        if state["stamina"] >= max_stamina - 1:
            add_log("Stamina already full", DIM_TEXT)
            return
        state["last_focus_time"] = now
        restored = min(FOCUS_RESTORE, max_stamina - state["stamina"])
        state["stamina"] += restored
        state["sprint_exhausted"] = False
        add_floater(f"+{int(restored)} STAMINA", hero_center(),
                    (105, 196, 238), size="small")

    def use_special():
        nonlocal last_attack_time
        now = pygame.time.get_ticks()
        elapsed = now - state["last_special_time"]
        if (state["result"] or state.get("sonic_stream")
                or elapsed < SPECIAL_COOLDOWN):
            if elapsed < SPECIAL_COOLDOWN:
                add_log(f"{SPECIAL_NAME} is recharging", DIM_TEXT)
            return
        if state["stamina"] < SPECIAL_COST:
            add_log("Not enough stamina for ability", YELLOW)
            return
        state["stamina"] -= SPECIAL_COST
        state["last_special_time"] = now
        last_attack_time = now
        state["stats"]["attacks"] += 1
        state["combo_index"] = 0
        state["last_combo_time"] = -100000
        state["current_recovery"] = (
            DEATHS_DANCE_DURATION if is_assassin else 820
        )
        if is_assassin:
            dash_vec = DIR_VECS.get(direction, (1, 0))
            state["deaths_dance"] = {
                "start": now,
                "direction": direction,
                "vec": dash_vec,
                "spin_done": set(),
                "eruption_done": set(),
                "landing_pos": None,
            }
            state["dashing"] = False
            state["invulnerable_until"] = now + DEATHS_DANCE_DURATION - 80
            play_dir("deaths_dance", _a_deaths_dance_rows, one_shot=True,
                     force=True, fps=9)
            add_log("DEATH'S DANCE: CRIMSON ERUPTION", (245, 48, 62))
            return
        else:
            last_special_damage = int(random.randint(45, 62) * damage_mult)
            last_special_damage, crit = roll_crit(
                last_special_damage,
                force_crit=state["hit_streak"] >= 8,
            )
            play_dir("attack", atk_combo_rows[2], one_shot=True,
                     force=True, fps=10)
            queue_hit(last_special_damage, knockback=24, atk_range=255,
                      fps=10, combo_step=3, facing=direction, crit=crit,
                      omni=False, special=True)
            wave_col = (230, 184, 88)
        state["shockwaves"].append({
            "pos": hero_center(), "start": now, "life": 650,
            "color": wave_col, "max_radius": 250 if is_assassin else 275,
            "omni": is_assassin, "facing": direction,
        })
        add_log(SPECIAL_NAME.upper(), wave_col)

    def use_sonic_stream():
        """Start the E-key lock-on dash and chained dagger barrage."""
        nonlocal last_attack_time, direction
        now = pygame.time.get_ticks()
        elapsed = now - state["last_sonic_stream_time"]
        if (state["result"] or not is_assassin or state.get("deaths_dance")
                or state.get("sonic_stream") or state["dashing"]):
            return
        if elapsed < SONIC_STREAM_COOLDOWN:
            add_log(f"{SONIC_STREAM_NAME} is recharging", DIM_TEXT)
            return
        if state["stamina"] < SONIC_STREAM_COST:
            add_log("Not enough stamina for Sonic Stream", YELLOW)
            return

        hx, hy = hero_center()
        living = [enemy for enemy in enemies if not enemy.dead]
        target = min(
            living,
            key=lambda enemy: math.hypot(
                enemy.center()[0] - hx, enemy.center()[1] - hy
            ),
            default=None,
        )
        if target is not None:
            tx, ty = target.center()
            target_dx, target_dy = tx - hx, ty - hy
            target_distance = math.hypot(target_dx, target_dy)
            if target_distance > 650:
                target = None
        if target is not None:
            tx, ty = target.center()
            target_dx, target_dy = tx - hx, ty - hy
            target_distance = max(1.0, math.hypot(target_dx, target_dy))
            travel_vec = (target_dx / target_distance, target_dy / target_distance)
            if abs(target_dx) >= abs(target_dy):
                direction = "right" if target_dx >= 0 else "left"
            else:
                direction = "down" if target_dy >= 0 else "up"
        else:
            travel_vec = DIR_VECS.get(direction, (1, 0))

        state["stamina"] -= SONIC_STREAM_COST
        state["last_sonic_stream_time"] = now
        last_attack_time = now
        state["stats"]["attacks"] += 1
        state["combo_index"] = 0
        state["last_combo_time"] = -100000
        state["current_recovery"] = SONIC_STREAM_DURATION
        state["sonic_stream"] = {
            "start": now,
            "direction": direction,
            "vec": travel_vec,
            "target": target,
            "strike_pos": None,
            "hit_done": set(),
            "wave_done": set(),
        }
        state["invulnerable_until"] = now + SONIC_STREAM_DURATION - 90
        play_dir(
            "sonic_stream", sonic_stream_rows,
            one_shot=True, force=True, fps=8.3,
        )
        add_log("SONIC STREAM", (245, 48, 62))

    def queue_hit(dmg, knockback, atk_range, fps, combo_step=None, facing=None,
                  crit=False, omni=False, special=False):
        # Land the hit partway through the swing (roughly the 3rd frame)
        # instead of the instant the mouse is clicked, so the damage
        # syncs up with the sword actually connecting on screen.
        delay = int(1000 / fps * 3)
        state["pending_hits"].append({
            "time": pygame.time.get_ticks() + delay,
            "dmg": dmg,
            "knockback": knockback,
            "range": atk_range,
            "combo_step": combo_step,
            "facing": facing,
            "crit": crit,
            "omni": omni,
            "special": special,
        })

    def resolve_attack_hit(dmg, knockback, atk_range, combo_step=None, facing=None,
                            crit=False, omni=False, special=False, origin=None,
                            quiet=False):
        state["last_hit_time"] = pygame.time.get_ticks()
        if is_assassin and combo_step:
            spawn_assassin_slash(
                facing, combo_step,
                duration=230 if combo_step == 3 else 175,
            )
        hx, hy = origin if origin is not None else hero_center()
        fvx, fvy = DIR_VECS.get(facing, (1, 0))
        hit_any = False
        hit_count = 0
        total_damage = 0
        for e in enemies:
            if e.dead:
                continue
            ex, ey = e.center()
            dnx, dny = ex - hx, ey - hy
            dist = (dnx * dnx + dny * dny) ** 0.5
            if dist > atk_range:
                continue
            if dist > 4 and not omni:
                dot = (dnx / dist) * fvx + (dny / dist) * fvy
                if dot < FACING_COS_THRESHOLD:
                    continue  # roughly behind the hero -- the swing doesn't reach
            stagger = 16 + knockback * 1.15 + (8 if combo_step == 3 else 0)
            if special:
                stagger += 18
            actual, killed = e.take_damage(dmg, stagger=stagger)
            if not actual:
                continue
            total_damage += actual
            hit_count += 1
            state["stats"]["damage_dealt"] += actual
            state["stats"]["hits"] += 1
            if crit:
                state["stats"]["crits"] += 1
            state["hit_streak"] += 1
            state["last_streak_time"] = pygame.time.get_ticks()
            state["best_streak"] = max(state["best_streak"], state["hit_streak"])
            number_col = (255, 92, 102) if crit else (245, 218, 150)
            add_floater(f"{actual}{'!' if crit else ''}", e.center(),
                        number_col, size="medium" if crit or combo_step == 3 else "small")
            if killed:
                state["stats"]["kills"] += 1
                add_floater("SLAIN", e.center(), GOLD_BRIGHT, size="medium", life=900)
                heal = run_state.get("heal_on_kill", 0)
                if heal:
                    recovered = min(heal, hero_max_hp - state["hero_hp"])
                    state["hero_hp"] += recovered
                    if recovered:
                        add_floater(f"+{recovered} HP", hero_center(),
                                    (108, 205, 124), life=800)
            if knockback:
                dnorm = max(1.0, dist)
                e.apply_knockback(dnx / dnorm, dny / dnorm, knockback)
            hit_any = True
        if hit_any:
            shake = 14 if combo_step == 3 else 8
            stop = HITSTOP_FINISHER if combo_step == 3 else HITSTOP_HIT
            if crit:
                shake += 6
                stop += 40
            state["shake"] = shake
            state["hitstop"] = stop

            if combo_step == 3:
                label = "FINISHER"
            elif combo_step:
                label = f"Hit {combo_step}"
            else:
                label = "Attack"

            if not quiet:
                if crit:
                    add_log(f"CRITICAL {label} - {total_damage}", RED)
                else:
                    suffix = f" x{hit_count}" if hit_count > 1 else ""
                    add_log(f"{label} - {total_damage}{suffix}",
                            GOLD if combo_step == 3 else GREEN)
        elif not quiet:
            add_log("Swing and a miss!", YELLOW)

    def spawn_eruption_fx(pos, eruption_index):
        """Create one persistent red ground burst for the Q finisher."""
        state["eruption_fx"].append({
            "pos": pos,
            "start": pygame.time.get_ticks(),
            "life": 620,
            "index": eruption_index,
        })

    def update_deaths_dance(now, frame_dt):
        """Advance the unique dash/spin hits and correctly anchored eruptions."""
        dance = state.get("deaths_dance")
        if not dance:
            return False

        elapsed = now - dance["start"]
        dx, dy = dance["vec"]

        # The opening spin carries Jinwoo forward like the reference clip.
        # Input movement is suspended during this travel so the direction
        # captured on Q remains readable and the finisher lands in one line.
        if elapsed < DEATHS_DANCE_TRAVEL_END and frame_dt > 0:
            progress = max(0.0, min(1.0, elapsed / DEATHS_DANCE_TRAVEL_END))
            speed_curve = 0.62 + math.sin(progress * math.pi) * 0.58
            step = DEATHS_DANCE_TRAVEL_SPEED * speed_curve * frame_dt / 16.667
            hero_pos[0] = max(
                0, min(STAGE_EXIT_X, hero_pos[0] + dx * step)
            )
            new_y = hero_pos[1] + dy * step
            if dy < 0 and new_y + FEET_OFFSET[hero_class] < TOP_BORDER_Y:
                new_y = TOP_BORDER_Y - FEET_OFFSET[hero_class]
            elif dy > 0:
                new_y = min(HEIGHT - FEET_OFFSET[hero_class], new_y)
            hero_pos[1] = new_y

        if elapsed >= DEATHS_DANCE_TRAVEL_END and dance["landing_pos"] is None:
            # Ground effects anchor to the feet, not the body-center position.
            # This is captured once, so later frames and camera shake cannot
            # make the eruption chain drift away from the actual landing spot.
            dance["landing_pos"] = (
                hero_center()[0],
                hero_pos[1] + FEET_OFFSET[hero_class],
            )

        # Three damage beats follow Jinwoo's unique horizontal spin and final
        # ground strike. The VFX is rendered separately in the red light-combo
        # palette; no LMB slash image is spawned here.
        for hit_index, hit_time in enumerate(DEATHS_DANCE_SPIN_TIMES):
            if elapsed < hit_time or hit_index in dance["spin_done"]:
                continue
            dance["spin_done"].add(hit_index)
            final_cut = hit_index == len(DEATHS_DANCE_SPIN_TIMES) - 1
            damage_range = (13, 18) if final_cut else (8, 12)
            dmg = int(random.randint(*damage_range) * damage_mult)
            dmg, crit = roll_crit(
                dmg,
                force_crit=final_cut and state["hit_streak"] >= 8,
            )
            resolve_attack_hit(
                dmg, knockback=12 if final_cut else 4 + hit_index * 2,
                atk_range=166 if final_cut else 150,
                facing=dance["direction"], crit=crit, omni=True,
                special=True, quiet=True,
            )
            if final_cut:
                state["shake"] = max(state["shake"], 12)

        # Restore the three advancing ground eruptions from the earlier Q.
        # Each owns its position, damage, and red animation frame sequence.
        landing_x, landing_y = dance["landing_pos"] or (
            hero_center()[0], hero_pos[1] + FEET_OFFSET[hero_class]
        )
        for eruption_index, eruption_time in enumerate(
                DEATHS_DANCE_ERUPTION_TIMES):
            if (elapsed < eruption_time
                    or eruption_index in dance["eruption_done"]):
                continue
            dance["eruption_done"].add(eruption_index)
            # Burst one is exactly at the landing point. Bursts two and three
            # continue forward from that fixed origin.
            distance = eruption_index * 78
            pos = (landing_x + dx * distance, landing_y + dy * distance)
            spawn_eruption_fx(pos, eruption_index)
            dmg = int(random.randint(13, 18) * damage_mult)
            dmg, crit = roll_crit(
                dmg,
                force_crit=(eruption_index == 2 and state["hit_streak"] >= 8),
            )
            resolve_attack_hit(
                dmg, knockback=10 + eruption_index * 4,
                atk_range=92 + eruption_index * 5,
                facing=dance["direction"], crit=crit, omni=True,
                special=True, origin=pos, quiet=True,
            )
            state["shake"] = max(state["shake"], 9 + eruption_index * 3)

        if elapsed >= DEATHS_DANCE_DURATION:
            state["deaths_dance"] = None
        return True

    def update_sonic_stream(now, frame_dt):
        """Advance Sonic Stream's lock-on entry, barrage, and fire wave."""
        sonic = state.get("sonic_stream")
        if not sonic:
            return False

        elapsed = now - sonic["start"]
        dx, dy = sonic["vec"]

        # The reference move first snaps Jinwoo into dagger range.  If an
        # enemy was close enough when E was pressed, travel ends just before
        # its center; otherwise Sonic Stream fires in the captured direction.
        if (elapsed < SONIC_STREAM_DASH_END and frame_dt > 0
                and sonic["strike_pos"] is None):
            target = sonic.get("target")
            if target is not None and not target.dead:
                tx, ty = target.center()
                hx, hy = hero_center()
                toward_x, toward_y = tx - hx, ty - hy
                distance = math.hypot(toward_x, toward_y)
                if distance > 112:
                    dx, dy = toward_x / distance, toward_y / distance
                    sonic["vec"] = (dx, dy)
                    step = min(
                        distance - 112,
                        SONIC_STREAM_DASH_SPEED * frame_dt / 16.667,
                    )
                else:
                    step = 0
                    sonic["strike_pos"] = hero_center()
            else:
                step = SONIC_STREAM_DASH_SPEED * frame_dt / 16.667

            hero_pos[0] = max(0, min(STAGE_EXIT_X, hero_pos[0] + dx * step))
            new_y = hero_pos[1] + dy * step
            if dy < 0 and new_y + FEET_OFFSET[hero_class] < TOP_BORDER_Y:
                new_y = TOP_BORDER_Y - FEET_OFFSET[hero_class]
            elif dy > 0:
                new_y = min(HEIGHT - FEET_OFFSET[hero_class], new_y)
            hero_pos[1] = new_y

        if elapsed >= SONIC_STREAM_DASH_END and sonic["strike_pos"] is None:
            sonic["strike_pos"] = hero_center()

        strike_pos = sonic["strike_pos"] or hero_center()

        # Five tight cuts happen around the target without reusing any LMB or
        # Death's Dance slash asset.  The last barrage hit is the launch into
        # the large finishing sweep.
        for hit_index, hit_time in enumerate(SONIC_STREAM_HIT_TIMES):
            if elapsed < hit_time or hit_index in sonic["hit_done"]:
                continue
            sonic["hit_done"].add(hit_index)
            final_barrage = hit_index == len(SONIC_STREAM_HIT_TIMES) - 1
            damage_range = (12, 17) if final_barrage else (6, 10)
            dmg = int(random.randint(*damage_range) * damage_mult)
            dmg, crit = roll_crit(
                dmg,
                force_crit=final_barrage and state["hit_streak"] >= 8,
            )
            resolve_attack_hit(
                dmg,
                knockback=10 if final_barrage else 3,
                atk_range=190 if final_barrage else 166,
                facing=sonic["direction"],
                crit=crit,
                omni=True,
                special=True,
                origin=strike_pos,
                quiet=True,
            )
            state["shake"] = max(
                state["shake"], 12 if final_barrage else 5 + hit_index
            )

        # The finishing cut launches the same advancing fire line shown in the
        # reference clip.  Each beat owns a forward world position so damage
        # and visuals cannot drift back underneath Jinwoo.
        for wave_index, wave_time in enumerate(SONIC_STREAM_WAVE_TIMES):
            if elapsed < wave_time or wave_index in sonic["wave_done"]:
                continue
            sonic["wave_done"].add(wave_index)
            distance = 76 + wave_index * 92
            origin = (
                strike_pos[0] + dx * distance,
                strike_pos[1] + dy * distance,
            )
            final_wave = wave_index == len(SONIC_STREAM_WAVE_TIMES) - 1
            damage_range = (18, 26) if final_wave else (9, 14)
            dmg = int(random.randint(*damage_range) * damage_mult)
            dmg, crit = roll_crit(
                dmg,
                force_crit=final_wave and state["hit_streak"] >= 8,
            )
            resolve_attack_hit(
                dmg,
                knockback=24 if final_wave else 10 + wave_index * 4,
                atk_range=112 + wave_index * 7,
                facing=sonic["direction"],
                crit=crit,
                omni=True,
                special=True,
                origin=origin,
                quiet=True,
            )
            state["shake"] = max(state["shake"], 11 + wave_index * 3)

        if elapsed >= SONIC_STREAM_DURATION:
            state["sonic_stream"] = None
        return True

    def draw_deaths_dance_vfx(now, dance):
        """Render the ARISE-style dash/spin using Jinwoo's crimson palette.

        This is unique Q choreography: accelerating dash streaks, a horizontal
        multi-ring spin, then one large rotating ground-strike crescent. It
        shares the normal attacks' layered red/white visual language without
        drawing or recoloring any of their three slash images.
        """
        elapsed = now - dance["start"]
        dx, dy = dance["vec"]
        side_x, side_y = -dy, dx
        world_cx = hero_center()[0] + ox
        world_cy = hero_center()[1] + oy + 12

        fx_w, fx_h = 540, 420
        cx, cy = fx_w // 2, fx_h // 2
        fx = pygame.Surface((fx_w, fx_h), pygame.SRCALPHA)

        def orbit_points(rx, ry, tip_angle, span, steps=30):
            return [
                (
                    int(cx + math.cos(tip_angle - span + span * i / steps) * rx),
                    int(cy + math.sin(tip_angle - span + span * i / steps) * ry),
                )
                for i in range(steps + 1)
            ]

        def curve_points(start, control, end, steps=24):
            points = []
            for i in range(steps + 1):
                t = i / steps
                inv = 1.0 - t
                points.append((
                    int(inv * inv * start[0] + 2 * inv * t * control[0]
                        + t * t * end[0]),
                    int(inv * inv * start[1] + 2 * inv * t * control[1]
                        + t * t * end[1]),
                ))
            return points

        def draw_red_ribbon(points, alpha, strength=1.0, echo=False):
            """Use the same aura -> crimson -> hot edge -> white core stack."""
            if alpha <= 0 or len(points) < 2:
                return
            layers = (
                ((76, 0, 18), 27, 0.33),
                ((150, 0, 24), 18, 0.60),
                ((235, 16, 43), 11, 0.91),
                ((255, 70, 88), 7, 1.00),
                ((255, 155, 165), 4, 1.00),
            )
            if echo:
                layers = layers[:3]
            segment_count = len(points) - 1
            for color, base_width, opacity in layers:
                for index, (p1, p2) in enumerate(zip(points, points[1:])):
                    phase = (index + 0.5) / segment_count
                    taper = max(0.14, math.sin(phase * math.pi) ** 0.45)
                    width = max(1, int(base_width * strength * taper))
                    layer_alpha = min(255, int(alpha * opacity
                                               * (0.70 + phase * 0.30)))
                    pygame.draw.line(fx, (*color, layer_alpha), p1, p2, width)
            if not echo:
                pygame.draw.aalines(
                    fx, (255, 240, 242, min(255, int(alpha * 0.96))),
                    False, points,
                )

        def draw_shard(px, py, angle, length, width, alpha):
            ux, uy = math.cos(angle), math.sin(angle)
            nx, ny = -uy, ux
            points = [
                (int(px + ux * length), int(py + uy * length)),
                (int(px + nx * width), int(py + ny * width)),
                (int(px - ux * length * 0.58), int(py - uy * length * 0.58)),
                (int(px - nx * width), int(py - ny * width)),
            ]
            pygame.draw.polygon(fx, (255, 34, 57, max(0, int(alpha))), points)

        # Red speed ribbons carry Jinwoo into the spin without borrowing a
        # light-attack pose or slash image.
        if 18 <= elapsed < 430:
            dash_t = (elapsed - 18) / 412.0
            dash_fade = min(1.0, dash_t * 5.0) * (1.0 - dash_t) ** 0.66
            for trail_index, lateral in enumerate((-27, 0, 27)):
                trail = []
                length = 172 - trail_index * 12
                gap = 20 + trail_index * 5
                for point_index in range(16):
                    t = point_index / 15.0
                    along = -length + (length - gap) * t
                    curl = math.sin(t * math.pi) * (10 - trail_index * 2)
                    lateral_now = lateral * (1.0 - t * 0.36) + curl
                    trail.append((
                        int(cx + dx * along + side_x * lateral_now),
                        int(cy + dy * along + side_y * lateral_now * 0.58),
                    ))
                draw_red_ribbon(
                    trail,
                    int((205 - trail_index * 28) * dash_fade),
                    0.62 - trail_index * 0.08,
                    echo=trail_index > 0,
                )

        # ARISE reference: Jinwoo rotates horizontally while advancing. Three
        # broken elliptical ribbons overlap without becoming one opaque hoop.
        if 62 <= elapsed < 590:
            spin_t = (elapsed - 62) / 528.0
            spin_fade = min(1.0, spin_t * 5.5) * (1.0 - spin_t) ** 0.34
            facing_angle = math.atan2(dy, dx)
            tip_angle = facing_angle + spin_t * math.tau * 2.35
            ring_specs = (
                (146, 62, 4.05, 1.00, 1.00, 0.00),
                (130, 52, 3.45, 0.72, 0.76, -0.42),
                (114, 44, 2.90, 0.48, 0.62, -0.78),
            )
            for ring_index, (rx, ry, span, opacity, strength, delay) in enumerate(
                    ring_specs):
                points = orbit_points(rx, ry, tip_angle + delay, span, 30)
                draw_red_ribbon(
                    points,
                    int(250 * spin_fade * opacity),
                    strength,
                    echo=ring_index > 0,
                )

                # Small torn fragments trail the leading blade edge, matching
                # the texture of the approved red normal attacks.
                tip_x, tip_y = points[-1]
                tangent = tip_angle + delay + math.pi / 2
                for shard_index in range(3 if ring_index == 0 else 2):
                    distance = 12 + shard_index * 10 + ring_index * 4
                    sx = tip_x - math.cos(tangent) * distance
                    sy = tip_y - math.sin(tangent) * distance * 0.55
                    draw_shard(
                        sx, sy, tangent - 0.12 * shard_index,
                        5 + shard_index * 3, 1 + shard_index,
                        185 * spin_fade * opacity,
                    )

            # Each actual spin hit gets a short white-hot contact star.
            for hit_index, hit_time in enumerate(DEATHS_DANCE_SPIN_TIMES[:2]):
                hit_age = elapsed - hit_time
                if not 0 <= hit_age < 82:
                    continue
                flash = (1.0 - hit_age / 82.0) ** 0.72
                angle = facing_angle + (hit_time - 62) / 528.0 * math.tau * 2.35
                impact = (
                    int(cx + math.cos(angle) * 146),
                    int(cy + math.sin(angle) * 62),
                )
                for ray in range(4):
                    ray_angle = angle + ray * math.pi / 2 + 0.28
                    ray_len = (13 + ray * 5) * flash
                    pygame.draw.line(
                        fx, (255, 164, 174, int(225 * flash)), impact,
                        (int(impact[0] + math.cos(ray_angle) * ray_len),
                         int(impact[1] + math.sin(ray_angle) * ray_len)),
                        3 if ray < 2 else 2,
                    )

        # ARISE reference payoff: the horizontal rotation rises into one large
        # red crescent, then drives down at the exact landing point.
        if 430 <= elapsed < 710:
            strike_t = (elapsed - 430) / 280.0
            extend = 1.0 - (1.0 - min(1.0, strike_t * 1.7)) ** 3
            strike_fade = (min(1.0, strike_t * 6.0)
                           if strike_t < 0.58
                           else max(0.0, (1.0 - strike_t) / 0.42))
            reach = 74 + 92 * extend
            sweep = 78 + 48 * extend
            start = (
                cx - dx * 74 - side_x * sweep,
                cy - dy * 74 - side_y * sweep,
            )
            control = (
                cx + dx * 36 - side_x * (110 + 28 * extend),
                cy + dy * 36 - side_y * (110 + 28 * extend),
            )
            end = (
                cx + dx * reach + side_x * (28 + 35 * extend),
                cy + dy * reach + side_y * (28 + 35 * extend),
            )
            strike = curve_points(start, control, end, 28)
            echo = [(int(x - dx * 12 - side_x * 7),
                     int(y - dy * 12 - side_y * 7)) for x, y in strike]
            draw_red_ribbon(echo, int(105 * strike_fade), 1.08, echo=True)
            draw_red_ribbon(strike, int(255 * strike_fade), 1.18)

            tip_x, tip_y = strike[-1]
            for shard_index in range(10):
                spread = (shard_index - 4.5) * 0.13
                shard_angle = math.atan2(dy, dx) + spread
                distance = 14 + (shard_index % 4) * 10 + 22 * extend
                draw_shard(
                    tip_x - math.cos(shard_angle) * distance,
                    tip_y - math.sin(shard_angle) * distance * 0.62,
                    shard_angle,
                    6 + (shard_index % 4) * 3,
                    1 + (shard_index % 3),
                    220 * strike_fade,
                )

            impact_age = elapsed - DEATHS_DANCE_SPIN_TIMES[-1]
            if 0 <= impact_age < 115:
                impact = (1.0 - impact_age / 115.0) ** 0.68
                impact_x = cx + dx * 76
                impact_y = cy + dy * 76
                for ray_index in range(8):
                    angle = ray_index * math.pi / 4
                    ray_len = (22 + (ray_index % 3) * 11) * impact
                    pygame.draw.line(
                        fx, (255, 86, 104, int(215 * impact)),
                        (int(impact_x), int(impact_y)),
                        (int(impact_x + math.cos(angle) * ray_len),
                         int(impact_y + math.sin(angle) * ray_len * 0.62)),
                        3,
                    )
                pygame.draw.circle(
                    fx, (255, 244, 244, int(250 * impact)),
                    (int(impact_x), int(impact_y)), max(2, int(6 * impact)),
                )

        fx_rect = fx.get_rect(center=(world_cx, world_cy))
        bloom = fx.copy()
        bloom.set_alpha(82)
        screen.blit(bloom, fx_rect, special_flags=pygame.BLEND_RGBA_ADD)
        screen.blit(fx, fx_rect)
        return
        elapsed = now - dance["start"]
        dx, dy = dance["vec"]
        side_x, side_y = -dy, dx
        world_cx = hero_center()[0] + ox
        world_cy = hero_center()[1] + oy + 14

        fx_w, fx_h = 520, 390
        cx, cy = fx_w // 2, fx_h // 2
        fx = pygame.Surface((fx_w, fx_h), pygame.SRCALPHA)

        def arc_points(rx, ry, tip_angle, span, steps=20):
            """Return a pointed elliptical ribbon ending at tip_angle."""
            return [
                (
                    int(cx + math.cos(tip_angle - span + span * i / steps) * rx),
                    int(cy + math.sin(tip_angle - span + span * i / steps) * ry),
                )
                for i in range(steps + 1)
            ]

        def quadratic_points(start, control, end, steps=18):
            points = []
            for i in range(steps + 1):
                t = i / steps
                inv = 1.0 - t
                points.append((
                    int(inv * inv * start[0] + 2 * inv * t * control[0]
                        + t * t * end[0]),
                    int(inv * inv * start[1] + 2 * inv * t * control[1]
                        + t * t * end[1]),
                ))
            return points

        def draw_ribbon(points, alpha, strength=1.0, echo=False):
            """Layer one tapered energy cut like Jinwoo's red dagger trails."""
            if alpha <= 0 or len(points) < 2:
                return
            layers = (
                ((38, 0, 82), 25, 0.34),
                ((86, 3, 180), 17, 0.58),
                ((166, 12, 246), 11, 0.86),
                ((236, 35, 255), 7, 1.00),
                ((255, 126, 255), 4, 1.00),
            )
            if echo:
                layers = layers[:3]
            segment_count = len(points) - 1
            for color, base_width, opacity in layers:
                for index, (p1, p2) in enumerate(zip(points, points[1:])):
                    phase = (index + 0.5) / segment_count
                    taper = max(0.16, math.sin(phase * math.pi) ** 0.46)
                    width = max(1, int(base_width * strength * taper))
                    layer_alpha = int(alpha * opacity * (0.72 + 0.28 * phase))
                    pygame.draw.line(fx, (*color, min(255, layer_alpha)),
                                     p1, p2, width)
            if not echo:
                pygame.draw.aalines(
                    fx, (255, 239, 255, min(255, int(alpha * 0.96))),
                    False, points,
                )

        def draw_fragment(px, py, angle, length, width, color):
            ux, uy = math.cos(angle), math.sin(angle)
            nx, ny = -uy, ux
            points = [
                (int(px + ux * length), int(py + uy * length)),
                (int(px + nx * width), int(py + ny * width)),
                (int(px - ux * length * 0.62), int(py - uy * length * 0.62)),
                (int(px - nx * width), int(py - ny * width)),
            ]
            pygame.draw.polygon(fx, color, points)

        # Opening dash: three curved dagger-speed ribbons. They are pointed,
        # layered strokes rather than a recolored light-attack sprite.
        if 18 <= elapsed < 390:
            dash_t = (elapsed - 18) / 372.0
            dash_fade = min(1.0, dash_t * 5.2) * (1.0 - dash_t) ** 0.62
            for trail_index, lateral in enumerate((-31, 0, 30)):
                points = []
                length = 176 - trail_index * 13
                gap = 21 + trail_index * 5
                for point_index in range(15):
                    t = point_index / 14.0
                    along = -length + (length - gap) * t
                    curl = math.sin(t * math.pi) * (11 - trail_index * 2)
                    wobble = math.sin(dash_t * math.tau * 1.8
                                      + trail_index * 1.7) * (1.0 - t) * 5
                    lateral_now = lateral * (1.0 - t * 0.34) + curl + wobble
                    points.append((
                        int(cx + dx * along + side_x * lateral_now),
                        int(cy + dy * along + side_y * lateral_now * 0.58),
                    ))
                alpha = int((205 - trail_index * 26) * dash_fade)
                draw_ribbon(points, alpha, 0.62 - trail_index * 0.08)

                # Broken flecks give the dash the same sharp, energized edge
                # as the normal attacks without forming a purple fog.
                for fleck in range(3):
                    phase = 0.20 + fleck * 0.23
                    px, py = points[int(phase * (len(points) - 1))]
                    px += int(side_x * (7 + fleck * 4) * (-1 if fleck % 2 else 1))
                    py += int(side_y * (7 + fleck * 4) * (-1 if fleck % 2 else 1))
                    draw_fragment(
                        px, py, math.atan2(dy, dx) + 0.18 * (fleck - 1),
                        5 + fleck * 2, 1 + fleck // 2,
                        (220, 27, 255, int(alpha * 0.72)),
                    )

        # Four twin-dagger spin beats. Each beat has one dominant blade ribbon,
        # a shorter counter-cut and two delayed echoes, so it reads as a rapid
        # dance rather than one circular aura around Jinwoo.
        facing_angle = math.atan2(dy, dx)
        for cut_index, hit_time in enumerate(DEATHS_DANCE_SPIN_TIMES):
            cut_age = elapsed - (hit_time - 92)
            cut_life = 245 if cut_index == 3 else 220
            if not 0 <= cut_age < cut_life:
                continue
            t = cut_age / cut_life
            ease = 1.0 - (1.0 - t) ** 3
            fade = math.sin(t * math.pi) ** 0.48
            spin_sign = 1 if cut_index % 2 == 0 else -1
            tip_angle = (
                facing_angle + cut_index * 0.72
                + spin_sign * (-0.48 + ease * 2.75)
            )
            span = 1.02 + 0.40 * math.sin(t * math.pi)
            rx = 139 + cut_index * 7 + int(13 * ease)
            ry = 62 + cut_index * 3 + int(7 * ease)
            alpha = int(255 * fade)

            # Fast delayed copies supply motion without hiding the character.
            for echo_index, echo_offset in enumerate((0.34, 0.18), start=1):
                echo_tip = tip_angle - spin_sign * echo_offset
                echo_points = arc_points(
                    rx - echo_index * 7, ry - echo_index * 3,
                    echo_tip,
                    spin_sign * (span * (0.76 - echo_index * 0.08)),
                    15,
                )
                draw_ribbon(
                    echo_points,
                    int(alpha * (0.20 + echo_index * 0.09)),
                    0.72 - echo_index * 0.08,
                    echo=True,
                )

            primary = arc_points(rx, ry, tip_angle, spin_sign * span, 22)
            draw_ribbon(primary, alpha, 1.0)

            counter_tip = tip_angle + math.pi - spin_sign * 0.20
            counter = arc_points(
                rx - 31, ry - 13, counter_tip,
                -spin_sign * (span * 0.66), 16,
            )
            draw_ribbon(counter, int(alpha * 0.74), 0.76)

            # Deterministic torn fragments at both dagger tips keep every
            # recorded frame stable while matching the normal attacks' debris.
            for blade_index, (tip, radius_x, radius_y) in enumerate((
                    (tip_angle, rx, ry),
                    (counter_tip, rx - 31, ry - 13))):
                tip_x = cx + math.cos(tip) * radius_x
                tip_y = cy + math.sin(tip) * radius_y
                tangent = tip + (math.pi / 2) * (spin_sign if blade_index == 0 else -spin_sign)
                for shard_index in range(5 if blade_index == 0 else 3):
                    spread = (shard_index - 2) * 0.12
                    distance = 13 + shard_index * 8 + ease * 18
                    sx = tip_x - math.cos(tangent + spread) * distance
                    sy = tip_y - math.sin(tangent + spread) * distance * 0.58
                    draw_fragment(
                        sx, sy, tangent + spread,
                        5 + shard_index * 1.7,
                        1 + shard_index * 0.36,
                        (231, 37 + shard_index * 10, 255,
                         int((190 - shard_index * 19) * fade)),
                    )

            # A very brief blade-contact star marks each damage beat. No ring,
            # ground circle, or reused left-click impact is involved.
            impact_age = elapsed - hit_time
            if 0 <= impact_age < 82:
                impact_fade = (1.0 - impact_age / 82.0) ** 0.7
                impact_x, impact_y = primary[-1]
                for ray_index in range(4):
                    angle = tip_angle + ray_index * math.pi / 2 + 0.38
                    ray_len = (13 + ray_index * 5) * impact_fade
                    end = (int(impact_x + math.cos(angle) * ray_len),
                           int(impact_y + math.sin(angle) * ray_len))
                    pygame.draw.line(
                        fx, (255, 178, 255, int(225 * impact_fade)),
                        (impact_x, impact_y), end,
                        3 if ray_index < 2 else 2,
                    )
                pygame.draw.circle(
                    fx, (255, 246, 255, int(250 * impact_fade)),
                    (impact_x, impact_y), max(1, int(4 * impact_fade)),
                )

        # The fourth hit resolves into two long, curved crossing dagger cuts.
        # Their layered edge and fracture burst mirror the quality of the red
        # combo finisher, while the preceding four-orbit dance stays unique.
        if 610 <= elapsed < 890:
            finish_t = (elapsed - 610) / 280.0
            extend = 1.0 - (1.0 - min(1.0, finish_t * 1.62)) ** 3
            fade = 1.0 if finish_t < 0.54 else max(0.0, (1.0 - finish_t) / 0.46)
            half_len = 52 + int(139 * extend)
            half_w = 18 + int(52 * extend)
            front_shift = 18 + int(34 * extend)
            cross_cx = cx + dx * front_shift
            cross_cy = cy + dy * front_shift * 0.55

            for slash_index, sign in enumerate((-1, 1)):
                start = (
                    cross_cx - dx * half_len - side_x * half_w * sign,
                    cross_cy - dy * half_len - side_y * half_w * sign,
                )
                end = (
                    cross_cx + dx * half_len + side_x * half_w * sign,
                    cross_cy + dy * half_len + side_y * half_w * sign,
                )
                control = (
                    cross_cx + side_x * sign * (22 + slash_index * 8),
                    cross_cy + side_y * sign * (22 + slash_index * 8),
                )
                points = quadratic_points(start, control, end, 24)
                alpha = int((255 - slash_index * 18) * fade)
                draw_ribbon(points, int(alpha * 0.25), 1.34, echo=True)
                draw_ribbon(points, alpha, 1.08)

            burst = max(0.0, 1.0 - abs(finish_t - 0.42) / 0.23)
            if burst > 0:
                for shard_index in range(18):
                    angle = shard_index * math.tau / 18 + 0.17 * (shard_index % 3)
                    distance = 22 + (shard_index % 5) * 11 + 24 * extend
                    sx = cross_cx + math.cos(angle) * distance
                    sy = cross_cy + math.sin(angle) * distance * 0.57
                    draw_fragment(
                        sx, sy, angle,
                        6 + (shard_index % 4) * 3,
                        1.2 + (shard_index % 3),
                        (235, 34 + (shard_index % 3) * 30, 255,
                         int(205 * burst)),
                    )
                for ray_index in range(8):
                    angle = ray_index * math.pi / 4
                    ray_len = (26 + (ray_index % 3) * 14) * burst
                    pygame.draw.line(
                        fx, (255, 152, 255, int(210 * burst)),
                        (int(cross_cx), int(cross_cy)),
                        (int(cross_cx + math.cos(angle) * ray_len),
                         int(cross_cy + math.sin(angle) * ray_len * 0.62)),
                        3,
                    )
                pygame.draw.circle(
                    fx, (255, 247, 255, int(250 * burst)),
                    (int(cross_cx), int(cross_cy)), max(2, int(6 * burst)),
                )

        fx_rect = fx.get_rect(center=(world_cx, world_cy))
        bloom = fx.copy()
        bloom.set_alpha(88)
        screen.blit(bloom, fx_rect, special_flags=pygame.BLEND_RGBA_ADD)
        screen.blit(fx, fx_rect)

    def draw_sonic_stream_vfx(now, sonic):
        """Draw the ARISE-inspired Sonic Stream without reusing Q/LMB art."""
        elapsed = now - sonic["start"]
        dx, dy = sonic["vec"]
        length = max(0.001, math.hypot(dx, dy))
        dx, dy = dx / length, dy / length
        side_x, side_y = -dy, dx
        anchor = sonic["strike_pos"] or hero_center()

        fx_w, fx_h = 760, 560
        cx, cy = fx_w // 2, fx_h // 2
        fx = pygame.Surface((fx_w, fx_h), pygame.SRCALPHA)

        def draw_fire_stroke(points, alpha, strength=1.0, echo=False):
            """Use Q's exact aura -> crimson -> hot edge -> pale core stack."""
            if alpha <= 0 or len(points) < 2:
                return
            layers = (
                ((76, 0, 18), 27, 0.33),
                ((150, 0, 24), 18, 0.60),
                ((235, 16, 43), 11, 0.91),
                ((255, 70, 88), 7, 1.00),
                ((255, 155, 165), 4, 1.00),
            )
            if echo:
                layers = layers[:3]
            segment_count = len(points) - 1
            for color, base_width, opacity in layers:
                for index, (start, end) in enumerate(zip(points, points[1:])):
                    phase = (index + 0.5) / segment_count
                    taper = max(0.14, math.sin(phase * math.pi) ** 0.45)
                    width = max(1, int(base_width * strength * taper))
                    layer_alpha = min(
                        255,
                        int(alpha * opacity * (0.70 + phase * 0.30)),
                    )
                    pygame.draw.line(
                        fx, (*color, layer_alpha), start, end, width,
                    )
            if not echo:
                pygame.draw.aalines(
                    fx, (255, 240, 242, min(255, int(alpha * 0.96))),
                    False, points,
                )

        def draw_impact_flare(point, strength, rotation=0.0):
            """Layered red hit-flash with a hot core and expanding ring."""
            if strength <= 0:
                return
            px, py = point
            outer_radius = max(3, int(34 * strength))
            pygame.draw.circle(
                fx, (76, 0, 18, int(84 * strength)),
                (px, py), outer_radius,
            )
            pygame.draw.circle(
                fx, (235, 16, 43, int(205 * strength)),
                (px, py), max(2, int(22 * strength)),
                max(1, int(3 * strength)),
            )
            pygame.draw.circle(
                fx, (255, 70, 88, int(245 * strength)),
                (px, py), max(2, int(11 * strength)),
            )
            for ray_index in range(8):
                angle = rotation + ray_index * math.pi / 4
                ray_len = (22 + (ray_index % 2) * 18) * strength
                ray_start = 5 * strength
                start = (
                    int(px + math.cos(angle) * ray_start),
                    int(py + math.sin(angle) * ray_start * 0.72),
                )
                end = (
                    int(px + math.cos(angle) * ray_len),
                    int(py + math.sin(angle) * ray_len * 0.72),
                )
                pygame.draw.line(
                    fx, (255, 86, 104, int(225 * strength)),
                    start, end, max(1, int(3 * strength)),
                )
            pygame.draw.circle(
                fx, (255, 244, 244, min(255, int(255 * strength))),
                (px, py), max(2, int(5 * strength)),
            )

        def draw_crimson_shard(forward, sideways, angle, length, alpha):
            """A compact motion fragment that reads as shattered blade-light."""
            px, py = local_point(forward, sideways)
            tip_x = px + math.cos(angle) * length
            tip_y = py + math.sin(angle) * length * 0.72
            wing_x = math.cos(angle + math.pi * 0.5) * length * 0.14
            wing_y = math.sin(angle + math.pi * 0.5) * length * 0.10
            points = [
                (int(px - wing_x), int(py - wing_y)),
                (int(tip_x), int(tip_y)),
                (int(px + wing_x), int(py + wing_y)),
            ]
            pygame.draw.polygon(fx, (150, 0, 24, int(alpha * 0.48)), points)
            pygame.draw.line(
                fx, (255, 34, 57, alpha),
                (px, py), (int(tip_x), int(tip_y)), 2,
            )
            pygame.draw.line(
                fx, (255, 155, 165, min(255, int(alpha * 0.76))),
                (px, py), (int(tip_x), int(tip_y)), 1,
            )

        def local_point(forward, sideways):
            return (
                int(cx + dx * forward + side_x * sideways),
                int(cy + dy * forward + side_y * sideways * 0.72),
            )

        # Entry dash: several thin converging streaks, not the circular Q spin.
        if elapsed < SONIC_STREAM_DASH_END + 70:
            dash_t = min(1.0, elapsed / (SONIC_STREAM_DASH_END + 70))
            fade = min(1.0, dash_t * 5.0) * (1.0 - dash_t) ** 0.45
            for trail_index, lateral in enumerate((-42, -15, 16, 43)):
                points = []
                for point_index in range(16):
                    t = point_index / 15.0
                    forward = -245 + 228 * t
                    sideways = lateral * (1.0 - t * 0.62)
                    sideways += math.sin(t * math.pi) * (8 - trail_index)
                    points.append(local_point(forward, sideways))
                draw_fire_stroke(
                    points,
                    int((210 - trail_index * 22) * fade),
                    0.58 - trail_index * 0.045,
                    echo=trail_index > 1,
                )
            # Crimson fragments peel away from the converging dash lanes. Their
            # positions are deterministic so the effect never flickers.
            for spark_index in range(14):
                phase = spark_index / 13.0
                spark_forward = -226 + phase * 205
                spark_side = math.sin(
                    spark_index * 2.18 + elapsed * 0.014
                ) * (18 + (spark_index % 4) * 7) * (1.0 - phase * 0.54)
                spark_angle = math.atan2(dy, dx) + math.pi
                spark_angle += (spark_index % 3 - 1) * 0.18
                draw_crimson_shard(
                    spark_forward,
                    spark_side,
                    spark_angle,
                    (9 + spark_index % 5 * 3) * fade,
                    int((135 + spark_index % 4 * 22) * fade),
                )

        # The central Sonic Stream: alternating diagonal cuts build a dense
        # star around the target while leaving Jinwoo readable at its center.
        for cut_index, hit_time in enumerate(SONIC_STREAM_HIT_TIMES):
            age = elapsed - (hit_time - 95)
            life = 235
            if not 0 <= age < life:
                continue
            t = age / life
            fade = math.sin(t * math.pi) ** 0.42
            extend = 1.0 - (1.0 - min(1.0, t * 1.75)) ** 3
            sign = -1 if cut_index % 2 else 1
            reach = 82 + 105 * extend + cut_index * 5
            across = 75 + 58 * extend
            points = []
            for point_index in range(23):
                phase = point_index / 22.0
                forward = -reach + reach * 2 * phase
                sideways = sign * across * (1.0 - phase * 2)
                sideways += math.sin(phase * math.pi) * sign * 24
                points.append(local_point(forward, sideways))
            echo = [
                (int(x - dx * 11 - side_x * sign * 8),
                 int(y - dy * 11 - side_y * sign * 8))
                for x, y in points
            ]
            far_echo = [
                (int(x - dx * 19 + side_x * sign * 13),
                 int(y - dy * 19 + side_y * sign * 13))
                for x, y in points
            ]
            draw_fire_stroke(far_echo, int(62 * fade), 0.48, echo=True)
            draw_fire_stroke(echo, int(92 * fade), 0.78, echo=True)
            draw_fire_stroke(points, int(255 * fade), 1.0)

            # Small red splinters continue the cut beyond its clean main arc.
            cut_angle = math.atan2(dy, dx) - sign * 0.62
            for shard_index in range(5):
                shard_phase = shard_index / 4.0
                draw_crimson_shard(
                    -70 + shard_phase * 170 + cut_index * 4,
                    sign * (-72 + shard_index * 27),
                    cut_angle + (shard_index - 2) * 0.11,
                    (12 + shard_index * 4) * fade,
                    int((122 + shard_index * 20) * fade),
                )

            impact_age = elapsed - hit_time
            if 0 <= impact_age < 130:
                flash = (1.0 - impact_age / 130.0) ** 0.65
                impact = local_point(35 + cut_index * 7, sign * 16)
                draw_impact_flare(impact, flash, cut_index * 0.38)

        # One huge two-dagger sweep launches the ground fire line.
        if 820 <= elapsed < 1120:
            finish_t = (elapsed - 820) / 300.0
            fade = min(1.0, finish_t * 6.0)
            if finish_t > 0.60:
                fade *= max(0.0, (1.0 - finish_t) / 0.40)
            tip = math.atan2(dy, dx) + (-2.55 + finish_t * 3.25)
            points = []
            for index in range(33):
                phase = index / 32.0
                angle = tip - 3.75 + phase * 3.75
                radial_x = math.cos(angle) * 224
                radial_y = math.sin(angle) * 108
                points.append((
                    int(cx + dx * radial_x + side_x * radial_y),
                    int(cy + dy * radial_x + side_y * radial_y * 0.72),
                ))
            inner_points = []
            for x, y in points:
                inner_points.append((
                    int(cx + (x - cx) * 0.82 - dx * 8),
                    int(cy + (y - cy) * 0.82 - dy * 8),
                ))
            draw_fire_stroke(inner_points, int(142 * fade), 0.68, echo=True)
            draw_fire_stroke(points, int(255 * fade), 1.25)
            if 0.10 < finish_t < 0.78:
                pulse = math.sin(min(1.0, finish_t / 0.78) * math.pi)
                draw_impact_flare(
                    local_point(18, 0), pulse * fade,
                    finish_t * math.pi * 2,
                )
                for shard_index in range(12):
                    shard_angle = (
                        math.atan2(dy, dx) - 1.4
                        + shard_index * (2.8 / 11.0)
                    )
                    draw_crimson_shard(
                        22 + (shard_index % 4) * 21,
                        (shard_index - 5.5) * 13,
                        shard_angle,
                        (15 + shard_index % 4 * 6) * pulse,
                        int(210 * pulse * fade),
                    )

        # Three travelling ground bursts follow the finisher from the fixed
        # strike point.  Their flame tips lean forward like the reference.
        for wave_index, wave_time in enumerate(SONIC_STREAM_WAVE_TIMES):
            age = elapsed - wave_time
            if not 0 <= age < 360:
                continue
            t = age / 360.0
            fade = (1.0 - t) ** 0.48
            distance = 76 + wave_index * 92
            bx, by = local_point(distance, 0)
            radius = int((34 + wave_index * 8) * (0.55 + math.sin(t * math.pi)))
            pygame.draw.ellipse(
                fx,
                (150, 0, 24, int(100 * fade)),
                pygame.Rect(bx - radius, by - radius // 3,
                            radius * 2, max(8, radius // 2)),
            )
            pygame.draw.ellipse(
                fx,
                (235, 16, 43, int(190 * fade)),
                pygame.Rect(
                    bx - radius,
                    by - max(5, radius // 5),
                    radius * 2,
                    max(10, radius // 2),
                ),
                max(1, int(3 * fade)),
            )
            for spike_index in range(9):
                spread = (spike_index - 4) * 0.20
                spike_len = radius * (1.15 + (spike_index % 3) * 0.32)
                base_side = (spike_index - 4) * radius * 0.17
                base = (
                    int(bx + side_x * base_side),
                    int(by + side_y * base_side * 0.72),
                )
                tip_point = (
                    int(base[0] + dx * spike_len
                        + side_x * math.sin(spread) * spike_len * 0.48),
                    int(base[1] + dy * spike_len
                        + side_y * math.sin(spread) * spike_len * 0.34
                        - (18 + spike_index % 3 * 7) * fade),
                )
                pygame.draw.line(
                    fx, (235, 16, 43, int(190 * fade)),
                    base, tip_point, max(2, 7 - spike_index // 2),
                )
                pygame.draw.line(
                    fx, (255, 70, 88, int(235 * fade)),
                    base, tip_point, 3,
                )
                if spike_index % 2 == 0:
                    ember_angle = math.atan2(dy, dx) - 0.34 + spike_index * 0.08
                    draw_crimson_shard(
                        distance + 12 + spike_index * 5,
                        (spike_index - 4) * radius * 0.18,
                        ember_angle,
                        (12 + spike_index * 2) * fade,
                        int(215 * fade),
                    )
            pygame.draw.circle(
                fx, (255, 244, 244, int(245 * fade)),
                (bx, by), max(2, int(7 * fade)),
            )

        world_center = (anchor[0] + ox, anchor[1] + oy + 8)
        rect = fx.get_rect(center=world_center)
        bloom = fx.copy()
        bloom.set_alpha(82)
        screen.blit(bloom, rect, special_flags=pygame.BLEND_RGBA_ADD)
        screen.blit(fx, rect)

    while True:
        now = pygame.time.get_ticks()
        dt = min(now - last_time, 50)
        last_time = now

        if state["hitstop"] > 0:
            state["hitstop"] -= dt
        # While hitstop is active, movement/animation freeze for a beat --
        # everything else (cooldown timers, the pending-hit queue) still
        # runs on real time, so the freeze itself doesn't delay anything.
        effective_dt = 0 if state["hitstop"] > 0 else dt
        state["damage_flash"] = max(0, state["damage_flash"] - dt)
        if state["hit_streak"] and now - state["last_streak_time"] > 2600:
            state["hit_streak"] = 0

        keys = pygame.key.get_pressed()
        shift_held = keys[pygame.K_LSHIFT]

        if state["stamina"] <= 0:
            state["stamina"] = 0
            state["sprint_exhausted"] = True

        # A depleted sprint remains disarmed while Shift is held.  Releasing
        # Shift after recovering a little stamina re-arms sprint cleanly.
        if (state["sprint_exhausted"] and not shift_held
                and state["stamina"] >= SPRINT_RESUME_STAMINA):
            state["sprint_exhausted"] = False

        sprinting = (shift_held and not state["sprint_exhausted"]
                     and state["stamina"] > 0)
        speed = RUN_SPEED if sprinting else WALK_SPEED
        moving = False

        if not state["result"]:
            dance_active = update_deaths_dance(now, effective_dt)
            sonic_active = update_sonic_stream(now, effective_dt)
            ability_active = dance_active or sonic_active
            if ability_active:
                moving = True
                sprinting = False

            if (not ability_active and state["hitstop"] <= 0
                    and state["dashing"]):
                if now >= state["dash_end_time"]:
                    state["dashing"] = False
                    state["dash_finished_at"] = now
                else:
                    dx, dy = state["dash_dir"]
                    hero_pos[0] = max(
                        0, min(STAGE_EXIT_X, hero_pos[0] + dx * DASH_SPEED))
                    new_y = hero_pos[1] + dy * DASH_SPEED
                    if dy < 0 and new_y + FEET_OFFSET[hero_class] < TOP_BORDER_Y:
                        new_y = TOP_BORDER_Y - FEET_OFFSET[hero_class]
                    elif dy > 0:
                        new_y = min(HEIGHT - FEET_OFFSET[hero_class], new_y)
                    hero_pos[1] = new_y
                    moving = True

            if (not ability_active and state["hitstop"] <= 0
                    and not state["dashing"]):
                if keys[pygame.K_a]:
                    hero_pos[0] = max(0, hero_pos[0] - speed)
                    direction = "left"
                    moving = True
                elif keys[pygame.K_d]:
                    hero_pos[0] = min(STAGE_EXIT_X, hero_pos[0] + speed)
                    direction = "right"
                    moving = True
                if keys[pygame.K_w]:
                    new_y = hero_pos[1] - speed
                    if new_y + FEET_OFFSET[hero_class] < TOP_BORDER_Y:
                        new_y = TOP_BORDER_Y - FEET_OFFSET[hero_class]
                    hero_pos[1] = new_y
                    moving = True
                    if not keys[pygame.K_a] and not keys[pygame.K_d]:
                        direction = "up"
                elif keys[pygame.K_s]:
                    hero_pos[1] = min(
                        HEIGHT - FEET_OFFSET[hero_class], hero_pos[1] + speed)
                    moving = True
                    if not keys[pygame.K_a] and not keys[pygame.K_d]:
                        direction = "down"
            if sprinting and moving:
                state["stamina"] = max(0, state["stamina"] - 0.35)
                if state["stamina"] <= 0:
                    state["sprint_exhausted"] = True
            elif not sprinting:
                state["stamina"] = min(max_stamina, state["stamina"] + 0.03)

            hero_velocity[0] = (hero_pos[0] - previous_hero_pos[0]) * 16.0 / max(1, dt)
            hero_velocity[1] = (hero_pos[1] - previous_hero_pos[1]) * 16.0 / max(1, dt)
            previous_hero_pos[:] = hero_pos

            if (state["buffered_attack_until"] >= now and
                    now - last_attack_time >= state["current_recovery"]):
                state["buffered_attack_until"] = 0
                do_attack(moving, sprinting)
            elif state["buffered_attack_until"] and state["buffered_attack_until"] < now:
                state["buffered_attack_until"] = 0

            def _spawn_projectile(enemy, target_center, kind=None,
                                  damage_mult=1.0):
                projectile_kind = (kind or ENEMY_TYPES[enemy.etype].get(
                    "projectile", "arrow"))
                if projectile_kind == "igris_shockwave":
                    ex, ey = enemy.feet()
                else:
                    ex, ey = enemy.center()
                dmg = int(random.randint(*enemy.dmg_range) * damage_mult)
                projectiles.append(Projectile(
                    ex, ey, target_center[0], target_center[1], dmg,
                    kind=projectile_kind,
                    source=(enemy if projectile_kind.startswith("igris_") else None),
                    heavy=projectile_kind == "igris_shockwave"))

            living = [e for e in enemies if not e.dead]
            committed_melee = sum(1 for e in living if not e.ranged and e.is_committed)
            committed_ranged = sum(1 for e in living if e.ranged and e.is_committed)
            ordered_enemies = sorted(
                enemies,
                key=lambda enemy: math.hypot(
                    enemy.center()[0] - hero_center()[0],
                    enemy.center()[1] - hero_center()[1],
                ),
            )
            for e in ordered_enemies:
                others = [o.center()
                          for o in enemies if o is not e and not o.dead]
                allow_attack = (e.is_boss or
                                (e.ranged and committed_ranged < 1) or
                                (not e.ranged and committed_melee < 2))
                before = e.combat_state
                # The room title is visual only. Enemy movement and decision
                # timers begin on the first gameplay frame beneath the banner.
                e.update(effective_dt, hero_center(), hurt_hero,
                         spawn_projectile=_spawn_projectile,
                         other_positions=others,
                         allow_attack=allow_attack,
                         hero_velocity=tuple(hero_velocity))
                if before != "windup" and e.combat_state == "windup":
                    if e.ranged:
                        committed_ranged += 1
                    else:
                        committed_melee += 1

            hx, hy = hero_center()
            for p in projectiles:
                p.update(effective_dt)
                if p.alive:
                    dist = ((p.pos[0] - hx) ** 2 + (p.pos[1] - hy) ** 2) ** 0.5
                    if dist <= p.hit_radius + 22:
                        hurt_hero(p.dmg, source=p.source, heavy=p.heavy)
                        p.alive = False
            projectiles[:] = [p for p in projectiles if p.alive]

            still_pending = []
            for ph in state["pending_hits"]:
                if now >= ph["time"]:
                    resolve_attack_hit(ph["dmg"], ph["knockback"],
                                       ph["range"], ph.get("combo_step"),
                                       ph.get("facing"), ph.get("crit", False),
                                       ph.get("omni", False), ph.get("special", False))
                else:
                    still_pending.append(ph)
            state["pending_hits"] = still_pending

            if (not state["result"] and not state["exit_unlocked"]
                    and enemies
                    and all(e.dead and e.dead_done for e in enemies)):
                boss_type = stage.get("boss")
                if boss_type and not state["boss_spawned"]:
                    boss = spawn_boss(stage)
                    enemies.append(boss)
                    state["boss_spawned"] = True
                    add_log(f"{boss.name} enters the throne room!", RED)
                    play_music("boss")
                else:
                    state["exit_unlocked"] = True
                    # Keep each enemy's final death frame in the room. Dead
                    # enemies are already excluded from attacks, targeting,
                    # separation and health-bar drawing, so their bodies can
                    # remain without interfering with stage progression.
                    projectiles.clear()
                    state["pending_hits"].clear()
                    state["slashes"].clear()
                    state["assassin_sparks"].clear()
                    state["eruption_fx"].clear()
                    log.clear()

            if (state["exit_unlocked"]
                    and hero_pos[0] >= STAGE_EXIT_X):
                save_stage_summary()
                if stage_idx + 1 < len(STAGES):
                    return "next"
                state["result"] = "cleared"

        # ── animation state machine ──
        if anim:
            anim.update(effective_dt)

            if not anim.locked:
                if state["result"] == "lose":
                    if not state.get("death_played"):
                        play_dir("death", death_rows,
                                 one_shot=True, force=True)
                        state["death_played"] = True
                elif state["dashing"]:
                    play_dir("dash", dash_rows, one_shot=False, fps=DASH_ANIM_FPS)
                elif moving and sprinting:
                    play_dir("run", run_rows, one_shot=False,
                             fps=RUN_ANIM_FPS)
                elif moving:
                    # Keep the side gait at its original rate while matching
                    # the subtler front/back poses more closely to world travel.
                    walk_fps = (
                        ASSASSIN_VERTICAL_WALK_FPS
                        if is_assassin and direction in ("up", "down")
                        else WALK_ANIM_FPS
                    )
                    play_dir("walk", walk_rows, one_shot=False,
                             fps=walk_fps)
                else:
                    play_dir("idle", idle_rows, one_shot=False,
                             fps=IDLE_ANIM_FPS)

        ox = random.randint(-5, 5) if state["shake"] > 0 else 0
        oy = random.randint(-4, 4) if state["shake"] > 0 else 0
        if state["shake"] > 0:
            state["shake"] -= 1

        screen.fill((0, 0, 0))
        screen.blit(bg_img, (ox, oy))
        mouse = video.get_virtual_mouse_pos((WIDTH, HEIGHT))

        # ── Enemies (back-to-front by y) ──
        for e in sorted(enemies, key=lambda e: e.pos[1]):
            e.draw(screen, ox, oy)

        # ── Projectiles ──
        for p in projectiles:
            p.draw(screen, ox, oy)

        # ── Hero ──
        draw_dx, draw_dy = ASSASSIN_DRAW_OFFSET if is_assassin else (0, 0)
        hero_x = hero_pos[0] + ox + draw_dx
        hero_y = hero_pos[1] + oy + draw_dy
        hero_frame = anim.get_frame()

        # The opening burst leaves only two short-lived copies behind Jinwoo.
        # They disappear before the main spin so the newly animated body turn
        # remains readable instead of becoming a solid crimson silhouette.
        dance = state.get("deaths_dance")
        sonic = state.get("sonic_stream")
        if dance:
            dance_elapsed = now - dance["start"]
            if dance_elapsed < DEATHS_DANCE_TRAVEL_END:
                ddx, ddy = dance["vec"]
                travel_fade = 1.0 - dance_elapsed / DEATHS_DANCE_TRAVEL_END
                for echo_index in range(2, 0, -1):
                    echo = hero_frame.copy()
                    echo.fill((255, 48, 62, 255),
                              special_flags=pygame.BLEND_RGBA_MULT)
                    echo.set_alpha(int((22 + echo_index * 19) * travel_fade))
                    offset = 14 * echo_index
                    screen.blit(
                        echo,
                        (hero_x - ddx * offset, hero_y - ddy * offset),
                    )
        if sonic:
            sonic_elapsed = now - sonic["start"]
            if sonic_elapsed < SONIC_STREAM_DASH_END:
                sdx, sdy = sonic["vec"]
                travel_fade = 1.0 - sonic_elapsed / SONIC_STREAM_DASH_END
                for echo_index in range(3, 0, -1):
                    echo = hero_frame.copy()
                    echo.fill(
                        (255, 48, 62, 255),
                        special_flags=pygame.BLEND_RGBA_MULT,
                    )
                    echo.set_alpha(int((17 + echo_index * 13) * travel_fade))
                    offset = 16 * echo_index
                    screen.blit(
                        echo,
                        (hero_x - sdx * offset, hero_y - sdy * offset),
                    )
        screen.blit(hero_frame, (hero_x, hero_y))
        if (now < state["invulnerable_until"] and not state["result"]
                and not dance and not sonic):
            shimmer = 70 + int(45 * (1 + math.sin(now * 0.035)))
            hero_mask = pygame.mask.from_surface(hero_frame)
            aura = hero_mask.to_surface(setcolor=(112, 205, 255, shimmer),
                                        unsetcolor=(0, 0, 0, 0))
            screen.blit(aura, (hero_x, hero_y))
        # Unique ARISE-style Q choreography, colored with the same layered red
        # palette as the normal attacks but using no LMB animation or asset.
        if dance:
            draw_deaths_dance_vfx(now, dance)
        if sonic:
            draw_sonic_stream_vfx(now, sonic)

        # Keep the world-space name readable above combat effects.
        name_w = font_small.size(hero_name)[0]
        visible = hero_frame.get_bounding_rect(min_alpha=30)
        if visible.height:
            name_y = hero_y + visible.top - font_small.get_height() - 8
        else:
            name_y = hero_y + 8
        draw_text(screen, hero_name, font_small, GREEN,
                  hero_x + hero_frame.get_width()//2 - name_w//2, name_y)

        # ── Sword trails ──
        still_slashing = []
        for sl in state["slashes"]:
            elapsed = now - sl["start"]
            if elapsed >= sl["duration"]:
                continue
            t = elapsed / sl["duration"]
            if sl.get("kind") == "assassin":
                base_trail = get_assassin_trail_surface(sl.get("combo_step", 1))
            else:
                base_trail = get_trail_surface()
            trail_img = pygame.transform.rotate(base_trail, sl["angle"])
            trail_img.set_alpha(int(255 * (1 - t)))
            rect = trail_img.get_rect(
                center=(sl["pos"][0] + ox, sl["pos"][1] + oy))
            screen.blit(trail_img, rect)
            still_slashing.append(sl)
        state["slashes"] = still_slashing

        # Extra assassin energy motes.  These are deliberately separate from
        # the body sprites and inherit the facing vector captured on impact,
        # so LEFT/RIGHT/UP/DOWN remain correct even if the player turns during
        # the fade-out.
        still_sparks = []
        for sp in state["assassin_sparks"]:
            elapsed = now - sp["start"]
            if elapsed >= sp["life"]:
                continue
            t = elapsed / sp["life"]
            steps = elapsed / 16.667
            px = sp["pos"][0] + sp["vel"][0] * steps + ox
            py = sp["pos"][1] + sp["vel"][1] * steps + oy
            radius = sp["radius"]
            alpha = max(0, int(210 * (1.0 - t)))
            # A tiny per-particle SRCALPHA surface gives the mote a crimson
            # glow plus white-hot center without requiring a giant overlay.
            mote_size = radius * 6 + 8
            mote = pygame.Surface((mote_size, mote_size), pygame.SRCALPHA)
            mc = mote_size // 2
            pygame.draw.circle(mote, (170, 0, 32, alpha // 2),
                               (mc, mc), radius + 3)
            pygame.draw.circle(mote, (255, 35, 64, alpha),
                               (mc, mc), radius + 1)
            pygame.draw.circle(mote, (255, 225, 225, min(255, alpha + 30)),
                               (mc, mc), 1)
            screen.blit(mote, (int(px - mc), int(py - mc)))
            still_sparks.append(sp)
        state["assassin_sparks"] = still_sparks

        # ── Class ability shockwaves ──
        still_waves = []
        for wave in state["shockwaves"]:
            elapsed = now - wave["start"]
            if elapsed >= wave["life"]:
                continue
            t = elapsed / wave["life"]
            radius = max(4, int(wave["max_radius"] * (0.18 + 0.82 * t)))
            alpha = int(220 * (1 - t))
            fx = pygame.Surface((radius * 2 + 20, radius + 20), pygame.SRCALPHA)
            col = (*wave["color"], alpha)
            rect = pygame.Rect(10, 10, radius * 2, radius)
            pygame.draw.ellipse(fx, (*wave["color"], max(10, alpha // 7)), rect)
            pygame.draw.ellipse(fx, col, rect, max(2, int(6 * (1 - t))))
            cx = wave["pos"][0] + ox - fx.get_width() / 2
            cy = wave["pos"][1] + oy - fx.get_height() / 2
            screen.blit(fx, (int(cx), int(cy)))
            still_waves.append(wave)
        state["shockwaves"] = still_waves

        # ── Death's Dance crimson ground eruptions ──
        still_eruptions = []
        for burst in state["eruption_fx"]:
            elapsed = now - burst["start"]
            if elapsed >= burst["life"]:
                continue
            frame_time = burst["life"] / len(_a_deaths_dance_fx)
            frame_index = min(
                len(_a_deaths_dance_fx) - 1,
                int(elapsed / frame_time),
            )
            fx = _a_deaths_dance_fx[frame_index]
            scale = 1.0 + burst["index"] * 0.07
            if scale != 1.0:
                fx = pygame.transform.scale(
                    fx,
                    (round(fx.get_width() * scale),
                     round(fx.get_height() * scale)),
                )
            bounds = fx.get_bounding_rect(min_alpha=8)
            draw_x = burst["pos"][0] + ox - (bounds.left + bounds.width / 2)
            draw_y = burst["pos"][1] + oy - bounds.bottom
            screen.blit(fx, (int(draw_x), int(draw_y)))
            still_eruptions.append(burst)
        state["eruption_fx"] = still_eruptions

        # ── World-space damage and status numbers ──
        still_floaters = []
        for floater in state["floaters"]:
            elapsed = now - floater["start"]
            if elapsed >= floater["life"]:
                continue
            t = elapsed / floater["life"]
            floater_font = font_big if floater["size"] == "medium" else font_small
            label = floater_font.render(floater["text"], True, floater["color"])
            label.set_alpha(int(255 * min(1.0, (1 - t) * 1.6)))
            px = floater["pos"][0] + ox - label.get_width() / 2
            py = floater["pos"][1] + oy - 34 - t * 58
            screen.blit(label, (int(px), int(py)))
            still_floaters.append(floater)
        state["floaters"] = still_floaters

        # World feedback remains behind the HUD so the important bars stay clear.
        hp_ratio = state["hero_hp"] / max(1, hero_max_hp)
        if hp_ratio <= 0.28 and not state["result"]:
            pulse = (1 + math.sin(now * 0.007)) * 0.5
            draw_vignette(screen, 105 + 85 * pulse, color=(84, 0, 5))
        if state["damage_flash"] > 0:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((190, 10, 20, int(42 * state["damage_flash"] / 280)))
            screen.blit(flash, (0, 0))

        # ── Player HUD ──
        panel_x, panel_y, panel_w, panel_h = 22, 20, 520, 142
        draw_panel(screen, panel_x, panel_y, panel_w, panel_h)
        draw_corner_marks(screen, panel_x, panel_y, panel_w, panel_h, GOLD_DIM, 13)
        portrait_size = 92
        draw_ornate_frame(screen, panel_x + 13, panel_y + 13,
                          portrait_size, portrait_size, GOLD)
        if hud_portrait:
            screen.blit(hud_portrait, (panel_x + 13, panel_y + 13))
        draw_text(screen, hero_name.upper(), font_header, CREAM,
                  panel_x + 122, panel_y + 14, shadow=False)
        draw_text(screen, stats["title"], font_micro, DIM_TEXT,
                  panel_x + 124, panel_y + 44, shadow=False)
        bar_x, bar_w = panel_x + 122, 370
        draw_segmented_bar(screen, bar_x, panel_y + 70, bar_w, 16,
                           state["hero_hp"], hero_max_hp, COL_HP, COL_HP_DARK,
                           segments=14)
        draw_segmented_bar(screen, bar_x, panel_y + 101, bar_w, 12,
                           state["stamina"], max_stamina, COL_STA, COL_STA_DARK,
                           segments=14)
        draw_text(screen, f"HP {int(state['hero_hp'])}/{hero_max_hp}", font_micro,
                  CREAM, bar_x + 6, panel_y + 72, shadow=False)
        draw_text(screen, f"STAMINA {int(state['stamina'])}/{max_stamina}", font_micro,
                  CREAM, bar_x + 6, panel_y + 100, shadow=False)

        # Ability strip directly under the main panel.
        special_remaining = max(0, SPECIAL_COOLDOWN - (now - state["last_special_time"]))
        sonic_remaining = max(
            0,
            SONIC_STREAM_COOLDOWN - (now - state["last_sonic_stream_time"]),
        )
        focus_remaining = max(0, FOCUS_COOLDOWN - (now - state["last_focus_time"]))
        ability_y = panel_y + panel_h + 10
        draw_keycap(screen, panel_x + 10, ability_y, "Q", special_remaining == 0)
        special_text = SPECIAL_NAME if special_remaining == 0 else f"{SPECIAL_NAME}  {special_remaining / 1000:.1f}s"
        draw_text(screen, special_text, font_micro,
                  GOLD_BRIGHT if special_remaining == 0 else DIM_TEXT,
                  panel_x + 52, ability_y + 9, shadow=False)
        draw_keycap(screen, panel_x + 274, ability_y, "E", sonic_remaining == 0)
        sonic_text = (SONIC_STREAM_NAME if sonic_remaining == 0 else
                      f"{SONIC_STREAM_NAME}  {sonic_remaining / 1000:.1f}s")
        draw_text(screen, sonic_text, font_micro,
                  (255, 112, 42) if sonic_remaining == 0 else DIM_TEXT,
                  panel_x + 316, ability_y + 9, shadow=False)
        focus_y = ability_y + 38
        draw_keycap(screen, panel_x + 10, focus_y, "R", focus_remaining == 0)
        focus_text = "Focus" if focus_remaining == 0 else f"Focus  {focus_remaining / 1000:.1f}s"
        draw_text(screen, focus_text, font_micro,
                  (120, 196, 235) if focus_remaining == 0 else DIM_TEXT,
                  panel_x + 52, focus_y + 9, shadow=False)

        # ── Stage/objective HUD ──
        living_count = sum(1 for e in enemies if not e.dead)
        objective = (None if state["exit_unlocked"] else
                     "DEFEAT COMMANDER IGRIS" if state["boss_spawned"] else
                     f"HOSTILES REMAINING  {living_count}")
        stage_w, stage_h = 430, 88
        stage_x = WIDTH // 2 - stage_w // 2
        draw_panel(screen, stage_x, 18, stage_w, stage_h)
        draw_text(screen, f"ACT {stage_idx + 1} / {len(STAGES)}", font_micro,
                  stage["accent"], stage_x + 20, 32, shadow=False)
        stage_name_lbl = font_header.render(stage["name"].upper(), True, CREAM)
        screen.blit(stage_name_lbl, (stage_x + 20, 53))
        if objective:
            objective_lbl = font_micro.render(objective, True, DIM_TEXT)
            screen.blit(objective_lbl,
                        (stage_x + stage_w - 20 - objective_lbl.get_width(), 71))

        if state["hit_streak"] > 1:
            combo_w, combo_h = 220, 88
            combo_x = WIDTH - combo_w - 24
            draw_panel(screen, combo_x, 20, combo_w, combo_h,
                       border_col=(150, 76, 205) if is_assassin else GOLD)
            mult = font_big.render(f"{state['hit_streak']}x", True,
                                   (184, 112, 255) if is_assassin else GOLD_BRIGHT)
            screen.blit(mult, (combo_x + 18, 36))
            draw_text(screen, "HIT STREAK", font_micro, CREAM,
                      combo_x + 90, 42, shadow=False)
            remaining = max(0, 2600 - (now - state["last_streak_time"]))
            draw_segmented_bar(screen, combo_x + 90, 67, 108, 7,
                               remaining, 2600, COL_FOCUS, COL_FOCUS_DARK,
                               segments=8)

        # ── Boss HP, phase, and readable identity ──
        boss_enemy = next((e for e in enemies if e.is_boss), None)
        if boss_enemy is not None and not boss_enemy.dead_done:
            boss_w = 760
            boss_x, boss_y = WIDTH // 2 - boss_w // 2, HEIGHT - 92
            draw_text(screen, boss_enemy.name.upper(), font_header, CREAM,
                      boss_x, boss_y - 34, shadow=False)
            phase_txt = f"PHASE {boss_enemy.boss_phase}"
            draw_text(screen, phase_txt, font_micro,
                      (220, 75, 96) if boss_enemy.boss_phase >= 2 else DIM_TEXT,
                      boss_x + boss_w - font_micro.size(phase_txt)[0],
                      boss_y - 25, shadow=False)
            draw_segmented_bar(screen, boss_x, boss_y, boss_w, 16,
                               boss_enemy.hp, boss_enemy.max_hp,
                               (170, 28, 47), (38, 8, 15), segments=20)

        # Combat log stays subtle and out of the action space.
        for i, (msg, color) in enumerate(reversed(log[-3:])):
            txt_surf = font_micro.render(msg, True, color)
            txt_surf.set_alpha(max(75, 210 - i * 55))
            screen.blit(txt_surf, (26, HEIGHT - 34 - i * 20))

        # Visual-only stage introduction; combat continues underneath it.
        if now < state["stage_intro_until"]:
            remain = state["stage_intro_until"] - now
            fade = min(1.0, remain / 500, (2100 - remain) / 450)
            intro = pygame.Surface((850, 145), pygame.SRCALPHA)
            intro.fill((4, 4, 7, int(175 * fade)))
            pygame.draw.line(intro, (*stage["accent"], int(230 * fade)),
                             (90, 18), (760, 18), 2)
            title = font_title.render(stage["name"].upper(), True, stage["accent"])
            title.set_alpha(int(255 * fade))
            intro.blit(title, (425 - title.get_width() // 2, 32))
            sub = font_label.render(stage["subtitle"], True, CREAM)
            sub.set_alpha(int(220 * fade))
            intro.blit(sub, (425 - sub.get_width() // 2, 98))
            screen.blit(intro, (WIDTH // 2 - 425, HEIGHT // 2 - 190))

        # ── Result overlay ──
        if state["result"]:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((2, 2, 6, 218))
            screen.blit(overlay, (0, 0))
            draw_vignette(screen, 170)
            result_w, result_h = 760, 430
            result_x, result_y = WIDTH // 2 - result_w // 2, HEIGHT // 2 - result_h // 2
            draw_panel(screen, result_x, result_y, result_w, result_h)
            draw_corner_marks(screen, result_x, result_y, result_w, result_h,
                              GOLD if state["result"] == "cleared" else COL_HP, 22)
            if state["result"] == "cleared":
                title = font_title.render("HUNT COMPLETE", True, GOLD_BRIGHT)
            else:
                title = font_title.render("YOU DIED", True, COL_HP)
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, result_y + 45))
            summary = run_state.get("last_summary", {})
            results = [
                ("TIME", summary.get("time", "--:--")),
                ("DAMAGE", str(summary.get("damage_dealt", state["stats"]["damage_dealt"]))),
                ("KILLS", str(summary.get("kills", state["stats"]["kills"]))),
                ("BEST COMBO", str(summary.get("best_combo", state["best_streak"]))),
            ]
            start_rx = result_x + 46
            for i, (label, value) in enumerate(results):
                cell_w = (result_w - 92) // 4
                cx = start_rx + i * cell_w
                if i:
                    pygame.draw.line(screen, (76, 65, 57),
                                     (cx, result_y + 145), (cx, result_y + 250), 1)
                value_lbl = font_big.render(value, True, CREAM)
                screen.blit(value_lbl, (cx + cell_w // 2 - value_lbl.get_width() // 2,
                                        result_y + 165))
                draw_text(screen, label, font_micro, DIM_TEXT,
                          cx + cell_w // 2 - font_micro.size(label)[0] // 2,
                          result_y + 214, shadow=False)
            action = "ENTER  Finish the run" if state["result"] == "cleared" else "ENTER  Retry stage"
            draw_text(screen, action, font_med, CREAM,
                      WIDTH // 2 - font_med.size(action)[0] // 2,
                      result_y + 310, shadow=False)
            draw_text(screen, "ESC  Pause menu", font_small, DIM_TEXT,
                      WIDTH // 2 - 74, result_y + 356, shadow=False)

        video.present(screen)
        clock.tick(video.get_fps_limit())

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    choice = pause_menu()
                    if choice == "Exit Game":
                        pygame.quit()
                        sys.exit()
                    elif choice == "Options":
                        options_menu()
                    elif choice == "Restart Stage":
                        return "restart"
                if event.key == pygame.K_r and not state["result"]:
                    try_focus()
                if event.key == pygame.K_q and not state["result"]:
                    use_special()
                if event.key == pygame.K_e and not state["result"]:
                    use_sonic_stream()
                if event.key == pygame.K_SPACE and not state["result"]:
                    try_dash()
                if event.key == pygame.K_RETURN and state["result"] == "cleared":
                    return "finished" if stage_idx + 1 >= len(STAGES) else "next"
                if event.key == pygame.K_RETURN and state["result"] == "lose":
                    return "retry"
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not state["result"]:
                    request_attack(is_moving=moving, is_sprinting=sprinting)
                if event.button == 3 and not state["result"]:
                    use_special()
