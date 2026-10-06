"""Load four-direction wolf and Castle Archer sprite sheets and create their ground shadows."""
from pathlib import Path
import pygame

CELL_SIZE = 128
SCALE = 3
PIVOT = (192, 312)
DIRECTIONS = ('down', 'left', 'right', 'up')
FRAME_COUNTS = {'idle': 4, 'walk': 6, 'attack': 8, 'hurt': 4, 'dead': 8}

def load_directional_enemy_frames(folder, frame_counts=None, *, cell_size=CELL_SIZE, scale=SCALE):
    result = {direction: {} for direction in DIRECTIONS}
    display_cell = round(cell_size*scale)
    for state, count in (frame_counts or FRAME_COUNTS).items():
        sheet = pygame.image.load(str(Path(folder)/f'{state}.png')).convert_alpha()
        if sheet.get_size() != (cell_size*count, cell_size*4):
            raise ValueError(f'Invalid directional enemy sheet: {folder}/{state}.png')
        for row, direction in enumerate(DIRECTIONS):
            result[direction][state] = [pygame.transform.scale(
                sheet.subsurface((i*cell_size,row*cell_size,cell_size,cell_size)),
                (display_cell,display_cell)) for i in range(count)]
    return result

def ground_shadow(brute=False, scale=SCALE):
    size = (30 if brute else 25, 7)
    shadow = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (5, 8, 7, 105), shadow.get_rect())
    return pygame.transform.scale(shadow, (round(size[0]*scale),round(size[1]*scale)))
