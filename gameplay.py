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

    ATTACK_COOLDOWN = 800
    RUN_ATK_COOLDOWN = 1200
    ATTACK_RANGE = 170
    last_attack_time = 0
    last_run_atk_time = 0

    direction = "right"
    anim = Animator(warrior_anims.copy(), default="idle", fps=8)
    idle_rows, walk_rows, run_rows = _w_idle_rows, _w_walk_rows, _w_run_rows
    atk_rows, run_atk_rows = _w_atk_rows,  _w_run_atk_rows
    walk_atk_rows = _w_walk_atk_rows
    death_rows = _w_death_rows
    has_run_attack = True

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
    }

    hero_pos = [120, HEIGHT - 450]
    enemies = spawn_enemies(stage)
    projectiles = []

    FEET_OFFSET = {
        "Warrior": 115,
    }
    TOP_BORDER_Y = HEIGHT - 700
    WALK_SPEED = 3
    RUN_SPEED = 5

    def hero_center():
        return (hero_pos[0] + DISPLAY_SIZE[0] / 2, hero_pos[1] + DISPLAY_SIZE[1] / 2)

    def hurt_hero(dmg):
        if state["result"]:
            return
        state["hero_hp"] -= dmg
        state["shake"] = 6
        add_log(f"Hit for {dmg}!", RED)
        if state["hero_hp"] <= 0:
            state["hero_hp"] = 0
            state["result"] = "lose"

    def do_attack(is_run_atk, is_moving, is_sprinting):
        nonlocal last_attack_time, last_run_atk_time
        now = pygame.time.get_ticks()

        if is_run_atk and has_run_attack:
            if now - last_run_atk_time < RUN_ATK_COOLDOWN:
                return
            if state["stamina"] < 30:
                add_log("Not enough stamina!", YELLOW)
                return
            state["stamina"] = max(0, state["stamina"] - 30)
            dmg = random.randint(60, 100)
            last_run_atk_time = now
            anim_name = "run_attack"
            rows = run_atk_rows
        elif is_moving and not is_sprinting:
            if now - last_attack_time < ATTACK_COOLDOWN:
                return
            dmg = random.randint(15, 40)
            last_attack_time = now
            anim_name = "walk_attack"
            rows = walk_atk_rows
        else:
            if now - last_attack_time < ATTACK_COOLDOWN:
                return
            dmg = random.randint(15, 40)
            last_attack_time = now
            anim_name = "attack"
            rows = atk_rows

        play_dir(anim_name, rows, one_shot=True, force=True)
        resolve_attack_hit(dmg)

    def resolve_attack_hit(dmg):
        hx, hy = hero_center()
        hit_any = False
        for e in enemies:
            if e.dead:
                continue
            ex, ey = e.center()
            dist = ((ex - hx) ** 2 + (ey - hy) ** 2) ** 0.5
            if dist <= ATTACK_RANGE:
                e.take_damage(dmg)
                hit_any = True
        state["shake"] = 8
        if hit_any:
            add_log(f"Attack! {dmg} dmg!", GREEN)
        else:
            add_log("Swing and a miss!", YELLOW)

    while True:
        now = pygame.time.get_ticks()
        dt = min(now - last_time, 50)
        last_time = now

        keys = pygame.key.get_pressed()
        sprinting = keys[pygame.K_LSHIFT] and state["stamina"] > 0
        speed = RUN_SPEED if sprinting else WALK_SPEED
        moving = False

        if not state["result"]:
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
                e.update(dt, hero_center(), hurt_hero,
                         spawn_projectile=_spawn_projectile, other_positions=others)

            hx, hy = hero_center()
            for p in projectiles:
                p.update(dt)
                if p.alive:
                    dist = ((p.pos[0] - hx) ** 2 + (p.pos[1] - hy) ** 2) ** 0.5
                    if dist <= 50:
                        hurt_hero(p.dmg)
                        p.alive = False
            projectiles[:] = [p for p in projectiles if p.alive]

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
            anim.update(dt)

            if not anim.locked:
                if state["result"] == "lose":
                    if not state.get("death_played"):
                        play_dir("death", death_rows,
                                 one_shot=True, force=True)
                        state["death_played"] = True
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
                if event.key == pygame.K_RETURN and state["result"] == "cleared":
                    return "next"
                if event.key == pygame.K_RETURN and state["result"] == "lose":
                    return "retry"
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not state["result"]:
                    do_attack(is_run_atk=keys[pygame.K_LSHIFT],
                              is_moving=moving, is_sprinting=sprinting)
