"""
Pre-computed door generation for relic matching.

A "door" is a concrete set of passives that a relic must have to count as a
match.  Doors are generated from the user's criteria (exact targets, pool
entries, pairings) at UI change time and stored in memory.  During analysis
each relic is simply compared against the door list — no runtime logic needed.

Each door is a tuple:  (frozenset[str], str)
  - frozenset of passive names the relic must contain (ALL must be present)
  - source label for debugging ("exact", "pool", "pairing")

The tier of a match = number of passives in the door (1, 2, or 3).
GOD ROLL = door with 3 passives matched.  HIT = door with 1 or 2 matched.
"""

from __future__ import annotations

import itertools
import re
from typing import TYPE_CHECKING

from bot.passives import COMPAT_GROUPS
from bot.probability_engine import compat_ok, DEEP_POOL_PASSIVES, NORMAL_POOL_PASSIVES

if TYPE_CHECKING:
    pass


# ── Helpers ──────────────────────────────────────────────────────────────── #

def _variants_compat(combo: list[str]) -> bool:
    """Check that a combination of passives can coexist on a single relic.

    Two rules:
      1. No two passives share a compat group (exclusive categories).
      2. No two passives are tier variants of each other (same base name).
    """
    if not compat_ok(combo):
        return False
    # Check for tier-variant collisions (same base name, differ only in +N)
    bases = []
    for p in combo:
        base = re.sub(r'\s*[+\-]?\d+(%?)$', '', p).strip()
        if base in bases:
            return False
        bases.append(base)
    return True


# ── Exact mode doors ────────────────────────────────────────────────────── #

def _doors_from_exact(criteria: dict, pool: frozenset[str]) -> list[tuple[frozenset, str]]:
    """Generate doors from exact-mode targets.

    Each target has up to 3 slots, each with a single passive, and a threshold.
    A target with threshold T and N passives generates C(N, T) doors — one for
    each T-sized subset of the N passives.

    For near-miss tracking, we also need the full target info, but doors only
    represent the concrete combinations that count as a match.
    """
    doors = []
    for target in criteria.get("targets", []):
        passives = [p for p in target.get("passives", []) if p and p in pool]
        threshold = target.get("threshold", 2)
        if len(passives) < threshold:
            continue
        # Generate all threshold-sized subsets
        for combo in itertools.combinations(passives, threshold):
            if _variants_compat(list(combo)):
                doors.append((frozenset(combo), "exact"))
    return doors


# ── Pool mode doors ──────────────────────────────────────────────────────── #

def _doors_from_pool_entries(criteria: dict, pool: frozenset[str]) -> list[tuple[frozenset, str]]:
    """Generate doors from pool individual entries + threshold.

    Each entry has an "accepted" list (variant options — any ONE counts).
    The pool threshold says how many entries must match simultaneously.

    We expand: for each threshold-sized subset of entries, take the cartesian
    product of their accepted lists, filter for compatibility, and emit a door
    per valid combination.
    """
    entries = criteria.get("entries", [])
    threshold = criteria.get("threshold", 2)

    # Collect accepted lists, filtering to mode-valid passives
    entry_options: list[list[str]] = []
    for entry in entries:
        accepted = [p for p in entry.get("accepted", []) if p in pool]
        if accepted:
            entry_options.append(accepted)

    if len(entry_options) < threshold:
        return []

    doors = []
    seen: set[frozenset] = set()

    # For each threshold-sized subset of entries
    for entry_subset in itertools.combinations(range(len(entry_options)), threshold):
        # Cartesian product of accepted variants for these entries
        option_lists = [entry_options[i] for i in entry_subset]
        for combo in itertools.product(*option_lists):
            combo_list = list(combo)
            # Skip if any duplicates (same passive selected from different entries)
            if len(set(combo_list)) < len(combo_list):
                continue
            fs = frozenset(combo_list)
            if fs in seen:
                continue
            if _variants_compat(combo_list):
                seen.add(fs)
                doors.append((fs, "pool"))

    return doors


def _doors_from_pairings(criteria: dict, pool: frozenset[str]) -> list[tuple[frozenset, str]]:
    """Generate doors from pairing definitions.

    Each pairing has slots A (left), B (right), C (pool).  Each slot is a list
    of accepted passives (variants).  Empty list = slot not populated.

    A pairing door requires ALL populated slots to be satisfied.  The door size
    equals the number of populated slots (2 or 3).

    For each pairing we take the cartesian product of the populated slots'
    accepted lists and emit one door per valid combination.
    """
    doors = []
    seen: set[frozenset] = set()

    for pairing in criteria.get("pairings", []):
        left  = [p for p in pairing.get("left",  []) if p in pool]
        right = [p for p in pairing.get("right", []) if p in pool]
        c_pool = [p for p in pairing.get("pool",  []) if p in pool]

        # Collect populated slots
        slots: list[list[str]] = []
        if left:
            slots.append(left)
        if right:
            slots.append(right)
        if c_pool:
            slots.append(c_pool)

        if len(slots) < 2:
            continue  # need at least 2 populated slots

        # Cartesian product of all populated slots
        for combo in itertools.product(*slots):
            combo_list = list(combo)
            if len(set(combo_list)) < len(combo_list):
                continue
            fs = frozenset(combo_list)
            if fs in seen:
                continue
            if _variants_compat(combo_list):
                seen.add(fs)
                doors.append((fs, "pairing"))

    return doors


# ── Combine mode ─────────────────────────────────────────────────────────── #

def generate_doors(criteria: dict, relic_type: str = "night") -> list[tuple[frozenset, str]]:
    """Generate all doors from a criteria dict.

    Returns a deduplicated list of (passive_set, source) tuples sorted by
    door size descending (3-passive doors first) for early best-match exit.

    Args:
        criteria: The criteria dict from get_criteria_dict()
        relic_type: "night" or "normal" — determines valid passive pool
    """
    pool = DEEP_POOL_PASSIVES if relic_type == "night" else NORMAL_POOL_PASSIVES

    mode = criteria.get("mode", "exact")

    if mode == "exact":
        doors = _doors_from_exact(criteria, pool)

    elif mode == "pool":
        doors = _doors_from_pool_entries(criteria, pool)
        doors += _doors_from_pairings(criteria, pool)

    elif mode == "combine":
        exact_crit = criteria.get("exact", {})
        pool_crit  = criteria.get("pool", {})
        doors = _doors_from_exact(exact_crit, pool)
        doors += _doors_from_pool_entries(pool_crit, pool)
        doors += _doors_from_pairings(pool_crit, pool)

    else:
        doors = []

    # Deduplicate (same passive set from different sources — keep first)
    seen: set[frozenset] = set()
    unique = []
    for door in doors:
        if door[0] not in seen:
            seen.add(door[0])
            unique.append(door)

    # Sort: largest doors first (3 > 2 > 1) for early best-match
    unique.sort(key=lambda d: len(d[0]), reverse=True)

    return unique


# ── Smart Analyze door generation ────────────────────────────────────────── #

# Spell → school mapping for starting armament passives.
# Built from database/spells.py at import time.
_STARTING_SPELL_SCHOOL: dict[str, str | None] = {}  # spell name → school passive or None
_STARTING_SPELL_DAMAGE: dict[str, str | None] = {}  # spell name → damage element or None
_STARTING_SPELL_TYPE: dict[str, str] = {}            # spell name → "sorcery" or "incantation"

def _init_spell_mappings():
    """Build starting-spell lookup tables from database/spells.py."""
    from database.spells import (
        SORCERIES as _SORC_IDS, INCANTATIONS as _INCANT_IDS,
        SCHOOL_ID_TO_PASSIVE,
    )
    from database.nightreign_spells import (
        SORCERIES as _NR_SORC, INCANTATIONS as _NR_INCANT,
    )

    # Starting armament incantations
    _starting_incant = {
        "Lightning Spear": 22,     # Dragon Cult → Lightning
        "Dragonfire":      25,     # Dragon Communion → Fire
        "Beast Claw":      23,     # Bestial → Physical
        "O, Flame!":       21,     # Giants' Flame → Fire
        "Wrath of Gold":   0,      # Generic (no school passive — Fundamentalist by lore but school_id=0)
    }
    # Fix: Wrath of Gold is school_id 0 in spells.py but is Fundamentalist by lore
    # Check the actual data
    for spell, sid in _INCANT_IDS.items():
        if spell in _starting_incant:
            _starting_incant[spell] = sid

    for spell, sid in _starting_incant.items():
        school_passive = SCHOOL_ID_TO_PASSIVE.get(sid)
        _STARTING_SPELL_SCHOOL[spell] = school_passive
        dmg = _NR_INCANT.get(spell, {}).get("damage")
        _STARTING_SPELL_DAMAGE[spell] = dmg
        _STARTING_SPELL_TYPE[spell] = "incantation"

    # Starting armament sorceries
    _starting_sorc = {
        "Carian Greatsword":    2,   # Carian → Magic
        "Magic Glintblade":     3,   # Glintblade → Magic
        "Briars of Punishment": 9,   # Thorn → Magic
        "Night Shard":          12,  # Night/Invisibility → Magic
        "Magma Shot":           8,   # Magma → Fire (unmapped, no school passive)
    }
    for spell, sid in _SORC_IDS.items():
        if spell in _starting_sorc:
            _starting_sorc[spell] = sid

    for spell, sid in _starting_sorc.items():
        school_passive = SCHOOL_ID_TO_PASSIVE.get(sid)
        _STARTING_SPELL_SCHOOL[spell] = school_passive
        dmg = _NR_SORC.get(spell, {}).get("damage")
        _STARTING_SPELL_DAMAGE[spell] = dmg
        _STARTING_SPELL_TYPE[spell] = "sorcery"

_init_spell_mappings()


# Element name → element damage passive base names
_ELEMENT_TO_PASSIVES: dict[str, str] = {
    "Magic":     "Magic Attack Power Up",
    "Fire":      "Fire Attack Power Up",
    "Lightning": "Lightning Attack Power Up",
    "Holy":      "Holy Attack Power Up",
}

# Pulled from ALL_PASSIVES to stay in sync with the canonical passive list.
_NIGHT_INVADER = next(
    (p for p in NORMAL_POOL_PASSIVES if "Night Invader" in p),
    "Attack power increased for each Night Invader defeated",  # fallback
)


def _element_tiers(element: str, relic_type: str) -> list[str]:
    """Return the mode-appropriate tier variants for an element damage passive."""
    base = _ELEMENT_TO_PASSIVES.get(element)
    if not base:
        return []
    if relic_type == "night":
        return [f"{base} +2", f"{base} +3", f"{base} +4"]
    else:
        return [base, f"{base} +1", f"{base} +2"]


def _physical_tiers(relic_type: str) -> list[str]:
    """Return the mode-appropriate Physical Attack Up tiers."""
    if relic_type == "night":
        return ["Physical Attack Up +2", "Physical Attack Up +3", "Physical Attack Up +4"]
    else:
        return ["Physical Attack Up", "Physical Attack Up +1", "Physical Attack Up +2"]


def generate_smart_doors(relic_type: str = "night") -> list[tuple[frozenset, str]]:
    """Generate Smart Analyze doors based on game knowledge synergy rules.

    These are checked ONLY on relics that did NOT pass any regular door.
    Returns a deduplicated list of (passive_set, rule_label) tuples.
    """
    pool = DEEP_POOL_PASSIVES if relic_type == "night" else NORMAL_POOL_PASSIVES
    doors: list[tuple[frozenset, str]] = []
    seen: set[frozenset] = set()

    from database.passive_groups import are_compatible as _compat

    def _add(passives: list[str], label: str):
        fs = frozenset(passives)
        if fs not in seen and all(p in pool for p in passives):
            # Reject doors with incompatible passives (same compat group
            # or tier variants of the same passive).
            _plist = list(fs)
            for _i in range(len(_plist)):
                for _j in range(_i + 1, len(_plist)):
                    if not _compat(_plist[_i], _plist[_j]):
                        return
            seen.add(fs)
            doors.append((fs, label))

    # ── Rule 1: School synergy pools ─────────────────────────────────── #
    # For each starting spell, build a synergy pool and generate all
    # valid 2-combinations from: [school_passive, element_passives, starting_spell, jokers]

    from bot.game_knowledge import (
        INCANTATION_SCHOOL_PASSIVE, SORCERY_SCHOOL_PASSIVE,
        INCANTATION_SCHOOLS, SORCERY_SCHOOLS,
        PASSIVE_CATEGORY, SPECIFIC_AFFINITY_ELEMENT,
        WEAPON_CLASS_TO_DORMANT_POWER,
    )

    # Also build school synergy doors from school passives + element passives
    # (without starting spells — the original Rule 1)
    all_school_passives = list(INCANTATION_SCHOOL_PASSIVE.keys()) + list(SORCERY_SCHOOL_PASSIVE.keys())
    for school_p in all_school_passives:
        # Determine spell type and school
        is_incant = school_p in INCANTATION_SCHOOL_PASSIVE
        school_name = (INCANTATION_SCHOOL_PASSIVE.get(school_p) if is_incant
                       else SORCERY_SCHOOL_PASSIVE.get(school_p))
        schools_dict = INCANTATION_SCHOOLS if is_incant else SORCERY_SCHOOLS
        affinities = schools_dict.get(school_name, [])
        primary = affinities[0] if affinities else None  # None = physical

        # Pool members for this school
        pool_members: list[str] = []

        # General delivery (Improved Incantations/Sorceries — Deep only)
        if relic_type == "night":
            delivery_base = "Improved Incantations" if is_incant else "Improved Sorceries"
            for suffix in ["", " +1", " +2"]:
                pool_members.append(delivery_base + suffix)

        # Matching element damage (or Physical for physical-only schools like Bestial)
        if primary:
            pool_members.extend(_element_tiers(primary, relic_type))
        else:
            # Physical-only school (e.g. Bestial) — pair with Physical Attack Up
            pool_members.extend(_physical_tiers(relic_type))

        # Improved Affinity Attack Power (Deep only, for non-physical schools)
        if primary and relic_type == "night":
            for suffix in ["", " +1", " +2"]:
                pool_members.append("Improved Affinity Attack Power" + suffix)

        # Night Invader joker (Normal only)
        if relic_type != "night":
            pool_members.append(_NIGHT_INVADER)

        # Starting spells that belong to this school (Normal mode only —
        # starting armament passives don't exist in Deep of Night)
        if relic_type != "night":
            for spell, sp_school in _STARTING_SPELL_SCHOOL.items():
                if sp_school == school_p:
                    # Find the exact passive name from the pool instead of constructing it
                    spell_type = _STARTING_SPELL_TYPE[spell]
                    _keyword = f"{spell_type} to {spell}"
                    _found = [p for p in pool if _keyword in p]
                    for sp in _found:
                        pool_members.append(sp)

        # Dormant catalyst (Sacred Seals for incantations, Staves for sorceries)
        _dormant_cat = (WEAPON_CLASS_TO_DORMANT_POWER.get("Sacred Seal", "")
                        if is_incant
                        else WEAPON_CLASS_TO_DORMANT_POWER.get("Glintstone Staff", ""))
        if _dormant_cat and _dormant_cat in pool:
            pool_members.append(_dormant_cat)

        # Generate all 2-combinations: school_passive + any pool member
        for member in pool_members:
            if member != school_p:
                _add([school_p, member], "smart:school_synergy")

        # Also generate pool_member + pool_member (e.g., element + starting spell)
        for i, m1 in enumerate(pool_members):
            for m2 in pool_members[i + 1:]:
                if m1 != m2:
                    _add([m1, m2], "smart:school_synergy")

        # 3-passive SMART GOD ROLL doors: school_passive + any 2 pool members
        for i, m1 in enumerate(pool_members):
            for m2 in pool_members[i + 1:]:
                if m1 != school_p and m2 != school_p and m1 != m2:
                    _add([school_p, m1, m2], "smart:school_synergy_3")

        # Also: any 3 from pool_members (without school_p)
        for i in range(len(pool_members)):
            for j in range(i + 1, len(pool_members)):
                for k in range(j + 1, len(pool_members)):
                    _add([pool_members[i], pool_members[j], pool_members[k]],
                         "smart:school_synergy_3")

    # ── 3-passive doors: starting spell + school passive + damage booster ── #
    # Normal mode only.  If 2 of 3 passives present → SMART HIT.
    # If all 3 present → SMART GOD ROLL.
    if relic_type != "night":
        for school_p in all_school_passives:
            is_incant = school_p in INCANTATION_SCHOOL_PASSIVE
            school_name = (INCANTATION_SCHOOL_PASSIVE.get(school_p) if is_incant
                           else SORCERY_SCHOOL_PASSIVE.get(school_p))
            schools_dict = INCANTATION_SCHOOLS if is_incant else SORCERY_SCHOOLS
            affinities = schools_dict.get(school_name, [])
            primary = affinities[0] if affinities else None

            # Find starting spells for this school
            for spell, sp_school in _STARTING_SPELL_SCHOOL.items():
                if sp_school != school_p:
                    continue
                spell_type = _STARTING_SPELL_TYPE[spell]
                _keyword = f"{spell_type} to {spell}"
                _found = [p for p in pool if _keyword in p]
                for starting_passive in _found:
                    # 3-door: starting_spell + school_passive + damage tier
                    if primary:
                        for tier in _element_tiers(primary, relic_type):
                            _add([starting_passive, school_p, tier],
                                 "smart:school_synergy_3")
                    else:
                        for tier in _physical_tiers(relic_type):
                            _add([starting_passive, school_p, tier],
                                 "smart:school_synergy_3")
                    # 3-door: starting_spell + school_passive + Night Invader
                    _add([starting_passive, school_p, _NIGHT_INVADER],
                         "smart:school_synergy_3")

    # Starting spells with no school passive (e.g., Magma Shot, Wrath of Gold)
    # Normal mode only — starting armament passives don't exist in Deep.
    if relic_type != "night":
        for spell, school_p in _STARTING_SPELL_SCHOOL.items():
            if school_p is not None:
                continue  # Already handled above
            spell_type = _STARTING_SPELL_TYPE[spell]
            _keyword = f"{spell_type} to {spell}"
            _found = [p for p in pool if _keyword in p]
            for starting_passive in _found:
                damage = _STARTING_SPELL_DAMAGE.get(spell)
                if damage:
                    for tier in _element_tiers(damage, relic_type):
                        _add([starting_passive, tier], "smart:school_synergy")
                _add([starting_passive, _NIGHT_INVADER], "smart:school_synergy")

    # ── Rule 2: Weapon class attack + dormant for same class ─────────── #
    from bot.game_knowledge import (
        WEAPON_CLASS_TO_ATTACK_PASSIVE,
        WEAPON_CLASS_TO_DORMANT_POWER,
    )
    for wclass, attack_p in WEAPON_CLASS_TO_ATTACK_PASSIVE.items():
        dormant_p = WEAPON_CLASS_TO_DORMANT_POWER.get(wclass)
        if dormant_p:
            _add([attack_p, dormant_p], "smart:weapon_class_combo")

    # ── Rule 4: Physical Attack Up + weapon/melee ────────────────────── #
    weapon_class_passives = list(WEAPON_CLASS_TO_ATTACK_PASSIVE.values())
    # Pull from pool to stay in sync with canonical passive names
    initial_standard = next(
        (p for p in pool if "Improved Initial Standard Attack" in p), "")

    for phys in _physical_tiers(relic_type):
        for wcp in weapon_class_passives:
            _add([phys, wcp], "smart:physical_stack")
        _add([phys, initial_standard], "smart:physical_stack")

    # ── Rule 5: Catalyst synergy ─────────────────────────────────────── #
    dormant_seals = WEAPON_CLASS_TO_DORMANT_POWER.get("Sacred Seal", "")
    dormant_staves = WEAPON_CLASS_TO_DORMANT_POWER.get("Glintstone Staff", "")

    for incant_school_p in INCANTATION_SCHOOL_PASSIVE:
        if dormant_seals:
            _add([incant_school_p, dormant_seals], "smart:catalyst_synergy")

    for sorc_school_p in SORCERY_SCHOOL_PASSIVE:
        if dormant_staves:
            _add([sorc_school_p, dormant_staves], "smart:catalyst_synergy")

    # ── Rule 6: Night Invader + specific skills (Normal only) ────────── #
    # Skill names pulled from the canonical passive list via pattern match.
    if relic_type != "night":
        _RULE6_SKILLS = ["Hoarfrost Stomp", "Flaming Strike", "Blood Blade"]
        for skill in _RULE6_SKILLS:
            # Find the exact passive name from ALL_PASSIVES to avoid hardcoding
            _skill_candidates = [
                p for p in pool
                if p.startswith("Changes compatible armament's skill to ")
                and skill in p
            ]
            for sp in _skill_candidates:
                _add([_NIGHT_INVADER, sp], "smart:night_invader_skill")

    # ── Rule 7: Same-class passive doubles ──────────────────────────── #
    # "Improved X Attack Power" + "Improved Attack Power with 3+ Xs Equipped"
    # Explicit mapping avoids substring false positives (e.g. Greatsword matching
    # Curved Greatswords, Hammer matching Great Hammers).
    _CLASS_TO_3X_KEYWORD = {
        "Dagger": "Daggers", "Thrusting Sword": "Thrusting Swords",
        "Heavy Thrusting Sword": "Heavy Thrusting Swords",
        "Straight Sword": "Straight Swords", "Greatsword": "Greatswords",
        "Colossal Sword": "Colossal Swords", "Curved Sword": "Curved Swords",
        "Curved Greatsword": "Curved Greatswords", "Katana": "Katana",
        "Twinblade": "Twinblades", "Axe": "Axes", "Greataxe": "Greataxes",
        "Hammer": "Hammers", "Flail": "Flails", "Great Hammer": "Great Hammers",
        "Colossal Weapon": "Colossal Weapons", "Spear": "Spears",
        "Great Spear": "Great Spears", "Halberd": "Halberds",
        "Reaper": "Reapers", "Whip": "Whips", "Fist": "Fists",
        "Claw": "Claws", "Bow": "Bows",
    }
    for wclass, attack_p in WEAPON_CLASS_TO_ATTACK_PASSIVE.items():
        plural = _CLASS_TO_3X_KEYWORD.get(wclass)
        if not plural:
            continue
        _3x_name = f"Improved Attack Power with 3+ {plural} Equipped"
        if _3x_name in pool:
            _add([attack_p, _3x_name], "smart:same_class_double")



    # Sort largest first, deduplicate
    doors.sort(key=lambda d: len(d[0]), reverse=True)
    return doors


# ── Door metadata ────────────────────────────────────────────────────────── #

def min_door_size(doors: list[tuple[frozenset, str]]) -> int:
    """Return the smallest door size (minimum passives needed for ANY match).

    Useful for early-skipping small relics:
      - If min_door_size > 1, Delicate relics (1 passive) can never match.
      - If min_door_size > 2, Polished relics (2 passives) can never match.
    Returns 0 if no doors exist.
    """
    if not doors:
        return 0
    return min(len(d[0]) for d in doors)


def get_3_passive_doors(doors: list[tuple[frozenset, str]]) -> list[frozenset]:
    """Return only the 3-passive doors (used for near-miss detection).

    A near miss can only come from a 3/3 door where 2 passives matched.
    """
    return [d[0] for d in doors if len(d[0]) == 3]


# ── Match checking ───────────────────────────────────────────────────────── #

def check_doors(
    relic_passives: list[str],
    doors: list[tuple[frozenset, str]],
) -> tuple[bool, list[str], list[dict]]:
    """Check a relic's passives against pre-computed doors.

    Returns (match, matched_passives, near_misses) — same shape as the old
    _check_criteria return value for backward compatibility.

    - match: True if any door was fully satisfied
    - matched_passives: list of real passive names from the best door
    - near_misses: list of near-miss dicts (only from 3/3 doors with 2 hits)

    The relic's tier = len(matched_passives) from the best door:
      3 = GOD ROLL, 2 = HIT, 1 = HIT (only if a 1-passive door exists)
    """
    relic_set = set(relic_passives)
    relic_count = len(relic_passives)

    best_match: list[str] = []
    near_misses: list[dict] = []

    for door_passives, source in doors:
        door_size = len(door_passives)

        # Early exit: skip doors requiring more passives than relic has
        hits = door_passives & relic_set

        if len(hits) == door_size:
            # Full match — keep if better than current best
            if door_size > len(best_match):
                best_match = sorted(hits)
                # If we hit a 3-passive door, can't do better — stop
                if door_size >= 3:
                    break
        elif len(hits) == 2 and door_size == 3:
            # Near miss: 2 of 3 from a 3-passive door (includes Polished relics)
            near_misses.append({
                "relic_name": "current relic",
                "matching_passive_count": 2,
                "matching_passives": sorted(hits),
            })

    if best_match:
        return True, best_match, []

    # Deduplicate near misses (same 2 passives from different 3-doors)
    seen_nm: set[frozenset] = set()
    unique_nm = []
    for nm in near_misses:
        key = frozenset(nm["matching_passives"])
        if key not in seen_nm:
            seen_nm.add(key)
            unique_nm.append(nm)

    return False, [], unique_nm
