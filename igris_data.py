"""Fixed-grid Igris assets and authored timing shared by rendering and combat."""
from itertools import accumulate
from pathlib import Path

import pygame

from igris_animator import IgrisAnimator


IGRIS_SCALE = 3
# A small presentation adjustment, applied uniformly to every authored pose.
IGRIS_WIDTH_RATIO = 0.90
IGRIS_BANK = IgrisAnimator(
    Path(__file__).resolve().parent / "assets/Blood_Red_Commander/GameReadyDetail")
IGRIS_PIVOT = tuple(value * IGRIS_SCALE for value in IGRIS_BANK.pivot)
IGRIS_STATE_CLIPS = {
    "idle": "Idle", "idle_alert": "Idle_Alert",
    "walk": "Walk", "run": "Run", "dash": "Dash",
    "run_attack": "Run_Attack", "dash_attack": "Dash_Attack",
    "attack": "Attack1", "overhead_slash": "Attack2",
    "ground_slam": "Attack3", "ranged_thrust": "Attack1",
    "hurt": "Hurt", "dead": "Death",
}
IGRIS_DURATIONS = {
    state: IGRIS_BANK.clips[name].durations_ms
    for state, name in IGRIS_STATE_CLIPS.items()
}
IGRIS_FRAME_ENDS = {
    state: tuple(accumulate(durations))
    for state, durations in IGRIS_DURATIONS.items()
}
IGRIS_LOOP_STATES = {
    state for state, name in IGRIS_STATE_CLIPS.items()
    if IGRIS_BANK.clips[name].loop
}


def render_igris_frame(frame):
    """Refine pixel edges and narrow the sprite around its fixed feet pivot.

    Scale2x uses neighbouring pixel colors to soften the large square steps.
    A single pass keeps the pixel-art palette and avoids a blurred texture.
    Refinement happens once at load time, never during combat playback.
    """
    size = tuple(value * IGRIS_SCALE for value in IGRIS_BANK.cell_size)
    refined = pygame.transform.scale2x(frame)
    width = round(size[0] * IGRIS_WIDTH_RATIO)
    slim = pygame.transform.scale(refined, (width, size[1]))
    canvas = pygame.Surface(size, pygame.SRCALPHA)
    # Scale horizontally about the pivot, rather than the bounding box of a
    # particular pose: the sword and cape cannot shift the body sideways.
    scaled_pivot_x = round(IGRIS_BANK.pivot[0] * width / frame.get_width())
    canvas.blit(slim, (IGRIS_PIVOT[0] - scaled_pivot_x, 0))
    return canvas


def load_igris_frames():
    """Keep every pose on the same canvas and at the same standing height."""
    return {
        direction: {
            state: [render_igris_frame(frame)
                    for frame in IGRIS_BANK.clips[name].frames[row]]
            for state, name in IGRIS_STATE_CLIPS.items()
        }
        for row, direction in enumerate(IGRIS_BANK.directions)
    }
