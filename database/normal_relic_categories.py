"""
Normal Relic Category System (Purchasable / Rolledable Relics)
==============================================================
Source: Relics.pdf (community data), cross-referenced with AttachEffectParam.csv
Data-mined: 2026-03-25

Normal purchasable relics have 19 categories.
"Relics in the same category can only appear once." (Category 19 is the exception.)

Categories 1-18 are mutually exclusive within themselves.
Categories from DIFFERENT numbers CAN coexist on the same relic.
Category 19 is the "Unique Stackable" group — these CAN appear alongside any other category.

This maps to the compatibilityId system in the param data:
  Category  1  → compatibilityId 100   (general attack boosters)
  Category  2  → compatibilityId 200   (starting armament imbue)
  Category  3  → compatibilityId 300   (starting armament skill/spell)
  Category  4  → compatibilityId 800   (school-specific spell boosters)
  Category  5  → compatibilityId 900   (character-specific passives)
  Categories 6-16 → per-stat groups  (each stat has its own compatibilityId)
  Category 17a → compatibilityId 7340000  (HP restoration on weapon attacks)
  Category 17b → compatibilityId 7350000  (FP restoration on weapon attacks)
  Category 18  → each element/status has its own group
  Category 19  → no exclusivity (free stacking, but each passive unique)

KEY INSIGHT: Categories 1 and 4 are different numbers, meaning
  Physical Attack Up (Cat 1) + Improved Dragon Cult Incantations (Cat 4) = VALID ✓
  Improved Incantations (Cat 1) + Improved Dragon Cult Incantations (Cat 4) = VALID ✓
  Physical Attack Up (Cat 1) + Improved Incantations (Cat 1) = INVALID ✗
  Improved Dragon Cult Incantations (Cat 4) + Improved Giants' Flame (Cat 4) = INVALID ✗

IMPORTANT: "Improved Affinity Attack Power", "Improved Sorceries", "Improved Incantations"
  (base tier) do NOT appear on normal purchasable relics.
  They are Deep of Night relic exclusives (table 2100000, base tier).
  Higher tiers (+1, +2) are also Deep of Night exclusive (table 2000000).

NOTE ON DEEP RELIC CATEGORIES: The Deep of Night system uses different category numbers
  (see deep_relic_data.py) but the underlying exclusivity mechanics are the same.
"""

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 1 — General Attack Boosters
# Corresponds to compatibilityId = 100 in AttachEffectParam
# One per relic. All passives listed here are mutually exclusive.
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_1_ATTACK = [
    # Elemental attack up (base to +2 available on normal relics)
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
    # Conditional / technique attack boosters
    "Physical attack power increases after using grease items",
    "Taking attacks improves attack power",
    "Improved Initial Standard Attack",
    "Improved Guard Counters",
    "Improved Critical Hits",
    "Improved Roar & Breath Attacks",
    "Guard counter is given a boost based on current HP",
    "Improved Stance-Breaking when Two-Handing",
    "Improved Stance-Breaking when Wielding Two Armaments",
    "Attack power increased for each evergaol prisoner defeated",
    "Attack power increased for each Night Invader defeated",
    # Weapon-class specific attack power (all in Cat 1, all mutually exclusive)
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
    # Triple-equip attack power (all in Cat 1, all mutually exclusive)
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
# CATEGORY 2 — Starting Armament Imbue
# Corresponds to compatibilityId = 200
# Only one imbue type per relic. Note: Recluse cannot use these.
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_2_IMBUE = [
    "Starting armament deals magic damage",
    "Starting armament deals fire damage",
    "Starting armament deals lightning damage",
    "Starting armament deals holy damage",
    "Starting armament inflicts frost",
    "Starting armament inflicts poison",
    "Starting armament inflicts blood loss",
]

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 3 — Starting Armament Skill / Spell
# Corresponds to compatibilityId = 300
# Only one skill/spell change per relic.
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_3_SKILLS = [
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
    # Sorceries (only accessible via table 110)
    "Changes compatible armament's sorcery to Magic Glintblade at start of expedition",
    "Changes compatible armament's sorcery to Carian Greatsword at start of expedition",
    "Changes compatible armament's sorcery to Night Shard at start of expedition",
    "Changes compatible armament's sorcery to Magma Shot at start of expedition",
    "Changes compatible armament's sorcery to Briars of Punishment at start of expedition",
    # Incantations (Revenant only)
    "Changes compatible armament's incantation to Wrath of Gold at start of expedition",
    "Changes compatible armament's incantation to Lightning Spear at start of expedition",
    "Changes compatible armament's incantation to O, Flame! at start of expedition",
    "Changes compatible armament's incantation to Beast Claw at start of expedition",
    "Changes compatible armament's incantation to Dragonfire at start of expedition",
]

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 4 — School-Specific Spell Boosters
# Corresponds to compatibilityId = 800
# One per relic. CAN coexist with Category 1.
# Sorcery school boosters and incantation school boosters are in the SAME category.
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_4_SCHOOL_BOOSTERS = [
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
# CATEGORY 5 — Character-Specific Passives
# Corresponds to compatibilityId = 900 (character-specific "fixed" passives)
# One per relic. Each passive restricts to one or two characters.
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_5_CHARACTER = [
    # Wylder
    "[Wylder] Art activation spreads fire in area",
    "[Wylder] Standard attacks enhanced with fiery follow-ups when using Character Skill (greatsword only)",
    "[Wylder] Art gauge greatly filled when ability is activated",
    "[Wylder] +1 additional Character Skill use",
    # Guardian
    "[Guardian] Increased duration for Character Skill",
    "[Guardian] Creates whirlwind when charging halberd attacks",
    "[Guardian] Slowly restores nearby allies' HP while Art is active",
    "[Guardian] Successful guards send out shockwaves while ability is active",
    # Ironeye
    "[Ironeye] Art Charge Activation Adds Poison Effect",
    "[Ironeye] Boosts thrusting counterattacks after executing Art",
    "[Ironeye] +1 additional Character Skill use",
    "[Ironeye] Extends duration of weak point",
    # Duchess
    "[Duchess] Reprise events upon nearby enemies by landing the final blow of a chain attack with dagger",
    "[Duchess] Become difficult to spot and silence footsteps after landing critical from behind",
    "[Duchess] Defeating enemies while Art is active ups attack power",
    "[Duchess] Improved Character Skill Attack Power",
    "[Duchess] Use Character Skill for Brief Invulnerability",
    # Raider
    "Improved Poise Near Totem Stela",
    "[Raider] Damage taken while using Character Skill",
    "Defeating enemies near Totem Stela restores HP",
    "[Raider] Duration of Ultimate Art extended",
    # Revenant
    "[Revenant] Expend own HP to fully heal nearby allies when activating Art",
    "[Revenant] Trigger ghostflame explosion during Ultimate Art activation",
    "[Revenant] Strengthens family and allies when Ultimate Art is activated",
    "[Revenant] Power up while fighting alongside family",
    # Recluse
    "[Recluse] Collecting affinity residue activates Terra Magica",
    "[Recluse] Suffer blood loss and increase attack power upon Art activation",
    "[Recluse] Activating Ultimate Art raises Max HP",
    # Executor
    "[Executor] Roaring restores HP while Art is active",
    "[Executor] Character Skill Boosts Attack but Lowers Damage Negation While Attacking",
    "[Executor] While Character Skill is active, unlocking use of cursed sword restores HP",
    # Scholar
    "[Scholar] Prevent slowing of Character Skill progress",
    "[Scholar] Allies targeted by Character Skill gain boosted attack",
    "[Scholar] Continuous damage inflicted on targets threaded by Ultimate Art",
    "[Scholar] Earn runes for each additional specimen acquired with Character Skill",
    # Undertaker
    "[Undertaker] Activating Ultimate Art increases attack power",
    "[Undertaker] Attack power increased by landing the final blow of a chain attack",
    "[Undertaker] Physical attacks boosted while assist effect from incantation is active for self",
    "[Undertaker] Contact with allies restores their HP while Ultimate Art is activated",
]

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORIES 6-16 — Stat Passives (each stat is its own sub-category)
# Each stat group is internally exclusive (can't have Vigor +1 AND Vigor +2).
# Stats from different groups CAN coexist (Vigor +3 + Mind +3 is valid).
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_STATS = {
    "vigor":          ["Vigor +1", "Vigor +2", "Vigor +3"],
    "mind":           ["Mind +1", "Mind +2", "Mind +3"],
    "endurance":      ["Endurance +1", "Endurance +2", "Endurance +3"],
    "strength":       ["Strength +1", "Strength +2", "Strength +3"],
    "dexterity":      ["Dexterity +1", "Dexterity +2", "Dexterity +3"],
    "intelligence":   ["Intelligence +1", "Intelligence +2", "Intelligence +3"],
    "faith":          ["Faith +1", "Faith +2", "Faith +3"],
    "arcane":         ["Arcane +1", "Arcane +2", "Arcane +3"],
    "poise":          ["Poise +1", "Poise +2", "Poise +3"],
    "skill_cooldown": [
        "Character Skill Cooldown Reduction +1",
        "Character Skill Cooldown Reduction +2",
        "Character Skill Cooldown Reduction +3",
    ],
    "art_gauge":      [
        "Ultimate Art Auto Charge +1",
        "Ultimate Art Auto Charge +2",
        "Ultimate Art Auto Charge +3",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 17 — Weapon Attack On-Hit Restoration
# Two sub-categories (HP and FP are in separate internal groups):
#   17a: HP Restoration upon [Weapon] Attacks — pick one weapon type
#   17b: FP Restoration upon [Weapon] Attacks — pick one weapon type
# HP and FP on-hit CAN coexist with each other.
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_17A_HP_ON_WEAPON = [
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

CATEGORY_17B_FP_ON_WEAPON = [
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

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 18 — Damage Negation & Status Resistance
# Each element/status type is its own internal sub-group.
# Different elements CAN coexist (Lightning Negation + Poison Resistance is valid).
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_18_NEGATION = {
    "magic_negation":       ["Magic Damage Negation Up"],
    "fire_negation":        ["Fire Damage Negation Up"],
    "lightning_negation":   ["Lightning Damage Negation Up"],
    "holy_negation":        ["Holy Damage Negation Up"],
    "physical_negation":    ["Improved Physical Damage Negation"],
    "poison_resistance":    ["Improved Poison Resistance"],
    "bleed_resistance":     ["Improved Blood Loss Resistance"],
    "sleep_resistance":     ["Improved Sleep Resistance"],
    "blight_resistance":    ["Improved Death Blight Resistance"],
    "rot_resistance":       ["Improved Rot Resistance"],
    "frost_resistance":     ["Improved Frost Resistance"],
    "madness_resistance":   ["Improved Madness Resistance"],
}

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 19 — Unique Stackable Relics
# These CAN appear alongside passives from any other category.
# Each of these is still unique on a single relic (you won't get two copies of
# the same Category 19 passive), but they don't block any other slot.
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_19_STACKABLE = [
    # Max resource
    "Increased Maximum HP",
    "Increased Maximum FP",
    "Increased Maximum Stamina",
    # HP restoration
    "Partial HP Restoration upon Post-Damage Attacks",
    "Slowly restore HP for self and nearby allies when HP is low",
    "Improved Damage Negation at Low HP",
    "HP restored when using medicinal boluses, etc.",
    "HP Recovery From Successful Guarding",
    # Art gauge / combat utility
    "Successful guarding fills more of the Art gauge",
    "Critical hits fill more of the Art gauge",
    "Defeating enemies fills more of the Art gauge",
    "Defeating enemies restores HP for allies but not for self",
    "FP Restoration upon Successive Attacks",
    "Critical Hits Earn Runes",
    "Critical Hit Boosts Stamina Recovery Speed",
    "Draw enemy attention while guarding",
    # Stamina
    "Stamina Recovery upon Landing Attacks",
    "Raised stamina recovery for nearby allies, but not for self",
    # Affinity / elemental switch
    "Switching Weapons Adds an Affinity Attack",
    "Boosts Attack Power of Added Affinity Attacks",
    # Throwables / consumable damage
    "Improved Throwing Pot Damage",
    "Improved Throwing Knife Damage",
    "Improved Glintstone and Gravity Stone Damage",
    "Improved Perfuming Arts",
    # Conditional attack
    "Attack power up when facing poison-afflicted enemy",
    "Attack power up when facing scarlet rot-afflicted enemy",
    "Attack power up when facing frostbite-afflicted enemy",
    # Status / madness synergies
    'Gesture "Crossed Legs" Builds Up Madness',
    "Madness Continually Recovers FP",
    "Frostbite in Vicinity Conceals Self",
    "Poison & Rot in Vicinity Increases Attack Power",
    # Team effects
    "Flask Also Heals Allies",
    "Items confer effect to all nearby allies",
    # Utility
    "Treasure marked upon map",
    "HP Restoration upon Thrusting Counterattack",
    "Rune discount for shop purchases while on expedition",
    "Huge rune discount for shop purchases while on expedition",
    "Increased rune acquisition for self and allies",
    "Improved Poise & Damage Negation When Knocked Back by Damage",
    "Max FP increased for each Sorcerer's Rise unlocked",
    # Triple-equip FP/HP (shields/staves)
    "Max FP Up with 3+ Staves Equipped",
    "Max FP Up with 3+ Sacred Seals Equipped",
    "Max HP Up with 3+ Small Shields Equipped",
    "Max HP Up with 3+ Medium Shields Equipped",
    "Max HP Up with 3+ Greatshields Equipped",
    # Starting items (Stonesword Key, Pouch, Pots, etc.)
    "Stonesword Key in possession at start of expedition",
    "Small Pouch in possession at start of expedition",
    "Fire Pots in possession at start of expedition",
    "Magic Pots in possession at start of expedition",
    "Lightning Pots in possession at start of expedition",
    "Holy Water Pots in possession at start of expedition",
    "Poisonbone Darts in possession at start of expedition",
    "Crystal Darts in possession at start of expedition",
    "Throwing Daggers in possession at start of expedition",
    "Glintstone Scraps in possession at start of expedition",
    "Gravity Stone Chunks in possession at start of expedition",
    "Bewitching Branches in possession at start of expedition",
    "Wraith Calling Bell in possession at start of expedition",
    "Fire Grease in possession at start of expedition",
    "Magic Grease in possession at start of expedition",
    "Lightning Grease in possession at start of expedition",
    "Holy Grease in possession at start of expedition",
    "Shield Grease in possession at start of expedition",
    "Starlight Shards in possession at start of expedition",
]

# ─────────────────────────────────────────────────────────────────────────────
# UNROLLABLE RELICS (special fixed-passive relics found in-world, not purchasable)
# These have fixed passives and some passives listed here don't appear in the
# normal random relic pools at all.
# ─────────────────────────────────────────────────────────────────────────────

UNROLLABLE_SPECIAL = [
    # These appear on special in-world relics (isSalable=0 in EquipParamAntique)
    "Switching Weapons Boosts Attack Power",
    # NOTE: Many of the regular passives also appear on special relics —
    # the above are ones that ONLY appear on special non-purchasable relics.
]

# ─────────────────────────────────────────────────────────────────────────────
# POOL AVAILABILITY
# Which passives appear on which relic tiers
# "Delicate" = 1-slot normal relic (pool tables 100/110)
# "Polished" = 2-slot normal relic (pool tables 200/210)
# "Grand" = 3-slot normal relic (pool tables 300/310)
# ─────────────────────────────────────────────────────────────────────────────

# Passives NOT available on normal relics (Deep of Night only)
DEEP_ONLY_PASSIVES = [
    "Improved Affinity Attack Power",
    "Improved Affinity Attack Power +1",
    "Improved Affinity Attack Power +2",
    "Improved Sorceries",
    "Improved Sorceries +1",
    "Improved Sorceries +2",
    "Improved Incantations",
    "Improved Incantations +1",
    "Improved Incantations +2",
    "Sleep in Vicinity Improves Attack Power",
    "Sleep in Vicinity Improves Attack Power +1",
    "Madness in Vicinity Improves Attack Power",
    "Madness in Vicinity Improves Attack Power +1",
    # Higher attack tiers
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
]

# ─────────────────────────────────────────────────────────────────────────────
# POOL WEIGHTS SUMMARY (from AttachEffectTableParam.csv)
# These are relative weights for rolling a given passive on a relic.
# Higher weight = more common. Total weight pool determines actual probability.
#
# Delicate (1-slot) pool weights (table 100/110):
#   Stats (+1/+2/+3):               52  (equal across tiers)
#   Ability passives (cooldown, art, poise):  47
#   Attack power passives:           47
#   Damage negation / resistances:   47
#   HP/utility misc passives:        46
#   School-specific spells (Cat 4):  39
#   Starting imbue passives (Cat 2): 37
#   Starting skill passives (Cat 3): 37
#   Sorcery/incantation spells (110 only): 20 (rare)
#   Dormant Power (110 only):        4  (very rare)
#   Character-specific (Cat 5):      67 (table 100), 53 (table 110)
#   Weapon-class attack / 3x-equip:  10 (rare)
#   HP/FP on weapon attack (Cat 17): 10 (rare)
#
# Polished (2-slot) pool weights (table 200/210):
#   Stats +1:                        47  (lower than Delicate)
#   Stats +2/+3:                     72  (higher than Delicate)
#   Attack power (base tier):        42
#   Attack power (+1/+2 tiers):      67  (much higher than Delicate)
#   Character-specific (Cat 5):      67
# ─────────────────────────────────────────────────────────────────────────────

WEIGHT_BY_TIER_DELICATE = {
    "stat_passives": 52,
    "ability_passives": 47,
    "attack_power_passives": 47,
    "damage_negation": 47,
    "utility_misc": 46,
    "school_spell_boosters": 39,
    "starting_imbue": 37,
    "starting_skill_change": 37,
    "sorcery_incantation_spell": 20,
    "dormant_power": 4,
    "character_specific_t100": 67,
    "character_specific_t110": 53,
    "weapon_class_attack": 10,
    "hp_fp_on_weapon": 10,
}

WEIGHT_BY_TIER_POLISHED = {
    "stat_tier1": 47,
    "stat_tier2_3": 72,
    "attack_power_base": 42,
    "attack_power_tier1_2": 67,
    "character_specific": 67,
}
