"""
Deep of Night Relic Data
========================
Source: "Available Deep Relic Effects.txt", "deep relic stackability.txt"
Data-mined / cross-referenced: 2026-03-25

Deep of Night relics use a DIFFERENT stackability system than normal relics.
Effects are divided into 6 categories. Effects within the same category
cannot appear together on the same deep relic (except Category 6).

Category 6 is special: ALL Category 6 effects CAN stack freely with each other
AND with effects from any other category.
"""

# ─────────────────────────────────────────────────────────────────────────────
# DEEP RELIC EFFECT POOLS
# 2000000 pool = appears on the main (Delicate/Polished/Grand) deep relic slots
# 2100000 pool = appears as the "extra" slot content on deeper relics
# ─────────────────────────────────────────────────────────────────────────────

# Effects available in the 2000000 deep relic pool (high-power exclusive effects)
POOL_2000000 = [
    # Higher-tier elemental attack up (not available on normal relics)
    "Physical Attack Up +3",
    "Physical Attack Up +4",
    "Magic Attack Power Up +3",
    "Magic Attack Power Up +4",
    "Fire Attack Power Up +3",
    "Fire Attack Power Up +4",
    "Lightning Attack Power Up +3",
    "Lightning Attack Power Up +4",
    "Holy Attack Power Up +3",
    "Holy Attack Power Up +4",
    # Damage negation (higher tiers)
    "Improved Magic Damage Negation +1",
    "Improved Magic Damage Negation +2",
    "Improved Fire Damage Negation +1",
    "Improved Fire Damage Negation +2",
    "Improved Lightning Damage Negation +1",
    "Improved Lightning Damage Negation +2",
    "Improved Holy Damage Negation +1",
    "Improved Holy Damage Negation +2",
    # Status resistance (higher tiers)
    "Improved Poison Resistance +1",
    "Improved Poison Resistance +2",
    "Improved Blood Loss Resistance +1",
    "Improved Blood Loss Resistance +2",
    "Improved Sleep Resistance +1",
    "Improved Sleep Resistance +2",
    "Improved Death Blight Resistance +1",
    "Improved Death Blight Resistance +2",
    "Improved Rot Resistance +1",
    "Improved Rot Resistance +2",
    "Improved Frost Resistance +1",
    "Improved Frost Resistance +2",
    "Improved Madness Resistance +1",
    "Improved Madness Resistance +2",
    # Utility (higher tiers)
    "Partial HP Restoration upon Post-Damage Attacks +1",
    "Partial HP Restoration upon Post-Damage Attacks +2",
    "Successful guarding fills more of the Art gauge +1",
    "Critical hits fill more of the Art gauge +1",
    "Physical attack power increases after using grease items +1",
    "Physical attack power increases after using grease items +2",
    "Improved Guard Counters +1",
    # NOTE: appears twice in source (same name, +1 tier) — one entry kept
    "Defeating enemies fills more of the Art gauge +1",
    "HP Restoration upon Thrusting Counterattack +1",
    "Attack power up when facing poison-afflicted enemy +1",
    "Attack power up when facing poison-afflicted enemy +2",
    "Attack power up when facing scarlet rot-afflicted enemy +1",
    "Attack power up when facing scarlet rot-afflicted enemy +2",
    "Attack power up when facing frostbite-afflicted enemy +1",
    "Attack power up when facing frostbite-afflicted enemy +2",
    "Sleep in Vicinity Improves Attack Power +1",
    "Madness in Vicinity Improves Attack Power +1",
    # Max resource (stackable — Category 6)
    "Increased Maximum HP",
    "Increased Maximum FP",
    "Increased Maximum Stamina",
    # Affinity (higher tiers, available in deep)
    "Improved Affinity Attack Power +1",
    "Improved Affinity Attack Power +2",
    # Damage negation (higher tiers)
    "Improved Physical Damage Negation +1",
    "Improved Physical Damage Negation +2",
    "Improved Affinity Damage Negation +1",
    "Improved Affinity Damage Negation +2",
    # Spell type (higher tiers)
    "Improved Sorceries +1",
    "Improved Sorceries +2",
    "Improved Incantations +1",
    "Improved Incantations +2",
]

# Effects available in the 2100000 deep relic pool (broader set)
POOL_2100000 = [
    # Stats
    "Poise +3",
    "Physical Attack Up +2",
    "Magic Attack Power Up +2",
    "Fire Attack Power Up +2",
    "Lightning Attack Power Up +2",
    "Holy Attack Power Up +2",
    # Damage negation (base tiers)
    "Magic Damage Negation Up",
    "Fire Damage Negation Up",
    "Lightning Damage Negation Up",
    "Holy Damage Negation Up",
    # Status resistances (base tiers)
    "Improved Poison Resistance",
    "Improved Blood Loss Resistance",
    "Improved Sleep Resistance",
    "Improved Death Blight Resistance",
    "Improved Rot Resistance",
    "Improved Frost Resistance",
    "Improved Madness Resistance",
    # HP/healing
    "Partial HP Restoration upon Post-Damage Attacks",
    "Flask Also Heals Allies",
    "Slowly restore HP for self and nearby allies when HP is low",
    "Improved Damage Negation at Low HP",
    "HP restored when using medicinal boluses, etc.",
    # Art gauge / combat
    "Successful guarding fills more of the Art gauge",
    "Draw enemy attention while guarding",
    "Critical hits fill more of the Art gauge",
    "Physical attack power increases after using grease items",
    "Critical Hits Earn Runes",
    "Critical Hit Boosts Stamina Recovery Speed",
    "HP Recovery From Successful Guarding",
    "Improved Initial Standard Attack",
    "Improved Guard Counters",
    "Improved Critical Hits",
    # Throwing / special attacks
    "Improved Throwing Pot Damage",
    "Improved Throwing Knife Damage",
    "Improved Glintstone and Gravity Stone Damage",
    "Improved Perfuming Arts",
    # School-specific sorceries
    "Improved Stonedigger Sorcery",
    "Improved Carian Sword Sorcery",
    "Improved Glintblade Sorcery",
    "Improved Invisibility Sorcery",
    "Improved Crystalian Sorcery",
    "Improved Gravity Sorcery",
    "Improved Thorn Sorcery",
    # School-specific incantations
    "Improved Fundamentalist Incantations",
    "Improved Dragon Cult Incantations",
    "Improved Giants' Flame Incantations",
    "Improved Godslayer Incantations",
    "Improved Bestial Incantations",
    "Improved Frenzied Flame Incantations",
    "Improved Dragon Communion Incantations",
    # Ally/team effects
    "Raised stamina recovery for nearby allies, but not for self",
    "Items confer effect to all nearby allies",
    # Utility
    "Treasure marked upon map",
    # Triple-equip bonuses (weapon classes)
    "Improved Attack Power with 3+ [Weapons] Equipped",  # generic display name
    "Max FP Up with 3+ Staves Equipped",
    "Max FP Up with 3+ Sacred Seals Equipped",
    "Max HP Up with 3+ Small Shields Equipped",
    "Max HP Up with 3+ Medium Shields Equipped",
    "Max HP Up with 3+ Greatshields Equipped",
    # Art gauge
    "Defeating enemies fills more of the Art gauge",
    "Defeating enemies restores HP for allies but not for self",
    # Stamina
    "Stamina Recovery upon Landing Attacks",
    # Runes
    "Increased rune acquisition for self and allies",
    # Starting items
    "Stonesword Key in possession at start of expedition",
    "Small Pouch in possession at start of expedition",
    # Guard
    "Guard counter is given a boost based on current HP",
    "HP Restoration upon Thrusting Counterattack",
    # Shop
    "Rune discount for shop purchases while on expedition",
    "Improved Poise & Damage Negation When Knocked Back by Damage",
    # Status-conditional attack
    "Attack power up when facing poison-afflicted enemy",
    "Attack power up when facing scarlet rot-afflicted enemy",
    "Attack power up when facing frostbite-afflicted enemy",
    # Weapon-class attack power (generic display)
    "Improved [Weapon] Attack Power",
    # Weapon-class on-hit effects (generic display)
    "HP Restoration upon [Weapon Attacks]",
    "FP Restoration upon [Weapon Attacks]",
    # Deep relic higher-tier stackables
    "HP restored when using medicinal boluses, etc. +1",
    "Critical Hit Boosts Stamina Recovery Speed +1",
    "Improved Throwing Pot Damage +1",
    "Improved Throwing Knife Damage +1",
    "Improved Glintstone and Gravity Stone Damage +1",
    "Improved Perfuming Arts +1",
    # Expedition scaling (per great enemy defeated)
    "Max HP increased for each great enemy defeated at a Great Church",
    "Runes and Item Discovery increased for each great enemy defeated at a Fort",
    "Arcane increased for each great enemy defeated at a Ruin",
    "Max stamina increased for each great enemy defeated at a Great Encampment",
    # Character-specific (Deep version)
    "[Wylder] Character Skill inflicts Blood Loss",
    "[Guardian] Character Skill Boosts Damage Negation of Nearby Allies",
    "[Ironeye] Character Skill Inflicts Heavy Poison Damage on Poisoned Enemies",
    "[Duchess] Use Character Skill for Brief Invulnerability",
    "[Raider] Hit With Character Skill to Reduce Enemy Attack Power",
    "[Revenant] Increased Max FP upon Ability Activation",
    "[Recluse] Collect Affinity Residues to Negate Affinity",
    "[Executor] Slowly Restore HP upon Ability Activation",
    # Sleep/madness vicinity
    "Sleep in Vicinity Improves Attack Power",
    "Madness in Vicinity Improves Attack Power",
    # Resource management
    "Reduced FP Consumption",
    "Improved Affinity Attack Power",
    "Improved Affinity Damage Negation",
    "Improved Sorceries",
    "Improved Incantations",
    "Improved Flask HP Restoration",
    # Tears (starting item)
    "[Tear item] in possession at start of expedition",
    # Dormant Powers
    "Dormant Power Helps Discover [Weapons]",
    # Character-specific demerits / stat swaps
    "[Wylder] Improved Mind, Reduced Vigor",
    "[Wylder] Improved Intelligence and Faith, Reduced Strength and Dexterity",
    "[Guardian] Improved Strength and Dexterity, Reduced Vigor",
    "[Guardian] Improved Mind and Faith, Reduced Vigor",
    "[Ironeye] Improved Arcane, Reduced Dexterity",
    "[Ironeye] Improved Vigor and Strength, Reduced Dexterity",
    "[Duchess] Improved Vigor and Strength, Reduced Mind",
    "[Duchess] Improved Mind and Faith, Reduced Intelligence",
    "[Raider] Improved Mind and Intelligence, Reduced Vigor and Endurance",
    "[Raider] Improved Arcane, Reduced Vigor",
    "[Revenant] Improved Vigor and Endurance, Reduced Mind",
    "[Revenant] Improved Strength, Reduced Faith",
    "[Recluse] Improved Vigor, Endurance, and Dexterity, Reduced Intelligence and Faith",
    "[Recluse] Improved Intelligence and Faith, Reduced Mind",
    "[Executor] Improved Vigor and Endurance, Reduced Arcane",
    "[Executor] Improved Dexterity and Arcane, Reduced Vigor",
]

# ─────────────────────────────────────────────────────────────────────────────
# DEEP RELIC STACKABILITY CATEGORIES
# Source: "deep relic stackability.txt"
# Effects in the same category CANNOT appear on the same relic.
# Category 6 is the exception — ALL Cat 6 effects freely stack with anything.
# ─────────────────────────────────────────────────────────────────────────────

# Category 1 — Attack Power (maps to compatibility Group 100)
DEEP_CAT_1_ATTACK_POWER = [
    "Physical Attack Up +3",
    "Physical Attack Up +4",
    "Physical Attack Up +2",    # also in this pool
    "Magic Attack Power Up +2",
    "Magic Attack Power Up +3",
    "Magic Attack Power Up +4",
    "Fire Attack Power Up +2",
    "Fire Attack Power Up +3",
    "Fire Attack Power Up +4",
    "Lightning Attack Power Up +2",
    "Lightning Attack Power Up +3",
    "Lightning Attack Power Up +4",
    "Holy Attack Power Up +2",
    "Holy Attack Power Up +3",
    "Holy Attack Power Up +4",
    "Physical attack power increases after using grease items +1",
    "Physical attack power increases after using grease items +2",
    "Improved Guard Counters +1",
    "Sleep in Vicinity Improves Attack Power",
    "Sleep in Vicinity Improves Attack Power +1",
    "Madness in Vicinity Improves Attack Power",
    "Madness in Vicinity Improves Attack Power +1",
    "Improved Affinity Attack Power",
    "Improved Affinity Attack Power +1",
    "Improved Affinity Attack Power +2",
    "Improved Sorceries",
    "Improved Sorceries +1",
    "Improved Sorceries +2",
    "Improved Incantations",
    "Improved Incantations +1",
    "Improved Incantations +2",
]

# Category 2 — Character Specific
DEEP_CAT_2_CHARACTER = [
    # Character ability modifiers
    "[Wylder] Character Skill inflicts Blood Loss",
    "[Guardian] Character Skill Boosts Damage Negation of Nearby Allies",
    "[Ironeye] Character Skill Inflicts Heavy Poison Damage on Poisoned Enemies",
    "[Duchess] Use Character Skill for Brief Invulnerability",
    "[Raider] Hit With Character Skill to Reduce Enemy Attack Power",
    "[Revenant] Increased Max FP upon Ability Activation",
    "[Recluse] Collect Affinity Residues to Negate Affinity",
    "[Executor] Slowly Restore HP upon Ability Activation",
    # Character stat swap demerits
    "[Wylder] Improved Mind, Reduced Vigor",
    "[Wylder] Improved Intelligence and Faith, Reduced Strength and Dexterity",
    "[Guardian] Improved Strength and Dexterity, Reduced Vigor",
    "[Guardian] Improved Mind and Faith, Reduced Vigor",
    "[Ironeye] Improved Arcane, Reduced Dexterity",
    "[Ironeye] Improved Vigor and Strength, Reduced Dexterity",
    "[Duchess] Improved Vigor and Strength, Reduced Mind",
    "[Duchess] Improved Mind and Faith, Reduced Intelligence",
    "[Raider] Improved Mind and Intelligence, Reduced Vigor and Endurance",
    "[Raider] Improved Arcane, Reduced Vigor",
    "[Revenant] Improved Vigor and Endurance, Reduced Mind",
    "[Revenant] Improved Strength, Reduced Faith",
    "[Recluse] Improved Vigor, Endurance, and Dexterity, Reduced Intelligence and Faith",
    "[Recluse] Improved Intelligence and Faith, Reduced Mind",
    "[Executor] Improved Vigor and Endurance, Reduced Arcane",
    "[Executor] Improved Dexterity and Arcane, Reduced Vigor",
]

# Category 3 — Aromatics (starting item: aromatic-type)
DEEP_CAT_3_AROMATICS = [
    "[Aromatic] in possession at start of expedition",
]

# Category 4 — Tears (starting item: flask tear-type)
DEEP_CAT_4_TEARS = [
    "[Tear item] in possession at start of expedition",
]

# Category 5 — Dormant Powers
DEEP_CAT_5_DORMANT = [
    "Dormant Power Helps Discover [Weapons]",  # generic for all weapon types
]

# Category 6 — Stackable (CAN appear alongside any other category, including each other)
# These have non-(-1) exclusivityId values in the param data.
DEEP_CAT_6_STACKABLE = [
    # Max resource
    "Increased Maximum HP",
    "Increased Maximum FP",
    "Increased Maximum Stamina",
    # Expedition scaling
    "Max HP increased for each great enemy defeated at a Great Church",
    "Runes and Item Discovery increased for each great enemy defeated at a Fort",
    "Arcane increased for each great enemy defeated at a Ruin",
    "Max stamina increased for each great enemy defeated at a Great Encampment",
    # Damage negation
    "Improved Magic Damage Negation +1",
    "Improved Magic Damage Negation +2",
    "Improved Fire Damage Negation +1",
    "Improved Fire Damage Negation +2",
    "Improved Lightning Damage Negation +1",
    "Improved Lightning Damage Negation +2",
    "Improved Holy Damage Negation +1",
    "Improved Holy Damage Negation +2",
    "Improved Physical Damage Negation +1",
    "Improved Physical Damage Negation +2",
    "Improved Affinity Damage Negation +1",
    "Improved Affinity Damage Negation +2",
    # Status resistances
    "Improved Poison Resistance +1",
    "Improved Poison Resistance +2",
    "Improved Blood Loss Resistance +1",
    "Improved Blood Loss Resistance +2",
    "Improved Sleep Resistance +1",
    "Improved Sleep Resistance +2",
    "Improved Death Blight Resistance +1",
    "Improved Death Blight Resistance +2",
    "Improved Rot Resistance +1",
    "Improved Rot Resistance +2",
    "Improved Frost Resistance +1",
    "Improved Frost Resistance +2",
    "Improved Madness Resistance +1",
    "Improved Madness Resistance +2",
    # HP restoration
    "Partial HP Restoration upon Post-Damage Attacks +1",
    "Partial HP Restoration upon Post-Damage Attacks +2",
    "HP restored when using medicinal boluses, etc. +1",
    # Art gauge
    "Successful guarding fills more of the Art gauge +1",
    "Critical hits fill more of the Art gauge +1",
    # Combat
    "Critical Hit Boosts Stamina Recovery Speed +1",
    # Throwables / special
    "Improved Throwing Pot Damage +1",
    "Improved Throwing Knife Damage +1",
    "Improved Glintstone and Gravity Stone Damage +1",
    "Improved Perfuming Arts +1",
    # Status-conditional attack (note: poison-afflicted and rot-afflicted CANNOT coexist)
    "Attack power up when facing poison-afflicted enemy +1",
    "Attack power up when facing poison-afflicted enemy +2",
    "Attack power up when facing scarlet rot-afflicted enemy +1",
    "Attack power up when facing scarlet rot-afflicted enemy +2",
    "Attack power up when facing frostbite-afflicted enemy +1",
    "Attack power up when facing frostbite-afflicted enemy +2",
    # Flask / resource
    "Reduced FP Consumption",
    "Improved Flask HP Restoration",
    # Art gauge on kill
    "Defeating enemies fills more of the Art gauge +1",
    # Stamina
    "Stamina Recovery upon Landing Attacks +1",
]

# Special note from source: within Cat 6, the poison-afflicted and
# rot-afflicted attack power passives CANNOT appear on the same relic,
# even though both are Cat 6. Everything else in Cat 6 can freely stack.
CAT_6_INTERNAL_CONFLICTS = [
    ("Attack power up when facing poison-afflicted enemy +1",
     "Attack power up when facing scarlet rot-afflicted enemy +1"),
    ("Attack power up when facing poison-afflicted enemy +2",
     "Attack power up when facing scarlet rot-afflicted enemy +2"),
    ("Attack power up when facing poison-afflicted enemy +1",
     "Attack power up when facing scarlet rot-afflicted enemy +2"),
    ("Attack power up when facing poison-afflicted enemy +2",
     "Attack power up when facing scarlet rot-afflicted enemy +1"),
]

DEEP_CATEGORIES = {
    1: DEEP_CAT_1_ATTACK_POWER,
    2: DEEP_CAT_2_CHARACTER,
    3: DEEP_CAT_3_AROMATICS,
    4: DEEP_CAT_4_TEARS,
    5: DEEP_CAT_5_DORMANT,
    6: DEEP_CAT_6_STACKABLE,
}

_DEEP_CAT_LOOKUP: dict[str, int] = {}
for _cat_num, _passives in DEEP_CATEGORIES.items():
    for _p in _passives:
        _DEEP_CAT_LOOKUP[_p] = _cat_num


def get_deep_category(passive_name: str) -> int | None:
    """Return the deep relic category (1-6) for a passive, or None if unknown."""
    return _DEEP_CAT_LOOKUP.get(passive_name)


def are_deep_compatible(passive_a: str, passive_b: str) -> bool:
    """
    Returns True if two passives can coexist on a Deep of Night relic.
    Category 6 passives are always compatible (except the poison/rot conflict).
    """
    cat_a = get_deep_category(passive_a)
    cat_b = get_deep_category(passive_b)
    # If either is unknown, assume compatible
    if cat_a is None or cat_b is None:
        return True
    # Category 6 stacks freely (except internal conflicts)
    if cat_a == 6 and cat_b == 6:
        return (passive_a, passive_b) not in CAT_6_INTERNAL_CONFLICTS and \
               (passive_b, passive_a) not in CAT_6_INTERNAL_CONFLICTS
    # Category 6 can coexist with any other category
    if cat_a == 6 or cat_b == 6:
        return True
    # Same category = conflict
    return cat_a != cat_b
