"""
Entry point. Run this file to play.
"""
import pygame
from game_data import STAGES
from screens import name_input_screen, run_upgrade_screen
from gameplay import stage_screen
from progression import new_run_state

hero_name = name_input_screen()
chosen_class = "Assassin"
run_state = new_run_state()
stage_idx = 0
while True:
    result = stage_screen(chosen_class, hero_name, stage_idx, run_state)
    if result in ("retry", "restart"):
        continue
    elif result == "next":
        run_upgrade_screen(chosen_class, run_state, stage_idx)
        stage_idx += 1
        if stage_idx >= len(STAGES):
            break
    else:
        break
pygame.quit()
