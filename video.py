"""
Actual OS window / display mode handling.

Everything else in the game draws onto a fixed 1920x1080 virtual
canvas (settings.screen) regardless of what resolution the player
picks — present() scales that canvas onto the real window each
frame. This means changing resolution here never requires touching
any layout code anywhere else in the game.
"""
import pygame

RESOLUTIONS = [
    (1280, 720),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
    (3840, 2160),
]

# None here means "unlimited" (uncapped) — pygame.Clock.tick(0) is uncapped.
FPS_OPTIONS = [30, 60, 75, 120, 144, None]

video_state = {
    "resolution": (1920, 1080),
    "fullscreen": True,
    "vsync": True,
    "fps_limit": 60,
}

real_screen = None  # the actual OS window surface, created by apply()


def apply():
    """(Re)create the real OS window from the current video_state."""
    global real_screen
    w, h = video_state["resolution"]
    flags = pygame.FULLSCREEN if video_state["fullscreen"] else 0
    try:
        real_screen = pygame.display.set_mode(
            (w, h), flags, vsync=1 if video_state["vsync"] else 0)
    except TypeError:
        # Older SDL/pygame builds don't accept the vsync kwarg for this
        # flag combination — fall back to a plain mode switch instead
        # of crashing over a nonessential setting.
        real_screen = pygame.display.set_mode((w, h), flags)
    return real_screen


def get_fps_limit():
    """0 means uncapped, which is exactly what pygame.Clock.tick(0) wants."""
    return video_state["fps_limit"] or 0


def get_virtual_mouse_pos(virtual_size):
    """Mouse position, converted from real-window pixels into the fixed
    virtual-canvas coordinate space that every menu/HUD is laid out in."""
    mx, my = pygame.mouse.get_pos()
    rw, rh = real_screen.get_size()
    vw, vh = virtual_size
    if rw == 0 or rh == 0:
        return (mx, my)
    return (mx * vw / rw, my * vh / rh)


def present(virtual_surface):
    """Scale the fixed-resolution virtual canvas onto the real window
    and flip it. Call this once per frame instead of pygame.display.flip()."""
    target_size = real_screen.get_size()
    if virtual_surface.get_size() == target_size:
        real_screen.blit(virtual_surface, (0, 0))
    else:
        pygame.transform.scale(virtual_surface, target_size, real_screen)
    pygame.display.flip()
