"""
All game configuration and asset loading: stage backgrounds, enemy
sprite packs, player sheets, boss effects, and class stats. This
module has side effects at import time (it loads every image) —
import it once, early.
"""
from settings import *
from igris_data import load_igris_frames, IGRIS_SCALE, IGRIS_BANK
from sprite_loaders import (
    load_img, load_sheet_all_rows,
    load_sheet, load_side_sheet_raw,
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
    {"name": "Dead Forest", "subtitle": "Where the buried refuse to sleep",
     "bg": "dead_forest", "accent": (126, 164, 108), "floor_top": 500,
     "enemies": ["graveborn_brute", "shadow_wolf", "graveborn_butcher"], "wave_mult": 1.0},
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
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    "knight2":           dict(folder="assets/Knight_2", name="Castle Sentinel", role="guard",
                              hp=76, dmg=(11, 18), speed=1.65, display=(195, 195),
                              atk_range=128, windup=500, recovery=500, poise=58,
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    "knight3":           dict(folder="assets/Knight_3", name="Castle Reaver", role="aggressor",
                              hp=66, dmg=(12, 20), speed=2.05, display=(195, 195),
                              atk_range=124, windup=340, recovery=390, poise=42,
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    "skeleton_spearman": dict(folder="assets/Skeleton_Spearman", hp=50, dmg=(8, 14),  speed=1.6, display=(195, 195),
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    "skeleton_warrior":  dict(folder="assets/Skeleton_Warrior",  hp=55, dmg=(9, 16),  speed=1.7, display=(195, 195),
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    # Slow, durable front-line enemy. Its heavy health/damage profile gives the
    # Dead Forest a tank role without requiring special AI behavior yet.
    "graveborn_brute":   dict(folder="assets/Graveborn_Brute", name="Graveborn Brute", role="tank",
                              hp=105, dmg=(15, 23), speed=1.15,
                              display=(185, 175), atk_range=145, windup=720, recovery=720,
                              attack_cooldown=1250, poise=92, source_facing="left",
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    # Mid-speed pressure bruiser: less durable than the Brute, but faster and
    # able to threaten the hero from farther away with its broad cleaver sweep.
    "graveborn_butcher": dict(folder="assets/Graveborn_Butcher", name="Graveborn Butcher", role="bruiser",
                              hp=82, dmg=(13, 21), speed=1.55,
                              display=(200, 175), atk_range=160, attack_cooldown=1150,
                              windup=560, recovery=620, poise=68,
                              source_facing="left", frame_width=160,
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    # Fast, fragile melee hunter introduced in the Dead Forest.  Its generated
    # source art faces left, so source_facing prevents the generic side-sheet
    # loader from reversing its movement direction in game.
    "shadow_wolf":       dict(folder="assets/Shadow_Wolf", name="Shadow Wolf", role="hunter",
                              hp=42, dmg=(8, 15), speed=2.65,
                              display=(150, 112), atk_range=130, windup=300, recovery=410,
                              attack_cooldown=900, poise=32, lunge_speed=5.4,
                              source_facing="left",
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    # Ranged castle support. The broader 160px source cells preserve the
    # magician's low collapse pose while the loader still scales by idle height.
    "dungeon_magician":  dict(folder="assets/Dungeon_Magician", name="Dungeon Magician", role="caster",
                              hp=50, dmg=(8, 15), speed=1.25,
                              display=(180, 185), ranged=True, atk_range=520, preferred_range=390,
                              min_range=245, windup=760, recovery=580, attack_cooldown=1450,
                              poise=35, projectile_lead=9,
                              projectile="magic_orb", source_facing="left", frame_width=160,
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png"),
    # Armored ranged support for the Castle. Wider source cells preserve the
    # full bow draw and the low corpse pose without clipping.
    "castle_archer":     dict(folder="assets/Castle_Archer", name="Castle Archer", role="marksman",
                              hp=48, dmg=(8, 14), speed=1.45,
                              display=(180, 185), ranged=True, atk_range=600, preferred_range=455,
                              min_range=275, windup=620, recovery=520, attack_cooldown=1300,
                              poise=30, projectile_lead=12,
                              source_facing="left", frame_width=160,
                              anchor_height=185,
                              walk_up="Walk_Up.png", walk_down="Walk_Down.png",
                              attack_up="Attack_Up.png", attack_down="Attack_Down.png"),
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
ENEMY_CROP_REGIONS = {}
ENEMY_SCALE_FACTORS = {}
for _etype, _cfg in ENEMY_TYPES.items():
    if _cfg.get("role") == "commander":
        ENEMY_ANIM_SETS[_etype] = load_igris_frames()
        # Logical body geometry remains independent of the 384px render cell.
        ENEMY_CANVAS_SIZE[_etype] = _cfg["display"]
        ENEMY_CROP_REGIONS[_etype] = pygame.Rect(0, 0, *IGRIS_BANK.cell_size)
        ENEMY_SCALE_FACTORS[_etype] = IGRIS_SCALE
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
    ENEMY_CROP_REGIONS[_etype] = _crop
    ENEMY_SCALE_FACTORS[_etype] = _scale
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

ARROW_IMG = load_img("assets/Castle_Archer/Arrow.png", (56, 20))
_IGRIS_CRESCENT_ROWS = load_sheet_all_rows(
    "assets/Blood_Red_Commander/Igris_Crescent_Anim.png", 4, 1,
    (208, 116))
IGRIS_CRESCENT_FRAMES = _IGRIS_CRESCENT_ROWS[0]
_IGRIS_SHOCKWAVE_ROWS = load_sheet_all_rows(
    "assets/Blood_Red_Commander/Igris_Shockwave_Anim.png", 4, 1,
    (196, 86))
IGRIS_SHOCKWAVE_FRAMES = _IGRIS_SHOCKWAVE_ROWS[0]

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

# ── Assassin sheets (4 directions: down, left, right, up) ────────────────────
# The Igris-style remake uses fixed 120px cells at exact 2x pixel scale.
# Extra transparent padding keeps long dagger thrusts inside the canvas; the
# draw offset preserves the original world center and feet at (110, 164).
ASSASSIN_DISPLAY_SIZE = (240, 240)
ASSASSIN_DRAW_OFFSET = (-10, -12)
ASSASSIN_SHEETS = {
    "idle":        ("assets/Assassin/PixelRemake/sheets/idle.png",         6, 4),
    # v10 uses a six-phase planted walk.  Both this sheet and idle are packed
    # to the same feet baseline, matching the root discipline of the Warrior
    # walk instead of letting generated frame placement move the whole body.
    "walk":        ("assets/Assassin/PixelRemake/sheets/walk.png",         6, 4),
    "run":         ("assets/Assassin/PixelRemake/sheets/run.png",          8, 4),
    # Three genuinely different light attacks.  gameplay.py advances through
    # these on consecutive LMB presses instead of replaying one sheet three
    # times with different damage values.
    "attack_1":    ("assets/Assassin/PixelRemake/sheets/attack_1.png",     6, 4),
    "attack_2":    ("assets/Assassin/PixelRemake/sheets/attack_2.png",     6, 4),
    "attack_3":    ("assets/Assassin/PixelRemake/sheets/attack_3.png",     6, 4),
    # Moving versions of the same 3-hit light combo.  Keeping them separate
    # prevents the standing attack art from visually sliding over the ground
    # while the player's world position continues to move.
    "walk_attack_1": ("assets/Assassin/PixelRemake/sheets/walk_attack_1.png", 6, 4),
    "walk_attack_2": ("assets/Assassin/PixelRemake/sheets/walk_attack_2.png", 6, 4),
    "walk_attack_3": ("assets/Assassin/PixelRemake/sheets/walk_attack_3.png", 6, 4),
    # Kept for backwards compatibility with any menu/preview code that still
    # asks for the legacy single walk-attack sheet.
    "walk_attack": ("assets/Assassin/PixelRemake/sheets/walk_attack.png",  6, 4),
    "run_attack":  ("assets/Assassin/PixelRemake/sheets/run_attack.png",   8, 4),
    "dash":        ("assets/Assassin/PixelRemake/sheets/dash.png",         7, 4),
    "dash_attack": ("assets/Assassin/PixelRemake/sheets/dash_attack.png",  6, 4),
    # Death's Dance is a completely separate ten-phase action: ignition,
    # accelerating dash, full-body rotation, braking skid, and recovery. The source is
    # packed into the same transparent 120px cells, so it uses the same stable
    # four-direction loader as Jinwoo's other production-ready sheets.
    "deaths_dance": ("assets/Assassin/PixelRemake/sheets/deaths_dance_spin.png", 10, 4),
    # Sonic Stream is the E-key target-entry barrage: launch, chained crossing
    # cuts, overhead finisher, landing skid, and recovery.  Its eleven poses
    # are original body animation, normalized to Q's action scale, Jinwoo's
    # normal head/torso proportions, and the regular planted root. gameplay.py
    # renders its trails separately so the character sheet stays reusable.
    "sonic_stream": ("assets/Assassin/PixelRemake/sheets/sonic_stream.png", 11, 4),
    "hurt":        ("assets/Assassin/PixelRemake/sheets/hurt.png",         5, 4),
    "death":       ("assets/Assassin/PixelRemake/sheets/death.png",        7, 4),
}

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
# Six transparent, game-sized frames for the restored red ground finisher.
# They are intentionally separate from the character sheet so the approved
# ten-frame dash/spin body animation remains untouched.
_a_deaths_dance_fx = load_sheet_all_rows(
    "assets/Assassin/VFX/deaths_dance_eruption_red.png", 6, 1, (260, 260)
)[0]
_a_walk_atk_rows = (
    ASSASSIN_ANIM_ROWS["walk_attack_1"],
    ASSASSIN_ANIM_ROWS["walk_attack_2"],
    ASSASSIN_ANIM_ROWS["walk_attack_3"],
)
_a_run_atk_rows = ASSASSIN_ANIM_ROWS["run_attack"]
_a_dash_rows = ASSASSIN_ANIM_ROWS["dash"]
_a_dash_atk_rows = ASSASSIN_ANIM_ROWS["dash_attack"]
_a_hurt_rows = ASSASSIN_ANIM_ROWS["hurt"]
_a_death_rows = ASSASSIN_ANIM_ROWS["death"]

assassin_anims = {name: rows[0] for name, rows in ASSASSIN_ANIM_ROWS.items()}
assassin_anims["idle"] = _a_idle_rows[0]

# ── Portraits ─────────────────────────────────────────────────────────────────
portrait_imgs = {
    "Warrior": load_img("assets/Swordsman/swordsmanpic.png", (80, 80)),
    "Assassin": load_img("assets/Assassin/PixelRemake/sungjinwoo.png", (80, 80)),
}

# ── Game data ─────────────────────────────────────────────────────────────────
CLASS_STATS = {
    "Warrior": dict(
        health=130, stamina=260,
        title="IRON VANGUARD", special="Earthsplitter",
        special_desc="A crushing frontal shockwave",
    ),
    "Assassin": dict(
        health=105, stamina=320,
        title="SHADOW HUNTER", special="Death's Dance",
        special_desc="Three crimson dagger cuts ending in ground eruptions",
    ),
}
