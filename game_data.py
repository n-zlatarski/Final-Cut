"""
All game configuration and asset loading: stage backgrounds, enemy
sprite packs, the Warrior and Vampire sheets, and class stats. This
module has side effects at import time (it loads every image) —
import it once, early.
"""
from settings import *
from sprite_loaders import (
    load_img, load_sheet_all_rows, load_sheet, load_side_sheet_raw,
    union_bbox, crop_and_fit_height, flip_frames,
)

# ── Stages ────────────────────────────────────────────────────────────────────
STAGE_BG_FILES = {
    "dead_forest": "assets/dead forest.png",
    "terrace":     "assets/terrace.png",
    "castle":      "assets/castle.png",
    "throne_room": "assets/throne room.png",
}
STAGE_BGS = {key: load_img(path, (WIDTH, HEIGHT))
             for key, path in STAGE_BG_FILES.items()}

STAGES = [
    {"name": "Dead Forest",  "bg": "dead_forest",
     "enemies": ["skeleton_archer", "skeleton_spearman", "skeleton_warrior"], "wave_mult": 1.0},
    {"name": "Castle",       "bg": "castle",
     "enemies": ["skeleton_archer", "skeleton_spearman", "skeleton_warrior"], "wave_mult": 1.4},
    {"name": "Terrace",      "bg": "terrace",
     "enemies": ["knight1", "knight2", "knight3"], "wave_mult": 1.0},
    {"name": "Throne Room",  "bg": "throne_room",
     "enemies": ["knight1", "knight2", "knight3"], "wave_mult": 1.4, "boss": "vampire"},
]

# ── Enemy types ───────────────────────────────────────────────────────────────
ENEMY_TYPES = {
    "knight1":           dict(folder="assets/Knight_1",           hp=70, dmg=(10, 18), speed=1.8, display=(195, 195)),
    "knight2":           dict(folder="assets/Knight_2",           hp=70, dmg=(10, 18), speed=1.8, display=(195, 195)),
    "knight3":           dict(folder="assets/Knight_3",           hp=70, dmg=(10, 18), speed=1.8, display=(195, 195)),
    "skeleton_archer":   dict(folder="assets/Skeleton_Archer",   hp=40, dmg=(6, 12),  speed=1.4, display=(180, 180), ranged=True, atk_range=520),
    "skeleton_spearman": dict(folder="assets/Skeleton_Spearman", hp=50, dmg=(8, 14),  speed=1.6, display=(185, 185)),
    "skeleton_warrior":  dict(folder="assets/Skeleton_Warrior",  hp=55, dmg=(9, 16),  speed=1.7, display=(185, 185)),
}
# Vampire boss uses a separate 4-directional sheet pipeline (see below,
# next to the Warrior sheets) since its sprite pack is laid out like the
# Swordsman's, not like the single-row knight/skeleton packs.
VAMPIRE_STATS = dict(hp=220, dmg=(14, 22), speed=1.7)

ENEMY_ANIM_FILES = {
    "idle": "Idle.png", "walk": "Walk.png", "attack": "Attack_1.png",
    "hurt": "Hurt.png", "dead": "Dead.png",
}
# Each entry: {"right": {anim_name: [frames]}, "left": {anim_name: [frames]}}
ENEMY_ANIM_SETS = {}
ENEMY_CANVAS_SIZE = {}
for _etype, _cfg in ENEMY_TYPES.items():
    _raw = {}
    for _name, _fname in ENEMY_ANIM_FILES.items():
        _path = f"{_cfg['folder']}/{_fname}"
        _raw[_name] = load_side_sheet_raw(_path)
    # Crop out the empty padding baked into each 128x128 cell, using the
    # union bbox across EVERY animation (idle/walk/attack/hurt/dead) so a
    # weapon swing never gets clipped. Scale by height only (not
    # width-constrained) so there's no letterboxing shrink either — a
    # wide attack swing just produces a wider frame, which is correct.
    _crop = union_bbox(_raw.values(), fallback_size=(128, 128))
    _target_h = _cfg["display"][1]
    _right = {
        _name: [crop_and_fit_height(f, _crop, _target_h) for f in _frames]
        for _name, _frames in _raw.items()
    }
    _left = {_name: flip_frames(_frames) for _name, _frames in _right.items()}
    ENEMY_ANIM_SETS[_etype] = {"right": _right, "left": _left}
    ENEMY_CANVAS_SIZE[_etype] = _right["idle"][0].get_size()

ARROW_IMG = load_img("assets/Skeleton_Archer/Arrow.png", (56, 20))

# ── Warrior sheets (256x256, 4 rows) ─────────────────────────────────────────
WARRIOR_SHEETS = {
    "idle":        ("assets/Swordsman/Swordsman_lvl3_Idle_with_shadow.png",         12, 4),
    "attack":      ("assets/Swordsman/Swordsman_lvl3_attack_with_shadow.png",        8, 4),
    "hurt":        ("assets/Swordsman/Swordsman_lvl3_Hurt_with_shadow.png",          5, 4),
    "death":       ("assets/Swordsman/Swordsman_lvl3_Death_with_shadow.png",         7, 4),
    "run":         ("assets/Swordsman/Swordsman_lvl3_Run_with_shadow.png",           8, 4),
    "run_attack":  ("assets/Swordsman/Swordsman_lvl3_Run_Attack_with_shadow.png",    8, 4),
    "walk":        ("assets/Swordsman/Swordsman_lvl3_Walk_with_shadow.png",          6, 4),
    "walk_attack": ("assets/Swordsman/Swordsman_lvl3_Walk_Attack_with_shadow.png",   6, 4),
}
warrior_anims = {}
for name, (path, cols, rows) in WARRIOR_SHEETS.items():
    warrior_anims[name] = load_sheet(path, cols, rows, DISPLAY_SIZE)

_w_idle_rows = load_sheet_all_rows(
    "assets/Swordsman/Swordsman_lvl3_Idle_with_shadow.png",         12, 4, DISPLAY_SIZE)
_w_walk_rows = load_sheet_all_rows(
    "assets/Swordsman/Swordsman_lvl3_Walk_with_shadow.png",          6, 4, DISPLAY_SIZE)
_w_run_rows = load_sheet_all_rows(
    "assets/Swordsman/Swordsman_lvl3_Run_with_shadow.png",           8, 4, DISPLAY_SIZE)
_w_atk_rows = load_sheet_all_rows(
    "assets/Swordsman/Swordsman_lvl3_attack_with_shadow.png",        8, 4, DISPLAY_SIZE)
_w_run_atk_rows = load_sheet_all_rows(
    "assets/Swordsman/Swordsman_lvl3_Run_Attack_with_shadow.png",    8, 4, DISPLAY_SIZE)
_w_walk_atk_rows = load_sheet_all_rows(
    "assets/Swordsman/Swordsman_lvl3_Walk_Attack_with_shadow.png",   6, 4, DISPLAY_SIZE)
_w_hurt_rows = load_sheet_all_rows(
    "assets/Swordsman/Swordsman_lvl3_Hurt_with_shadow.png",          5, 4, DISPLAY_SIZE)
_w_death_rows = load_sheet_all_rows(
    "assets/Swordsman/Swordsman_lvl3_Death_with_shadow.png",         7, 4, DISPLAY_SIZE)

# ── Vampire boss (4-directional sheets, same layout style as the Swordsman) ──
VAMPIRE_DISPLAY = (230, 230)
VAMPIRE_SHEETS = {
    "idle":   ("assets/vampire/Vampires2_Idle_with_shadow.png",   4,  4),
    "walk":   ("assets/vampire/Vampires2_Walk_with_shadow.png",   6,  4),
    "run":    ("assets/vampire/Vampires2_Run_with_shadow.png",    8,  4),
    "attack": ("assets/vampire/Vampires2_Attack_with_shadow.png", 12, 4),
    "hurt":   ("assets/vampire/Vampires2_Hurt_with_shadow.png",   4,  4),
    "dead":   ("assets/vampire/Vampires2_Death_with_shadow.png",  11, 4),
}
VAMPIRE_ANIMS = {
    name: load_sheet_all_rows(path, cols, rows, VAMPIRE_DISPLAY)
    for name, (path, cols, rows) in VAMPIRE_SHEETS.items()
}

# ── Portraits ─────────────────────────────────────────────────────────────────
portrait_imgs = {
    "Warrior": load_img("assets/Swordsman/swordsmanpic.png", (80, 80)),
}

# ── Game data ─────────────────────────────────────────────────────────────────
CLASS_STATS = {
    "Warrior": dict(health=120, stamina=260),
}
