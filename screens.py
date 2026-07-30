"""
Menu screens: pause menu, options/controls, name entry, and class
selection.
"""
import pygame
import sys
from settings import *
from ui import draw_text, draw_panel, draw_menu_button
from audio import play_music, set_music_volume, audio_state
from animator import Animator
from sprite_loaders import dir_frames
from game_data import STAGE_BGS, warrior_anims, _w_idle_rows, CLASS_STATS

def pause_menu():
    options = ["Resume", "Options", "Change Class", "Exit Game"]
    btn_w, btn_h = 320, 58
    btn_x = WIDTH // 2 - btn_w // 2
    spacing = 74
    start_y = HEIGHT // 2 - (len(options) * spacing) // 2

    while True:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        screen.blit(overlay, (0, 0))
        title = font_title.render("PAUSED", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, start_y - 100))
        mouse = pygame.mouse.get_pos()
        clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "Resume"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        for i, label in enumerate(options):
            bx = btn_x
            by = start_y + i * spacing
            hovered = bx < mouse[0] < bx + btn_w and by < mouse[1] < by + btn_h
            draw_menu_button(screen, bx, by, btn_w, btn_h, label, hovered)
            if clicked and hovered:
                return label

        pygame.display.flip()
        clock.tick(60)


def options_menu():
    btn_w, btn_h = 300, 55
    btn_x = WIDTH // 2 - btn_w // 2
    btn_y = HEIGHT // 2 + 170
    controls = [
        ("WASD",          "Move"),
        ("LShift",        "Sprint"),
        ("LClick",        "Attack"),
        ("LShift+LClick", "Run Attack"),
        ("R",             "Recover stamina"),
        ("ESC",           "Pause menu"),
    ]
    panel_w, panel_h = 460, 290
    panel_x = WIDTH // 2 - panel_w // 2
    panel_y = HEIGHT // 2 - 165
    while True:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 205))
        screen.blit(overlay, (0, 0))
        title = font_title.render("OPTIONS", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 250))
        draw_panel(screen, panel_x, panel_y, panel_w, panel_h)
        hdr = font_header.render("Controls", True, GOLD)
        screen.blit(hdr, (panel_x + 24, panel_y + 16))
        for i, (key, action) in enumerate(controls):
            row_y = panel_y + 60 + i * 28
            draw_text(screen, key,    font_small, CREAM,
                      panel_x + 24, row_y, shadow=False)
            draw_text(screen, action, font_small, DIM_TEXT,
                      panel_x + 220, row_y, shadow=False)
        vol_y = panel_y + 60 + len(controls) * 28 + 20
        draw_text(screen, "Music Volume  (←/→)", font_small,
                  GOLD, panel_x + 24, vol_y, shadow=False)
        bar_x, bar_y2, bar_w = panel_x + 24, vol_y + 24, panel_w - 48
        pygame.draw.rect(screen, (30, 25, 28), (bar_x, bar_y2, bar_w, 10))
        pygame.draw.rect(screen, GOLD, (bar_x, bar_y2,
                         int(bar_w * audio_state["volume"]), 10))
        pygame.draw.rect(screen, GOLD_DIM, (bar_x, bar_y2, bar_w, 10), 1)
        mouse = pygame.mouse.get_pos()
        hovered = btn_x < mouse[0] < btn_x + \
            btn_w and btn_y < mouse[1] < btn_y + btn_h
        draw_menu_button(screen, btn_x, btn_y, btn_w, btn_h, "Back", hovered)
        pygame.display.flip()
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
                set_music_volume(audio_state["volume"] - 0.1)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
                set_music_volume(audio_state["volume"] + 0.1)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and hovered:
                return

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 0 — Name input
# ══════════════════════════════════════════════════════════════════════════════


def name_input_screen():
    play_music("menu")
    name = ""
    cursor_visible = True
    cursor_timer = 0
    while True:
        screen.blit(STAGE_BGS["terrace"], (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        title = font_title.render("Final Cut", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 200))
        draw_text(screen, "Enter your name", font_label,
                  CREAM, WIDTH//2 - 90, HEIGHT//2 - 100, shadow=False)
        box_w, box_h = 420, 58
        box_x = WIDTH//2 - box_w//2
        box_y = HEIGHT//2 - 20
        draw_panel(screen, box_x, box_y, box_w, box_h)
        cursor_timer += clock.get_time()
        if cursor_timer > 500:
            cursor_visible = not cursor_visible
            cursor_timer = 0
        display_text = name + ("|" if cursor_visible else " ")
        screen.blit(font_big.render(display_text, True, CREAM),
                    (box_x + 16, box_y + 12))
        draw_text(screen, "Press ENTER to continue", font_small,
                  DIM_TEXT, WIDTH//2 - 120, HEIGHT//2 + 60, shadow=False)
        pygame.display.flip()
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and name.strip():
                    return name.strip()
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif len(name) < 16 and event.unicode.isprintable():
                    name += event.unicode

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — Class selection
# ══════════════════════════════════════════════════════════════════════════════


def class_select_screen():
    play_music("menu")
    classes = ["Warrior"]

    warrior_preview_anims = warrior_anims.copy()
    warrior_preview_anims["idle"] = dir_frames(_w_idle_rows, "down")

    previews = {
        "Warrior": Animator(warrior_preview_anims, default="idle", fps=8),
    }
    descriptions = {
        "Warrior": ["HP: 120  Stamina: 260", "Heavy sword fighter.", "High HP, strong attacks."],
    }
    CARD_W = DISPLAY_SIZE[0] + 20
    CARD_H = DISPLAY_SIZE[1] + 110
    GAP = 40
    total_w = CARD_W * 1
    start_x = WIDTH // 2 - total_w // 2
    card_y = HEIGHT // 2 - CARD_H // 2
    positions = {
        "Warrior": (start_x, card_y),
    }
    last_time = pygame.time.get_ticks()
    while True:
        now = pygame.time.get_ticks()
        dt = min(now - last_time, 50)
        last_time = pygame.time.get_ticks()
        for p in previews.values():
            p.update(dt)
        screen.blit(STAGE_BGS["terrace"], (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))
        title = font_title.render("Final Cut", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        draw_text(screen, "Choose your class", font_label,
                  CREAM, WIDTH//2 - 80, 122, shadow=False)
        mouse = pygame.mouse.get_pos()
        for cls in classes:
            cx, cy = positions[cls]
            frame = previews[cls].get_frame()
            _, ih = frame.get_size()
            card_x, card_y2, card_w, card_h = cx, cy, CARD_W, CARD_H
            is_hovered = card_x < mouse[0] < card_x + \
                card_w and card_y2 < mouse[1] < card_y2+card_h
            draw_panel(screen, card_x, card_y2, card_w, card_h,
                      border_col=GOLD if is_hovered else GOLD_DIM)
            screen.blit(frame, (cx + 10, cy + 10))
            lbl = font_header.render(cls, True, GOLD if is_hovered else CREAM)
            screen.blit(
                lbl, (cx + CARD_W//2 - lbl.get_width()//2, cy + ih + 14))
            for di, line in enumerate(descriptions[cls]):
                dl = font_small.render(line, True, DIM_TEXT)
                screen.blit(dl, (cx + CARD_W//2 - dl.get_width() //
                            2, cy + ih + 40 + di * 18))
        draw_text(screen, "Click a class to begin", font_small,
                  DIM_TEXT, WIDTH//2-100, HEIGHT-50, shadow=False)
        pygame.display.flip()
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for cls in classes:
                    cx, cy = positions[cls]
                    if cx < mouse[0] < cx+CARD_W and cy < mouse[1] < cy+CARD_H:
                        return cls

