"""Small run-progression layer used between stages.

Upgrades are deliberately data-driven so combat code only reads the resulting
modifiers.  Nothing is written to disk; starting a new class starts a fresh run.
"""

BOONS = {
    "edge": {
        "name": "Sharpened Edge",
        "tag": "OFFENSE",
        "description": "+12% all damage",
    },
    "heart": {
        "name": "Iron Heart",
        "tag": "SURVIVAL",
        "description": "+20 maximum health",
    },
    "breath": {
        "name": "Deep Breath",
        "tag": "MOBILITY",
        "description": "+45 maximum stamina",
    },
    "predator": {
        "name": "Predator's Eye",
        "tag": "OFFENSE",
        "description": "+6% critical chance",
    },
    "fleet": {
        "name": "Fleetfoot",
        "tag": "MOBILITY",
        "description": "Dash cooldown reduced by 12%",
    },
    "siphon": {
        "name": "Grim Siphon",
        "tag": "SURVIVAL",
        "description": "Recover 12 health on each kill",
    },
    "mastery": {
        "name": "Combat Mastery",
        "tag": "ABILITY",
        "description": "Special cooldown reduced by 15%",
    },
}


def new_run_state():
    return {
        "damage_mult": 1.0,
        "bonus_health": 0,
        "bonus_stamina": 0,
        "crit_bonus": 0.0,
        "dash_cooldown_mult": 1.0,
        "special_cooldown_mult": 1.0,
        "heal_on_kill": 0,
        "boons": [],
        "last_summary": {},
    }


def boon_choices(stage_idx, hero_class):
    """Return three stable but varied choices for this transition."""
    orders = {
        "Warrior": ("heart", "edge", "breath", "siphon", "mastery", "predator", "fleet"),
        "Assassin": ("edge", "fleet", "predator", "breath", "siphon", "mastery", "heart"),
    }
    order = orders.get(hero_class, tuple(BOONS))
    start = (stage_idx * 2) % len(order)
    return [order[(start + offset) % len(order)] for offset in (0, 1, 3)]


def apply_boon(run_state, boon_id):
    if boon_id == "edge":
        run_state["damage_mult"] *= 1.12
    elif boon_id == "heart":
        run_state["bonus_health"] += 20
    elif boon_id == "breath":
        run_state["bonus_stamina"] += 45
    elif boon_id == "predator":
        run_state["crit_bonus"] += 0.06
    elif boon_id == "fleet":
        run_state["dash_cooldown_mult"] *= 0.88
    elif boon_id == "siphon":
        run_state["heal_on_kill"] += 12
    elif boon_id == "mastery":
        run_state["special_cooldown_mult"] *= 0.85
    else:
        raise ValueError(f"Unknown boon: {boon_id}")
    run_state["boons"].append(boon_id)

