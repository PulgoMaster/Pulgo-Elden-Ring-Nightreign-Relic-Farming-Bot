# Nightreign Consumable Damage Database
# Mined from AtkParam_Pc.csv + Bullet.csv + EquipParamGoods.csv (Smithbox exports)
# Data mining completed: 2026-03-25
#
# Nightreign adds a 3-level upgrade system to consumables (base = L1, L2, L3).
# L1 entries use IDs 10xxxxxx (inherited from base Elden Ring).
# L2/L3 entries use IDs 13xxxxxx (Nightreign-exclusive additions).
#
# ThrowParam.csv is irrelevant — grab animation data only, no damage values.
#
# NOTE: Damage values are from AtkParam_Pc (the actual resolved AoE/impact hit),
# NOT projectile travel damage. Most pots deal damage via their "(Blast)" sub-entry.
# Bullet.csv maps projectiles → AtkParam rows; hitRadius is the AoE of the blast.
#
# SCHOLAR NOTE: Scholar's Arc=50 scales consumables significantly more than other
# characters. Spark Aromatic (1060 fire at L3, 10 simultaneous hits) is the highest
# single-cast raw damage consumable in the game at max upgrade.


# =============================================================================
# POTS
# =============================================================================
# Format: {
#   "base_damage": int,   — primary blast damage value (highest damage type shown)
#   "damage_type": str,   — "fire", "lightning", "holy", "magic", "physical", "mixed"
#   "l2_damage": int,     — L2 upgrade blast damage
#   "l3_damage": int,     — L3 upgrade blast damage
#   "l3_bonus": str,      — description of L3 new mechanic (if any)
# }

POTS: dict[str, dict] = {
    "Fire Pot": {
        "damage_type": "fire",
        "base_damage": 230,    # AtkParam 10030001 (Blast)
        "l2_damage":   390,    # AtkParam 13030001
        "l3_damage":   390,    # AtkParam 13030011 (same blast; value in ground fire)
        "l3_bonus": "Persistent ground fire DoT: 25 fire/tick",
    },
    "Lightning Pot": {
        "damage_type": "lightning",
        "base_damage": 260,    # AtkParam 10032000 (Blast)
        "l2_damage":   402,    # AtkParam 13032001
        "l3_damage":   402,    # AtkParam 13032051
        "l3_bonus": "Bonus followup strike: 203 lightning",
    },
    "Holy Water Pot": {
        "damage_type": "holy",
        "base_damage": 167,    # AtkParam 10035001 (Blast)
        "l2_damage":   300,    # AtkParam 13035001
        "l3_damage":   300,    # AtkParam 13035011
        "l3_bonus": "Healing AoE pulse on impact (spEffect 708320)",
    },
    "Freezing Pot": {
        "damage_type": "physical",   # frostbite via spEffect; physical impact damage
        "base_damage": 119,    # AtkParam 10036001 (Blast)
        "l2_damage":   119,    # AtkParam 13036001 (same; L2 gains extra spEffect)
        "l3_damage":   119,    # AtkParam 13036011
        "l3_bonus": "Persistent ground ice chain ending in Ice Blast AoE",
    },
    "Magic Pot": {
        "damage_type": "magic",
        "base_damage": 322,    # AtkParam 10066001 (Blast, hitRadius=4)
        "l2_damage":   393,    # AtkParam 13066001
        "l3_damage":   393,    # AtkParam 13066011
        "l3_bonus": "Spawns bolt cloud: 8 × 20 magic bolts (up to +160 bonus)",
    },
    # Variants (base game only — Nightreign may not include all)
    "Redmane Fire Pot": {
        "damage_type": "fire",
        "base_damage": 326,    # AtkParam 10030101
        "l2_damage":   None,
        "l3_damage":   None,
    },
    "Giantsflame Fire Pot": {
        "damage_type": "fire",
        "base_damage": 344,    # AtkParam 10030201
        "l2_damage":   None,
        "l3_damage":   None,
    },
    "Academy Magic Pot": {
        "damage_type": "magic",
        "base_damage": 405,    # AtkParam 10066101 (hitRadius=2, more focused)
        "l2_damage":   None,
        "l3_damage":   None,
    },
    "Ancient Dragonbolt Pot": {
        "damage_type": "lightning",
        "base_damage": 340,    # AtkParam 10032100
        "l2_damage":   None,
        "l3_damage":   None,
    },
}


# =============================================================================
# KNIVES / DARTS
# =============================================================================
KNIVES: dict[str, dict] = {
    "Throwing Dagger": {
        "damage_type": "physical",
        "base_damage": 67,     # AtkParam 10170000
        "l2_damage":   134,    # AtkParam 13170000 (exactly 2x)
        "l3_damage":   134,    # AtkParam 13170010 (same; gains special Nightreign spEffect 799901)
        "l3_bonus": "Unknown Nightreign-specific spEffect 799901",
        "projectile_dist": 15,
    },
    "Bone Dart": {
        "damage_type": "physical",
        "base_damage": 57,
        "l2_damage":   None,
        "l3_damage":   None,
    },
    "Poisonbone Dart": {
        "damage_type": "physical",
        "base_damage": 50,
        "l2_damage":   None,
        "l3_damage":   None,
        "note": "Applies poison status",
    },
    "Kukri": {
        "damage_type": "physical",
        "base_damage": 87,
        "l2_damage":   None,
        "l3_damage":   None,
        "note": "Applies scarlet rot",
    },
    "Crystal Dart": {
        "damage_type": "mixed",
        "base_damage_phys": 66,
        "base_damage_mag":  44,
        "l2_damage":   None,
        "l3_damage":   None,
    },
    "Fan Daggers": {
        "damage_type": "physical",
        "base_damage": 37,     # Low per-hit; multiple daggers thrown
        "l2_damage":   None,
        "l3_damage":   None,
    },
}


# =============================================================================
# GLINTSTONE SCRAPS (Sorcery-type projectiles, subCategory1=121)
# =============================================================================
GLINTSTONE_SCRAPS: dict[str, dict] = {
    "Glintstone Scrap": {
        "damage_type": "magic",
        "base_damage": 82,     # AtkParam 10305000; fires 3-bolt burst
        "l2_damage":   117,    # AtkParam 13305000
        "l3_damage":   117,    # AtkParam 13305010 (fires 2-3 bolts vs 1-2)
        "l3_bonus": "Increased bolt count per cast",
    },
    "Large Glintstone Scrap": {
        "damage_type": "magic",
        "base_damage": 65,     # AtkParam 10305100; 5-bolt fan spread
        "l2_damage":   78,     # AtkParam 13305100
        "l3_damage":   70,     # AtkParam 13305110 (anomaly: slightly lower than L2)
        "note": "L3 damage anomaly — possibly intentional, offset by additional bolts",
    },
}


# =============================================================================
# GRAVITY STONES (Gravity-type projectiles, subCategory1=121)
# =============================================================================
GRAVITY_STONES: dict[str, dict] = {
    "Gravity Stone Fan": {
        "damage_type": "mixed",
        "base_damage_phys": 178,
        "base_damage_mag":   60,
        "l2_damage_phys":   236,
        "l2_damage_mag":    146,
        "l3_damage_phys":   176,   # anomaly: lower than L2
        "l3_damage_mag":     66,
        "l3_bonus": "Pull-in gravity mechanic added at L3 (offsets the lower direct damage)",
        "note": "5-rock scatter (22-entry Bullet chain)",
    },
    "Gravity Stone Chunk": {
        "damage_type": "mixed",
        "base_damage_phys": 261,
        "base_damage_mag":   70,
        "l2_damage_phys":   310,
        "l2_damage_mag":    155,
        "l3_damage_phys":   310,
        "l3_damage_mag":    155,
        "l3_bonus": "Gravity Near hit: 180 magic pull-in strike (bonus)",
        "note": "Single large blast; hitRadius=4. L3 total: 310+155+180=645 mixed",
    },
}


# =============================================================================
# AROMATICS (Perfumes, subCategory1=109)
# =============================================================================
AROMATICS: dict[str, dict] = {
    "Spark Aromatic": {
        "damage_type": "fire",
        "base_damage": 740,    # AtkParam 10351000; 10 simultaneous Bullet instances
        "l2_damage":   880,    # AtkParam 13351000
        "l3_damage":  1060,    # AtkParam 13351010
        "l3_bonus": "Wider edge hitRadius (2.5 vs 1.4) — larger effective AoE",
        "note": "Fires as 10 simultaneous projectiles. Against large targets all 10 can connect: effective max = 10×damage",
    },
    "Uplifting Aromatic": {
        "damage_type": None,   # Buff only
        "base_damage":    0,
        "l2_damage":      0,
        "l3_damage":      0,
        "l3_bonus": "Explosion bonus: 490 fire (AtkParam 13350050, new Nightreign mechanic)",
        "note": "Pure buff at L1/L2; L3 adds a separate 490 fire detonation",
    },
}


# =============================================================================
# SPRAYMISTS (Status-focused, subCategory1=109)
# =============================================================================
SPRAYMISTS: dict[str, dict] = {
    "Poison Spraymist": {
        "damage_type": "status",
        "base_damage": 0,
        "l2_damage":   0,
        "l3_damage":   600,    # AtkParam 13358015 (Explosion; fire type)
        "l3_bonus": "L3: Full explosion chain ending in 600 fire detonation after status linger",
        "note": "L1/L2: status application only. L3: converts to damage item.",
    },
    "Acid Spraymist": {
        "damage_type": "status",
        "base_damage": 0,
        "l2_damage":   0,
        "l3_damage":   600,    # AtkParam 13361012 (Explosion; fire type)
        "l3_bonus": "L3: Same explosion chain as Poison Spraymist (600 fire)",
        "note": "Armor-break via spEffect. L3 adds damage payoff.",
    },
}


# =============================================================================
# SCHOLAR DAMAGE RANKINGS (L3 max, single cast)
# =============================================================================
SCHOLAR_TOP_DAMAGE_L3: list[tuple[str, int, str]] = [
    # (item_name, max_single_cast_damage, damage_type)
    ("Spark Aromatic ×10 hits",        10600, "fire"),      # 1060 × 10 max
    ("Gravity Stone Chunk (all hits)",   645, "mixed"),      # 310+155+180
    ("L3 Poison Spraymist Explosion",    600, "fire"),
    ("L3 Acid Spraymist Explosion",      600, "fire"),
    ("Uplifting Aromatic (explosion)",   490, "fire"),
    ("Lightning Pot (w/ followup)",      605, "lightning"),  # 402+203
    ("Magic Pot (w/ all bolts)",         553, "magic"),      # 393+8×20
    ("Magic Pot (blast only)",           393, "magic"),
    ("Fire Pot",                         390, "fire"),
    ("Holy Water Pot",                   300, "holy"),
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_consumable(name: str, level: int = 1) -> dict | None:
    """
    Return damage info for a consumable at a given level (1, 2, or 3).
    Searches all categories. Returns None if not found.
    """
    all_items = {**POTS, **KNIVES, **GLINTSTONE_SCRAPS, **GRAVITY_STONES, **AROMATICS, **SPRAYMISTS}
    item = all_items.get(name)
    if item is None:
        return None
    key = {1: "base_damage", 2: "l2_damage", 3: "l3_damage"}.get(level, "base_damage")
    damage = item.get(key)
    return {"name": name, "level": level, "damage": damage, "damage_type": item.get("damage_type"),
            "l3_bonus": item.get("l3_bonus") if level == 3 else None}


def best_consumables_by_type(damage_type: str, level: int = 3) -> list[tuple[str, int]]:
    """
    Return list of (name, damage) sorted by damage for a given type and level.
    damage_type: 'fire', 'lightning', 'holy', 'magic', 'physical', 'mixed', 'status'
    """
    all_items = {**POTS, **KNIVES, **GLINTSTONE_SCRAPS, **GRAVITY_STONES, **AROMATICS, **SPRAYMISTS}
    key = {1: "base_damage", 2: "l2_damage", 3: "l3_damage"}.get(level, "base_damage")
    results = []
    for name, item in all_items.items():
        if item.get("damage_type") == damage_type:
            dmg = item.get(key)
            if dmg is not None:
                results.append((name, dmg))
    return sorted(results, key=lambda x: -x[1])
