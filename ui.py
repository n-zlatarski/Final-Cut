"""
Reusable drawing helpers for HUD panels, bars, text, and buttons.
"""
import pygame
from settings import *

def draw_text(surf, text, font, color, x, y, shadow=True):
    if shadow:
        surf.blit(font.render(text, True, BLACK), (x+1, y+1))
    surf.blit(font.render(text, True, color), (x, y))


def draw_panel(surf, x, y, w, h, border_col=None):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    top = (26, 20, 24, 225)
    bot = (9, 7, 10, 225)
    steps = max(1, h)
    for i in range(steps):
        t = i / max(1, steps - 1)
        col = (int(top[0] + (bot[0]-top[0])*t),
               int(top[1] + (bot[1]-top[1])*t),
               int(top[2] + (bot[2]-top[2])*t),
               225)
        pygame.draw.line(s, col, (0, i), (w, i))
    surf.blit(s, (x, y))
    bc = border_col or GOLD_DIM
    pygame.draw.rect(surf, bc, (x, y, w, h), 2, border_radius=6)
    pygame.draw.rect(surf, (255, 255, 255, 25),
                     (x+2, y+2, w-4, h-4), 1, border_radius=5)


def draw_ornate_frame(surf, x, y, w, h, col=GOLD):
    pygame.draw.rect(surf, (8, 7, 9), (x, y, w, h))
    pygame.draw.rect(surf, col, (x, y, w, h), 2)
    t = 10
    for cx, cy, dx, dy in [(x, y, 1, 1), (x+w, y, -1, 1), (x, y+h, 1, -1), (x+w, y+h, -1, -1)]:
        pygame.draw.line(surf, col, (cx, cy), (cx + t*dx, cy), 3)
        pygame.draw.line(surf, col, (cx, cy), (cx, cy + t*dy), 3)


def draw_stat_bar(surf, x, y, w, h, val, max_val, col_main, col_dark, label=None, font=None, value_text=None):
    max_val = max(1, max_val)
    val = max(0, val)
    pygame.draw.rect(surf, col_dark, (x, y, w, h), border_radius=h // 2)
    fill_w = int(w * val / max_val)
    if fill_w > 0:
        pygame.draw.rect(surf, col_main, (x, y, fill_w, h),
                         border_radius=h // 2)
        hi = tuple(min(255, c + 70) for c in col_main)
        pygame.draw.rect(surf, hi, (x, y, fill_w,
                         max(2, h // 3)), border_radius=h // 2)
    pygame.draw.rect(surf, GOLD_DIM, (x, y, w, h), 2, border_radius=h // 2)
    if label and font:
        txt = value_text if value_text is not None else f"{label}  {int(val)}/{int(max_val)}"
        lbl = font.render(txt, True, CREAM)
        surf.blit(lbl, (x, y - lbl.get_height() - 2))


def draw_menu_button(surf, x, y, w, h, label, hovered, font=None):
    font = font or font_med
    base = (34, 28, 30) if not hovered else (52, 40, 34)
    pygame.draw.rect(surf, base, (x, y, w, h), border_radius=6)
    pygame.draw.rect(surf, GOLD if hovered else GOLD_DIM,
                     (x, y, w, h), 2, border_radius=6)
    lbl = font.render(label, True, GOLD if hovered else CREAM)
    surf.blit(lbl, (x + w//2 - lbl.get_width()//2,
                   y + h//2 - lbl.get_height()//2))


