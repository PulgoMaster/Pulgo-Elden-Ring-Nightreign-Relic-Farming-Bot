"""
Smart Analyze rules for the Relic Bot.

Each rule is a named callable that inspects a relic's passive list and
returns a human-readable reason string when it fires, or None when it doesn't.

Rules are intentionally transparent — each one documents exactly what
combination it's looking for and why it's valuable.

Integration notes:
  - Rules fire ONLY on relics that did NOT match user criteria.
  - A relic that already triggered a HIT or GOD ROLL is never passed here.
  - `evaluate_relic(passives)` is the main entry point. It returns a list of
    all rule descriptions that fired.
"""

from __future__ import annotations
import re as _re
from collections.abc import Callable

from bot.game_knowledge import (
    PASSIVE_CATEGORY,
    SPECIFIC_AFFINITY_ELEMENT,
    INCANTATION_SCHOOL_PASSIVE,
    SORCERY_SCHOOL_PASSIVE,
    INCANTATION_SCHOOLS,
    SORCERY_SCHOOLS,
    WEAPON_CLASS_TO_DORMANT_POWER,
    DORMANT_POWER_TO_WEAPON_CLASS,
    WEAPON_CLASS_TO_ATTACK_PASSIVE,
    WEAPON_CLASS_POWER_PASSIVE_TO_CLASS,
)

# ── Tier-suffix stripping ──────────────────────────────────────────────────────

_TIER_SUFFIX = _re.compile(r"\s+\+\d+$")


def _base(passive: str) -> str:
    """Strip trailing ' +N' tier suffix."""
    return _TIER_SUFFIX.sub("", passive.strip())


def _cat(passive: str) -> str | None:
    """Return PASSIVE_CATEGORY tag for a passive (tier-stripped)."""
    return PASSIVE_CATEGORY.get(_base(passive))


def _has_cat(passives: list[str], category: str) -> list[str]:
    """Return all passives in the list that match the given category."""
    return [p for p in passives if _cat(p) == category]


# ── Individual rule functions ──────────────────────────────────────────────────
# Each returns a string description if it fires, or None if it doesn't.
# Passives are the relic's passive list (may include None entries from OCR).

def _rule_dragon_cult_triple(passives: list[str]) -> str | None:
    """
    Dragon Cult triple-stack:
      Improved Incantations + Improved Dragon Cult Incantations + Lightning Attack Power Up
    Reason: Dragon Cult spells deal Lightning damage, so all three passives
    boost the same spells — the rarest and most powerful incant synergy.
    """
    clean = [p for p in passives if p]
    bases = [_base(p) for p in clean]

    has_incant    = any(_cat(p) == "incantation_any" for p in clean)
    has_dc_school = "Improved Dragon Cult Incantations" in bases
    has_lightning = any(SPECIFIC_AFFINITY_ELEMENT.get(_base(p)) == "Lightning"
                        for p in clean)

    if has_incant and has_dc_school and has_lightning:
        return "Dragon Cult triple-stack: Improved Incantations + Dragon Cult + Lightning Attack Power Up"
    return None


def _rule_incant_school_double(passives: list[str]) -> str | None:
    """
    Incantation school double-stack: Improved Incantations + any incantation school passive.
    Reason: School buff stacks with delivery buff — worth having regardless of whether
    the user specified it. Reports which school was found.
    """
    clean = [p for p in passives if p]
    if not any(_cat(p) == "incantation_any" for p in clean):
        return None
    school_passives = [p for p in clean if _cat(p) == "incantation_school"]
    if not school_passives:
        return None
    schools = [INCANTATION_SCHOOL_PASSIVE.get(_base(p), _base(p)) for p in school_passives]
    school_str = " + ".join(schools)
    return f"Incantation double-stack: Improved Incantations + {school_str}"


def _rule_incant_triple_any(passives: list[str]) -> str | None:
    """
    Any incantation triple-stack: delivery + school + matching element.
    Covers schools other than Dragon Cult (Giants' Flame/Fire, Golden Order/Holy, etc.).
    Dragon Cult triple is reported by its own dedicated rule (above) for clarity.
    """
    clean = [p for p in passives if p]
    if not any(_cat(p) == "incantation_any" for p in clean):
        return None
    school_passives = [p for p in clean if _cat(p) == "incantation_school"]
    if not school_passives:
        return None

    for sp in school_passives:
        school_name = INCANTATION_SCHOOL_PASSIVE.get(_base(sp))
        if not school_name or school_name == "Dragon Cult":
            # Dragon Cult handled above
            continue
        # INCANTATION_SCHOOLS maps school → list of affinity damage types
        school_affinities = INCANTATION_SCHOOLS.get(school_name, [])
        if not school_affinities:
            continue
        affinity = school_affinities[0]   # primary affinity type
        # Check if a matching element passive is also present
        has_element = any(
            SPECIFIC_AFFINITY_ELEMENT.get(_base(p)) == affinity
            or _cat(p) == "affinity_damage"
            for p in clean
        )
        if has_element:
            return (f"{school_name} incantation triple-stack: "
                    f"Improved Incantations + {_base(sp)} + {affinity} Attack Power")
    return None


def _rule_sorcery_double(passives: list[str]) -> str | None:
    """
    Sorcery school double-stack: Improved Sorceries + any sorcery school passive.
    Reason: School buff stacks with delivery buff.
    """
    clean = [p for p in passives if p]
    if not any(_cat(p) == "sorcery_any" for p in clean):
        return None
    school_passives = [p for p in clean if _cat(p) == "sorcery_school"]
    if not school_passives:
        return None
    schools = [SORCERY_SCHOOL_PASSIVE.get(_base(p), _base(p)) for p in school_passives]
    school_str = " + ".join(schools)
    return f"Sorcery double-stack: Improved Sorceries + {school_str}"


def _rule_affinity_element_double(passives: list[str]) -> str | None:
    """
    Affinity double-stack: Improved Affinity Attack Power + element-specific passive.
    Reason: Both boost the same elemental attacks simultaneously.
    Only fires when the passives are on the SAME relic (which the game allows).
    """
    clean = [p for p in passives if p]
    if not any(_cat(p) == "affinity_damage" for p in clean):
        return None
    element_passives = [p for p in clean if _cat(p) == "specific_affinity"]
    if not element_passives:
        return None
    elements = list({SPECIFIC_AFFINITY_ELEMENT.get(_base(p)) for p in element_passives
                     if SPECIFIC_AFFINITY_ELEMENT.get(_base(p))})
    if not elements:
        return None
    elem_str = " + ".join(elements)
    return (f"Affinity double-stack: Improved Affinity Attack Power + "
            f"{elem_str} Attack Power Up")


def _rule_weapon_class_combo(passives: list[str]) -> str | None:
    """
    Weapon class power + dormant on same relic for same class.
    Reason: Improved X Attack Power boosts damage; Dormant Power improves drop rate.
    Having both for the same class on one relic is unusually convenient.
    """
    clean = [p for p in passives if p]
    bases = {_base(p) for p in clean}

    for p in clean:
        if _cat(p) != "weapon_class_power":
            continue
        wclass = WEAPON_CLASS_POWER_PASSIVE_TO_CLASS.get(_base(p))
        if not wclass:
            continue
        dormant = WEAPON_CLASS_TO_DORMANT_POWER.get(wclass)
        if dormant and dormant in bases:
            return (f"Weapon class combo ({wclass}): "
                    f"Attack Power + Dormant Power on same relic")
    return None


def _rule_multiple_attack_boosters(passives: list[str]) -> str | None:
    """
    Two or more general attack-boosting passives that stack.
    Covers: physical_damage, melee_damage, weapon_skill_damage, critical_damage,
    weapon_class_power, guard_counter.
    Reason: Stacking two attack modifiers on one relic is inherently strong for
    melee builds. Note: direct damage passives (Physical/Affinity/Sorceries/Incantations)
    are in exclusive group 0 and cannot coexist — this catches the non-exclusive ones.
    """
    STACKABLE_ATTACK_CATS = {
        "melee_damage", "weapon_skill_damage", "critical_damage",
        "weapon_class_power", "guard_counter", "roar_breath",
    }
    clean = [p for p in passives if p]
    boosters = [p for p in clean if _cat(p) in STACKABLE_ATTACK_CATS]
    # Must be at least 2 distinct categories (weapon_class_power counts per class)
    cats = [_cat(p) for p in boosters]
    if len(boosters) >= 2 and len(set(cats)) >= 2:
        names = ", ".join(_base(p) for p in boosters[:3])
        return f"Multiple attack boosters: {names}"
    return None


def _rule_physical_plus_melee(passives: list[str]) -> str | None:
    """
    Physical Attack Up + Improved Melee Attack Power (or weapon class power).
    Reason: Physical Attack Up stacks with melee/weapon-class boosters — unlike
    the affinity exclusive group, Physical Attack Up and melee boosters are not
    mutually exclusive.
    """
    clean = [p for p in passives if p]
    has_phys = any(_cat(p) == "physical_damage" for p in clean)
    if not has_phys:
        return None
    has_melee = any(_cat(p) in ("melee_damage", "weapon_class_power") for p in clean)
    if not has_melee:
        return None
    return "Physical stack: Physical Attack Up + melee/weapon-class damage booster"


# ── Rule registry ──────────────────────────────────────────────────────────────
# Ordered by value (highest-signal rules first).
# Each entry: (rule_id, rule_fn, short_label)

RULES: list[tuple[str, Callable]] = [
    ("dragon_cult_triple",       _rule_dragon_cult_triple),
    ("incant_triple_any",        _rule_incant_triple_any),
    ("incant_school_double",     _rule_incant_school_double),
    ("sorcery_double",           _rule_sorcery_double),
    ("affinity_element_double",  _rule_affinity_element_double),
    ("physical_plus_melee",      _rule_physical_plus_melee),
    ("multiple_attack_boosters", _rule_multiple_attack_boosters),
    ("weapon_class_combo",       _rule_weapon_class_combo),
]

RULE_IDS: set[str] = {r[0] for r in RULES}


# ── Main entry point ───────────────────────────────────────────────────────────

def evaluate_relic(passives: list[str | None]) -> list[str]:
    """
    Check a relic's passives against all smart rules.
    Returns a list of human-readable reason strings for every rule that fired.
    Passives may include None entries (empty slots from OCR).

    Call this only on relics that did NOT match user criteria.
    """
    clean = [p for p in passives if p]
    if not clean:
        return []
    triggered = []
    for _rule_id, rule_fn in RULES:
        result = rule_fn(clean)
        if result:
            triggered.append(result)
    return triggered


def evaluate_relic_with_ids(passives: list[str | None]) -> list[tuple[str, str]]:
    """
    Like evaluate_relic() but returns (rule_id, description) tuples.
    Useful for filtering or logging by rule type.
    """
    clean = [p for p in passives if p]
    if not clean:
        return []
    triggered = []
    for rule_id, rule_fn in RULES:
        result = rule_fn(clean)
        if result:
            triggered.append((rule_id, result))
    return triggered
