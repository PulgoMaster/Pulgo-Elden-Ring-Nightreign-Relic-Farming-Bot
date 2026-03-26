# =============================================================================
# character_stats.py
# Nightreign Nightfarer base stats database
#
# Mined from two Smithbox param exports (Elden Ring Nightreign):
#   - HeroStatusParam.csv  — per-character stats at Level 1, 2, 12, and 15,
#                            plus per-level passive upgrade deltas (IDs 300000+)
#                            and Libra (guest NPC) stat archetypes (IDs 210000+)
#   - CharaInitParam.csv   — starting equipment, spell loadouts, heroId mapping,
#                            and CharacterScale (physical size scalar per hero)
#
# HeroStatusParam columns used:
#   totalLevel            — snapshot level for this row
#   statVigor             — VIG at that level
#   statMind              — MND at that level
#   statEndurance         — END at that level
#   statStrength          — STR at that level
#   statDexterity         — DEX at that level
#   statIntelligence      — INT at that level
#   statFaith             — FAI at that level
#   statArcane            — ARC at that level
#   abilityReinforce      — passive ability tier at this snapshot
#   revenantSpiritReinforce — Revenant spirit tier (Revenant-specific)
#   attackRate            — attack rate multiplier flag (1 = normal)
#   executorBeastReinforce  — Executor beast mode tier (Executor-specific)
#
# CharaInitParam columns used:
#   soulLv                — starting rune level for the init entry
#   baseVit/baseWil/etc.  — base stats baked into the init entry (pre-scaling)
#   heroId                — links init entry to HeroStatusParam hero group
#   CharacterScale        — float scalar for character physical size
#
# NOTE: "Scholar" appears in the data as a 10th Nightfarer alongside Undertaker.
# "Undertaker" (ID prefix 100000) is the 10th character — likely the one
# described as using consumables heavily based on its stat profile.
# No "Furnace Golem" playable entry was found in these params.
#
# Level snapshots in HeroStatusParam are: 1, 2, 12, 15
# (Not every level — these are specific reference snapshots for scaling curves.)
# =============================================================================

from typing import TypedDict, Dict, List


class StatSnapshot(TypedDict):
    level: int
    vig: int
    mnd: int
    end: int
    str: int
    dex: int
    int_: int   # "int" is a Python builtin, so stored as int_
    fai: int
    arc: int
    ability_reinforce: int
    revenant_spirit_reinforce: int
    attack_rate: int
    executor_beast_reinforce: int


class CharacterStats(TypedDict):
    hero_id: int                    # Internal ID group prefix (x10000 in HeroStatusParam)
    chara_init_id: int              # Primary CharaInitParam row ID
    character_scale: float          # Physical size scalar from CharaInitParam
    level_snapshots: List[StatSnapshot]   # Stats at levels 1, 2, 12, 15
    stat_upgrade_variants: Dict[str, List[StatSnapshot]]  # Named passive upgrade deltas


# ---------------------------------------------------------------------------
# Raw level snapshot data — sourced directly from HeroStatusParam.csv
# Each entry = one row in the param, keyed by (hero_name, level).
# ---------------------------------------------------------------------------

def _snap(level, vig, mnd, end, str_, dex, int_, fai, arc,
          ab_reinf, rev_spirit, atk_rate, exe_beast) -> StatSnapshot:
    return StatSnapshot(
        level=level, vig=vig, mnd=mnd, end=end, str=str_, dex=dex,
        int_=int_, fai=fai, arc=arc,
        ability_reinforce=ab_reinf,
        revenant_spirit_reinforce=rev_spirit,
        attack_rate=atk_rate,
        executor_beast_reinforce=exe_beast,
    )


# ---------------------------------------------------------------------------
# CHARACTER_STATS
# Primary lookup: character_name (lowercase) -> CharacterStats dict
#
# hero_id matches the leading digits of HeroStatusParam IDs:
#   Wylder=1, Guardian=2, Ironeye=3, Duchess=4, Raider=5,
#   Revenant=6, Recluse=7, Executor=8, Scholar=9, Undertaker=10
#
# chara_init_id = the primary CharaInitParam row for that character
# character_scale = CharacterScale field from CharaInitParam
# ---------------------------------------------------------------------------

CHARACTER_STATS: Dict[str, CharacterStats] = {
    "wylder": {
        "hero_id": 1,
        "chara_init_id": 50,          # CharaInitParam ID 50 (heroId group 0)
        "character_scale": 1.0,
        # Level snapshots: (level, VIG, MND, END, STR, DEX, INT, FAI, ARC,
        #                    ab_reinf, rev_spirit, atk_rate, exe_beast)
        "level_snapshots": [
            _snap( 1,  8,  4,  3,  5,  4,  2,  2, 10,  0,  0, 1, 0),
            _snap( 2, 16,  6,  6, 18, 15,  4,  4, 10,  1,  1, 1, 1),
            _snap(12, 46, 16, 24, 44, 35, 12, 12, 10, 11, 11, 1, 11),
            _snap(15, 52, 19, 27, 50, 40, 15, 15, 10, 14, 14, 1, 14),
        ],
        # Passive upgrade deltas (added on top of base level stats)
        # Source: HeroStatusParam IDs 300000–300101
        "stat_upgrade_variants": {
            "+Mnd/-Vig": [
                _snap( 1, -1,  1,  0,  0,  0,  0,  0,  0, 0, 0, 1, 0),
                _snap(12, -5, 10,  0,  0,  0,  0,  0,  0, 0, 0, 1, 0),
            ],
            "+Int/+Fth/-Str/-Dex": [
                _snap( 1,  0,  0,  0, -1, -1,  1,  1,  0, 0, 0, 1, 0),
                _snap(12,  0,  0,  0, -7, -5, 15, 15,  0, 0, 0, 1, 0),
            ],
        },
    },

    "guardian": {
        "hero_id": 2,
        "chara_init_id": 51,
        "character_scale": 1.05,
        "level_snapshots": [
            _snap( 1, 10,  2,  6,  4,  3,  2,  3, 10,  0,  0, 1, 0),
            _snap( 2, 19,  3, 12, 11,  9,  3,  5, 10,  1,  1, 1, 1),
            _snap(12, 54, 11, 33, 36, 26,  8, 18, 10, 11, 11, 1, 11),
            _snap(15, 60, 14, 38, 41, 31, 10, 21, 10, 14, 14, 1, 14),
        ],
        "stat_upgrade_variants": {
            "+Str/+Dex/-Vig": [
                _snap( 1, -1,  0,  0,  1,  2,  0,  0,  0, 0, 0, 1, 0),
                _snap(12, -8,  0,  0,  9, 19,  0,  0,  0, 0, 0, 1, 0),
            ],
            "+Mnd/+Fth/-Vig": [
                _snap( 1, -1,  1,  0,  0,  0,  0,  2,  0, 0, 0, 1, 0),
                _snap(12, -6,  8,  0,  0,  0,  0, 17,  0, 0, 0, 1, 0),
            ],
        },
    },

    "ironeye": {
        "hero_id": 3,
        "chara_init_id": 60,
        "character_scale": 0.85,
        "level_snapshots": [
            _snap( 1,  6,  2,  4,  4,  8,  2,  2, 13,  0,  0, 1, 0),
            _snap( 2, 12,  3,  7,  7, 20,  3,  3, 13,  1,  1, 1, 1),
            _snap(12, 34, 11, 25, 17, 51,  6, 10, 13, 11, 11, 1, 11),
            _snap(15, 37, 14, 28, 19, 57,  7, 13, 13, 14, 14, 1, 14),
        ],
        "stat_upgrade_variants": {
            "+Arc/-Dex": [
                _snap( 1,  0,  0,  0,  0, -1,  0,  0,  2, 0, 0, 1, 0),
                _snap(12,  0,  0,  0,  0, -9,  0,  0, 15, 0, 0, 1, 0),
            ],
            "+Vig/+Str/-Dex": [
                _snap( 1,  1,  0,  0,  2, -2,  0,  0,  0, 0, 0, 1, 0),
                _snap(12,  5,  0,  0, 20,-13,  0,  0,  0, 0, 0, 1, 0),
            ],
        },
    },

    "duchess": {
        "hero_id": 4,
        "chara_init_id": 61,
        "character_scale": 0.85,
        "level_snapshots": [
            _snap( 1,  7,  6,  3,  2,  5,  4,  3, 11,  0,  0, 1, 0),
            _snap( 2, 13,  9,  4,  4, 13,  8,  6, 11,  1,  1, 1, 1),
            _snap(12, 35, 24, 14,  9, 38, 36, 24, 11, 11, 11, 1, 11),
            _snap(15, 39, 27, 18, 11, 45, 42, 27, 11, 14, 14, 1, 14),
        ],
        "stat_upgrade_variants": {
            "+Vig/+Str/-Mnd": [
                _snap( 1,  1, -2,  0,  2,  0,  0,  0,  0, 0, 0, 1, 0),
                _snap(12,  3,-14,  0, 24,  0,  0,  0,  0, 0, 0, 1, 0),
            ],
            "+Mnd/+Fth/-Int": [
                _snap( 1,  0,  1,  0,  0,  0, -1,  2,  0, 0, 0, 1, 0),
                _snap(12,  0,  3,  0,  0,  0, -5, 13,  0, 0, 0, 1, 0),
            ],
        },
    },

    "raider": {
        "hero_id": 5,
        "chara_init_id": 62,
        "character_scale": 0.85,
        "level_snapshots": [
            _snap( 1,  9,  2,  6,  9,  4,  1,  2, 10,  0,  0, 1, 0),
            _snap( 2, 18,  3, 12, 25,  6,  2,  4, 10,  1,  1, 1, 1),
            _snap(12, 50,  8, 31, 60, 16,  2, 10, 10, 11, 11, 1, 11),
            _snap(15, 56, 10, 37, 68, 19,  3, 12, 10, 14, 14, 1, 14),
        ],
        "stat_upgrade_variants": {
            "+Mnd/+Int/-Vig/-End": [
                _snap( 1, -1,  1, -1,  0,  0,  2,  0,  0, 0, 0, 1, 0),
                _snap(12, -8,  9, -4,  0,  0, 35,  0,  0, 0, 0, 1, 0),
            ],
            "+Arc/-Vig": [
                _snap( 1, -1,  0,  0,  0,  0,  0,  0,  2, 0, 0, 1, 0),
                _snap(12, -4,  0,  0,  0,  0,  0,  0, 17, 0, 0, 1, 0),
            ],
        },
    },

    "revenant": {
        "hero_id": 6,
        "chara_init_id": 50,   # shares Wylder's init slot range; heroId group 6
        "character_scale": 1.0,
        "level_snapshots": [
            _snap( 1,  6,  7,  3,  2,  2,  4,  5, 12,  0,  0, 1, 0),
            _snap( 2, 11, 11,  4,  6,  6,  7, 15, 12,  1,  1, 1, 1),
            _snap(12, 32, 28, 18, 18, 18, 27, 45, 12, 11, 11, 1, 11),
            _snap(15, 35, 31, 21, 21, 21, 30, 51, 12, 14, 14, 1, 14),
        ],
        "stat_upgrade_variants": {
            "+Vig/+End/-Mnd": [
                _snap( 1,  1, -1,  1,  0,  0,  0,  0,  0, 0, 0, 1, 0),
                _snap(12,  5,-11,  5,  0,  0,  0,  0,  0, 0, 0, 1, 0),
            ],
            "+Str/-Fth": [
                _snap( 1,  0,  0,  0,  2,  0,  0, -1,  0, 0, 0, 1, 0),
                _snap(12,  0,  0,  0, 25,  0,  0, -6,  0, 0, 0, 1, 0),
            ],
        },
    },

    "recluse": {
        "hero_id": 7,
        "chara_init_id": 51,
        "character_scale": 1.05,
        "level_snapshots": [
            _snap( 1,  6,  7,  3,  1,  2,  5,  5, 10,  0,  0, 1, 0),
            _snap( 2, 10, 11,  5,  2,  4, 15, 15, 10,  1,  1, 1, 1),
            _snap(12, 30, 27, 20,  9, 16, 45, 45, 10, 11, 11, 1, 11),
            _snap(15, 33, 30, 23, 12, 19, 51, 51, 10, 14, 14, 1, 14),
        ],
        "stat_upgrade_variants": {
            "+Vig/+End/+Dex/-Int/-Fth": [
                _snap( 1,  1,  0,  1,  0,  2, -1, -1,  0, 0, 0, 1, 0),
                _snap(12,  4,  0,  5,  0, 20,-10,-10,  0, 0, 0, 1, 0),
            ],
            "+Int/+Fth/-Mnd": [
                _snap( 1,  0, -2,  0,  0,  0,  2,  2,  0, 0, 0, 1, 0),
                _snap(12,  0,-13,  0,  0,  0, 12, 12,  0, 0, 0, 1, 0),
            ],
        },
    },

    "executor": {
        "hero_id": 8,
        "chara_init_id": 60,
        "character_scale": 0.85,
        "level_snapshots": [
            _snap( 1,  7,  2,  3,  5,  8,  2,  2, 28,  0,  0, 1, 0),
            _snap( 2, 14,  3,  5,  9, 20,  3,  3, 28,  1,  1, 1, 1),
            _snap(12, 40,  9, 24, 22, 60,  7,  5, 28, 11, 11, 1, 11),
            _snap(15, 46, 11, 27, 25, 63,  8,  6, 28, 14, 14, 1, 14),
        ],
        "stat_upgrade_variants": {
            "+Vig/+End/-Arc": [
                _snap( 1,  1,  0,  1,  0,  0,  0,  0, -2, 0, 0, 1, 0),
                _snap(12,  5,  0,  6,  0,  0,  0,  0,-13, 0, 0, 1, 0),
            ],
            "+Dex/+Arc/-Vig": [
                _snap( 1, -1,  0,  0,  0,  1,  0,  0,  1, 0, 0, 1, 0),
                _snap(12, -7,  0,  0,  0, 12,  0,  0,  9, 0, 0, 1, 0),
            ],
        },
    },

    "scholar": {
        "hero_id": 9,
        "chara_init_id": 62,
        "character_scale": 0.85,
        "level_snapshots": [
            _snap( 1,  7,  4,  3,  1,  2,  4,  2, 50,  0,  0, 1, 0),
            _snap( 2, 14,  6,  5,  2,  4,  7,  4, 50,  1,  1, 1, 1),
            _snap(12, 36, 17, 22, 12, 15, 25, 12, 50, 11, 11, 1, 11),
            _snap(15, 41, 20, 25, 14, 18, 28, 15, 50, 14, 14, 1, 14),
        ],
        "stat_upgrade_variants": {
            "+Mnd/-Vig": [
                _snap( 1, -1,  1,  0,  0,  0,  0,  0,  0, 0, 0, 1, 0),
                _snap(12, -3,  9,  0,  0,  0,  0,  0,  0, 0, 0, 1, 0),
            ],
            "+End/+Dex/-Int/-Arc": [
                _snap( 1,  0,  0,  1,  0,  6, -1,  0, -5, 0, 0, 1, 0),
                _snap(12,  0,  0,  6,  0, 40, -4,  0,-20, 0, 0, 1, 0),
            ],
        },
    },

    "undertaker": {
        "hero_id": 10,
        "chara_init_id": 50,   # heroId group 10
        "character_scale": 1.0,
        "level_snapshots": [
            _snap( 1,  7,  4,  3,  5,  2,  2,  5, 10,  0,  0, 1, 0),
            _snap( 2, 14,  6,  5, 18,  4,  2, 17, 10,  1,  1, 1, 1),
            _snap(12, 42, 12, 19, 44, 11,  4, 37, 10, 11, 11, 1, 11),
            _snap(15, 48, 14, 22, 50, 13,  5, 41, 10, 14, 14, 1, 14),
        ],
        "stat_upgrade_variants": {
            "+Dex/-Vig/-Fth": [
                _snap( 1, -1,  0,  0,  0,  2,  0, -2,  0, 0, 0, 1, 0),
                _snap(12, -5,  0,  0,  0, 19,  0,-13,  0, 0, 0, 1, 0),
            ],
            "+Mnd/+Fth/-Str": [
                _snap( 1,  0,  1,  0, -2,  0,  0,  1,  0, 0, 0, 1, 0),
                _snap(12,  0,  9,  0,-15,  0,  0, 12,  0, 0, 0, 1, 0),
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# LIBRA_STATS
# "Libra" is a guest/NPC Nightfarer with 5 stat archetypes (not player-selectable).
# HeroStatusParam IDs 210000–250003.
# Included for completeness; not a playable character.
# ---------------------------------------------------------------------------

LIBRA_STATS: Dict[str, List[StatSnapshot]] = {
    "strength": [
        _snap( 1,  7,  1,  3, 11,  2,  1,  1,  1, 0, 0, 1, 0),
        _snap( 2, 15,  2,  5, 28,  3,  2,  2,  2, 1, 1, 1, 1),
        _snap(12, 42,  5, 21, 65,  8,  2,  2,  2, 11, 11, 1, 11),
        _snap(15, 47,  6, 23, 73,  9,  3,  3,  3, 14, 14, 1, 14),
    ],
    "dexterity": [
        _snap( 1,  7,  2,  3,  2, 11,  1,  1,  1, 0, 0, 1, 0),
        _snap( 2, 13,  3,  5,  3, 28,  2,  2,  2, 1, 1, 1, 1),
        _snap(12, 39,  8, 21,  8, 65,  2,  2,  2, 11, 11, 1, 11),
        _snap(15, 43, 10, 23,  9, 73,  3,  3,  3, 14, 14, 1, 14),
    ],
    "intelligence": [
        _snap( 1,  6,  6,  3,  1,  1,  6,  3,  1, 0, 0, 1, 0),
        _snap( 2, 10,  9,  4,  2,  2, 17,  6,  2, 1, 1, 1, 1),
        _snap(12, 30, 25, 14,  7,  7, 49, 22,  2, 11, 11, 1, 11),
        _snap(15, 33, 28, 17,  9,  9, 55, 24,  3, 14, 14, 1, 14),
    ],
    "faith": [
        _snap( 1,  6,  6,  3,  1,  1,  3,  6,  1, 0, 0, 1, 0),
        _snap( 2, 10,  9,  4,  2,  2,  6, 17,  2, 1, 1, 1, 1),
        _snap(12, 30, 25, 14,  7,  7, 22, 49,  2, 11, 11, 1, 11),
        _snap(15, 33, 28, 17,  9,  9, 24, 55,  3, 14, 14, 1, 14),
    ],
    "arcane": [
        _snap( 1,  7,  6,  3,  4,  4,  4,  4, 35, 0, 0, 1, 0),
        _snap( 2, 13,  9,  5, 10, 10,  7,  7, 35, 1, 1, 1, 1),
        _snap(12, 37, 23, 23, 34, 34, 27, 27, 35, 11, 11, 1, 11),
        _snap(15, 41, 26, 26, 39, 39, 30, 30, 35, 14, 14, 1, 14),
    ],
}


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def get_level1_stats(character_name: str) -> StatSnapshot:
    """Return the Level 1 stat snapshot for a named Nightfarer."""
    name = character_name.lower()
    if name not in CHARACTER_STATS:
        raise KeyError(f"Unknown Nightfarer: {character_name!r}. "
                       f"Valid names: {sorted(CHARACTER_STATS)}")
    snaps = CHARACTER_STATS[name]["level_snapshots"]
    return next(s for s in snaps if s["level"] == 1)


def get_stats_at_level(character_name: str, level: int) -> StatSnapshot:
    """
    Return the closest stat snapshot at or below the given level.
    Available snapshot levels are 1, 2, 12, 15.
    """
    name = character_name.lower()
    if name not in CHARACTER_STATS:
        raise KeyError(f"Unknown Nightfarer: {character_name!r}.")
    snaps = sorted(CHARACTER_STATS[name]["level_snapshots"], key=lambda s: s["level"])
    result = snaps[0]
    for snap in snaps:
        if snap["level"] <= level:
            result = snap
        else:
            break
    return result


# Ordered list matching the 10 playable Nightfarers
NIGHTFARER_NAMES: List[str] = [
    "wylder",
    "guardian",
    "duchess",
    "ironeye",
    "recluse",
    "revenant",
    "raider",
    "executor",
    "undertaker",
    "scholar",
]
