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
from ui import draw_text, draw_panel, draw_stat_bar, draw_ornate_frame
from audio import play_music
from animator import Animator
from sprite_loaders import dir_frames
from entities import Enemy, Projectile
from game_data import (
    STAGES, ENEMY_TYPES, CLASS_STATS, portrait_imgs, STAGE_BGS,
    warrior_anims, _w_idle_rows, _w_walk_rows, _w_run_rows, _w_atk_rows,
    _w_run_atk_rows, _w_walk_atk_rows, _w_hurt_rows, _w_death_rows,
    assassin_anims, _a_idle_rows, _a_walk_rows, _a_run_rows, _a_atk_rows,
    _a_walk_atk_rows, _a_run_atk_rows, _a_dash_rows, _a_dash_atk_rows,
    _a_hurt_rows, _a_death_rows,
    VAMPIRE_STATS,
)
from screens import pause_menu, options_menu

def spawn_enemies(stage):
    enemies = []
    mult = stage.get("wave_mult", 1.0)
    slots = [
        (WIDTH - 750, HEIGHT - 620),
        (WIDTH - 520, HEIGHT - 500),
        (WIDTH - 750, HEIGHT - 350),
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


def stage_screen(hero_class, hero_name, stage_idx):
    stage = STAGES[stage_idx]
    bg_img = STAGE_BGS[stage["bg"]]
    play_music(stage["bg"])

    stats = CLASS_STATS[hero_class]
    hero_hp = stats["health"]
    hero_max_hp = stats["health"]
    stamina = stats["stamina"]
    max_stamina = stamina

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
            {"dmg": (14, 24), "knockback": 4,  "recovery": 330, "fps": 22, "range": ATTACK_RANGE},
            {"dmg": (17, 28), "knockback": 6,  "recovery": 330, "fps": 22, "range": ATTACK_RANGE + 5},
            {"dmg": (28, 42), "knockback": 11, "recovery": 420, "fps": 20, "range": ATTACK_RANGE + 18},
        ]
        COMBO_WINDOW = 520
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
    DASH_COOLDOWN = 420 if is_assassin else 500
    DASH_STAMINA_COST = 18 if is_assassin else 20
    DASH_ATTACK_BUFFER = 170 if is_assassin else 150
    DIR_VECS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}
    last_dash_time = 0
    FACING_COS_THRESHOLD = math.cos(math.radians(100))

    # ── critical hits ──
    CRIT_CHANCE = 0.24 if is_assassin else 0.18
    CRIT_MULT = 1.8

    # ── hitstop / enemy flash / sword trail ──
    HITSTOP_HIT = 45 if is_assassin else 55
    HITSTOP_FINISHER = 80 if is_assassin else 100
    _trail_base = None

    direction = "right"
    if hero_class == "Assassin":
        anim = Animator(assassin_anims.copy(), default="idle", fps=8)
        idle_rows, walk_rows, run_rows = _a_idle_rows, _a_walk_rows, _a_run_rows
        atk_rows, run_atk_rows = _a_atk_rows, _a_run_atk_rows
        dash_rows, dash_attack_rows = _a_dash_rows, _a_dash_atk_rows
        hurt_rows, death_rows = _a_hurt_rows, _a_death_rows
        walk_atk_rows = _a_walk_atk_rows
    else:
        anim = Animator(warrior_anims.copy(), default="idle", fps=8)
        idle_rows, walk_rows, run_rows = _w_idle_rows, _w_walk_rows, _w_run_rows
        atk_rows, run_atk_rows = _w_atk_rows, _w_run_atk_rows
        dash_rows, dash_attack_rows = _w_run_rows, _w_atk_rows
        walk_atk_rows = _w_walk_atk_rows
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
        "combo_index": 0,
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
    }

    hero_pos = [120, HEIGHT - 450]
    enemies = spawn_enemies(stage)
    projectiles = []

    FEET_OFFSET = {
        "Warrior": 115,
        "Assassin": 166,
    }
    TOP_BORDER_Y = HEIGHT - 700
    WALK_SPEED = 3.4 if is_assassin else 3
    RUN_SPEED = 4.7 if is_assassin else 4

    def hero_center():
        return (hero_pos[0] + DISPLAY_SIZE[0] / 2, hero_pos[1] + DISPLAY_SIZE[1] / 2)

    def hurt_hero(dmg):
        if state["result"] or state["dashing"]:
            return
        state["hero_hp"] -= dmg
        state["shake"] = 6
        add_log(f"Hit for {dmg}!", RED)
        if state["hero_hp"] <= 0:
            state["hero_hp"] = 0
            state["result"] = "lose"
            play_dir("death", death_rows, one_shot=True, force=True, fps=9)
            state["death_played"] = True
        else:
            play_dir("hurt", hurt_rows, one_shot=True, force=True, fps=12)

    def try_dash():
        nonlocal last_dash_time
        now = pygame.time.get_ticks()
        if state["result"] or state["dashing"]:
            return
        if now - last_dash_time < DASH_COOLDOWN:
            return
        if state["stamina"] < DASH_STAMINA_COST:
            add_log("Not enough stamina to dash!", YELLOW)
            return
        state["stamina"] -= DASH_STAMINA_COST
        last_dash_time = now
        state["dashing"] = True
        state["dash_dir"] = DIR_VECS.get(direction, (1, 0))
        state["dash_end_time"] = now + DASH_DURATION
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
        dmg = random.randint(28, 42)
        dmg, crit = roll_crit(dmg)
        last_attack_time = now
        state["current_recovery"] = 310 if is_assassin else 260
        state["combo_index"] = 0
        # The strike plants your feet -- any leftover dash momentum stops here.
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

        if is_dash_attack_window():
            do_dash_attack()
            return

        # ── normal 3-hit combo ──
        if now - last_attack_time < state["current_recovery"]:
            return  # still recovering from the last swing

        # Waited too long since the last hit landed? Combo resets to step 1.
        if now - state["last_hit_time"] > COMBO_WINDOW:
            state["combo_index"] = 0

        step = COMBO_STEPS[state["combo_index"]]
        dmg = random.randint(*step["dmg"])
        dmg, crit = roll_crit(dmg)
        last_attack_time = now
        state["current_recovery"] = step["recovery"]

        if is_moving and is_sprinting:
            anim_name, rows = "run_attack", run_atk_rows
        elif is_moving:
            anim_name, rows = "walk_attack", walk_atk_rows
        else:
            anim_name, rows = "attack", atk_rows
        play_dir(anim_name, rows, one_shot=True, force=True, fps=step["fps"])
        if hero_class == "Warrior":
            spawn_slash(direction, duration=260 if state["combo_index"] == 2 else 190)

        queue_hit(dmg, knockback=step["knockback"],
                  atk_range=step["range"], fps=step["fps"],
                  combo_step=state["combo_index"] + 1, facing=direction, crit=crit)

        state["combo_index"] = (state["combo_index"] + 1) % len(COMBO_STEPS)

    def queue_hit(dmg, knockback, atk_range, fps, combo_step=None, facing=None,
                  crit=False):
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
        })

    def resolve_attack_hit(dmg, knockback, atk_range, combo_step=None, facing=None,
                            crit=False):
        state["last_hit_time"] = pygame.time.get_ticks()
        hx, hy = hero_center()
        fvx, fvy = DIR_VECS.get(facing, (1, 0))
        hit_any = False
        for e in enemies:
            if e.dead:
                continue
            ex, ey = e.center()
            dnx, dny = ex - hx, ey - hy
            dist = (dnx * dnx + dny * dny) ** 0.5
            if dist > atk_range:
                continue
            if dist > 4:
                dot = (dnx / dist) * fvx + (dny / dist) * fvy
                if dot < FACING_COS_THRESHOLD:
                    continue  # roughly behind the hero -- the swing doesn't reach
            e.take_damage(dmg)
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

            if crit:
                add_log(f"CRITICAL {label}! {dmg} dmg!", RED)
            else:
                add_log(f"{label}! {dmg} dmg!", GOLD if combo_step == 3 else GREEN)
        else:
            add_log("Swing and a miss!", YELLOW)

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

        keys = pygame.key.get_pressed()
        sprinting = keys[pygame.K_LSHIFT] and state["stamina"] > 0
        speed = RUN_SPEED if sprinting else WALK_SPEED
        moving = False

        if not state["result"]:
            if state["hitstop"] <= 0 and state["dashing"]:
                if now >= state["dash_end_time"]:
                    state["dashing"] = False
                    state["dash_finished_at"] = now
                else:
                    dx, dy = state["dash_dir"]
                    hero_pos[0] = max(
                        0, min(WIDTH - DISPLAY_SIZE[0], hero_pos[0] + dx * DASH_SPEED))
                    new_y = hero_pos[1] + dy * DASH_SPEED
                    if dy < 0 and new_y + FEET_OFFSET[hero_class] < TOP_BORDER_Y:
                        new_y = TOP_BORDER_Y - FEET_OFFSET[hero_class]
                    elif dy > 0:
                        new_y = min(HEIGHT - FEET_OFFSET[hero_class], new_y)
                    hero_pos[1] = new_y
                    moving = True

            if state["hitstop"] <= 0 and not state["dashing"]:
                if keys[pygame.K_a]:
                    hero_pos[0] = max(0, hero_pos[0] - speed)
                    direction = "left"
                    moving = True
                elif keys[pygame.K_d]:
                    hero_pos[0] = min(WIDTH - DISPLAY_SIZE[0], hero_pos[0] + speed)
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
            elif not sprinting:
                state["stamina"] = min(max_stamina, state["stamina"] + 0.03)

            def _spawn_projectile(enemy, target_center):
                ex, ey = enemy.center()
                dmg = random.randint(*enemy.dmg_range)
                projectiles.append(Projectile(
                    ex, ey, target_center[0], target_center[1], dmg))

            for e in enemies:
                others = [o.center()
                          for o in enemies if o is not e and not o.dead]
                e.update(effective_dt, hero_center(), hurt_hero,
                         spawn_projectile=_spawn_projectile, other_positions=others)

            hx, hy = hero_center()
            for p in projectiles:
                p.update(effective_dt)
                if p.alive:
                    dist = ((p.pos[0] - hx) ** 2 + (p.pos[1] - hy) ** 2) ** 0.5
                    if dist <= 50:
                        hurt_hero(p.dmg)
                        p.alive = False
            projectiles[:] = [p for p in projectiles if p.alive]

            still_pending = []
            for ph in state["pending_hits"]:
                if now >= ph["time"]:
                    resolve_attack_hit(ph["dmg"], ph["knockback"],
                                       ph["range"], ph.get("combo_step"),
                                       ph.get("facing"), ph.get("crit", False))
                else:
                    still_pending.append(ph)
            state["pending_hits"] = still_pending

            if not state["result"] and enemies and all(e.dead and e.dead_done for e in enemies):
                boss_type = stage.get("boss")
                if boss_type and not state["boss_spawned"]:
                    boss_cfg = VAMPIRE_STATS if boss_type == "vampire" else ENEMY_TYPES[boss_type]
                    mult = stage.get("wave_mult", 1.0)
                    boss = Enemy(boss_type, WIDTH - 640, HEIGHT - 520)
                    boss.set_stats(int(boss_cfg["hp"] * mult),
                                   (int(boss_cfg["dmg"][0] * mult), int(boss_cfg["dmg"][1] * mult)))
                    boss.is_boss = True
                    enemies.append(boss)
                    state["boss_spawned"] = True
                    add_log("The Vampire emerges!", RED)
                    play_music("boss")
                else:
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
                    play_dir("run",  run_rows,  one_shot=False)
                elif moving:
                    play_dir("walk", walk_rows, one_shot=False)
                else:
                    play_dir("idle", idle_rows, one_shot=False)

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
        hero_x = hero_pos[0] + ox
        hero_y = hero_pos[1] + oy
        screen.blit(anim.get_frame(), (hero_x, hero_y))
        name_w = font_small.size(hero_name)[0]
        draw_text(screen, hero_name, font_small, GREEN,
                  hero_x + DISPLAY_SIZE[0]//2 - name_w//2, hero_y + 40)

        # ── Sword trails ──
        still_slashing = []
        for sl in state["slashes"]:
            elapsed = now - sl["start"]
            if elapsed >= sl["duration"]:
                continue
            t = elapsed / sl["duration"]
            trail_img = pygame.transform.rotate(get_trail_surface(), sl["angle"])
            trail_img.set_alpha(int(255 * (1 - t)))
            rect = trail_img.get_rect(
                center=(sl["pos"][0] + ox, sl["pos"][1] + oy))
            screen.blit(trail_img, rect)
            still_slashing.append(sl)
        state["slashes"] = still_slashing

        # ── Stage name — banner, top center ──
        stage_txt = f"{stage['name']}"
        stage_sub = f"Stage {stage_idx + 1} / {len(STAGES)}"
        banner_w = max(font_header.size(stage_txt)[0],
                       font_label.size(stage_sub)[0]) + 60
        banner_x = WIDTH // 2 - banner_w // 2
        draw_panel(screen, banner_x, 14, banner_w, 62)
        hdr = font_header.render(stage_txt, True, GOLD)
        screen.blit(hdr, (WIDTH // 2 - hdr.get_width() // 2, 18))
        sub = font_label.render(stage_sub, True, DIM_TEXT)
        screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 46))

        # ── Boss HP bar — bottom center, Elden Ring style ──
        boss_enemy = next((e for e in enemies if e.is_boss), None)
        if boss_enemy is not None:
            boss_bar_w = 560
            boss_bar_x = WIDTH // 2 - boss_bar_w // 2
            boss_bar_y = HEIGHT - 90
            name_lbl = font_header.render("VAMPIRE", True, CREAM)
            screen.blit(
                name_lbl, (WIDTH // 2 - name_lbl.get_width() // 2, boss_bar_y - 32))
            draw_stat_bar(screen, boss_bar_x, boss_bar_y, boss_bar_w, 12,
                         boss_enemy.hp, boss_enemy.max_hp, COL_HP, COL_HP_DARK)

        # ── Portrait + bars top left ──
        P_SIZE = 84
        P_X, P_Y = 20, 20
        draw_ornate_frame(screen, P_X, P_Y, P_SIZE, P_SIZE)
        portrait = portrait_imgs.get(hero_class)
        if portrait:
            screen.blit(portrait, (P_X, P_Y))

        BAR_X, BAR_W, BAR_H, BAR_GAP = P_X + P_SIZE + 16, 260, 14, 34

        draw_stat_bar(screen, BAR_X, P_Y + 20, BAR_W, BAR_H,
                     state["hero_hp"], hero_max_hp, COL_HP, COL_HP_DARK,
                     label="HP", font=font_label)
        draw_stat_bar(screen, BAR_X, P_Y + 20 + BAR_GAP, BAR_W, BAR_H,
                     state["stamina"], max_stamina, COL_STA, COL_STA_DARK,
                     label="Stamina", font=font_label)

        # ── Low stamina warning ──
        if state["stamina"] <= 10:
            draw_text(screen, "LOW STAMINA — press R to recover!",
                      font_small, YELLOW, P_X, P_Y + P_SIZE + 14)

        # ── Combat log — bottom left, fading feed ──
        for i, (msg, color) in enumerate(reversed(log)):
            txt_surf = font_small.render(msg, True, color)
            txt_surf.set_alpha(max(50, 255 - i * 45))
            screen.blit(txt_surf, (24, HEIGHT - 40 - i * 22))


        # ── Result overlay ──
        if state["result"]:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 175))
            screen.blit(overlay, (0, 0))
            if state["result"] == "cleared":
                title = font_title.render("STAGE CLEAR", True, GOLD)
                screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 90))
                pygame.draw.line(screen, GOLD_DIM, (WIDTH//2-140, HEIGHT//2-18),
                                 (WIDTH//2+140, HEIGHT//2-18), 1)
                if stage_idx + 1 < len(STAGES):
                    draw_text(screen, "Press ENTER to continue",
                              font_med, CREAM,  WIDTH//2-160, HEIGHT//2+10, shadow=False)
                else:
                    draw_text(screen, "You cleared every stage!",
                              font_med, CREAM,  WIDTH//2-160, HEIGHT//2+10, shadow=False)
                    draw_text(screen, "Press ENTER to finish",
                              font_small, DIM_TEXT, WIDTH//2-100, HEIGHT//2+42, shadow=False)
            else:
                title = font_title.render("YOU DIED", True, COL_HP)
                screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 90))
                pygame.draw.line(screen, GOLD_DIM, (WIDTH//2-140, HEIGHT//2-18),
                                 (WIDTH//2+140, HEIGHT//2-18), 1)
                draw_text(screen, "Press ENTER to retry the stage",
                          font_med, CREAM, WIDTH//2-190, HEIGHT//2+10, shadow=False)
            draw_text(screen, "Press ESC for menu", font_small,
                      DIM_TEXT, WIDTH//2-80, HEIGHT//2+60, shadow=False)

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
                    elif choice == "Change Class":
                        return "change_class"
                if event.key == pygame.K_r and not state["result"]:
                    state["stamina"] = min(max_stamina, state["stamina"] + 60)
                if event.key == pygame.K_SPACE and not state["result"]:
                    try_dash()
                if event.key == pygame.K_RETURN and state["result"] == "cleared":
                    return "next"
                if event.key == pygame.K_RETURN and state["result"] == "lose":
                    return "retry"
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not state["result"]:
                    do_attack(is_moving=moving, is_sprinting=sprinting)
