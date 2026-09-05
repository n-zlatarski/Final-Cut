"""Launch the campaign, or use --igris to go directly to the boss fight."""
import argparse
import os
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Final Cut")
    parser.add_argument("--igris", action="store_true",
                        help="Start in the throne room with Igris")
    args = parser.parse_args(argv)
    # Asset paths also work when launched from another directory.
    os.chdir(Path(__file__).resolve().parent)
    import pygame
    from game_data import STAGES
    from screens import name_input_screen, run_upgrade_screen
    from gameplay import stage_screen
    from progression import new_run_state

    hero_name = name_input_screen()
    chosen_class = "Assassin"
    run_state = new_run_state()
    stage_idx = len(STAGES) - 1 if args.igris else 0
    while True:
        result = stage_screen(chosen_class, hero_name, stage_idx, run_state,
                              boss_only=args.igris)
        if result in ("retry", "restart"):
            continue
        if result == "next":
            run_upgrade_screen(chosen_class, run_state, stage_idx)
            stage_idx += 1
            if stage_idx >= len(STAGES):
                break
        else:
            break
    pygame.quit()


if __name__ == "__main__":
    main()
