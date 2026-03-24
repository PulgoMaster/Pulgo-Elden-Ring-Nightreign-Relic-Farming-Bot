"""
Relic criteria builder widget.

Provides two modes selectable via a notebook (tab bar):
  1. Exact Relic  – build up to 10 relic targets, each with 3 slots and a
                    configurable match threshold (≥2 or all 3 passives).
                    Incompatible passives (same exclusive category) are
                    flagged and blocked.
  2. Passive Pool – select any number of passives; match when a relic has
                    at least N of them simultaneously.
"""

import re
import tkinter as tk
from tkinter import ttk

from ui import theme, relic_images
from bot.passives import (
    ALL_PASSIVES_SORTED, CATEGORIES, UI_CATEGORIES,
    COMPAT_GROUPS, get_compat_violations,
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
        items = ALL_PASSIVES_SORTED if cat == "(all)" else sorted(UI_CATEGORIES.get(cat, []), key=str.casefold)
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

    def set_excluded(self, excluded: set):
        """Delegate exclusion update to the inner listbox."""
        self._lb.set_excluded(excluded)


# ─────────────────────────────────────────────────────────────────────────── #
#  EXACT RELIC TAB  (up to 10 targets, each with 3 slots + threshold)
# ─────────────────────────────────────────────────────────────────────────── #

class _ExactRelicTab(ttk.Frame):
    """
    Manage up to 10 relic targets.  Each target has three passive slots and a
    match threshold (2 = any two specified passives, 3 = all three).  The bot
    considers a relic a MATCH if it satisfies ANY of the defined targets.
    """

    _MAX_TARGETS = 10

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # Each target: {"slots": [str|None, str|None, str|None], "threshold": int}
        self._targets: list[dict] = [self._new_target()]
        self._active: int = 0
        self._slots: list[_SlotSelector] = []
        self._threshold_var = tk.IntVar(value=2)
        self._compat_var = tk.StringVar(value="")
        self._build()

    # ── construction ─────────────────────────────────────────────────── #

    def _load_blank_gem(self):
        photo = relic_images.get_blank_gem()
        self._blank_gem_lbl.configure(image=photo)
        self._blank_gem_lbl.image = photo   # keep reference

    @staticmethod
    def _new_target() -> dict:
        return {"slots": [None, None, None], "threshold": 2}

    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=8, pady=(6, 0))

        # Blank relic gem — represents "any relic" / the slot you're crafting
        self._blank_gem_lbl = tk.Label(header, bg=theme.SURFACE)
        self._blank_gem_lbl.pack(side="left", padx=(0, 8))
        self.after(0, self._load_blank_gem)

        ttk.Label(
            header,
            text=(
                "Build up to 10 relic targets. "
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
        self._refresh_list()
        self._target_lb.selection_clear(0, "end")
        self._target_lb.selection_set(self._active)

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
        self._save_current()
        self._refresh_list()
        self._target_lb.selection_set(self._active)

    def _on_threshold_change(self):
        self._save_current()

    def _update_exclusions(self):
        """
        For each slot, compute the set of passives it must NOT show
        (those sharing an exclusive compat group with any other slot's value)
        and push that set into the slot's listbox.
        """
        slot_vals = [s.get() for s in self._slots]
        for i, slot in enumerate(self._slots):
            excluded: set = set()
            for j, val in enumerate(slot_vals):
                if j == i or val is None:
                    continue
                gj = COMPAT_GROUPS.get(val)
                if gj is None:
                    continue
                # Hide every passive that shares this group
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
        self._left_lb = _SearchableListbox(left_frame, ALL_PASSIVES_SORTED, height=13)
        self._left_lb.pack(fill="both", expand=True, padx=4, pady=(4, 2))
        ttk.Button(left_frame, text="✔ Select for Left",
                   command=self._select_left).pack(padx=4, pady=(0, 4))

        # ── Divider ──────────────────────────────────────────────────── #
        ttk.Label(cols, text="↔", font=("", 16, "bold")).grid(
            row=0, column=1, padx=10)

        # ── Right picker ─────────────────────────────────────────────── #
        right_frame = ttk.LabelFrame(cols, text="Right Passive")
        right_frame.grid(row=0, column=2, sticky="nsew")
        self._right_lb = _SearchableListbox(right_frame, ALL_PASSIVES_SORTED, height=13)
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
        self._build()

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
        cats = ["(all)"] + list(CATEGORIES.keys())
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

        pair_btns = ttk.Frame(pair_frame)
        pair_btns.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Button(pair_btns, text="+ Create Pairing", command=self._create_pairing, width=16).pack(side="left", padx=2)
        ttk.Button(pair_btns, text="X Remove",         command=self._remove_pairing, width=10).pack(side="left", padx=2)

        # ── Threshold row ──────────────────────────────────────────────────── #
        foot = ttk.Frame(self)
        foot.pack(fill="x", padx=8, pady=6)
        ttk.Label(foot, text="Match when relic has at least").pack(side="left")
        self._threshold = tk.IntVar(value=2)
        self._spin = ttk.Spinbox(foot, from_=1, to=3, textvariable=self._threshold, width=4)
        self._spin.pack(side="left", padx=4)
        self._count_lbl = tk.StringVar(value="of 0 passives in pool")
        ttk.Label(foot, textvariable=self._count_lbl).pack(side="left")

    # ── category filter ─────────────────────────────────────────────────── #

    def _on_cat_change(self, _event=None):
        cat = self._cat_var.get()
        items = ALL_PASSIVES_SORTED if cat == "(all)" else sorted(CATEGORIES.get(cat, []), key=str.casefold)
        self._left_lb._all = items
        self._left_lb._refresh(items)
        self._left_lb.clear_search()

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
        self._build()

    def _build(self):
        # ── Notebook (2 modes) ───────────────────────────────────────── #
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=8, pady=6)

        # Tab 0 – Exact Relic Builder
        self._exact = _ExactRelicTab(self._nb)
        self._nb.add(self._exact, text="  Build Exact Relic  ")

        # Tab 1 – Passive Pool
        self._pool = _PassivePoolTab(self._nb)
        self._nb.add(self._pool, text="  Passive Pool  ")

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
