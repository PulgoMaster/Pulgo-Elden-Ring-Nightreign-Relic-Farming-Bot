# Build Advisor — Relic Recommendation Engine
# Given a weapon type, skill, or spell, recommends the best passive combination.
#
# Outputs a list of RelicHint objects sorted by priority.
# Passives tagged deep_only=True only appear on Deep of Night relics.

from __future__ import annotations
from dataclasses import dataclass, field


# =============================================================================
# OUTPUT TYPE
# =============================================================================

@dataclass
class RelicHint:
    passive: str
    reason: str
    deep_only: bool = False
    priority: int = 2        # 1 = best, 2 = good, 3 = situational/optional


# =============================================================================
# WEAPON TYPE DATA
# Class booster, dormant power, base damage type, and text aliases.
# =============================================================================

_W = {
    "Dagger":               ("Improved Dagger Attack Power",            "Dormant Power Helps Discover Daggers",             "physical"),
    "Thrusting Sword":      ("Improved Thrusting Sword Attack Power",   "Dormant Power Helps Discover Thrusting Swords",    "physical"),
    "Heavy Thrusting Sword":("Improved Heavy Thrusting Sword Attack Power","Dormant Power Helps Discover Heavy Thrusting Swords","physical"),
    "Straight Sword":       ("Improved Straight Sword Attack Power",    "Dormant Power Helps Discover Straight Swords",     "physical"),
    "Greatsword":           ("Improved Greatsword Attack Power",        "Dormant Power Helps Discover Greatswords",         "physical"),
    "Colossal Sword":       ("Improved Colossal Sword Attack Power",    "Dormant Power Helps Discover Colossal Swords",     "physical"),
    "Curved Sword":         ("Improved Curved Sword Attack Power",      "Dormant Power Helps Discover Curved Swords",       "physical"),
    "Curved Greatsword":    ("Improved Curved Greatsword Attack Power", "Dormant Power Helps Discover Curved Greatswords",  "physical"),
    "Katana":               ("Improved Katana Attack Power",            "Dormant Power Helps Discover Katana",              "physical"),
    "Twinblade":            ("Improved Twinblade Attack Power",         "Dormant Power Helps Discover Twinblades",          "physical"),
    "Axe":                  ("Improved Axe Attack Power",               "Dormant Power Helps Discover Axes",                "physical"),
    "Greataxe":             ("Improved Greataxe Attack Power",          "Dormant Power Helps Discover Greataxes",           "physical"),
    "Hammer":               ("Improved Hammer Attack Power",            "Dormant Power Helps Discover Hammers",             "physical"),
    "Flail":                ("Improved Flail Attack Power",             "Dormant Power Helps Discover Flails",              "physical"),
    "Great Hammer":         ("Improved Great Hammer Attack Power",      "Dormant Power Helps Discover Great Hammers",       "physical"),
    "Colossal Weapon":      ("Improved Colossal Weapon Attack Power",   "Dormant Power Helps Discover Colossal Weapons",    "physical"),
    "Spear":                ("Improved Spear Attack Power",             "Dormant Power Helps Discover Spears",              "physical"),
    "Great Spear":          ("Improved Great Spear Attack Power",       "Dormant Power Helps Discover Great Spears",        "physical"),
    "Halberd":              ("Improved Halberd Attack Power",           "Dormant Power Helps Discover Halberds",            "physical"),
    "Reaper":               ("Improved Reaper Attack Power",            "Dormant Power Helps Discover Reapers",             "physical"),
    "Whip":                 ("Improved Whip Attack Power",              "Dormant Power Helps Discover Whips",               "physical"),
    "Fist":                 ("Improved Fist Attack Power",              "Dormant Power Helps Discover Fists",               "physical"),
    "Claw":                 ("Improved Claw Attack Power",              "Dormant Power Helps Discover Claws",               "physical"),
    "Bow":                  ("Improved Bow Attack Power",               "Dormant Power Helps Discover Bows",                "physical"),
    # Greatbow/Crossbow/Ballista have Dormant only — no class attack booster
    "Greatbow":             (None,                                      "Dormant Power Helps Discover Greatbows",           "physical"),
    "Crossbow":             (None,                                      "Dormant Power Helps Discover Crossbows",           "physical"),
    "Ballista":             (None,                                      "Dormant Power Helps Discover Ballistas",           "physical"),
    # Catalysts
    "Glintstone Staff":     (None,                                      "Dormant Power Helps Discover Staves",              "magic"),
    "Sacred Seal":          (None,                                      "Dormant Power Helps Discover Sacred Seals",        "holy"),
}

# Best elemental attack-up passives by damage type (priority order — all are deep-only)
_ELEMENTAL_DEEP: dict[str, list[str]] = {
    "physical":  ["Physical Attack Up +4",          "Physical Attack Up +3"],
    "magic":     ["Magic Attack Power Up +4",        "Magic Attack Power Up +3"],
    "fire":      ["Fire Attack Power Up +4",         "Fire Attack Power Up +3"],
    "lightning": ["Lightning Attack Power Up +4",    "Lightning Attack Power Up +3"],
    "holy":      ["Holy Attack Power Up +4",         "Holy Attack Power Up +3"],
}

# Best normal-relic elemental attack-up (highest tier that appears in normal pools)
_ELEMENTAL_NORMAL: dict[str, str] = {
    "physical":  "Physical Attack Up +2",
    "magic":     "Magic Attack Power Up +2",
    "fire":      "Fire Attack Power Up +2",
    "lightning": "Lightning Attack Power Up +2",
    "holy":      "Holy Attack Power Up +2",
}

# Skill category → primary damage type it deals
_SKILL_CAT_DAMAGE: dict[str, str] = {
    "Standard": "physical",
    "Shield":   "physical",
    "Bow":      "physical",
    "Fire":     "fire",
    "Lightning":"lightning",
    "Holy":     "holy",
    "Magic":    "magic",
    "Frost":    "physical",   # frost status amp boosts physical-type output
    "Blood":    "physical",   # hemorrhage scales with HP, skill damage is physical
    "Poison":   "physical",   # status build, physical base
    "Specific": "physical",   # weapon-unique, usually physical unless known otherwise
    "Legendary":"physical",
}

# Override damage type for specific named skills (weapon-unique skills with known element)
_SKILL_DAMAGE_OVERRIDE: dict[str, str] = {
    "Moonlight Greatsword":     "magic",
    "Carian Grandeur":          "magic",
    "Carian Greatsword":        "magic",
    "Night-and-Flame Stance":   "magic",    # R1=magic, R2=fire; magic is primary
    "Wave of Gold":             "holy",
    "Golden Slam":              "holy",
    "Sacred Ring of Light":     "holy",
    "Miquella's Ring of Light": "holy",
    "Blade of Gold":            "holy",
    "Sacred Phalanx":           "holy",
    "Ruinous Ghostflame":       "magic",
    "Ghostflame Ignition":      "magic",
    "Gravity Bolt":             "magic",
    "Knowledge Above All":      "magic",
    "Death Flare":              "magic",
    "Nebula (Bastard's Stars)": "magic",
    "Nebula (Wing of Astel)":   "magic",
    "Thundercloud Form":        "lightning",
    "Ice Lightning Sword":      "lightning",
    "Ancient Lightning Spear":  "lightning",
    "Lansseax's Glaive":        "lightning",
    "Fortissax's Lightning Spear": "lightning",
    "Thunderstorm":             "lightning",
    "Erdtree Slam":             "holy",
    "Black Flame Tornado":      "fire",
    "The Queen's Black Flame":  "fire",
    "Magma Shower":             "fire",
    "Magma Guillotine":         "fire",
    "Sea of Magma":             "fire",
    "Taker's Flames":           "fire",
    "Fires of Slumber":         "fire",
}

# Skill name → weapon classes it can appear on (datamine-verified)
# Only skills appearing on <=4 weapon classes — general skills excluded
# since they don't strongly imply a specific weapon type.
_SKILL_WEAPON_TYPES: dict[str, list[str]] = {
    "Assassin's Gambit":    ["Dagger", "Katana", "Straight Sword", "Twinblade"],
    "Barrage":              ["Bow"],
    "Barricade Shield":     ["Greatshield", "Medium Shield", "Small Shield"],
    "Black Flame Tornado":  ["Halberd", "Reaper", "Spear", "Twinblade"],
    "Blood Blade":          ["Dagger", "Katana", "Straight Sword", "Twinblade"],
    "Bloody Slash":         ["Dagger", "Katana", "Straight Sword", "Twinblade"],
    "Buckler Parry":        ["Small Shield"],
    "Carian Retaliation":   ["Medium Shield", "Small Shield"],
    "Charge Forth":         ["Halberd", "Spear", "Twinblade"],
    "Enchanted Shot":       ["Bow"],
    "Eruption":             ["Colossal Sword", "Colossal Weapon", "Great Hammer", "Greataxe"],
    "Giant Hunt":           ["Colossal Sword", "Halberd", "Spear", "Twinblade"],
    "Golden Parry":         ["Medium Shield", "Small Shield"],
    "Holy Ground":          ["Greatshield", "Medium Shield", "Small Shield"],
    "Ice Spear":            ["Halberd", "Spear", "Twinblade"],
    "Lifesteal Fist":       ["Claw", "Fist"],
    "Loretta's Slash":      ["Great Spear", "Halberd", "Spear", "Twinblade"],
    "Mighty Shot":          ["Bow"],
    "Phantom Slash":        ["Halberd", "Spear", "Twinblade"],
    "Prelate's Charge":     ["Colossal Weapon", "Great Hammer", "Greataxe"],
    "Rain of Arrows":       ["Bow", "Greatbow"],
    "Sacred Ring of Light":  ["Halberd", "Reaper", "Spear"],
    "Shield Bash":          ["Greatshield", "Medium Shield", "Small Shield"],
    "Shield Crash":         ["Greatshield", "Medium Shield", "Small Shield"],
    "Sky Shot":             ["Bow"],
    "Spectral Lance":       ["Halberd", "Spear"],
    "Spinning Strikes":     ["Halberd", "Reaper", "Spear"],
    "Square Off":           ["Straight Sword"],
    "Storm Assault":        ["Halberd", "Spear", "Twinblade"],
    "Storm Wall":           ["Medium Shield", "Small Shield"],
    "Thops's Barrier":      ["Medium Shield", "Small Shield"],
    "Through and Through":  ["Greatbow"],
    "Troll's Roar":         ["Colossal Sword", "Colossal Weapon", "Great Hammer", "Greataxe"],
    "Unsheathe":            ["Katana"],
    "Vow of the Indomitable": ["Greatshield", "Medium Shield", "Small Shield"],
}

# Spell school booster passives (school name → passive)
_SCHOOL_BOOSTER: dict[str, str] = {
    "Bestial":          "Improved Bestial Incantations",
    "Giants' Flame":    "Improved Giants' Flame Incantations",
    "Dragon Cult":      "Improved Dragon Cult Incantations",
    "Godslayer":        "Improved Godslayer Incantations",
    "Fundamentalist":   "Improved Fundamentalist Incantations",
    "Dragon Communion": "Improved Dragon Communion Incantations",
    "Frenzied Flame":   "Improved Frenzied Flame Incantations",
    "Glintblade":       "Improved Glintblade Sorcery",
    "Stonedigger":      "Improved Stonedigger Sorcery",
    "Crystalian":       "Improved Crystalian Sorcery",
    "Carian Sword":     "Improved Carian Sword Sorcery",
    "Invisibility":     "Improved Invisibility Sorcery",
    "Gravity":          "Improved Gravity Sorcery",
    "Thorn":            "Improved Thorn Sorcery",
}

# School → primary damage type for that school
_SCHOOL_DAMAGE: dict[str, str] = {
    "Bestial":          "physical",
    "Giants' Flame":    "fire",
    "Dragon Cult":      "lightning",
    "Godslayer":        "fire",
    "Fundamentalist":   "holy",
    "Dragon Communion": "fire",
    "Frenzied Flame":   "fire",
    "Glintblade":       "magic",
    "Stonedigger":      "physical",
    "Crystalian":       "magic",
    "Carian Sword":     "magic",
    "Invisibility":     "magic",
    "Gravity":          "magic",
    "Thorn":            "physical",
}

# Spell school ID → school name (mirrors database/spells.py SCHOOL_ID_TO_PASSIVE)
_SCHOOL_ID_TO_NAME: dict[int, str] = {
    2:  "Carian Sword",
    3:  "Glintblade",
    4:  "Stonedigger",
    5:  "Crystalian",
    9:  "Thorn",
    11: "Gravity",
    12: "Invisibility",
    20: "Godslayer",
    21: "Giants' Flame",
    22: "Dragon Cult",
    23: "Bestial",
    24: "Fundamentalist",
    25: "Dragon Communion",
    26: "Frenzied Flame",
}


# =============================================================================
# CORE RECOMMENDATION FUNCTIONS
# =============================================================================

def recommend_for_weapon(weapon_type: str) -> list[RelicHint]:
    """Recommend passives for a pure melee weapon build."""
    data = _W.get(weapon_type)
    if data is None:
        return []

    class_booster, dormant, dmg_type = data
    hints: list[RelicHint] = []

    if class_booster:
        hints.append(RelicHint(
            passive=class_booster,
            reason=f"Direct damage booster for all {weapon_type} attacks.",
            priority=1,
        ))

    best_deep = _ELEMENTAL_DEEP.get(dmg_type, [])[0] if _ELEMENTAL_DEEP.get(dmg_type) else None
    second_deep = _ELEMENTAL_DEEP.get(dmg_type, [None, None])[1]
    best_normal = _ELEMENTAL_NORMAL.get(dmg_type)

    if best_deep:
        hints.append(RelicHint(
            passive=best_deep,
            reason=f"Highest {dmg_type} attack bonus — Deep of Night only.",
            deep_only=True,
            priority=1 if not class_booster else 2,
        ))
    if second_deep:
        hints.append(RelicHint(
            passive=second_deep,
            reason=f"Strong {dmg_type} attack bonus — Deep of Night only.",
            deep_only=True,
            priority=2,
        ))
    if best_normal:
        hints.append(RelicHint(
            passive=best_normal,
            reason=f"Best {dmg_type} attack bonus available on normal relics.",
            priority=2,
        ))

    if dormant:
        hints.append(RelicHint(
            passive=dormant,
            reason=f"Increases chance of finding {weapon_type}s while looting.",
            deep_only=True,
            priority=3,
        ))

    return hints


def recommend_for_skill(skill_name: str, weapon_type: str | None = None) -> list[RelicHint]:
    """Recommend passives for a weapon + AoW skill combination."""
    from database.weapon_skills import SKILLS
    # Find skill by name
    skill_data = None
    for sid, sdata in SKILLS.items():
        if sdata["name"].lower() == skill_name.lower():
            skill_data = sdata
            break

    if skill_data is None:
        # Unknown skill — fall back to weapon type only
        return recommend_for_weapon(weapon_type) if weapon_type else []

    cat = skill_data.get("cat", "Standard")
    dmg_type = _SKILL_DAMAGE_OVERRIDE.get(skill_name) or _SKILL_CAT_DAMAGE.get(cat, "physical")

    hints: list[RelicHint] = []

    # Elemental attack ups (primary if elemental skill)
    deep_ups = _ELEMENTAL_DEEP.get(dmg_type, [])
    normal_up = _ELEMENTAL_NORMAL.get(dmg_type)

    if deep_ups:
        hints.append(RelicHint(
            passive=deep_ups[0],
            reason=f"{skill_name} deals {dmg_type} damage — this is the top booster.",
            deep_only=True,
            priority=1,
        ))
        if len(deep_ups) > 1:
            hints.append(RelicHint(
                passive=deep_ups[1],
                reason=f"Second-best {dmg_type} attack booster — Deep of Night only.",
                deep_only=True,
                priority=2,
            ))
    if normal_up:
        hints.append(RelicHint(
            passive=normal_up,
            reason=f"Best {dmg_type} attack bonus on normal relics.",
            priority=2,
        ))

    # Weapon class booster (for the weapon holding this skill)
    inferred_types = _SKILL_WEAPON_TYPES.get(skill_name, [])
    if weapon_type:
        inferred_types = [weapon_type] + [t for t in inferred_types if t != weapon_type]

    for wtype in inferred_types[:1]:
        wdata = _W.get(wtype)
        if wdata:
            class_booster, dormant, _ = wdata
            if class_booster:
                hints.append(RelicHint(
                    passive=class_booster,
                    reason=f"Boosts base {wtype} attacks alongside the skill.",
                    priority=2,
                ))
            if dormant:
                hints.append(RelicHint(
                    passive=dormant,
                    reason=f"Increases {wtype} spawn rate — useful if farming for the weapon.",
                    deep_only=True,
                    priority=3,
                ))

    # Status skills: add note about the status-specific interaction
    if cat == "Frost":
        hints.append(RelicHint(
            passive="Physical Attack Up +2",
            reason="Frostbite triggers a 20% damage amp — boosting physical maximizes the combo.",
            priority=2,
        ))
    elif cat == "Blood":
        hints.append(RelicHint(
            passive="Improved Critical Hits",
            reason="Blood builds excel at critical hits — pairs well with hemorrhage procs.",
            priority=3,
        ))

    return _deduplicate(hints)


def recommend_for_spell(spell_name: str) -> list[RelicHint]:
    """Recommend passives for a spell-casting build centered on a specific spell."""
    from database.spells import SORCERIES, INCANTATIONS, SCHOOL_ID_TO_PASSIVE
    hints: list[RelicHint] = []

    is_sorcery    = spell_name in SORCERIES
    is_incantation = spell_name in INCANTATIONS

    if not is_sorcery and not is_incantation:
        return []

    school_id = SORCERIES.get(spell_name) if is_sorcery else INCANTATIONS.get(spell_name)
    school_name = _SCHOOL_ID_TO_NAME.get(school_id)
    dmg_type = _SCHOOL_DAMAGE.get(school_name, "magic") if school_name else ("magic" if is_sorcery else "holy")

    # School booster (if the spell has a mapped school)
    if school_name and school_name in _SCHOOL_BOOSTER:
        booster = _SCHOOL_BOOSTER[school_name]
        hints.append(RelicHint(
            passive=booster,
            reason=f"Direct booster for all {school_name} {'incantations' if is_incantation else 'sorceries'} — 12% damage increase.",
            priority=1,
        ))
    elif school_id == 0 or school_name is None:
        # Generic / no school — use broad booster
        broad = "Improved Incantations +2" if is_incantation else "Improved Sorceries +2"
        hints.append(RelicHint(
            passive=broad,
            reason=f"Broad booster for all {'incantations' if is_incantation else 'sorceries'} — best tier.",
            priority=1,
        ))

    # Broad booster (stacks with school booster)
    if school_name:
        broad = "Improved Incantations +2" if is_incantation else "Improved Sorceries +2"
        hints.append(RelicHint(
            passive=broad,
            reason=f"Broad booster stacks with the school passive — both apply simultaneously.",
            priority=2,
        ))

    # Elemental attack up matching the spell's damage type
    deep_ups = _ELEMENTAL_DEEP.get(dmg_type, [])
    normal_up = _ELEMENTAL_NORMAL.get(dmg_type)

    if deep_ups:
        hints.append(RelicHint(
            passive=deep_ups[0],
            reason=f"{spell_name} deals {dmg_type} damage — this is the top elemental booster.",
            deep_only=True,
            priority=2,
        ))
    if normal_up:
        hints.append(RelicHint(
            passive=normal_up,
            reason=f"Best {dmg_type} booster available on normal relics.",
            priority=2,
        ))

    # Catalyst dormant power
    catalyst_type = "Glintstone Staff" if is_sorcery else "Sacred Seal"
    catalyst_dormant = _W[catalyst_type][1]
    hints.append(RelicHint(
        passive=catalyst_dormant,
        reason=f"Increases {catalyst_type} spawn rate — helps find better catalysts.",
        deep_only=True,
        priority=3,
    ))

    return _deduplicate(hints)


def recommend_for_text(query: str) -> tuple[str, list[RelicHint]]:
    """
    Parse free text and return (interpreted_label, hints).
    Tries spell name → skill name → weapon type keyword match.
    """
    from database.spells import SORCERIES, INCANTATIONS
    from database.weapon_skills import SKILLS
    q = query.strip().lower()

    # 1. Try spell name match (exact or substring)
    for name in list(SORCERIES.keys()) + list(INCANTATIONS.keys()):
        if name.lower() in q or q in name.lower():
            label = f"Spell: {name}"
            return label, recommend_for_spell(name)

    # 2. Try skill name match
    for sid, sdata in SKILLS.items():
        sname = sdata["name"]
        if sdata["cat"] == "Internal":
            continue
        if sname.lower() in q or q in sname.lower():
            # Try to also extract weapon type
            wtype = _infer_weapon_type(q)
            label = f"Skill: {sname}" + (f" on {wtype}" if wtype else "")
            return label, recommend_for_skill(sname, wtype)

    # 3. Try weapon type match
    wtype = _infer_weapon_type(q)
    if wtype:
        return f"Weapon: {wtype}", recommend_for_weapon(wtype)

    return "", []


# =============================================================================
# KEYWORD → WEAPON TYPE
# =============================================================================

_WEAPON_KEYWORDS: dict[str, list[str]] = {
    "Dagger":               ["dagger", "reduvia", "misericorde", "scorpion stinger", "parrying dagger"],
    "Thrusting Sword":      ["thrusting sword", "rapier", "estoc", "estoque"],
    "Heavy Thrusting Sword":["heavy thrusting", "great epee", "cleanrot knight"],
    "Straight Sword":       ["straight sword", "longsword", "broadsword", "noble's slender"],
    "Greatsword":           ["greatsword", "claymore", "knight's greatsword", "inseparable"],
    "Colossal Sword":       ["colossal sword", "grafted blade", "starscourge"],
    "Curved Sword":         ["curved sword", "scimitar", "falchion"],
    "Curved Greatsword":    ["curved greatsword", "beastman's cleaver", "bloodhound's fang"],
    "Katana":               ["katana", "moonveil", "rivers of blood", "nagakiba", "unsheathe", "uchi"],
    "Twinblade":            ["twinblade", "eleonora"],
    "Axe":                  ["axe", "battle axe", "warped axe"],
    "Greataxe":             ["greataxe", "great axe", "longhaft axe"],
    "Hammer":               ["hammer", "morning star", "monk's flameblade"],
    "Flail":                ["flail", "nightrider flail"],
    "Great Hammer":         ["great hammer", "brick hammer", "large club"],
    "Colossal Weapon":      ["colossal weapon", "giant crusher", "golem's halberd"],
    "Spear":                ["spear", "short spear"],
    "Great Spear":          ["great spear", "lance", "partisan", "siluria", "treespear"],
    "Halberd":              ["halberd", "golden halberd", "dragon halberd"],
    "Reaper":               ["reaper", "scythe", "death's poker"],
    "Whip":                 ["whip", "thorned whip", "magma whip"],
    "Fist":                 ["fist", "caestus", "star fist"],
    "Claw":                 ["claw", "venomous fang"],
    "Bow":                  ["bow", "composite bow", "horn bow"],
    "Greatbow":             ["greatbow", "great bow", "rain of arrows", "radahn's rain", "pulley bow"],
    "Crossbow":             ["crossbow"],
    "Ballista":             ["ballista"],
    "Glintstone Staff":     ["staff", "sorcery", "sorceries", "sorcerer", "int build", "intelligence build"],
    "Sacred Seal":          ["seal", "incantation", "incantations", "faith build"],
}


def _infer_weapon_type(text: str) -> str | None:
    """Return the best-matching weapon type from a text query."""
    text_lower = text.lower()
    for wtype, keywords in _WEAPON_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return wtype
    return None


# =============================================================================
# DROPDOWN DATA — what to show in the skill/spell selector
# =============================================================================

def get_skill_options() -> list[str]:
    """Return sorted skill names for the dropdown (excludes Internal/disabled)."""
    from database.weapon_skills import SKILLS
    return sorted(
        {s["name"] for s in SKILLS.values() if s["cat"] not in ("Internal",)},
        key=str.casefold,
    )


def get_spell_options() -> list[str]:
    """Return sorted spell names (sorceries and incantations) for the dropdown."""
    from database.spells import SORCERIES, INCANTATIONS
    return sorted(list(SORCERIES.keys()) + list(INCANTATIONS.keys()), key=str.casefold)


def get_weapon_type_options() -> list[str]:
    """Return sorted weapon type names for the dropdown."""
    return sorted(
        [k for k in _W if not k.endswith("Staff") and not k.endswith("Seal")],
        key=str.casefold,
    )


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _deduplicate(hints: list[RelicHint]) -> list[RelicHint]:
    """Remove duplicate passives, keeping highest priority entry."""
    seen: set[str] = set()
    out: list[RelicHint] = []
    for h in sorted(hints, key=lambda x: x.priority):
        if h.passive not in seen:
            seen.add(h.passive)
            out.append(h)
    return out


def top_recommendations(hints: list[RelicHint], max_n: int = 4) -> list[RelicHint]:
    """Return the top N hints sorted by priority then deep_only (normal first)."""
    return sorted(hints, key=lambda h: (h.priority, h.deep_only))[:max_n]
