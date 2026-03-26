"""
Relic Passive Compatibility Groups
===================================
Source: AttachEffectParam.csv (Smithbox export), "deep relic stackability.txt"
Data-mined: 2026-03-25

KEY MECHANIC: The `compatibilityId` field in AttachEffectParam determines mutual exclusion.
Passives that share the same compatibilityId CANNOT appear on the same relic.
Two passives with DIFFERENT compatibilityIds CAN coexist (subject to slot count).

The two most important groups are 100 and 800 — they CAN coexist with each other.

GROUP 100  — "Direct Attack Boosters"
  All passives that directly boost damage output in some general way.
  CANNOT appear together. One per relic maximum.

GROUP 800  — "School-Specific Spell Boosters"
  All passives that boost a specific sorcery or incantation school.
  CANNOT appear together. One per relic maximum.
  CAN coexist with one passive from Group 100.

Example valid combination:
  Lightning Attack Power Up (Group 100) + Improved Dragon Cult Incantations (Group 800) ✓

Example invalid combinations:
  Improved Incantations (Group 100) + Lightning Attack Power Up (Group 100) ✗
  Improved Dragon Cult Incantations (Group 800) + Improved Giants' Flame Incantations (Group 800) ✗
"""

# ─────────────────────────────────────────────────────────────────────────────
# GROUP 100 — Direct Attack Boosters (all mutually exclusive)
# These include: elemental attack up, improved sorceries/incantations,
# weapon-class attack up, conditional attack boosts, stance-break boosts
# ─────────────────────────────────────────────────────────────────────────────

GROUP_100_ATTACK_BOOSTERS = [
    # Elemental / general damage up (normal tiers on standard relics)
    "Physical Attack Up",
    "Physical Attack Up +1",
    "Physical Attack Up +2",
    "Magic Attack Power Up",
    "Magic Attack Power Up +1",
    "Magic Attack Power Up +2",
    "Fire Attack Power Up",
    "Fire Attack Power Up +1",
    "Fire Attack Power Up +2",
    "Lightning Attack Power Up",
    "Lightning Attack Power Up +1",
    "Lightning Attack Power Up +2",
    "Holy Attack Power Up",
    "Holy Attack Power Up +1",
    "Holy Attack Power Up +2",
    # Deep of Night exclusive higher tiers
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
    # Affinity (all tiers — available in deep)
    "Improved Affinity Attack Power",
    "Improved Affinity Attack Power +1",
    "Improved Affinity Attack Power +2",
    # Broad spell type boosters (NOT school-specific — those are Group 800)
    "Improved Sorceries",
    "Improved Sorceries +1",
    "Improved Sorceries +2",
    "Improved Incantations",
    "Improved Incantations +1",
    "Improved Incantations +2",
    # Melee / combat technique boosters
    "Improved Initial Standard Attack",
    "Improved Guard Counters",
    "Improved Critical Hits",
    "Improved Roar & Breath Attacks",
    "Guard counter is given a boost based on current HP",
    "Improved Stance-Breaking when Two-Handing",
    "Improved Stance-Breaking when Wielding Two Armaments",
    # Conditional attack boosters
    "Physical attack power increases after using grease items",
    "Physical attack power increases after using grease items +1",
    "Physical attack power increases after using grease items +2",
    "Taking attacks improves attack power",
    "Switching Weapons Boosts Attack Power",
    "Sleep in Vicinity Improves Attack Power",
    "Sleep in Vicinity Improves Attack Power +1",
    "Madness in Vicinity Improves Attack Power",
    "Madness in Vicinity Improves Attack Power +1",
    "Attack power increased for each evergaol prisoner defeated",
    "Attack power increased for each Night Invader defeated",
    # Weapon-class specific attack power (one per relic — all in Group 100)
    "Improved Dagger Attack Power",
    "Improved Straight Sword Attack Power",
    "Improved Greatsword Attack Power",
    "Improved Colossal Sword Attack Power",
    "Improved Curved Sword Attack Power",
    "Improved Curved Greatsword Attack Power",
    "Improved Katana Attack Power",
    "Improved Twinblade Attack Power",
    "Improved Thrusting Sword Attack Power",
    "Improved Heavy Thrusting Sword Attack Power",
    "Improved Axe Attack Power",
    "Improved Greataxe Attack Power",
    "Improved Hammer Attack Power",
    "Improved Great Hammer Attack Power",
    "Improved Flail Attack Power",
    "Improved Spear Attack Power",
    "Improved Great Spear Attack Power",
    "Improved Halberd Attack Power",
    "Improved Reaper Attack Power",
    "Improved Fist Attack Power",
    "Improved Claw Attack Power",
    "Improved Whip Attack Power",
    "Improved Colossal Weapon Attack Power",
    "Improved Bow Attack Power",
    # Triple-equip attack power (all in Group 100)
    "Improved Attack Power with 3+ Daggers Equipped",
    "Improved Attack Power with 3+ Straight Swords Equipped",
    "Improved Attack Power with 3+ Greatswords Equipped",
    "Improved Attack Power with 3+ Colossal Swords Equipped",
    "Improved Attack Power with 3+ Curved Swords Equipped",
    "Improved Attack Power with 3+ Curved Greatswords Equipped",
    "Improved Attack Power with 3+ Katana Equipped",
    "Improved Attack Power with 3+ Twinblades Equipped",
    "Improved Attack Power with 3+ Thrusting Swords Equipped",
    "Improved Attack Power with 3+ Heavy Thrusting Swords Equipped",
    "Improved Attack Power with 3+ Axes Equipped",
    "Improved Attack Power with 3+ Greataxes Equipped",
    "Improved Attack Power with 3+ Hammers Equipped",
    "Improved Attack Power with 3+ Great Hammers Equipped",
    "Improved Attack Power with 3+ Flails Equipped",
    "Improved Attack Power with 3+ Spears Equipped",
    "Improved Attack Power with 3+ Great Spears Equipped",
    "Improved Attack Power with 3+ Halberds Equipped",
    "Improved Attack Power with 3+ Reapers Equipped",
    "Improved Attack Power with 3+ Fists Equipped",
    "Improved Attack Power with 3+ Claws Equipped",
    "Improved Attack Power with 3+ Whips Equipped",
    "Improved Attack Power with 3+ Colossal Weapons Equipped",
    "Improved Attack Power with 3+ Bows Equipped",
]

# ─────────────────────────────────────────────────────────────────────────────
# GROUP 800 — School-Specific Spell Boosters (all mutually exclusive)
# These CAN coexist with exactly one Group 100 passive on the same relic.
# Note: sorcery school boosters and incantation school boosters are in the
# SAME Group 800 — a sorcery school passive and incantation school passive
# are mutually exclusive with each other.
# ─────────────────────────────────────────────────────────────────────────────

GROUP_800_SCHOOL_BOOSTERS = [
    # Sorcery schools
    "Improved Stonedigger Sorcery",
    "Improved Carian Sword Sorcery",
    "Improved Glintblade Sorcery",
    "Improved Invisibility Sorcery",
    "Improved Crystalian Sorcery",
    "Improved Gravity Sorcery",
    "Improved Thorn Sorcery",
    # Incantation schools
    "Improved Fundamentalist Incantations",
    "Improved Dragon Cult Incantations",
    "Improved Giants' Flame Incantations",
    "Improved Godslayer Incantations",
    "Improved Bestial Incantations",
    "Improved Frenzied Flame Incantations",
    "Improved Dragon Communion Incantations",
]

# ─────────────────────────────────────────────────────────────────────────────
# OTHER COMPATIBILITY GROUPS
# Each group below is internally exclusive (one per relic), but
# can coexist with passives from other groups.
# ─────────────────────────────────────────────────────────────────────────────

# GROUP 200 — Starting Armament Imbue (mutually exclusive with each other)
# Source: compatibilityId = 200 in AttachEffectParam
# Note: Not available to Recluse (allowRecluse = 0)
GROUP_200_STARTING_IMBUE = [
    "Starting armament deals magic damage",
    "Starting armament deals fire damage",
    "Starting armament deals lightning damage",
    "Starting armament deals holy damage",
    "Starting armament inflicts frost",
    "Starting armament inflicts poison",
    "Starting armament inflicts blood loss",
]

# GROUP 300 — Starting Armament Skill/Spell Change (mutually exclusive)
# Source: compatibilityId = 300 in AttachEffectParam
GROUP_300_STARTING_SKILLS = [
    # Weapon skills (AoW)
    "Changes compatible armament's skill to Glintblade Phalanx at start of expedition",
    "Changes compatible armament's skill to Gravitas at start of expedition",
    "Changes compatible armament's skill to Flaming Strike at start of expedition",
    "Changes compatible armament's skill to Eruption at start of expedition",
    "Changes compatible armament's skill to Thunderbolt at start of expedition",
    "Changes compatible armament's skill to Lightning Slash at start of expedition",
    "Changes compatible armament's skill to Sacred Blade at start of expedition",
    "Changes compatible armament's skill to Prayerful Strike at start of expedition",
    "Changes compatible armament's skill to Poisonous Mist at start of expedition",
    "Changes compatible armament's skill to Poison Moth Flight at start of expedition",
    "Changes compatible armament's skill to Blood Blade at start of expedition",
    "Changes compatible armament's skill to Seppuku at start of expedition",
    "Changes compatible armament's skill to Chilling Mist at start of expedition",
    "Changes compatible armament's skill to Hoarfrost Stomp at start of expedition",
    "Changes compatible armament's skill to White Shadow's Lure at start of expedition",
    "Changes compatible armament's skill to Endure at start of expedition",
    "Changes compatible armament's skill to Quickstep at start of expedition",
    "Changes compatible armament's skill to Storm Stomp at start of expedition",
    "Changes compatible armament's skill to Determination at start of expedition",
    "Changes compatible armament's skill to Rain of Arrows at start of expedition",
    # Sorceries
    "Changes compatible armament's sorcery to Magic Glintblade at start of expedition",
    "Changes compatible armament's sorcery to Carian Greatsword at start of expedition",
    "Changes compatible armament's sorcery to Night Shard at start of expedition",
    "Changes compatible armament's sorcery to Magma Shot at start of expedition",
    "Changes compatible armament's sorcery to Briars of Punishment at start of expedition",
    # Incantations
    "Changes compatible armament's incantation to Wrath of Gold at start of expedition",
    "Changes compatible armament's incantation to Lightning Spear at start of expedition",
    "Changes compatible armament's incantation to O, Flame! at start of expedition",
    "Changes compatible armament's incantation to Beast Claw at start of expedition",
    "Changes compatible armament's incantation to Dragonfire at start of expedition",
]

# GROUP Dormant (compatibilityId = 6630000) — Dormant Power Weapon Discovery
# All Dormant Power passives are mutually exclusive with each other.
# One weapon class per relic maximum.
GROUP_DORMANT_DISCOVERY = [
    "Dormant Power Helps Discover Daggers",
    "Dormant Power Helps Discover Straight Swords",
    "Dormant Power Helps Discover Greatswords",
    "Dormant Power Helps Discover Colossal Swords",
    "Dormant Power Helps Discover Curved Swords",
    "Dormant Power Helps Discover Curved Greatswords",
    "Dormant Power Helps Discover Katana",
    "Dormant Power Helps Discover Twinblades",
    "Dormant Power Helps Discover Thrusting Swords",
    "Dormant Power Helps Discover Heavy Thrusting Swords",
    "Dormant Power Helps Discover Axes",
    "Dormant Power Helps Discover Greataxes",
    "Dormant Power Helps Discover Hammers",
    "Dormant Power Helps Discover Great Hammers",
    "Dormant Power Helps Discover Flails",
    "Dormant Power Helps Discover Spears",
    "Dormant Power Helps Discover Great Spears",
    "Dormant Power Helps Discover Halberds",
    "Dormant Power Helps Discover Reapers",
    "Dormant Power Helps Discover Fists",
    "Dormant Power Helps Discover Claws",
    "Dormant Power Helps Discover Whips",
    "Dormant Power Helps Discover Colossal Weapons",
    "Dormant Power Helps Discover Bows",
    "Dormant Power Helps Discover Greatbows",
    "Dormant Power Helps Discover Crossbows",
    "Dormant Power Helps Discover Ballistas",
    "Dormant Power Helps Discover Small Shields",
    "Dormant Power Helps Discover Medium Shields",
    "Dormant Power Helps Discover Greatshields",
    "Dormant Power Helps Discover Staves",
    "Dormant Power Helps Discover Sacred Seals",
    "Dormant Power Helps Discover Torches",
]

# Stat groups — passives within each stat group are mutually exclusive
# (e.g., can't have Vigor +1 AND Vigor +2 on the same relic)
GROUP_VIGOR = ["Vigor +1", "Vigor +2", "Vigor +3", "Increased Maximum HP"]
GROUP_MIND = ["Mind +1", "Mind +2", "Mind +3", "Increased Maximum FP"]
GROUP_ENDURANCE = ["Endurance +1", "Endurance +2", "Endurance +3", "Increased Maximum Stamina"]
GROUP_STRENGTH = ["Strength +1", "Strength +2", "Strength +3"]
GROUP_DEXTERITY = ["Dexterity +1", "Dexterity +2", "Dexterity +3"]
GROUP_INTELLIGENCE = ["Intelligence +1", "Intelligence +2", "Intelligence +3"]
GROUP_FAITH = ["Faith +1", "Faith +2", "Faith +3"]
GROUP_ARCANE = ["Arcane +1", "Arcane +2", "Arcane +3"]
GROUP_POISE = ["Poise +1", "Poise +2", "Poise +3"]
GROUP_SKILL_COOLDOWN = [
    "Character Skill Cooldown Reduction +1",
    "Character Skill Cooldown Reduction +2",
    "Character Skill Cooldown Reduction +3",
]
GROUP_ART_CHARGE = [
    "Ultimate Art Auto Charge +1",
    "Ultimate Art Auto Charge +2",
    "Ultimate Art Auto Charge +3",
]
GROUP_HP_ON_WEAPON = [
    "HP Restoration upon Dagger Attacks",
    "HP Restoration upon Straight Sword Attacks",
    "HP Restoration upon Greatsword Attacks",
    "HP Restoration upon Colossal Sword Attacks",
    "HP Restoration upon Curved Sword Attacks",
    "HP Restoration upon Curved Greatsword Attacks",
    "HP Restoration upon Katana Attacks",
    "HP Restoration upon Twinblade Attacks",
    "HP Restoration upon Thrusting Sword Attacks",
    "HP Restoration upon Heavy Thrusting Sword Attacks",
    "HP Restoration upon Axe Attacks",
    "HP Restoration upon Greataxe Attacks",
    "HP Restoration upon Hammer Attacks",
    "HP Restoration upon Great Hammer Attacks",
    "HP Restoration upon Flail Attacks",
    "HP Restoration upon Spear Attacks",
    "HP Restoration upon Great Spear Attacks",
    "HP Restoration upon Halberd Attacks",
    "HP Restoration upon Reaper Attacks",
    "HP Restoration upon Fist Attacks",
    "HP Restoration upon Claw Attacks",
    "HP Restoration upon Whip Attacks",
    "HP Restoration upon Colossal Weapon Attacks",
    "HP Restoration upon Bow Attacks",
]
GROUP_FP_ON_WEAPON = [
    "FP Restoration upon Dagger Attacks",
    "FP Restoration upon Straight Sword Attacks",
    "FP Restoration upon Greatsword Attacks",
    "FP Restoration upon Colossal Sword Attacks",
    "FP Restoration upon Curved Sword Attacks",
    "FP Restoration upon Curved Greatsword Attacks",
    "FP Restoration upon Katana Attacks",
    "FP Restoration upon Twinblade Attacks",
    "FP Restoration upon Thrusting Sword Attacks",
    "FP Restoration upon Heavy Thrusting Sword Attacks",
    "FP Restoration upon Axe Attacks",
    "FP Restoration upon Greataxe Attacks",
    "FP Restoration upon Hammer Attacks",
    "FP Restoration upon Great Hammer Attacks",
    "FP Restoration upon Flail Attacks",
    "FP Restoration upon Spear Attacks",
    "FP Restoration upon Great Spear Attacks",
    "FP Restoration upon Halberd Attacks",
    "FP Restoration upon Reaper Attacks",
    "FP Restoration upon Fist Attacks",
    "FP Restoration upon Claw Attacks",
    "FP Restoration upon Whip Attacks",
    "FP Restoration upon Colossal Weapon Attacks",
    "FP Restoration upon Bow Attacks",
]
GROUP_MAX_HP_ON_SHIELDS = [
    "Max HP Up with 3+ Small Shields Equipped",
    "Max HP Up with 3+ Medium Shields Equipped",
    "Max HP Up with 3+ Greatshields Equipped",
]
GROUP_MAX_FP_ON_CAST = [
    "Max FP Up with 3+ Staves Equipped",
    "Max FP Up with 3+ Sacred Seals Equipped",
]
GROUP_AFFINITY_NEGATION = [
    "Improved Affinity Damage Negation",
    "Improved Affinity Damage Negation +1",
    "Improved Affinity Damage Negation +2",
]

# ─────────────────────────────────────────────────────────────────────────────
# LOOKUP: given a passive name, return its compatibility group ID string
# ─────────────────────────────────────────────────────────────────────────────

def _build_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for passive in GROUP_100_ATTACK_BOOSTERS:
        lookup[passive] = "100"
    for passive in GROUP_800_SCHOOL_BOOSTERS:
        lookup[passive] = "800"
    for passive in GROUP_200_STARTING_IMBUE:
        lookup[passive] = "200"
    for passive in GROUP_300_STARTING_SKILLS:
        lookup[passive] = "300"
    for passive in GROUP_DORMANT_DISCOVERY:
        lookup[passive] = "dormant"
    for passive in GROUP_VIGOR:
        lookup[passive] = "vigor"
    for passive in GROUP_MIND:
        lookup[passive] = "mind"
    for passive in GROUP_ENDURANCE:
        lookup[passive] = "endurance"
    for passive in GROUP_STRENGTH:
        lookup[passive] = "strength"
    for passive in GROUP_DEXTERITY:
        lookup[passive] = "dexterity"
    for passive in GROUP_INTELLIGENCE:
        lookup[passive] = "intelligence"
    for passive in GROUP_FAITH:
        lookup[passive] = "faith"
    for passive in GROUP_ARCANE:
        lookup[passive] = "arcane"
    for passive in GROUP_POISE:
        lookup[passive] = "poise"
    for passive in GROUP_SKILL_COOLDOWN:
        lookup[passive] = "skill_cooldown"
    for passive in GROUP_ART_CHARGE:
        lookup[passive] = "art_charge"
    for passive in GROUP_HP_ON_WEAPON:
        lookup[passive] = "hp_on_weapon"
    for passive in GROUP_FP_ON_WEAPON:
        lookup[passive] = "fp_on_weapon"
    for passive in GROUP_MAX_HP_ON_SHIELDS:
        lookup[passive] = "max_hp_shields"
    for passive in GROUP_MAX_FP_ON_CAST:
        lookup[passive] = "max_fp_cast"
    for passive in GROUP_AFFINITY_NEGATION:
        lookup[passive] = "affinity_negation"
    return lookup


PASSIVE_COMPATIBILITY_GROUP: dict[str, str] = _build_lookup()


def get_compatibility_group(passive_name: str) -> str | None:
    """
    Return the compatibility group ID for a passive name.
    Returns None if the passive has no known group (can stack freely).

    Two passives with the same group ID cannot appear on the same relic.
    Two passives with different (non-None) group IDs CAN coexist.
    """
    return PASSIVE_COMPATIBILITY_GROUP.get(passive_name)


def are_compatible(passive_a: str, passive_b: str) -> bool:
    """
    Returns True if two passives CAN appear together on the same relic.
    Returns False if they share a compatibility group (mutually exclusive).
    """
    group_a = get_compatibility_group(passive_a)
    group_b = get_compatibility_group(passive_b)
    if group_a is None or group_b is None:
        return True  # unknown passives assumed compatible
    return group_a != group_b


def check_relic_passives(passives: list[str | None]) -> list[tuple[str, str]]:
    """
    Given a list of passive names on a relic (None = empty slot),
    return a list of (passive_a, passive_b) conflict pairs.
    Empty list = no conflicts.
    """
    filled = [p for p in passives if p is not None]
    conflicts = []
    for i in range(len(filled)):
        for j in range(i + 1, len(filled)):
            if not are_compatible(filled[i], filled[j]):
                conflicts.append((filled[i], filled[j]))
    return conflicts
