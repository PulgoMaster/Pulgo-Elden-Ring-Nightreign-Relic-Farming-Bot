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

def _rule_school_synergy(passives: list[str]) -> str | None:
    """
    School + damage synergy: detects when an incantation/sorcery school passive
    is paired with a Group 0 passive that boosts the same damage type.

    For each school passive on the relic, determines the school's primary damage
    type, then checks for any of these synergistic Group 0 pairings:
      1. General delivery boost ("Improved Incantations" / "Improved Sorceries")
      2. Matching element passive (e.g. "Fire Attack Power Up" for Giants' Flame)
      3. "Improved Affinity Attack Power" (if the school primarily deals affinity
         damage — i.e. non-physical: Magic, Fire, Lightning, Holy)

    Only one Group 0 passive can exist per relic, so this is always a double-stack.
    Schools with no affinity (e.g. Bestial = physical) only pair with option 1.
    """
    clean = [p for p in passives if p]
    if not clean:
        return None

    # Collect all school passives on this relic
    incant_schools = [p for p in clean if _cat(p) == "incantation_school"]
    sorc_schools   = [p for p in clean if _cat(p) == "sorcery_school"]
    if not incant_schools and not sorc_schools:
        return None

    # Identify the single Group 0 passive present (only one can exist)
    g0_delivery  = None   # "incantation_any" or "sorcery_any"
    g0_element   = None   # e.g. "Fire" from SPECIFIC_AFFINITY_ELEMENT
    g0_affinity  = False  # "affinity_damage" category
    for p in clean:
        cat = _cat(p)
        if cat == "incantation_any":
            g0_delivery = "incantation"
        elif cat == "sorcery_any":
            g0_delivery = "sorcery"
        elif cat == "specific_affinity":
            g0_element = SPECIFIC_AFFINITY_ELEMENT.get(_base(p))
        elif cat == "affinity_damage":
            g0_affinity = True

    # Try to match each school passive against the Group 0 passive
    for sp in incant_schools:
        school_name = INCANTATION_SCHOOL_PASSIVE.get(_base(sp), _base(sp))
        affinities  = INCANTATION_SCHOOLS.get(school_name, [])
        primary     = affinities[0] if affinities else None  # None = physical

        if g0_delivery == "incantation":
            return (f"School synergy: Improved Incantations + "
                    f"{_base(sp)} ({school_name})")
        if primary and g0_element == primary:
            return (f"School synergy: {primary} Attack Power Up + "
                    f"{_base(sp)} ({school_name} deals {primary})")
        if primary and g0_affinity:
            return (f"School synergy: Improved Affinity Attack Power + "
                    f"{_base(sp)} ({school_name} deals {primary})")

    for sp in sorc_schools:
        school_name = SORCERY_SCHOOL_PASSIVE.get(_base(sp), _base(sp))
        affinities  = SORCERY_SCHOOLS.get(school_name, [])
        primary     = affinities[0] if affinities else None

        if g0_delivery == "sorcery":
            return (f"School synergy: Improved Sorceries + "
                    f"{_base(sp)} ({school_name})")
        if primary and g0_element == primary:
            return (f"School synergy: {primary} Attack Power Up + "
                    f"{_base(sp)} ({school_name} deals {primary})")
        if primary and g0_affinity:
            return (f"School synergy: Improved Affinity Attack Power + "
                    f"{_base(sp)} ({school_name} deals {primary})")

    return None


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
    ("school_synergy",           _rule_school_synergy),
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
