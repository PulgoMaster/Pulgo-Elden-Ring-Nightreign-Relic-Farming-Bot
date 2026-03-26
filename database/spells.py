# Nightreign Spell School Database
# Built from Magic.csv (Smithbox export)
# Data mining completed: 2026-03-25
#
# subCategory1 (column 85, 0-based) is the school ID field.
# disableParam_NT: 1 or 2 = enabled for all named spells (0 = disabled, none found).
# Spell type determined by Name prefix ([Sorcery] / [Incantation]) and
# spEffectCategory column (27): 3 = Sorcery, 4 = Incantation.
#
# NOTE: Magic.csv contains all base ER spells. Not all are available in Nightreign.
# The school → GROUP_800 passive mapping is still correct for any that appear.


# =============================================================================
# SCHOOL ID → GROUP_800 RELIC PASSIVE
# =============================================================================
# Confirmed from cross-referencing SpEffectParam.csv (magicSubCategoryChange1)
# and AttachEffectParam.csv (passiveSpEffectId_1 → school filter value).
# IDs NOT in this dict have no corresponding GROUP_800 relic passive.

SCHOOL_ID_TO_PASSIVE: dict[int, str] = {
    # Sorcery schools
    2:  "Improved Carian Sword Sorcery",
    3:  "Improved Glintblade Sorcery",
    4:  "Improved Stonedigger Sorcery",
    5:  "Improved Crystalian Sorcery",
    9:  "Improved Thorn Sorcery",
    11: "Improved Gravity Sorcery",
    12: "Improved Invisibility Sorcery",
    # Incantation schools
    20: "Improved Godslayer Incantations",
    21: "Improved Giants' Flame Incantations",
    22: "Improved Dragon Cult Incantations",
    23: "Improved Bestial Incantations",
    24: "Improved Fundamentalist Incantations",
    25: "Improved Dragon Communion Incantations",
    26: "Improved Frenzied Flame Incantations",
}

# Reverse: passive name → school ID
PASSIVE_TO_SCHOOL_ID: dict[str, int] = {v: k for k, v in SCHOOL_ID_TO_PASSIVE.items()}


# =============================================================================
# SCHOOL IDs FOUND IN DATA WITH NO MAPPED GROUP_800 PASSIVE
# =============================================================================
# These spell schools exist in the param data but have no corresponding
# school-specific relic passive in Nightreign's AttachEffectParam.
# Spells in these schools benefit only from the broad boosters
# (Improved Sorceries / Improved Incantations) and generic attack-up passives.

UNMAPPED_SCHOOL_IDS: dict[int, str] = {
    0:   "Generic / No school",
    1:   "Moon (Rennala's / Ranni's Dark Moon)",
    6:   "Eternal Darkness / Night variant",
    8:   "Magma / Volcano Manor (Rykard)",
    10:  "Death / Ghostflame",
    13:  "Cold / Carian Ice",
    14:  "Prismatic / Comet Azur",
    15:  "Stars of Ruin",
    27:  "Unknown (Noble Presence)",
    28:  "Crucible",
    126: "Special flag (Poison Mist)",
}


# =============================================================================
# SORCERIES — name → subCategory1 school ID
# =============================================================================
# 56 named sorceries total (incl. Carian Retaliation internal variants).
# subCategory1 = 0 → no school passive, benefits only from Improved Sorceries.

SORCERIES: dict[str, int] = {

    # ── Glintstone (generic, subCategory1 = 0) ────────────────────────────
    "Glintstone Pebble":            0,
    "Great Glintstone Shard":       0,
    "Swift Glintstone Shard":       0,
    "Shard Spiral":                 0,
    "Glintstone Arc":               0,
    "Crystal Barrage":              0,
    "Crystal Burst":                0,
    "Cannon of Haima":              0,
    "Gavel of Haima":               0,
    "Terra Magica":                 0,
    "Founding Rain of Stars":       0,
    "Magic Downpour":               0,
    "Loretta's Greatbow":           0,
    "Loretta's Mastery":            0,
    "Scholar's Armament":           0,
    "Scholar's Shield":             0,
    "Ambush Shard":                 0,
    "Thops's Barrier":              0,
    "Night Maiden's Mist":          0,
    "Oracle Bubbles":               0,
    "Great Oracular Bubble":        0,

    # ── Moon (subCategory1 = 1, unmapped) ─────────────────────────────────
    "Rennala's Full Moon":          1,
    "Ranni's Dark Moon":            1,

    # ── Carian Sword (subCategory1 = 2) ───────────────────────────────────
    "Carian Greatsword":            2,   # → Improved Carian Sword Sorcery
    "Carian Slicer":                2,   # → Improved Carian Sword Sorcery
    "Carian Piercer":               2,   # → Improved Carian Sword Sorcery
    "Adula's Moonblade":            2,   # → Improved Carian Sword Sorcery

    # ── Glintblade (subCategory1 = 3) ─────────────────────────────────────
    "Magic Glintblade":             3,   # → Improved Glintblade Sorcery
    "Glintblade Phalanx":           3,   # → Improved Glintblade Sorcery
    "Carian Phalanx":               3,   # → Improved Glintblade Sorcery
    "Greatblade Phalanx":           3,   # → Improved Glintblade Sorcery
    "Carian Retaliation":           3,   # → Improved Glintblade Sorcery
    "Carian Retaliation (Level 3)": 3,   # internal variant
    "Carian Retaliation (Level 4)": 3,   # internal variant

    # ── Stonedigger (subCategory1 = 4) ────────────────────────────────────
    "Shatter Earth":                4,   # → Improved Stonedigger Sorcery
    "Rock Blaster":                 4,   # → Improved Stonedigger Sorcery

    # ── Crystalian (subCategory1 = 5) ─────────────────────────────────────
    "Shattering Crystal":           5,   # → Improved Crystalian Sorcery
    "Crystal Release":              5,   # → Improved Crystalian Sorcery
    "Crystal Torrent":              5,   # → Improved Crystalian Sorcery

    # ── Eternal Darkness (subCategory1 = 6, unmapped) ─────────────────────
    "Eternal Darkness":             6,

    # ── Magma / Volcano (subCategory1 = 8, unmapped) ──────────────────────
    "Magma Shot":                   8,
    "Gelmir's Fury":                8,
    "Roiling Magma":                8,
    "Rykard's Rancor":              8,

    # ── Thorn (subCategory1 = 9) ──────────────────────────────────────────
    "Briars of Sin":                9,   # → Improved Thorn Sorcery
    "Briars of Punishment":         9,   # → Improved Thorn Sorcery

    # ── Death / Ghostflame (subCategory1 = 10, unmapped) ─────────────────
    "Rancorcall":                   10,
    "Ancient Death Rancor":         10,
    "Explosive Ghostflame":         10,
    "Tibia's Summons":              10,

    # ── Gravity (subCategory1 = 11) ───────────────────────────────────────
    "Rock Sling":                   11,  # → Improved Gravity Sorcery
    "Gravity Well":                 11,  # → Improved Gravity Sorcery
    "Collapsing Stars":             11,  # → Improved Gravity Sorcery
    "Meteorite":                    11,  # → Improved Gravity Sorcery
    "Meteorite of Astel":           11,  # → Improved Gravity Sorcery

    # ── Night / Invisibility (subCategory1 = 12) ──────────────────────────
    "Night Shard":                  12,  # → Improved Invisibility Sorcery
    "Night Comet":                  12,  # → Improved Invisibility Sorcery

    # ── Cold / Carian Ice (subCategory1 = 13, unmapped) ───────────────────
    "Glintstone Icecrag":           13,
    "Zamor Ice Storm":              13,
    "Freezing Mist":                13,
    "Frozen Armament":              13,

    # ── Prismatic / Azure (subCategory1 = 14, unmapped) ───────────────────
    "Comet Azur":                   14,

    # ── Stars of Ruin (subCategory1 = 15, unmapped) ───────────────────────
    "Stars of Ruin":                15,
}


# =============================================================================
# INCANTATIONS — name → subCategory1 school ID
# =============================================================================
# 65 named incantations total.
# subCategory1 = 0 → no school passive; benefits from Improved Incantations.

INCANTATIONS: dict[str, int] = {

    # ── Generic / no school (subCategory1 = 0) ────────────────────────────
    "Catch Flame":                          0,
    "Flame Sling":                          0,
    "Fire's Deadly Sin":                    0,
    "Rejection":                            0,
    "Wrath of Gold":                        0,
    "Urgent Heal":                          0,
    "Heal":                                 0,
    "Great Heal":                           0,
    "Lord's Heal":                          0,
    "Erdtree Heal":                         0,
    "Blessing's Boon":                      0,
    "Blessing of the Erdtree":              0,
    "Flame Fortification":                  0,
    "Magic Fortification":                  0,
    "Lightning Fortification":              0,
    "Divine Fortification":                 0,
    "Lord's Divine Fortification":          0,
    "Golden Lightning Fortification":       0,
    "Shadow Bait":                          0,
    "Darkness":                             0,
    "Golden Vow":                           0,
    "Barrier of Gold":                      0,
    "Protection of the Erdtree":            0,
    "Pest Threads":                         0,
    "Swarm of Flies":                       0,
    "Poison Armament":                      0,
    "Scarlet Aeonia":                       0,
    "Elden Stars":                          0,
    "Bloodflame Talons":                    0,
    "Bloodboon":                            0,
    "Bloodflame Blade":                     0,
    "Placidusax's Ruin":                    0,
    "Black Blade":                          0,

    # ── Godslayer (subCategory1 = 20) ─────────────────────────────────────
    "Black Flame":                          20,  # → Improved Godslayer Incantations
    "Scouring Black Flame":                 20,  # → Improved Godslayer Incantations
    "Black Flame Ritual":                   20,  # → Improved Godslayer Incantations
    "Black Flame Blade":                    20,  # → Improved Godslayer Incantations
    "Black Flame's Protection":             20,  # → Improved Godslayer Incantations

    # ── Giants' Flame (subCategory1 = 21) ─────────────────────────────────
    "O, Flame!":                            21,  # → Improved Giants' Flame Incantations
    "Flame, Fall Upon Them":                21,
    "Whirl, O Flame!":                      21,
    "Flame, Grant Me Strength":             21,
    "Flame, Protect Me":                    21,
    "Giantsflame Take Thee":                21,
    "Flame of the Fell God":                21,
    "Burn, O Flame!":                       21,
    "Surge, O Flame!":                      21,

    # ── Dragon Cult / Lightning (subCategory1 = 22) ────────────────────────
    "Death Lightning":                      22,  # → Improved Dragon Cult Incantations
    "Lightning Spear":                      22,
    "Lightning Strike":                     22,
    "Ancient Dragons' Lightning Strike":    22,
    "Ancient Dragons' Lightning Spear":     22,
    "Frozen Lightning Spear":               22,
    "Honed Bolt":                           22,
    "Fortissax's Lightning Spear":          22,
    "Lansseax's Glaive":                    22,
    "Electrify Armament":                   22,
    "Dragonbolt Blessing":                  22,

    # ── Bestial (subCategory1 = 23) ───────────────────────────────────────
    "Bestial Sling":                        23,  # → Improved Bestial Incantations
    "Stone of Gurranq":                     23,
    "Beast Claw":                           23,
    "Gurranq's Beast Claw":                 23,
    "Bestial Vitality":                     23,

    # ── Fundamentalist (subCategory1 = 24) ────────────────────────────────
    "Litany of Proper Death":               24,  # → Improved Fundamentalist Incantations
    "Discus of Light":                      24,
    "Triple Rings of Light":                24,
    "Radagon's Rings of Light":             24,
    "Law of Regression":                    24,
    "Immutable Shield":                     24,
    "Law of Causality":                     24,
    "Order's Blade":                        24,

    # ── Dragon Communion (subCategory1 = 25) ──────────────────────────────
    "Dragonfire":                           25,  # → Improved Dragon Communion Incantations
    "Agheel's Flame":                       25,
    "Magma Breath":                         25,
    "Theodorix's Magma":                    25,
    "Dragonice":                            25,
    "Borealis's Mist":                      25,
    "Rotten Breath":                        25,
    "Ekzykes's Decay":                      25,
    "Glintstone Breath":                    25,
    "Smarag's Glint Breath":                25,
    "Dragonclaw":                           25,
    "Dragonmaw":                            25,
    "Greyoll's Roar":                       25,

    # ── Frenzied Flame (subCategory1 = 26) ────────────────────────────────
    "The Flame of Frenzy":                  26,  # → Improved Frenzied Flame Incantations
    "Unendurable Frenzy":                   26,
    "Frenzied Burst":                       26,
    "Howl of Shabriri":                     26,

    # ── Unknown / unmapped school IDs ─────────────────────────────────────
    "Poison Mist":                          126, # special flag (unmapped)
    "Noble Presence":                       27,  # unmapped
    "Aspects of the Crucible: Tail":        28,  # Crucible (unmapped)
    "Aspects of the Crucible: Horns":       28,
    "Aspects of the Crucible: Breath":      28,
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_school_passive(spell_name: str) -> str | None:
    """
    Return the GROUP_800 relic passive that boosts this spell, or None if
    the spell has no mapped school passive (generic or unmapped school).
    """
    school_id = SORCERIES.get(spell_name) or INCANTATIONS.get(spell_name)
    if school_id is None:
        return None
    return SCHOOL_ID_TO_PASSIVE.get(school_id)


def get_spells_for_passive(passive_name: str) -> list[str]:
    """
    Return all spell names boosted by a given GROUP_800 school passive.
    """
    school_id = PASSIVE_TO_SCHOOL_ID.get(passive_name)
    if school_id is None:
        return []
    return (
        [s for s, sid in SORCERIES.items() if sid == school_id]
        + [i for i, sid in INCANTATIONS.items() if sid == school_id]
    )


def is_sorcery(spell_name: str) -> bool:
    return spell_name in SORCERIES


def is_incantation(spell_name: str) -> bool:
    return spell_name in INCANTATIONS


# Quick-access: school passive → spells (precomputed)
PASSIVE_TO_SPELLS: dict[str, list[str]] = {
    passive: get_spells_for_passive(passive)
    for passive in SCHOOL_ID_TO_PASSIVE.values()
}
