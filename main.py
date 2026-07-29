import pygame
from game_data import STAGES
from screens import name_input_screen, class_select_screen
from gameplay import stage_screen

hero_name = name_input_screen()
chosen_class = class_select_screen()
stage_idx = 0
while True:
    result = stage_screen(chosen_class, hero_name, stage_idx)
    if result == "change_class":
        chosen_class = class_select_screen()
    elif result == "retry":
        continue
    elif result == "next":
        stage_idx += 1
        if stage_idx >= len(STAGES):
            break
    else:
        break
pygame.quit()
