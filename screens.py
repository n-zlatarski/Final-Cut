"""Menus, options, class selection, and between-stage rewards."""
import sys
import math

import pygame

import video
from settings import *
from ui import (
    draw_text, draw_panel, draw_menu_button, draw_segmented_bar,
    draw_vignette, draw_corner_marks,
)
from audio import play_music, set_music_volume, audio_state
from game_data import STAGE_BGS, STAGES
from progression import BOONS, boon_choices, apply_boon


def _quit():
    pygame.quit()
    sys.exit()


def _menu_backdrop(bg_key="terrace", darkness=165):
    screen.blit(STAGE_BGS[bg_key], (0, 0))
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 12):
        t = y / HEIGHT
        alpha = int(darkness + 45 * (1 - abs(t - 0.5) * 2))
        pygame.draw.rect(shade, (5, 5, 9, min(235, alpha)), (0, y, WIDTH, 12))
    screen.blit(shade, (0, 0))
    draw_vignette(screen, 150)
    pygame.draw.line(screen, (198, 165, 92, 80), (120, 82), (WIDTH - 120, 82), 1)
    pygame.draw.line(screen, (198, 165, 92, 45), (120, HEIGHT - 82),
                     (WIDTH - 120, HEIGHT - 82), 1)


def _draw_brand(y=92, compact=False):
    font = font_title if compact else font_huge
    title = font.render("FINAL CUT", True, GOLD_BRIGHT)
    shadow = font.render("FINAL CUT", True, (0, 0, 0))
    x = WIDTH // 2 - title.get_width() // 2
    screen.blit(shadow, (x + 4, y + 6))
    screen.blit(title, (x, y))
    line_y = y + title.get_height() + 12
    pygame.draw.line(screen, GOLD_DIM, (x - 45, line_y),
                     (x + title.get_width() + 45, line_y), 1)
    diamond = [(WIDTH // 2, line_y - 5), (WIDTH // 2 + 7, line_y),
               (WIDTH // 2, line_y + 5), (WIDTH // 2 - 7, line_y)]
    pygame.draw.polygon(screen, GOLD, diamond)


def pause_menu():
    options = ["Resume", "Restart Stage", "Options", "Exit Game"]
    selected = 0
    snapshot = screen.copy()
    panel_w, panel_h = 460, 500
    panel_x, panel_y = WIDTH // 2 - panel_w // 2, HEIGHT // 2 - panel_h // 2
    btn_w, btn_h = 350, 54
    btn_x = WIDTH // 2 - btn_w // 2
    start_y = panel_y + 125

    while True:
        screen.blit(snapshot, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((3, 3, 7, 205))
        screen.blit(overlay, (0, 0))
        draw_vignette(screen, 160)
        draw_panel(screen, panel_x, panel_y, panel_w, panel_h)
        draw_corner_marks(screen, panel_x, panel_y, panel_w, panel_h, GOLD)
        title = font_title.render("PAUSED", True, GOLD_BRIGHT)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, panel_y + 30))
        draw_text(screen, "THE FIGHT WAITS", font_micro, DIM_TEXT,
                  WIDTH // 2 - 58, panel_y + 94, shadow=False)

        mouse = video.get_virtual_mouse_pos((WIDTH, HEIGHT))
        clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "Resume"
                if event.key in (pygame.K_w, pygame.K_UP):
                    selected = (selected - 1) % len(options)
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    selected = (selected + 1) % len(options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return options[selected]
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        for i, label in enumerate(options):
            by = start_y + i * 66
            hovered = btn_x < mouse[0] < btn_x + btn_w and by < mouse[1] < by + btn_h
            if hovered:
                selected = i
            draw_menu_button(screen, btn_x, by, btn_w, btn_h, label,
                             i == selected)
            if clicked and hovered:
                return label

        video.present(screen)
        clock.tick(video.get_fps_limit())


def _cycle(values, current, direction):
    idx = values.index(current) if current in values else 0
    return values[(idx + direction) % len(values)]


def options_menu():
    tabs = ["Controls", "Audio", "Video"]
    state = {"tab": "Controls", "row": 0, "msg": "", "msg_timer": 0}
    snapshot = screen.copy()
    controls = [
        ("W A S D", "Move"), ("SHIFT", "Sprint"),
        ("LMB", "Three-hit light combo"), ("SPACE", "Dash / evade"),
        ("SPACE + LMB", "Dash strike"), ("Q", "Death's Dance"),
        ("E", "Sonic Stream"),
        ("R", "Focus: recover stamina"), ("ESC", "Pause"),
    ]

    def video_rows():
        vs = video.video_state
        return [
            ("Resolution", f"{vs['resolution'][0]} x {vs['resolution'][1]}"),
            ("Fullscreen", "ON" if vs["fullscreen"] else "OFF"),
            ("VSync", "ON" if vs["vsync"] else "OFF"),
            ("FPS Limit", "Unlimited" if vs["fps_limit"] is None else str(vs["fps_limit"])),
        ]

    def change_video_row(row, direction):
        before = dict(video.video_state)
        vs = video.video_state
        if row == 0:
            vs["resolution"] = _cycle(video.RESOLUTIONS, vs["resolution"], direction)
        elif row == 1:
            vs["fullscreen"] = not vs["fullscreen"]
        elif row == 2:
            vs["vsync"] = not vs["vsync"]
        elif row == 3:
            vs["fps_limit"] = _cycle(video.FPS_OPTIONS, vs["fps_limit"], direction)
        try:
            video.apply()
            state["msg"] = ""
        except pygame.error as exc:
            vs.update(before)
            video.apply()
            state["msg"] = f"Could not apply: {exc}"
            state["msg_timer"] = 3000

    panel_w, panel_h = 760, 470
    panel_x, panel_y = WIDTH // 2 - panel_w // 2, HEIGHT // 2 - 215
    tab_w, tab_h = 190, 42
    last_time = pygame.time.get_ticks()

    while True:
        now = pygame.time.get_ticks()
        dt = min(now - last_time, 50)
        last_time = now
        state["msg_timer"] = max(0, state["msg_timer"] - dt)
        screen.blit(snapshot, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((3, 3, 7, 220))
        screen.blit(overlay, (0, 0))
        draw_vignette(screen, 150)

        title = font_title.render("OPTIONS", True, GOLD_BRIGHT)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, panel_y - 90))
        draw_panel(screen, panel_x, panel_y, panel_w, panel_h)
        mouse = video.get_virtual_mouse_pos((WIDTH, HEIGHT))
        clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_TAB:
                    state["tab"] = tabs[(tabs.index(state["tab"]) + 1) % len(tabs)]
                    state["row"] = 0
                if state["tab"] == "Audio" and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    set_music_volume(audio_state["volume"] + (0.1 if event.key == pygame.K_RIGHT else -0.1))
                if state["tab"] == "Video":
                    if event.key in (pygame.K_UP, pygame.K_w):
                        state["row"] = (state["row"] - 1) % len(video_rows())
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        state["row"] = (state["row"] + 1) % len(video_rows())
                    elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        change_video_row(state["row"], 1 if event.key == pygame.K_RIGHT else -1)

        total_tabs_w = tab_w * len(tabs)
        tab_x0 = WIDTH // 2 - total_tabs_w // 2
        for i, tab in enumerate(tabs):
            tx, ty = tab_x0 + i * tab_w, panel_y - 48
            hovered = tx < mouse[0] < tx + tab_w - 5 and ty < mouse[1] < ty + tab_h
            active = tab == state["tab"]
            pygame.draw.rect(screen, (50, 39, 34) if active or hovered else (20, 18, 23),
                             (tx, ty, tab_w - 5, tab_h), border_radius=5)
            pygame.draw.rect(screen, GOLD if active else GOLD_DIM,
                             (tx, ty, tab_w - 5, tab_h), 2, border_radius=5)
            lbl = font_med.render(tab, True, GOLD_BRIGHT if active else CREAM)
            screen.blit(lbl, (tx + (tab_w - 5 - lbl.get_width()) // 2,
                              ty + (tab_h - lbl.get_height()) // 2))
            if clicked and hovered:
                state["tab"], state["row"] = tab, 0

        content_x, content_y = panel_x + 44, panel_y + 38
        if state["tab"] == "Controls":
            draw_text(screen, "COMBAT CONTROLS", font_header, GOLD,
                      content_x, content_y, shadow=False)
            for i, (key, action) in enumerate(controls):
                y = content_y + 58 + i * 42
                pygame.draw.line(screen, (80, 68, 58),
                                 (content_x, y + 28), (panel_x + panel_w - 44, y + 28), 1)
                draw_text(screen, key, font_small, CREAM, content_x, y, shadow=False)
                draw_text(screen, action, font_small, DIM_TEXT,
                          content_x + 260, y, shadow=False)
        elif state["tab"] == "Audio":
            draw_text(screen, "MUSIC", font_header, GOLD, content_x, content_y, shadow=False)
            draw_text(screen, "Use LEFT / RIGHT to adjust", font_small, DIM_TEXT,
                      content_x, content_y + 40, shadow=False)
            bx, by, bw = content_x, content_y + 100, panel_w - 88
            draw_segmented_bar(screen, bx, by, bw, 18, audio_state["volume"], 1.0,
                               GOLD, (38, 31, 28), segments=10)
            pct = font_big.render(f"{int(audio_state['volume'] * 100)}%", True, CREAM)
            screen.blit(pct, (bx + bw // 2 - pct.get_width() // 2, by + 40))
        else:
            draw_text(screen, "DISPLAY", font_header, GOLD, content_x, content_y, shadow=False)
            for i, (label, value) in enumerate(video_rows()):
                y = content_y + 64 + i * 66
                selected = i == state["row"]
                if selected:
                    pygame.draw.rect(screen, (48, 38, 34),
                                     (content_x - 12, y - 12, panel_w - 64, 48),
                                     border_radius=5)
                draw_text(screen, label, font_small, GOLD if selected else CREAM,
                          content_x, y, shadow=False)
                value_lbl = font_small.render((f"<  {value}  >" if selected else value),
                                              True, CREAM if selected else DIM_TEXT)
                screen.blit(value_lbl, (panel_x + panel_w - 44 - value_lbl.get_width(), y))
            if state["msg_timer"] > 0:
                draw_text(screen, state["msg"], font_small, COL_DANGER,
                          content_x, panel_y + panel_h - 40, shadow=False)

        back_hover = WIDTH // 2 - 150 < mouse[0] < WIDTH // 2 + 150 and \
            panel_y + panel_h + 28 < mouse[1] < panel_y + panel_h + 82
        draw_menu_button(screen, WIDTH // 2 - 150, panel_y + panel_h + 28,
                         300, 54, "Back", back_hover)
        if clicked and back_hover:
            return
        video.present(screen)
        clock.tick(video.get_fps_limit())


def name_input_screen():
    play_music("menu")
    name = ""
    cursor_timer = 0
    cursor_visible = True
    while True:
        _menu_backdrop("terrace", 158)
        _draw_brand(96)
        draw_text(screen, "ENTER THE HUNT", font_micro, DIM_TEXT,
                  WIDTH // 2 - 61, 222, shadow=False)

        panel_w, panel_h = 650, 310
        panel_x, panel_y = WIDTH // 2 - panel_w // 2, 330
        draw_panel(screen, panel_x, panel_y, panel_w, panel_h)
        draw_corner_marks(screen, panel_x, panel_y, panel_w, panel_h, GOLD)
        prompt = font_header.render("Name your fighter", True, CREAM)
        screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, panel_y + 42))
        draw_text(screen, "This name appears above your character in battle.",
                  font_small, DIM_TEXT, WIDTH // 2 - 204, panel_y + 82,
                  shadow=False)

        box_w, box_h = 480, 62
        box_x, box_y = WIDTH // 2 - box_w // 2, panel_y + 125
        pygame.draw.rect(screen, (7, 7, 10), (box_x, box_y, box_w, box_h), border_radius=5)
        pygame.draw.rect(screen, GOLD if name else GOLD_DIM,
                         (box_x, box_y, box_w, box_h), 2, border_radius=5)
        cursor_timer += clock.get_time()
        if cursor_timer >= 500:
            cursor_visible = not cursor_visible
            cursor_timer = 0
        shown = name + ("|" if cursor_visible else " ")
        label = font_big.render(shown, True, GOLD_BRIGHT if name else CREAM)
        screen.blit(label, (box_x + 18, box_y + 14))
        hint = "ENTER  Continue" if name.strip() else "Type a name to continue"
        hint_col = GOLD if name.strip() else DIM_TEXT
        draw_text(screen, hint, font_small, hint_col,
                  WIDTH // 2 - font_small.size(hint)[0] // 2,
                  panel_y + 220, shadow=False)

        video.present(screen)
        clock.tick(video.get_fps_limit())
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and name.strip():
                    return name.strip()
                if event.key == pygame.K_ESCAPE:
                    _quit()
                if event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif len(name) < 16 and event.unicode.isprintable():
                    name += event.unicode


def run_upgrade_screen(hero_class, run_state, cleared_stage_idx):
    """Offer a permanent run upgrade before the next stage."""
    play_music("menu")
    choices = boon_choices(cleared_stage_idx, hero_class)
    selected = 0
    summary = run_state.get("last_summary", {})
    next_stage = STAGES[min(cleared_stage_idx + 1, len(STAGES) - 1)]
    card_w, card_h, gap = 390, 315, 34
    total = card_w * 3 + gap * 2
    start_x = WIDTH // 2 - total // 2
    card_y = 445

    while True:
        _menu_backdrop(next_stage["bg"], 188)
        title = font_title.render("CLAIM YOUR REWARD", True, GOLD_BRIGHT)
        # Center the visible letters, not the font surface's asymmetric side
        # bearings.  This fixes the title's apparent rightward shift.
        visible = title.get_bounding_rect(min_alpha=1)
        title_x = round(WIDTH / 2 - (visible.left + visible.width / 2))
        screen.blit(title, (title_x, 66))
        draw_text(screen, f"{STAGES[cleared_stage_idx]['name'].upper()} CLEARED",
                  font_micro, DIM_TEXT, WIDTH // 2 - 86, 132, shadow=False)

        panel_w, panel_h = 850, 150
        panel_x = WIDTH // 2 - panel_w // 2
        draw_panel(screen, panel_x, 195, panel_w, panel_h)
        stats = [
            ("TIME", summary.get("time", "--:--")),
            ("DAMAGE", str(summary.get("damage_dealt", 0))),
            ("KILLS", str(summary.get("kills", 0))),
            ("BEST COMBO", str(summary.get("best_combo", 0))),
        ]
        cell_w = panel_w // len(stats)
        for i, (label, value) in enumerate(stats):
            cx = panel_x + i * cell_w
            if i:
                pygame.draw.line(screen, (76, 65, 57), (cx, 220), (cx, 320), 1)
            v = font_big.render(value, True, CREAM)
            screen.blit(v, (cx + cell_w // 2 - v.get_width() // 2, 230))
            draw_text(screen, label, font_micro, DIM_TEXT,
                      cx + cell_w // 2 - font_micro.size(label)[0] // 2,
                      280, shadow=False)

        mouse = video.get_virtual_mouse_pos((WIDTH, HEIGHT))
        clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _quit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    selected = (selected - 1) % 3
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    selected = (selected + 1) % 3
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    selected = 0
                    apply_boon(run_state, choices[selected])
                    return
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    selected = 1
                    apply_boon(run_state, choices[selected])
                    return
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    selected = 2
                    apply_boon(run_state, choices[selected])
                    return
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    apply_boon(run_state, choices[selected])
                    return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        for i, boon_id in enumerate(choices):
            x = start_x + i * (card_w + gap)
            hovered = x < mouse[0] < x + card_w and card_y < mouse[1] < card_y + card_h
            if hovered:
                selected = i
            active = i == selected
            boon = BOONS[boon_id]
            accent = (136, 82, 204) if boon["tag"] == "ABILITY" else \
                (108, 166, 205) if boon["tag"] == "MOBILITY" else \
                (190, 65, 72) if boon["tag"] == "OFFENSE" else (126, 168, 116)
            draw_panel(screen, x, card_y, card_w, card_h,
                       border_col=accent if active else GOLD_DIM)
            draw_text(screen, f"0{i + 1}", font_micro, accent,
                      x + 24, card_y + 22, shadow=False)
            draw_text(screen, boon["tag"], font_micro, DIM_TEXT,
                      x + card_w - 24 - font_micro.size(boon["tag"])[0],
                      card_y + 22, shadow=False)
            pygame.draw.line(screen, accent, (x + 24, card_y + 55),
                             (x + card_w - 24, card_y + 55), 2)
            name = font_header.render(boon["name"], True, CREAM)
            screen.blit(name, (x + card_w // 2 - name.get_width() // 2, card_y + 96))
            desc = font_med.render(boon["description"], True, accent)
            screen.blit(desc, (x + card_w // 2 - desc.get_width() // 2, card_y + 158))
            owned = sum(1 for b in run_state.get("boons", []) if b == boon_id)
            if owned:
                draw_text(screen, f"Already owned x{owned}", font_small, DIM_TEXT,
                          x + card_w // 2 - 66, card_y + 210, shadow=False)
            if active:
                draw_text(screen, "ENTER TO CLAIM", font_micro, GOLD_BRIGHT,
                          x + card_w // 2 - 57, card_y + 266, shadow=False)
            if clicked and hovered:
                apply_boon(run_state, boon_id)
                return

        destination = f"NEXT: {next_stage['name'].upper()}"
        draw_text(screen, destination, font_micro, DIM_TEXT,
                  WIDTH // 2 - font_micro.size(destination)[0] // 2,
                  HEIGHT - 105, shadow=False)
        video.present(screen)
        clock.tick(video.get_fps_limit())
