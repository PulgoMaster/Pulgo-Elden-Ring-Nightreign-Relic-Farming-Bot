# Nightreign Weapon Database
# Built from EquipParamWeapon.csv and EquipParamCustomWeapon.csv (Smithbox exports)
# Data mining completed: 2026-03-25
#
# Scaling values (corrStr, corrAgi, etc.) are raw param percentages.
# Approximate letter grades: S=175+, A=140+, B=100+, C=73+, D=50+, E=20+
# These are internal scaling percentages, not the final AR bonus.

# =============================================================================
# HERO IDs
# =============================================================================

HERO_IDS = {
    1: "Wylder",
    2: "Guardian",
    3: "Ironeye",
    4: "Duchess",
    5: "Raider",
    6: "Revenant",
    7: "Recluse",
    8: "Executor",
    9: "Scholar",
    10: "Undertaker",
}

# Reverse mapping: hero name → hero ID
HERO_NAME_TO_ID = {v: k for k, v in HERO_IDS.items()}

# =============================================================================
# WEAPON CATEGORIES
# =============================================================================
# Categories from EquipParamWeapon.weaponCategory
# Note: In Nightreign each category is primarily associated with certain heroes.
# Relic passives like "Sword Attack Power Up" apply to the full category (cat=1).

WEAPON_CATEGORY_IDS = {
    "Dagger": 0,
    "Sword": 1,          # Straight swords, greatswords, twinblades
    "Thrusting Sword": 2,
    "Curved Sword": 3,   # Curved swords, katanas, curved greatswords
    "Axe": 4,
    "Hammer": 5,         # Hammers, clubs, colossal weapons
    "Spear": 6,
    "Halberd": 7,        # Halberds, reapers
    "Staff": 8,          # Glintstone staves and sacred seals
    "Fist": 9,           # Fists and claws
    "Bow": 10,
    "Crossbow": 11,
    "Offhand": 12,       # Torches and shields
}

WEAPON_CATEGORY_NAMES = {v: k for k, v in WEAPON_CATEGORY_IDS.items()}

# Primary hero associations per category (which hero primarily uses this weapon type)
# 0 = any hero can find/use this category
CATEGORY_PRIMARY_HERO = {
    0: "Duchess",
    1: None,      # Shared: generic pool + Wylder (Bastard Sword tier)
    2: None,      # Shared: generic (Great Épée) + Scholar (Rapier)
    3: None,      # Shared: generic (Falchion/Dismounter) + Executor (Uchigatana)
    4: None,      # Shared: generic (Battle Axe) + Raider (Greataxe)
    5: None,      # Shared: generic (Flail) + Undertaker (Mace) + Raider (Colossal)
    6: None,      # Any hero
    7: None,      # Shared: generic (Scythe) + Guardian (Halberd)
    8: "Recluse",
    9: None,      # Shared: generic (Caestus/Hookclaws) + Revenant (Cursed Claws)
    10: None,     # Shared: generic (Greatbow) + Ironeye (standard bows)
    11: None,     # Any hero
    12: None,     # Any hero (torches + shields)
}

# =============================================================================
# WEAPON DATA
# =============================================================================
# Format: weapon_name -> {
#   "category": str,      # Category name (matches WEAPON_CATEGORY_IDS keys)
#   "cat_id": int,        # Numeric category ID
#   "hero": str | None,   # Restricting hero, or None for unrestricted
#   "element": str,       # Primary element ("Physical", "Fire", "Lightning", "Holy", "Magic", "Sleep")
#   "base_phys": int,     # Base physical attack at base level
#   "base_mag": int,      # Base magic attack
#   "base_fire": int,     # Base fire attack
#   "base_thun": int,     # Base lightning attack
#   "corr_str": int,      # Strength scaling % (param value, not letter grade)
#   "corr_agi": int,      # Dexterity (Agility) scaling %
#   "corr_mag": int,      # Intelligence (Magic) scaling %
#   "corr_fai": int,      # Faith scaling %
#   "is_hero_weapon": bool  # True = this is the hero's signature weapon
#   "innate_status": str | None  # Permanent status buildup regardless of infusion
#                                # ("Rot", "Bleed", "Frost", etc.) — None if none
#                                # Note: Cold/Poison/Blood INFUSIONS also add status,
#                                # but those are infusion-dependent, not innate.
# }
#
# NOTE on Rot: Rot is NOT an infusion type. It appears as an innate spEffectBehaviorId
# on specific weapons (e.g. Scorpion's Stinger = spEff 107010). The Antspur Rapier has
# rot in the param data but is disabled and NOT in the Nightreign active loot pool.

WEAPONS: dict[str, dict] = {

    # =========================================================================
    # DAGGERS (Cat 0) — Duchess
    # =========================================================================
    "Dagger": {
        "category": "Dagger", "cat_id": 0, "hero": "Duchess", "element": "Physical",
        "base_phys": 58, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 13, "corr_agi": 73, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Parrying Dagger": {
        "category": "Dagger", "cat_id": 0, "hero": "Duchess", "element": "Physical",
        "base_phys": 60, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 13, "corr_agi": 73, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Misericorde": {
        "category": "Dagger", "cat_id": 0, "hero": "Duchess", "element": "Physical",
        "base_phys": 72, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 13, "corr_agi": 73, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Black Knife": {
        "category": "Dagger", "cat_id": 0, "hero": "Duchess", "element": "Physical",
        "base_phys": 46, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 12, "corr_agi": 63, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Scorpion's Stinger": {
        "category": "Dagger", "cat_id": 0, "hero": "Duchess", "element": "Physical",
        "base_phys": 71, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 13, "corr_agi": 73, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
        "innate_status": "Rot",  # spEffectBehaviorId=107010 on ALL variants
    },
    "Duchess' Dagger": {
        "category": "Dagger", "cat_id": 0, "hero": "Duchess", "element": "Physical",
        "base_phys": 55, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 13, "corr_agi": 73, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": True,
    },

    # =========================================================================
    # SWORDS (Cat 1) — Generic + Wylder
    # Includes: straight swords, greatswords, twinblades, whips
    # =========================================================================
    "Longsword": {
        "category": "Sword", "cat_id": 1, "hero": None, "element": "Physical",
        "base_phys": 70, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 50, "corr_agi": 50, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Carian Knight's Sword": {
        "category": "Sword", "cat_id": 1, "hero": None, "element": "Magic",
        "base_phys": 60, "base_mag": 30, "base_fire": 0, "base_thun": 0,
        "corr_str": 43, "corr_agi": 43, "corr_mag": 30, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Greatsword": {
        "category": "Sword", "cat_id": 1, "hero": None, "element": "Physical",
        "base_phys": 109, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 61, "corr_agi": 33, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Twinblade": {
        "category": "Sword", "cat_id": 1, "hero": None, "element": "Physical",
        "base_phys": 72, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 44, "corr_agi": 54, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Whip": {
        "category": "Sword", "cat_id": 1, "hero": None, "element": "Physical",
        # Note: base Whip only appears in infused variants; lightning variant is the base for Nightreign
        "base_phys": 36, "base_mag": 0, "base_fire": 0, "base_thun": 36,
        "corr_str": 18, "corr_agi": 70, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Bastard Sword": {
        "category": "Sword", "cat_id": 1, "hero": "Wylder", "element": "Physical",
        "base_phys": 85, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 54, "corr_agi": 44, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Wylder's Greatsword": {
        "category": "Sword", "cat_id": 1, "hero": "Wylder", "element": "Physical",
        "base_phys": 80, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 54, "corr_agi": 44, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": True,
    },

    # =========================================================================
    # THRUSTING SWORDS (Cat 2) — Scholar + Generic
    # =========================================================================
    "Rapier": {
        "category": "Thrusting Sword", "cat_id": 2, "hero": "Scholar", "element": "Physical",
        "base_phys": 73, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 8, "corr_agi": 76, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Scholar's Thrusting Sword": {
        "category": "Thrusting Sword", "cat_id": 2, "hero": "Scholar", "element": "Physical",
        "base_phys": 66, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 8, "corr_agi": 76, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": True,
    },
    "Great Epee": {
        "category": "Thrusting Sword", "cat_id": 2, "hero": None, "element": "Physical",
        # Base Épée only in infused variants; lightning is smallest base
        "base_phys": 41, "base_mag": 0, "base_fire": 0, "base_thun": 41,
        "corr_str": 38, "corr_agi": 58, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },

    # =========================================================================
    # CURVED SWORDS / KATANAS (Cat 3) — Executor + Generic
    # =========================================================================
    "Falchion": {
        "category": "Curved Sword", "cat_id": 3, "hero": None, "element": "Physical",
        "base_phys": 70, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 28, "corr_agi": 64, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Dismounter": {
        "category": "Curved Sword", "cat_id": 3, "hero": None, "element": "Physical",
        # Base Dismounter only in infused variants
        "base_phys": 43, "base_mag": 0, "base_fire": 0, "base_thun": 43,
        "corr_str": 50, "corr_agi": 50, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Uchigatana": {
        "category": "Curved Sword", "cat_id": 3, "hero": "Executor", "element": "Physical",
        "base_phys": 66, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 13, "corr_agi": 73, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Executor's Blade": {
        "category": "Curved Sword", "cat_id": 3, "hero": "Executor", "element": "Physical",
        "base_phys": 62, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 13, "corr_agi": 73, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": True,
    },

    # =========================================================================
    # AXES (Cat 4) — Raider + Generic
    # =========================================================================
    "Battle Axe": {
        "category": "Axe", "cat_id": 4, "hero": None, "element": "Physical",
        "base_phys": 77, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 54, "corr_agi": 44, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Greataxe": {
        "category": "Axe", "cat_id": 4, "hero": "Raider", "element": "Physical",
        "base_phys": 91, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 73, "corr_agi": 13, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },

    # =========================================================================
    # HAMMERS / COLOSSAL (Cat 5) — Undertaker (Mace), Raider (Heavy), Generic
    # =========================================================================
    "Mace": {
        "category": "Hammer", "cat_id": 5, "hero": "Undertaker", "element": "Physical",
        "base_phys": 74, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 64, "corr_agi": 28, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Undertaker's Hammer": {
        "category": "Hammer", "cat_id": 5, "hero": "Undertaker", "element": "Physical",
        "base_phys": 68, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 64, "corr_agi": 28, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": True,
    },
    "Flail": {
        "category": "Hammer", "cat_id": 5, "hero": None, "element": "Physical",
        "base_phys": 67, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 38, "corr_agi": 58, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Nightrider Flail": {
        "category": "Hammer", "cat_id": 5, "hero": None, "element": "Physical",
        # Base only in infused variants
        "base_phys": 41, "base_mag": 0, "base_fire": 0, "base_thun": 41,
        "corr_str": 38, "corr_agi": 58, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Large Club": {
        "category": "Hammer", "cat_id": 5, "hero": "Raider", "element": "Physical",
        # Base only in infused variants
        "base_phys": 44, "base_mag": 0, "base_fire": 44, "base_thun": 0,
        "corr_str": 80, "corr_agi": 0, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Great Mace": {
        "category": "Hammer", "cat_id": 5, "hero": "Raider", "element": "Physical",
        "base_phys": 88, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 76, "corr_agi": 8, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Great Club": {
        "category": "Hammer", "cat_id": 5, "hero": "Raider", "element": "Holy",
        "base_phys": 101, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 68, "corr_agi": 0, "corr_mag": 0, "corr_fai": 24,
        "is_hero_weapon": False,
    },
    "Duelist Greataxe": {
        "category": "Hammer", "cat_id": 5, "hero": "Raider", "element": "Physical",
        "base_phys": 106, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 80, "corr_agi": 0, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Golem's Halberd": {
        "category": "Hammer", "cat_id": 5, "hero": "Raider", "element": "Physical",
        "base_phys": 133, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 80, "corr_agi": 0, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Prelate's Inferno Crozier": {
        "category": "Hammer", "cat_id": 5, "hero": "Raider", "element": "Physical",
        "base_phys": 163, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 80, "corr_agi": 0, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Watchdog's Staff": {
        "category": "Hammer", "cat_id": 5, "hero": "Raider", "element": "Physical",
        "base_phys": 159, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 80, "corr_agi": 0, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Raider's Greataxe": {
        "category": "Hammer", "cat_id": 5, "hero": "Raider", "element": "Physical",
        "base_phys": 100, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 80, "corr_agi": 0, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": True,
    },

    # =========================================================================
    # SPEARS (Cat 6) — Generic (any hero)
    # =========================================================================
    "Short Spear": {
        "category": "Spear", "cat_id": 6, "hero": None, "element": "Physical",
        "base_phys": 72, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 44, "corr_agi": 54, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Lance": {
        "category": "Spear", "cat_id": 6, "hero": None, "element": "Physical",
        "base_phys": 95, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 58, "corr_agi": 38, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Mohgwyn's Sacred Spear": {
        "category": "Spear", "cat_id": 6, "hero": None, "element": "Fire",
        "base_phys": 79, "base_mag": 0, "base_fire": 51, "base_thun": 0,
        "corr_str": 50, "corr_agi": 33, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
        "innate_status": "Bleed",  # spEffectBehaviorId=105110
    },

    # =========================================================================
    # HALBERDS / REAPERS (Cat 7) — Guardian + Generic
    # =========================================================================
    "Halberd": {
        "category": "Halberd", "cat_id": 7, "hero": "Guardian", "element": "Physical",
        "base_phys": 82, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 54, "corr_agi": 44, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Lucerne": {
        "category": "Halberd", "cat_id": 7, "hero": "Guardian", "element": "Physical",
        "base_phys": 82, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 54, "corr_agi": 44, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Banished Knight's Halberd": {
        "category": "Halberd", "cat_id": 7, "hero": "Guardian", "element": "Physical",
        "base_phys": 86, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 54, "corr_agi": 44, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Nightrider Glaive": {
        "category": "Halberd", "cat_id": 7, "hero": "Guardian", "element": "Physical",
        "base_phys": 103, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 54, "corr_agi": 44, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Guardian's Halberd": {
        "category": "Halberd", "cat_id": 7, "hero": "Guardian", "element": "Physical",
        "base_phys": 78, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 54, "corr_agi": 44, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": True,
    },
    "Scythe": {
        "category": "Halberd", "cat_id": 7, "hero": None, "element": "Physical",
        "base_phys": 70, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 22, "corr_agi": 68, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },

    # =========================================================================
    # STAVES / SEALS (Cat 8) — Recluse
    # =========================================================================
    "Azur's Glintstone Staff": {
        "category": "Staff", "cat_id": 8, "hero": "Recluse", "element": "Physical",
        "base_phys": 24, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 0, "corr_agi": 0, "corr_mag": 100, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Recluse's Staff": {
        "category": "Staff", "cat_id": 8, "hero": "Recluse", "element": "Physical",
        "base_phys": 25, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 0, "corr_agi": 0, "corr_mag": 100, "corr_fai": 0,
        "is_hero_weapon": True,
    },
    "Golden Order Seal": {
        "category": "Staff", "cat_id": 8, "hero": "Recluse", "element": "Physical",
        "base_phys": 24, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 0, "corr_agi": 0, "corr_mag": 0, "corr_fai": 100,
        "is_hero_weapon": False,
    },

    # =========================================================================
    # FISTS / CLAWS (Cat 9) — Revenant + Generic
    # =========================================================================
    "Caestus": {
        "category": "Fist", "cat_id": 9, "hero": None, "element": "Physical",
        "base_phys": 61, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 54, "corr_agi": 44, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Hookclaws": {
        "category": "Fist", "cat_id": 9, "hero": None, "element": "Physical",
        "base_phys": 56, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 28, "corr_agi": 64, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Revenant's Cursed Claws": {
        "category": "Fist", "cat_id": 9, "hero": "Revenant", "element": "Magic",
        "base_phys": 12, "base_mag": 54, "base_fire": 0, "base_thun": 0,
        "corr_str": 13, "corr_agi": 0, "corr_mag": 0, "corr_fai": 73,
        "is_hero_weapon": True,
    },

    # =========================================================================
    # BOWS (Cat 10) — Ironeye + Generic (Greatbow)
    # =========================================================================
    "Longbow": {
        "category": "Bow", "cat_id": 10, "hero": "Ironeye", "element": "Physical",
        "base_phys": 48, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 8, "corr_agi": 76, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Composite Bow": {
        "category": "Bow", "cat_id": 10, "hero": "Ironeye", "element": "Physical",
        "base_phys": 59, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 8, "corr_agi": 76, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Horn Bow": {
        "category": "Bow", "cat_id": 10, "hero": "Ironeye", "element": "Magic",
        "base_phys": 41, "base_mag": 22, "base_fire": 0, "base_thun": 0,
        "corr_str": 7, "corr_agi": 65, "corr_mag": 26, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Erdtree Bow": {
        "category": "Bow", "cat_id": 10, "hero": "Ironeye", "element": "Holy",
        "base_phys": 46, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 7, "corr_agi": 65, "corr_mag": 0, "corr_fai": 26,
        "is_hero_weapon": False,
    },
    "Ironeye's Bow": {
        "category": "Bow", "cat_id": 10, "hero": "Ironeye", "element": "Physical",
        "base_phys": 45, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 8, "corr_agi": 76, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": True,
    },
    "Greatbow": {
        "category": "Bow", "cat_id": 10, "hero": None, "element": "Physical",
        "base_phys": 116, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 58, "corr_agi": 38, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Lion Greatbow": {
        "category": "Bow", "cat_id": 10, "hero": None, "element": "Physical",
        "base_phys": 182, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 58, "corr_agi": 38, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },

    # =========================================================================
    # CROSSBOWS (Cat 11) — Any hero
    # Note: Crossbows have 0 scaling (stat-independent)
    # =========================================================================
    "Pulley Crossbow": {
        "category": "Crossbow", "cat_id": 11, "hero": None, "element": "Physical",
        "base_phys": 106, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 0, "corr_agi": 0, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Full Moon Crossbow": {
        "category": "Crossbow", "cat_id": 11, "hero": None, "element": "Magic",
        "base_phys": 93, "base_mag": 93, "base_fire": 0, "base_thun": 0,
        "corr_str": 0, "corr_agi": 0, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Jar Cannon": {
        "category": "Crossbow", "cat_id": 11, "hero": None, "element": "Physical",
        "base_phys": 584, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 0, "corr_agi": 0, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },

    # =========================================================================
    # OFFHAND (Cat 12) — Torches and Shields
    # =========================================================================
    "Torch": {
        "category": "Offhand", "cat_id": 12, "hero": None, "element": "Fire",
        "base_phys": 19, "base_mag": 0, "base_fire": 36, "base_thun": 0,
        "corr_str": 50, "corr_agi": 50, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Steel-Wire Torch": {
        "category": "Offhand", "cat_id": 12, "hero": None, "element": "Fire",
        "base_phys": 24, "base_mag": 0, "base_fire": 44, "base_thun": 0,
        "corr_str": 50, "corr_agi": 50, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "St. Trina's Torch": {
        "category": "Offhand", "cat_id": 12, "hero": None, "element": "Sleep",
        "base_phys": 24, "base_mag": 0, "base_fire": 44, "base_thun": 0,
        "corr_str": 43, "corr_agi": 43, "corr_mag": 0, "corr_fai": 20,
        "is_hero_weapon": False,
    },
    "Ghostflame Torch": {
        "category": "Offhand", "cat_id": 12, "hero": None, "element": "Magic",
        "base_phys": 26, "base_mag": 48, "base_fire": 0, "base_thun": 0,
        "corr_str": 43, "corr_agi": 43, "corr_mag": 20, "corr_fai": 0,
        "is_hero_weapon": False,
        "innate_status": "Frost",  # spEffectBehaviorId=107510
    },
    "Beast-Repellent Torch": {
        "category": "Offhand", "cat_id": 12, "hero": None, "element": "Fire",
        "base_phys": 20, "base_mag": 0, "base_fire": 37, "base_thun": 0,
        "corr_str": 50, "corr_agi": 50, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Sentry's Torch": {
        "category": "Offhand", "cat_id": 12, "hero": None, "element": "Holy",
        "base_phys": 11, "base_mag": 0, "base_fire": 18, "base_thun": 0,
        "corr_str": 43, "corr_agi": 43, "corr_mag": 0, "corr_fai": 20,
        "is_hero_weapon": False,
    },
    "Buckler": {
        "category": "Offhand", "cat_id": 12, "hero": None, "element": "Physical",
        "base_phys": 49, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 58, "corr_agi": 38, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Perfumer's Shield": {
        "category": "Offhand", "cat_id": 12, "hero": None, "element": "Physical",
        "base_phys": 71, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 58, "corr_agi": 38, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Red Thorn Roundshield": {
        "category": "Offhand", "cat_id": 12, "hero": None, "element": "Physical",
        "base_phys": 48, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 58, "corr_agi": 38, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Kite Shield": {
        "category": "Offhand", "cat_id": 12, "hero": None, "element": "Physical",
        "base_phys": 71, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 64, "corr_agi": 28, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
    "Dragon Towershield": {
        "category": "Offhand", "cat_id": 12, "hero": None, "element": "Physical",
        "base_phys": 80, "base_mag": 0, "base_fire": 0, "base_thun": 0,
        "corr_str": 70, "corr_agi": 18, "corr_mag": 0, "corr_fai": 0,
        "is_hero_weapon": False,
    },
}

# =============================================================================
# HERO SIGNATURE WEAPONS
# Each hero's starting/unique weapon
# =============================================================================
HERO_SIGNATURE_WEAPONS = {
    "Wylder": "Wylder's Greatsword",
    "Guardian": "Guardian's Halberd",
    "Ironeye": "Ironeye's Bow",
    "Duchess": "Duchess' Dagger",
    "Raider": "Raider's Greataxe",
    "Revenant": "Revenant's Cursed Claws",
    "Recluse": "Recluse's Staff",
    "Executor": "Executor's Blade",
    "Scholar": "Scholar's Thrusting Sword",
    "Undertaker": "Undertaker's Hammer",
}

# =============================================================================
# WEAPON INFUSION TYPES
# Standard infusion variants available for most base weapons.
# Offsets match the ID suffix pattern in EquipParamWeapon (e.g. base=1000000, fire=1000500).
# NOTE: Rot/Scarlet Rot is NOT a live infusion — all rot-named weapon entries in the
# param are disabled and absent from EquipParamCustomWeapon. No +1200 offset exists.
# =============================================================================
INFUSION_TYPES = {
    "Physical": 0,     # Base/no infusion
    "Fire": 500,       # split phys/fire damage, fire scaling
    "Lightning": 600,  # split phys/lightning, lightning scaling
    "Holy": 700,       # split phys/holy, faith scaling
    "Magic": 800,      # split phys/magic, intelligence scaling
    "Cold": 900,       # split phys/magic, intelligence scaling + inherent frostbite buildup
    "Poison": 1000,    # reduced phys, inherent poison buildup
    "Blood": 1100,     # reduced phys, inherent bleed buildup
    # "Rot": —        # NOT in Nightreign; disabled ER leftover entries only
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_weapon_category(weapon_name: str) -> str | None:
    """Return the category name for a weapon, or None if not found."""
    weapon = WEAPONS.get(weapon_name)
    if weapon:
        return weapon["category"]
    # Try case-insensitive match
    lower = weapon_name.lower()
    for name, data in WEAPONS.items():
        if name.lower() == lower:
            return data["category"]
    return None


def get_weapon_category_id(weapon_name: str) -> int | None:
    """Return the numeric category ID for a weapon."""
    weapon = WEAPONS.get(weapon_name)
    if weapon:
        return weapon["cat_id"]
    lower = weapon_name.lower()
    for name, data in WEAPONS.items():
        if name.lower() == lower:
            return data["cat_id"]
    return None


def get_weapons_by_category(category: str) -> list[str]:
    """Return all weapon names in the given category."""
    return [name for name, data in WEAPONS.items() if data["category"] == category]


def get_weapons_by_hero(hero_name: str) -> list[str]:
    """Return all weapon names restricted to the given hero."""
    return [name for name, data in WEAPONS.items() if data["hero"] == hero_name]


def get_hero_weapon_category(hero_name: str) -> str | None:
    """Return the weapon category name for a hero's signature weapon."""
    sig = HERO_SIGNATURE_WEAPONS.get(hero_name)
    if sig:
        return get_weapon_category(sig)
    return None


def is_weapon_for_hero(weapon_name: str, hero_name: str) -> bool:
    """
    Return True if the weapon is usable by the given hero.
    Weapons with hero=None are usable by any hero.
    """
    weapon = WEAPONS.get(weapon_name)
    if not weapon:
        return False
    return weapon["hero"] is None or weapon["hero"] == hero_name
