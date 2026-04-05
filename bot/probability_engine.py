"""
Relic passive probability engine.
All formulas use actual datamine pool weights from database/pool_weights.py.

Key design:
  - Slot draws are treated as independent (approximation for Deep slots 2+3 which
    share the same table, but compat depletion across slots is a small correction).
  - Compat group conflict → P = 0 immediately.
  - Multi-target combo uses inclusion-exclusion over the slot-draw structure.
  - Color filter and size distribution applied to get per-relic probability.
"""

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from database.pool_weights import (
    TABLE_100, TABLE_110, TABLE_200, TABLE_210, TABLE_300, TABLE_310,  # 100/200/300 = pre-1.02 tables, kept for future use
    TABLE_110_TOTAL, TABLE_210_TOTAL, TABLE_310_TOTAL,
    TABLE_2000000, TABLE_2100000,
    TABLE_2000000_TOTAL, TABLE_2100000_TOTAL,
    NUM_CURSES, DEEP_CURSE_COUNT_DIST,
)
from bot.passives import COMPAT_GROUPS


# ── Color distributions ──────────────────────────────────────────────────── #
# Confirmed from EquipParamAntique.csv  (2026-03-26)
NORMAL_COLOR_COUNTS: dict[str, int] = {"Red": 148, "Blue": 145, "Green": 143, "Yellow": 143}
NORMAL_COLOR_TOTAL:  int = 579

DEEP_COLOR_COUNTS: dict[str, int] = {"Red": 54, "Blue": 54, "Green": 54, "Yellow": 54}
DEEP_COLOR_TOTAL:  int = 216

# ── Size distributions ───────────────────────────────────────────────────── #
# From ShopLineupParam / ItemTableParam confirmed weights
NORMAL_SIZE_PROBS: dict[str, float] = {"delicate": 0.45, "polished": 0.35, "grand": 0.20}
DEEP_SIZE_PROBS:   dict[str, float] = {"delicate": 0.10, "polished": 0.50, "grand": 0.40}

# ── Slot→table assignments ────────────────────────────────────────────────── #
# Normal slots draw from fixed-tier tables.  Prefix maps display name to pool key.
# (table_dict, total_weight, key_prefix)
_NORMAL_SLOTS: dict[str, list[tuple]] = {
    "delicate": [
        (TABLE_110, TABLE_110_TOTAL, "<Delicate Scene> "),
    ],
    "polished": [
        (TABLE_210, TABLE_210_TOTAL, "<Polished Scene> "),
        (TABLE_110, TABLE_110_TOTAL, "<Delicate Scene> "),
    ],
    "grand": [
        (TABLE_310, TABLE_310_TOTAL, "<Grand Scene> "),
        (TABLE_210, TABLE_210_TOTAL, "<Polished Scene> "),
        (TABLE_110, TABLE_110_TOTAL, "<Delicate Scene> "),
    ],
}

# ── Deep relic variant structure (confirmed from EquipParamAntique.csv 2026-03-26) ── #
#
# Each Deep bazaar relic is one of 9 variants determined by (size × curse_count).
# Each curse slot is paired 1-to-1 with a TABLE_2000000 passive slot — they are
# the same count on any given relic entry.
#
# TABLE_2000000 = exclusive pool (49 entries, high-tier: PA+3/+4, Affinity+2, Max HP…)
# TABLE_2100000 = broad pool    (277 entries, mid-tier: PA+2, Poise+3…)
# TABLE_2200000 is a clone of TABLE_2100000 (identical passives + weights).
# Referenced by EQA 201xxxx entries but unreachable from the item selection
# chain (49100 → 49110-49112 → 49120-49143 → only 200xxxx / 2003xxx EQAs).
#
# Format: (combined_probability, [(table, total, prefix), …])
_T2M = (TABLE_2000000, TABLE_2000000_TOTAL, "<Table> ")  # exclusive slot
_T2B = (TABLE_2100000, TABLE_2100000_TOTAL, "<Table> ")  # broad slot

_DEEP_VARIANTS: list[tuple[float, list[tuple]]] = [
    # Delicate (10% of relics)
    (0.050, [_T2B]),                                # Del / 0 curses
    (0.050, [_T2M]),                                # Del / 1 curse
    # Polished (50% of relics)
    (0.150, [_T2B, _T2B]),                          # Pol / 0 curses
    (0.250, [_T2M, _T2B]),                          # Pol / 1 curse
    (0.100, [_T2M, _T2M]),                          # Pol / 2 curses
    # Grand (40% of relics)
    (0.160, [_T2B, _T2B, _T2B]),                    # Grd / 0 curses
    (0.120, [_T2M, _T2B, _T2B]),                    # Grd / 1 curse
    (0.080, [_T2M, _T2M, _T2B]),                    # Grd / 2 curses
    (0.040, [_T2M, _T2M, _T2M]),                    # Grd / 3 curses
]


# ── Color probability ─────────────────────────────────────────────────────── #

def color_probability(relic_type: str, allowed_colors: list[str]) -> float:
    """P(relic color is in allowed_colors). Returns 0 if allowed_colors is empty."""
    if not allowed_colors:
        return 0.0
    if relic_type == "night":
        counts, total = DEEP_COLOR_COUNTS, DEEP_COLOR_TOTAL
    else:
        counts, total = NORMAL_COLOR_COUNTS, NORMAL_COLOR_TOTAL
    return sum(counts.get(c, 0) for c in allowed_colors) / total


# ── Per-slot probability helpers ─────────────────────────────────────────── #

def _slot_probs(passive: str, size: str) -> list[float]:
    """
    Return [p_slot1, p_slot2, ...] for the given passive in a Normal relic of given size.
    Only used for Normal relics — Deep relics use _DEEP_VARIANTS directly.
    """
    result = []
    for table, total, prefix in _NORMAL_SLOTS.get(size, []):
        key = prefix + passive
        result.append(table.get(key, 0) / total)
    return result


def _slot_probs_from_list(passive: str, slot_list: list[tuple]) -> list[float]:
    """Return [p_slot1, …] for the passive against an explicit list of (table, total, prefix) slots."""
    return [table.get(prefix + passive, 0) / total for table, total, prefix in slot_list]


def prob_passive_on_size(passive: str, relic_type: str, size: str) -> float | None:
    """
    P(passive appears on a relic of given type and size).
    Returns None if the passive has no pool entry for this type+size.
    For Deep relics, averages across curse-count variants within the given size.
    """
    if relic_type == "night":
        # Conditional probability: P(passive | Deep, size) — average over curse-count variants
        _size_variants = {
            "delicate": [_DEEP_VARIANTS[0], _DEEP_VARIANTS[1]],
            "polished": [_DEEP_VARIANTS[2], _DEEP_VARIANTS[3], _DEEP_VARIANTS[4]],
            "grand":    [_DEEP_VARIANTS[5], _DEEP_VARIANTS[6], _DEEP_VARIANTS[7], _DEEP_VARIANTS[8]],
        }
        variants = _size_variants.get(size, [])
        if not variants:
            return None
        size_total_prob = sum(p for p, _ in variants)
        total = 0.0
        for p_var, slot_list in variants:
            probs = _slot_probs_from_list(passive, slot_list)
            q = 1.0
            for p in probs:
                q *= (1.0 - p)
            total += (p_var / size_total_prob) * (1.0 - q)
        return total if total > 1e-12 else None
    else:
        probs = _slot_probs(passive, size)
        if not probs or all(p == 0.0 for p in probs):
            return None
        q = 1.0
        for p in probs:
            q *= (1.0 - p)
        return 1.0 - q


def prob_passive_by_size(passive: str, relic_type: str) -> dict[str, float | None]:
    """Return {size: P(passive on that size relic)} for all three sizes."""
    return {
        size: prob_passive_on_size(passive, relic_type, size)
        for size in ("delicate", "polished", "grand")
    }


# ── Compat check ─────────────────────────────────────────────────────────── #

def compat_ok(targets: list[str]) -> bool:
    """Return True if no two targets share a compat group (can all coexist on a relic)."""
    seen: set[int] = set()
    for t in targets:
        g = COMPAT_GROUPS.get(t)
        if g is not None:
            if g in seen:
                return False
            seen.add(g)
    return True


# ── Multi-target combo probability ───────────────────────────────────────── #

def _combo_from_slot_list(targets: list[str], slot_list: list[tuple]) -> float:
    """
    P(all targets appear on a relic with the given explicit slot configuration).
    Uses inclusion-exclusion.  Returns 0.0 if any target is absent from all slots
    or if more targets than slots.
    (Internal helper; does not check compat — caller must verify.)
    """
    n_slots   = len(slot_list)
    n_targets = len(targets)
    if n_targets > n_slots:
        return 0.0

    all_slot_probs = [_slot_probs_from_list(t, slot_list) for t in targets]
    if any(all(p == 0.0 for p in sp) for sp in all_slot_probs):
        return 0.0

    result = 0.0
    for mask in range(1 << n_targets):
        subset = [i for i in range(n_targets) if mask & (1 << i)]
        sign   = (-1) ** len(subset)
        prod   = 1.0
        for slot_idx in range(n_slots):
            p_none = 1.0 - sum(all_slot_probs[i][slot_idx] for i in subset)
            prod  *= max(0.0, p_none)
        result += sign * prod
    return max(0.0, result) if result > 1e-12 else 0.0


def prob_combo_on_size(targets: list[str], relic_type: str, size: str) -> float | None:
    """
    P(all targets appear on a single relic of given type and size).
    For Normal relics: uses the fixed-tier slot tables.
    For Deep relics: averages across curse-count variants within the given size.

    Returns:
      0.0   — targets compat-incompatible, or confirmed impossible for this size
      None  — any target has no pool entry at all (Normal only)
      float — probability
    """
    targets = [t for t in targets if t]
    if not targets:
        return None
    if not compat_ok(targets):
        return 0.0

    if relic_type == "night":
        _size_variants = {
            "delicate": [_DEEP_VARIANTS[0], _DEEP_VARIANTS[1]],
            "polished": [_DEEP_VARIANTS[2], _DEEP_VARIANTS[3], _DEEP_VARIANTS[4]],
            "grand":    [_DEEP_VARIANTS[5], _DEEP_VARIANTS[6], _DEEP_VARIANTS[7], _DEEP_VARIANTS[8]],
        }
        variants = _size_variants.get(size, [])
        if not variants:
            return 0.0
        size_total_prob = sum(p for p, _ in variants)
        total = 0.0
        for p_var, slot_list in variants:
            total += (p_var / size_total_prob) * _combo_from_slot_list(targets, slot_list)
        return total if total > 1e-12 else 0.0

    # Normal relic path
    all_slot_probs: list[list[float]] = []
    for t in targets:
        sp = _slot_probs(t, size)
        if not sp:
            return None
        all_slot_probs.append(sp)

    n_slots   = len(all_slot_probs[0])
    n_targets = len(targets)
    if n_targets > n_slots:
        return 0.0
    if any(all(p == 0.0 for p in sp) for sp in all_slot_probs):
        return 0.0

    result = 0.0
    for mask in range(1 << n_targets):
        subset = [i for i in range(n_targets) if mask & (1 << i)]
        sign   = (-1) ** len(subset)
        prod   = 1.0
        for slot_idx in range(n_slots):
            p_none = 1.0 - sum(all_slot_probs[i][slot_idx] for i in subset)
            prod  *= max(0.0, p_none)
        result += sign * prod
    return max(0.0, result) if result > 1e-12 else 0.0


def prob_combo_on_relic(
    targets: list[str],
    relic_type: str,
    allowed_colors: list[str] | None = None,
) -> float | None:
    """
    P(all targets appear on a randomly drawn relic of given type, accounting for
    the full variant distribution and optional color filter.

    Deep relics: sums over all 9 (size × curse_count) variants.
    Normal relics: sums over 3 sizes.
    """
    targets = [t for t in targets if t]
    if not targets:
        return None

    if allowed_colors is not None and not allowed_colors:
        return 0.0

    p_color = (color_probability(relic_type, allowed_colors)
               if allowed_colors is not None else 1.0)
    if p_color == 0.0:
        return 0.0

    if relic_type == "night":
        # Iterate over all 9 Deep variants directly
        if not compat_ok(targets):
            return 0.0   # compat conflict → truly impossible
        total = 0.0
        for p_var, slot_list in _DEEP_VARIANTS:
            total += p_var * _combo_from_slot_list(targets, slot_list)
        # Return None (not in pool) rather than 0.0 when passive simply isn't
        # in any deep table — 0.0 is reserved for compat conflicts above.
        return (total * p_color) if total > 1e-12 else None

    # Normal relics — existing size-based path
    total    = 0.0
    has_pos  = False
    has_none = False
    for size, p_size in NORMAL_SIZE_PROBS.items():
        p_combo = prob_combo_on_size(targets, relic_type, size)
        if p_combo is None:
            has_none = True
        elif p_combo > 0.0:
            total   += p_size * p_combo
            has_pos  = True

    # All sizes confirmed 0 → impossible
    if not has_pos and not has_none:
        return 0.0
    # No pool data at all
    if not has_pos:
        return None

    return total * p_color


def prob_any_combo_on_relic(
    combo_list: list[list[str]],
    relic_type: str,
    allowed_colors: list[str] | None = None,
) -> float | None:
    """
    P(at least one combo from combo_list matches a single relic).
    Uses the complement product:  1 − ∏(1 − P(combo_i)).
    Treats combos as independent events (approximation, very accurate when
    combo passives don't heavily overlap).
    """
    found_any = False
    complement = 1.0
    for combo in combo_list:
        p = prob_combo_on_relic(combo, relic_type, allowed_colors)
        if p is not None and p >= 0.0:
            complement *= max(0.0, 1.0 - p)
            found_any   = True

    if not found_any:
        return None
    return max(0.0, 1.0 - complement)


# ── Pool threshold probability ────────────────────────────────────────────── #

def prob_at_least_k_of_pool(per_entry_probs: list[float], k: int) -> float:
    """
    P(at least k of N pool entries appear on a relic).
    Uses DP treating entries as independent (approximation).

    per_entry_probs: list of P(entry_i appears on one relic) — use
                     prob_passive_on_relic() for each entry.
    k: minimum threshold.
    """
    n = len(per_entry_probs)
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0

    # dp[j] = P(exactly j hits among processed entries so far)
    dp = [0.0] * (n + 1)
    dp[0] = 1.0
    for p in per_entry_probs:
        new_dp = [0.0] * (n + 1)
        for j in range(n + 1):
            if dp[j] == 0.0:
                continue
            new_dp[j]     += dp[j] * (1.0 - p)
            if j + 1 <= n:
                new_dp[j + 1] += dp[j] * p
        dp = new_dp

    return sum(dp[k:])


# ── Pool membership sets (used by UI for mode-based filtering) ────────────── #
# A passive is "in the deep pool" if it has a non-zero weight entry in any deep
# table (TABLE_2000000 or TABLE_2100000).  The key prefix is "<Table> ".
# A passive is "in the normal pool" if it has an entry in any normal table
# (TABLE_100/200/300).  Their prefixes differ per scene level.

_DEEP_PREFIX = "<Table> "
_NORMAL_PREFIXES = ("<Delicate Scene> ", "<Polished Scene> ", "<Grand Scene> ")

DEEP_POOL_PASSIVES: frozenset = frozenset(
    k[len(_DEEP_PREFIX):]
    for table in (TABLE_2000000, TABLE_2100000)
    for k, v in table.items()
    if k.startswith(_DEEP_PREFIX) and v > 0
)

NORMAL_POOL_PASSIVES: frozenset = frozenset(
    k.split("> ", 1)[1]
    for table in (TABLE_110, TABLE_210, TABLE_310)
    for k, v in table.items()
    if any(k.startswith(pfx) for pfx in _NORMAL_PREFIXES) and v > 0
)


def prob_passive_on_relic(
    passive: str,
    relic_type: str,
    allowed_colors: list[str] | None = None,
) -> float | None:
    """
    P(passive appears on a randomly drawn relic, weighted across all sizes.
    Convenience wrapper for single-passive pool-tab display.
    """
    return prob_combo_on_relic([passive], relic_type, allowed_colors)


# ── N-relic search probability ───────────────────────────────────────────── #

def prob_success_in_n(p_per_relic: float, n: int) -> float:
    """P(at least 1 success in n relics) = 1 − (1 − p)^n."""
    if p_per_relic <= 0.0:
        return 0.0
    if p_per_relic >= 1.0:
        return 1.0
    return 1.0 - (1.0 - p_per_relic) ** n


def expected_relics(p_per_relic: float) -> float | None:
    """Expected number of relics to find the first success (geometric mean)."""
    if p_per_relic <= 0.0:
        return None
    return 1.0 / p_per_relic


def format_duration(seconds: float) -> str:
    """Format a duration in seconds as a human-readable string."""
    if seconds < 60:
        return f"~{int(seconds)} sec"
    if seconds < 3600:
        return f"~{seconds / 60:.1f} min"
    if seconds < 86400:
        return f"~{seconds / 3600:.1f} hrs"
    return f"~{seconds / 86400:.1f} days"


# ── Curse probability ─────────────────────────────────────────────────────── #
# Curses only exist on Deep of Night relics (relic_type == "night").
# Each curse slot draws independently from TABLE_3000000 (24 curses, uniform weight).
# Curse count per relic varies by size (see DEEP_CURSE_COUNT_DIST).
# Passives do NOT correlate with curse count — draws are fully independent.

# Minimum number of curses that must remain unblocked (enforced by the UI).
MIN_UNBLOCKED_CURSES: int = 3


def prob_curse_pass_on_size(excluded_count: int, size: str) -> float:
    """
    P(a Deep relic of given size has none of its drawn curses in the excluded set).

    Curses draw WITHOUT replacement from NUM_CURSES (24) entries — a curse
    that appears on one slot cannot appear again.  P(none of k draws hit
    any of N blocked) = C(24-N, k) / C(24, k).

    excluded_count: number of curses the user has blocked (0 → always 1.0).
    """
    if excluded_count <= 0:
        return 1.0
    dist = DEEP_CURSE_COUNT_DIST.get(size, {})
    total = 0.0
    for k, pk in dist.items():
        # k==0: relic has no curses → always passes
        if k == 0:
            total += pk
        else:
            # C(24-N, k) / C(24, k) = product((24-N-i)/(24-i) for i in 0..k-1)
            p_pass = 1.0
            for i in range(k):
                p_pass *= (NUM_CURSES - excluded_count - i) / (NUM_CURSES - i)
            total += pk * p_pass
    return total


def prob_curse_pass(excluded_count: int, relic_type: str) -> float:
    """
    P(a randomly purchased relic passes the curse filter).

    For Normal relics (relic_type != 'night'): always 1.0 — no curses.
    For Deep relics: weighted average across size distribution.

    excluded_count is clamped to at most (NUM_CURSES - MIN_UNBLOCKED_CURSES) so
    that blocking every single curse is not modelled as a guaranteed fail (the UI
    prevents it by enforcing the minimum).
    """
    if relic_type != "night" or excluded_count <= 0:
        return 1.0
    excluded_count = min(excluded_count, NUM_CURSES - MIN_UNBLOCKED_CURSES)
    total = 0.0
    for size, p_size in DEEP_SIZE_PROBS.items():
        total += p_size * prob_curse_pass_on_size(excluded_count, size)
    return total


# ── Enhanced probability with exclusions (Deep of Night only) ──────────── #
# Computes P(desired passives appear AND no excluded passive AND no blocked
# curse) using exact enumeration with compat-group elimination across slots.
# Normal relics have no curses and no exclusive/broad table split, so this
# model only applies to Deep of Night.

def _build_group_index(table: dict, prefix: str) -> dict:
    """Precompute {group_id: [(passive_name, weight), ...]} for a table.

    Group None collects passives with no compat group assignment.
    Also returns total_weight and group_weight_totals.
    """
    groups: dict[int | None, list[tuple[str, int]]] = {}
    for key, weight in table.items():
        name = key[len(prefix):] if key.startswith(prefix) else key
        g = COMPAT_GROUPS.get(name)
        groups.setdefault(g, []).append((name, weight))
    group_totals = {g: sum(w for _, w in entries)
                    for g, entries in groups.items()}
    total = sum(table.values())
    return {"groups": groups, "group_totals": group_totals, "total": total}


# Precompute once at import time
_GI_EXCLUSIVE = _build_group_index(TABLE_2000000, "<Table> ")
_GI_BROAD     = _build_group_index(TABLE_2100000, "<Table> ")


# Precompute Normal mode group indices per slot table + prefix
_GI_NORMAL: dict[str, list[dict]] = {}
for _sz, _slot_defs in _NORMAL_SLOTS.items():
    _GI_NORMAL[_sz] = [_build_group_index(t, pfx)
                       for t, _tot, pfx in _slot_defs]


def _passive_weight_in_group(names: set[str], group_entries: list[tuple[str, int]]) -> int:
    """Sum of weights for passives in `names` that appear in `group_entries`."""
    return sum(w for n, w in group_entries if n in names)


def prob_effective_deep(
    desired: list[str],
    threshold: int,
    excluded_passives: set[str],
    n_blocked_curses: int,
    allowed_colors: list[str] | None = None,
) -> dict[str, float | None]:
    """Exact P(match AND clean) for Deep of Night relics with exclusions.

    Uses recursive slot-by-slot enumeration, branching by compat group at each
    slot.  At each slot the possible outcomes are:
      - Drew a desired passive (from a specific group)
      - Drew an excluded passive (relic is EXCLUDED — prune)
      - Drew a neutral passive (from a specific group or ungrouped)
    Compat-group elimination is applied after each slot draw.

    For cursed slots (TABLE_2000000): curses draw WITHOUT replacement from 24.
    P(none of k draws hit any of N blocked) = C(24-N, k) / C(24, k).

    Returns:
      p_match:       P(criteria satisfied, ignoring exclusions)
      p_clean:       P(criteria satisfied AND no exclusion)
      p_excluded:    P(criteria satisfied BUT excluded by passive or curse)
      n_effective:   1 / p_clean  (expected relics to find a usable match)
    """
    desired_set = set(desired)
    if not desired_set:
        return {"p_match": None, "p_clean": None, "p_excluded": None,
                "n_effective": None}

    if not compat_ok(list(desired_set)):
        return {"p_match": 0.0, "p_clean": 0.0, "p_excluded": 0.0,
                "n_effective": None}

    p_color = 1.0
    if allowed_colors is not None:
        p_color = color_probability("night", allowed_colors)
        if p_color <= 0:
            return {"p_match": 0.0, "p_clean": 0.0, "p_excluded": 0.0,
                    "n_effective": None}

    n_blocked = min(n_blocked_curses, NUM_CURSES - MIN_UNBLOCKED_CURSES)

    total_match = 0.0
    total_clean = 0.0

    for p_var, slot_list in _DEEP_VARIANTS:
        # Determine which slots are cursed (TABLE_2000000)
        is_cursed = [s is _T2M for s in slot_list]
        n_cursed = sum(is_cursed)

        # P(all curses on this variant pass the filter).
        # Curses draw WITHOUT replacement from 24 entries — a curse that
        # appears on one slot is eliminated from the pool for subsequent
        # slots.  P(none of k draws hit any of N blocked) = C(24-N,k)/C(24,k).
        if n_blocked <= 0 or n_cursed == 0:
            p_curses_pass = 1.0
        else:
            # C(24-N, k) / C(24, k) = product((24-N-i)/(24-i) for i in 0..k-1)
            p_curses_pass = 1.0
            for _ci in range(n_cursed):
                p_curses_pass *= (NUM_CURSES - n_blocked - _ci) / (NUM_CURSES - _ci)

        # Identify which group index each slot uses
        slot_gis = [_GI_EXCLUSIVE if s is _T2M else _GI_BROAD
                    for s in slot_list]

        # Recursive enumeration over slots
        p_m, p_c = _enumerate_slots(
            slot_gis, 0, frozenset(), 0,
            desired_set, threshold, excluded_passives,
            p_curses_pass,
        )
        total_match += p_var * p_m
        total_clean += p_var * p_c

    total_match *= p_color
    total_clean *= p_color
    p_excluded = max(0.0, total_match - total_clean)

    return {
        "p_match":     total_match if total_match > 1e-15 else None,
        "p_clean":     total_clean if total_clean > 1e-15 else None,
        "p_excluded":  p_excluded  if p_excluded  > 1e-15 else None,
        "n_effective": (1.0 / total_clean) if total_clean > 1e-15 else None,
    }


def _enumerate_slots(
    slot_gis: list[dict],
    slot_idx: int,
    elim_groups: frozenset,
    n_desired_found: int,
    desired: set[str],
    threshold: int,
    excluded: set[str],
    p_curses_pass: float,
) -> tuple[float, float]:
    """Recursive slot enumeration.  Returns (p_match, p_clean).

    p_match: P(at least `threshold` desired passives found across all slots)
    p_clean: P(match AND no excluded passive in any slot) * p_curses_pass
    """
    n_slots = len(slot_gis)

    # Base case: all slots processed
    if slot_idx >= n_slots:
        if n_desired_found >= threshold:
            return (1.0, p_curses_pass)
        return (0.0, 0.0)

    # Pruning: even if all remaining slots hit desired, can we reach threshold?
    remaining = n_slots - slot_idx
    if n_desired_found + remaining < threshold:
        return (0.0, 0.0)

    gi = slot_gis[slot_idx]
    groups       = gi["groups"]
    group_totals = gi["group_totals"]
    table_total  = gi["total"]

    # Compute available weight after eliminating groups
    avail_weight = table_total - sum(
        group_totals.get(g, 0) for g in elim_groups if g is not None)
    if avail_weight <= 0:
        # All passives eliminated (shouldn't happen in practice)
        return (0.0, 0.0)

    p_match_accum = 0.0
    p_clean_accum = 0.0

    # Iterate over each group (including None for ungrouped)
    for g, entries in groups.items():
        if g is not None and g in elim_groups:
            continue  # this group was eliminated by a prior slot

        g_weight = group_totals[g]
        if g_weight <= 0:
            continue
        p_draw_from_g = g_weight / avail_weight

        # Split this group's weight into: desired, excluded, neutral
        w_desired  = _passive_weight_in_group(desired, entries)
        w_excluded = _passive_weight_in_group(excluded, entries)
        # Remove overlap (a passive in both desired AND excluded is treated
        # as desired — explicit inclusion overrides exclusion)
        w_excl_only = w_excluded - _passive_weight_in_group(
            desired & excluded, entries)
        w_neutral = g_weight - w_desired - w_excl_only

        new_elim = elim_groups | frozenset([g]) if g is not None else elim_groups

        # Branch 1: drew a desired passive from this group
        if w_desired > 0:
            p_desired_in_g = w_desired / g_weight
            p_branch = p_draw_from_g * p_desired_in_g
            sub_m, sub_c = _enumerate_slots(
                slot_gis, slot_idx + 1, new_elim,
                n_desired_found + 1,
                desired, threshold, excluded, p_curses_pass)
            p_match_accum += p_branch * sub_m
            p_clean_accum += p_branch * sub_c

        # Branch 2: drew an excluded (non-desired) passive — relic is EXCLUDED
        # Match can still happen (for p_match), but p_clean = 0
        if w_excl_only > 0:
            p_excl_in_g = w_excl_only / g_weight
            p_branch = p_draw_from_g * p_excl_in_g
            sub_m, _ = _enumerate_slots(
                slot_gis, slot_idx + 1, new_elim,
                n_desired_found,
                desired, threshold, excluded, p_curses_pass)
            p_match_accum += p_branch * sub_m
            # p_clean stays 0 for this branch (excluded passive found)

        # Branch 3: drew a neutral passive (neither desired nor excluded)
        if w_neutral > 0:
            p_neutral_in_g = w_neutral / g_weight
            p_branch = p_draw_from_g * p_neutral_in_g
            sub_m, sub_c = _enumerate_slots(
                slot_gis, slot_idx + 1, new_elim,
                n_desired_found,
                desired, threshold, excluded, p_curses_pass)
            p_match_accum += p_branch * sub_m
            p_clean_accum += p_branch * sub_c

    return (p_match_accum, p_clean_accum)


def prob_effective_normal(
    desired: list[str],
    threshold: int,
    excluded_passives: set[str],
    allowed_colors: list[str] | None = None,
) -> dict[str, float | None]:
    """Exact P(match AND clean) for Normal relics with passive exclusions.

    Normal relics have no curses.  Each size has 1-3 slots drawing from
    different tables (TABLE_310/210/110) with different prefixes.  Compat-group
    elimination across slots is modelled identically to Deep mode.

    Returns same dict shape as prob_effective_deep.
    """
    desired_set = set(desired)
    if not desired_set:
        return {"p_match": None, "p_clean": None, "p_excluded": None,
                "n_effective": None}

    if not compat_ok(list(desired_set)):
        return {"p_match": 0.0, "p_clean": 0.0, "p_excluded": 0.0,
                "n_effective": None}

    p_color = 1.0
    if allowed_colors is not None:
        p_color = color_probability("normal", allowed_colors)
        if p_color <= 0:
            return {"p_match": 0.0, "p_clean": 0.0, "p_excluded": 0.0,
                    "n_effective": None}

    total_match = 0.0
    total_clean = 0.0

    for size, p_size in NORMAL_SIZE_PROBS.items():
        slot_gis = _GI_NORMAL.get(size, [])
        if not slot_gis:
            continue

        p_m, p_c = _enumerate_slots(
            slot_gis, 0, frozenset(), 0,
            desired_set, threshold, excluded_passives,
            1.0,  # no curses in Normal mode
        )
        total_match += p_size * p_m
        total_clean += p_size * p_c

    total_match *= p_color
    total_clean *= p_color
    p_excluded = max(0.0, total_match - total_clean)

    return {
        "p_match":     total_match if total_match > 1e-15 else None,
        "p_clean":     total_clean if total_clean > 1e-15 else None,
        "p_excluded":  p_excluded  if p_excluded  > 1e-15 else None,
        "n_effective": (1.0 / total_clean) if total_clean > 1e-15 else None,
    }
