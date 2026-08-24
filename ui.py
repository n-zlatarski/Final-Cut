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
    top = (*PANEL_TOP, 238)
    bot = (*PANEL_BOTTOM, 238)
    steps = max(1, h)
    for i in range(steps):
        t = i / max(1, steps - 1)
        col = (int(top[0] + (bot[0]-top[0])*t),
               int(top[1] + (bot[1]-top[1])*t),
               int(top[2] + (bot[2]-top[2])*t),
               225)
        pygame.draw.line(s, col, (0, i), (w, i))
    pygame.draw.rect(surf, (0, 0, 0, 110), (x + 8, y + 10, w, h), border_radius=8)
    surf.blit(s, (x, y))
    bc = border_col or GOLD_DIM
    pygame.draw.rect(surf, bc, (x, y, w, h), 2, border_radius=8)
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


def draw_segmented_bar(surf, x, y, w, h, val, max_val, col_main, col_dark,
                       segments=12, lag_value=None):
    """A compact combat bar with optional delayed-damage backing."""
    max_val = max(1, max_val)
    val = max(0, min(max_val, val))
    lag_value = val if lag_value is None else max(val, min(max_val, lag_value))
    pygame.draw.rect(surf, (5, 5, 7), (x - 2, y - 2, w + 4, h + 4),
                     border_radius=4)
    pygame.draw.rect(surf, col_dark, (x, y, w, h), border_radius=3)
    lag_w = int(w * lag_value / max_val)
    if lag_w:
        pygame.draw.rect(surf, (215, 182, 106), (x, y, lag_w, h),
                         border_radius=3)
    fill_w = int(w * val / max_val)
    if fill_w:
        pygame.draw.rect(surf, col_main, (x, y, fill_w, h), border_radius=3)
        hi = tuple(min(255, c + 54) for c in col_main)
        pygame.draw.rect(surf, hi, (x, y, fill_w, max(2, h // 3)),
                         border_radius=3)
    gap = w / max(1, segments)
    for i in range(1, segments):
        gx = int(x + i * gap)
        pygame.draw.line(surf, (5, 5, 8), (gx, y + 1), (gx, y + h - 2), 1)
    pygame.draw.rect(surf, GOLD_DIM, (x, y, w, h), 1, border_radius=3)


def draw_keycap(surf, x, y, key, active=False, size=34):
    col = GOLD_BRIGHT if active else GOLD_DIM
    bg = (55, 43, 37) if active else (18, 16, 20)
    pygame.draw.rect(surf, (0, 0, 0, 125), (x + 3, y + 4, size, size),
                     border_radius=6)
    pygame.draw.rect(surf, bg, (x, y, size, size), border_radius=6)
    pygame.draw.rect(surf, col, (x, y, size, size), 2, border_radius=6)
    lbl = font_micro.render(key, True, CREAM if not active else GOLD_BRIGHT)
    surf.blit(lbl, (x + size // 2 - lbl.get_width() // 2,
                    y + size // 2 - lbl.get_height() // 2))


def draw_vignette(surf, strength=120, color=(0, 0, 0)):
    """Cheap layered vignette that works without external shader assets."""
    strength = max(0, min(255, int(strength)))
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    steps = 8
    for i in range(steps):
        inset_x = int(i * WIDTH * 0.018)
        inset_y = int(i * HEIGHT * 0.025)
        alpha = int(strength * (1 - i / steps) * 0.34)
        pygame.draw.rect(overlay, (*color, alpha),
                         (inset_x, inset_y,
                          WIDTH - inset_x * 2, HEIGHT - inset_y * 2),
                         max(12, int(HEIGHT * 0.025)))
    surf.blit(overlay, (0, 0))


def draw_corner_marks(surf, x, y, w, h, col=GOLD_DIM, length=18):
    for cx, cy, dx, dy in (
        (x, y, 1, 1), (x + w, y, -1, 1),
        (x, y + h, 1, -1), (x + w, y + h, -1, -1),
    ):
        pygame.draw.line(surf, col, (cx, cy), (cx + length * dx, cy), 2)
        pygame.draw.line(surf, col, (cx, cy), (cx, cy + length * dy), 2)


def draw_menu_button(surf, x, y, w, h, label, hovered, font=None):
    font = font or font_med
    base = (25, 22, 28) if not hovered else (58, 43, 35)
    pygame.draw.rect(surf, (0, 0, 0, 120), (x + 5, y + 6, w, h), border_radius=6)
    pygame.draw.rect(surf, base, (x, y, w, h), border_radius=6)
    pygame.draw.rect(surf, GOLD if hovered else GOLD_DIM,
                     (x, y, w, h), 2, border_radius=6)
    if hovered:
        # Draw the tint on an alpha surface and cover the whole button. Drawing
        # RGBA directly onto the RGB game canvas made the old half-height tint
        # turn into the opaque cream block visible in the pause-menu screenshot.
        tint = pygame.Surface((w - 6, h - 6), pygame.SRCALPHA)
        tint.fill((255, 225, 165, 24))
        surf.blit(tint, (x + 3, y + 3))
    lbl = font.render(label, True, GOLD_BRIGHT if hovered else CREAM)
    surf.blit(lbl, (x + w//2 - lbl.get_width()//2,
                   y + h//2 - lbl.get_height()//2))
