"""
Nightreign game knowledge database.
Used by the Smart Analyze / Smart Recommendations feature to detect passive synergies.

Passive names are sourced verbatim from bot/passives.py.
Weapon data is sourced from in-game knowledge and the Nightreign Weapons sheet.
Wiki fields that could not be verified are marked with # TODO: verify.

Damage system rules (from user spec):
  - Physical damage: buffed by "Physical Attack Up" only (no affinity passives)
  - Affinity damage (Magic/Fire/Lightning/Holy): buffed by "Improved Affinity Attack Power"
      AND the element-specific passive (e.g. "Lightning Attack Power Up")
  - Incantations: buffed by "Improved Incantations" regardless of damage type.
      School-specific buffs STACK on top (e.g. Improved Dragon Cult Incantations).
  - Dragon Cult incantations get 3 stacking buffs:
      Improved Incantations + Lightning Attack Power Up + Improved Dragon Cult Incantations
  - Sorceries: buffed by "Improved Sorceries" + type-specific (e.g. Improved Glintblade Sorcery)
  - No two direct damage modifier passives can coexist on the same relic (exclusive group),
      except affinity + school-specific CAN coexist.
"""

# ── Damage types ───────────────────────────────────────────────────────────────

# Physical subtypes — buffed only by "Physical Attack Up"
PHYSICAL_DAMAGE_TYPES = [
    "Standard",
    "Strike",
    "Slash",
    "Pierce",
]

# Elemental/affinity types — buffed by "Improved Affinity Attack Power"
# AND the element-specific passive (Magic/Fire/Lightning/Holy Attack Power Up)
AFFINITY_DAMAGE_TYPES = [
    "Magic",
    "Fire",
    "Lightning",
    "Holy",
]

# All damage types combined (for generic lookups)
ALL_DAMAGE_TYPES = PHYSICAL_DAMAGE_TYPES + AFFINITY_DAMAGE_TYPES


# ── Status effects ─────────────────────────────────────────────────────────────

STATUS_EFFECTS = [
    "Hemorrhage",      # Blood Loss
    "Frostbite",
    "Poison",
    "Scarlet Rot",
    "Sleep",
    "Madness",
    "Death Blight",    # Death
    # TODO: verify — check wiki for any Nightreign-specific additional status effects
]

# Aliases used in passive names (maps display name → canonical name above)
STATUS_EFFECT_ALIASES = {
    "Blood Loss": "Hemorrhage",
    "Rot":        "Scarlet Rot",
    "Death":      "Death Blight",
}


# ── Incantation schools ────────────────────────────────────────────────────────
# Maps school name → affinity damage types it deals (for passive synergy stacking).
# A None affinity entry means the school deals Physical (e.g. Bestial).
# Source: passives.py "Sorceries & Incantations" category + game knowledge.
#
# Synergy rule: school-specific buff STACKS with "Improved Incantations" (delivery)
# AND with the affinity buff if the school deals elemental damage.

INCANTATION_SCHOOLS = {
    # School                         Affinity types dealt
    "Dragon Cult":          ["Lightning"],   # 3 stacking buffs: Incantations + Lightning + Dragon Cult
    "Dragon Communion":     ["Fire"],        # Fire breath / dragonfire affinities
    "Bestial":              [],              # Physical — no affinity buff applies
    "Golden Order":         ["Holy"],        # Fundamentalist sub-school
    "Fundamentalist":       ["Holy"],        # alias / overlapping school
    "Fire":                 ["Fire"],        # Giants' Flame and standard fire incantations
    "Giants' Flame":        ["Fire"],        # sub-school of Fire incantations
    "Frenzied Flame":       ["Fire"],        # Frenzied Flame deals Fire (+ Madness buildup)
    "Godslayer":            ["Fire", "Holy"],# Godslayer incants deal Fire and Holy  # TODO: verify split
    # TODO: verify — add any additional Nightreign-specific incantation schools
}

# Passive name → incantation school mapping (reverse lookup)
INCANTATION_SCHOOL_PASSIVE = {
    "Improved Dragon Cult Incantations":       "Dragon Cult",
    "Improved Giants' Flame Incantations":     "Giants' Flame",
    "Improved Godslayer Incantations":         "Godslayer",
    "Improved Bestial Incantations":           "Bestial",
    "Improved Frenzied Flame Incantations":    "Frenzied Flame",
    "Improved Dragon Communion Incantations":  "Dragon Communion",
    "Improved Fundamentalist Incantations":    "Fundamentalist",
}


# ── Sorcery schools ────────────────────────────────────────────────────────────
# Maps school name → affinity damage types it deals.
# All sorcery schools deal Magic affinity unless noted.

SORCERY_SCHOOLS = {
    # School                         Affinity types dealt
    "Glintblade":   ["Magic"],   # Glintblade Phalanx, Magic Glintblade, etc.
    "Stonedigger":  ["Magic"],   # Stonedigger Troll-type sorceries
    "Carian":       ["Magic"],   # Carian Sword Sorcery, Carian Greatsword, etc.
    "Invisibility": ["Magic"],   # Unseen Form and invisibility sorceries
    "Crystalian":   ["Magic"],   # Crystal Torrent, Shattering Crystal, etc.
    "Gravity":      ["Magic"],   # Gravitational sorceries (Rock Sling, Collapsing Stars)
    "Thorn":        ["Magic"],   # Briars of Punishment, Thorn Sorceries
    "Night":        ["Magic"],   # Night Shard, Night Maiden's Mist — mostly Magic  # TODO: verify
    # TODO: verify — confirm any Nightreign-exclusive sorcery schools
}

# Passive name → sorcery school mapping (reverse lookup)
SORCERY_SCHOOL_PASSIVE = {
    "Improved Glintblade Sorcery":    "Glintblade",
    "Improved Stonedigger Sorcery":   "Stonedigger",
    "Improved Carian Sword Sorcery":  "Carian",
    "Improved Invisibility Sorcery":  "Invisibility",
    "Improved Crystalian Sorcery":    "Crystalian",
    "Improved Gravity Sorcery":       "Gravity",
    "Improved Thorn Sorcery":         "Thorn",
}


# ── Weapon classes ─────────────────────────────────────────────────────────────
# All weapon classes as derived from passives.py weapon categories.

WEAPON_CLASSES = [
    "Dagger",
    "Thrusting Sword",
    "Heavy Thrusting Sword",
    "Straight Sword",
    "Greatsword",
    "Colossal Sword",
    "Curved Sword",
    "Curved Greatsword",
    "Katana",
    "Twinblade",
    "Axe",
    "Greataxe",
    "Hammer",
    "Flail",
    "Great Hammer",
    "Colossal Weapon",
    "Spear",
    "Great Spear",
    "Halberd",
    "Reaper",
    "Whip",
    "Fist",
    "Claw",
    "Bow",
    "Greatbow",
    "Crossbow",
    "Ballista",
    "Glintstone Staff",
    "Sacred Seal",
    "Small Shield",
    "Medium Shield",
    "Greatshield",
]


# ── Weapon class → Dormant Power passive mapping ───────────────────────────────
# Maps weapon class → the "Dormant Power Helps Discover <class>" passive name.

WEAPON_CLASS_TO_DORMANT_POWER = {
    "Dagger":               "Dormant Power Helps Discover Daggers",
    "Thrusting Sword":      "Dormant Power Helps Discover Thrusting Swords",
    "Heavy Thrusting Sword":"Dormant Power Helps Discover Heavy Thrusting Swords",
    "Straight Sword":       "Dormant Power Helps Discover Straight Swords",
    "Greatsword":           "Dormant Power Helps Discover Greatswords",
    "Colossal Sword":       "Dormant Power Helps Discover Colossal Swords",
    "Curved Sword":         "Dormant Power Helps Discover Curved Swords",
    "Curved Greatsword":    "Dormant Power Helps Discover Curved Greatswords",
    "Katana":               "Dormant Power Helps Discover Katana",
    "Twinblade":            "Dormant Power Helps Discover Twinblades",
    "Axe":                  "Dormant Power Helps Discover Axes",
    "Greataxe":             "Dormant Power Helps Discover Greataxes",
    "Hammer":               "Dormant Power Helps Discover Hammers",
    "Flail":                "Dormant Power Helps Discover Flails",
    "Great Hammer":         "Dormant Power Helps Discover Great Hammers",
    "Colossal Weapon":      "Dormant Power Helps Discover Colossal Weapons",
    "Spear":                "Dormant Power Helps Discover Spears",
    "Great Spear":          "Dormant Power Helps Discover Great Spears",
    "Halberd":              "Dormant Power Helps Discover Halberds",
    "Reaper":               "Dormant Power Helps Discover Reapers",
    "Whip":                 "Dormant Power Helps Discover Whips",
    "Fist":                 "Dormant Power Helps Discover Fists",
    "Claw":                 "Dormant Power Helps Discover Claws",
    "Bow":                  "Dormant Power Helps Discover Bows",
    "Greatbow":             "Dormant Power Helps Discover Greatbows",
    "Crossbow":             "Dormant Power Helps Discover Crossbows",
    "Ballista":             "Dormant Power Helps Discover Ballistas",
    "Glintstone Staff":     "Dormant Power Helps Discover Staves",
    "Sacred Seal":          "Dormant Power Helps Discover Sacred Seals",
    "Small Shield":         "Dormant Power Helps Discover Small Shields",
    "Medium Shield":        "Dormant Power Helps Discover Medium Shields",
    "Greatshield":          "Dormant Power Helps Discover Greatshields",
}

# Reverse mapping: passive → weapon class
DORMANT_POWER_TO_WEAPON_CLASS = {v: k for k, v in WEAPON_CLASS_TO_DORMANT_POWER.items()}


# ── Weapon class → attack power passive mapping ────────────────────────────────
# Maps weapon class → the "Improved <class> Attack Power" passive name.

WEAPON_CLASS_TO_ATTACK_PASSIVE = {
    "Dagger":               "Improved Dagger Attack Power",
    "Thrusting Sword":      "Improved Thrusting Sword Attack Power",
    "Heavy Thrusting Sword":"Improved Heavy Thrusting Sword Attack Power",
    "Straight Sword":       "Improved Straight Sword Attack Power",
    "Greatsword":           "Improved Greatsword Attack Power",
    "Colossal Sword":       "Improved Colossal Sword Attack Power",
    "Curved Sword":         "Improved Curved Sword Attack Power",
    "Curved Greatsword":    "Improved Curved Greatsword Attack Power",
    "Katana":               "Improved Katana Attack Power",
    "Twinblade":            "Improved Twinblade Attack Power",
    "Axe":                  "Improved Axe Attack Power",
    "Greataxe":             "Improved Greataxe Attack Power",
    "Hammer":               "Improved Hammer Attack Power",
    "Flail":                "Improved Flail Attack Power",
    "Great Hammer":         "Improved Great Hammer Attack Power",
    "Colossal Weapon":      "Improved Colossal Weapon Attack Power",
    "Spear":                "Improved Spear Attack Power",
    "Great Spear":          "Improved Great Spear Attack Power",
    "Halberd":              "Improved Halberd Attack Power",
    "Reaper":               "Improved Reaper Attack Power",
    "Whip":                 "Improved Whip Attack Power",
    "Fist":                 "Improved Fist Attack Power",
    "Claw":                 "Improved Claw Attack Power",
    "Bow":                  "Improved Bow Attack Power",
    # Greatbow, Crossbow, Ballista, Staves, Seals, Shields have no "Improved X Attack Power"
}


# ── Weapons ────────────────────────────────────────────────────────────────────
# Each entry: name, weapon class, physical damage subtypes, affinity (None = physical),
# primary scaling stats, innate status effect (None if none), default weapon skill,
# whether it can be infused with an affinity.
#
# ── Weapons & Skills: imported from datamine-verified modules ──────────────────
# NIGHTREIGN_WEAPONS: 50 base weapons with categories, damage, skill pools
# WEAPON_SKILLS_FULL: 183 weapon skills with affinity, damage types, status
# NIGHTREIGN_SORCERIES / NIGHTREIGN_INCANTATIONS: spells with damage types
from database.nightreign_weapons import NIGHTREIGN_WEAPONS
from database.nightreign_weapon_skills import WEAPON_SKILLS_FULL
from database.nightreign_spells import SORCERIES as NIGHTREIGN_SORCERIES
from database.nightreign_spells import INCANTATIONS as NIGHTREIGN_INCANTATIONS

# Legacy WEAPONS list — kept for backward compatibility with existing code
# that iterates game_knowledge.WEAPONS as a list of dicts.
# TODO: migrate callers to use NIGHTREIGN_WEAPONS dict directly.
WEAPONS = [

    # ── Daggers ────────────────────────────────────────────────────────────────
    {
        "name": "Dagger",
        "class": "Dagger",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Quickstep",
        "infusable": True,
    },
    {
        "name": "Parrying Dagger",
        "class": "Dagger",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Parry",
        "infusable": True,
    },
    {
        "name": "Misericorde",
        "class": "Dagger",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Quickstep",
        "infusable": True,
    },
    {
        "name": "Reduvia",
        "class": "Dagger",
        "damage_types": ["Slash", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity", "Arcane"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Reduvia Blood Blade",
        "infusable": False,
    },
    {
        "name": "Ivory Sickle",
        "class": "Dagger",
        "damage_types": ["Slash"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Quickstep",
        "infusable": True,  # TODO: verify
    },
    {
        "name": "Black Knife",
        "class": "Dagger",
        "damage_types": ["Standard", "Pierce"],
        "affinity": "Holy",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Blade of Death",
        "infusable": False,
    },
    {
        "name": "Scorpion's Stinger",
        "class": "Dagger",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity", "Arcane"],
        "innate_status": "Poison",
        "weapon_skill": "Quickstep",
        "infusable": False,  # TODO: verify
    },

    # ── Thrusting Swords ───────────────────────────────────────────────────────
    {
        "name": "Estoc",
        "class": "Thrusting Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Impaling Thrust",
        "infusable": True,
    },
    {
        "name": "Rapier",
        "class": "Thrusting Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Impaling Thrust",
        "infusable": True,
    },
    {
        "name": "Rogier's Rapier",
        "class": "Thrusting Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": "Magic",
        "scaling": ["Strength", "Dexterity", "Intelligence"],
        "innate_status": None,
        "weapon_skill": "Glintblade Phalanx",
        "infusable": False,
    },
    {
        "name": "Cleanrot Knight's Sword",
        "class": "Thrusting Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": "Holy",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": "Scarlet Rot",
        "weapon_skill": "Sacred Order",
        "infusable": False,  # TODO: verify
    },

    # ── Heavy Thrusting Swords ─────────────────────────────────────────────────
    {
        "name": "Bloody Helice",
        "class": "Heavy Thrusting Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity", "Arcane"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Dynast's Finesse",
        "infusable": False,
    },
    {
        "name": "Crystal Spear",
        "class": "Heavy Thrusting Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": "Magic",
        "scaling": ["Strength", "Dexterity", "Intelligence"],
        "innate_status": None,
        "weapon_skill": "Impaling Thrust",
        "infusable": False,  # TODO: verify
    },

    # ── Straight Swords ────────────────────────────────────────────────────────
    {
        "name": "Longsword",
        "class": "Straight Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Storm Stomp",
        "infusable": True,
    },
    {
        "name": "Broadsword",
        "class": "Straight Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,
    },
    {
        "name": "Lordsworn's Straight Sword",
        "class": "Straight Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,
    },
    {
        "name": "Weathered Straight Sword",
        "class": "Straight Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,  # TODO: verify
    },
    {
        "name": "Cane Sword",
        "class": "Straight Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Impaling Thrust",
        "infusable": True,  # TODO: verify
    },
    {
        "name": "Sword of Night and Flame",
        "class": "Straight Sword",
        "damage_types": ["Standard"],
        "affinity": "Magic",        # has both Magic and Fire; primary listed as Magic # TODO: verify
        "scaling": ["Strength", "Dexterity", "Intelligence", "Faith"],
        "innate_status": None,
        "weapon_skill": "Night-and-Flame Stance",
        "infusable": False,
    },
    {
        "name": "Miquellan Knight's Sword",
        "class": "Straight Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": "Holy",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Sacred Blade",
        "infusable": False,
    },
    {
        "name": "Coded Sword",
        "class": "Straight Sword",
        "damage_types": ["Standard"],
        "affinity": "Holy",
        "scaling": ["Faith"],
        "innate_status": None,
        "weapon_skill": "Unblockable Blade",
        "infusable": False,
    },
    {
        "name": "Regalia of Eochaid",
        "class": "Straight Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity", "Arcane"],
        "innate_status": None,
        "weapon_skill": "Eochaid's Dancing Blade",
        "infusable": False,
    },

    # ── Greatswords ────────────────────────────────────────────────────────────
    {
        "name": "Claymore",
        "class": "Greatsword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Lion's Claw",
        "infusable": True,
    },
    {
        "name": "Knight's Greatsword",
        "class": "Greatsword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,
    },
    {
        "name": "Iron Greatsword",
        "class": "Greatsword",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,
    },
    {
        "name": "Lordsworn's Greatsword",
        "class": "Greatsword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,
    },
    {
        "name": "Flamberge",
        "class": "Greatsword",
        "damage_types": ["Slash"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Spinning Slash",
        "infusable": True,
    },
    {
        "name": "Banished Knight's Greatsword",
        "class": "Greatsword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,
    },
    {
        "name": "Gargoyle's Greatsword",
        "class": "Greatsword",
        "damage_types": ["Standard"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,  # TODO: verify
    },
    {
        "name": "Inseparable Sword",
        "class": "Greatsword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": "Holy",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Sacred Order",
        "infusable": False,
    },
    {
        "name": "Zweihander",
        "class": "Greatsword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,
    },
    {
        "name": "Watchdog's Greatsword",
        "class": "Greatsword",
        "damage_types": ["Standard"],
        "affinity": "Fire",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Spearcall Ritual",  # TODO: verify skill name
        "infusable": False,
    },

    # ── Colossal Swords ────────────────────────────────────────────────────────
    {
        "name": "Greatsword",
        "class": "Colossal Sword",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,
    },
    {
        "name": "Grafted Blade Greatsword",
        "class": "Colossal Sword",
        "damage_types": ["Standard"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Oath of Vengeance",
        "infusable": False,
    },
    {
        "name": "Starscourge Greatsword",
        "class": "Colossal Sword",
        "damage_types": ["Standard"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Starcaller Cry",
        "infusable": False,
    },
    {
        "name": "Maliketh's Black Blade",
        "class": "Colossal Sword",
        "damage_types": ["Standard"],
        "affinity": "Holy",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Destined Death",
        "infusable": False,
    },
    {
        "name": "Ruins Greatsword",
        "class": "Colossal Sword",
        "damage_types": ["Standard"],
        "affinity": "Magic",
        "scaling": ["Strength", "Intelligence"],
        "innate_status": None,
        "weapon_skill": "Wave of Destruction",
        "infusable": False,
    },

    # ── Curved Swords ──────────────────────────────────────────────────────────
    {
        "name": "Scimitar",
        "class": "Curved Sword",
        "damage_types": ["Slash"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Spinning Slash",
        "infusable": True,
    },
    {
        "name": "Falchion",
        "class": "Curved Sword",
        "damage_types": ["Slash"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Spinning Slash",
        "infusable": True,
    },
    {
        "name": "Mantis Blade",
        "class": "Curved Sword",
        "damage_types": ["Slash", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Spinning Slash",
        "infusable": True,  # TODO: verify
    },
    {
        "name": "Omensmirk Machete",
        "class": "Curved Sword",
        "damage_types": ["Slash"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Spinning Slash",
        "infusable": True,  # TODO: verify
    },

    # ── Curved Greatswords ─────────────────────────────────────────────────────
    {
        "name": "Banished Knight's Halberd",  # TODO: verify — may not be Curved Greatsword
        "class": "Curved Greatsword",
        "damage_types": ["Slash"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Spinning Slash",
        "infusable": True,  # TODO: verify
    },
    {
        "name": "Magma Wyrm's Scalesword",
        "class": "Curved Greatsword",
        "damage_types": ["Slash"],
        "affinity": "Fire",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Magma Guillotine",
        "infusable": False,
    },

    # ── Katanas ────────────────────────────────────────────────────────────────
    {
        "name": "Uchigatana",
        "class": "Katana",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Unsheathe",
        "infusable": True,
    },
    {
        "name": "Nagakiba",
        "class": "Katana",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Unsheathe",
        "infusable": True,
    },
    {
        "name": "Hand of Malenia",
        "class": "Katana",
        "damage_types": ["Slash", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Waterfowl Dance",
        "infusable": False,
    },
    {
        "name": "Moonveil",
        "class": "Katana",
        "damage_types": ["Standard", "Pierce"],
        "affinity": "Magic",
        "scaling": ["Strength", "Dexterity", "Intelligence"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Transient Moonlight",
        "infusable": False,
    },
    {
        "name": "Rivers of Blood",
        "class": "Katana",
        "damage_types": ["Slash", "Pierce"],
        "affinity": "Fire",
        "scaling": ["Strength", "Dexterity", "Arcane"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Corpse Piler",
        "infusable": False,
    },
    {
        "name": "Serpentbone Blade",
        "class": "Katana",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": "Poison",
        "weapon_skill": "Double Slash",
        "infusable": False,
    },

    # ── Twinblades ─────────────────────────────────────────────────────────────
    {
        "name": "Twinblade",
        "class": "Twinblade",
        "damage_types": ["Slash"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Spinning Slash",
        "infusable": True,
    },
    {
        "name": "Eleonora's Poleblade",
        "class": "Twinblade",
        "damage_types": ["Slash"],
        "affinity": "Fire",
        "scaling": ["Strength", "Dexterity", "Arcane"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Bloodblade Dance",
        "infusable": False,
    },
    {
        "name": "Godskin Peeler",
        "class": "Twinblade",
        "damage_types": ["Slash", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Black Flame Tornado",
        "infusable": True,
    },

    # ── Axes ───────────────────────────────────────────────────────────────────
    {
        "name": "Limiter's Axe",
        "class": "Axe",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,  # TODO: verify
    },
    {
        "name": "Hand Axe",
        "class": "Axe",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,
    },
    {
        "name": "Lordsworn's Axe",
        "class": "Axe",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,
    },
    {
        "name": "Ripple Blade",
        "class": "Axe",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Arcane"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": False,  # TODO: verify
    },
    {
        "name": "Jawbone Axe",
        "class": "Axe",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,  # TODO: verify
    },

    # ── Greataxes ──────────────────────────────────────────────────────────────
    {
        "name": "Greataxe",
        "class": "Greataxe",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,
    },
    {
        "name": "Executioner's Greataxe",
        "class": "Greataxe",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,
    },
    {
        "name": "Rusted Anchor",
        "class": "Greataxe",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,  # TODO: verify
    },
    {
        "name": "Gargoyle's Great Axe",
        "class": "Greataxe",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,  # TODO: verify
    },

    # ── Hammers ────────────────────────────────────────────────────────────────
    {
        "name": "Club",
        "class": "Hammer",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,
    },
    {
        "name": "Mace",
        "class": "Hammer",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,
    },
    {
        "name": "Morning Star",
        "class": "Hammer",
        "damage_types": ["Strike", "Pierce"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Stamp (Upward Cut)",
        "infusable": True,
    },
    {
        "name": "Cranial Vessel Candlestand",
        "class": "Hammer",
        "damage_types": ["Strike"],
        "affinity": "Fire",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Surge of Faith",
        "infusable": False,  # TODO: verify
    },

    # ── Flails ─────────────────────────────────────────────────────────────────
    {
        "name": "Flail",
        "class": "Flail",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Spinning Chain",
        "infusable": True,
    },
    {
        "name": "Family Heads",
        "class": "Flail",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Familial Rancor",
        "infusable": False,
    },

    # ── Great Hammers ──────────────────────────────────────────────────────────
    {
        "name": "Large Club",
        "class": "Great Hammer",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,
    },
    {
        "name": "Great Club",
        "class": "Great Hammer",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,
    },
    {
        "name": "Envoy's Horn",
        "class": "Great Hammer",
        "damage_types": ["Strike"],
        "affinity": "Holy",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Bubble Shower",
        "infusable": False,
    },

    # ── Colossal Weapons ───────────────────────────────────────────────────────
    {
        "name": "Giant-Crusher",
        "class": "Colossal Weapon",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,
    },
    {
        "name": "Prelate's Inferno Crozier",
        "class": "Colossal Weapon",
        "damage_types": ["Strike"],
        "affinity": "Fire",
        "scaling": ["Strength", "Faith"],
        "innate_status": None,
        "weapon_skill": "Prelate's Charge",
        "infusable": False,
    },
    {
        "name": "Watchdog's Staff",
        "class": "Colossal Weapon",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,  # TODO: verify
    },

    # ── Spears ─────────────────────────────────────────────────────────────────
    {
        "name": "Spear",
        "class": "Spear",
        "damage_types": ["Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Impaling Thrust",
        "infusable": True,
    },
    {
        "name": "Torchpole",
        "class": "Spear",
        "damage_types": ["Pierce"],
        "affinity": "Fire",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Impaling Thrust",
        "infusable": False,  # TODO: verify
    },
    {
        "name": "Cleanrot Spear",
        "class": "Spear",
        "damage_types": ["Pierce"],
        "affinity": "Holy",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": "Scarlet Rot",
        "weapon_skill": "Sacred Order",
        "infusable": False,
    },
    {
        "name": "Rotten Crystal Spear",
        "class": "Spear",
        "damage_types": ["Pierce"],
        "affinity": "Magic",
        "scaling": ["Strength", "Dexterity", "Intelligence"],
        "innate_status": "Scarlet Rot",
        "weapon_skill": "Impaling Thrust",
        "infusable": False,
    },

    # ── Great Spears ───────────────────────────────────────────────────────────
    {
        "name": "Partisan",
        "class": "Great Spear",
        "damage_types": ["Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Impaling Thrust",
        "infusable": True,
    },
    {
        "name": "Lance",
        "class": "Great Spear",
        "damage_types": ["Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Impaling Thrust",
        "infusable": True,
    },
    {
        "name": "Vyke's War Spear",
        "class": "Great Spear",
        "damage_types": ["Pierce"],
        "affinity": "Lightning",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": "Madness",
        "weapon_skill": "Frenzyflame Thrust",
        "infusable": False,
    },

    # ── Halberds ───────────────────────────────────────────────────────────────
    {
        "name": "Halberd",
        "class": "Halberd",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Impaling Thrust",
        "infusable": True,
    },
    {
        "name": "Golden Halberd",
        "class": "Halberd",
        "damage_types": ["Standard", "Pierce"],
        "affinity": "Holy",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Golden Vow",
        "infusable": False,
    },
    {
        "name": "Loretta's War Sickle",
        "class": "Halberd",
        "damage_types": ["Slash", "Pierce"],
        "affinity": "Magic",
        "scaling": ["Strength", "Dexterity", "Intelligence"],
        "innate_status": None,
        "weapon_skill": "Loretta's Slash",
        "infusable": False,
    },
    {
        "name": "Gargoyle's Black Halberd",
        "class": "Halberd",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Impaling Thrust",
        "infusable": True,  # TODO: verify
    },

    # ── Reapers ────────────────────────────────────────────────────────────────
    {
        "name": "Scythe",
        "class": "Reaper",
        "damage_types": ["Slash", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Spinning Slash",
        "infusable": True,
    },
    {
        "name": "Grave Scythe",
        "class": "Reaper",
        "damage_types": ["Slash", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Spinning Slash",
        "infusable": True,
    },
    {
        "name": "Death's Poker",
        "class": "Reaper",
        "damage_types": ["Standard", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": "Frostbite",
        "weapon_skill": "Ghostflame Ignition",
        "infusable": False,
    },

    # ── Whips ──────────────────────────────────────────────────────────────────
    {
        "name": "Whip",
        "class": "Whip",
        "damage_types": ["Standard"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Kick",
        "infusable": True,
    },
    {
        "name": "Thorned Whip",
        "class": "Whip",
        "damage_types": ["Slash"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Kick",
        "infusable": False,  # TODO: verify
    },
    {
        "name": "Urumi",
        "class": "Whip",
        "damage_types": ["Slash"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Kick",
        "infusable": True,  # TODO: verify
    },

    # ── Fists ──────────────────────────────────────────────────────────────────
    {
        "name": "Caestus",
        "class": "Fist",
        "damage_types": ["Strike"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,
    },
    {
        "name": "Spiked Caestus",
        "class": "Fist",
        "damage_types": ["Strike", "Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Endure",
        "infusable": True,
    },
    {
        "name": "Veteran's Prosthesis",
        "class": "Fist",
        "damage_types": ["Strike"],
        "affinity": "Lightning",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Prosthesis-Wearer Heirloom",  # TODO: verify skill name
        "infusable": False,
    },

    # ── Claws ──────────────────────────────────────────────────────────────────
    {
        "name": "Claws",
        "class": "Claw",
        "damage_types": ["Slash"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Quickstep",
        "infusable": True,
    },
    {
        "name": "Hookclaws",
        "class": "Claw",
        "damage_types": ["Slash"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": "Hemorrhage",
        "weapon_skill": "Quickstep",
        "infusable": True,
    },
    {
        "name": "Venomous Fang",
        "class": "Claw",
        "damage_types": ["Slash"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": "Poison",
        "weapon_skill": "Quickstep",
        "infusable": False,  # TODO: verify
    },

    # ── Bows ───────────────────────────────────────────────────────────────────
    {
        "name": "Short Bow",
        "class": "Bow",
        "damage_types": ["Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Barrage",
        "infusable": False,
    },
    {
        "name": "Composite Bow",
        "class": "Bow",
        "damage_types": ["Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Mighty Shot",
        "infusable": False,
    },
    {
        "name": "Horn Bow",
        "class": "Bow",
        "damage_types": ["Pierce"],
        "affinity": "Magic",
        "scaling": ["Strength", "Dexterity", "Intelligence"],
        "innate_status": None,
        "weapon_skill": "Mighty Shot",
        "infusable": False,
    },
    {
        "name": "Serpent Bow",
        "class": "Bow",
        "damage_types": ["Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity", "Arcane"],
        "innate_status": "Poison",
        "weapon_skill": "Mighty Shot",
        "infusable": False,
    },

    # ── Greatbows ──────────────────────────────────────────────────────────────
    {
        "name": "Erdtree Greatbow",
        "class": "Greatbow",
        "damage_types": ["Pierce"],
        "affinity": "Holy",
        "scaling": ["Strength", "Dexterity", "Faith"],
        "innate_status": None,
        "weapon_skill": "Through and Through",
        "infusable": False,
    },

    # ── Crossbows ──────────────────────────────────────────────────────────────
    {
        "name": "Light Crossbow",
        "class": "Crossbow",
        "damage_types": ["Pierce"],
        "affinity": None,
        "scaling": ["Strength", "Dexterity"],
        "innate_status": None,
        "weapon_skill": "Kick",
        "infusable": False,
    },
    {
        "name": "Arbalest",
        "class": "Crossbow",
        "damage_types": ["Pierce"],
        "affinity": None,
        "scaling": ["Strength"],
        "innate_status": None,
        "weapon_skill": "Kick",
        "infusable": False,
    },

    # ── Catalysts (Glintstone Staves) ──────────────────────────────────────────
    {
        "name": "Demi-Human Queen's Staff",
        "class": "Glintstone Staff",
        "damage_types": ["Standard"],
        "affinity": "Magic",
        "scaling": ["Strength", "Dexterity", "Intelligence"],
        "innate_status": None,
        "weapon_skill": "Spinning Weapon",
        "infusable": False,
    },
    {
        "name": "Academy Glintstone Staff",
        "class": "Glintstone Staff",
        "damage_types": ["Standard"],
        "affinity": "Magic",
        "scaling": ["Strength", "Intelligence"],
        "innate_status": None,
        "weapon_skill": "Spinning Weapon",
        "infusable": False,
    },
    {
        "name": "Carian Regal Scepter",
        "class": "Glintstone Staff",
        "damage_types": ["Standard"],
        "affinity": "Magic",
        "scaling": ["Strength", "Intelligence"],
        "innate_status": None,
        "weapon_skill": "Spinning Weapon",
        "infusable": False,
    },
    {
        "name": "Staff of the Guilty",
        "class": "Glintstone Staff",
        "damage_types": ["Standard"],
        "affinity": "Magic",
        "scaling": ["Strength", "Faith", "Arcane"],
        "innate_status": None,
        "weapon_skill": "Spinning Weapon",
        "infusable": False,  # TODO: verify
    },

    # ── Catalysts (Sacred Seals) ───────────────────────────────────────────────
    {
        "name": "Finger Seal",
        "class": "Sacred Seal",
        "damage_types": ["Standard"],
        "affinity": "Holy",
        "scaling": ["Strength", "Faith"],
        "innate_status": None,
        "weapon_skill": "Unfaltering Prayer",
        "infusable": False,
    },
    {
        "name": "Golden Order Seal",
        "class": "Sacred Seal",
        "damage_types": ["Standard"],
        "affinity": "Holy",
        "scaling": ["Intelligence", "Faith"],
        "innate_status": None,
        "weapon_skill": "Unfaltering Prayer",
        "infusable": False,
    },
    {
        "name": "Dragon Communion Seal",
        "class": "Sacred Seal",
        "damage_types": ["Standard"],
        "affinity": "Fire",
        "scaling": ["Faith", "Arcane"],
        "innate_status": None,
        "weapon_skill": "Unfaltering Prayer",
        "infusable": False,
    },
    {
        "name": "Giant's Seal",
        "class": "Sacred Seal",
        "damage_types": ["Standard"],
        "affinity": "Fire",
        "scaling": ["Strength", "Faith"],
        "innate_status": None,
        "weapon_skill": "Unfaltering Prayer",
        "infusable": False,
    },
    {
        "name": "Frenzied Flame Seal",
        "class": "Sacred Seal",
        "damage_types": ["Standard"],
        "affinity": "Fire",
        "scaling": ["Strength", "Dexterity", "Faith", "Arcane"],
        "innate_status": None,
        "weapon_skill": "Unfaltering Prayer",
        "infusable": False,
    },
    {
        "name": "Godslayer's Seal",
        "class": "Sacred Seal",
        "damage_types": ["Standard"],
        "affinity": "Holy",
        "scaling": ["Strength", "Faith"],
        "innate_status": None,
        "weapon_skill": "Unfaltering Prayer",
        "infusable": False,
    },
]


# ── Weapon skills (legacy — 69 entries) ────────────────────────────────────────
# Kept for backward compatibility. The authoritative source is now
# WEAPON_SKILLS_FULL (183 entries) imported from database/nightreign_weapon_skills.py.
# TODO: migrate callers to use WEAPON_SKILLS_FULL directly.

WEAPON_SKILLS = {
    # ── Physical / General ─────────────────────────────────────────────────────
    "Unsheathe":            {"damage_types": ["Standard", "Pierce"], "affinity": None},
    "Waterfowl Dance":      {"damage_types": ["Slash", "Pierce"],    "affinity": None},
    "Double Slash":         {"damage_types": ["Standard", "Pierce"], "affinity": None},
    "Spinning Slash":       {"damage_types": ["Slash"],              "affinity": None},
    "Lion's Claw":          {"damage_types": ["Standard"],           "affinity": None},
    "Stamp (Upward Cut)":   {"damage_types": ["Standard"],           "affinity": None},
    "Impaling Thrust":      {"damage_types": ["Pierce"],             "affinity": None},
    "Endure":               {"damage_types": [],                     "affinity": None},
    "Quickstep":            {"damage_types": [],                     "affinity": None},
    "Kick":                 {"damage_types": ["Strike"],             "affinity": None},
    "Parry":                {"damage_types": [],                     "affinity": None},
    "Storm Stomp":          {"damage_types": ["Standard"],           "affinity": None},
    "Spinning Chain":       {"damage_types": ["Strike"],             "affinity": None},
    "Spinning Weapon":      {"damage_types": ["Standard"],           "affinity": None},
    "Determination":        {"damage_types": [],                     "affinity": None},
    "Rain of Arrows":       {"damage_types": ["Pierce"],             "affinity": None},
    "Barrage":              {"damage_types": ["Pierce"],             "affinity": None},
    "Mighty Shot":          {"damage_types": ["Pierce"],             "affinity": None},
    "Through and Through":  {"damage_types": ["Pierce"],             "affinity": None},

    # ── Lightning ─────────────────────────────────────────────────────────────
    "Thunderbolt":          {"damage_types": [], "affinity": "Lightning"},
    "Lightning Slash":      {"damage_types": [], "affinity": "Lightning"},
    "Frenzyflame Thrust":   {"damage_types": [], "affinity": "Fire", "innate_status": "Madness"},

    # ── Fire ──────────────────────────────────────────────────────────────────
    "Flaming Strike":       {"damage_types": [], "affinity": "Fire"},
    "Eruption":             {"damage_types": [], "affinity": "Fire"},
    "Magma Guillotine":     {"damage_types": [], "affinity": "Fire"},
    "Prelate's Charge":     {"damage_types": [], "affinity": "Fire"},
    "Black Flame Tornado":  {"damage_types": [], "affinity": "Fire"},
    "Surge of Faith":       {"damage_types": [], "affinity": "Fire"},
    "Corpse Piler":         {"damage_types": ["Slash"], "affinity": "Fire"},
    "Bloodblade Dance":     {"damage_types": ["Slash"], "affinity": "Fire"},
    "Ghostflame Ignition":  {"damage_types": [], "affinity": "Magic", "innate_status": "Frostbite"},

    # ── Magic ─────────────────────────────────────────────────────────────────
    "Glintblade Phalanx":       {"damage_types": [], "affinity": "Magic"},
    "Transient Moonlight":      {"damage_types": [], "affinity": "Magic"},
    "Loretta's Slash":          {"damage_types": ["Slash"], "affinity": "Magic"},
    "Night-and-Flame Stance":   {"damage_types": [], "affinity": "Magic"},  # has both; primary Magic
    "Wave of Destruction":      {"damage_types": [], "affinity": "Magic"},
    "Eochaid's Dancing Blade":  {"damage_types": ["Standard"], "affinity": "Magic"},

    # ── Holy ──────────────────────────────────────────────────────────────────
    "Sacred Blade":         {"damage_types": [], "affinity": "Holy"},
    "Prayerful Strike":     {"damage_types": [], "affinity": "Holy"},
    "Sacred Order":         {"damage_types": [], "affinity": "Holy"},
    "Blade of Death":       {"damage_types": [], "affinity": "Holy"},
    "Golden Vow":           {"damage_types": [], "affinity": "Holy"},
    "Unblockable Blade":    {"damage_types": [], "affinity": "Holy"},
    "Destined Death":       {"damage_types": [], "affinity": "Holy"},
    "Bubble Shower":        {"damage_types": [], "affinity": "Holy"},
    "Oath of Vengeance":    {"damage_types": [],                     "affinity": None},

    # ── Poison / Status ───────────────────────────────────────────────────────
    "Poisonous Mist":       {"damage_types": [], "affinity": None, "innate_status": "Poison"},
    "Poison Moth Flight":   {"damage_types": [], "affinity": None, "innate_status": "Poison"},
    "Blood Blade":          {"damage_types": [], "affinity": None, "innate_status": "Hemorrhage"},
    "Seppuku":              {"damage_types": [], "affinity": None, "innate_status": "Hemorrhage"},
    "Chilling Mist":        {"damage_types": [], "affinity": None, "innate_status": "Frostbite"},
    "Hoarfrost Stomp":      {"damage_types": [], "affinity": None, "innate_status": "Frostbite"},
    "White Shadow's Lure":  {"damage_types": [], "affinity": None, "innate_status": "Sleep"},

    # ── Unique skills ─────────────────────────────────────────────────────────
    "Starcaller Cry":       {"damage_types": ["Strike"], "affinity": "Magic"},
    "Dynast's Finesse":     {"damage_types": ["Pierce"], "affinity": None},
    "Reduvia Blood Blade":  {"damage_types": [], "affinity": None, "innate_status": "Hemorrhage"},
    "Familial Rancor":      {"damage_types": [], "affinity": "Magic"},
    "Gravitas":             {"damage_types": [], "affinity": "Magic"},
    "Unfaltering Prayer":   {"damage_types": [], "affinity": None},

    # ── Spell-as-skill (from Starting Armaments passives) ─────────────────────
    "Magic Glintblade":         {"damage_types": [], "affinity": "Magic"},
    "Carian Greatsword":        {"damage_types": [], "affinity": "Magic"},
    "Night Shard":              {"damage_types": [], "affinity": "Magic"},
    "Magma Shot":               {"damage_types": [], "affinity": "Fire"},
    "Briars of Punishment":     {"damage_types": [], "affinity": "Magic"},
    "Wrath of Gold":            {"damage_types": [], "affinity": "Holy"},
    "Lightning Spear":          {"damage_types": [], "affinity": "Lightning"},
    "O, Flame!":                {"damage_types": [], "affinity": "Fire"},
    "Beast Claw":               {"damage_types": ["Standard"], "affinity": None},
    "Dragonfire":               {"damage_types": [], "affinity": "Fire"},
}


# ── Passive category map ───────────────────────────────────────────────────────
# Maps exact passive name (as it appears in relic OCR / passives.py) →
# semantic category used by the synergy engine.
#
# Categories:
#   physical_damage       — boosts physical attack directly
#   affinity_damage       — boosts all affinity (elemental) attack
#   specific_affinity     — boosts one specific affinity (Magic/Fire/Lightning/Holy)
#   incantation_any       — boosts all incantations (delivery buff)
#   incantation_school    — boosts incantations of a specific school (stacks with above)
#   sorcery_any           — boosts all sorceries
#   sorcery_school        — boosts sorceries of a specific school
#   status_buildup        — increases status buildup application
#   status_resistance     — reduces incoming status buildup
#   scaling_stat          — adds points to a scaling attribute
#   weapon_class_power    — boosts a specific weapon class's attack power
#   weapon_class_dormant  — Dormant Power passive for a weapon class
#   weapon_class_3x       — "Improved Attack Power with 3+ <class> Equipped"
#   hp_restore_on_hit     — HP restored on weapon attacks
#   fp_restore_on_hit     — FP restored on weapon attacks
#   character_skill       — buffs/modifies character-specific skill
#   damage_negation       — reduces incoming damage
#   utility               — everything else (stats, QoL, etc.)

PASSIVE_CATEGORY: "dict[str, str]" = {

    # ── Direct damage — physical ───────────────────────────────────────────────
    "Physical Attack Up":                               "physical_damage",
    "Physical Attack Up +1":                            "physical_damage",
    "Physical Attack Up +2":                            "physical_damage",
    "Physical Attack Up +3":                            "physical_damage",
    "Physical Attack Up +4":                            "physical_damage",

    # ── Direct damage — all affinity ──────────────────────────────────────────
    "Improved Affinity Attack Power":                   "affinity_damage",
    "Improved Affinity Attack Power +1":                "affinity_damage",
    "Improved Affinity Attack Power +2":                "affinity_damage",

    # ── Direct damage — element-specific ──────────────────────────────────────
    "Magic Attack Power Up":                            "specific_affinity",
    "Magic Attack Power Up +1":                         "specific_affinity",
    "Magic Attack Power Up +2":                         "specific_affinity",
    "Magic Attack Power Up +3":                         "specific_affinity",
    "Magic Attack Power Up +4":                         "specific_affinity",
    "Fire Attack Power Up":                             "specific_affinity",
    "Fire Attack Power Up +1":                          "specific_affinity",
    "Fire Attack Power Up +2":                          "specific_affinity",
    "Fire Attack Power Up +3":                          "specific_affinity",
    "Fire Attack Power Up +4":                          "specific_affinity",
    "Lightning Attack Power Up":                        "specific_affinity",
    "Lightning Attack Power Up +1":                     "specific_affinity",
    "Lightning Attack Power Up +2":                     "specific_affinity",
    "Lightning Attack Power Up +3":                     "specific_affinity",
    "Lightning Attack Power Up +4":                     "specific_affinity",
    "Holy Attack Power Up":                             "specific_affinity",
    "Holy Attack Power Up +1":                          "specific_affinity",
    "Holy Attack Power Up +2":                          "specific_affinity",
    "Holy Attack Power Up +3":                          "specific_affinity",
    "Holy Attack Power Up +4":                          "specific_affinity",

    # ── Direct damage — incantations ──────────────────────────────────────────
    "Improved Incantations":                            "incantation_any",
    "Improved Incantations +1":                         "incantation_any",
    "Improved Incantations +2":                         "incantation_any",

    # ── Incantation school-specific (stacks with incantation_any) ─────────────
    "Improved Dragon Cult Incantations":                "incantation_school",
    "Improved Giants' Flame Incantations":              "incantation_school",
    "Improved Godslayer Incantations":                  "incantation_school",
    "Improved Bestial Incantations":                    "incantation_school",
    "Improved Frenzied Flame Incantations":             "incantation_school",
    "Improved Dragon Communion Incantations":           "incantation_school",
    "Improved Fundamentalist Incantations":             "incantation_school",

    # ── Direct damage — sorceries ─────────────────────────────────────────────
    "Improved Sorceries":                               "sorcery_any",
    "Improved Sorceries +1":                            "sorcery_any",
    "Improved Sorceries +2":                            "sorcery_any",

    # ── Sorcery school-specific (stacks with sorcery_any) ─────────────────────
    "Improved Glintblade Sorcery":                      "sorcery_school",
    "Improved Stonedigger Sorcery":                     "sorcery_school",
    "Improved Carian Sword Sorcery":                    "sorcery_school",
    "Improved Invisibility Sorcery":                    "sorcery_school",
    "Improved Crystalian Sorcery":                      "sorcery_school",
    "Improved Gravity Sorcery":                         "sorcery_school",
    "Improved Thorn Sorcery":                           "sorcery_school",

    # ── Weapon class — attack power ───────────────────────────────────────────
    "Improved Dagger Attack Power":                     "weapon_class_power",
    "Improved Thrusting Sword Attack Power":            "weapon_class_power",
    "Improved Heavy Thrusting Sword Attack Power":      "weapon_class_power",
    "Improved Straight Sword Attack Power":             "weapon_class_power",
    "Improved Greatsword Attack Power":                 "weapon_class_power",
    "Improved Colossal Sword Attack Power":             "weapon_class_power",
    "Improved Curved Sword Attack Power":               "weapon_class_power",
    "Improved Curved Greatsword Attack Power":          "weapon_class_power",
    "Improved Katana Attack Power":                     "weapon_class_power",
    "Improved Twinblade Attack Power":                  "weapon_class_power",
    "Improved Axe Attack Power":                        "weapon_class_power",
    "Improved Greataxe Attack Power":                   "weapon_class_power",
    "Improved Hammer Attack Power":                     "weapon_class_power",
    "Improved Flail Attack Power":                      "weapon_class_power",
    "Improved Great Hammer Attack Power":               "weapon_class_power",
    "Improved Colossal Weapon Attack Power":            "weapon_class_power",
    "Improved Spear Attack Power":                      "weapon_class_power",
    "Improved Great Spear Attack Power":                "weapon_class_power",
    "Improved Halberd Attack Power":                    "weapon_class_power",
    "Improved Reaper Attack Power":                     "weapon_class_power",
    "Improved Whip Attack Power":                       "weapon_class_power",
    "Improved Fist Attack Power":                       "weapon_class_power",
    "Improved Claw Attack Power":                       "weapon_class_power",
    "Improved Bow Attack Power":                        "weapon_class_power",

    # ── Weapon class — Dormant Power discovery ────────────────────────────────
    "Dormant Power Helps Discover Daggers":             "weapon_class_dormant",
    "Dormant Power Helps Discover Thrusting Swords":    "weapon_class_dormant",
    "Dormant Power Helps Discover Heavy Thrusting Swords": "weapon_class_dormant",
    "Dormant Power Helps Discover Straight Swords":     "weapon_class_dormant",
    "Dormant Power Helps Discover Greatswords":         "weapon_class_dormant",
    "Dormant Power Helps Discover Colossal Swords":     "weapon_class_dormant",
    "Dormant Power Helps Discover Curved Swords":       "weapon_class_dormant",
    "Dormant Power Helps Discover Curved Greatswords":  "weapon_class_dormant",
    "Dormant Power Helps Discover Katana":              "weapon_class_dormant",
    "Dormant Power Helps Discover Twinblades":          "weapon_class_dormant",
    "Dormant Power Helps Discover Axes":                "weapon_class_dormant",
    "Dormant Power Helps Discover Greataxes":           "weapon_class_dormant",
    "Dormant Power Helps Discover Hammers":             "weapon_class_dormant",
    "Dormant Power Helps Discover Flails":              "weapon_class_dormant",
    "Dormant Power Helps Discover Great Hammers":       "weapon_class_dormant",
    "Dormant Power Helps Discover Colossal Weapons":    "weapon_class_dormant",
    "Dormant Power Helps Discover Spears":              "weapon_class_dormant",
    "Dormant Power Helps Discover Great Spears":        "weapon_class_dormant",
    "Dormant Power Helps Discover Halberds":            "weapon_class_dormant",
    "Dormant Power Helps Discover Reapers":             "weapon_class_dormant",
    "Dormant Power Helps Discover Whips":               "weapon_class_dormant",
    "Dormant Power Helps Discover Fists":               "weapon_class_dormant",
    "Dormant Power Helps Discover Claws":               "weapon_class_dormant",
    "Dormant Power Helps Discover Bows":                "weapon_class_dormant",
    "Dormant Power Helps Discover Greatbows":           "weapon_class_dormant",
    "Dormant Power Helps Discover Crossbows":           "weapon_class_dormant",
    "Dormant Power Helps Discover Ballistas":           "weapon_class_dormant",
    "Dormant Power Helps Discover Staves":              "weapon_class_dormant",
    "Dormant Power Helps Discover Sacred Seals":        "weapon_class_dormant",
    "Dormant Power Helps Discover Small Shields":       "weapon_class_dormant",
    "Dormant Power Helps Discover Medium Shields":      "weapon_class_dormant",
    "Dormant Power Helps Discover Greatshields":        "weapon_class_dormant",

    # ── Weapon class — 3x equipped bonus ──────────────────────────────────────
    "Improved Attack Power with 3+ Daggers Equipped":              "weapon_class_3x",
    "Improved Attack Power with 3+ Thrusting Swords Equipped":     "weapon_class_3x",
    "Improved Attack Power with 3+ Heavy Thrusting Swords Equipped": "weapon_class_3x",
    "Improved Attack Power with 3+ Straight Swords Equipped":      "weapon_class_3x",
    "Improved Attack Power with 3+ Greatswords Equipped":          "weapon_class_3x",
    "Improved Attack Power with 3+ Colossal Swords Equipped":      "weapon_class_3x",
    "Improved Attack Power with 3+ Curved Swords Equipped":        "weapon_class_3x",
    "Improved Attack Power with 3+ Curved Greatswords Equipped":   "weapon_class_3x",
    "Improved Attack Power with 3+ Katana Equipped":               "weapon_class_3x",
    "Improved Attack Power with 3+ Twinblades Equipped":           "weapon_class_3x",
    "Improved Attack Power with 3+ Axes Equipped":                 "weapon_class_3x",
    "Improved Attack Power with 3+ Greataxes Equipped":            "weapon_class_3x",
    "Improved Attack Power with 3+ Hammers Equipped":              "weapon_class_3x",
    "Improved Attack Power with 3+ Flails Equipped":               "weapon_class_3x",
    "Improved Attack Power with 3+ Great Hammers Equipped":        "weapon_class_3x",
    "Improved Attack Power with 3+ Colossal Weapons Equipped":     "weapon_class_3x",
    "Improved Attack Power with 3+ Spears Equipped":               "weapon_class_3x",
    "Improved Attack Power with 3+ Great Spears Equipped":         "weapon_class_3x",
    "Improved Attack Power with 3+ Halberds Equipped":             "weapon_class_3x",
    "Improved Attack Power with 3+ Reapers Equipped":              "weapon_class_3x",
    "Improved Attack Power with 3+ Whips Equipped":                "weapon_class_3x",
    "Improved Attack Power with 3+ Fists Equipped":                "weapon_class_3x",
    "Improved Attack Power with 3+ Claws Equipped":                "weapon_class_3x",
    "Improved Attack Power with 3+ Bows Equipped":                 "weapon_class_3x",

    # ── HP/FP on weapon hit ───────────────────────────────────────────────────
    "HP Restoration upon Dagger Attacks":               "hp_restore_on_hit",
    "HP Restoration upon Thrusting Sword Attacks":      "hp_restore_on_hit",
    "HP Restoration upon Heavy Thrusting Sword Attacks":"hp_restore_on_hit",
    "HP Restoration upon Straight Sword Attacks":       "hp_restore_on_hit",
    "HP Restoration upon Greatsword Attacks":           "hp_restore_on_hit",
    "HP Restoration upon Colossal Sword Attacks":       "hp_restore_on_hit",
    "HP Restoration upon Curved Sword Attacks":         "hp_restore_on_hit",
    "HP Restoration upon Curved Greatsword Attacks":    "hp_restore_on_hit",
    "HP Restoration upon Katana Attacks":               "hp_restore_on_hit",
    "HP Restoration upon Twinblade Attacks":            "hp_restore_on_hit",
    "HP Restoration upon Axe Attacks":                  "hp_restore_on_hit",
    "HP Restoration upon Greataxe Attacks":             "hp_restore_on_hit",
    "HP Restoration upon Hammer Attacks":               "hp_restore_on_hit",
    "HP Restoration upon Flail Attacks":                "hp_restore_on_hit",
    "HP Restoration upon Great Hammer Attacks":         "hp_restore_on_hit",
    "HP Restoration upon Colossal Weapon Attacks":      "hp_restore_on_hit",
    "HP Restoration upon Spear Attacks":                "hp_restore_on_hit",
    "HP Restoration upon Great Spear Attacks":          "hp_restore_on_hit",
    "HP Restoration upon Halberd Attacks":              "hp_restore_on_hit",
    "HP Restoration upon Reaper Attacks":               "hp_restore_on_hit",
    "HP Restoration upon Whip Attacks":                 "hp_restore_on_hit",
    "HP Restoration upon Fist Attacks":                 "hp_restore_on_hit",
    "HP Restoration upon Claw Attacks":                 "hp_restore_on_hit",
    "HP Restoration upon Bow Attacks":                  "hp_restore_on_hit",
    "HP Restoration upon Thrusting Counterattack":      "hp_restore_on_hit",
    "HP Restoration upon Thrusting Counterattack +1":   "hp_restore_on_hit",

    "FP Restoration upon Dagger Attacks":               "fp_restore_on_hit",
    "FP Restoration upon Thrusting Sword Attacks":      "fp_restore_on_hit",
    "FP Restoration upon Heavy Thrusting Sword Attacks":"fp_restore_on_hit",
    "FP Restoration upon Straight Sword Attacks":       "fp_restore_on_hit",
    "FP Restoration upon Greatsword Attacks":           "fp_restore_on_hit",
    "FP Restoration upon Colossal Sword Attacks":       "fp_restore_on_hit",
    "FP Restoration upon Curved Sword Attacks":         "fp_restore_on_hit",
    "FP Restoration upon Curved Greatsword Attacks":    "fp_restore_on_hit",
    "FP Restoration upon Katana Attacks":               "fp_restore_on_hit",
    "FP Restoration upon Twinblade Attacks":            "fp_restore_on_hit",
    "FP Restoration upon Axe Attacks":                  "fp_restore_on_hit",
    "FP Restoration upon Greataxe Attacks":             "fp_restore_on_hit",
    "FP Restoration upon Hammer Attacks":               "fp_restore_on_hit",
    "FP Restoration upon Flail Attacks":                "fp_restore_on_hit",
    "FP Restoration upon Great Hammer Attacks":         "fp_restore_on_hit",
    "FP Restoration upon Colossal Weapon Attacks":      "fp_restore_on_hit",
    "FP Restoration upon Spear Attacks":                "fp_restore_on_hit",
    "FP Restoration upon Great Spear Attacks":          "fp_restore_on_hit",
    "FP Restoration upon Halberd Attacks":              "fp_restore_on_hit",
    "FP Restoration upon Reaper Attacks":               "fp_restore_on_hit",
    "FP Restoration upon Whip Attacks":                 "fp_restore_on_hit",
    "FP Restoration upon Fist Attacks":                 "fp_restore_on_hit",
    "FP Restoration upon Claw Attacks":                 "fp_restore_on_hit",
    "FP Restoration upon Bow Attacks":                  "fp_restore_on_hit",

    # ── Scaling stats (attribute points) ──────────────────────────────────────
    "Vigor +1": "scaling_stat", "Vigor +2": "scaling_stat", "Vigor +3": "scaling_stat",
    "Mind +1":  "scaling_stat", "Mind +2":  "scaling_stat", "Mind +3":  "scaling_stat",
    "Endurance +1": "scaling_stat", "Endurance +2": "scaling_stat", "Endurance +3": "scaling_stat",
    "Strength +1":  "scaling_stat", "Strength +2":  "scaling_stat", "Strength +3":  "scaling_stat",
    "Dexterity +1": "scaling_stat", "Dexterity +2": "scaling_stat", "Dexterity +3": "scaling_stat",
    "Intelligence +1": "scaling_stat", "Intelligence +2": "scaling_stat", "Intelligence +3": "scaling_stat",
    "Faith +1":  "scaling_stat", "Faith +2":  "scaling_stat", "Faith +3":  "scaling_stat",
    "Arcane +1": "scaling_stat", "Arcane +2": "scaling_stat", "Arcane +3": "scaling_stat",
    "Poise +1":  "scaling_stat", "Poise +2":  "scaling_stat", "Poise +3":  "scaling_stat",

    # ── Status buildup (applying status to enemies) ───────────────────────────
    # No explicit "status buildup" passives in passives.py; nearest are the status
    # conditions on starting armaments and the "Status Ailment Gauges Slowly Increase Attack Power"
    "Status Ailment Gauges Slowly Increase Attack Power": "utility",  # conditional atk boost

    # ── Status resistance (receiving status) ──────────────────────────────────
    "Improved Poison Resistance":    "status_resistance",
    "Improved Poison Resistance +1": "status_resistance",
    "Improved Poison Resistance +2": "status_resistance",
    "Improved Rot Resistance":       "status_resistance",
    "Improved Rot Resistance +1":    "status_resistance",
    "Improved Rot Resistance +2":    "status_resistance",
    "Improved Blood Loss Resistance":    "status_resistance",
    "Improved Blood Loss Resistance +1": "status_resistance",
    "Improved Blood Loss Resistance +2": "status_resistance",
    "Improved Frost Resistance":     "status_resistance",
    "Improved Frost Resistance +1":  "status_resistance",
    "Improved Frost Resistance +2":  "status_resistance",
    "Improved Sleep Resistance":     "status_resistance",
    "Improved Sleep Resistance +1":  "status_resistance",
    "Improved Sleep Resistance +2":  "status_resistance",
    "Improved Madness Resistance":   "status_resistance",
    "Improved Madness Resistance +1":"status_resistance",
    "Improved Madness Resistance +2":"status_resistance",
    "Improved Death Blight Resistance":    "status_resistance",
    "Improved Death Blight Resistance +1": "status_resistance",
    "Improved Death Blight Resistance +2": "status_resistance",

    # ── Damage negation ────────────────────────────────────────────────────────
    "Improved Physical Damage Negation":   "damage_negation",
    "Improved Affinity Damage Negation":   "damage_negation",
    "Magic Damage Negation Up":            "damage_negation",
    "Magic Damage Negation Up +1":         "damage_negation",
    "Magic Damage Negation Up +2":         "damage_negation",
    "Fire Damage Negation Up":             "damage_negation",
    "Fire Damage Negation Up +1":          "damage_negation",
    "Fire Damage Negation Up +2":          "damage_negation",
    "Lightning Damage Negation Up":        "damage_negation",
    "Lightning Damage Negation Up +1":     "damage_negation",
    "Lightning Damage Negation Up +2":     "damage_negation",
    "Holy Damage Negation Up":             "damage_negation",
    "Holy Damage Negation Up +1":          "damage_negation",
    "Holy Damage Negation Up +2":          "damage_negation",
    "Improved Damage Negation at Low HP":  "damage_negation",
    "Improved Poise & Damage Negation When Knocked Back by Damage": "damage_negation",

    # ── Combat modifiers ──────────────────────────────────────────────────────
    "Improved Melee Attack Power":                      "melee_damage",
    "Improved Skill Attack Power":                      "weapon_skill_damage",
    "Improved Initial Standard Attack":                 "melee_damage",
    "Successive Attacks Boost Attack Power":            "melee_damage",
    "Improved Critical Hits":                           "critical_damage",
    "Improved Roar & Breath Attacks":                   "roar_breath",
    "Improved Stance-Breaking when Two-Handing":        "melee_damage",
    "Improved Stance-Breaking when Wielding Two Armaments": "melee_damage",
    "Switching Weapons Boosts Attack Power":            "melee_damage",
    "Boosts Attack Power of Added Affinity Attacks":    "affinity_damage",
    "Taking attacks improves attack power":             "utility",
    "Attack power increased for each evergaol prisoner defeated": "utility",
    "Attack power increased for each Night Invader defeated":     "utility",
    "Improved Guard Counters":                          "guard_counter",
    "Improved Guard Counters +1":                       "guard_counter",
    "Improved Guard Counters +2":                       "guard_counter",
    "Guard counter is given a boost based on current HP": "guard_counter",
    "Physical attack power increases after using grease items":    "physical_damage",
    "Physical attack power increases after using grease items +1": "physical_damage",
    "Physical attack power increases after using grease items +2": "physical_damage",
    "Improved Throwing Pot Damage":                     "utility",
    "Improved Throwing Pot Damage +1":                  "utility",
    "Improved Throwing Knife Damage":                   "utility",
    "Improved Throwing Knife Damage +1":                "utility",
    "Improved Glintstone and Gravity Stone Damage":      "utility",
    "Improved Glintstone and Gravity Stone Damage +1":  "utility",
    "Improved Perfuming Arts":                          "utility",
    "Improved Perfuming Arts +1":                       "utility",

    # ── Character skills ───────────────────────────────────────────────────────
    "Character Skill Cooldown Reduction":   "character_skill",
    "Character Skill Cooldown Reduction +1":"character_skill",
    "Character Skill Cooldown Reduction +2":"character_skill",
    "Character Skill Cooldown Reduction +3":"character_skill",
    "Ultimate Art Auto Charge":             "character_skill",
    "Ultimate Art Auto Charge +1":          "character_skill",
    "Ultimate Art Auto Charge +2":          "character_skill",
    "Ultimate Art Auto Charge +3":          "character_skill",
    "Defeating enemies fills more of the Art gauge":    "character_skill",
    "Defeating enemies fills more of the Art gauge +1": "character_skill",
    "Critical hits fill more of the Art gauge":         "character_skill",
    "Critical hits fill more of the Art gauge +1":      "character_skill",
    "Successful guarding fills more of the Art gauge":  "character_skill",
    "Successful guarding fills more of the Art gauge +1": "character_skill",

    # ── Restoration ────────────────────────────────────────────────────────────
    "Continuous HP Recovery":               "utility",
    "Slowly restore HP for self and nearby allies when HP is low": "utility",
    "HP Recovery From Successful Guarding": "utility",
    "Partial HP Restoration upon Post-Damage Attacks":    "utility",
    "Partial HP Restoration upon Post-Damage Attacks +1": "utility",
    "Partial HP Restoration upon Post-Damage Attacks +2": "utility",
    "HP restored when using medicinal boluses, etc.":     "utility",
    "HP restored when using medicinal boluses, etc. +1":  "utility",
    "Rot in Vicinity Causes Continuous HP Recovery":      "utility",
    "Improved Flask HP Restoration":        "utility",
    "Reduced FP Consumption":               "utility",
    "Continuous FP Recovery":               "utility",
    "FP Restoration upon Successive Attacks": "utility",
    "Madness Continually Recovers FP":      "utility",
    "Stamina Recovery upon Landing Attacks":    "utility",
    "Stamina Recovery upon Landing Attacks +1": "utility",
    "Critical Hit Boosts Stamina Recovery Speed":    "utility",
    "Critical Hit Boosts Stamina Recovery Speed +1": "utility",

    # ── Max resources ──────────────────────────────────────────────────────────
    "Increased Maximum HP":      "utility",
    "Increased Maximum FP":      "utility",
    "Increased Maximum Stamina": "utility",
    "Max FP increased for each Sorcerer's Rise unlocked":             "utility",
    "Runes and Item Discovery increased for each great enemy defeated at a Fort": "utility",
    "Max HP increased for each great enemy defeated at a Great Church": "utility",
    "Max stamina increased for each great enemy defeated at a Great Encampment": "utility",
    "Arcane increased for each great enemy defeated at a Ruin":       "utility",
    "Max FP Up with 3+ Staves Equipped":        "utility",
    "Max FP Up with 3+ Sacred Seals Equipped":  "utility",
    "Max HP Up with 3+ Small Shields Equipped":   "utility",
    "Max HP Up with 3+ Medium Shields Equipped":  "utility",
    "Max HP Up with 3+ Greatshields Equipped":    "utility",

    # ── Actions / conditional ─────────────────────────────────────────────────
    "Critical Hits Earn Runes":                         "utility",
    "Switching Weapons Adds an Affinity Attack":        "affinity_damage",
    "Attacks Inflict Rot when Damage is Taken":         "utility",
    "Draw enemy attention while guarding":              "utility",
    "Gesture \"Crossed Legs\" Builds Up Madness":       "utility",
    "Occasionally Nullify Attacks When Damage Negation is Lowered": "utility",
    "Attack power up when facing poison-afflicted enemy":    "utility",
    "Attack power up when facing poison-afflicted enemy +1": "utility",
    "Attack power up when facing poison-afflicted enemy +2": "utility",
    "Attack power up when facing scarlet rot-afflicted enemy":    "utility",
    "Attack power up when facing scarlet rot-afflicted enemy +1": "utility",
    "Attack power up when facing scarlet rot-afflicted enemy +2": "utility",
    "Attack power up when facing frostbite-afflicted enemy":    "utility",
    "Attack power up when facing frostbite-afflicted enemy +1": "utility",
    "Attack power up when facing frostbite-afflicted enemy +2": "utility",
    "Poison & Rot in Vicinity Increases Attack Power":  "utility",
    "Frostbite in Vicinity Conceals Self":              "utility",
    "Sleep in Vicinity Improves Attack Power":          "utility",
    "Sleep in Vicinity Improves Attack Power +1":       "utility",
    "Madness in Vicinity Improves Attack Power":        "utility",
    "Madness in Vicinity Improves Attack Power +1":     "utility",

    # ── Environment ────────────────────────────────────────────────────────────
    "Treasure marked upon map":                                       "utility",
    "Rune discount for shop purchases while on expedition":           "utility",
    "Huge rune discount for shop purchases while on expedition":      "utility",

    # ── Team ───────────────────────────────────────────────────────────────────
    "Increased rune acquisition for self and allies":                 "utility",
    "Raised stamina recovery for nearby allies, but not for self":    "utility",
    "Flask Also Heals Allies":                                        "utility",
    "Defeating enemies restores HP for allies but not for self":      "utility",
    "Items confer effect to all nearby allies":                       "utility",

    # ── Character-specific (all mapped to character_skill) ────────────────────
    "[Wylder] Art gauge greatly filled when ability is activated":    "character_skill",
    "[Wylder] Standard attacks enhanced with fiery follow-ups when using Character Skill (greatsword only)": "character_skill",
    "[Wylder] +1 additional Character Skill use":                     "character_skill",
    "[Wylder] Art activation spreads fire in area":                   "character_skill",
    "[Wylder] Improved Mind, Reduced Vigor":                          "scaling_stat",
    "[Wylder] Improved Intelligence and Faith, Reduced Strength and Dexterity": "scaling_stat",
    "[Wylder] Character Skill inflicts Blood Loss":                   "character_skill",

    "[Guardian] Successful guards send out shockwaves while ability is active": "character_skill",
    "[Guardian] Increased duration for Character Skill":              "character_skill",
    "[Guardian] Slowly restores nearby allies' HP while Art is active": "character_skill",
    "[Guardian] Creates whirlwind when charging halberd attacks":     "character_skill",
    "[Guardian] Improved Strength and Dexterity, Reduced Vigor":      "scaling_stat",
    "[Guardian] Improved Mind and Faith, Reduced Vigor":              "scaling_stat",
    "[Guardian] Character Skill Boosts Damage Negation of Nearby Allies": "character_skill",

    "[Ironeye] +1 additional Character Skill use":                    "character_skill",
    "[Ironeye] Art Charge Activation Adds Poison Effect":             "character_skill",
    "[Ironeye] Boosts thrusting counterattacks after executing Art":   "character_skill",
    "[Ironeye] Extends duration of weak point":                       "character_skill",
    "[Ironeye] Improved Vigor and Strength, Reduced Dexterity":       "scaling_stat",
    "[Ironeye] Improved Arcane, Reduced Dexterity":                   "scaling_stat",
    "[Ironeye] Character Skill Inflicts Heavy Poison Damage on Poisoned Enemies": "character_skill",

    "[Duchess] Improved Character Skill Attack Power":                "character_skill",
    "[Duchess] Defeating enemies while Art is active ups attack power": "character_skill",
    "[Duchess] Reprise events upon nearby enemies by landing the final blow of a chain attack with dagger": "character_skill",
    "[Duchess] Become difficult to spot and silence footsteps after landing critical from behind": "character_skill",
    "[Duchess] Improved Vigor and Strength, Reduced Mind":            "scaling_stat",
    "[Duchess] Improved Mind and Faith, Reduced Intelligence":        "scaling_stat",
    "[Duchess] Use Character Skill for Brief Invulnerability":        "character_skill",

    "[Raider] Damage taken while using Character Skill improves attack power and stamina": "character_skill",
    "[Raider] Duration of Ultimate Art extended":                     "character_skill",
    "Defeating enemies near Totem Stela restores HP":                 "utility",
    "Improved Poise Near Totem Stela":                                "utility",
    "[Raider] Improved Mind and Intelligence, Reduced Vigor and Endurance": "scaling_stat",
    "[Raider] Improved Arcane, Reduced Vigor":                        "scaling_stat",
    "[Raider] Hit With Character Skill to Reduce Enemy Attack Power": "character_skill",

    "[Revenant] Trigger ghostflame explosion during Ultimate Art activation": "character_skill",
    "[Revenant] Expend own HP to fully heal nearby allies when activating Art": "character_skill",
    "[Revenant] Strengthens family and allies when Ultimate Art is activated": "character_skill",
    "[Revenant] Power up while fighting alongside family":             "character_skill",
    "[Revenant] Improved Vigor and Endurance, Reduced Mind":          "scaling_stat",
    "[Revenant] Improved Strength, Reduced Faith":                    "scaling_stat",
    "[Revenant] Increased Max FP upon Ability Activation":            "utility",

    "[Recluse] Suffer blood loss and increase attack power upon Art activation": "character_skill",
    "[Recluse] Activating Ultimate Art raises Max HP":                "character_skill",
    "[Recluse] Collecting affinity residue activates Terra Magica":   "character_skill",
    "[Recluse] Improved Vigor, Endurance, and Dexterity, Reduced Intelligence and Faith": "scaling_stat",
    "[Recluse] Improved Intelligence and Faith, Reduced Mind":        "scaling_stat",
    "[Recluse] Collect Affinity Residues to Negate Affinity":         "character_skill",

    "[Executor] Character Skill Boosts Attack but Lowers Damage Negation While Attacking": "character_skill",
    "[Executor] While Character Skill is active, unlocking use of cursed sword restores HP": "character_skill",
    "[Executor] Roaring restores HP while Art is active":             "character_skill",
    "[Executor] Improved Vigor and Endurance, Reduced Arcane":        "scaling_stat",
    "[Executor] Improved Dexterity and Arcane, Reduced Vigor":        "scaling_stat",
    "[Executor] Slowly Restore HP upon Ability Activation":           "utility",

    "[Scholar] Prevent slowing of Character Skill progress":          "character_skill",
    "[Scholar] Allies targeted by Character Skill gain boosted attack": "character_skill",
    "[Scholar] Earn runes for each additional specimen acquired with Character Skill": "character_skill",
    "[Scholar] Continuous damage inflicted on targets threaded by Ultimate Art": "character_skill",
    "[Scholar] Improved Mind, Reduced Vigor":                         "scaling_stat",
    "[Scholar] Improved Endurance and Dexterity, Reduced Intelligence and Arcane": "scaling_stat",
    "[Scholar] Reduced FP consumption when using Character Skill on self": "character_skill",

    "[Undertaker] Activating Ultimate Art increases attack power":    "character_skill",
    "[Undertaker] Contact with allies restores their HP while Ultimate Art is activated": "character_skill",
    "[Undertaker] Attack power increased by landing the final blow of a chain attack": "character_skill",
    "[Undertaker] Physical attacks boosted while assist effect from incantation is active for self": "physical_damage",
    "[Undertaker] Improved Dexterity, Reduced Vigor and Faith":       "scaling_stat",
    "[Undertaker] Improved Mind and Faith, Reduced Strength":         "scaling_stat",
    "[Undertaker] Executing Art readies Character Skill":             "character_skill",

    # ── Extended spell duration ────────────────────────────────────────────────
    "Extended Spell Duration":  "utility",

    # ── Damage Negation tiers ──────────────────────────────────────────────────
    "Improved Physical Damage Negation +1":      "damage_negation",
    "Improved Physical Damage Negation +2":      "damage_negation",
    "Improved Affinity Damage Negation +1":      "damage_negation",
    "Improved Affinity Damage Negation +2":      "damage_negation",
    "Improved Magic Damage Negation":            "damage_negation",
    "Improved Magic Damage Negation +1":         "damage_negation",
    "Improved Magic Damage Negation +2":         "damage_negation",
    "Improved Fire Damage Negation":             "damage_negation",
    "Improved Fire Damage Negation +1":          "damage_negation",
    "Improved Fire Damage Negation +2":          "damage_negation",
    "Improved Lightning Damage Negation":        "damage_negation",
    "Improved Lightning Damage Negation +1":     "damage_negation",
    "Improved Lightning Damage Negation +2":     "damage_negation",
    "Improved Holy Damage Negation":             "damage_negation",
    "Improved Holy Damage Negation +1":          "damage_negation",
    "Improved Holy Damage Negation +2":          "damage_negation",

    # ── Starting Items ─────────────────────────────────────────────────────────
    "Starlight Shards in possession at start of expedition":       "starting_item",
    "Fire Pots in possession at start of expedition":              "starting_item",
    "Magic Pots in possession at start of expedition":             "starting_item",
    "Lightning Pots in possession at start of expedition":         "starting_item",
    "Holy Water Pots in possession at start of expedition":        "starting_item",
    "Poisonbone Darts in possession at start of expedition":       "starting_item",
    "Crystal Darts in possession at start of expedition":          "starting_item",
    "Throwing Daggers in possession at start of expedition":       "starting_item",
    "Glintstone Scraps in possession at start of expedition":      "starting_item",
    "Gravity Stone Chunks in possession at start of expedition":   "starting_item",
    "Bewitching Branches in possession at start of expedition":    "starting_item",
    "Fire Grease in possession at start of expedition":            "starting_item",
    "Magic Grease in possession at start of expedition":           "starting_item",
    "Lightning Grease in possession at start of expedition":       "starting_item",
    "Holy Grease in possession at start of expedition":            "starting_item",
    "Shield Grease in possession at start of expedition":          "starting_item",
    "Wraith Calling Bell in possession at start of expedition":    "starting_item",
    "Small Pouch in possession at start of expedition":            "starting_item",
    "Stonesword Key in possession at start of expedition":         "starting_item",
    "Spark Aromatic in possession at start of expedition":         "starting_item",
    "Poison Spraymist in possession at start of expedition":       "starting_item",
    "Ironjar Aromatic in possession at start of expedition":       "starting_item",
    "Uplifting Aromatic in possession at start of expedition":     "starting_item",
    "Acid Spraymist in possession at start of expedition":         "starting_item",
    "Bloodboil Aromatic in possession at start of expedition":     "starting_item",

    # ── Starting Items (Tears) ─────────────────────────────────────────────────
    "Crimson Crystal Tear in possession at start of expedition":        "starting_tear",
    "Crimson Bubbletear in possession at start of expedition":          "starting_tear",
    "Crimsonburst Crystal Tear in possession at start of expedition":   "starting_tear",
    "Crimsonspill Crystal Tear in possession at start of expedition":   "starting_tear",
    "Crimsonwhorl Bubbletear in possession at start of expedition":     "starting_tear",
    "Cerulean Crystal Tear in possession at start of expedition":       "starting_tear",
    "Cerulean Hidden Tear in possession at start of expedition":        "starting_tear",
    "Greenburst Crystal Tear in possession at start of expedition":     "starting_tear",
    "Greenspill Crystal Tear in possession at start of expedition":     "starting_tear",
    "Opaline Bubbletear in possession at start of expedition":          "starting_tear",
    "Opaline Hardtear in possession at start of expedition":            "starting_tear",
    "Leaden Hardtear in possession at start of expedition":             "starting_tear",
    "Speckled Hardtear in possession at start of expedition":           "starting_tear",
    "Windy Crystal Tear in possession at start of expedition":          "starting_tear",
    "Ruptured Crystal Tear in possession at start of expedition":       "starting_tear",
    "Stonebarb Cracked Tear in possession at start of expedition":      "starting_tear",
    "Spiked Cracked Tear in possession at start of expedition":         "starting_tear",
    "Thorny Cracked Tear in possession at start of expedition":         "starting_tear",
    "Twiggy Cracked Tear in possession at start of expedition":         "starting_tear",
    "Flame-Shrouding Cracked Tear in possession at start of expedition":    "starting_tear",
    "Magic-Shrouding Cracked Tear in possession at start of expedition":    "starting_tear",
    "Lightning-Shrouding Cracked Tear in possession at start of expedition":"starting_tear",
    "Holy-Shrouding Cracked Tear in possession at start of expedition":     "starting_tear",

    # ── Starting Armaments (Skills) ────────────────────────────────────────────
    "Changes compatible armament's skill to Endure at start of expedition":             "starting_skill",
    "Changes compatible armament's skill to Quickstep at start of expedition":           "starting_skill",
    "Changes compatible armament's skill to Storm Stomp at start of expedition":         "starting_skill",
    "Changes compatible armament's skill to Determination at start of expedition":       "starting_skill",
    "Changes compatible armament's skill to Glintblade Phalanx at start of expedition":  "starting_skill",
    "Changes compatible armament's skill to Gravitas at start of expedition":            "starting_skill",
    "Changes compatible armament's skill to Flaming Strike at start of expedition":      "starting_skill",
    "Changes compatible armament's skill to Eruption at start of expedition":            "starting_skill",
    "Changes compatible armament's skill to Thunderbolt at start of expedition":         "starting_skill",
    "Changes compatible armament's skill to Lightning Slash at start of expedition":     "starting_skill",
    "Changes compatible armament's skill to Sacred Blade at start of expedition":        "starting_skill",
    "Changes compatible armament's skill to Prayerful Strike at start of expedition":    "starting_skill",
    "Changes compatible armament's skill to Poisonous Mist at start of expedition":      "starting_skill",
    "Changes compatible armament's skill to Poison Moth Flight at start of expedition":  "starting_skill",
    "Changes compatible armament's skill to Blood Blade at start of expedition":         "starting_skill",
    "Changes compatible armament's skill to Seppuku at start of expedition":             "starting_skill",
    "Changes compatible armament's skill to Chilling Mist at start of expedition":       "starting_skill",
    "Changes compatible armament's skill to Hoarfrost Stomp at start of expedition":     "starting_skill",
    "Changes compatible armament's skill to White Shadow's Lure at start of expedition": "starting_skill",
    "Changes compatible armament's skill to Rain of Arrows at start of expedition":      "starting_skill",

    # ── Starting Armaments (Imbues) ────────────────────────────────────────────
    "Starting armament deals magic damage":        "starting_imbue",
    "Starting armament deals fire damage":         "starting_imbue",
    "Starting armament deals lightning damage":    "starting_imbue",
    "Starting armament deals holy damage":         "starting_imbue",
    "Starting armament inflicts poison":           "starting_imbue",
    "Starting armament inflicts blood loss":       "starting_imbue",
    "Starting armament inflicts frost":            "starting_imbue",

    # ── Starting Armaments (Spells) ────────────────────────────────────────────
    "Changes compatible armament's sorcery to Magic Glintblade at start of expedition":     "starting_spell",
    "Changes compatible armament's sorcery to Carian Greatsword at start of expedition":    "starting_spell",
    "Changes compatible armament's sorcery to Night Shard at start of expedition":           "starting_spell",
    "Changes compatible armament's sorcery to Magma Shot at start of expedition":            "starting_spell",
    "Changes compatible armament's sorcery to Briars of Punishment at start of expedition":  "starting_spell",
    "Changes compatible armament's incantation to Wrath of Gold at start of expedition":     "starting_spell",
    "Changes compatible armament's incantation to Lightning Spear at start of expedition":   "starting_spell",
    "Changes compatible armament's incantation to O, Flame! at start of expedition":         "starting_spell",
    "Changes compatible armament's incantation to Beast Claw at start of expedition":         "starting_spell",
    "Changes compatible armament's incantation to Dragonfire at start of expedition":         "starting_spell",
}


# ── Passive → specific affinity element ───────────────────────────────────────
# For passives with category "specific_affinity", maps to the element they boost.

SPECIFIC_AFFINITY_ELEMENT: "dict[str, str]" = {
    "Magic Attack Power Up":      "Magic",
    "Magic Attack Power Up +1":   "Magic",
    "Magic Attack Power Up +2":   "Magic",
    "Magic Attack Power Up +3":   "Magic",
    "Magic Attack Power Up +4":   "Magic",
    "Fire Attack Power Up":       "Fire",
    "Fire Attack Power Up +1":    "Fire",
    "Fire Attack Power Up +2":    "Fire",
    "Fire Attack Power Up +3":    "Fire",
    "Fire Attack Power Up +4":    "Fire",
    "Lightning Attack Power Up":  "Lightning",
    "Lightning Attack Power Up +1":"Lightning",
    "Lightning Attack Power Up +2":"Lightning",
    "Lightning Attack Power Up +3":"Lightning",
    "Lightning Attack Power Up +4":"Lightning",
    "Holy Attack Power Up":       "Holy",
    "Holy Attack Power Up +1":    "Holy",
    "Holy Attack Power Up +2":    "Holy",
    "Holy Attack Power Up +3":    "Holy",
    "Holy Attack Power Up +4":    "Holy",
}


# ── Passive → weapon class (for weapon_class_power and weapon_class_dormant) ───

WEAPON_CLASS_POWER_PASSIVE_TO_CLASS: "dict[str, str]" = {
    v: k for k, v in WEAPON_CLASS_TO_ATTACK_PASSIVE.items()
}


# ── Quick lookup helpers ───────────────────────────────────────────────────────

def weapon_by_name(name: str) -> "dict | None":
    """Return the weapon dict for the given name, or None."""
    for w in WEAPONS:
        if w["name"].lower() == name.lower():
            return w
    return None


def weapons_by_class(weapon_class: str) -> "list[dict]":
    """Return all weapons of the given class."""
    return [w for w in WEAPONS if w["class"] == weapon_class]


def weapons_with_status(status: str) -> "list[dict]":
    """Return all weapons with the given innate status effect."""
    canon = STATUS_EFFECT_ALIASES.get(status, status)
    return [w for w in WEAPONS if w.get("innate_status") == canon]


def weapons_with_affinity(affinity: str) -> "list[dict]":
    """Return all weapons that deal the given affinity damage."""
    return [w for w in WEAPONS if w.get("affinity") == affinity]


# ── Characters (Nightfarers) ───────────────────────────────────────────────────
# Source: Fextralife wiki individual character pages + overview page.
# Stats are Level 1 base values.
#
# Fields:
#   name            — character name
#   description     — brief playstyle summary
#   dlc             — True if requires DLC (Forsaken Hollows)
#   starting_weapons — list of weapon classes they start with
#   starting_spells  — list of spell names (empty list if none)
#   stats           — {vigor, mind, endurance, strength, dexterity, intelligence, faith, arcane}
#   main_scaling    — stats with highest natural scaling (drives best relic synergies)
#   passive         — {name, description}
#   character_skill — {name, description, damage_types, status_effects}
#   ultimate_art    — {name, description, damage_types, status_effects}
#   relic_synergies — list of PASSIVE_CATEGORY tags that synergize strongly with this character
#   notes           — additional synergy/gameplay notes

CHARACTERS: "dict[str, dict]" = {

    "Wylder": {
        "description": "Balanced all-rounder, effective in both speed and attack power.",
        "dlc": False,
        "starting_weapons": ["Greatsword"],
        "starting_spells": [],
        "stats": {
            "vigor": 8, "mind": 4, "endurance": 3,
            "strength": 5, "dexterity": 4,
            "intelligence": 2, "faith": 2, "arcane": 10,
        },
        "main_scaling": ["Strength", "Dexterity"],
        "passive": {
            "name": "Sixth Sense",
            "description": (
                "If Wylder would take lethal damage, he immediately dodges it. "
                "Triggers once per Site of Grace visit or respawn."
            ),
        },
        "character_skill": {
            "name": "Claw Shot",
            "description": (
                "Launch grappling claw to rope foes in or move swiftly by retracting. "
                "Smaller enemies are pulled toward Wylder; larger ones pull him forward."
            ),
            "damage_types": ["Physical"],
            "status_effects": [],
        },
        "ultimate_art": {
            "name": "Onslaught Stake",
            "description": (
                "Launches an iron stake with a great explosion. Chargeable. "
                "Provides invulnerability during wind-up. High stance-breaking."
            ),
            "damage_types": ["Physical"],   # Fire with certain relics
            "status_effects": [],
        },
        "relic_synergies": [
            "physical_damage", "melee_damage", "weapon_class_power",  # Greatsword
            "weapon_skill_damage", "character_skill", "weapon_class_dormant",
        ],
        "notes": (
            "Greatsword passive synergizes directly. Relic '[Wylder] Standard attacks enhanced "
            "with fiery follow-ups when using Character Skill (greatsword only)' adds Fire to Claw Shot. "
            "High Arcane base is unusual for a Str/Dex character — may support status buildup."
        ),
    },

    "Guardian": {
        "description": "Tank with heavy attacks and increased damage resistance.",
        "dlc": False,
        "starting_weapons": ["Halberd", "Greatshield"],
        "starting_spells": [],
        "stats": {
            "vigor": 10, "mind": 2, "endurance": 6,
            "strength": 4, "dexterity": 3,
            "intelligence": 2, "faith": 3, "arcane": 10,
        },
        "main_scaling": ["Strength"],
        "passive": {
            "name": "Steel Guard",
            "description": (
                "Activate by holding Block + pressing Dodge. Multiplies shield Guard Boost by 5×, "
                "greatly reducing stamina damage from blocking. Drains stamina continuously."
            ),
        },
        "character_skill": {
            "name": "Whirlwind",
            "description": (
                "Beat wing to whip up a wind-churning cyclone. 360-degree hit. "
                "Holding the inputs extends the area of effect. Excellent for knockdowns."
            ),
            "damage_types": ["Physical"],
            "status_effects": [],
        },
        "ultimate_art": {
            "name": "Wings of Salvation",
            "description": (
                "Leap skyward and dive back down, creating a protective aura that grants damage "
                "immunity. Near-death allies within range are instantly resurrected. "
                "Uncharged use consumes half the Ultimate Gauge."
            ),
            "damage_types": [],             # Primarily utility / revive
            "status_effects": [],
        },
        "relic_synergies": [
            "physical_damage", "melee_damage", "weapon_class_power",  # Halberd
            "guard_counter", "character_skill", "weapon_class_dormant",
        ],
        "notes": (
            "Halberd and Greatshield passives synergize directly. Guard counter passives "
            "combine with Steel Guard for consistent passive damage. High Vigor base (10) "
            "makes HP-scaling passives more impactful."
        ),
    },

    "Ironeye": {
        "description": "Archer with split-second judgement and pinpoint accuracy.",
        "dlc": False,
        "starting_weapons": ["Bow"],
        "starting_spells": [],
        "stats": {
            "vigor": 6, "mind": 2, "endurance": 4,
            "strength": 4, "dexterity": 8,
            "intelligence": 2, "faith": 2, "arcane": 13,
        },
        "main_scaling": ["Dexterity", "Arcane"],
        "passive": {
            "name": "Eagle Eye",
            "description": "A keenly observant eye discovers more items to obtain from foes.",
        },
        "character_skill": {
            "name": "Marking",
            "description": (
                "Dash with a dagger to create a temporary weak point on an enemy. "
                "Marked enemy takes 10% additional damage from all sources."
            ),
            "damage_types": ["Physical"],   # The dash itself is Physical
            "status_effects": [],
        },
        "ultimate_art": {
            "name": "Single Shot",
            "description": (
                "Shoots a supersonic arrow that surpasses sound and ignores any defense. "
                "Releases a shockwave dealing area damage upon impact."
            ),
            "damage_types": ["Physical", "Pierce"],
            "status_effects": [],
        },
        "relic_synergies": [
            "physical_damage", "weapon_class_power",   # Bow
            "weapon_skill_damage", "critical_damage",
            "weapon_class_dormant", "character_skill",
        ],
        "notes": (
            "Bow class passives synergize directly. High Arcane (13 base) enables strong "
            "innate status buildup with bleed/poison weapons. Marking's +10% damage bonus "
            "amplifies all damage types, so any attack booster is effective."
        ),
    },

    "Duchess": {
        "description": "Nimble fighter who specializes in stealth and prefers daggers.",
        "dlc": False,
        "starting_weapons": ["Dagger"],
        "starting_spells": [],
        "stats": {
            "vigor": 7, "mind": 6, "endurance": 3,
            "strength": 2, "dexterity": 4,
            "intelligence": 4, "faith": 3, "arcane": 11,
        },
        "main_scaling": ["Dexterity", "Intelligence"],
        "passive": {
            "name": "Magnificent Poise",
            "description": (
                "Enables consecutive dodges by pressing dodge twice rapidly, "
                "providing high speed and extended i-frames."
            ),
        },
        "character_skill": {
            "name": "Restage",
            "description": (
                "Reapplies all damage an enemy has taken within the last 3 seconds "
                "at 50% potency (60% with relic). Any ailment buildup also reapplied."
            ),
            "damage_types": [],             # Mirrors whatever damage was dealt
            "status_effects": [],           # Mirrors whatever status was applied
        },
        "ultimate_art": {
            "name": "Finale",
            "description": (
                "Obscure self and surrounding allies to hide from foes for ~10 seconds. "
                "Grants temporary invulnerability frames during activation."
            ),
            "damage_types": [],
            "status_effects": [],
        },
        "relic_synergies": [
            "physical_damage", "weapon_class_power",   # Dagger
            "critical_damage", "weapon_skill_damage",
            "weapon_class_dormant", "character_skill",
        ],
        "notes": (
            "Dagger class passives synergize directly. Restage effectively doubles any "
            "damage dealt in the last 3 seconds — so ANY damage booster becomes 2× effective. "
            "High Intelligence (4, A-rank at level 15) enables sorcery hybrids. "
            "Arcane (11) enables status buildup synergy. "
            "'[Duchess] Reprise events upon nearby enemies by landing final blow of chain '  "
            "attack with dagger' is a specific Duchess relic passive."
        ),
    },

    "Raider": {
        "description": "Powerful sea-farer who favors enormous weapons.",
        "dlc": False,
        "starting_weapons": ["Greataxe"],
        "starting_spells": [],
        "stats": {
            "vigor": 9, "mind": 2, "endurance": 6,
            "strength": 9, "dexterity": 4,
            "intelligence": 1, "faith": 2, "arcane": 10,
        },
        "main_scaling": ["Strength"],
        "passive": {
            "name": "Fighter's Resolve",
            "description": (
                "Taking damage boosts Retaliate potency. Cannot be knocked down "
                "while using Retaliate."
            ),
        },
        "character_skill": {
            "name": "Retaliate",
            "description": (
                "Assume attack stance and pummel vigorously. Reduces incoming damage "
                "during activation. Delivers a powerful punch capable of staggering "
                "or knocking down opponents."
            ),
            "damage_types": ["Physical", "Strike"],
            "status_effects": [],
        },
        "ultimate_art": {
            "name": "Totem Stela",
            "description": (
                "Drive gravekeeper's wedge into earth to summon a giant tombstone. "
                "Creates a protective aura for allies while dealing high AoE damage. "
                "Duration: 20 seconds."
            ),
            "damage_types": ["Physical"],
            "status_effects": [],
        },
        "relic_synergies": [
            "physical_damage", "melee_damage", "weapon_class_power",  # Greataxe / Colossal
            "character_skill", "weapon_class_dormant",
        ],
        "notes": (
            "Highest base Strength (9) and Vigor (9) in the game. Greataxe and Colossal Weapon "
            "passives synergize directly. Totem Stela relics "
            "('Defeating enemies near Totem Stela restores HP', 'Improved Poise Near Totem Stela') "
            "are Raider-specific. STR-scaling weapons with high poise damage are optimal."
        ),
    },

    "Recluse": {
        "description": "Witch of the deep forest who deftly wields ancient sorceries.",
        "dlc": False,
        "starting_weapons": ["Glintstone Staff"],
        "starting_spells": ["Glintstone Pebble", "Glintstone Arc"],
        "stats": {
            "vigor": 6, "mind": 8, "endurance": 3,       # TODO: verify exact level 1 values
            "strength": 1, "dexterity": 2,
            "intelligence": 8, "faith": 4, "arcane": 4,   # S-scaling at higher levels
        },
        "main_scaling": ["Intelligence", "Faith"],
        "passive": {
            "name": "Elemental Defense",
            "description": (
                "Discover affinity residues that can be collected to replenish FP. "
                "Residues appear near elemental attacks and effects."
            ),
        },
        "character_skill": {
            "name": "Magic Cocktail",
            "description": (
                "Collect affinity residues of targets to fire an affinity-exploiting "
                "magic cocktail. Every 4th cast triggers a more powerful effect based "
                "on collected elements."
            ),
            "damage_types": ["Magic"],      # Base type; varies by collected affinity
            "status_effects": [],
        },
        "ultimate_art": {
            "name": "Soulblood Song",
            "description": (
                "Unleash forbidden blood chant to brand nearby foes with blood sigils. "
                "Marks enemies for 16 seconds. Allies regain HP and FP when attacking marked targets."
            ),
            "damage_types": [],             # Utility — HP/FP drain effect, no direct damage
            "status_effects": ["Blood Loss"],
        },
        "relic_synergies": [
            "sorcery_any", "sorcery_school", "affinity_damage", "specific_affinity",
            "incantation_any",              # Faith S-scaling → incantation synergy too
            "fp_resource", "character_skill",
        ],
        "notes": (
            "Primary sorcery caster. Intelligence and Faith both reach S-scaling — supports "
            "both sorcery and incantation builds. Sorcery passives (Improved Sorceries, "
            "school-specific) synergize directly. Magic Cocktail scales with collected affinity "
            "so Improved Affinity Attack Power is effective. "
            "'[Recluse] Collecting affinity residue activates Terra Magica' is a specific passive."
        ),
    },

    "Executor": {
        "description": "Katana-wielding, parry-focused fighter excelling in one-on-one combat.",
        "dlc": False,
        "starting_weapons": ["Katana"],
        "starting_spells": [],
        "stats": {
            "vigor": 7, "mind": 4, "endurance": 3,
            "strength": 3, "dexterity": 8,
            "intelligence": 1, "faith": 1, "arcane": 13,
        },
        "main_scaling": ["Dexterity", "Arcane"],
        "passive": {
            "name": "Tenacity",
            "description": (
                "Grants ~20% attack power boost and faster stamina recovery lasting "
                "~20 seconds after recovering from a status ailment."
            ),
        },
        "character_skill": {
            "name": "Suncatcher",
            "description": (
                "Deploy a cursed sword that can deflect enemy attacks. No cooldown. "
                "Generous parry window with minimal stamina cost. Mirrors Sekiro-style parry."
            ),
            "damage_types": ["Physical"],
            "status_effects": [],
        },
        "ultimate_art": {
            "name": "Aspects of the Crucible: Beast",
            "description": (
                "Transform into a primordial beast form enabling four unique attacks. "
                "Partial gauge preservation allows ~15 seconds of active transformation."
            ),
            "damage_types": ["Physical"],
            "status_effects": [],
        },
        "relic_synergies": [
            "physical_damage", "melee_damage", "weapon_class_power",  # Katana
            "critical_damage", "character_skill", "weapon_class_dormant",
        ],
        "notes": (
            "Highest base Dexterity (8) + Arcane (13). Katana class passives synergize. "
            "Arcane (13 base) drives strong innate Blood Loss buildup — Katanas with hemorrhage "
            "are natural. Tenacity passive means status-inflicting weapons like bleed/frost "
            "weapons have added value by triggering the power buff more often. "
            "Executor is the only character that can also use the cursed sword mechanic."
        ),
    },

    "Revenant": {
        "description": "Summoner who can conjure phantoms and coordinate attacks with them.",
        "dlc": False,
        "starting_weapons": ["Claw"],          # Cursed Claws = Claw class
        "starting_spells": ["Rejection", "Heal"],
        "stats": {
            "vigor": 6, "mind": 8, "endurance": 3,
            "strength": 3, "dexterity": 3,
            "intelligence": 4, "faith": 8, "arcane": 4,
        },
        "main_scaling": ["Faith", "Arcane"],
        "passive": {
            "name": "Necromancy",
            "description": (
                "Raise enemy ghosts to fight as allies. When defeated enemies are slain, "
                "they reanimate as temporary phantoms lasting ~1 minute."
            ),
        },
        "character_skill": {
            "name": "Summon Spirit",
            "description": (
                "Summon one of three family members: Helen (agile rapier), "
                "Frederick (tanky hammer), or Sebastian (stationary skeleton with AoE). "
                "Each brings different combat roles."
            ),
            "damage_types": ["Physical"],   # Varies by summon
            "status_effects": [],
        },
        "ultimate_art": {
            "name": "Immortal March",
            "description": (
                "Release vengeful ire to make self and nearby allies immortal for 15 seconds. "
                "Damage that would be lethal leaves characters at 1 HP. "
                "Revives downed allies within range."
            ),
            "damage_types": [],             # Utility
            "status_effects": [],
        },
        "relic_synergies": [
            "incantation_any", "incantation_school",  # Faith S-scaling
            "physical_damage", "weapon_class_power",  # Claw class
            "character_skill", "fp_resource",
        ],
        "notes": (
            "Faith S-scaling enables incantation hybrid builds. Starts with a Sacred Seal "
            "in addition to Claws — incantation passives are immediately useful. "
            "Claw class passives synergize with the starting weapon. "
            "Support-focused; Immortal March makes any ally-benefiting passive more impactful."
        ),
    },

    "Scholar": {
        "description": "Academic gaining advantages through battlefield observation.",
        "dlc": True,
        "starting_weapons": ["Thrusting Sword"],
        "starting_spells": [],
        "stats": {
            "vigor": 7, "mind": 4, "endurance": 3,
            "strength": 1, "dexterity": 2,
            "intelligence": 4, "faith": 2, "arcane": 50,   # Arcane S-scaling (50 base at level 1)
        },
        "main_scaling": ["Arcane"],
        "passive": {
            "name": "Bagcraft",
            "description": (
                "Store additional resources. Level up the power or effect of consumable "
                "items by using them — each consumable can be upgraded twice per expedition."
            ),
        },
        "character_skill": {
            "name": "Analyze",
            "description": (
                "Study enemies or allies to fill a gauge. Longer observation stacks "
                "debuffs on enemies or buffs on allies."
            ),
            "damage_types": [],             # No direct damage
            "status_effects": [],
        },
        "ultimate_art": {
            "name": "Communion",
            "description": (
                "Damage is shared by linked enemies and can heal threaded allies. "
                "Links nearby targets, distributing 20% damage between connected enemies "
                "while pooling healing effects for allies."
            ),
            "damage_types": [],             # Utility / damage redirection
            "status_effects": [],
        },
        "relic_synergies": [
            "physical_damage", "weapon_class_power",   # Thrusting Sword
            "character_skill", "weapon_skill_damage",
        ],
        "notes": (
            "Arcane 50 base at level 1 — extraordinary base stat. This drives extremely high "
            "natural innate status buildup (Bleed, Poison, Frostbite) on compatible weapons. "
            "Thrusting Sword class passives synergize with starting weapon. "
            "Arcane +1/+2/+3 relics compound the already-massive Arcane base. "
            "Item-enhancement passives (grease, consumables) synergize with Bagcraft."
        ),
    },

    "Undertaker": {
        "description": "Abbess mandated to slay the Nightlord, boasting strength and faith.",
        "dlc": True,
        "starting_weapons": ["Hammer"],
        "starting_spells": [],
        "stats": {
            "vigor": 7, "mind": 4, "endurance": 3,
            "strength": 7, "dexterity": 2,
            "intelligence": 1, "faith": 7, "arcane": 4,
        },
        "main_scaling": ["Strength", "Faith"],
        "passive": {
            "name": "Confluence",
            "description": (
                "When an ally uses their ultimate art, Undertaker can activate her own "
                "ultimate art for free regardless of gauge status."
            ),
        },
        "character_skill": {
            "name": "Trance",
            "description": (
                "Bloodletting triggers the power of the loathsome hex. Increases movement "
                "speed, poise, and defense. With full gauge, grants auto-dodge and "
                "significantly boosts attack power for 15 seconds."
            ),
            "damage_types": [],             # Buff, no direct damage
            "status_effects": ["Blood Loss"],   # Self-inflicted as activation cost
        },
        "ultimate_art": {
            "name": "Loathsome Hex",
            "description": (
                "Pull out uncanny bone from body, speed toward target, and strike. "
                "Long-range ability. Can be used mid-air. High damage."
            ),
            "damage_types": ["Physical"],
            "status_effects": [],
        },
        "relic_synergies": [
            "physical_damage", "melee_damage", "weapon_class_power",   # Hammer
            "incantation_any",              # Faith A-scaling
            "character_skill", "weapon_class_dormant",
        ],
        "notes": (
            "Str A + Fai A base scaling — supports physical melee AND incantation hybrids. "
            "Hammer class passives synergize with starting weapon. "
            "Trance uses self-inflicted Blood Loss as a resource, so blood-buildup resistance "
            "and status interaction passives have unique relevance. "
            "'[Undertaker] Physical attacks boosted while assist effect from incantation is "
            "active for self' — incantations that buff Undertaker create a physical damage loop."
        ),
    },
}


# ── Character → best relic passive synergies (summary) ────────────────────────
# Quick lookup: which PASSIVE_CATEGORY tags matter for each character.
# Used by smart_rules.py to score relics for unrequested recommendations.

CHARACTER_SYNERGY_CATEGORIES: "dict[str, list[str]]" = {
    char: data["relic_synergies"]
    for char, data in CHARACTERS.items()
}


def character_by_name(name: str) -> "dict | None":
    """Return character dict (case-insensitive), or None."""
    for k, v in CHARACTERS.items():
        if k.lower() == name.lower():
            return v
    return None
