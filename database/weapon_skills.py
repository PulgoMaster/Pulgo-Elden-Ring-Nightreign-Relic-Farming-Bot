# Nightreign Weapon Skills (Ashes of War) Database
# Mined from SwordArtsParam.csv + SwordArtsTableParam.csv (Smithbox exports)
# Data mining completed: 2026-03-25
#
# SwordArtsParam: 155 named skills (+ ID 9999 placeholder for skill reroll).
# SwordArtsTableParam: 11,896 rows — per-weapon-type rollable skill pools.
#
# Key structural notes:
# - FP costs vary per input: useMagicPoint_L1, _L2, _R1, _R2 (-1 = not applicable).
# - Skills [Specific] (IDs 1000–1198) are weapon-unique and cannot be rolled freely.
# - isStartSkill_<Hero> flags (10 columns) are Nightreign-exclusive additions.
# - defaultWepAttr: 5=Fire, 6=Lightning, 7=Holy, 8=Magic, 9=Frost, 10=Poison, 11=Blood.
# - chanceWeight in pool tables: 100=normal, 50=half-weight, 0=disabled.
# - ID 9999 "??? (Skill Reroll Standin)" is a Nightreign-only placeholder.
#
# SwordArtsTableParam pool ID structure (high-ID tables ≥ 10,000,000):
#   [WeaponCategoryBase] + [AffinityOffset]
#   +0=Full pool, +50=Standard-only, +100=Elemental-only,
#   +500=Fire, +600=Lightning, +700=Holy, +800=Magic, +900=Frost,
#   +1000=Poison, +1100=Blood, +1200=Shadow (Assassin/White Shadow only)


# =============================================================================
# SKILLS — id → {name, category, fp_r1, fp_r2, fp_l1, attr, start_heroes}
# =============================================================================
# fp values: -1 = not applicable for that input
# attr: weapon attribute granted (None = Standard, physical)
# start_heroes: set of heroes for whom this is a starting skill

SKILLS: dict[int, dict] = {
    # ── Standard melee ──────────────────────────────────────────────────
    1:   {"name": "No Skill",           "cat": "Standard", "fp_r1":  0, "fp_r2":  0, "fp_l1": -1, "attr": None},
    10:  {"name": "No Skill",           "cat": "Standard", "fp_r1": -1, "fp_r2": -1, "fp_l1": -1, "attr": None,   "note": "Two-hand variant"},
    100: {"name": "Lion's Claw",        "cat": "Standard", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    101: {"name": "Impaling Thrust",    "cat": "Standard", "fp_r1":  0, "fp_r2":  9, "fp_l1": -1, "attr": None},
    102: {"name": "Piercing Fang",      "cat": "Standard", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None},
    103: {"name": "Spinning Slash",     "cat": "Standard", "fp_r1":  0, "fp_r2":  6, "fp_l1": -1, "attr": None,   "fp_hold": 12},
    105: {"name": "Charge Forth",       "cat": "Standard", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None},
    106: {"name": "Stamp (Upward Cut)", "cat": "Standard", "fp_r1":  0, "fp_r2":  5, "fp_l1": -1, "attr": None,   "fp_hold":  8},
    107: {"name": "Stamp (Sweep)",      "cat": "Standard", "fp_r1":  0, "fp_r2":  5, "fp_l1": -1, "attr": None,   "fp_hold":  8},
    109: {"name": "Repeating Thrust",   "cat": "Standard", "fp_r1":  0, "fp_r2":  7, "fp_l1": -1, "attr": None},
    110: {"name": "Wild Strikes",       "cat": "Standard", "fp_r1":  2, "fp_r2": 15, "fp_l1": -1, "attr": None},
    111: {"name": "Spinning Strikes",   "cat": "Standard", "fp_r1":  2, "fp_r2": 15, "fp_l1": -1, "attr": None},
    112: {"name": "Double Slash",       "cat": "Standard", "fp_r1":  6, "fp_r2": -1, "fp_l1": -1, "attr": None,   "fp_hold":  3},
    114: {"name": "Unsheathe",          "cat": "Standard", "fp_r1": 10, "fp_r2": 15, "fp_l1": -1, "attr": None},
    115: {"name": "Square Off",         "cat": "Standard", "fp_r1":  6, "fp_r2":  8, "fp_l1": -1, "attr": None},
    116: {"name": "Giant Hunt",         "cat": "Standard", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None},
    117: {"name": "Torch Attack",       "cat": "Standard", "fp_r1":  0, "fp_r2":  0, "fp_l1": -1, "attr": None,   "note": "Torch only"},
    122: {"name": "Storm Assault",      "cat": "Standard", "fp_r1":  0, "fp_r2": 22, "fp_l1": -1, "attr": None},
    123: {"name": "Stormcaller",        "cat": "Standard", "fp_r1":  0, "fp_r2":  9, "fp_l1": -1, "attr": None,   "fp_hold": 11},
    124: {"name": "Sword Dance",        "cat": "Standard", "fp_r1":  6, "fp_r2": -1, "fp_l1": -1, "attr": None,   "fp_hold":  6},
    125: {"name": "Spinning Chain",     "cat": "Standard", "fp_r1":  8, "fp_r2": 10, "fp_l1": -1, "attr": None},
    210: {"name": "Storm Blade",        "cat": "Standard", "fp_r1": 10, "fp_r2": -1, "fp_l1": -1, "attr": None,   "fp_hold":  6},
    212: {"name": "Earthshaker",        "cat": "Standard", "fp_r1": 10, "fp_r2": -1, "fp_l1": -1, "attr": None,   "fp_hold":  5},
    220: {"name": "Vacuum Slice",       "cat": "Standard", "fp_r1":  0, "fp_r2": 14, "fp_l1": -1, "attr": None},
    225: {"name": "Phantom Slash",      "cat": "Standard", "fp_r1":  8, "fp_r2": -1, "fp_l1": -1, "attr": None,   "fp_hold":  8},
    226: {"name": "Spectral Lance",     "cat": "Standard", "fp_r1":  0, "fp_r2":  9, "fp_l1": -1, "attr": None},

    # ── Buffs / utility ─────────────────────────────────────────────────
    600: {"name": "Determination",           "cat": "Standard", "fp_r1":  0, "fp_r2": 10, "fp_l1": -1, "attr": None},
    601: {"name": "Royal Knight's Resolve",  "cat": "Standard", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},
    602: {"name": "Assassin's Gambit",       "cat": "Standard", "fp_r1":  0, "fp_r2":  5, "fp_l1": -1, "attr": None},
    603: {"name": "Golden Vow",              "cat": "Holy",     "fp_r1":  0, "fp_r2": 40, "fp_l1": -1, "attr": 7},
    604: {"name": "Sacred Order",            "cat": "Holy",     "fp_r1":  0, "fp_r2": 18, "fp_l1": -1, "attr": 7},
    605: {"name": "Shared Order",            "cat": "Holy",     "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": 7},
    606: {"name": "Seppuku",                 "cat": "Blood",    "fp_r1":  0, "fp_r2":  4, "fp_l1": -1, "attr": 11},
    607: {"name": "Cragblade",               "cat": "Standard", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None},
    700: {"name": "Endure",                  "cat": "Standard", "fp_r1":  0, "fp_r2":  9, "fp_l1": -1, "attr": None},
    701: {"name": "Vow of the Indomitable",  "cat": "Holy",     "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": 7},
    702: {"name": "Holy Ground",             "cat": "Holy",     "fp_r1":  0, "fp_r2": 30, "fp_l1": -1, "attr": 7},
    800: {"name": "Quickstep",               "cat": "Standard", "fp_r1":  0, "fp_r2":  3, "fp_l1": -1, "attr": None},
    801: {"name": "Bloodhound's Step",       "cat": "Standard", "fp_r1":  0, "fp_r2":  5, "fp_l1": -1, "attr": None},
    802: {"name": "Raptor of the Mists",     "cat": "Standard", "fp_r1":  0, "fp_r2":  6, "fp_l1": -1, "attr": None},
    850: {"name": "White Shadow's Lure",     "cat": "Standard", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},

    # ── Roars ───────────────────────────────────────────────────────────
    650: {"name": "Barbaric Roar",   "cat": "Standard", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None},
    651: {"name": "War Cry",         "cat": "Standard", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None},
    652: {"name": "Beast's Roar",    "cat": "Standard", "fp_r1":  0, "fp_r2": 10, "fp_l1": -1, "attr": None},
    653: {"name": "Troll's Roar",    "cat": "Standard", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None,   "fp_hold":  6},
    654: {"name": "Braggart's Roar", "cat": "Standard", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None},

    # ── Fire ────────────────────────────────────────────────────────────
    113: {"name": "Prelate's Charge",       "cat": "Fire", "fp_r1":  0, "fp_r2":  7, "fp_l1": -1, "attr": 5, "fp_hold": 7},
    207: {"name": "Eruption",               "cat": "Fire", "fp_r1":  0, "fp_r2": 14, "fp_l1": -1, "attr": 5},
    214: {"name": "Flaming Strike",         "cat": "Fire", "fp_r1":  0, "fp_r2":  4, "fp_l1": -1, "attr": 5, "fp_hold": 10},
    221: {"name": "Black Flame Tornado",    "cat": "Fire", "fp_r1":  0, "fp_r2": 30, "fp_l1": -1, "attr": 5},
    505: {"name": "Flame of the Redmanes",  "cat": "Fire", "fp_r1":  0, "fp_r2": 14, "fp_l1": -1, "attr": 5},

    # ── Lightning ───────────────────────────────────────────────────────
    216: {"name": "Thunderbolt",    "cat": "Lightning", "fp_r1":  0, "fp_r2": 10, "fp_l1": -1, "attr": 6, "fp_hold": 10},
    217: {"name": "Lightning Slash","cat": "Lightning", "fp_r1":  0, "fp_r2": 10, "fp_l1": -1, "attr": 6},
    504: {"name": "Lightning Ram",  "cat": "Lightning", "fp_r1":  0, "fp_r2":  5, "fp_l1": -1, "attr": 6, "fp_hold":  5},

    # ── Holy ────────────────────────────────────────────────────────────
    201: {"name": "Sacred Blade",       "cat": "Holy", "fp_r1":  0, "fp_r2": 19, "fp_l1": -1, "attr": 7},
    208: {"name": "Prayerful Strike",   "cat": "Holy", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": 7},
    213: {"name": "Golden Land",        "cat": "Holy", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": 7, "fp_hold": 5},
    222: {"name": "Sacred Ring of Light","cat": "Holy", "fp_r1":  0, "fp_r2":  9, "fp_l1": -1, "attr": 7, "fp_hold": 9},
    307: {"name": "Golden Parry",       "cat": "Holy", "fp_r1":  0, "fp_r2":  4, "fp_l1": -1, "attr": 7},
    507: {"name": "Golden Slam",        "cat": "Holy", "fp_r1":  0, "fp_r2": 22, "fp_l1": -1, "attr": 7},

    # ── Magic ───────────────────────────────────────────────────────────
    118: {"name": "Loretta's Slash",        "cat": "Magic", "fp_r1":  0, "fp_r2": 14, "fp_l1": -1, "attr": 8},
    120: {"name": "Spinning Weapon",        "cat": "Magic", "fp_r1":  0, "fp_r2": 12, "fp_l1": -1, "attr": 8},
    200: {"name": "Glintblade Phalanx",     "cat": "Magic", "fp_r1":  0, "fp_r2": 10, "fp_l1": -1, "attr": 8, "fp_hold": 4},
    203: {"name": "Glintstone Pebble",      "cat": "Magic", "fp_r1":  0, "fp_r2":  8, "fp_l1": -1, "attr": 8, "fp_hold": 4},
    209: {"name": "Gravitas",               "cat": "Magic", "fp_r1":  0, "fp_r2": 13, "fp_l1": -1, "attr": 8},
    218: {"name": "Carian Grandeur",        "cat": "Magic", "fp_r1":  0, "fp_r2": 26, "fp_l1": -1, "attr": 8},
    219: {"name": "Carian Greatsword",      "cat": "Magic", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": 8},
    305: {"name": "Carian Retaliation",     "cat": "Magic", "fp_r1":  0, "fp_r2":  8, "fp_l1": -1, "attr": 8},
    309: {"name": "Thops's Barrier",        "cat": "Magic", "fp_r1":  0, "fp_r2":  0, "fp_l1": -1, "attr": 8},
    508: {"name": "Waves of Darkness",      "cat": "Magic", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": 8, "fp_hold": 5},

    # ── Frost ───────────────────────────────────────────────────────────
    202: {"name": "Ice Spear",      "cat": "Frost", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": 9},
    227: {"name": "Chilling Mist",  "cat": "Frost", "fp_r1":  0, "fp_r2": 14, "fp_l1": -1, "attr": 9},
    501: {"name": "Hoarfrost Stomp","cat": "Frost", "fp_r1":  0, "fp_r2": 10, "fp_l1": -1, "attr": 9},

    # ── Poison ──────────────────────────────────────────────────────────
    119: {"name": "Poison Moth Flight","cat": "Poison", "fp_r1": 0, "fp_r2": 7,  "fp_l1": -1, "attr": 10},
    228: {"name": "Poisonous Mist",    "cat": "Poison", "fp_r1": 0, "fp_r2": 14, "fp_l1": -1, "attr": 10},

    # ── Blood ───────────────────────────────────────────────────────────
    108: {"name": "Blood Tax",          "cat": "Blood", "fp_r1":  0, "fp_r2": 14, "fp_l1": -1, "attr": 11},
    204: {"name": "Bloody Slash",       "cat": "Blood", "fp_r1":  0, "fp_r2":  6, "fp_l1": -1, "attr": 11},
    205: {"name": "Lifesteal Fist",     "cat": "Blood", "fp_r1":  0, "fp_r2": 14, "fp_l1": -1, "attr": 11},
    224: {"name": "Blood Blade",        "cat": "Blood", "fp_r1":  0, "fp_r2":  3, "fp_l1": -1, "attr": 11, "fp_hold": 3},

    # ── Shield ──────────────────────────────────────────────────────────
    300: {"name": "Shield Bash",        "cat": "Shield", "fp_r1":  0, "fp_r2": 10, "fp_l1": -1, "attr": None},
    301: {"name": "Barricade Shield",   "cat": "Shield", "fp_r1":  0, "fp_r2": 12, "fp_l1": -1, "attr": None},
    302: {"name": "Parry",              "cat": "Shield", "fp_r1":  0, "fp_r2":  0, "fp_l1": -1, "attr": None},
    303: {"name": "Buckler Parry",      "cat": "Shield", "fp_r1":  0, "fp_r2":  0, "fp_l1": -1, "attr": None},
    306: {"name": "Storm Wall",         "cat": "Shield", "fp_r1":  0, "fp_r2":  3, "fp_l1": -1, "attr": None},
    308: {"name": "Shield Crash",       "cat": "Shield", "fp_r1":  0, "fp_r2": 12, "fp_l1": -1, "attr": None},

    # ── Bow ─────────────────────────────────────────────────────────────
    400: {"name": "Through and Through","cat": "Bow", "fp_r1":  9, "fp_r2":  9, "fp_l1": -1, "attr": None},
    401: {"name": "Barrage",            "cat": "Bow", "fp_r1":  2, "fp_r2":  2, "fp_l1": -1, "attr": None},
    402: {"name": "Mighty Shot",        "cat": "Bow", "fp_r1":  6, "fp_r2":  6, "fp_l1": -1, "attr": None},
    404: {"name": "Enchanted Shot",     "cat": "Bow", "fp_r1":  8, "fp_r2":  8, "fp_l1": -1, "attr": None},
    405: {"name": "Sky Shot",           "cat": "Bow", "fp_r1":  3, "fp_r2":  3, "fp_l1": -1, "attr": None},
    406: {"name": "Rain of Arrows",     "cat": "Bow", "fp_r1": 20, "fp_r2": 20, "fp_l1": -1, "attr": None},

    # ── Stomp / Ground ──────────────────────────────────────────────────
    502: {"name": "Storm Stomp",                "cat": "Standard", "fp_r1":  0, "fp_r2":  6, "fp_l1": -1, "attr": None},
    503: {"name": "Kick",                       "cat": "Standard", "fp_r1":  0, "fp_r2":  0, "fp_l1": -1, "attr": None},
    506: {"name": "Ground Slam",                "cat": "Standard", "fp_r1":  0, "fp_r2": 14, "fp_l1": -1, "attr": None},
    509: {"name": "Hoarah Loux's Earthshaker",  "cat": "Standard", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None, "fp_hold": 16},

    # ── Weapon-Unique [Specific] ─────────────────────────────────────────
    1000: {"name": "Surge of Faith",          "cat": "Specific", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},
    1001: {"name": "Flame Spit",              "cat": "Specific", "fp_r1":  0, "fp_r2": 28, "fp_l1": -1, "attr": None},
    1002: {"name": "Tongues of Fire",         "cat": "Specific", "fp_r1":  0, "fp_r2":  5, "fp_l1": -1, "attr": None},
    1003: {"name": "Oracular Bubble",         "cat": "Specific", "fp_r1":  0, "fp_r2":  6, "fp_l1": -1, "attr": None},
    1004: {"name": "Bubble Shower",           "cat": "Specific", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None},
    1005: {"name": "Great Oracular Bubble",   "cat": "Specific", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None},
    1006: {"name": "Sea of Magma",            "cat": "Specific", "fp_r1":  0, "fp_r2":  5, "fp_l1": -1, "attr": None},
    1007: {"name": "Viper Bite",              "cat": "Specific", "fp_r1":  0, "fp_r2":  8, "fp_l1": -1, "attr": None},
    1008: {"name": "Moonlight Greatsword",    "cat": "Specific", "fp_r1":  0, "fp_r2": 32, "fp_l1": -1, "attr": None},
    1009: {"name": "Siluria's Woe",           "cat": "Specific", "fp_r1":  0, "fp_r2": 25, "fp_l1": -1, "attr": None},
    1010: {"name": "Rallying Standard",       "cat": "Specific", "fp_r1":  0, "fp_r2": 30, "fp_l1": -1, "attr": None},
    1011: {"name": "Bear Witness!",           "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1012: {"name": "Eochaid's Dancing Blade", "cat": "Specific", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},
    1013: {"name": "Soul Stifler",            "cat": "Specific", "fp_r1":  0, "fp_r2": 12, "fp_l1": -1, "attr": None},
    1014: {"name": "Taker's Flames",          "cat": "Specific", "fp_r1":  0, "fp_r2": 30, "fp_l1": -1, "attr": None},
    1015: {"name": "Shriek of Milos",         "cat": "Specific", "fp_r1":  0, "fp_r2": 30, "fp_l1": -1, "attr": None},
    1016: {"name": "Reduvia Blood Blade",     "cat": "Specific", "fp_r1":  0, "fp_r2":  6, "fp_l1": -1, "attr": None},
    1017: {"name": "Glintstone Dart",         "cat": "Specific", "fp_r1":  0, "fp_r2": 10, "fp_l1": -1, "attr": None},
    1018: {"name": "Flowing Form",            "cat": "Specific", "fp_r1":  0, "fp_r2":  9, "fp_l1": -1, "attr": None},
    1019: {"name": "Night-and-Flame Stance",  "cat": "Specific", "fp_r1": 26, "fp_r2": 32, "fp_l1": -1, "attr": None},
    1020: {"name": "Wave of Gold",            "cat": "Specific", "fp_r1":  0, "fp_r2": 42, "fp_l1": -1, "attr": None},
    1021: {"name": "Ruinous Ghostflame",      "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1022: {"name": "Establish Order",         "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1023: {"name": "Mists of Slumber",        "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1024: {"name": "Spearcall Ritual",        "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1025: {"name": "Wolf's Assault",          "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1026: {"name": "Thundercloud Form",       "cat": "Specific", "fp_r1":  0, "fp_r2": 28, "fp_l1": -1, "attr": None},
    1027: {"name": "Cursed-Blood Slice",      "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1028: {"name": "Waterfowl Dance",         "cat": "Specific", "fp_r1":  0, "fp_r2": 12, "fp_l1": -1, "attr": None},
    1029: {"name": "Gold Breaker",            "cat": "Specific", "fp_r1":  0, "fp_r2": 26, "fp_l1": -1, "attr": None},
    1030: {"name": "I Command Thee, Kneel!",  "cat": "Specific", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},
    1031: {"name": "Regal Roar",              "cat": "Specific", "fp_r1":  0, "fp_r2": 25, "fp_l1": -1, "attr": None},
    1032: {"name": "Starcaller Cry",          "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1033: {"name": "Wave of Destruction",     "cat": "Specific", "fp_r1":  0, "fp_r2": 25, "fp_l1": -1, "attr": None},
    1034: {"name": "Bloodboon Ritual",        "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1035: {"name": "Flowing Form (Hammer)",   "cat": "Specific", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None},
    1036: {"name": "Blade of Death",          "cat": "Specific", "fp_r1":  0, "fp_r2": 25, "fp_l1": -1, "attr": None},
    1037: {"name": "Blade of Gold",           "cat": "Specific", "fp_r1":  0, "fp_r2": 17, "fp_l1": -1, "attr": None},
    1038: {"name": "Destined Death",          "cat": "Specific", "fp_r1":  0, "fp_r2": 40, "fp_l1": -1, "attr": None},
    1039: {"name": "Spinning Wheel",          "cat": "Specific", "fp_r1":  0, "fp_r2":  3, "fp_l1": -1, "attr": None},
    1040: {"name": "Alabaster Lords' Pull",   "cat": "Specific", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},
    1041: {"name": "Onyx Lords' Repulsion",   "cat": "Specific", "fp_r1":  0, "fp_r2": 27, "fp_l1": -1, "attr": None},
    1042: {"name": "Oath of Vengeance",       "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1043: {"name": "Ice Lightning Sword",     "cat": "Specific", "fp_r1":  0, "fp_r2": 25, "fp_l1": -1, "attr": None},
    1044: {"name": "Regal Beastclaw",         "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1045: {"name": "Flame Dance",             "cat": "Specific", "fp_r1":  0, "fp_r2": 25, "fp_l1": -1, "attr": None},
    1046: {"name": "Claw Flick",              "cat": "Specific", "fp_r1":  0, "fp_r2": 14, "fp_l1": -1, "attr": None},
    1047: {"name": "Nebula (Bastard's Stars)","cat": "Specific", "fp_r1":  0, "fp_r2": 25, "fp_l1": -1, "attr": None},
    1048: {"name": "Ghostflame Ignition",     "cat": "Specific", "fp_r1": 10, "fp_r2": 10, "fp_l1": 15, "attr": None},
    1049: {"name": "Ancient Lightning Spear", "cat": "Specific", "fp_r1":  0, "fp_r2": 24, "fp_l1": -1, "attr": None},
    1050: {"name": "Frenzyflame Thrust",      "cat": "Specific", "fp_r1":  0, "fp_r2": 14, "fp_l1": -1, "attr": None},
    1051: {"name": "Miquella's Ring of Light","cat": "Specific", "fp_r1":  0, "fp_r2": 11, "fp_l1": -1, "attr": None},
    1052: {"name": "Golden Tempering",        "cat": "Specific", "fp_r1":  0, "fp_r2": 24, "fp_l1": -1, "attr": None},
    1053: {"name": "Last Rites",              "cat": "Specific", "fp_r1":  0, "fp_r2": 25, "fp_l1": -1, "attr": None},
    1054: {"name": "Unblockable Blade",       "cat": "Specific", "fp_r1":  0, "fp_r2": 18, "fp_l1": -1, "attr": None},
    1055: {"name": "Eochaid's Dancing Blade", "cat": "Specific", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},
    1056: {"name": "Magic Dagger",            "cat": "Specific", "fp_r1":  0, "fp_r2":  7, "fp_l1": -1, "attr": None},
    1165: {"name": "Loretta's Slash (Sickle)","cat": "Specific", "fp_r1":  0, "fp_r2": 14, "fp_l1": -1, "attr": None},
    1166: {"name": "Spinning Slash (Dragon Halberd)","cat": "Specific", "fp_r1": 0, "fp_r2": 17, "fp_l1": -1, "attr": None},
    1167: {"name": "Corpse Wax Cutter",       "cat": "Specific", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None},
    1168: {"name": "Zamor Ice Storm",         "cat": "Specific", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},
    1169: {"name": "Radahn's Rain",           "cat": "Specific", "fp_r1": 32, "fp_r2": -1, "fp_l1": -1, "attr": None},
    1170: {"name": "The Queen's Black Flame", "cat": "Specific", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},
    1171: {"name": "Dynast's Finesse",        "cat": "Specific", "fp_r1":  0, "fp_r2":  5, "fp_l1": -1, "attr": None},
    1172: {"name": "Magma Shower",            "cat": "Specific", "fp_r1":  0, "fp_r2": 12, "fp_l1": -1, "attr": None},
    1173: {"name": "Nebula (Wing of Astel)",  "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1174: {"name": "Death Flare",             "cat": "Specific", "fp_r1":  0, "fp_r2": 16, "fp_l1": -1, "attr": None},
    1175: {"name": "Bloodhound's Finesse",    "cat": "Specific", "fp_r1":  0, "fp_r2":  8, "fp_l1": -1, "attr": None},
    1176: {"name": "Magma Guillotine",        "cat": "Specific", "fp_r1":  0, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1177: {"name": "Corpse Piler",            "cat": "Specific", "fp_r1":  0, "fp_r2": 17, "fp_l1": -1, "attr": None},
    1178: {"name": "Transient Moonlight",     "cat": "Specific", "fp_r1": 15, "fp_r2": 20, "fp_l1": -1, "attr": None},
    1179: {"name": "Bloodblade Dance",        "cat": "Specific", "fp_r1":  0, "fp_r2": 11, "fp_l1": -1, "attr": None},
    1182: {"name": "Knowledge Above All",     "cat": "Specific", "fp_r1":  0, "fp_r2": 35, "fp_l1": -1, "attr": None},
    1183: {"name": "Devourer of Worlds",      "cat": "Specific", "fp_r1":  0, "fp_r2": 35, "fp_l1": -1, "attr": None},
    1184: {"name": "Familial Rancor",         "cat": "Specific", "fp_r1":  0, "fp_r2": 25, "fp_l1": -1, "attr": None},
    1185: {"name": "Rosus's Summons",         "cat": "Specific", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},
    1186: {"name": "Thunderstorm",            "cat": "Specific", "fp_r1":  0, "fp_r2": 19, "fp_l1": -1, "attr": None},
    1187: {"name": "Sacred Phalanx",          "cat": "Specific", "fp_r1":  0, "fp_r2": 12, "fp_l1": -1, "attr": None},
    1188: {"name": "Great-Serpent Hunt",      "cat": "Specific", "fp_r1":  0, "fp_r2": 10, "fp_l1": -1, "attr": None},
    1189: {"name": "Angel's Wings",           "cat": "Specific", "fp_r1":  0, "fp_r2": 17, "fp_l1": -1, "attr": None},
    1190: {"name": "Storm Kick",              "cat": "Specific", "fp_r1":  0, "fp_r2":  4, "fp_l1": -1, "attr": None},
    1191: {"name": "Unblockable Blade (Pata)","cat": "Specific", "fp_r1":  0, "fp_r2": 17, "fp_l1": -1, "attr": None},
    1192: {"name": "Sorcery of the Crozier",  "cat": "Specific", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},
    1193: {"name": "Erdtree Slam",            "cat": "Specific", "fp_r1":  0, "fp_r2": 19, "fp_l1": -1, "attr": None},
    1194: {"name": "Gravity Bolt",            "cat": "Specific", "fp_r1":  0, "fp_r2": 13, "fp_l1": -1, "attr": None},
    1195: {"name": "Fires of Slumber",        "cat": "Specific", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},
    1196: {"name": "Golden Retaliation",      "cat": "Specific", "fp_r1":  0, "fp_r2":  4, "fp_l1": -1, "attr": None},
    1197: {"name": "Contagious Fury",         "cat": "Specific", "fp_r1":  0, "fp_r2":  9, "fp_l1": -1, "attr": None},
    1198: {"name": "Ordovis's Vortex",        "cat": "Specific", "fp_r1":  0, "fp_r2": 15, "fp_l1": -1, "attr": None},

    # ── Legendary ───────────────────────────────────────────────────────
    1200: {"name": "Storm Ruler",   "cat": "Legendary", "fp_r1":  9, "fp_r2": 18, "fp_l1": -1, "attr": None},

    # ── Nightreign-specific ──────────────────────────────────────────────
    9999: {"name": "??? (Skill Reroll Standin)", "cat": "Internal", "fp_r1": 0, "fp_r2": 0, "fp_l1": -1, "attr": None,
           "note": "Nightreign-only placeholder used in skill reroll system"},
}

# =============================================================================
# SKILL CATEGORY → START HEROES MAPPING
# Based on isStartSkill_<Hero> flags in SwordArtsParam
# =============================================================================
START_SKILLS: dict[str, list[str]] = {
    "Determination":       ["Wylder", "Guardian", "Ironeye", "Duchess", "Raider", "Revenant", "Undertaker"],
    "Endure":              ["Wylder", "Guardian", "Ironeye", "Duchess", "Raider", "Revenant", "Undertaker"],
    "Quickstep":           ["Wylder", "Guardian", "Ironeye", "Duchess", "Raider", "Revenant", "Undertaker"],
    "White Shadow's Lure": ["Wylder", "Guardian", "Ironeye", "Duchess", "Raider", "Revenant", "Undertaker"],
}

# =============================================================================
# POOL TABLE BASE IDs (SwordArtsTableParam weapon type roots)
# =============================================================================
# Full pools (affinityOffset +0), append affinity offsets as needed:
# +50 = Standard only, +100 = All elemental, +500..+1100 = specific element
WEAPON_POOL_BASES: dict[str, int] = {
    "Dagger":          10000000,
    "Straight Sword":  20000000,
    "Greatsword":      30000000,
    "Colossal Sword":  40000000,
    "Thrusting Sword": 50000000,
    "Heavy Thrusting": 60000000,
    "Curved Sword":    70000000,
    # Additional weapon types follow pattern at higher base IDs
}

AFFINITY_OFFSET: dict[str, int] = {
    "Full":      0,
    "Standard":  50,
    "Elemental": 100,
    "Fire":      500,
    "Lightning": 600,
    "Holy":      700,
    "Magic":     800,
    "Frost":     900,
    "Poison":   1000,
    "Blood":    1100,
    "Shadow":   1200,
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def skill_name(skill_id: int) -> str | None:
    """Return the display name for a skill ID, or None if not found."""
    s = SKILLS.get(skill_id)
    return s["name"] if s else None


def skills_by_category(cat: str) -> list[tuple[int, str]]:
    """Return [(id, name)] for all skills in a given category."""
    return [(sid, s["name"]) for sid, s in SKILLS.items() if s["cat"] == cat]


def elemental_skills() -> list[tuple[int, str, str]]:
    """Return [(id, name, category)] for all elemental skills (non-Standard/Shield/Bow)."""
    elemental_cats = {"Fire", "Lightning", "Holy", "Magic", "Frost", "Poison", "Blood"}
    return [(sid, s["name"], s["cat"]) for sid, s in SKILLS.items()
            if s["cat"] in elemental_cats]
