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
# TABLE_2200000 does NOT appear in any bazaar relic — it was a datamine error.
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

    Each curse slot draws independently from NUM_CURSES options.  If excluded_count
    curses are blocked, each slot has (NUM_CURSES - excluded_count) / NUM_CURSES
    chance of being acceptable.  The overall probability is the weighted average
    across possible curse counts for this size.

    excluded_count: number of curses the user has blocked (0 → always 1.0).
    """
    if excluded_count <= 0:
        return 1.0
    dist = DEEP_CURSE_COUNT_DIST.get(size, {})
    p_ok_per_slot = (NUM_CURSES - excluded_count) / NUM_CURSES
    total = 0.0
    for k, pk in dist.items():
        # k==0: relic has no curses → always passes
        total += pk * (p_ok_per_slot ** k)
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
