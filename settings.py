"""
Global display setup, fonts, and the UI color palette.
Everything here is a plain constant — other modules do
`from settings import *` so these are available everywhere
without repeating the same setup in every file.
"""
import pygame
import video

pygame.init()

WIDTH, HEIGHT = 1920, 1080

# 'screen' is a fixed-resolution VIRTUAL canvas — every draw call in the
# game targets this, regardless of the player's actual chosen resolution.
# video.apply() creates the real OS window, and video.present(screen)
# scales this canvas onto it once per frame. This is what lets the video
# settings menu change resolution/fullscreen freely without any layout
# code anywhere else needing to know about it.
screen = pygame.Surface((WIDTH, HEIGHT))
video.apply()
pygame.display.set_caption("Mini Fight Game")
clock = pygame.time.Clock()

DISPLAY_SIZE = (220, 220)

# ── Fonts ─────────────────────────────────────────────────────────────────────
font_big = pygame.font.SysFont("Consolas", 28, bold=True)
font_med = pygame.font.SysFont("Consolas", 20)
font_small = pygame.font.SysFont("Consolas", 16)
font_title = pygame.font.SysFont("Georgia", 58, bold=True)
font_header = pygame.font.SysFont("Georgia", 24, bold=True)
font_label = pygame.font.SysFont("Georgia", 17, italic=True)

# ── Basic colors ──────────────────────────────────────────────────────────────
WHITE = (255, 255, 255)
BLACK = (0,   0,   0)
RED = (200, 40,  40)
GREEN = (50,  200, 80)
YELLOW = (255, 220, 50)

# ── UI theme palette ──────────────────────────────────────────────────────────
GOLD = (198, 165, 92)
GOLD_DIM = (120, 100, 62)
CREAM = (232, 222, 200)
DIM_TEXT = (168, 158, 144)
COL_HP = (176, 34, 42)
COL_HP_DARK = (46, 12, 14)
COL_STA = (64, 146, 196)
COL_STA_DARK = (14, 40, 58)
