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
from jinwoo_data import ATTACK_FRAME_MS, FRAME_STARTS, frame_at, duration as attack_duration
from jinwoo_vfx import JinwooVFX
from sprite_loaders import dir_frames
from entities import Enemy, Projectile
from game_data import (
    STAGES, ENEMY_TYPES, CLASS_STATS, portrait_imgs, STAGE_BGS,
    ASSASSIN_DRAW_OFFSET,
    warrior_anims, _w_idle_rows, _w_walk_rows, _w_run_rows, _w_atk_rows,
    _w_run_atk_rows, _w_walk_atk_rows, _w_hurt_rows, _w_death_rows,
    assassin_anims, _a_idle_rows, _a_walk_rows, _a_run_rows,
    _a_atk1_rows, _a_atk2_rows, _a_atk3_rows, _a_walk_atk_rows,
    _a_deaths_dance_rows, _a_sonic_stream_rows,
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

    # Each class keeps its established contact and recovery timing.
    is_assassin = hero_class == "Assassin"
    RUN_ATK_COOLDOWN = 1200
    ATTACK_RANGE = 158 if is_assassin else 170
    last_attack_time = 0
    last_run_atk_time = 0

    # ── 3-hit combo ──
    if is_assassin:
        COMBO_STEPS = [
            # Preserve damage and recovery. jinwoo_data supplies individual
            # pose durations and contact beats for the new choreography.
            {"dmg": (14, 24), "knockback": 4,  "recovery": 350, "fps": 16, "range": ATTACK_RANGE},
            {"dmg": (17, 28), "knockback": 6,  "recovery": 390, "fps": 16, "range": ATTACK_RANGE + 5},
            {"dmg": (28, 42), "knockback": 11, "recovery": 455, "fps": 13, "range": ATTACK_RANGE + 18},
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
    DEATHS_DANCE_DURATION = attack_duration('deaths_dance')
    DEATHS_DANCE_TRAVEL_START = FRAME_STARTS['deaths_dance'][2]
    DEATHS_DANCE_TRAVEL_END = FRAME_STARTS['deaths_dance'][7]
    DEATHS_DANCE_TRAVEL_DISTANCE = 280
    DEATHS_DANCE_SPIN_TIMES = tuple(FRAME_STARTS['deaths_dance'][i] for i in (2,3,4))
    DEATHS_DANCE_ERUPTION_TIMES = (FRAME_STARTS['deaths_dance'][7],)
    SONIC_STREAM_NAME = 'Sonic Stream'
    SONIC_STREAM_COOLDOWN = int(9200*run_state.get('special_cooldown_mult',1.0))
    SONIC_STREAM_COST = 60
    SONIC_STREAM_DURATION = attack_duration('sonic_stream')
    SONIC_STREAM_DASH_START = FRAME_STARTS['sonic_stream'][1]
    SONIC_STREAM_DASH_END = FRAME_STARTS['sonic_stream'][2]
    SONIC_STREAM_TRAVEL_DISTANCE = 250
    SONIC_STREAM_HIT_TIMES = tuple(FRAME_STARTS['sonic_stream'][i] for i in range(2,12))

    # ── hitstop / enemy flash / sword trail ──
    HITSTOP_HIT = 45 if is_assassin else 55
    HITSTOP_FINISHER = 80 if is_assassin else 100
    _trail_base = None
    jinwoo_fx = JinwooVFX() if is_assassin else None

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

    def play_dir(anim_name, rows_or_frames, one_shot=False, force=False, fps=None,
                 pose_profile=None):
        frames = dir_frames(rows_or_frames, direction)
        anim.play(anim_name, frames=frames,
                  one_shot=one_shot, force=force, fps=fps)
        profile = pose_profile or anim_name
        if is_assassin and one_shot and profile in ATTACK_FRAME_MS:
            state["jinwoo_action"] = {"name": anim_name, "profile": profile,
                                      "start": state["jinwoo_clock"]}

    def sync_jinwoo_pose():
        action = state.get("jinwoo_action")
        if not action:
            return
        if anim.current != action["name"]:
            state["jinwoo_action"] = None
            return
        elapsed = state["jinwoo_clock"] - action["start"]
        anim.frame_idx = frame_at(action["profile"], elapsed)
        anim.timer = 0
        anim.done = elapsed >= attack_duration(action["profile"])
        anim.locked = not anim.done
        if anim.done:
            state["jinwoo_action"] = None

    state = {
        "jinwoo_clock": 0.0,
        "jinwoo_action": None,
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
        if is_assassin:
            state["jinwoo_action"] = None
            state["pending_hits"].clear()
            state["deaths_dance"] = None
            state["sonic_stream"] = None
            jinwoo_fx.clear()
            state["buffered_attack_until"] = 0
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
        if is_assassin:
            state["jinwoo_action"] = None
            state["pending_hits"].clear()
            state["buffered_attack_until"] = 0
        state["stamina"] -= DASH_STAMINA_COST
        last_dash_time = now
        state["dashing"] = True
        state["dash_started_at"] = now
        state["evaded_this_dash"] = False
        state["dash_dir"] = DIR_VECS.get(direction, (1, 0))
        state["dash_end_time"] = now + DASH_DURATION
        state["invulnerable_until"] = state["dash_end_time"] + 70
        play_dir("dash", dash_rows, one_shot=True, force=True, fps=DASH_ANIM_FPS)
        if jinwoo_fx:
            jinwoo_fx.begin_dash((hero_center()[0],hero_pos[1]+FEET_OFFSET[hero_class]),
                                 direction,state["jinwoo_clock"])

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
        if (is_assassin and state["jinwoo_action"]
                and state["jinwoo_action"]["name"] == "dash_attack"):
            return
        dmg = int(random.randint(28, 42) * damage_mult)
        dmg, crit = roll_crit(dmg)
        state["stats"]["attacks"] += 1
        last_attack_time = now
        state["current_recovery"] = 340 if is_assassin else 260
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


    def spawn_slash(facing, duration=200):
        hx, hy = hero_center()
        dirx, diry = DIR_VECS.get(facing, (1, 0))
        pos = (hx + dirx * 55, hy + diry * 55)
        angle = {"right": 0, "left": 180, "up": 90, "down": 270}.get(facing, 0)
        state["slashes"].append({
            "pos": pos, "angle": angle,
            "start": pygame.time.get_ticks(), "duration": duration,
        })


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
                # Sprinting now retains all three distinct combo poses, with
                # the same contact times as their six-frame walking versions.
                anim_name, rows = "run_attack", walk_atk_rows[combo_index]
            else:
                anim_name = f"attack_{combo_index + 1}"
                rows = (walk_atk_rows if is_moving else atk_combo_rows)[combo_index]
        elif is_moving and is_sprinting:
            anim_name, rows = "run_attack", run_atk_rows
        elif is_moving:
            anim_name, rows = "walk_attack", walk_atk_rows[combo_index]
        else:
            anim_name, rows = "attack", atk_combo_rows[combo_index]
        play_dir(anim_name, rows, one_shot=True, force=True, fps=visual_fps,
                 pose_profile=f"attack_{combo_index + 1}" if is_assassin else None)
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
        if (state["result"] or state.get("sonic_stream") or state.get("deaths_dance")
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
            state["pending_hits"].clear()
            state["buffered_attack_until"] = 0
            dash_vec = DIR_VECS.get(direction, (1, 0))
            state["deaths_dance"] = {
                "start": now, "start_clock": state["jinwoo_clock"],
                "elapsed_ms": 0, "fx_done": set(),
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
            add_log("DEATH'S DANCE: ERUPTION", (245, 48, 62))
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
        """Start a short approach and ten fast dagger slashes."""
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
        state["pending_hits"].clear()
        state["buffered_attack_until"] = 0
        state["sonic_stream"] = {
            "start": now, "start_clock": state["jinwoo_clock"],
            "elapsed_ms": 0, "fx_done": set(),
            "direction": direction,
            "vec": travel_vec,
            "target": target,
            "strike_pos": None,
            "hit_done": set(),
        }
        state["invulnerable_until"] = now + SONIC_STREAM_DURATION - 90
        play_dir(
            "sonic_stream", sonic_stream_rows,
            one_shot=True, force=True, fps=8.3,
        )
        add_log("SONIC STREAM", (245, 48, 62))

    def queue_hit(dmg, knockback, atk_range, fps, combo_step=None, facing=None,
                  crit=False, omni=False, special=False):
        # Jinwoo contacts on the fourth pose (index 3).
        # Warrior retains its existing frame delay.
        delay = (FRAME_STARTS[state["jinwoo_action"]["profile"]][3]
                 if is_assassin else int(1000 / fps * 3))
        state["pending_hits"].append({
            "time": (state["jinwoo_clock"] if is_assassin else pygame.time.get_ticks()) + delay,
            "simulation_clock": is_assassin,
            "trail_spawned": False,
            "dmg": dmg,
            "knockback": knockback,
            "range": atk_range,
            "combo_step": combo_step,
            "facing": facing,
            "crit": crit,
            "omni": omni,
            "special": special,
            "impact_effect": ("blue_dash_sparks" if is_assassin and
                              state["jinwoo_action"]["profile"]=="dash_attack" else "contact"),
        })

    def resolve_attack_hit(dmg, knockback, atk_range, combo_step=None, facing=None,
                            crit=False, omni=False, special=False, origin=None,
                            quiet=False, impact_effect="contact", hit_stop_ms=None):
        state["last_hit_time"] = pygame.time.get_ticks()
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
            if is_assassin:
                jinwoo_fx.add(impact_effect, e.center(), facing or direction,
                              state["jinwoo_clock"], life=145, peak=True)
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
            stop = (hit_stop_ms if hit_stop_ms is not None else
                    HITSTOP_FINISHER if combo_step == 3 else HITSTOP_HIT)
            if crit:
                shake += 6
                if hit_stop_ms is None:
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

    def skill_step(dx, dy, distance):
        """Keep skill movement within the normal stage boundaries."""
        hero_pos[0]=max(0,min(STAGE_EXIT_X,hero_pos[0]+dx*distance))
        hero_pos[1]=max(TOP_BORDER_Y-FEET_OFFSET[hero_class],min(
            HEIGHT-FEET_OFFSET[hero_class],hero_pos[1]+dy*distance))

    def update_deaths_dance(now, frame_dt):
        """Spin forward, aerial turn, then one eruption straight ahead."""
        dance=state.get('deaths_dance')
        if not dance:return False
        elapsed=state['jinwoo_clock']-dance['start_clock']
        dance['elapsed_ms']=elapsed;dx,dy=dance['vec']
        span=DEATHS_DANCE_TRAVEL_END-DEATHS_DANCE_TRAVEL_START
        def progress(t):
            u=max(0,min(1,(t-DEATHS_DANCE_TRAVEL_START)/span))
            return u*u*(3-2*u)
        step=DEATHS_DANCE_TRAVEL_DISTANCE*(progress(elapsed)-progress(elapsed-frame_dt))
        if step:skill_step(dx,dy,step)
        if elapsed>=DEATHS_DANCE_TRAVEL_END and dance['landing_pos'] is None:
            dance['landing_pos']=(hero_center()[0],hero_pos[1]+FEET_OFFSET[hero_class])
        for index,beat in enumerate(DEATHS_DANCE_SPIN_TIMES):
            if elapsed<beat or index in dance['spin_done']:continue
            dance['spin_done'].add(index)
            jinwoo_fx.add('spin_ring',(hero_center()[0],hero_center()[1]+8),
                dance['direction'],state['jinwoo_clock'],start=dance['start_clock']+beat,
                life=260,follow_ms=240,offset=(0,8))
            last=index==2
            dmg=int(random.randint(*((13,18) if last else (8,12)))*damage_mult)
            dmg,crit=roll_crit(dmg,force_crit=last and state['hit_streak']>=8)
            resolve_attack_hit(dmg,knockback=12 if last else 4+index*2,
                atk_range=166 if last else 150,facing=dance['direction'],crit=crit,
                omni=True,special=True,quiet=True)
        landing=dance['landing_pos'] or (hero_center()[0],hero_pos[1]+FEET_OFFSET[hero_class])
        for index,beat in enumerate(DEATHS_DANCE_ERUPTION_TIMES):
            if elapsed<beat or index in dance['eruption_done']:continue
            dance['eruption_done'].add(index)
            feet=(landing[0]+dx*96,landing[1]+dy*96)
            jinwoo_fx.add('red_eruption',feet,dance['direction'],state['jinwoo_clock'],
                start=dance['start_clock']+beat,life=430,peak=True)
            dmg=int(random.randint(39,54)*damage_mult)
            dmg,crit=roll_crit(dmg,force_crit=state['hit_streak']>=8)
            resolve_attack_hit(dmg,knockback=18,atk_range=120,
                facing=dance['direction'],crit=crit,omni=True,special=True,
                origin=(feet[0],feet[1]-54),quiet=True)
            state['shake']=max(state['shake'],14)
        if elapsed>=DEATHS_DANCE_DURATION:state['deaths_dance']=None
        return True

    def update_sonic_stream(now, frame_dt):
        """Approach once, slash rapidly ten times, then release control."""
        sonic=state.get('sonic_stream')
        if not sonic:return False
        elapsed=state['jinwoo_clock']-sonic['start_clock']
        sonic['elapsed_ms']=elapsed;dx,dy=sonic['vec']
        travel_dt=max(0,min(elapsed,SONIC_STREAM_DASH_END)-max(elapsed-frame_dt,SONIC_STREAM_DASH_START))
        if travel_dt and sonic['strike_pos'] is None:
            step=SONIC_STREAM_TRAVEL_DISTANCE*travel_dt/(SONIC_STREAM_DASH_END-SONIC_STREAM_DASH_START)
            target=sonic.get('target')
            if target is not None and not target.dead:
                tx,ty=target.center();hx,hy=hero_center();distance=math.hypot(tx-hx,ty-hy)
                if distance>112:
                    dx,dy=(tx-hx)/distance,(ty-hy)/distance;sonic['vec']=(dx,dy)
                    step=min(step,distance-112)
                else:
                    step=0;sonic['strike_pos']=hero_center()
            skill_step(dx,dy,step)
        if elapsed>=SONIC_STREAM_DASH_END and sonic['strike_pos'] is None:
            sonic['strike_pos']=hero_center()
        strike=sonic['strike_pos'] or hero_center()
        for index,beat in enumerate(SONIC_STREAM_HIT_TIMES):
            if elapsed<beat or index in sonic['hit_done']:continue
            sonic['hit_done'].add(index)
            last=index==len(SONIC_STREAM_HIT_TIMES)-1
            jinwoo_fx.flurry_cut(index,hero_center(),sonic['direction'],state['jinwoo_clock'],
                start=sonic['start_clock']+beat,last=last)
            # Preserve the previous overall 72–111 base-damage range.
            dmg=int(random.randint(*((9,21) if last else (7,10)))*damage_mult)
            dmg,crit=roll_crit(dmg,force_crit=last and state['hit_streak']>=8)
            resolve_attack_hit(dmg,knockback=10 if last else 2,atk_range=190 if last else 166,
                facing=sonic['direction'],crit=crit,omni=False,special=True,origin=strike,
                quiet=True,hit_stop_ms=18 if last else 8)
            state['shake']=max(state['shake'],8 if last else 3)
        if elapsed>=SONIC_STREAM_DURATION:state['sonic_stream']=None
        return True


    while True:
        now = pygame.time.get_ticks()
        dt = min(now - last_time, 50)
        last_time = now

        paused_dt = min(dt, max(0, state["hitstop"]))
        state["hitstop"] = max(0, state["hitstop"] - dt)
        effective_dt = (dt - paused_dt if is_assassin else
                        0 if state["hitstop"] > 0 else dt)
        if is_assassin:
            state["jinwoo_clock"] += effective_dt
            if state["jinwoo_action"]:
                # Preserve recovery and buffering relative to the pose. Skill
                # recharge and stamina still use the original wall timers.
                last_attack_time += paused_dt
                state["last_combo_time"] += paused_dt
                if state["buffered_attack_until"]:
                    state["buffered_attack_until"] += paused_dt
                if state["deaths_dance"] or state["sonic_stream"]:
                    state["invulnerable_until"] += paused_dt
            sync_jinwoo_pose()
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
                hit_clock = state["jinwoo_clock"] if ph.get("simulation_clock") else now
                if ph.get("simulation_clock") and not ph["trail_spawned"]:
                    if hit_clock >= ph["time"]:
                        ph["trail_spawned"] = True
                        effect = {1:"sweep_cut", 2:"rising_cut", 3:"cross_finish"}.get(
                            ph.get("combo_step"), "blue_dash_cut")
                        jinwoo_fx.cut(effect, hero_center(), ph["facing"], hit_clock,
                            start=ph["time"], life=210 if effect=="blue_dash_cut" else 170, peak=True)
                if hit_clock >= ph["time"]:
                    resolve_attack_hit(ph["dmg"], ph["knockback"],
                                       ph["range"], ph.get("combo_step"),
                                       ph.get("facing"), ph.get("crit", False),
                                       ph.get("omni", False), ph.get("special", False),
                                       impact_effect=ph.get("impact_effect","contact"))
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
                    if jinwoo_fx:
                        jinwoo_fx.clear()
                    log.clear()

            if (state["exit_unlocked"]
                    and hero_pos[0] >= STAGE_EXIT_X):
                save_stage_summary()
                if stage_idx + 1 < len(STAGES):
                    return "next"
                state["result"] = "cleared"

        # ── animation state machine ──
        if anim:
            if not (is_assassin and state["jinwoo_action"]):
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
        # A ground wave traveling away from Igris passes behind his body.
        for p in projectiles:
            if p.behind_source:
                p.draw(screen, ox, oy)
        for e in sorted(enemies, key=lambda e: e.pos[1]):
            e.draw(screen, ox, oy)

        # ── Projectiles ──
        for p in projectiles:
            if not p.behind_source:
                p.draw(screen, ox, oy)

        # ── Hero ──
        draw_dx, draw_dy = ASSASSIN_DRAW_OFFSET if is_assassin else (0, 0)
        hero_x = hero_pos[0] + ox + draw_dx
        hero_y = hero_pos[1] + oy + draw_dy
        hero_frame = anim.get_frame()

        dance = state.get("deaths_dance")
        sonic = state.get("sonic_stream")
        dash_strike=(state.get("jinwoo_action") or {}).get("profile")=="dash_attack"
        blue_dash=is_assassin and not state["result"] and (state["dashing"] or dash_strike)
        if jinwoo_fx:
            fx_facing = sonic["direction"] if sonic else direction
            dash_active = state["dashing"]
            if dance and DEATHS_DANCE_TRAVEL_START <= dance["elapsed_ms"] < DEATHS_DANCE_TRAVEL_END:
                jinwoo_fx.sample_shadow(hero_frame,(hero_pos[0]+draw_dx,hero_pos[1]+draw_dy),
                    state["jinwoo_clock"],(210,30,58))
            elif sonic and SONIC_STREAM_DASH_START <= sonic["elapsed_ms"] < SONIC_STREAM_DASH_END:
                jinwoo_fx.sample_shadow(hero_frame,(hero_pos[0]+draw_dx,hero_pos[1]+draw_dy),
                    state["jinwoo_clock"],(220,69,34))
            elif sonic and SONIC_STREAM_DASH_END <= sonic["elapsed_ms"] < FRAME_STARTS['sonic_stream'][12]:
                jinwoo_fx.sample_shadow(hero_frame,(hero_pos[0]+draw_dx,hero_pos[1]+draw_dy),
                    state["jinwoo_clock"],(210,25,49),interval=65,life=110,opacity=55)
            if state["dashing"]:
                jinwoo_fx.sample_blue_shadow(hero_frame,(hero_pos[0]+draw_dx,hero_pos[1]+draw_dy),
                    (hero_center()[0],hero_pos[1]+FEET_OFFSET[hero_class]),state["jinwoo_clock"])
            jinwoo_fx.update(state["jinwoo_clock"], hero_center(),
                (hero_center()[0], hero_pos[1]+FEET_OFFSET[hero_class]),
                fx_facing, dash_active)
            jinwoo_fx.draw(screen, state["jinwoo_clock"], hero_center(), ox, oy, behind=True)
        if blue_dash:
            strength=1.0
            if dash_strike and not state["dashing"]:
                remaining=attack_duration('dash_attack')-(state["jinwoo_clock"]-state["jinwoo_action"]["start"])
                strength=max(0.0,min(1.0,remaining/80))
            jinwoo_fx.draw_blue_body(screen,hero_frame,(hero_x,hero_y),strength)
        else:
            screen.blit(hero_frame,(hero_x,hero_y))
        if (now < state["invulnerable_until"] and not state["result"]
                and not dance and not sonic and not blue_dash):
            shimmer = 70 + int(45 * (1 + math.sin(now * 0.035)))
            hero_mask = pygame.mask.from_surface(hero_frame)
            aura = hero_mask.to_surface(setcolor=(112, 205, 255, shimmer),
                                        unsetcolor=(0, 0, 0, 0))
            screen.blit(aura, (hero_x, hero_y))
        if jinwoo_fx:
            jinwoo_fx.draw(screen, state["jinwoo_clock"], hero_center(), ox, oy)

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
            base_trail = get_trail_surface()
            trail_img = pygame.transform.rotate(base_trail, sl["angle"])
            trail_img.set_alpha(int(255 * (1 - t)))
            rect = trail_img.get_rect(
                center=(sl["pos"][0] + ox, sl["pos"][1] + oy))
            screen.blit(trail_img, rect)
            still_slashing.append(sl)
        state["slashes"] = still_slashing

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
