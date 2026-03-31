"""
Relic criteria builder widget.

Provides two modes selectable via a notebook (tab bar):
  1. Exact Relic  – build up to 20 relic targets, each with 3 slots and a
                    configurable match threshold (≥2 or all 3 passives).
                    Incompatible passives (same exclusive category) are
                    flagged and blocked.
  2. Passive Pool – select any number of passives; match when a relic has
                    at least N of them simultaneously.
"""

import math
import re
import tkinter as tk
from tkinter import ttk


def _fmt_pct(pct: float) -> str:
    """Format a percentage value (already ×100) with adaptive decimal places.
    Shows at least 2 decimal places; extends until the first non-zero digit
    appears, so very small odds like 0.0003% are not rounded away to 0.00%."""
    decimals = 2
    while decimals < 12 and round(pct, decimals) == 0.0:
        decimals += 1
    return f"{pct:.{decimals}f}"

from ui import theme, relic_images
from bot.passives import (
    ALL_PASSIVES_SORTED, CATEGORIES, UI_CATEGORIES,
    COMPAT_GROUPS, get_compat_violations, DEBUFFS,
)
from bot.probability_engine import (
    prob_combo_on_relic, prob_any_combo_on_relic,
    prob_passive_on_relic, prob_at_least_k_of_pool,
    compat_ok,
    DEEP_POOL_PASSIVES, NORMAL_POOL_PASSIVES,
)

_DEBUFFS_SET: frozenset = frozenset(DEBUFFS)
_CURSE_CATS: frozenset = frozenset(
    {"Demerits (Attributes)", "Demerits (Damage Negation)", "Demerits (Action)"}
)


def _passive_variants(passive: str) -> list[str]:
    """Return all passives sharing the same base name (differ only in +N suffix)."""
    base = re.sub(r'\s*[+\-]?\d+(%?)$', '', passive).strip()
    return [p for p in ALL_PASSIVES_SORTED
            if re.sub(r'\s*[+\-]?\d+(%?)$', '', p).strip() == base]


def _entry_label(entry: dict) -> str:
    """Display string for a pool entry in the listbox."""
    accepted = entry.get("accepted", [])
    if not accepted:
        return "(empty)"
    if len(accepted) == 1:
        return accepted[0]
    prefix = accepted[0]
    for a in accepted[1:]:
        while prefix and not a.startswith(prefix):
            prefix = prefix[:-1]
    prefix = prefix.rstrip()
    if prefix:
        suffixes = [a[len(prefix):].strip() for a in accepted]
        return f"{prefix} ({', '.join(suffixes)})"
    return " / ".join(accepted)


# ─────────────────────────────────────────────────────────────────────────── #
#  LOW-LEVEL REUSABLE WIDGET
# ─────────────────────────────────────────────────────────────────────────── #

class _SearchableListbox(ttk.Frame):
    """Search entry + scrollable listbox combo."""

    def __init__(self, parent, items: list, height: int = 10, **kwargs):
        super().__init__(parent, **kwargs)
        self._all = items
        self._build(height)

    def _build(self, height: int):
        self._var = tk.StringVar()
        self._var.trace_add("write", self._on_type)
        self._excluded: set = set()   # passives hidden from this listbox

        search = ttk.Entry(self, textvariable=self._var)
        search.pack(fill="x", pady=(0, 2))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        self._lb = tk.Listbox(
            body, height=height, selectmode="browse",
            exportselection=False, activestyle="none",
        )
        theme.style_listbox(self._lb)
        sb = ttk.Scrollbar(body, orient="vertical", command=self._lb.yview)
        self._lb.configure(yscrollcommand=sb.set)
        self._lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Consume mousewheel events so they scroll this listbox, not the main canvas
        self._lb.bind("<MouseWheel>",
                      lambda e: (self._lb.yview_scroll(int(-1 * (e.delta / 120)), "units"), "break")[1])

        self._refresh(self._all)

    def _on_type(self, *_):
        q = self._var.get().strip().lower()
        self._refresh(
            [x for x in self._all if q in x.lower()] if q else self._all
        )

    def _refresh(self, items: list):
        self._lb.delete(0, "end")
        for item in items:
            if item not in self._excluded:
                self._lb.insert("end", item)

    def set_items(self, items: list):
        """Replace the item list and refresh the display."""
        self._all = items
        self._on_type()

    def set_excluded(self, excluded: set):
        """Update the hidden-passives set and redisplay."""
        self._excluded = excluded
        self._on_type()   # re-run search so new exclusions take effect

    def get_selected(self) -> str | None:
        sel = self._lb.curselection()
        return self._lb.get(sel[0]) if sel else None

    def bind_select(self, cb):
        self._lb.bind("<<ListboxSelect>>", cb)

    def clear_search(self):
        self._var.set("")


# ─────────────────────────────────────────────────────────────────────────── #
#  SINGLE SLOT SELECTOR  (used by the Exact Relic tab)
# ─────────────────────────────────────────────────────────────────────────── #

class _SlotSelector(ttk.LabelFrame):
    """One passive slot in the Exact Relic builder."""

    _ANY = "(any)"

    def __init__(self, parent, slot_num: int, on_change=None, **kwargs):
        super().__init__(parent, text=f"Slot {slot_num}", **kwargs)
        self._chosen = tk.StringVar(value=self._ANY)
        self._on_change = on_change
        self._build()

    def _build(self):
        cat_row = ttk.Frame(self)
        cat_row.pack(fill="x", padx=4, pady=(4, 0))
        ttk.Label(cat_row, text="Category:").pack(side="left")
        self._cat_var = tk.StringVar(value="(all)")
        cats = ["(all)"] + list(UI_CATEGORIES.keys())
        cat_cb = ttk.Combobox(cat_row, textvariable=self._cat_var, values=cats,
                               state="readonly", width=22)
        cat_cb.pack(side="left", padx=4)
        cat_cb.bind("<<ComboboxSelected>>", self._on_cat_change)

        self._lb = _SearchableListbox(self, ALL_PASSIVES_SORTED, height=9)
        self._lb.pack(fill="both", expand=True, padx=4, pady=(2, 2))
        self._lb.bind_select(self._on_pick)

        foot = ttk.Frame(self)
        foot.pack(fill="x", padx=4, pady=(0, 4))

        ttk.Label(foot, text="→").pack(side="left")
        ttk.Label(
            foot, textvariable=self._chosen,
            foreground="#7ec8f0", wraplength=190, justify="left",
        ).pack(side="left", padx=(4, 0), fill="x", expand=True)
        ttk.Button(foot, text="✕", width=3, command=self._clear).pack(side="right")

    def _on_cat_change(self, _event=None):
        cat = self._cat_var.get()
        pool = getattr(self, "_mode_pool", None)
        if cat == "(all)":
            items = ([p for p in ALL_PASSIVES_SORTED if p in pool]
                     if pool is not None else ALL_PASSIVES_SORTED)
        else:
            base = sorted(UI_CATEGORIES.get(cat, []), key=str.casefold)
            items = [p for p in base if p in pool] if pool is not None else base
        self._lb.set_items(items)
        self._lb.clear_search()

    def _on_pick(self, _event=None):
        val = self._lb.get_selected()
        if val:
            self._chosen.set(val)
            if self._on_change:
                self._on_change()

    def _clear(self):
        self._chosen.set(self._ANY)
        self._lb.clear_search()
        if self._on_change:
            self._on_change()

    def get(self) -> str | None:
        v = self._chosen.get()
        return None if v == self._ANY else v

    def set_value(self, value: str | None):
        """Programmatically set the slot value (None → '(any)')."""
        self._chosen.set(value if value is not None else self._ANY)
        self._lb.clear_search()

    def set_mode_passives(self, relic_type: str):
        """Replace the listbox item pool with passives available in the given mode."""
        self._mode_pool = DEEP_POOL_PASSIVES if relic_type == "night" else NORMAL_POOL_PASSIVES
        self._on_cat_change()

    def set_excluded(self, excluded: set):
        """Delegate exclusion update to the inner listbox."""
        self._lb.set_excluded(excluded)


# ─────────────────────────────────────────────────────────────────────────── #
#  EXACT RELIC TAB  (up to 20 targets, each with 3 slots + threshold)
# ─────────────────────────────────────────────────────────────────────────── #

class _ExactRelicTab(ttk.Frame):
    """
    Manage up to 20 relic targets.  Each target has three passive slots and a
    match threshold (2 = any two specified passives, 3 = all three).  The bot
    considers a relic a MATCH if it satisfies ANY of the defined targets.
    """

    _MAX_TARGETS = 20

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # Each target: {"slots": [str|None, str|None, str|None], "threshold": int}
        self._targets: list[dict] = [self._new_target()]
        self._active: int = 0
        self._slots: list[_SlotSelector] = []
        self._threshold_var = tk.IntVar(value=2)
        self._compat_var = tk.StringVar(value="")
        self._relic_type: str = "night"
        self._allowed_colors: list[str] = ["Red", "Blue", "Green", "Yellow"]
        self._build()

    # ── construction ─────────────────────────────────────────────────── #

    def _set_odds_text(self, text: str) -> None:
        """Update the read-only odds display."""
        self._odds_txt.config(state="normal")
        self._odds_txt.delete("1.0", "end")
        self._odds_txt.insert("1.0", text)
        self._odds_txt.config(state="disabled")

    @staticmethod
    def _new_target() -> dict:
        return {"slots": [None, None, None], "threshold": 2}

    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=8, pady=(6, 0))

        ttk.Label(
            header,
            text=(
                "Build up to 20 relic targets. "
                "For each target, choose passives for up to 3 slots and set the "
                "minimum match threshold. "
                "The bot stops when a relic satisfies ANY target. "
                "Incompatible passive combinations (same exclusive category) are blocked."
            ),
            wraplength=680, justify="left",
        ).pack(side="left", anchor="w", fill="x", expand=True)

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=6, pady=2)
        main.columnconfigure(1, weight=1)

        # ── Left: target list ──────────────────────────────────────────── #
        left = ttk.LabelFrame(main, text="Targets")
        left.grid(row=0, column=0, sticky="ns", padx=(0, 6))

        self._target_lb = tk.Listbox(
            left, height=12, width=24,
            selectmode="browse", exportselection=False, activestyle="none",
        )
        theme.style_listbox(self._target_lb)
        self._target_lb.pack(fill="both", expand=True, padx=4, pady=4)
        self._target_lb.bind("<<ListboxSelect>>", self._on_target_select)
        self._target_lb.bind("<MouseWheel>",
            lambda e: (self._target_lb.yview_scroll(int(-1*(e.delta/120)), "units"), "break")[1])

        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Button(btn_row, text="+ Add", command=self._add_target, width=7).pack(side="left", padx=2)
        ttk.Button(btn_row, text="− Delete", command=self._delete_target, width=7).pack(side="left", padx=2)

        # ── Right: slot editors ────────────────────────────────────────── #
        right = ttk.LabelFrame(main, text="Edit Target")
        right.grid(row=0, column=1, sticky="nsew")

        cols = ttk.Frame(right)
        cols.pack(fill="both", expand=True, padx=4, pady=4)
        for i in range(3):
            s = _SlotSelector(cols, i + 1, on_change=self._on_slot_change)
            s.grid(row=0, column=i, sticky="nsew", padx=4, pady=2)
            cols.columnconfigure(i, weight=1)
            self._slots.append(s)

        # ── Threshold + compat warning ─────────────────────────────────── #
        foot = ttk.Frame(right)
        foot.pack(fill="x", padx=8, pady=(0, 6))

        ttk.Label(foot, text="Match when ≥").pack(side="left")
        self._threshold_spin = ttk.Spinbox(
            foot, from_=1, to=3, textvariable=self._threshold_var,
            width=3, command=self._on_threshold_change,
        )
        self._threshold_spin.pack(side="left", padx=4)
        ttk.Label(foot, text="of the specified passives are present.").pack(side="left")

        self._compat_lbl = ttk.Label(
            foot, textvariable=self._compat_var,
            foreground="#ff6666", wraplength=440,
        )
        self._compat_lbl.pack(anchor="w", padx=8, pady=(4, 0))

        # ── Odds display ──────────────────────────────────────────────────── #
        odds_frame = ttk.LabelFrame(right, text="Odds  (per relic)")
        odds_frame.pack(fill="x", padx=6, pady=(2, 6))

        from ui import theme as _theme
        _odds_container = ttk.Frame(odds_frame)
        _odds_container.pack(fill="x", padx=6, pady=(4, 2))
        _odds_sb = ttk.Scrollbar(_odds_container, orient="vertical")
        _odds_sb.pack(side="right", fill="y")
        self._odds_txt = tk.Text(
            _odds_container, height=8, wrap="word", state="disabled",
            bg=_theme.INPUT_BG, fg="#90c890",
            relief="flat", bd=0, highlightthickness=0,
            font=("TkDefaultFont", 9),
            yscrollcommand=_odds_sb.set,
        )
        self._odds_txt.pack(side="left", fill="x", expand=True)
        _odds_sb.config(command=self._odds_txt.yview)
        self._odds_txt.bind("<1>", lambda e: self._odds_txt.focus_set())
        self._odds_txt.bind("<MouseWheel>",
            lambda e: (self._odds_txt.yview_scroll(int(-1*(e.delta/120)), "units"), "break")[1])
        self._set_odds_text("Select passives above to see odds.")
        self._odds_disclaimer_var = tk.StringVar(
            value="Odds from AttachEffectTableParam. Per-relic rate accounts for size distribution and color filter.")
        ttk.Label(
            odds_frame, textvariable=self._odds_disclaimer_var,
            foreground=theme.TEXT_MUTED, wraplength=860,
        ).pack(anchor="w", padx=6, pady=(0, 4))

        # Populate initial state
        self._refresh_list()
        self._target_lb.selection_set(0)

    # ── target list management ────────────────────────────────────────── #

    def _refresh_list(self):
        self._target_lb.delete(0, "end")
        for i, t in enumerate(self._targets):
            filled = [s for s in t["slots"] if s]
            summary = " / ".join(s[:20] for s in filled) if filled else "(empty)"
            self._target_lb.insert("end", f" #{i + 1}: {summary}")

    def _on_target_select(self, _event=None):
        sel = self._target_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx == self._active:
            return
        self._save_current()
        self._active = idx
        self._load_active()

    def _save_current(self):
        if self._active >= len(self._targets):
            return
        t = self._targets[self._active]
        t["slots"] = [s.get() for s in self._slots]
        t["threshold"] = self._threshold_var.get()

    def _load_active(self):
        t = self._targets[self._active]
        for s, val in zip(self._slots, t["slots"]):
            s.set_value(val)
        self._threshold_var.set(t["threshold"])
        self._update_exclusions()
        self._check_compat()
        self._update_odds()
        self._refresh_list()
        self._target_lb.selection_clear(0, "end")
        self._target_lb.selection_set(self._active)

    def import_target(self, passives: list[str]) -> bool:
        """
        Add a new target pre-filled with up to 3 passives from the Build Advisor.
        Returns True on success, False if at max capacity.
        """
        # Filter to only valid passives
        from bot.passives import ALL_PASSIVES
        valid = [p for p in passives if p in ALL_PASSIVES][:3]
        if not valid:
            return False
        if len(self._targets) >= self._MAX_TARGETS:
            return False
        self._save_current()
        t = self._new_target()
        for i, p in enumerate(valid):
            t["slots"][i] = p
        self._targets.append(t)
        self._active = len(self._targets) - 1
        self._load_active()
        return True

    def _add_target(self):
        if len(self._targets) >= self._MAX_TARGETS:
            return
        self._save_current()
        self._targets.append(self._new_target())
        self._active = len(self._targets) - 1
        self._load_active()

    def _delete_target(self):
        if len(self._targets) <= 1:
            self._targets[0] = self._new_target()
            self._load_active()
            return
        self._targets.pop(self._active)
        self._active = min(self._active, len(self._targets) - 1)
        self._load_active()

    # ── slot / threshold handlers ─────────────────────────────────────── #

    def _on_slot_change(self):
        # 1. Recompute which passives are hidden in every other slot.
        self._update_exclusions()
        # 2. Auto-clear any slot whose current value is now excluded (edge case:
        #    user changed one slot to something that conflicts with another).
        self._clear_newly_excluded()
        self._check_compat()
        self._update_odds()
        self._save_current()
        self._refresh_list()
        self._target_lb.selection_set(self._active)

    def set_relic_context(self, relic_type: str, allowed_colors: list[str]) -> None:
        """Called by RelicBuilderFrame when relic type or color selection changes."""
        self._relic_type = relic_type
        self._allowed_colors = list(allowed_colors)
        pool_label = "Deep of Night" if relic_type == "night" else "Normal"
        color_note = (f"{len(allowed_colors)} color(s) selected"
                      if len(allowed_colors) < 4 else "all colors")
        self._odds_disclaimer_var.set(
            f"Odds from AttachEffectTableParam ({pool_label} pools, {color_note}). "
            f"Per-relic rate accounts for size distribution and color filter.")
        # Update slot listboxes to show only passives available in the current mode
        for slot in self._slots:
            slot.set_mode_passives(relic_type)
        self._update_odds()

    def _on_threshold_change(self):
        self._save_current()
        self._update_odds()

    def _update_exclusions(self):
        """
        For each slot, compute the set of passives it must NOT show
        and push that set into the slot's listbox.

        Two exclusion rules:
          • Compat group  — if passive belongs to an exclusive compat group,
            hide every other member of that group in all other slots.
          • Variant family — if passive has no compat group (or belongs to
            the "special" tier-variant families), hide all passives that share
            the same base name (e.g. selecting "Stamina Recovery upon Landing
            Attacks" hides the "+1" variant and vice-versa).  This prevents
            duplicate-family passives from appearing on the same relic.
        """
        slot_vals = [s.get() for s in self._slots]
        for i, slot in enumerate(self._slots):
            excluded: set = set()
            for j, val in enumerate(slot_vals):
                if j == i or val is None:
                    continue
                gj = COMPAT_GROUPS.get(val)
                if gj is None:
                    # No exclusive compat group — still block tier variants of
                    # this passive (same base name, e.g. base ↔ +1 ↔ +2 …).
                    for p in _passive_variants(val):
                        excluded.add(p)
                    continue
                # Hide every passive that shares this compat group
                for passive, g in COMPAT_GROUPS.items():
                    if g == gj:
                        excluded.add(passive)
            slot.set_excluded(excluded)

    def _clear_newly_excluded(self):
        """
        If any slot's current value is now inside its own excluded set,
        clear that slot.  Iterates until stable in case clearing cascades.
        """
        changed = True
        while changed:
            changed = False
            for slot in self._slots:
                val = slot.get()
                if val is not None and val in slot._lb._excluded:
                    slot.set_value(None)
                    changed = True
            if changed:
                self._update_exclusions()

    def _check_compat(self):
        slots = [s.get() for s in self._slots]
        violations = get_compat_violations(slots)
        if violations:
            msgs = [
                f"Slots {i + 1} & {j + 1}: both are '{name}' – can't appear on same relic."
                for i, j, name in violations
            ]
            self._compat_var.set("⚠  " + "   |   ".join(msgs))
        else:
            self._compat_var.set("")

    def _update_odds(self):
        """Recompute and display odds for the currently active target."""
        rtype  = self._relic_type
        colors = self._allowed_colors

        slots  = [s.get() for s in self._slots]
        filled = [(i, p) for i, p in enumerate(slots) if p]

        if not filled:
            self._set_odds_text("Select passives above to see odds.")
            self._propagate_p(None)
            return

        violations = get_compat_violations(slots)
        if violations:
            self._set_odds_text("Cannot calculate — incompatible passives selected.")
            self._propagate_p(None)
            return

        targets = [p for _, p in filled]
        thresh  = self._threshold_var.get()
        lines   = []

        # ── Per-passive odds (per-relic, color-filtered) ─────────────────────
        pool_name = "Deep of Night" if rtype == "night" else "Normal"
        for i, p in filled:
            p_relic = prob_passive_on_relic(p, rtype, colors)
            if p_relic and p_relic > 0:
                n_r = int(round(1.0 / p_relic))
                pct = p_relic * 100
                lines.append(f"  {p}  →  {_fmt_pct(pct)}%  (~1 in {n_r:,} per relic)")
            elif p_relic == 0.0:
                lines.append(f"  {p}  →  Impossible — not available on {pool_name} Relics")
            else:
                lines.append(f"  {p}  →  not in {pool_name} pool")

        # ── This target probability (color-filtered, size-weighted) ─────────
        lines.append("")
        n_filled = len(filled)
        p_this: float | None = None

        if thresh >= n_filled:
            p_this = prob_combo_on_relic(targets, rtype, colors)
            if p_this and p_this > 0:
                n = int(round(1.0 / p_this))
                pct = p_this * 100
                lines.append(f"  This target (all {n_filled}): {_fmt_pct(pct)}%  (~1 in {n:,} per relic)")
            elif p_this == 0.0:
                lines.append(f"  Impossible Combo — can't be rolled on {pool_name} Relics")
            else:
                lines.append(f"  This target: odds unknown (passive may not be in pool)")
        else:
            per_p    = [prob_passive_on_relic(t, rtype, colors) or 0.0 for t in targets]
            p_thresh = prob_at_least_k_of_pool(per_p, thresh)
            p_all    = prob_combo_on_relic(targets, rtype, colors)
            p_this   = p_thresh if p_thresh > 0 else p_all
            if p_thresh > 0:
                n_thresh = int(round(1.0 / max(p_thresh, 1e-12)))
                pct_thresh = p_thresh * 100
                lines.append(f"  This target (≥{thresh} of {n_filled}): {_fmt_pct(pct_thresh)}%  (~1 in {n_thresh:,} per relic)")
            if p_all and p_all > 0:
                n_all = int(round(1.0 / max(p_all, 1e-12)))
                pct_all = p_all * 100
                lines.append(f"  This target (all {n_filled}): {_fmt_pct(pct_all)}%  (~1 in {n_all:,} per relic)")

        # ── All defined targets combined (any target matches) ────────────────
        self._save_current()
        all_valid = [
            {"slots": [p for p in t["slots"] if p], "threshold": t["threshold"]}
            for t in self._targets
            if any(t["slots"])
        ]
        p_combined: float | None = None

        if len(all_valid) > 1:
            complement = 1.0
            found_any  = False
            for t in all_valid:
                t_slots  = t["slots"]
                t_thresh = t["threshold"]
                if t_thresh >= len(t_slots):
                    p = prob_combo_on_relic(t_slots, rtype, colors)
                else:
                    pp_list = [prob_passive_on_relic(s, rtype, colors) or 0.0 for s in t_slots]
                    p = prob_at_least_k_of_pool(pp_list, t_thresh)
                if p and p > 0:
                    complement *= max(0.0, 1.0 - p)
                    found_any   = True
            if found_any:
                p_combined = max(0.0, 1.0 - complement)
                if p_combined > 0:
                    n_any = int(round(1.0 / max(p_combined, 1e-12)))
                    pct_any = p_combined * 100
                    lines.append(f"  Odds of meeting any of {len(all_valid)} targets: {_fmt_pct(pct_any)}%  (~1 in {n_any:,} per relic)")

        self._propagate_p(p_combined if p_combined is not None else p_this)
        self._set_odds_text("\n".join(lines))

    def _propagate_p(self, p: float | None) -> None:
        """Push the current per-relic probability up to RelicBuilderFrame."""
        try:
            nb = self.nametowidget(self.winfo_parent())
            rb = self.nametowidget(nb.winfo_parent())
            if hasattr(rb, "_set_p_per_relic"):
                rb._set_p_per_relic(p)
        except Exception:
            pass

    def has_compat_errors(self) -> bool:
        """Return True if any defined target has incompatible passive combinations."""
        self._save_current()
        for t in self._targets:
            if get_compat_violations(t["slots"]):
                return True
        return False

    # ── criteria generation ───────────────────────────────────────────── #

    def get_criteria_prompt(self) -> str:
        self._save_current()
        valid = [t for t in self._targets if any(t["slots"])]
        if not valid:
            return ""

        if len(valid) == 1:
            t = valid[0]
            thresh = t["threshold"]
            lines = ["I am searching for a relic with these passives:", ""]
            for i, v in enumerate(t["slots"]):
                if v:
                    lines.append(f"  Slot {i + 1}: {v}")
                else:
                    lines.append(f"  Slot {i + 1}: (any – ignore this slot)")
            lines += [
                "",
                f"The relic is a MATCH if it has at least {thresh} of the specified passives.",
                "Slots marked '(any)' can contain any passive.",
            ]
            return "\n".join(lines)

        lines = [
            f"I am searching for a relic matching ANY of the following {len(valid)} targets.",
            "The relic is a MATCH if it satisfies at least one target.",
            "",
        ]
        for ti, t in enumerate(valid, 1):
            thresh = t["threshold"]
            filled = [v for v in t["slots"] if v]
            lines.append(
                f"Target {ti}  (≥ {thresh} of {len(filled)} specified passive(s) must be present):"
            )
            for i, v in enumerate(t["slots"]):
                lines.append(f"  Slot {i + 1}: {v if v else '(any)'}")
            lines.append("")
        return "\n".join(lines)

    def get_criteria_dict(self) -> dict:
        """Return structured criteria dict for the local analyzer."""
        self._save_current()
        valid = [t for t in self._targets if any(t["slots"])]
        return {
            "mode": "exact",
            "targets": [
                {"passives": [s for s in t["slots"] if s], "threshold": t["threshold"]}
                for t in valid
            ],
        }

    def is_valid(self) -> bool:
        self._save_current()
        return any(any(t["slots"]) for t in self._targets)

    def get_min_hit_threshold(self) -> int:
        """
        Return the minimum passive count needed to qualify as a HIT tier.
        This equals the lowest threshold across all valid (non-empty) targets.
        If every target requires all 3 passives, returns 3 so that 2/3 near-misses
        are not counted as hits.  If any target only requires ≥2, returns 2.
        """
        self._save_current()
        valid = [t for t in self._targets if any(t["slots"])]
        if not valid:
            return 2
        return min(t["threshold"] for t in valid)

    # ── state serialization ───────────────────────────────────────────── #

    def get_state(self) -> dict:
        self._save_current()
        return {
            "targets": [{"slots": list(t["slots"]), "threshold": t["threshold"]} for t in self._targets],
            "active": self._active,
        }

    def set_state(self, state: dict):
        targets = state.get("targets", [])
        self._targets = [
            {"slots": list(t.get("slots", [None, None, None])), "threshold": t.get("threshold", 2)}
            for t in targets
        ] or [self._new_target()]
        self._active = min(state.get("active", 0), len(self._targets) - 1)
        self._load_active()


# ─────────────────────────────────────────────────────────────────────────── #
#  VARIANT DIALOG  (select which +N versions to accept)
# ─────────────────────────────────────────────────────────────────────────── #

class _VariantDialog(tk.Toplevel):
    """Modal dialog: select which +N versions of a passive are acceptable."""

    def __init__(self, parent, passive: str, variants: list[str]):
        super().__init__(parent)
        self.title("Select Versions to Accept")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.result: list[str] | None = None
        self.configure(bg=theme.BG)

        ttk.Label(
            self,
            text="Select which versions of this passive you will accept on a relic:",
            wraplength=360,
        ).pack(padx=14, pady=(12, 4))

        inner = ttk.Frame(self)
        inner.pack(padx=14, pady=4, fill="x")
        self._vars: dict[str, tk.BooleanVar] = {}
        for v in variants:
            var = tk.BooleanVar(value=(v == passive))
            self._vars[v] = var
            ttk.Checkbutton(inner, text=v, variable=var).pack(anchor="w", pady=1)

        btn_row = ttk.Frame(self)
        btn_row.pack(padx=14, pady=(6, 12))
        ttk.Button(btn_row, text="Add Selected", command=self._ok).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Cancel",        command=self.destroy).pack(side="left")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window()

    def _ok(self):
        sel = [v for v, var in self._vars.items() if var.get()]
        if sel:
            self.result = sel
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────── #
#  PARTNER DIALOG  (pick passives to require alongside a pool entry)
# ─────────────────────────────────────────────────────────────────────────── #

class _CreatePairingDialog(tk.Toplevel):
    """
    Select two passives (with optional +N variant sets) to form a required pair.
    Both passives must appear on the same relic for the pair to count as a match.
    Neither passive needs to be in My Pool.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Create Pairing")
        self.transient(parent)
        self.grab_set()
        self.resizable(True, True)
        self.geometry("720x520")
        self.result: tuple[list[str], list[str]] | None = None   # (left_accepted, right_accepted)
        self.configure(bg=theme.BG)
        self._left:  list[str] = []
        self._right: list[str] = []

        ttk.Label(
            self,
            text=(
                "Choose one passive for each side. Both must appear on the same relic "
                "for this pair to count as a match.\n"
                "Passives with +N variants let you accept multiple versions at once."
            ),
            wraplength=680, justify="left",
        ).pack(padx=12, pady=(10, 6))

        cols = ttk.Frame(self)
        cols.pack(fill="both", expand=True, padx=12, pady=2)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(2, weight=1)

        # ── Left picker ──────────────────────────────────────────────── #
        left_frame = ttk.LabelFrame(cols, text="Left Passive")
        left_frame.grid(row=0, column=0, sticky="nsew")
        _pair_mode_passives = (
            sorted(DEEP_POOL_PASSIVES, key=str.casefold)
            if getattr(parent, "_relic_type", "night") == "night"
            else sorted(NORMAL_POOL_PASSIVES, key=str.casefold)
        )
        self._left_lb = _SearchableListbox(left_frame, _pair_mode_passives, height=13)
        self._left_lb.pack(fill="both", expand=True, padx=4, pady=(4, 2))
        ttk.Button(left_frame, text="✔ Select for Left",
                   command=self._select_left).pack(padx=4, pady=(0, 4))

        # ── Divider ──────────────────────────────────────────────────── #
        ttk.Label(cols, text="↔", font=("", 16, "bold")).grid(
            row=0, column=1, padx=10)

        # ── Right picker ─────────────────────────────────────────────── #
        right_frame = ttk.LabelFrame(cols, text="Right Passive")
        right_frame.grid(row=0, column=2, sticky="nsew")
        self._right_lb = _SearchableListbox(right_frame, _pair_mode_passives, height=13)
        self._right_lb.pack(fill="both", expand=True, padx=4, pady=(4, 2))
        ttk.Button(right_frame, text="✔ Select for Right",
                   command=self._select_right).pack(padx=4, pady=(0, 4))

        cols.rowconfigure(0, weight=1)

        # ── Status / confirm row ──────────────────────────────────────── #
        status_row = ttk.Frame(self)
        status_row.pack(fill="x", padx=12, pady=(4, 2))
        self._left_lbl  = ttk.Label(status_row, text="Left:  (none selected)",
                                     foreground=theme.TEXT_MUTED)
        self._left_lbl.pack(side="left", padx=4)
        self._right_lbl = ttk.Label(status_row, text="Right: (none selected)",
                                     foreground=theme.TEXT_MUTED)
        self._right_lbl.pack(side="right", padx=4)

        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", padx=12, pady=(2, 12))
        ttk.Button(btn_row, text="Create Pairing", command=self._confirm).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Cancel",         command=self.destroy).pack(side="left")
        self._err_lbl = ttk.Label(btn_row, text="", foreground="#cc3300")
        self._err_lbl.pack(side="left", padx=8)

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window()

    def _pick_variants(self, passive: str) -> list[str] | None:
        """If the passive has +N variants, ask user which to accept. Else return [passive]."""
        variants = _passive_variants(passive)
        if len(variants) > 1:
            dlg = _VariantDialog(self, passive, variants)
            return dlg.result   # None if cancelled
        return [passive]

    def _select_left(self):
        p = self._left_lb.get_selected()
        if not p:
            return
        accepted = self._pick_variants(p)
        if not accepted:
            return
        self._left = accepted
        label = accepted[0] if len(accepted) == 1 else f"{accepted[0]}… (+{len(accepted)-1} variant(s))"
        self._left_lbl.configure(text=f"Left:  {label}", foreground="")

    def _select_right(self):
        p = self._right_lb.get_selected()
        if not p:
            return
        accepted = self._pick_variants(p)
        if not accepted:
            return
        self._right = accepted
        label = accepted[0] if len(accepted) == 1 else f"{accepted[0]}… (+{len(accepted)-1} variant(s))"
        self._right_lbl.configure(text=f"Right: {label}", foreground="")

    def _confirm(self):
        if not self._left:
            self._err_lbl.configure(text="Select a Left passive first.")
            return
        if not self._right:
            self._err_lbl.configure(text="Select a Right passive first.")
            return
        self.result = (self._left, self._right)
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────── #
#  PASSIVE POOL TAB  (pick N passives, match ≥ threshold, optional pairing)
# ─────────────────────────────────────────────────────────────────────────── #

class _PassivePoolTab(ttk.Frame):
    """
    Multi-select passive pool with configurable threshold and optional pairing.

    Each pool entry accepts one or more passive names (variant multi-select via Feature 2).
    An entry can optionally require a partner: it only counts toward the threshold if
    at least one of its required partners is also present on the relic (Feature 1).
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # Pool entries: {"accepted": list[str]}  (no pair_required — pairings are separate)
        self._entries: list[dict] = []
        # Pairings: {"left": list[str], "right": list[str]}  (independent of pool)
        self._pairings: list[dict] = []
        self._relic_type: str = "night"
        self._allowed_colors: list[str] = ["Red", "Blue", "Green", "Yellow"]
        self._build()

    def _set_odds_text(self, text: str) -> None:
        """Update the read-only odds display."""
        self._odds_txt.config(state="normal")
        self._odds_txt.delete("1.0", "end")
        self._odds_txt.insert("1.0", text)
        self._odds_txt.config(state="disabled")

    def _build(self):
        note = ttk.Label(
            self,
            text=(
                "Add passives you want to the pool. "
                "A relic matches if it has at least the specified number of pool passives. "
                "Passives with +N variants let you accept multiple versions at once. "
                "Use pairing to require two passives to appear together."
            ),
            wraplength=700, justify="left",
        )
        note.pack(anchor="w", padx=8, pady=(6, 4))

        content = ttk.Frame(self)
        content.pack(fill="both", expand=True, padx=6, pady=2)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(2, weight=2)

        # ── Left: All Passives ─────────────────────────────────────────────── #
        left = ttk.LabelFrame(content, text="All Passives")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        cat_row = ttk.Frame(left)
        cat_row.pack(fill="x", padx=4, pady=(4, 0))
        ttk.Label(cat_row, text="Category:").pack(side="left")
        self._cat_var = tk.StringVar(value="(all)")
        # Exclude Demerit (curse) categories — curses are not selectable as passives
        _non_curse_cats = [c for c in CATEGORIES.keys() if c not in _CURSE_CATS]
        cats = ["(all)"] + _non_curse_cats
        cat_cb = ttk.Combobox(cat_row, textvariable=self._cat_var, values=cats,
                               state="readonly", width=34)
        cat_cb.pack(side="left", padx=4)
        cat_cb.bind("<<ComboboxSelected>>", self._on_cat_change)

        self._left_lb = _SearchableListbox(left, ALL_PASSIVES_SORTED, height=11)
        self._left_lb.pack(fill="both", expand=True, padx=4, pady=4)

        # ── Centre: action buttons ─────────────────────────────────────────── #
        mid = ttk.Frame(content)
        mid.grid(row=0, column=1, padx=6)
        ttk.Button(mid, text="Add →",    command=self._add,       width=10).pack(pady=4)
        ttk.Button(mid, text="← Remove", command=self._remove,    width=10).pack(pady=4)
        ttk.Button(mid, text="Clear All",command=self._clear_all, width=10).pack(pady=8)

        # ── Right: My Pool + Pairing ───────────────────────────────────────── #
        right = ttk.Frame(content)
        right.grid(row=0, column=2, sticky="nsew")
        right.rowconfigure(0, weight=2)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        pool_frame = ttk.LabelFrame(right, text="My Pool")
        pool_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 4))

        body_r = ttk.Frame(pool_frame)
        body_r.pack(fill="both", expand=True, padx=4, pady=4)
        self._sel_lb = tk.Listbox(body_r, height=8, selectmode="browse",
                                   exportselection=False, activestyle="none")
        theme.style_listbox(self._sel_lb)
        sb_r = ttk.Scrollbar(body_r, orient="vertical", command=self._sel_lb.yview)
        self._sel_lb.configure(yscrollcommand=sb_r.set)
        self._sel_lb.pack(side="left", fill="both", expand=True)
        sb_r.pack(side="right", fill="y")
        self._sel_lb.bind("<MouseWheel>",
            lambda e: (self._sel_lb.yview_scroll(int(-1*(e.delta/120)), "units"), "break")[1])

        # Pairings — independent of My Pool; each pair counts as 1 match when both present
        pair_frame = ttk.LabelFrame(right, text="Pairings  (both must be present → counts as 1 match)")
        pair_frame.grid(row=1, column=0, sticky="nsew")

        ttk.Label(pair_frame,
                  text="Each pair is independent — neither passive needs to be in My Pool.",
                  foreground=theme.TEXT_MUTED, wraplength=260).pack(anchor="w", padx=6, pady=(4, 0))

        pair_body = ttk.Frame(pair_frame)
        pair_body.pack(fill="both", expand=True, padx=4, pady=2)
        self._pair_lb = tk.Listbox(pair_body, height=5, selectmode="browse",
                                    exportselection=False, activestyle="none")
        theme.style_listbox(self._pair_lb)
        sb_p = ttk.Scrollbar(pair_body, orient="vertical", command=self._pair_lb.yview)
        self._pair_lb.configure(yscrollcommand=sb_p.set)
        self._pair_lb.pack(side="left", fill="both", expand=True)
        sb_p.pack(side="right", fill="y")
        self._pair_lb.bind("<MouseWheel>",
            lambda e: (self._pair_lb.yview_scroll(int(-1*(e.delta/120)), "units"), "break")[1])

        pair_btns = ttk.Frame(pair_frame)
        pair_btns.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Button(pair_btns, text="+ Create Pairing", command=self._create_pairing, width=16).pack(side="left", padx=2)
        ttk.Button(pair_btns, text="X Remove",         command=self._remove_pairing, width=10).pack(side="left", padx=2)

        # ── Threshold row ──────────────────────────────────────────────────── #
        foot = ttk.Frame(self)
        foot.pack(fill="x", padx=8, pady=6)
        ttk.Label(foot, text="Match when relic has at least").pack(side="left")
        self._threshold = tk.IntVar(value=2)
        self._spin = ttk.Spinbox(foot, from_=1, to=3, textvariable=self._threshold, width=4,
                                  command=self._on_threshold_change)
        self._spin.pack(side="left", padx=4)
        self._count_lbl = tk.StringVar(value="of 0 passives in pool")
        ttk.Label(foot, textvariable=self._count_lbl).pack(side="left")

        # ── Odds display ───────────────────────────────────────────────────── #
        odds_frame = ttk.LabelFrame(self, text="Odds  (per relic)")
        odds_frame.pack(fill="x", padx=8, pady=(0, 6))

        from ui import theme as _theme
        _odds_container = ttk.Frame(odds_frame)
        _odds_container.pack(fill="x", padx=6, pady=(4, 2))
        _odds_sb = ttk.Scrollbar(_odds_container, orient="vertical")
        _odds_sb.pack(side="right", fill="y")
        self._odds_txt = tk.Text(
            _odds_container, height=8, wrap="word", state="disabled",
            bg=_theme.INPUT_BG, fg="#90c890",
            relief="flat", bd=0, highlightthickness=0,
            font=("TkDefaultFont", 9),
            yscrollcommand=_odds_sb.set,
        )
        self._odds_txt.pack(side="left", fill="x", expand=True)
        _odds_sb.config(command=self._odds_txt.yview)
        self._odds_txt.bind("<1>", lambda e: self._odds_txt.focus_set())
        self._odds_txt.bind("<MouseWheel>",
            lambda e: (self._odds_txt.yview_scroll(int(-1*(e.delta/120)), "units"), "break")[1])
        self._set_odds_text("Add passives to your pool to see odds.")
        self._odds_disclaimer_var = tk.StringVar(
            value="Odds from AttachEffectTableParam. Per-relic rate accounts for size distribution and color filter.")
        ttk.Label(
            odds_frame, textvariable=self._odds_disclaimer_var,
            foreground=theme.TEXT_MUTED, wraplength=860,
        ).pack(anchor="w", padx=6, pady=(0, 4))

    # ── category filter ─────────────────────────────────────────────────── #

    def _on_cat_change(self, _event=None):
        cat = self._cat_var.get()
        pool = NORMAL_POOL_PASSIVES if self._relic_type != "night" else DEEP_POOL_PASSIVES
        if cat == "(all)":
            items = [p for p in ALL_PASSIVES_SORTED if p in pool]
        else:
            items = sorted(
                [p for p in CATEGORIES.get(cat, [])
                 if p not in _DEBUFFS_SET and p in pool],
                key=str.casefold,
            )
        self._left_lb._all = items
        self._left_lb._refresh(items)
        self._left_lb.clear_search()

    def set_relic_context(self, relic_type: str, allowed_colors: list[str]) -> None:
        """Called by RelicBuilderFrame when relic type or color selection changes."""
        self._relic_type = relic_type
        self._allowed_colors = list(allowed_colors)
        pool_label = "Deep of Night" if relic_type == "night" else "Normal"
        color_note = (f"{len(allowed_colors)} color(s) selected"
                      if len(allowed_colors) < 4 else "all colors")
        self._odds_disclaimer_var.set(
            f"Odds from AttachEffectTableParam ({pool_label} pools, {color_note}). "
            f"Per-relic rate accounts for size distribution and color filter.")
        # Refresh listbox to show only passives available in the current mode
        self._on_cat_change()
        self._update_odds()

    def _on_threshold_change(self):
        self._update_odds()

    def _update_odds(self):
        """Recompute and display odds for the current pool + threshold."""
        rtype  = self._relic_type
        colors = self._allowed_colors
        n_pool = len(self._entries) + len(self._pairings)
        thresh = self._threshold.get()

        if n_pool == 0:
            self._set_odds_text("Add passives to your pool to see odds.")
            self._propagate_p(None)
            return

        lines: list[str] = []
        per_relic_probs: list[float] = []

        pool_name = "Deep of Night" if rtype == "night" else "Normal"

        # ── Single-entry odds ────────────────────────────────────────────────
        for entry in self._entries:
            accepted = entry["accepted"]
            label = _entry_label(entry)
            # P(any of the accepted variants appears) — use complement product
            # so multi-variant entries (e.g. Physical +3 OR +4) are handled correctly.
            p_relic = prob_any_combo_on_relic([[p] for p in accepted], rtype, colors)
            if p_relic and p_relic > 0:
                n_r = int(round(1.0 / p_relic))
                pct = p_relic * 100
                lines.append(f"  {label}  →  {_fmt_pct(pct)}%  (~1 in {n_r:,} per relic)")
                per_relic_probs.append(p_relic)
            elif p_relic == 0.0:
                lines.append(f"  {label}  →  Impossible Combo — passives are from the same exclusive group")
            else:
                lines.append(f"  {label}  →  not in {pool_name} pool")

        # ── Pairing odds ─────────────────────────────────────────────────────
        for pair in self._pairings:
            ll = _entry_label({"accepted": pair["left"]})
            rl = _entry_label({"accepted": pair["right"]})
            # Sum over all compat-valid (left, right) combinations.
            # When left/right variants are mutually exclusive (same compat group),
            # the sum is the exact P(any_left AND any_right).
            pair_p = 0.0
            any_compat = False
            for lp in pair["left"]:
                for rp in pair["right"]:
                    if compat_ok([lp, rp]):
                        any_compat = True
                        p_lr = prob_combo_on_relic([lp, rp], rtype, colors)
                        if p_lr:
                            pair_p += p_lr
            if pair_p > 0:
                n = int(round(1.0 / pair_p))
                pct = pair_p * 100
                lines.append(f"  PAIR {ll} + {rl}  →  {_fmt_pct(pct)}%  (~1 in {n:,} per relic)")
                per_relic_probs.append(pair_p)
            elif not any_compat:
                lines.append(f"  PAIR {ll} + {rl}  →  Impossible Combo — passives are from the same exclusive group")
            else:
                lines.append(f"  PAIR {ll} + {rl}  →  not available in {pool_name} pool")

        # ── Combined P(≥ thresh of pool) ─────────────────────────────────────
        p_combined: float | None = None
        if per_relic_probs:
            p_combined = prob_at_least_k_of_pool(per_relic_probs, thresh)
            if p_combined and p_combined > 0:
                n_combined = int(round(1.0 / max(p_combined, 1e-12)))
                pct_combined = p_combined * 100
                lines.append(
                    f"\n  Odds of finding a relic that fulfills at least {thresh} of the expected criteria:"
                    f"  {_fmt_pct(pct_combined)}%  (~1 in {n_combined:,} per relic)")
            elif p_combined == 0.0:
                lines.append(f"\n  Odds of finding a relic that fulfills at least {thresh} of the expected criteria: Impossible")

        self._propagate_p(p_combined)
        self._set_odds_text("\n".join(lines))

    def _propagate_p(self, p: float | None) -> None:
        """Push the current per-relic probability up to RelicBuilderFrame."""
        try:
            nb = self.nametowidget(self.winfo_parent())
            rb = self.nametowidget(nb.winfo_parent())
            if hasattr(rb, "_set_p_per_relic"):
                rb._set_p_per_relic(p)
        except Exception:
            pass

    # ── add / remove ────────────────────────────────────────────────────── #

    def _add(self):
        item = self._left_lb.get_selected()
        if not item:
            return
        # Check for variants
        variants = _passive_variants(item)
        if len(variants) > 1:
            dlg = _VariantDialog(self.winfo_toplevel(), item, variants)
            accepted = dlg.result
            if not accepted:
                return
        else:
            accepted = [item]
        # Avoid duplicate accepted sets
        existing = [e["accepted"] for e in self._entries]
        if accepted not in existing:
            self._entries.append({"accepted": accepted})
            self._sel_lb.insert("end", _entry_label(self._entries[-1]))
            self._sync_threshold()

    def _remove(self):
        sel = self._sel_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        self._entries.pop(idx)
        self._sel_lb.delete(idx)
        self._sync_threshold()

    def _clear_all(self):
        self._entries.clear()
        self._pairings.clear()
        self._sel_lb.delete(0, "end")
        self._refresh_pairings()
        self._sync_threshold()

    def _sync_threshold(self):
        n = len(self._entries) + len(self._pairings)
        cap = max(1, min(3, n))
        self._spin.configure(to=cap)
        self._threshold.set(min(self._threshold.get(), cap))
        self._update_odds()
        pool_str  = f"{len(self._entries)} passive{'s' if len(self._entries) != 1 else ''}"
        pair_str  = f"{len(self._pairings)} pair{'s' if len(self._pairings) != 1 else ''}"
        self._count_lbl.set(f"of {pool_str} + {pair_str}")

    # ── pairing panel ────────────────────────────────────────────────────── #

    def _refresh_pairings(self):
        """Rebuild the pairings listbox."""
        self._pair_lb.delete(0, "end")
        for p in self._pairings:
            left_label  = _entry_label({"accepted": p.get("left",  [])})
            right_label = _entry_label({"accepted": p.get("right", [])})
            self._pair_lb.insert("end", f"{left_label}  ↔  {right_label}")

    def _create_pairing(self):
        dlg = _CreatePairingDialog(self.winfo_toplevel())
        if dlg.result:
            left, right = dlg.result
            self._pairings.append({"left": left, "right": right})
            self._refresh_pairings()
            self._sync_threshold()

    def _remove_pairing(self):
        sel = self._pair_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self._pairings):
            self._pairings.pop(idx)
        self._refresh_pairings()
        self._sync_threshold()

    def _refresh_pool_labels(self):
        """Redraw all pool listbox labels."""
        self._sel_lb.delete(0, "end")
        for entry in self._entries:
            self._sel_lb.insert("end", _entry_label(entry))

    # ── criteria generation ──────────────────────────────────────────────── #

    def get_criteria_dict(self) -> dict:
        return {
            "mode": "pool",
            "entries":  [{"accepted": list(e["accepted"])} for e in self._entries],
            "pairings": [{"left": list(p["left"]), "right": list(p["right"])}
                         for p in self._pairings],
            "threshold": self._threshold.get(),
        }

    def get_criteria_prompt(self) -> str:
        if not self._entries and not self._pairings:
            return ""
        t = self._threshold.get()
        lines = [
            f"I am searching for a relic with AT LEAST {t} of the following"
            f" (passives count individually; pairs count as 1 only if BOTH are present):", "",
        ]
        for e in self._entries:
            label = _entry_label({"accepted": e["accepted"]})
            lines.append(f"  • {label}")
        for p in self._pairings:
            left_label  = _entry_label({"accepted": p["left"]})
            right_label = _entry_label({"accepted": p["right"]})
            lines.append(f"  • PAIR: {left_label}  ↔  {right_label}")
        lines += ["", f"The relic is a MATCH if {t} or more of the above are satisfied simultaneously."]
        return "\n".join(lines)

    def is_valid(self) -> bool:
        return len(self._entries) > 0 or len(self._pairings) > 0

    def get_min_hit_threshold(self) -> int:
        return self._threshold.get()

    # ── state serialization ──────────────────────────────────────────────── #

    def get_state(self) -> dict:
        return {
            "entries":  [{"accepted": list(e["accepted"])} for e in self._entries],
            "pairings": [{"left": list(p["left"]), "right": list(p["right"])}
                         for p in self._pairings],
            "threshold": self._threshold.get(),
        }

    def set_state(self, state: dict):
        self._clear_all()
        # Support old format: {"passives": [...], "threshold": N}
        if "entries" in state:
            for e in state["entries"]:
                accepted = e.get("accepted", [])
                if accepted:
                    self._entries.append({"accepted": list(accepted)})
                    self._sel_lb.insert("end", _entry_label(self._entries[-1]))
        elif "passives" in state:
            for p in state["passives"]:
                self._entries.append({"accepted": [p]})
                self._sel_lb.insert("end", p)
        for p in state.get("pairings", []):
            left  = p.get("left",  [])
            right = p.get("right", [])
            if left and right:
                self._pairings.append({"left": list(left), "right": list(right)})
        self._threshold.set(state.get("threshold", 2))
        self._sync_threshold()
        self._refresh_pairings()


# ─────────────────────────────────────────────────────────────────────────── #
#  TOP-LEVEL BUILDER FRAME  (replaces the old criteria LabelFrame in app.py)
# ─────────────────────────────────────────────────────────────────────────── #
#  BUILD ADVISOR TAB
# ─────────────────────────────────────────────────────────────────────────── #

class _BuildAdvisorTab(ttk.Frame):
    """
    Build Advisor — recommends relic passive combinations for a given
    weapon/skill/spell build. Two input modes:
      1. Free text (type what you want to build)
      2. Dropdown selector (pick a skill, spell, or weapon type directly)
    Output can be imported into the Exact Relic Builder.
    """

    def __init__(self, parent, on_import: "callable", **kwargs):
        super().__init__(parent, **kwargs)
        self._on_import = on_import    # callback(passives: list[str]) → bool
        self._hints: list = []         # current RelicHint results
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 6, "pady": 4}

        # ── Top: two input panels side-by-side ──────────────────────── #
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=(6, 2))
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)

        # ── Panel A: Quick Select ────────────────────────────────────── #
        qs_frame = ttk.LabelFrame(top, text="Quick Select")
        qs_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        ttk.Label(qs_frame, text="Category:").grid(row=0, column=0, sticky="w", **pad)
        self._cat_var = tk.StringVar(value="Weapon Skill")
        cat_cb = ttk.Combobox(qs_frame, textvariable=self._cat_var,
                              values=["Weapon Skill", "Sorcery", "Incantation", "Weapon Type"],
                              state="readonly", width=14)
        cat_cb.grid(row=0, column=1, sticky="ew", **pad)
        cat_cb.bind("<<ComboboxSelected>>", lambda _: self._refresh_qs_options())
        qs_frame.columnconfigure(1, weight=1)

        ttk.Label(qs_frame, text="Selection:").grid(row=1, column=0, sticky="w", **pad)
        self._qs_var = tk.StringVar()
        self._qs_cb = ttk.Combobox(qs_frame, textvariable=self._qs_var,
                                   state="readonly", width=22)
        self._qs_cb.grid(row=1, column=1, sticky="ew", **pad)

        ttk.Button(qs_frame, text="→ Recommend",
                   command=self._recommend_from_dropdown).grid(
            row=2, column=0, columnspan=2, pady=(4, 6))

        self._refresh_qs_options()

        # ── Panel B: Free Text ───────────────────────────────────────── #
        ft_frame = ttk.LabelFrame(top, text="Free Text")
        ft_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        ft_frame.columnconfigure(0, weight=1)

        ttk.Label(ft_frame, text='Describe your build:', foreground="#aaa").grid(
            row=0, column=0, sticky="w", **pad)
        self._text_var = tk.StringVar()
        ttk.Entry(ft_frame, textvariable=self._text_var, width=30).grid(
            row=1, column=0, sticky="ew", padx=6, pady=2)
        ttk.Label(ft_frame,
                  text='e.g. "Rain of Arrows Greatbow", "Beast Claw", "Katana bleed build"',
                  foreground="#888", font=("TkDefaultFont", 8)).grid(
            row=2, column=0, sticky="w", padx=6)
        ttk.Button(ft_frame, text="→ Recommend",
                   command=self._recommend_from_text).grid(
            row=3, column=0, pady=(4, 6))

        # ── Bottom: Recommendation output ───────────────────────────── #
        out_frame = ttk.LabelFrame(self, text="Recommendation")
        out_frame.pack(fill="both", expand=True, padx=6, pady=(2, 6))

        self._label_var = tk.StringVar(value="Make a selection above to see recommendations.")
        ttk.Label(out_frame, textvariable=self._label_var,
                  foreground="#c8a84c", font=("TkDefaultFont", 9, "bold")).pack(
            anchor="w", padx=8, pady=(6, 2))

        # Scrollable hint list
        list_frame = ttk.Frame(out_frame)
        list_frame.pack(fill="both", expand=True, padx=4, pady=2)
        self._hint_lb = tk.Listbox(list_frame, height=7, selectmode="extended",
                                   font=("Consolas", 9),
                                   bg="#1e1e1e", fg="#d4d4d4",
                                   selectbackground="#3a3d41",
                                   activestyle="none")
        sb = ttk.Scrollbar(list_frame, orient="vertical",
                           command=self._hint_lb.yview)
        self._hint_lb.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._hint_lb.pack(side="left", fill="both", expand=True)

        # Reason text below list
        self._reason_var = tk.StringVar(value="")
        ttk.Label(out_frame, textvariable=self._reason_var,
                  foreground="#90c890", wraplength=680, justify="left").pack(
            anchor="w", padx=8, pady=(2, 2))

        self._hint_lb.bind("<<ListboxSelect>>", self._on_hint_select)

        # Action buttons
        btn_row = ttk.Frame(out_frame)
        btn_row.pack(fill="x", padx=6, pady=(2, 6))
        ttk.Button(btn_row, text="→ Import Selected into Relic Builder",
                   command=self._import_selected).pack(side="left", padx=4)
        ttk.Button(btn_row, text="→ Import All (Top 3) into Relic Builder",
                   command=self._import_top3).pack(side="left", padx=4)
        ttk.Label(btn_row,
                  text="Imports as one new target in the Build Exact Relic tab.",
                  foreground="#888", font=("TkDefaultFont", 8)).pack(side="left", padx=8)

    # ── Dropdown refresh ─────────────────────────────────────────────── #

    def _refresh_qs_options(self):
        from bot.build_advisor import get_skill_options, get_spell_options, get_weapon_type_options
        from database.spells import SORCERIES, INCANTATIONS
        cat = self._cat_var.get()
        if cat == "Weapon Skill":
            opts = get_skill_options()
        elif cat == "Sorcery":
            opts = sorted(SORCERIES.keys(), key=str.casefold)
        elif cat == "Incantation":
            opts = sorted(INCANTATIONS.keys(), key=str.casefold)
        else:  # Weapon Type
            opts = get_weapon_type_options()
        self._qs_cb["values"] = opts
        if opts:
            self._qs_cb.set(opts[0])

    # ── Recommendation triggers ──────────────────────────────────────── #

    def _recommend_from_dropdown(self):
        from bot.build_advisor import (recommend_for_skill, recommend_for_spell,
                                        recommend_for_weapon)
        from database.spells import SORCERIES, INCANTATIONS
        cat = self._cat_var.get()
        sel = self._qs_var.get().strip()
        if not sel:
            return
        if cat == "Weapon Skill":
            hints = recommend_for_skill(sel)
            label = f"Skill: {sel}"
        elif cat in ("Sorcery", "Incantation"):
            hints = recommend_for_spell(sel)
            label = f"{'Sorcery' if sel in SORCERIES else 'Incantation'}: {sel}"
        else:
            hints = recommend_for_weapon(sel)
            label = f"Weapon: {sel}"
        self._show_hints(label, hints)

    def _recommend_from_text(self):
        from bot.build_advisor import recommend_for_text
        q = self._text_var.get().strip()
        if not q:
            return
        label, hints = recommend_for_text(q)
        if not hints:
            self._label_var.set(f'No match found for "{q}". Try a different description.')
            self._hint_lb.delete(0, "end")
            self._reason_var.set("")
            self._hints = []
            return
        self._show_hints(label, hints)

    # ── Display ──────────────────────────────────────────────────────── #

    def _show_hints(self, label: str, hints: list):
        from bot.build_advisor import top_recommendations
        self._hints = top_recommendations(hints, max_n=6)
        self._label_var.set(f"Recommendations for: {label}")
        self._hint_lb.delete(0, "end")
        for h in self._hints:
            badge = " [DEEP ONLY]" if h.deep_only else " [NORMAL]  "
            prio  = "★" * (4 - h.priority) if h.priority <= 3 else ""
            self._hint_lb.insert("end", f"{prio:<3} {badge}  {h.passive}")
        self._reason_var.set("")

    def _on_hint_select(self, _evt=None):
        sel = self._hint_lb.curselection()
        if sel and self._hints:
            idx = sel[0]
            if idx < len(self._hints):
                self._reason_var.set(f"Why: {self._hints[idx].reason}")

    # ── Import actions ───────────────────────────────────────────────── #

    def _import_selected(self):
        sel = self._hint_lb.curselection()
        if not sel or not self._hints:
            return
        passives = [self._hints[i].passive for i in sel if i < len(self._hints)]
        self._do_import(passives)

    def _import_top3(self):
        if not self._hints:
            return
        passives = [h.passive for h in self._hints[:3]]
        self._do_import(passives)

    def _do_import(self, passives: list):
        ok = self._on_import(passives)
        if ok:
            self._reason_var.set(
                f"✓ Imported {len(passives)} passive(s) as a new target in Build Exact Relic.")
        else:
            self._reason_var.set("✗ Could not import — Build Exact Relic tab is full (20 targets max).")


# ─────────────────────────────────────────────────────────────────────────── #

class RelicBuilderFrame(ttk.LabelFrame):
    """
    Relic criteria selector.
    Exposes:
        get_criteria_dict()   – returns structured dict for the local analyzer
        get_criteria_summary()– returns human-readable string for README output
        is_valid()            – True when criteria is non-empty
        has_compat_errors()   – True if the Exact Relic tab has compat issues
        get_min_hit_threshold()
        get_state() / set_state()
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="Relic Criteria", **kwargs)
        self._p_per_relic: float | None = None
        self._on_odds_changed = None  # optional callback(float | None)
        self._relic_type: str = "night"
        self._build()

    def _build(self):
        # ── Flatstone icon header (swaps with relic type) ────────────── #
        _icon_row = ttk.Frame(self)
        _icon_row.pack(fill="x", padx=8, pady=(6, 0))
        self._flatstone_lbl = tk.Label(_icon_row, bg=theme.SURFACE)
        self._flatstone_lbl.pack(side="left")
        self.after(0, self._refresh_flatstone_icon)

        # ── Notebook (3 tabs) ────────────────────────────────────────── #
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=8, pady=6)

        # Tab 0 – Exact Relic Builder
        self._exact = _ExactRelicTab(self._nb)
        self._nb.add(self._exact, text="  Build Exact Relic  ")

        # Tab 1 – Passive Pool
        self._pool = _PassivePoolTab(self._nb)
        self._nb.add(self._pool, text="  Passive Pool  ")

        # Tab 2 – Build Advisor
        self._advisor = _BuildAdvisorTab(self._nb, on_import=self._exact.import_target)
        self._nb.add(self._advisor, text="  Build Advisor  ")

        # ── Combine toggle ──────────────────────────────────────────── #
        combine_row = ttk.Frame(self)
        combine_row.pack(anchor="w", padx=8, pady=(0, 4))
        self._combine_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            combine_row,
            text="Combine both tabs — match if relic satisfies Build Exact Relic OR Passive Pool",
            variable=self._combine_var,
        ).pack(side="left")

    # ── Public API ──────────────────────────────────────────────────── #

    def _refresh_flatstone_icon(self):
        """Load and display the mode-appropriate flatstone icon."""
        if not hasattr(self, "_flatstone_lbl"):
            return
        don   = self._relic_type == "night"
        photo = relic_images.get_flatstone(don)
        self._flatstone_lbl.configure(image=photo)
        self._flatstone_lbl.image = photo   # keep reference

    def set_relic_context(self, relic_type: str, allowed_colors: list[str]) -> None:
        """
        Propagate relic type and color selection to both builder tabs.
        Call from app.py whenever relic type or color changes.
        """
        self._relic_type = relic_type
        self._exact.set_relic_context(relic_type, allowed_colors)
        self._pool.set_relic_context(relic_type, allowed_colors)
        self._refresh_flatstone_icon()

    def _set_p_per_relic(self, p: float | None) -> None:
        """Called by child tabs when they recompute per-relic probability."""
        self._p_per_relic = p
        if self._on_odds_changed is not None:
            self._on_odds_changed(p)

    def get_current_p_per_relic(self) -> float | None:
        """Return the most recently computed per-relic success probability."""
        return self._p_per_relic

    def get_criteria_dict(self) -> dict:
        """Return structured criteria dict consumed by relic_analyzer.analyze()."""
        if self._combine_var.get():
            return {
                "mode": "combine",
                "exact": self._exact.get_criteria_dict(),
                "pool": self._pool.get_criteria_dict(),
            }
        tab = self._nb.index(self._nb.select())
        if tab == 0:
            return self._exact.get_criteria_dict()
        return self._pool.get_criteria_dict()

    def get_criteria_summary(self) -> str:
        """Return a human-readable criteria description for README output."""
        if self._combine_var.get():
            return (
                "[COMBINED]\n"
                + self._exact.get_criteria_prompt()
                + "\n\n--- OR ---\n\n"
                + self._pool.get_criteria_prompt()
            )
        tab = self._nb.index(self._nb.select())
        if tab == 0:
            return self._exact.get_criteria_prompt()
        return self._pool.get_criteria_prompt()

    def is_valid(self) -> bool:
        if self._combine_var.get():
            return self._exact.is_valid() or self._pool.is_valid()
        tab = self._nb.index(self._nb.select())
        if tab == 0:
            return self._exact.is_valid()
        return self._pool.is_valid()

    def has_compat_errors(self) -> bool:
        """True if the Exact Relic tab has incompatible passive combinations."""
        tab = self._nb.index(self._nb.select())
        if tab == 0:
            return self._exact.has_compat_errors()
        return False

    def get_min_hit_threshold(self) -> int:
        """
        Return the minimum passive count needed to qualify as a HIT tier.
        - Exact Relic tab: lowest threshold across all valid targets.
        - Passive Pool tab: the configured threshold.
        """
        if self._combine_var.get():
            return min(self._exact.get_min_hit_threshold(), self._pool.get_min_hit_threshold())
        tab = self._nb.index(self._nb.select())
        if tab == 0:
            return self._exact.get_min_hit_threshold()
        return self._pool.get_min_hit_threshold()

    def get_state(self) -> dict:
        return {
            "active_tab": self._nb.index(self._nb.select()),
            "combine": self._combine_var.get(),
            "exact": self._exact.get_state(),
            "pool": self._pool.get_state(),
        }

    def set_state(self, state: dict):
        if "exact" in state:
            self._exact.set_state(state["exact"])
        if "pool" in state:
            self._pool.set_state(state["pool"])
        self._combine_var.set(state.get("combine", False))
        try:
            self._nb.select(state.get("active_tab", 0))
        except Exception:
            pass
