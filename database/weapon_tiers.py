# Nightreign Weapon Tier (Reinforcement) Database
# Mined from ReinforceParamWeapon.csv (Smithbox export)
# Data mining completed: 2026-03-25
#
# Nightreign uses a 4-rarity tier system for weapons, NOT the base ER +0/+25 structure.
# Weapon tiers: White (+0) → Blue (+1) → Purple (+2) → Orange (+3)
#
# "Red" (uncommon Deep of Night) tier is NOT in this param — it uses a different
# mechanism and is not a distinct reinforcement entry. Likely uses Uncommon track visually.
#
# Key facts:
# - All stat scaling corrections (Str/Dex/Int/Fai/Arc) are 1.0 universally —
#   reinforcement never changes scaling letter grades, only raw damage.
# - physicsAtkRate and baseAtkRate split at +3 (Orange): 1.70 vs 1.80.
#   baseAtkRate grows faster at max tier.
# - All elemental damage rates (magic/fire/lightning/holy) move identically
#   to physicsAtkRate — no split by element.
# - Staves and Seals: physicsAtkRate stays 1.0 at all tiers; only
#   correctSpellScalingRate increases. Spell damage only, no physical AR.


# =============================================================================
# COMMON WEAPONS (IDs 0–3)
# White (+0) → Blue (+1) → Purple (+2) → Orange (+3)
# Standard loot drop weapons.
# =============================================================================
COMMON_TIERS: list[dict] = [
    {"level": 0, "color": "White",  "physics_rate": 1.000, "base_rate": 1.000},
    {"level": 1, "color": "Blue",   "physics_rate": 1.230, "base_rate": 1.230},
    {"level": 2, "color": "Purple", "physics_rate": 1.500, "base_rate": 1.500},
    {"level": 3, "color": "Orange", "physics_rate": 1.700, "base_rate": 1.800},
]

# CHARACTER WEAPONS (IDs 100–103)
# Starting/NPC weapons — slightly stronger damage curve.
CHARACTER_TIERS: list[dict] = [
    {"level": 0, "color": "White",  "physics_rate": 1.000, "base_rate": 1.000},
    {"level": 1, "color": "Blue",   "physics_rate": 1.290, "base_rate": 1.230},
    {"level": 2, "color": "Purple", "physics_rate": 1.580, "base_rate": 1.500},
    {"level": 3, "color": "Orange", "physics_rate": 1.790, "base_rate": 1.800},
]

# UNCOMMON WEAPONS (IDs 200–202) — Deep of Night loot, 3 upgrade tiers
# Born at Blue power: baseAtkRate starts at 1.23.
UNCOMMON_TIERS: list[dict] = [
    {"level": 0, "color": "Blue-class",   "physics_rate": 1.000, "base_rate": 1.230},
    {"level": 1, "color": "Purple-class", "physics_rate": 1.210, "base_rate": 1.500},
    {"level": 2, "color": "Orange-class", "physics_rate": 1.370, "base_rate": 1.800},
]

# RARE WEAPONS (IDs 300–301) — Deep of Night loot, 2 upgrade tiers
# Born at Purple power: baseAtkRate starts at 1.50.
RARE_TIERS: list[dict] = [
    {"level": 0, "color": "Purple-class", "physics_rate": 1.000, "base_rate": 1.500},
    {"level": 1, "color": "Orange-class", "physics_rate": 1.140, "base_rate": 1.800},
]

# LEGENDARY WEAPONS (ID 400) — Orange only, no upgrades possible.
LEGENDARY_TIERS: list[dict] = [
    {"level": 0, "color": "Orange", "physics_rate": 1.000, "base_rate": 1.800},
]


# =============================================================================
# RARITY SUMMARY TABLE
# =============================================================================
RARITY: dict[str, dict] = {
    "Common":     {"max_upgrades": 3, "tiers": COMMON_TIERS,     "born_at": "White"},
    "Character":  {"max_upgrades": 3, "tiers": CHARACTER_TIERS,  "born_at": "White"},
    "Uncommon":   {"max_upgrades": 2, "tiers": UNCOMMON_TIERS,   "born_at": "Blue"},
    "Rare":       {"max_upgrades": 1, "tiers": RARE_TIERS,        "born_at": "Purple"},
    "Legendary":  {"max_upgrades": 0, "tiers": LEGENDARY_TIERS,  "born_at": "Orange"},
}

# All rarities reach the same maximum base_rate of 1.800 when fully upgraded.
# A Common weapon fully upgraded (Orange) and a Legendary weapon are equal in base_rate.
# physicsAtkRate differs slightly between rarities at max — Legendary starts at 1.0
# (no physics scaling increase), while Common reaches 1.70.


# =============================================================================
# SHIELD TIERS
# =============================================================================
# Same 4-tier structure as weapons but with staminaGuardDefRate instead of physicsAtkRate.
# Extracted entries: Small Shield (1000–1203), Medium Shield (1300–1501),
#                    Greatshield (1600–1801).
# The physicsAtkRate and baseAtkRate are irrelevant for shields — guard stability
# (staminaGuardDefRate) is the key multiplier. All staminaGuardDefRate values = 1.0
# in the extracted rows (likely handled elsewhere for shields).

SHIELD_TIERS: dict[str, dict] = {
    "Small Shield":  {"max_upgrades": 2, "common_max": 3},
    "Medium Shield": {"max_upgrades": 2, "common_max": 3},
    "Greatshield":   {"max_upgrades": 2, "common_max": 3},
}


# =============================================================================
# SKILL / ULTIMATE UPGRADE TRACKS
# =============================================================================
# Skills and Ultimates have separate reinforcement tracks (IDs 8000–9914).
# These have 15 upgrade levels (+0 to +14), completely separate from weapon tiers.
# Upgrade curve: approximately +7% per level for most skills.

SKILL_TRACKS: dict[str, int] = {
    "Generic (all classes)":          8000,
    "Ironeye - Marking":              8200,
    "Raider - Retaliate":             8500,
    "Recluse - Magic Cocktail":       8700,
    "Executor - Cursed Sword":        8800,
    "Guardian - Wings of Salvation":  9100,
    "Ironeye - Single Shot":          9200,
}


# =============================================================================
# HELPER
# =============================================================================

def physics_rate(rarity: str, level: int) -> float:
    """Return the physicsAtkRate multiplier for a given rarity and upgrade level."""
    tiers = RARITY.get(rarity, {}).get("tiers", [])
    for t in tiers:
        if t["level"] == level:
            return t["physics_rate"]
    return 1.0


def base_rate(rarity: str, level: int) -> float:
    """Return the baseAtkRate multiplier for a given rarity and upgrade level."""
    tiers = RARITY.get(rarity, {}).get("tiers", [])
    for t in tiers:
        if t["level"] == level:
            return t["base_rate"]
    return 1.0
