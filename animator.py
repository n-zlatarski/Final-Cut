"""
Frame-by-frame sprite animation player.
"""
import pygame


class Animator:
    def __init__(self, anims, default="idle", fps=8):
        self.anims = anims
        self.current = default
        self.frame_idx = 0
        self.fps = fps
        self.fps_overrides = {}   # anim_name -> custom fps
        self.timer = 0
        self.one_shot = False
        self.done = False
        self.locked = False

    def play(self, name, frames=None, one_shot=False, force=False, fps=None):
        if self.locked and not force:
            return
        if fps is not None:
            self.fps_overrides[name] = fps

        switching_anim = self.current != name
        frames_changed = frames is not None and self.anims.get(
            name) is not frames

        if frames is not None:
            self.anims[name] = frames

        if switching_anim or frames_changed or force:
            self.current = name
            self.frame_idx = 0
            self.timer = 0
            self.one_shot = one_shot
            self.done = False
            self.locked = one_shot

    def update(self, dt):
        frames = self.anims.get(self.current, list(self.anims.values())[0])
        current_fps = self.fps_overrides.get(self.current, self.fps)
        self.timer += dt
        ms_per_frame = 1000 / current_fps
        if self.timer >= ms_per_frame:
            self.timer -= ms_per_frame
            self.frame_idx += 1
            if self.frame_idx >= len(frames):
                if self.one_shot:
                    self.frame_idx = len(frames) - 1
                    self.done = True
                    self.locked = False
                else:
                    self.frame_idx = 0

    def get_frame(self):
        frames = self.anims.get(self.current, list(self.anims.values())[0])
        return frames[min(self.frame_idx, len(frames)-1)]

