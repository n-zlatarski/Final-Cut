"""
Low-level asset loading and sprite-sheet slicing helpers. Pure
functions only — no globals from the rest of the game.
"""
import pygame
import os

def load_img(path, size):
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, size)
    except Exception:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((180, 60, 200, 200))
        return surf

# ── Sprite sheet loader ───────────────────────────────────────────────────────


def load_sheet_all_rows(path, num_cols, num_rows, display_size=(128, 128)):
    try:
        sheet = pygame.image.load(path).convert_alpha()
        sw, sh = sheet.get_size()
        frame_w = sw // num_cols
        frame_h = sh // num_rows
        print(
            f"Loaded {path} | {num_cols}x{num_rows} grid | frame={frame_w}x{frame_h}")
        all_rows = []
        for row in range(num_rows):
            frames = []
            for col in range(num_cols):
                frame_surf = pygame.Surface(
                    (frame_w, frame_h), pygame.SRCALPHA)
                frame_surf.fill((0, 0, 0, 0))
                frame_surf.blit(sheet, (0, 0), pygame.Rect(
                    col * frame_w, row * frame_h, frame_w, frame_h))
                pixel_count = sum(
                    1 for x in range(0, frame_w, 4)
                    for y in range(0, frame_h, 4)
                    if frame_surf.get_at((x, y))[3] > 30
                )
                if pixel_count < 5:
                    continue
                scaled = pygame.transform.scale(frame_surf, display_size)
                frames.append(scaled)
            if frames:
                all_rows.append(frames)
        return all_rows
    except Exception as e:
        print(f"FAILED to load {path}: {e}")
        surf = pygame.Surface(display_size, pygame.SRCALPHA)
        surf.fill((180, 60, 200, 200))
        return [[surf]]


def load_sheet(path, num_cols, num_rows, display_size=(128, 128)):
    all_rows = load_sheet_all_rows(path, num_cols, num_rows, display_size)
    if len(all_rows) >= 2:
        return all_rows[1]
    return all_rows[0] if all_rows else [pygame.Surface(display_size, pygame.SRCALPHA)]


def dir_frames(rows, direction):
    idx = {"down": 0, "left": 1, "right": 2, "up": 3}.get(direction, 0)
    if idx < len(rows):
        return rows[idx]
    return rows[0]


def vamp_dir_frames(rows, direction):
    idx = {"down": 0, "up": 1, "left": 2, "right": 3}.get(direction, 0)
    if idx < len(rows):
        return rows[idx]
    return rows[0]


def resolve_path(path):
    if os.path.exists(path):
        return path
    folder, fname = os.path.split(path)
    candidates = [
        os.path.join(folder, fname.replace("_", " ")),
        os.path.join(folder, fname.replace(" ", "_")),
        os.path.join(folder, fname.replace("_", "")),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # try case-insensitive match within the folder as a last resort
    if os.path.isdir(folder):
        for entry in os.listdir(folder):
            if entry.lower() == fname.lower():
                return os.path.join(folder, entry)
    return path


def load_side_sheet_raw(path, frame_size=128):
    path = resolve_path(path)
    try:
        sheet = pygame.image.load(path).convert_alpha()
        sw, sh = sheet.get_size()
        num_frames = max(1, sw // frame_size)
        frames = []
        for i in range(num_frames):
            frame_surf = pygame.Surface((frame_size, sh), pygame.SRCALPHA)
            frame_surf.blit(sheet, (0, 0), pygame.Rect(
                i * frame_size, 0, frame_size, sh))
            frames.append(frame_surf)
        return frames
    except Exception as e:
        print(f"FAILED to load {path}: {e}")
        surf = pygame.Surface((frame_size, frame_size), pygame.SRCALPHA)
        surf.fill((180, 60, 200, 200))
        return [surf]


def _frame_bbox(surface):
    mask = pygame.mask.from_surface(surface)
    rects = mask.get_bounding_rects()
    if not rects:
        return None
    r = rects[0]
    for rr in rects[1:]:
        r = r.union(rr)
    return r


def union_bbox(frame_lists, fallback_size):
    result = None
    for frames in frame_lists:
        for f in frames:
            b = _frame_bbox(f)
            if b is None:
                continue
            result = b if result is None else result.union(b)
    if result is None:
        return pygame.Rect(0, 0, *fallback_size)
    return result


def crop_and_fit_height(frame, crop_rect, target_h):
    cropped = pygame.Surface(
        (crop_rect.width, crop_rect.height), pygame.SRCALPHA)
    cropped.blit(frame, (0, 0), crop_rect)
    scale = target_h / max(1, crop_rect.height)
    new_w = max(1, round(crop_rect.width * scale))
    new_h = max(1, round(crop_rect.height * scale))
    return pygame.transform.scale(cropped, (new_w, new_h))


def flip_frames(frames):
    return [pygame.transform.flip(f, True, False) for f in frames]


