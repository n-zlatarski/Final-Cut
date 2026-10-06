"""Define stages and characters, then load their sprites, portraits and backgrounds."""
from display_fonts_and_colors import *
from igris_sprites_and_timing import load_igris_frames
from jinwoo_sprites_and_timing import animation_overrides
import castle_archer_sprite_settings as archer_data
from wolf_and_archer_sprites import load_directional_enemy_frames, CELL_SIZE as DEFAULT_ENEMY_CELL_SIZE, SCALE as DEFAULT_ENEMY_SCALE
from sprite_loading import (
    load_img, load_sheet_all_rows,
    load_side_sheet_raw,
    union_bbox, scale_crop, flip_frames,
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
    {"name": "Dead Forest", "subtitle": "The armored pack is hunting",
     "bg": "dead_forest", "accent": (126, 164, 108), "floor_top": 500,
     "enemies": ["shadow_wolf", "azure_wolf", "ember_wolf"], "wave_mult": 1.0},
    {"name": "Castle", "subtitle": "Break the outer guard",
     "bg": "castle", "accent": (190, 151, 92), "floor_top": 450,
     "enemies": ["knight1", "knight2", "dungeon_magician", "castle_archer"], "wave_mult": 1.4},
    {"name": "Terrace", "subtitle": "No cover. No retreat.",
     "bg": "terrace", "accent": (160, 174, 198), "floor_top": 480,
     "enemies": ["knight1", "knight2", "knight3"], "wave_mult": 1.0},
    {"name": "Throne Room", "subtitle": "The commander awaits",
     "bg": "throne_room", "accent": (176, 54, 74), "floor_top": 560,
     "enemies": ["knight1", "knight2", "knight3"], "wave_mult": 1.4,
     "boss": "blood_red_commander"},
]

# ── Enemy types ───────────────────────────────────────────────────────────────
ENEMY_TYPES = {
    "knight1":           dict(folder="assets/Knight_1", name="Castle Vanguard", role="duelist",
                              hp=70, dmg=(10, 18), speed=1.8, display=(195, 195),
                              atk_range=122, windup=420, recovery=430, poise=48,
                              attack_hit_frame=4, mobile_recovery=True,
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    "knight2":           dict(folder="assets/Knight_2", name="Castle Sentinel", role="guard",
                              hp=76, dmg=(11, 18), speed=1.65, display=(195, 195),
                              atk_range=128, windup=500, recovery=500, poise=58,
                              attack_hit_frame=4, mobile_recovery=True,
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    "knight3":           dict(folder="assets/Knight_3", name="Castle Reaver", role="aggressor",
                              hp=66, dmg=(12, 20), speed=2.05, display=(195, 195),
                              atk_range=124, windup=340, recovery=390, poise=42,
                              attack_hit_frame=4, mobile_recovery=True,
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    # Heavy plated wolf: slower pursuit, a longer windup and a forceful bite.
    "azure_wolf":        dict(folder="assets/Azure_Wolf", name="Azure Wolf", role="hunter",
                              hp=78, dmg=(12, 18), speed=2.15,
                              display=(165, 125), atk_range=140, windup=280, recovery=240,
                              attack_cooldown=1100, poise=70, lunge_speed=4.6,
                              directional_pack=True, attack_hit_frame=4, attack_active_ms=70,
                              frame_counts=dict(idle=4, walk=8, attack=8, hurt=4, dead=8),
                              attack_recovery_frames=(5, 6, 7), idle_fps=4, walk_fps=8,
                              hurt_fps=12.5, death_fps=10, body_height=168),
    # Lighter armored wolf: a quicker trot and an airborne forward snap.
    "ember_wolf":        dict(folder="assets/Ember_Wolf", name="Ember Wolf", role="hunter",
                              hp=58, dmg=(10, 16), speed=2.85,
                              display=(155, 112), atk_range=130, windup=210, recovery=240,
                              attack_cooldown=900, poise=38, lunge_speed=6.3,
                              directional_pack=True, attack_hit_frame=3, attack_active_ms=65,
                              frame_counts=dict(idle=4, walk=8, attack=8, hurt=4, dead=8),
                              attack_recovery_frames=(4, 5, 6, 7), idle_fps=4, walk_fps=10,
                              hurt_fps=12.5, death_fps=10, body_height=156),
    # Four-direction wolf: planted paws, a diagonal trot and a committed bite.
    "shadow_wolf":       dict(folder="assets/Shadow_Wolf", name="Shadow Wolf", role="hunter",
                              hp=42, dmg=(8, 15), speed=2.65,
                              display=(150, 112), atk_range=130, windup=210, recovery=260,
                              attack_cooldown=900, poise=32, lunge_speed=5.4,
                              directional_pack=True, attack_hit_frame=3, attack_active_ms=65,
                              frame_counts=dict(idle=4, walk=8, attack=8, hurt=4, dead=8),
                              attack_recovery_frames=(4, 5, 6, 7), idle_fps=4, walk_fps=10,
                              hurt_fps=12.5, death_fps=10, body_height=150),
    # Ranged castle support. The broader 160px source cells preserve the
    # magician's low collapse pose while the loader still scales by idle height.
    "dungeon_magician":  dict(folder="assets/Dungeon_Magician", name="Dungeon Magician", role="caster",
                              hp=50, dmg=(8, 15), speed=1.25,
                              display=(180, 185), ranged=True, atk_range=520, preferred_range=390,
                              min_range=245, windup=760, recovery=580, attack_cooldown=1450,
                              poise=35, projectile_lead=9,
                              projectile="magic_orb", source_facing="left", frame_width=160,
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    # Four authored directions, registered to one ground pivot. The shot uses
    # the same clock as the draw/release/recovery poses.
    "castle_archer":     dict(folder="assets/Castle_Archer", name="Castle Archer", role="marksman",
                              hp=48, dmg=(8, 14), speed=1.45,
                              display=(180, 185), ranged=True, atk_range=600, preferred_range=455,
                              min_range=275, windup=620, recovery=520, attack_cooldown=1300,
                              poise=30, projectile_lead=12,
                              anchor_height=185,
                              directional_pack=True, frame_counts=archer_data.FRAME_COUNTS,
                              sprite_cell=archer_data.CELL_SIZE, sprite_scale=archer_data.SCALE,
                              sprite_shadow_scale=2.7,
                              sprite_pivot=archer_data.PIVOT, body_height=185,
                              attack_hit_frame=archer_data.RELEASE_FRAME, attack_active_ms=90,
                              attack_recovery_frames=(5, 0), idle_fps=4, walk_fps=7.5,
                              hurt_fps=12.5, death_fps=8),
    "blood_red_commander": dict(
        folder="assets/Blood_Red_Commander",
        name="Blood-Red Commander Igris", role="commander",
        hp=360, dmg=(16, 25), speed=1.95,
        display=(205, 205), anchor_height=205,
        # Start committed attacks at sword range.  The previous 560px trigger
        # made every grounded combo get replaced by another gap-closing dash.
        atk_range=198, engage_range=225, windup=390, recovery=360,
        attack_cooldown=820, poise=145,
        detection_range=720, forget_range=900, floor_top=560,
        dash_speed=15.2,
    ),
}

ENEMY_ANIM_FILES = {
    "idle": "Idle.png", "walk": "Walk.png", "attack": "Attack_1.png",
    "hurt": "Hurt.png", "dead": "Dead.png",
}
# Each entry: {"right": {anim_name: [frames]}, "left": {anim_name: [frames]}}
ENEMY_ANIM_SETS = {}
ENEMY_CANVAS_SIZE = {}
for _etype, _cfg in ENEMY_TYPES.items():
    if _cfg.get("directional_pack"):
        ENEMY_ANIM_SETS[_etype] = load_directional_enemy_frames(
            _cfg["folder"], _cfg.get("frame_counts"),
            cell_size=_cfg.get("sprite_cell", DEFAULT_ENEMY_CELL_SIZE),
            scale=_cfg.get("sprite_scale", DEFAULT_ENEMY_SCALE))
        ENEMY_CANVAS_SIZE[_etype] = _cfg["display"]
        continue
    if _cfg.get("role") == "commander":
        ENEMY_ANIM_SETS[_etype] = load_igris_frames()
        # Logical body geometry remains independent of the 384px render cell.
        ENEMY_CANVAS_SIZE[_etype] = _cfg["display"]
        continue
    _frame_width = _cfg.get("frame_width", 128)
    _raw = {}
    for _name, _fname in ENEMY_ANIM_FILES.items():
        _path = f"{_cfg['folder']}/{_fname}"
        _raw[_name] = load_side_sheet_raw(_path, frame_size=_frame_width)
    _special_raw = {
        _state: load_side_sheet_raw(
            f"{_cfg['folder']}/{_filename}", frame_size=_frame_width)
        for _state, _filename in _cfg.get("special_anims", {}).items()
    }
    _vertical_raw = {}
    for _direction in ("up", "down"):
        _direction_anims = {}
        for _state in ("walk", "attack", *_special_raw.keys()):
            _key = f"{_state}_{_direction}"
            if _cfg.get(_key):
                _direction_anims[_state] = load_side_sheet_raw(
                    f"{_cfg['folder']}/{_cfg[_key]}", frame_size=_frame_width)
        if _direction_anims:
            _vertical_raw[_direction] = _direction_anims
    # Crop region: union bbox across EVERY animation (idle/walk/attack/
    # hurt/dead) so a weapon swing never gets clipped.
    _crop = union_bbox(
        [
            *_raw.values(),
            *_special_raw.values(),
            *(
                _frames
                for _direction_anims in _vertical_raw.values()
                for _frames in _direction_anims.values()
            ),
        ],
        fallback_size=(_frame_width, 128),
    )
    # Scale factor: based on the IDLE pose's own height only. Using the
    # full crop's height here would make characters whose attack/idle
    # poses reach further (a spear held overhead, a drawn bow) end up
    # with a smaller-looking standing body than a compact character
    # like the knight, even at the same canvas size. Idle is the same
    # "neutral standing" reference for every character, so scaling off
    # it keeps everyone's actual height on screen consistent. Attack
    # frames may still extend beyond the target height/width during a
    # swing — that's correct, not a bug.
    _idle_bbox = union_bbox([_raw["idle"]], fallback_size=(_frame_width, 128))
    _target_h = _cfg["display"][1]
    _scale = _target_h / max(1, _idle_bbox.height)
    _all_side_raw = {**_raw, **_special_raw}
    _source_frames = {
        _name: [scale_crop(f, _crop, _scale) for f in _frames]
        for _name, _frames in _all_side_raw.items()
    }
    _flipped_frames = {
        _name: flip_frames(_frames)
        for _name, _frames in _source_frames.items()
    }
    if _cfg.get("source_facing", "right") == "left":
        _left, _right = _source_frames, _flipped_frames
    else:
        _right, _left = _source_frames, _flipped_frames
    ENEMY_ANIM_SETS[_etype] = {"right": _right, "left": _left}
    for _direction, _direction_anims in _vertical_raw.items():
        ENEMY_ANIM_SETS[_etype][_direction] = {
            _state: [scale_crop(f, _crop, _scale) for f in _frames]
            for _state, _frames in _direction_anims.items()
        }
    ENEMY_CANVAS_SIZE[_etype] = _right["idle"][0].get_size()

ARROW_IMG = load_img("assets/Castle_Archer/Arrow.png", (80, 20))
_IGRIS_CRESCENT_ROWS = load_sheet_all_rows(
    "assets/Blood_Red_Commander/vfx/blood_wave.png", 6, 1,
    (256, 256))
IGRIS_CRESCENT_FRAMES = _IGRIS_CRESCENT_ROWS[0]
_IGRIS_SHOCKWAVE_ROWS = load_sheet_all_rows(
    "assets/Blood_Red_Commander/vfx/ground_wave.png", 6, 1,
    (256, 256))
IGRIS_SHOCKWAVE_FRAMES = _IGRIS_SHOCKWAVE_ROWS[0]

# ── Assassin sheets (4 directions: down, left, right, up) ────────────────────
# The Igris-style remake uses fixed 120px cells at exact 2x pixel scale.
# Extra transparent padding keeps long dagger thrusts inside the canvas; the
# draw offset preserves the original world center and feet at (110, 164).
ASSASSIN_DISPLAY_SIZE = (240, 240)
ASSASSIN_DRAW_OFFSET = (-10, -12)
ASSASSIN_SHEETS = {
    "idle": ("assets/Assassin/sheets/idle.png", 6, 4),
    "walk": ("assets/Assassin/sheets/walk.png", 6, 4),
    "run": ("assets/Assassin/sheets/run.png", 8, 4),
    "dash": ("assets/Assassin/sheets/dash.png", 7, 4),
    "hurt": ("assets/Assassin/sheets/hurt.png", 5, 4),
    "death": ("assets/Assassin/sheets/death.png", 7, 4),
}

# The attack bank replaces only LMB (stationary/moving/dash), Q and E.
# All animations use the same canonical asset folder and fixed ground alignment.
ASSASSIN_SHEETS.update(animation_overrides())
ASSASSIN_ANIM_ROWS = {
    name: load_sheet_all_rows(
        path, cols, rows, ASSASSIN_DISPLAY_SIZE, remove_flat_background=True)
    for name, (path, cols, rows) in ASSASSIN_SHEETS.items()
}

# The six generated idle poses form only half of a natural breathing cycle.
# Ping-pong them instead of jumping directly from pose 6 back to pose 1.  This
# produces a 12-step / 1.5-second idle at the existing 8 FPS, matching the
# Swordsman's overall idle-loop duration without inventing interpolated art.
_a_idle_rows = [row + list(reversed(row)) for row in ASSASSIN_ANIM_ROWS["idle"]]
_a_walk_rows = ASSASSIN_ANIM_ROWS["walk"]
_a_run_rows = ASSASSIN_ANIM_ROWS["run"]
_a_atk1_rows = ASSASSIN_ANIM_ROWS["attack_1"]
_a_atk2_rows = ASSASSIN_ANIM_ROWS["attack_2"]
_a_atk3_rows = ASSASSIN_ANIM_ROWS["attack_3"]
_a_deaths_dance_rows = ASSASSIN_ANIM_ROWS["deaths_dance"]
_a_sonic_stream_rows = ASSASSIN_ANIM_ROWS["sonic_stream"]
_a_walk_atk_rows = (
    ASSASSIN_ANIM_ROWS["walk_attack_1"],
    ASSASSIN_ANIM_ROWS["walk_attack_2"],
    ASSASSIN_ANIM_ROWS["walk_attack_3"],
)
_a_dash_rows = ASSASSIN_ANIM_ROWS["dash"]
_a_dash_atk_rows = ASSASSIN_ANIM_ROWS["dash_attack"]
_a_hurt_rows = ASSASSIN_ANIM_ROWS["hurt"]
_a_death_rows = ASSASSIN_ANIM_ROWS["death"]

assassin_anims = {name: rows[0] for name, rows in ASSASSIN_ANIM_ROWS.items()}
assassin_anims["idle"] = _a_idle_rows[0]

# ── Portraits ─────────────────────────────────────────────────────────────────
portrait_imgs = {
    "Assassin": load_img("assets/Assassin/portrait.png", (80, 80)),
}

# ── Game data ─────────────────────────────────────────────────────────────────
CLASS_STATS = {
    "Assassin": dict(
        health=105, stamina=320,
        title="SHADOW HUNTER", special="Death's Dance",
    ),
}
