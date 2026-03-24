"""
Main UI for the Elden Ring Nightreign Relic Bot.

Two modes:
  Live Mode  – runs continuously; pauses when a match is found and asks the
               user to keep it or keep searching.
  Batch Mode – runs for a fixed number of loops or a fixed duration; saves
               every iteration's save file to its own folder, then writes a
               README.txt summarising matches (with passives + screenshots).
"""

import ctypes
import json
import math
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

from pynput import keyboard as _kb

from bot import input_controller, relic_analyzer, save_manager, screen_capture
from ui import theme, relic_images
from ui.relic_builder import RelicBuilderFrame


def _app_root() -> str:
    """Working root: folder containing the EXE when frozen, repo root in dev."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


_REPO_ROOT    = _app_root()
_PROFILES_DIR = os.path.join(_REPO_ROOT, "profiles")


# ─────────────────────────────────────────────────────────────────────────── #
#  README GENERATOR (Batch Mode)
# ─────────────────────────────────────────────────────────────────────────── #

def generate_readme(
    output_dir: str,
    criteria: str,
    run_mode: str,
    run_limit,
    results: list,
    hit_min: int = 2,
) -> None:
    """Write README.txt into output_dir summarising a completed batch run."""
    total = len(results)

    def _tier(r):
        n = len(r.get("matched_passives", []))
        if n > 0:
            return n
        near = r.get("near_misses", [])
        if near:
            return max(nm.get("matching_passive_count", 0) for nm in near)
        return 0

    god_rolls = [r for r in results if _tier(r) >= 3]
    hits      = [r for r in results if _tier(r) == 2]
    near_miss = [r for r in results if _tier(r) == 1]
    garbage   = [r for r in results if _tier(r) == 0]

    def _find_relic_num(r, name):
        """Return the 1-based position of `name` in relics_found, or None."""
        for i, relic in enumerate(r.get("relics_found", []), 1):
            if isinstance(relic, dict) and relic.get("name") == name:
                return i
        return None

    def _hit_detail_block(r, indent="  "):
        """Full detail block for a matched or near-miss relic.
        Only marks passives with * when the matching count meets hit_min."""
        out = []
        matched_name = r.get("matched_relic")
        matched_passives = set(r.get("matched_passives", []))
        match_count = len(matched_passives)

        # If no full match, use best near-miss
        if not matched_name:
            best = max(
                r.get("near_misses", []),
                key=lambda nm: nm.get("matching_passive_count", 0),
                default=None,
            )
            if best:
                matched_name = best.get("relic_name")
                matched_passives = set(best.get("matching_passives", []))
                match_count = best.get("matching_passive_count", len(matched_passives))

        relic_num = _find_relic_num(r, matched_name)
        num_str = f"Relic #{relic_num}" if relic_num else "Relic #?"
        out.append(f"{indent}{num_str}: {matched_name or 'Unknown'}")

        mark = match_count >= hit_min
        for relic in r.get("relics_found", []):
            if isinstance(relic, dict) and relic.get("name") == matched_name:
                for p in relic.get("passives", []):
                    marker = "* " if (mark and p in matched_passives) else "  "
                    out.append(f"{indent}  {marker}{p}")
                for c in relic.get("curses", []):
                    out.append(f"{indent}  [CURSE] {c}")
                break
        return out

    def _all_relics_block(r):
        out = []
        for relic in r.get("relics_found", []):
            if isinstance(relic, dict):
                out.append(f"  {relic.get('name', 'Unknown')}")
                for p in relic.get("passives", []):
                    out.append(f"    • {p}")
        return out

    lines = [
        "ELDEN RING NIGHTREIGN – RELIC FARMING RESULTS",
        "=" * 60,
        f"Date        : {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Mode        : {run_mode} ({run_limit})",
        f"Total runs  : {total}",
        f"God Rolls   : {len(god_rolls)}",
        f"Hits (2/3)  : {len(hits)}",
        f"Near Miss   : {len(near_miss)}",
        f"No Match    : {len(garbage)}",
        "",
        "CRITERIA",
        "-" * 60,
        criteria.strip(),
        "",
    ]

    # ── HITS SUMMARY (most important — read this first) ───────────────── #
    lines += ["=" * 60, "HITS SUMMARY  (open these save files)", "=" * 60, ""]
    notable = god_rolls + hits
    if notable:
        for r in notable:
            tier = "GOD ROLL" if _tier(r) >= 3 else "HIT"
            lines.append(f"  [{tier}]  Batch: {r['folder']}  |  Iteration #{r['iteration']:03d}")
            lines += _hit_detail_block(r, indent="    ")
            for ss in r.get("screenshots", []):
                lines.append(f"    Screenshot: {r['folder']}/{ss}")
            lines.append("")
    else:
        lines += ["  No hits yet.", ""]

    # ── DETAILED BREAKDOWN ────────────────────────────────────────────── #
    lines += ["=" * 60, "DETAILED BREAKDOWN", "=" * 60, ""]

    lines += ["", "★★★ GOD ROLL — ALL 3 PASSIVES MATCH ★★★", "-" * 60, ""]
    if god_rolls:
        for r in god_rolls:
            lines.append(f"  Iteration #{r['iteration']:03d}  |  Folder: {r['folder']}")
            lines += _hit_detail_block(r)
            lines.append("")
    else:
        lines += ["  None.", ""]

    lines += ["", "★★ HITS — 2 PASSIVES MATCH", "-" * 60, ""]
    if hits:
        for r in hits:
            lines.append(f"  Iteration #{r['iteration']:03d}  |  Folder: {r['folder']}")
            lines += _hit_detail_block(r)
            lines.append("")
    else:
        lines += ["  None.", ""]

    lines += ["", "NEAR MISS — 1 PASSIVE MATCH (save not flagged)", "-" * 60, ""]
    if near_miss:
        for r in near_miss:
            lines.append(f"  Iteration #{r['iteration']:03d}  |  Folder: {r['folder']}")
            lines += _hit_detail_block(r)
            lines.append("")
    else:
        lines += ["  None.", ""]

    lines += ["", "NO MATCH", "-" * 60, ""]
    if garbage:
        for r in garbage:
            lines.append(f"  Iteration #{r['iteration']:03d}  |  Folder: {r['folder']}")
            lines += _all_relics_block(r)
            lines.append("")
    else:
        lines += ["  None.", ""]

    readme_path = os.path.join(output_dir, "README.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_iter_info(iter_dir: str, iteration: int, relic_results: list, hit_min: int = 2) -> None:
    """Write info.txt inside an iteration folder.
    Uses per-relic results directly so the MATCH/NEAR MISS labels are always
    accurate regardless of whether multiple relics share the same OCR name."""
    lines = [f"Iteration #{iteration:03d}", "=" * 40, ""]

    # ── HITS FOUND section (relics with 2/3 or 3/3 match, always at top) ─ #
    hit_entries = []
    for relic_num, rr in enumerate(relic_results, 1):
        relic = (rr.get("relics_found") or [{}])[0]
        if not isinstance(relic, dict):
            continue
        passives   = relic.get("passives", [])
        is_match   = rr.get("match", False)
        matched_ps = set(rr.get("matched_passives", []))
        nms        = rr.get("near_misses", [])
        best_nm    = max(nms, key=lambda n: n.get("matching_passive_count", 0), default={})
        best_nm_count = best_nm.get("matching_passive_count", 0)
        best_nm_ps    = set(best_nm.get("matching_passives", []))

        n_matched = len(matched_ps) if is_match else best_nm_count
        mark_ps   = matched_ps if is_match and matched_ps else best_nm_ps

        if n_matched >= 3:
            hit_entries.append((relic_num, "3/3", relic.get("name", "Unknown"),
                                passives, mark_ps))
        elif n_matched >= hit_min:
            hit_entries.append((relic_num, "2/3", relic.get("name", "Unknown"),
                                passives, mark_ps))

    if hit_entries:
        lines.append("=" * 40)
        lines.append("  HITS FOUND")
        lines.append("=" * 40)
        for rn, tier, rname, passives, mark_ps in hit_entries:
            lines.append(f"  ★ Relic #{rn} [{tier}]  {rname}")
            for p in passives:
                marker = "    * " if p in mark_ps else "      "
                lines.append(f"{marker}{p}")
            lines.append("")
        lines.append("-" * 40)
        lines.append("")

    # ── All relics in order ──────────────────────────────────────────────── #
    for relic_num, rr in enumerate(relic_results, 1):
        relic = (rr.get("relics_found") or [{}])[0]
        if not isinstance(relic, dict):
            continue
        name    = relic.get("name", "Unknown")
        passives = relic.get("passives", [])
        curses   = relic.get("curses", [])

        is_match       = rr.get("match", False)
        matched_ps     = set(rr.get("matched_passives", []))
        nms            = rr.get("near_misses", [])
        best_nm        = max(nms, key=lambda n: n.get("matching_passive_count", 0), default={})
        best_nm_count  = best_nm.get("matching_passive_count", 0)
        best_nm_ps     = set(best_nm.get("matching_passives", []))

        if is_match and len(matched_ps) >= hit_min:
            lines.append(f"* Relic #{relic_num}: {name}  <-- MATCH")
            mark_ps, mark = matched_ps, True
        elif best_nm_count >= hit_min:
            lines.append(f"* Relic #{relic_num}: {name}  <-- NEAR MISS")
            mark_ps, mark = best_nm_ps, True
        else:
            lines.append(f"  Relic #{relic_num}: {name}")
            mark_ps, mark = set(), False

        for p in passives:
            marker = "  * " if (mark and p in mark_ps) else "    "
            lines.append(f"{marker}{p}")
        for c in curses:
            lines.append(f"    [CURSE] {c}")
        lines.append("")
    with open(os.path.join(iter_dir, "info.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_priority_summary(output_dir: str, results: list) -> None:
    """
    Write PRIORITY.txt at the run root.

    Lists every save that has any value: perfect matches (match=true) and
    near misses (relics with 2+ of the desired passives). Relics with only
    1 matching passive are ignored — they are worth nothing.
    Each save gets one plain summary line so the player can decide which
    to open for manual review.
    """
    lines = [
        "SAVE FILE SUMMARY – notable saves from this batch run",
        "=" * 60,
        "  Perfect match = relic fully satisfied your criteria",
        "  Near miss     = relic had 2+ of your desired passives but not enough to be a full hit",
        "  (Relics with only 1 matching passive are ignored)",
        "=" * 60,
        "",
    ]

    notable = []
    for r in results:
        perfect = 1 if r["match"] else 0
        # Count near-miss relics: must have 2+ matching passives
        near_miss_count = sum(
            1 for nm in r.get("near_misses", [])
            if nm.get("matching_passive_count", len(nm.get("matching_passives", []))) >= 2
        )
        if perfect or near_miss_count:
            notable.append((r, perfect, near_miss_count))

    if notable:
        for r, perfect, near_miss_count in notable:
            parts = []
            if perfect:
                parts.append(f"{perfect} perfect match")
            if near_miss_count:
                parts.append(f"{near_miss_count} near miss{'es' if near_miss_count != 1 else ''}")
            summary = " and ".join(parts)
            lines.append(f"  {r['folder']:<14}  –  {summary}")
        lines.append("")
        lines.append(f"  {len(notable)} save(s) worth reviewing out of {len(results)} total.")
    else:
        lines.append("  No saves with notable passives found in this run.")

    skipped = len(results) - len(notable)
    if skipped:
        lines.append(f"  {skipped} save(s) had nothing matching your criteria — skip them.")

    with open(os.path.join(output_dir, "PRIORITY.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ─────────────────────────────────────────────────────────────────────────── #
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────── #

class _Tooltip:
    """Lightweight hover tooltip for tkinter widgets."""
    def __init__(self, widget, text: str):
        self._widget = widget
        self._text = text
        self._win = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event=None):
        if self._win:
            return
        x = self._widget.winfo_rootx() + 16
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._win = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw, text=self._text, background="#2a2a2a", foreground="#dddddd",
            relief="solid", borderwidth=1, font=("Segoe UI", 8),
            wraplength=280, justify="left", padx=6, pady=4,
        ).pack()

    def _hide(self, _event=None):
        if self._win:
            self._win.destroy()
            self._win = None


class RelicBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Elden Ring Nightreign – Relic Bot  |  Made by Pulgo")
        self.resizable(True, True)

        # App icon
        _icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "icon.ico",
        )
        if os.path.exists(_icon_path):
            self.iconbitmap(_icon_path)

        # Input recording
        self.recorder = input_controller.InputRecorder()
        self.player = input_controller.InputPlayer()
        # phase_events[0] = Setup, [1] = Buy Loop, [2] = Relic Rites nav, [3] = F2 sell loop, [4] = Review Step
        self.phase_events: list = [[], [], [], [], []]
        self._active_phase: int = 0
        self._rec_blink = False

        # Relic type — controls murk cost per relic for the Phase 3 count calculation
        self.relic_type_var = tk.StringVar(value="night")   # "night" or "normal"

        # Global hotkey (works even when the game window has focus)
        self._hotkey_str = "Key.f9"       # pynput key string
        self._hotkey_display = "F9"        # human-readable label
        self._global_kb_listener = None    # persistent pynput Listener

        # Bot state
        self.bot_thread: threading.Thread | None = None
        self.bot_running = False
        self.attempt_count = 0
        self._batch_log_path: str = ""   # set while a batch run is active

        # Manual iteration reset (user-triggered soft nuke from overlay)
        self._reset_iter_requested = False

        # Backup/startup ready event
        self._ready_event = threading.Event()

        # Overlay (Batch Mode only)
        self._overlay = None
        self._overlay_enabled_var  = tk.BooleanVar(value=True)
        self._parallel_enabled_var  = tk.BooleanVar(value=False)
        self._parallel_workers_var  = tk.IntVar(value=2)
        self._async_enabled_var     = tk.BooleanVar(value=False)
        self._stop_after_batch      = False   # graceful stop flag
        self._game_hung             = False   # set True by watchdog when game freezes
        # Per-run counters (reset each start)
        self._ov_hits_33 = 0
        self._ov_hits_23 = 0
        self._ov_duds    = 0
        # All-time counters (reset each START — track current run only)
        self._ov_at_33   = 0
        self._ov_at_23   = 0
        self._ov_at_duds = 0
        # Best-batch scoreboard (reset each START)
        self._best_33_iter   = None  # {"iteration": n, "count": x}
        self._best_hits_iter = None  # {"iteration": n, "count": x}

        # Batch identity and overflow state
        self._current_batch_id: str = ""
        self._overflow_handoff: dict | None = None
        self._ov_overflow_hits: int = 0   # hits found in previous batch overflow

        theme.apply(self)
        self._build_ui()
        self._start_global_hotkey_listener()
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

        os.makedirs(_PROFILES_DIR, exist_ok=True)
        self._refresh_profile_list()
        self.after(200, self._log_screen_resolution)

    # ------------------------------------------------------------------ #
    #  UI CONSTRUCTION
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # Scrollable canvas so the window can be smaller than its content
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        _canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg=theme.BG)
        _vsb = ttk.Scrollbar(self, orient="vertical", command=_canvas.yview)
        _canvas.configure(yscrollcommand=_vsb.set)
        _vsb.grid(row=0, column=1, sticky="ns")
        _canvas.grid(row=0, column=0, sticky="nsew")

        # Inner frame lives inside the canvas
        inner = ttk.Frame(_canvas)
        _canvas_window = _canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_frame_configure(event):
            _canvas.configure(scrollregion=_canvas.bbox("all"))

        def _on_canvas_configure(event):
            _canvas.itemconfig(_canvas_window, width=event.width)

        inner.bind("<Configure>", _on_frame_configure)
        _canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse-wheel scrolling — yscrollincrement=20 means each "unit" = 20px;
        # delta/120 per notch * 3 units = 60px per scroll notch.
        _canvas.configure(yscrollincrement=20)
        def _on_mousewheel(event):
            _canvas.yview_scroll(int(-1 * (event.delta / 120)) * 3, "units")
        _canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # All widgets go into `inner` instead of `self`
        self._inner = inner

        # ── Profile ─────────────────────────────────────────────────── #
        profile_frame = ttk.LabelFrame(inner, text="Profile")
        profile_frame.grid(row=0, column=0, sticky="ew", **pad)

        ttk.Label(profile_frame, text="Profile:").grid(row=0, column=0, sticky="w", **pad)
        self._profile_var = tk.StringVar()
        self._profile_cb = ttk.Combobox(
            profile_frame, textvariable=self._profile_var, state="readonly", width=30
        )
        self._profile_cb.grid(row=0, column=1, **pad)
        ttk.Button(profile_frame, text="Load", command=self._load_profile).grid(row=0, column=2, **pad)
        ttk.Button(profile_frame, text="Save", command=self._save_profile).grid(row=0, column=3, **pad)
        ttk.Button(profile_frame, text="Save As…", command=self._save_profile_as).grid(row=0, column=4, **pad)
        ttk.Button(profile_frame, text="Delete", command=self._delete_profile).grid(row=0, column=5, **pad)
        ttk.Button(profile_frame, text="Restore Defaults", command=self._reset_to_defaults).grid(row=0, column=6, **pad)

        # ── Save File & Game Configuration ──────────────────────────── #
        save_frame = ttk.LabelFrame(inner, text="Save File & Game Configuration")
        save_frame.grid(row=1, column=0, sticky="ew", **pad)

        ttk.Label(save_frame, text="Save file:").grid(row=0, column=0, sticky="w", **pad)
        self.save_path_var = tk.StringVar()
        ttk.Entry(save_frame, textvariable=self.save_path_var, width=52).grid(row=0, column=1, **pad)
        ttk.Button(save_frame, text="Browse", command=self._browse_save).grid(row=0, column=2, **pad)

        ttk.Label(save_frame, text="Backup folder:").grid(row=1, column=0, sticky="w", **pad)
        self.backup_path_var = tk.StringVar(value=os.path.join(_REPO_ROOT, "save_backups"))
        ttk.Entry(save_frame, textvariable=self.backup_path_var, width=52).grid(row=1, column=1, **pad)
        ttk.Button(save_frame, text="Browse", command=self._browse_backup).grid(row=1, column=2, **pad)

        ttk.Label(save_frame, text="Game executable:").grid(row=2, column=0, sticky="w", **pad)
        self.game_exe_var = tk.StringVar()
        ttk.Entry(save_frame, textvariable=self.game_exe_var, width=52).grid(row=2, column=1, **pad)
        ttk.Button(save_frame, text="Browse", command=self._browse_game_exe).grid(row=2, column=2, **pad)

        ttk.Label(save_frame, text="Game load wait (s):").grid(row=3, column=0, sticky="w", **pad)
        self.game_load_wait_var = tk.StringVar(value="30")
        _glw_entry = ttk.Entry(save_frame, textvariable=self.game_load_wait_var, width=7)
        _glw_entry.grid(row=3, column=1, sticky="w", **pad)
        _Tooltip(_glw_entry, "Seconds to wait after launch before sending inputs.\nAdjust in small increments based on your PC speed — lower if the game loads fast, higher if inputs arrive too early.")

        ttk.Label(save_frame, text="Confirm key:").grid(row=4, column=0, sticky="w", **pad)
        self.confirm_key_var = tk.StringVar(value="f")
        _ck_entry = ttk.Entry(save_frame, textvariable=self.confirm_key_var, width=5)
        _ck_entry.grid(row=4, column=1, sticky="w", **pad)
        _Tooltip(_ck_entry, "The key used to confirm/interact in-game.\nSpammed automatically during the load wait to skip title screens and navigate menus.")

        ttk.Label(save_frame, text="Close buffer (s):").grid(row=5, column=0, sticky="w", **pad)
        self.game_close_buffer_var = tk.StringVar(value="4")
        _gcb_entry = ttk.Entry(save_frame, textvariable=self.game_close_buffer_var, width=7)
        _gcb_entry.grid(row=5, column=1, sticky="w", **pad)
        _Tooltip(_gcb_entry, "Extra seconds to wait after the game process fully closes before\nrestoring the save or relaunching. Increase on slow machines or if\nEasyAntiCheat causes issues on restart.")

        # ── Choose Relic Type + Color Filter ────────────────────────── #
        type_color_frame = ttk.LabelFrame(inner, text="Choose Relic Type")
        type_color_frame.grid(row=2, column=0, sticky="ew", **pad)

        self._gem_mode_var = tk.StringVar(value="don")   # driven by relic_type_var; used by _refresh_gem_images

        rtype_row = ttk.Frame(type_color_frame)
        rtype_row.pack(anchor="w", padx=6, pady=(6, 4))
        ttk.Radiobutton(rtype_row, text="Deep of Night  (1800 murk each)",
                        variable=self.relic_type_var, value="night",
                        command=self._on_relic_type_change).pack(side="left", padx=(0, 8))
        ttk.Radiobutton(rtype_row, text="Normal  (600 murk each)",
                        variable=self.relic_type_var, value="normal",
                        command=self._on_relic_type_change).pack(side="left")
        _Tooltip(rtype_row,
                 "Deep of Night relics cost 1800 murk each and have stronger passives.\n"
                 "Normal relics cost 600 murk each.\n"
                 "This also auto-loads the correct Setup sequence and updates the gem images below.")

        ttk.Separator(type_color_frame, orient="horizontal").pack(fill="x", padx=6, pady=(0, 4))

        ttk.Label(
            type_color_frame,
            text="Select which relic colors you are hunting for. At least one color must be enabled.",
            foreground=theme.TEXT_MUTED, wraplength=700,
        ).pack(anchor="w", padx=6, pady=(0, 2))

        RELIC_COLORS = ["Red", "Blue", "Green", "Yellow"]
        color_row = ttk.Frame(type_color_frame)
        color_row.pack(fill="x", padx=6, pady=(0, 6))
        self._color_vars:     dict[str, tk.BooleanVar] = {}
        self._gem_img_labels: dict[str, tk.Label]      = {}

        for color in RELIC_COLORS:
            var = tk.BooleanVar(value=True)
            self._color_vars[color] = var

            cell = ttk.Frame(color_row)
            cell.pack(side="left", padx=10)

            img_lbl = tk.Label(cell, bg=theme.SURFACE, cursor="hand2")
            img_lbl.pack()
            img_lbl.bind("<Button-1>", lambda _e, c=color: self._toggle_color(c))
            self._gem_img_labels[color] = img_lbl

            ttk.Checkbutton(cell, text=color, variable=var,
                            command=self._on_color_change).pack()

        _Tooltip(color_row, "Relics are identified by a keyword in their name:\nRed = Burning, Blue = Drizzly, Green = Tranquil, Yellow = Luminous.\nDeselect colors you don't want — only matching colors will count as hits.")

        self._color_warn = ttk.Label(type_color_frame, text="", foreground="#ff6666")
        self._color_warn.pack(anchor="w", padx=6)

        # Populate gem images after widget hierarchy is ready
        self.after(0, self._refresh_gem_images)

        # ── Sequence Phases ──────────────────────────────────────────── #
        seq_frame = ttk.LabelFrame(inner, text="Sequence Phases")
        seq_frame.grid(row=6, column=0, sticky="ew", **pad)

        # Per-phase status labels (event counts)
        self.phase_stop_text_vars = [None, tk.StringVar(value="Insufficient murk"),
                                     None, None, None]
        self.phase_max_vars   = [None, tk.StringVar(value="50"),
                                 None, None, tk.StringVar(value="30")]
        self.phase_settle_vars = [None, tk.StringVar(value="0"),
                                  None, None, tk.StringVar(value="0.45")]
        self.phase_count_vars = [tk.StringVar(value="0 events")
                                 for _ in self._PHASE_NAMES]

        status_row = ttk.Frame(seq_frame)
        status_row.grid(row=0, column=0, sticky="w", **pad)
        for i, name in enumerate(self._PHASE_NAMES):
            ttk.Label(status_row, text=f"{name}:", foreground=theme.TEXT_MUTED).pack(
                side="left", padx=(12 if i else 0, 2))
            ttk.Label(status_row, textvariable=self.phase_count_vars[i]).pack(side="left", padx=(0, 8))

        self._manual_setup_expanded = False
        self._manual_toggle_btn = ttk.Button(
            seq_frame, text="Manual Key Recording ▼",
            command=self._toggle_manual_setup)
        self._manual_toggle_btn.grid(row=1, column=0, sticky="w", **pad)

        # Collapsible recording frame (hidden by default)
        self._manual_setup_frame = ttk.Frame(seq_frame)
        self._build_manual_setup_frame()

        # ── Relic Criteria (builder with Free Text / Exact / Pool tabs) ─ #
        self.relic_builder = RelicBuilderFrame(inner)
        self.relic_builder.grid(row=3, column=0, sticky="ew", **pad)

        # ── Curse Filter ─────────────────────────────────────────────── #
        curse_frame = ttk.LabelFrame(inner, text="Curse Filter  (relics with these curses are rejected)")
        curse_frame.grid(row=4, column=0, sticky="ew", **pad)

        ttk.Label(
            curse_frame,
            text="Select curses to block. Relics carrying any blocked curse will not count as matches. Leave empty to allow all.",
            foreground=theme.TEXT_MUTED, wraplength=700, justify="left",
        ).pack(anchor="w", padx=6, pady=(4, 2))

        curse_content = ttk.Frame(curse_frame)
        curse_content.pack(fill="both", expand=False, padx=6, pady=(0, 6))
        curse_content.columnconfigure(0, weight=3)
        curse_content.columnconfigure(2, weight=2)

        # Left: curses-only list
        curse_left = ttk.LabelFrame(curse_content, text="Curses")
        curse_left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        from bot.passives import ALL_CURSES as _ALL_CURSES
        self._curse_search_var = tk.StringVar()
        self._curse_search_var.trace_add("write", self._curse_filter_list)
        _curse_entry = ttk.Entry(curse_left, textvariable=self._curse_search_var)
        _curse_entry.pack(fill="x", padx=4, pady=(4, 2))
        _Tooltip(_curse_entry, "Search and select curses to block. Relics carrying any blocked curse are rejected even if their passives match.")

        curse_src_body = ttk.Frame(curse_left)
        curse_src_body.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._curse_src_lb = tk.Listbox(curse_src_body, height=5, selectmode="browse",
                                         exportselection=False, activestyle="none")
        from ui.theme import style_listbox as _sl
        _sl(self._curse_src_lb)
        cs_sb = ttk.Scrollbar(curse_src_body, orient="vertical", command=self._curse_src_lb.yview)
        self._curse_src_lb.configure(yscrollcommand=cs_sb.set)
        self._curse_src_lb.pack(side="left", fill="both", expand=True)
        cs_sb.pack(side="right", fill="y")
        self._curse_all_passives = _ALL_CURSES
        for p in self._curse_all_passives:
            self._curse_src_lb.insert("end", p)

        # Centre: buttons
        curse_mid = ttk.Frame(curse_content)
        curse_mid.grid(row=0, column=1, padx=6)
        ttk.Button(curse_mid, text="Block →",   command=self._curse_add,    width=10).pack(pady=4)
        ttk.Button(curse_mid, text="← Remove",  command=self._curse_remove, width=10).pack(pady=4)
        ttk.Button(curse_mid, text="Clear All",  command=self._curse_clear,  width=10).pack(pady=8)

        # Right: blocked curses list
        curse_right = ttk.LabelFrame(curse_content, text="Blocked Curses")
        curse_right.grid(row=0, column=2, sticky="nsew")
        curse_body = ttk.Frame(curse_right)
        curse_body.pack(fill="both", expand=True, padx=4, pady=4)
        self._blocked_curses_lb = tk.Listbox(curse_body, height=5, selectmode="browse",
                                              exportselection=False, activestyle="none")
        _sl(self._blocked_curses_lb)
        cb_sb = ttk.Scrollbar(curse_body, orient="vertical", command=self._blocked_curses_lb.yview)
        self._blocked_curses_lb.configure(yscrollcommand=cb_sb.set)
        self._blocked_curses_lb.pack(side="left", fill="both", expand=True)
        cb_sb.pack(side="right", fill="y")
        self._blocked_curses_list: list[str] = []

        # ── Batch Mode Settings ─────────────────────────────────────── #
        self.batch_frame = ttk.LabelFrame(inner, text="Batch Mode Settings")
        self.batch_frame.grid(row=5, column=0, sticky="ew", **pad)

        ttk.Label(self.batch_frame, text="Run for:").grid(row=0, column=0, sticky="w", **pad)
        self.batch_limit_type = tk.StringVar(value="loops")
        ttk.Radiobutton(self.batch_frame, text="Loops (max 1000)", variable=self.batch_limit_type,
                        value="loops").grid(row=0, column=1, **pad)
        ttk.Radiobutton(self.batch_frame, text="Hours (max 24)", variable=self.batch_limit_type,
                        value="hours").grid(row=0, column=2, **pad)
        self.batch_limit_var = tk.StringVar(value="20")
        ttk.Entry(self.batch_frame, textvariable=self.batch_limit_var, width=7).grid(row=0, column=3, **pad)

        ttk.Label(self.batch_frame, text="Analysis delay (s):").grid(row=1, column=0, sticky="w", **pad)
        self.batch_delay_var = tk.StringVar(value="3.0")
        _bd_entry = ttk.Entry(self.batch_frame, textvariable=self.batch_delay_var, width=7)
        _bd_entry.grid(row=1, column=1, **pad)
        _Tooltip(_bd_entry, "Wait time after inputs before taking the relic screenshot.\nIncrease if relics haven't fully loaded when captured.")

        ttk.Label(self.batch_frame, text="Output folder:").grid(row=2, column=0, sticky="w", **pad)
        self.batch_output_var = tk.StringVar(value=os.path.join(_REPO_ROOT, "batch_output"))
        ttk.Entry(self.batch_frame, textvariable=self.batch_output_var, width=52).grid(row=2, column=1,
                                                                                        columnspan=3, **pad)
        ttk.Button(self.batch_frame, text="Browse", command=self._browse_batch_output).grid(row=2, column=4, **pad)

        # Overlay toggle
        ov_chk = ttk.Checkbutton(
            self.batch_frame, text="Show HUD overlay while bot is running",
            variable=self._overlay_enabled_var,
        )
        ov_chk.grid(row=3, column=0, columnspan=5, sticky="w", **pad)
        _Tooltip(ov_chk,
                 "Displays a translucent HUD in the bottom-left of your screen with live stats and log.\n"
                 "Requires the game to run in Borderless or Fullscreen.\n"
                 "Clicking the HUD does NOT steal focus from the game window.")

        # Brute Force Analysis toggle
        bf_chk = ttk.Checkbutton(
            self.batch_frame, text="⚡ Brute Force Analysis",
            variable=self._parallel_enabled_var,
            command=self._on_parallel_toggle,
        )
        bf_chk.grid(row=4, column=0, columnspan=2, sticky="w", **pad)
        _Tooltip(bf_chk,
                 "Runs multiple OCR workers in parallel to speed up relic analysis.\n"
                 "Each extra worker loads an additional ~100 MB of RAM for the OCR model.\n\n"
                 "Recommended: 2–4 workers (safe for most PCs).\n"
                 "6+ workers: use at your own discretion — very high CPU/RAM usage.\n"
                 "Max: 8 workers.\n\n"
                 "Leave OFF if you notice crashes or system slowdowns.")
        ttk.Label(self.batch_frame, text="Workers:").grid(row=4, column=2, **pad)
        self._parallel_spin = ttk.Spinbox(
            self.batch_frame, from_=2, to=8, width=4,
            textvariable=self._parallel_workers_var, state="disabled",
        )
        self._parallel_spin.grid(row=4, column=3, sticky="w", **pad)
        _Tooltip(self._parallel_spin,
                 "Number of parallel OCR workers (2–8).\n"
                 "Each worker uses ~100 MB extra RAM for its own OCR model.\n\n"
                 "⚠ 6+ workers: use at your own discretion.\n"
                 "Very high CPU and RAM usage — may destabilise the game or OS.")
        self._ram_label_var = tk.StringVar(value="")
        self._ram_label = ttk.Label(self.batch_frame, textvariable=self._ram_label_var,
                                    foreground=theme.TEXT_MUTED)
        self._ram_label.grid(row=4, column=4, sticky="w", **pad)
        self._parallel_workers_var.trace_add("write", lambda *_: self._update_ram_label())

        # Async Analysis toggle
        async_chk = ttk.Checkbutton(
            self.batch_frame, text="⚑ Async Analysis",
            variable=self._async_enabled_var,
        )
        async_chk.grid(row=5, column=0, columnspan=2, sticky="w", **pad)
        _Tooltip(async_chk,
                 "Decouples screenshot capture from OCR analysis.\n"
                 "The bot captures all relics first, then analyzes them in the\n"
                 "background while the next iteration is already running.\n\n"
                 "Screenshots appear live in the output folder as pending files\n"
                 "and are renamed/removed once analysis completes.\n\n"
                 "After all iterations are captured, the bot waits for analysis\n"
                 "to fully finish before stopping (grace period).\n\n"
                 "Best paired with Brute Force Analysis for maximum throughput.")

        # ── Bot Control ─────────────────────────────────────────────── #
        ctrl_frame = ttk.LabelFrame(inner, text="Bot Control")
        ctrl_frame.grid(row=7, column=0, sticky="ew", **pad)

        self.start_btn = ttk.Button(ctrl_frame, text="▶ START", command=self._start_bot,
                                    style="Start.TButton")
        self.start_btn.grid(row=0, column=0, padx=12, pady=6)
        self.stop_btn = ttk.Button(ctrl_frame, text="■ STOP", command=self._stop_bot,
                                   state="disabled", style="Stop.TButton")
        self.stop_btn.grid(row=0, column=1, padx=12, pady=6)

        self.status_var = tk.StringVar(value="Status: Idle")
        self.status_label = ttk.Label(ctrl_frame, textvariable=self.status_var,
                                      foreground=theme.TEXT_MUTED)
        self.status_label.grid(row=0, column=3, padx=16)

        self.attempt_var = tk.StringVar(value="Attempts: 0")
        ttk.Label(ctrl_frame, textvariable=self.attempt_var).grid(row=0, column=4, **pad)

        # Screen capture indicator
        self.capture_lbl = ttk.Label(ctrl_frame, text="📷", foreground=theme.TEXT_MUTED)
        self.capture_lbl.grid(row=0, column=5, padx=8)

        # ── Log ─────────────────────────────────────────────────────── #
        log_frame = ttk.LabelFrame(inner, text="Log")
        log_frame.grid(row=8, column=0, sticky="ew", **pad)
        self.log_box = scrolledtext.ScrolledText(
            log_frame, height=10, width=82, state="disabled", wrap="word"
        )
        theme.style_text(self.log_box)
        self.log_box.grid(row=0, column=0, **pad)

        # ── Credit ──────────────────────────────────────────────────── #
        ttk.Label(inner, text="Made by Pulgo",
                  foreground=theme.TEXT_MUTED,
                  font=("Segoe UI", 8)).grid(
            row=9, column=0, sticky="e", padx=12, pady=(0, 4)
        )

        # Auto-load standard sequences after UI is built
        self.after(100, self._auto_load_sequences)

    # ------------------------------------------------------------------ #
    #  MANUAL SETUP WINDOW
    # ------------------------------------------------------------------ #

    def _build_manual_setup_frame(self):
        """Build recording UI inside the collapsible frame."""
        frame = self._manual_setup_frame
        pad = {"padx": 8, "pady": 4}

        # F9 recording hotkey enable toggle
        self._recording_enabled_var = tk.BooleanVar(value=False)
        hk_row = ttk.Frame(frame)
        hk_row.pack(fill="x", padx=4, pady=(6, 2))
        hk_cb = ttk.Checkbutton(hk_row, text="Enable recording hotkey (F9)",
                                 variable=self._recording_enabled_var)
        hk_cb.pack(side="left")
        _Tooltip(hk_cb, "When enabled, F9 starts/stops recording while this panel is open.\nDisabled by default to prevent accidental recordings during normal use.")

        # Stop recording + status + hotkey buttons
        hdr = ttk.Frame(frame)
        hdr.pack(fill="x", **pad)
        self.stop_rec_btn = ttk.Button(hdr, text="⏹ Stop Recording",
                                       command=self._stop_recording, state="disabled")
        self.stop_rec_btn.pack(side="left", padx=4)
        self.rec_status_var = tk.StringVar(value="")
        ttk.Label(hdr, textvariable=self.rec_status_var,
                  foreground="#ff6666", font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)
        self._hotkey_btn = ttk.Button(hdr, text=f"Rec Hotkey: {self._hotkey_display}",
                                      command=self._set_hotkey_dialog, width=18)
        self._hotkey_btn.pack(side="left", padx=(12, 0))
        # Phase notebook
        nb = ttk.Notebook(frame)
        nb.pack(fill="both", expand=True, **pad)
        self._phase_notebook = nb

        _phase_labels = [
            (
                "Setup",
                "Plays once — navigates from Roundtable Hold to the Relic Rites buy menu.",
                (
                    "Phase 0 — Setup\n"
                    "Navigates from Roundtable Hold to the Relic Rites merchant buy screen.\n\n"
                    "Default sequence assumes:\n"
                    "  • You own the DLC (Nightreign)\n"
                    "  • All shops in Roundtable Hold are unlocked\n\n"
                    "⚠  If you don't have the DLC or not all shops are unlocked,\n"
                    "    RE-RECORD this phase to match your own menu layout."
                ),
                False,
            ),
            (
                "Buy Loop",
                "Repeats — buys one relic. Stops on 'Insufficient murk' popup.",
                (
                    "Phase 1 — Buy Loop\n"
                    "Presses confirm to purchase relics one by one.\n"
                    "Stops automatically when the game shows the 'Insufficient murk' message.\n\n"
                    "Works for all setups — no re-recording needed."
                ),
                True,
            ),
            (
                "Relic Rites Nav",
                "Plays once — opens the Relic Rites review screen (Esc → Map → down → F).",
                (
                    "Phase 2 — Relic Rites Nav\n"
                    "After buying, opens the Relic Rites review screen via the pause menu.\n"
                    "Sequence: Esc → Map tab → scroll down to Relic Rites → F to confirm.\n\n"
                    "⚠  If you don't have all shops unlocked, the menu layout may differ.\n"
                    "    RE-RECORD this phase if navigation fails to land on the sell screen."
                ),
                False,
            ),
            (
                "Navigate to Sell",
                "Automatic — OCR detects which character tab is active, then presses F2 exactly N times.",
                (
                    "Phase 3 — Navigate to Sell  (no recording needed)\n"
                    "Runs automatically whenever Phase 2 is configured.\n\n"
                    "How it works:\n"
                    "  1. Takes a screenshot and identifies the active character tab via OCR.\n"
                    "  2. Presses F2 the exact number of times needed to reach Sell\n"
                    "     (Wylder=10, Guardian=9 … Undertaker=1, Sell=0).\n"
                    "  3. Verifies the Sell page is open.  If not, runs a safety F2 loop\n"
                    "     (up to 15 extra presses) to recover automatically.\n\n"
                    "No recording required — this phase adapts to any starting tab."
                ),
                False,
            ),
            (
                "Review Step",
                "Repeats — advances to the next relic. Stops after reviewing all purchased relics.",
                (
                    "Phase 4 — Review Step\n"
                    "Presses the right arrow to move from one relic to the next.\n"
                    "Stops automatically after reviewing all relics (count = murk spent ÷ relic cost).\n\n"
                    "Works for all setups — no re-recording needed."
                ),
                True,
            ),
        ]
        self.phase_rec_btns = []

        for phase_idx, (tab_title, hint_text, tooltip_text, has_stop) in enumerate(_phase_labels):
            tab = ttk.Frame(nb)
            nb.add(tab, text=tab_title)

            hint_lbl = ttk.Label(tab, text=hint_text, foreground=theme.TEXT_MUTED)
            hint_lbl.grid(row=0, column=0, columnspan=5, sticky="w", padx=6, pady=2)
            _Tooltip(hint_lbl, tooltip_text)

            rec_btn = ttk.Button(tab, text="⏺ Record",
                                 command=lambda p=phase_idx: self._start_recording(p))
            rec_btn.grid(row=1, column=0, **pad)
            self.phase_rec_btns.append(rec_btn)

            ttk.Button(tab, text="▶ Test",
                       command=lambda p=phase_idx: self._test_play(p)).grid(row=1, column=1, **pad)
            ttk.Button(tab, text="Load",
                       command=lambda p=phase_idx: self._load_sequence(p)).grid(row=1, column=2, **pad)
            ttk.Button(tab, text="Save",
                       command=lambda p=phase_idx: self._save_sequence(p)).grid(row=1, column=3, **pad)
            ttk.Label(tab, textvariable=self.phase_count_vars[phase_idx]).grid(row=1, column=4, **pad)

            if has_stop:
                ttk.Label(tab, text="Settle (s):").grid(row=2, column=0, sticky="w", **pad)
                ttk.Entry(tab, textvariable=self.phase_settle_vars[phase_idx],
                          width=6).grid(row=2, column=1, **pad)

    def _toggle_manual_setup(self):
        if self._manual_setup_expanded:
            self._manual_setup_frame.grid_remove()
            self._manual_setup_expanded = False
            self._manual_toggle_btn.config(text="Manual Key Recording ▼")
        else:
            self._manual_setup_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=2)
            self._manual_setup_expanded = True
            self._manual_toggle_btn.config(text="Manual Key Recording ▲")

    # ------------------------------------------------------------------ #
    #  SEQUENCE AUTO-LOAD
    # ------------------------------------------------------------------ #

    _SEQ_DIR = os.path.join(_REPO_ROOT, "sequences")

    def _auto_load_sequences(self):
        """Load all standard sequence files on startup."""
        rtype = self.relic_type_var.get()
        phase0_file = ("phase0_setup_don.json" if rtype == "night" else "phase0_setup_normal.json")
        files = [
            phase0_file,
            "phase1_buy_loop.json",
            "phase2_relic_rites_nav.json",
            "phase3_navigate_to_sell.json",
            "phase4_review_step.json",
        ]
        for i, fname in enumerate(files):
            path = os.path.join(self._SEQ_DIR, fname)
            if os.path.exists(path):
                try:
                    self.recorder.load(path)
                    self.phase_events[i] = list(self.recorder.events)
                    n = len(self.phase_events[i])
                    self.phase_count_vars[i].set(f"{n} events")
                    self._log(f"Auto-loaded Phase {i} ({self._PHASE_NAMES[i]}): {n} events from {fname}")
                except Exception as e:
                    self._log(f"WARNING: Failed to auto-load Phase {i} ({fname}): {e}")
            else:
                self._log(f"WARNING: Sequence file not found for Phase {i}: {path}")

    def _on_relic_type_change(self):
        """Swap Phase 0 sequence and sync gem images when the user switches relic type."""
        rtype = self.relic_type_var.get()
        self._gem_mode_var.set("don" if rtype == "night" else "normal")
        self._refresh_gem_images()
        fname = ("phase0_setup_don.json" if rtype == "night" else "phase0_setup_normal.json")
        path = os.path.join(self._SEQ_DIR, fname)
        if os.path.exists(path):
            try:
                self.recorder.load(path)
                self.phase_events[0] = list(self.recorder.events)
                n = len(self.phase_events[0])
                self.phase_count_vars[0].set(f"{n} events")
                self._log(f"Phase 0 (Setup) swapped to {rtype} sequence ({n} events).")
            except Exception as e:
                self._log(f"WARNING: Could not load Phase 0 for '{rtype}': {e}")

    def _log_screen_resolution(self):
        """Log detected screen resolution so the user can verify the crop is correct."""
        from bot.screen_capture import get_screen_size
        w, h = get_screen_size()
        self._log(
            f"Screen resolution detected: {w}×{h}. "
            f"Relic panel crop: left={int(w*0.45)}px, top={int(h*0.65)}px "
            f"→ {w - int(w*0.45)}×{h - int(h*0.65)}px region. "
            f"Run in borderless or fullscreen for best results."
        )

    # ------------------------------------------------------------------ #
    #  SAVE FILE HELPERS
    # ------------------------------------------------------------------ #

    def _browse_save(self):
        path = filedialog.askopenfilename(title="Select save file")
        if path:
            self.save_path_var.set(path)

    def _browse_backup(self):
        path = filedialog.askdirectory(title="Choose backup folder")
        if path:
            self.backup_path_var.set(path)

    def _browse_batch_output(self):
        path = filedialog.askdirectory(title="Choose batch output folder")
        if path:
            self.batch_output_var.set(path)

    def _on_parallel_toggle(self):
        """Enable/disable the workers spinbox based on the Brute Force checkbox."""
        state = "normal" if self._parallel_enabled_var.get() else "disabled"
        self._parallel_spin.config(state=state)
        self._update_ram_label()

    def _update_ram_label(self):
        """Update the RAM estimate label next to the workers spinbox."""
        if not self._parallel_enabled_var.get():
            self._ram_label_var.set("")
            return
        try:
            w = int(self._parallel_workers_var.get())
        except (ValueError, tk.TclError):
            self._ram_label_var.set("")
            return
        mb = w * 100
        if w >= 6:
            self._ram_label_var.set(f"~{mb} MB RAM ⚠")
            self._ram_label.configure(foreground="#d4a843")
        else:
            self._ram_label_var.set(f"~{mb} MB RAM")
            self._ram_label.configure(foreground=theme.TEXT_MUTED)

    def _browse_game_exe(self):
        path = filedialog.askopenfilename(
            title="Select game executable",
            filetypes=[("Executable", "*.exe"), ("All", "*.*")]
        )
        if path:
            self.game_exe_var.set(path)

    # ------------------------------------------------------------------ #
    #  PROFILE MANAGEMENT
    # ------------------------------------------------------------------ #

    def _profile_path(self, name: str) -> str:
        safe = "".join(c for c in name if c.isalnum() or c in " _-").strip()
        return os.path.join(_PROFILES_DIR, f"{safe}.json")

    def _refresh_profile_list(self):
        try:
            names = [os.path.splitext(f)[0] for f in sorted(os.listdir(_PROFILES_DIR)) if f.endswith(".json")]
        except FileNotFoundError:
            names = []
        self._profile_cb["values"] = names

    def _profile_to_dict(self) -> dict:
        return {
            "save_path": self.save_path_var.get(),
            "backup_folder": self.backup_path_var.get(),
            "game_executable": self.game_exe_var.get(),
            "game_load_wait": self.game_load_wait_var.get(),
            "game_close_buffer": self.game_close_buffer_var.get(),
            "confirm_key": self.confirm_key_var.get(),
            "batch_limit_type": self.batch_limit_type.get(),
            "batch_limit": self.batch_limit_var.get(),
            "batch_delay": self.batch_delay_var.get(),
            "batch_output": self.batch_output_var.get(),
            "phase_events": self.phase_events,
            "phase1_stop_text": self.phase_stop_text_vars[1].get(),
            "phase1_max_loops": self.phase_max_vars[1].get(),
            "phase1_settle": self.phase_settle_vars[1].get(),
            "phase4_settle": self.phase_settle_vars[4].get(),
            "relic_type": self.relic_type_var.get(),
            "hotkey_str": self._hotkey_str,
            "hotkey_display": self._hotkey_display,
            "blocked_curses": list(self._blocked_curses_list),
            "allowed_colors": self._get_allowed_colors(),
            "criteria": self.relic_builder.get_state(),
            "parallel_enabled": self._parallel_enabled_var.get(),
            "parallel_workers": self._parallel_workers_var.get(),
            "async_enabled": self._async_enabled_var.get(),
        }

    def _dict_to_profile(self, data: dict):
        _default_backup = os.path.join(_REPO_ROOT, "save_backups")
        _default_output = os.path.join(_REPO_ROOT, "batch_output")
        self.save_path_var.set(data.get("save_path", ""))
        self.backup_path_var.set(data.get("backup_folder", _default_backup))
        self.game_exe_var.set(data.get("game_executable", ""))
        self.game_load_wait_var.set(str(data.get("game_load_wait", "30")))
        self.game_close_buffer_var.set(str(data.get("game_close_buffer", "4")))
        self.confirm_key_var.set(data.get("confirm_key", "e"))
        self.batch_limit_type.set(data.get("batch_limit_type", "loops"))
        self.batch_limit_var.set(str(data.get("batch_limit", "20")))
        self.batch_delay_var.set(str(data.get("batch_delay", "3.0")))
        self.batch_output_var.set(data.get("batch_output", _default_output))
        # Load phase events (support old single-sequence profiles via "input_sequence")
        if "phase_events" in data:
            loaded = data["phase_events"]
            for i in range(5):
                self.phase_events[i] = loaded[i] if i < len(loaded) else []
        else:
            # Legacy: treat old recorded sequence as Phase 0 (Setup)
            self.phase_events = [data.get("input_sequence", []), [], [], [], []]
        for i, var in enumerate(self.phase_count_vars):
            var.set(f"{len(self.phase_events[i])} events")
        self.phase_stop_text_vars[1].set(data.get("phase1_stop_text", "Insufficient murk"))
        self.phase_max_vars[1].set(str(data.get("phase1_max_loops", "50")))
        self.phase_settle_vars[1].set(str(data.get("phase1_settle", "0.5")))
        self.phase_settle_vars[4].set(str(data.get("phase4_settle", data.get("phase3_settle", "0.5"))))
        self.relic_type_var.set(data.get("relic_type", "night"))
        self._parallel_enabled_var.set(data.get("parallel_enabled", False))
        self._parallel_workers_var.set(data.get("parallel_workers", 2))
        self._async_enabled_var.set(data.get("async_enabled", False))
        self._on_parallel_toggle()
        if "hotkey_str" in data:
            self._hotkey_str = data["hotkey_str"]
            self._hotkey_display = data.get("hotkey_display", self._hotkey_str.replace("Key.", "").upper())
            self._hotkey_btn.config(text=f"Rec Hotkey: {self._hotkey_display}")
            self._start_global_hotkey_listener()
        if "blocked_curses" in data:
            self._curse_clear()
            saved = data["blocked_curses"]
            # Support old format (newline-separated string) and new (list)
            if isinstance(saved, str):
                items = [s.strip() for s in saved.splitlines() if s.strip()]
            else:
                items = list(saved)
            for item in items:
                self._blocked_curses_list.append(item)
                self._blocked_curses_lb.insert("end", item)
        if "allowed_colors" in data:
            saved = data["allowed_colors"]
            for color, var in self._color_vars.items():
                var.set(color in saved)
        # gem images follow relic_type — sync after relic_type is loaded
        self._gem_mode_var.set("don" if self.relic_type_var.get() == "night" else "normal")
        self._refresh_gem_images()
        if "criteria" in data:
            self.relic_builder.set_state(data["criteria"])

    def _load_profile(self):
        name = self._profile_var.get().strip()
        if not name:
            messagebox.showwarning("No Profile Selected", "Select a profile from the list first.")
            return
        try:
            with open(self._profile_path(name), "r", encoding="utf-8") as f:
                data = json.load(f)
            self._dict_to_profile(data)
            self._log(f"Profile '{name}' loaded.")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def _save_profile(self):
        name = self._profile_var.get().strip()
        if not name:
            self._save_profile_as()
            return
        self._write_profile(name)

    def _save_profile_as(self):
        path = filedialog.asksaveasfilename(
            title="Save Profile As",
            initialdir=_PROFILES_DIR,
            defaultextension=".json",
            filetypes=[("Profile", "*.json"), ("All", "*.*")],
        )
        if not path:
            return
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._profile_to_dict(), f, indent=2)
            self._refresh_profile_list()
            self._profile_var.set(name)
            self._log(f"Profile '{name}' saved to {path}.")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def _write_profile(self, name: str):
        os.makedirs(_PROFILES_DIR, exist_ok=True)
        try:
            with open(self._profile_path(name), "w", encoding="utf-8") as f:
                json.dump(self._profile_to_dict(), f, indent=2)
            self._refresh_profile_list()
            self._log(f"Profile '{name}' saved.")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def _delete_profile(self):
        name = self._profile_var.get().strip()
        if not name:
            messagebox.showwarning("No Profile Selected", "Select a profile to delete.")
            return
        if not messagebox.askyesno("Delete Profile", f"Delete profile '{name}'?"):
            return
        try:
            os.remove(self._profile_path(name))
            self._profile_var.set("")
            self._refresh_profile_list()
            self._log(f"Profile '{name}' deleted.")
        except Exception as e:
            messagebox.showerror("Delete Error", str(e))

    def _reset_to_defaults(self):
        """Restore all settings to their out-of-the-box defaults."""
        if not messagebox.askyesno(
            "Restore Defaults",
            "Reset all settings to their defaults?\n\n"
            "This will clear your save/backup paths, criteria, filters, and sequences.\n"
            "Your saved profiles will not be affected.",
        ):
            return
        self._dict_to_profile({})   # empty dict → every field falls back to its default
        self._auto_load_sequences()
        self._log("Settings restored to defaults.")

    # ------------------------------------------------------------------ #
    #  GAME MANAGEMENT
    # ------------------------------------------------------------------ #

    def _is_game_running(self, exe_name: str) -> bool:
        try:
            result = subprocess.run(
                ["tasklist", "/fi", f"imagename eq {exe_name}"],
                capture_output=True, text=True
            )
            return exe_name.lower() in result.stdout.lower()
        except Exception:
            return False

    def _close_game(self) -> bool:
        exe_path = self.game_exe_var.get().strip()
        if not exe_path:
            return True
        exe_name = os.path.basename(exe_path)
        if not self._is_game_running(exe_name):
            self._log("Game already not running — applying close buffer before relaunch…")
            try:
                _buf = float(self.game_close_buffer_var.get())
            except Exception:
                _buf = 4.0
            if _buf > 0:
                time.sleep(_buf)
            return True
        self._log(f"Closing game ({exe_name})…")
        subprocess.run(["taskkill", "/f", "/im", exe_name], capture_output=True)
        for _ in range(120):  # wait up to 60 s
            time.sleep(0.5)
            if not self.bot_running:
                return False
            if not self._is_game_running(exe_name):
                self._log("Game closed — waiting for cleanup…")
                try:
                    _buf = float(self.game_close_buffer_var.get())
                except Exception:
                    _buf = 4.0
                if _buf > 0:
                    time.sleep(_buf)
                return True
        self._log("WARNING: Game did not close within 60s.")
        return False

    _STEAM_APP_ID = "2622380"

    def _launch_game(self):
        exe_path = self.game_exe_var.get().strip()
        self._log(f"Launching via Steam (App ID: {self._STEAM_APP_ID})…")
        os.startfile(f"steam://rungameid/{self._STEAM_APP_ID}")
        if exe_path:
            # Also store exe path so focus can find the process window
            pass

    def _focus_game_window(self, exe_name: str, timeout: float = 15.0) -> bool:
        """Find the game window by process exe name and bring it to the foreground.
        Polls until the window appears or timeout expires. Returns True on success."""
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        target = exe_name.lower()
        deadline = time.time() + timeout

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        while time.time() < deadline:
            if not self.bot_running:
                return False

            found = []

            def _cb(hwnd, _):
                if not user32.IsWindowVisible(hwnd):
                    return True
                pid = ctypes.c_ulong(0)
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                h = kernel32.OpenProcess(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
                if h:
                    buf = ctypes.create_unicode_buffer(260)
                    sz = ctypes.c_ulong(260)
                    if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(sz)):
                        if os.path.basename(buf.value).lower() == target:
                            found.append(hwnd)
                    kernel32.CloseHandle(h)
                return True

            user32.EnumWindows(EnumWindowsProc(_cb), None)

            if found:
                hwnd = found[0]
                user32.ShowWindow(hwnd, 9)   # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
                return True

            time.sleep(0.5)

        return False

    def _esc_to_game_screen(self, region) -> bool:
        """ESC recovery: press ESC, wait for OCR to confirm screen state, repeat
        until the Equipment menu tab is detected, then press ESC once more to
        return to the game screen.

        Each ESC press is followed by a 0.5 s settle delay and a full OCR check.
        The next press fires only after the analysis completes — recovery speed
        is proportional to actual UI transition time rather than a fixed timer.

        Works regardless of how many menus deep the bot is stuck in (1–3 ESCs
        typically needed). Times out after 30 s.

        Returns True on success, False on timeout.
        """
        self._log("[Recovery] ESC recovery — pressing ESC until Equipment menu appears…")
        deadline = time.time() + 30
        while time.time() < deadline:
            if not self.bot_running:
                return False
            self.player.tap("Key.esc")
            time.sleep(0.5)   # let UI transition settle before capturing
            try:
                _rec_img = screen_capture.capture(region)
                if relic_analyzer.check_text_visible(_rec_img, "equipment"):
                    self._log("[Recovery] Equipment menu detected — pressing ESC to return to game.")
                    time.sleep(0.3)
                    self.player.tap("Key.esc")
                    time.sleep(3.5)   # extended settle: ensure menu fully closes before next phase
                    return True
            except Exception as _re:
                self._log(f"[Recovery] OCR error: {_re}")
        self._log("[Recovery] Could not find Equipment menu within 30 s — aborting.")
        return False

    def _confirm_in_game(self, region, exe_name: str) -> bool:
        """Phase -0.5: verify the game has loaded past the title screen into the
        game world before Phase 0 begins.

        Presses ESC repeatedly (up to 10 s per attempt) and checks for the
        Equipment menu tab via OCR. Presence of the Equipment tab confirms the
        game world is active. On confirmation, one final ESC dismisses the menu
        and leaves the bot in a neutral in-game state ready for Phase 0.

        If Equipment is not found in 10 s, presses F for 10 s (0.5 s interval)
        to advance through the title screen, then retries the ESC check.
        Up to 3 full ESC-check cycles. Returns False if all cycles fail.
        """
        _MAX_CYCLES = 3
        for _cycle in range(_MAX_CYCLES):
            self._log(
                f"[Phase -0.5] Confirming in-game state "
                f"(cycle {_cycle + 1}/{_MAX_CYCLES})…")
            _esc_deadline = time.time() + 10
            while time.time() < _esc_deadline:
                if not self.bot_running:
                    return False
                self.player.tap("Key.esc")
                time.sleep(0.5)
                try:
                    _img = screen_capture.capture(region)
                    if relic_analyzer.check_text_visible(_img, "equipment"):
                        self._log("[Phase -0.5] Equipment menu detected — in-game confirmed.")
                        time.sleep(0.5)
                        self.player.tap("Key.esc")
                        time.sleep(1.5)   # wait for menu to fully close before Phase 0
                        return True
                except Exception as _ce:
                    self._log(f"[Phase -0.5] OCR error: {_ce}")

            # ESC check timed out — press F to advance through title screen
            if _cycle < _MAX_CYCLES - 1:
                self._log(
                    "[Phase -0.5] Equipment menu not found — "
                    "pressing F for 10 s to advance through title screen.")
                _f_deadline = time.time() + 10
                _f_focused  = self._focus_game_window(exe_name) if exe_name else False
                while time.time() < _f_deadline:
                    if not self.bot_running:
                        return False
                    if _f_focused:
                        self.player.tap("f")
                    time.sleep(0.5)
                    if not _f_focused and exe_name:
                        _f_focused = self._focus_game_window(exe_name, timeout=1.0)

        self._log("[Phase -0.5] Could not confirm in-game state after 3 cycles — aborting.")
        return False

    def _game_watchdog(self):
        """Background thread: polls for a hung game window every 5 s.
        Requires two consecutive IsHungAppWindow detections (~10 s) before acting.
        Force-kills the process and sets self._game_hung = True."""
        user32   = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        _consecutive = 0

        while self.bot_running:
            time.sleep(5)
            if not self.bot_running:
                break

            exe_name = os.path.basename(self.game_exe_var.get().strip()).lower()
            if not exe_name:
                _consecutive = 0
                continue

            found = []

            def _enum_cb(hwnd, _):
                if not user32.IsWindowVisible(hwnd):
                    return True
                pid = ctypes.c_ulong(0)
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                h = kernel32.OpenProcess(0x1000, False, pid.value)
                if h:
                    buf = ctypes.create_unicode_buffer(260)
                    sz  = ctypes.c_ulong(260)
                    if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(sz)):
                        if os.path.basename(buf.value).lower() == exe_name:
                            found.append(hwnd)
                    kernel32.CloseHandle(h)
                return True

            try:
                user32.EnumWindows(EnumWindowsProc(_enum_cb), None)
            except Exception:
                _consecutive = 0
                continue

            if not found:
                _consecutive = 0
                continue

            try:
                is_hung = bool(user32.IsHungAppWindow(found[0]))
            except Exception:
                _consecutive = 0
                continue

            if is_hung:
                _consecutive += 1
                self._log(f"[Watchdog] Game window not responding ({_consecutive}/2)…")
                if _consecutive >= 2:
                    self._log("[Watchdog] Game confirmed hung — force-closing…")
                    exe_full = os.path.basename(self.game_exe_var.get().strip())
                    subprocess.run(["taskkill", "/F", "/IM", exe_full], capture_output=True)
                    self._game_hung = True
                    _consecutive = 0
            else:
                _consecutive = 0

    # ------------------------------------------------------------------ #
    #  BACKUP READY CONFIRMATION
    # ------------------------------------------------------------------ #

    def _ask_backup_ready(self):
        msg = (
            "Backup complete!\n\n"
            "The bot will automatically close the game, restore your save, "
            "and relaunch it at the start of each iteration.\n\n"
            "Click OK to begin."
        )
        # No overlay exists yet — show dialog cleanly in front of everything
        self.wm_attributes("-topmost", True)
        self.lift()
        self.focus_force()
        messagebox.showinfo("Backup Ready", msg, parent=self)
        self.wm_attributes("-topmost", False)
        # Now create and launch the overlay (only if enabled)
        if self._overlay_enabled_var.get():
            from ui.overlay import BotOverlay
            from bot.screen_capture import get_screen_size
            sw, sh = get_screen_size()
            self._overlay = BotOverlay(self)
            self._overlay.build(sw, sh, async_mode=self._async_enabled_var.get())
            self._overlay.set_reset_iter_callback(self._request_reset_iter)
            self._overlay.set_stop_callback(self._request_stop_after_batch)
            self._overlay.set_force_stop_callback(self._stop_bot)
            def _fmt_best(info, suffix):
                if info is None:
                    return "N/A"
                return f"Batch #{info['iteration']:03d}  —  {info['count']} {suffix}"
            self._overlay.update(
                at_33=self._ov_at_33, at_23=self._ov_at_23, at_duds=self._ov_at_duds,
                best_33=_fmt_best(self._best_33_iter, "★★★"),
                best_hits=_fmt_best(self._best_hits_iter, "hits"),
            )
            self._overlay.start_game_watch(
                getattr(self, "_overlay_exe_frag", "nightreign"))
        self._ready_event.set()

    # ------------------------------------------------------------------ #
    #  INPUT RECORDING
    # ------------------------------------------------------------------ #

    _PHASE_NAMES = ["Setup", "Buy Loop", "Relic Rites Nav", "Navigate to Sell", "Review Step"]

    def _start_recording(self, phase: int):
        self._active_phase = phase
        for btn in self.phase_rec_btns:
            btn.config(state="disabled")
        self.stop_rec_btn.config(state="disabled")
        self._log(f"Recording Phase {phase} ({self._PHASE_NAMES[phase]}) in 3s — switch to game.")
        self._rec_countdown(3)

    def _rec_countdown(self, n: int):
        if n > 0:
            self.rec_status_var.set(f"Starting in {n}…")
            self.after(1000, self._rec_countdown, n - 1)
            return
        bot_hwnd = self.winfo_id()
        def _game_only():
            try:
                return ctypes.windll.user32.GetForegroundWindow() != bot_hwnd
            except Exception:
                return True
        self.recorder.filter_fn = _game_only
        self.recorder.suppress_keys = {self._hotkey_str}
        self.recorder.start()
        self._rec_blink = True
        self.stop_rec_btn.config(state="normal")
        self.rec_status_var.set("")
        self._log("Recording active — inputs only captured while the game window is focused.")
        self._poll_event_count()

    def _poll_event_count(self):
        if self.recorder.recording:
            p = self._active_phase
            self.phase_count_vars[p].set(f"{len(self.recorder.events)} events")
            self.rec_status_var.set("● RECORDING" if self._rec_blink else "○ RECORDING")
            self._rec_blink = not self._rec_blink
            self.after(500, self._poll_event_count)

    # ------------------------------------------------------------------ #
    #  GLOBAL HOTKEY  (works while game window has focus)
    # ------------------------------------------------------------------ #

    def _start_global_hotkey_listener(self):
        """Start (or restart) the persistent listener that watches for the hotkey."""
        if self._global_kb_listener is not None:
            try:
                self._global_kb_listener.stop()
            except Exception:
                pass

        hotkey = self._hotkey_str

        def _on_press(key):
            try:
                k = key.char if (hasattr(key, "char") and key.char) else str(key)
            except Exception:
                k = str(key)
            if k == hotkey:
                self.after(0, self._hotkey_pressed)

        self._global_kb_listener = _kb.Listener(on_press=_on_press, daemon=True)
        self._global_kb_listener.start()

    def _hotkey_pressed(self):
        """Toggle recording — only active when recording is enabled in Manual Key Recording."""
        if not (hasattr(self, "_recording_enabled_var") and self._recording_enabled_var.get()):
            return
        if not self._manual_setup_expanded:
            return
        if self.recorder.recording:
            self._stop_recording()
        elif not self.bot_running:
            try:
                phase = self._phase_notebook.index(self._phase_notebook.select())
            except Exception:
                phase = 0
            self._start_recording(phase)

    def _set_hotkey_dialog(self):
        """Show a small dialog that captures the next keypress as the new hotkey."""
        dlg = tk.Toplevel(self)
        dlg.title("Set Recording Hotkey")
        dlg.geometry("290x115")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self)

        tk.Label(dlg, text="Press any key to use as the\nrecording toggle hotkey:").pack(pady=8)
        lbl = tk.Label(dlg, text="Waiting for key…", font=("", 11, "bold"))
        lbl.pack()

        done = [False]
        temp_listener = [None]

        def _capture(key):
            if done[0]:
                return False
            done[0] = True
            try:
                k = key.char if (hasattr(key, "char") and key.char) else str(key)
            except Exception:
                k = str(key)
            display = k.replace("Key.", "").upper() if k.startswith("Key.") else k.upper()
            self._hotkey_str = k
            self._hotkey_display = display

            def _finish():
                lbl.config(text=f"Set to: {display}")
                self._hotkey_btn.config(text=f"Rec Hotkey: {display}")
                self._start_global_hotkey_listener()
                dlg.after(700, dlg.destroy)

            self.after(0, _finish)
            return False  # stops this temporary listener

        listener = _kb.Listener(on_press=_capture, daemon=True)
        temp_listener[0] = listener
        listener.start()
        dlg.protocol("WM_DELETE_WINDOW", lambda: (listener.stop(), dlg.destroy()))

    def _request_reset_iter(self):
        """Overlay Reset Iteration button: confirm then signal the batch loop to soft-nuke this iteration."""
        if not self.bot_running:
            return
        if not messagebox.askyesno(
            "Reset Iteration",
            "Close the game, delete this iteration's folder, restore the save, and re-run this iteration?",
            parent=self,
        ):
            return
        self._reset_iter_requested = True
        self.player.stop()   # interrupt any ongoing play() so the phase exits quickly
        self._log("⟳ Reset iteration requested — interrupting current phase.")

    def _on_app_close(self):
        """Stop the global hotkey listener then close the window."""
        if self._global_kb_listener is not None:
            try:
                self._global_kb_listener.stop()
            except Exception:
                pass
        self.destroy()

    def _stop_recording(self):
        self.recorder.stop()
        self.recorder.filter_fn = None
        p = self._active_phase
        self.phase_events[p] = list(self.recorder.events)
        for btn in self.phase_rec_btns:
            btn.config(state="normal")
        self.stop_rec_btn.config(state="disabled")
        self.rec_status_var.set("")
        n = len(self.phase_events[p])
        self.phase_count_vars[p].set(f"{n} events")
        self._log(f"Phase {p} ({self._PHASE_NAMES[p]}) recording stopped. {n} events captured.")

    def _test_play(self, phase: int):
        if not self.phase_events[phase]:
            messagebox.showwarning("No Sequence", f"Record or load Phase {phase} first.")
            return
        threading.Thread(target=self.player.play,
                         args=(self.phase_events[phase],), daemon=True).start()
        self._log(f"Test playback: Phase {phase} ({self._PHASE_NAMES[phase]})…")

    def _load_sequence(self, phase: int):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if not path:
            return
        try:
            self.recorder.load(path)
            self.phase_events[phase] = list(self.recorder.events)
            n = len(self.phase_events[phase])
            self.phase_count_vars[phase].set(f"{n} events")
            self._log(f"Phase {phase} loaded from {path} ({n} events).")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def _save_sequence(self, phase: int):
        if not self.phase_events[phase]:
            messagebox.showwarning("No Sequence", f"Phase {phase} has no events to save.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                             filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            self.recorder.events = self.phase_events[phase]
            self.recorder.save(path)
            self._log(f"Phase {phase} saved to {path}.")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    # ------------------------------------------------------------------ #
    #  BOT ENTRY POINT
    # ------------------------------------------------------------------ #

    def _start_bot(self):
        if not self._validate():
            return

        self.bot_running       = True
        self.attempt_count     = 0
        self._stop_after_batch = False
        self._game_hung        = False
        # Reset all counters — "All Time" tracks the current run only
        self._ov_hits_33     = 0
        self._ov_hits_23     = 0
        self._ov_duds        = 0
        self._ov_at_33       = 0
        self._ov_at_23       = 0
        self._ov_at_duds     = 0
        self._best_33_iter   = None
        self._best_hits_iter = None
        self._reset_iter_requested = False
        # Tell the player which exe to watch so inputs are blocked if game loses focus
        self.player.game_exe = os.path.basename(self.game_exe_var.get().strip())
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        # Store overlay settings — actual overlay is created after confirmation dialog
        self._overlay_exe_frag = os.path.splitext(
            os.path.basename(self.game_exe_var.get().strip()))[0].lower() or "nightreign"

        self._set_status("Running (Batch)…", "green")
        self.bot_thread = threading.Thread(target=self._batch_loop, daemon=True)
        self.bot_thread.start()
        threading.Thread(target=self._game_watchdog, daemon=True,
                         name="game-watchdog").start()

    def _request_stop_after_batch(self):
        """Graceful stop: let the current batch finish, then exit cleanly."""
        self._stop_after_batch = True
        self._log("Stop requested — will finish current batch then exit.")
        self._set_status("Stopping after this batch…", "orange")
        if self._overlay:
            self._overlay.set_stop_pending(True)

    def _stop_bot(self):
        self._stop_after_batch = False
        self.bot_running = False
        self.player.stop()
        # Unblock backup ready wait if it's stuck
        self._ready_event.set()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self._set_status("Stopped", "gray")
        self._log("Bot stopped by user.")
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None

    # ------------------------------------------------------------------ #
    #  BATCH MODE LOOP
    # ------------------------------------------------------------------ #

    def _batch_loop(self):
        save_path = self.save_path_var.get()
        backup_path = os.path.join(
            self.backup_path_var.get(), os.path.basename(save_path)
        )
        criteria = self.relic_builder.get_criteria_dict()
        criteria_summary = self.relic_builder.get_criteria_summary()
        criteria["allowed_colors"] = self._get_allowed_colors()
        region = self._get_region()
        delay = float(self.batch_delay_var.get())
        limit_type = self.batch_limit_type.get()
        limit_value = float(self.batch_limit_var.get())
        mode_desc = "loops" if limit_type == "loops" else "hours"
        base_output = self.batch_output_var.get()
        load_wait = float(self.game_load_wait_var.get())
        # Minimum passive count for a result to be labelled a "HIT" tier.
        # If the user's criteria requires all 3 passives, 2/3 near-misses are
        # not counted as hits and won't get a HIT folder or ★★ log message.
        hit_min = self.relic_builder.get_min_hit_threshold()

        # The run folder is created lazily — only when the first iteration actually runs.
        # This prevents empty batch_run_* folders when the bot is stopped before any iteration.
        run_stamp = time.strftime("%Y-%m-%d_%H%M%S")
        batch_id  = time.strftime("%Y%m%d_%H%M%S")
        self._current_batch_id = batch_id
        self._ov_overflow_hits = 0
        run_dir = os.path.join(base_output, f"batch_run_{run_stamp}")
        live_log_path = os.path.join(run_dir, "live_log.txt")
        batch_log_path = os.path.join(run_dir, "run_log.txt")
        _run_dir_created = [False]

        def _ensure_run_dir():
            if not _run_dir_created[0]:
                os.makedirs(run_dir, exist_ok=True)
                _run_dir_created[0] = True
                # run_log.txt: full copy of everything logged to the UI
                try:
                    with open(batch_log_path, "w", encoding="utf-8") as _f:
                        _f.write(f"Run Log — {run_stamp}\n")
                        _f.write("=" * 60 + "\n")
                    self._batch_log_path = batch_log_path
                except Exception:
                    pass
                # live_log.txt: per-relic analysis summary only
                try:
                    with open(live_log_path, "w", encoding="utf-8") as _f:
                        _f.write(f"Live Analysis Log — {run_stamp}\n")
                        _f.write("=" * 60 + "\n")
                except Exception:
                    pass
                self._log(f"Batch output folder: {run_dir}")

        try:
            save_manager.backup(save_path, backup_path)
            self._log("Save file backed up.")
        except Exception as e:
            self._log(f"ERROR backing up save: {e}")
            self.after(0, self._reset_controls)
            return

        self._ready_event.clear()
        self.after(0, self._ask_backup_ready)
        self._ready_event.wait()
        if not self.bot_running:
            self.after(0, self._reset_controls)
            return

        results = []
        start_time = time.time()
        iteration = 0
        save_filename = os.path.basename(save_path)
        _prev_save_dir = None  # iteration folder waiting for its save copy

        # ── Async mode setup ──────────────────────────────────────────── #
        _async_mode = self._async_enabled_var.get()
        _async_relic_q: queue.PriorityQueue | None = None
        _async_dir_map:    dict = {}   # iteration → final dir (after any rename)
        _async_iter_state: dict = {}   # iteration → per-iter completion tracking
        _async_state_lock = threading.Lock()
        _async_shutdown_done = [False]
        _ASYNC_TASK_TIMEOUT  = 90      # seconds per relic before requeueing

        if _async_mode:
            _async_relic_q = queue.PriorityQueue()
            _async_workers = (max(1, min(8, self._parallel_workers_var.get()))
                              if self._parallel_enabled_var.get() else 1)
            self._log(
                f"Async Analysis enabled — {_async_workers} worker(s); "
                "relics queued by priority across all iterations."
            )

            def _relic_worker():  # noqa: E306
                while True:
                    _prio, _task = _async_relic_q.get()
                    if _task is None:   # sentinel
                        _async_relic_q.task_done()
                        break
                    try:
                        _rt = threading.Thread(
                            target=self._analyze_relic_task,
                            args=(_task, _async_iter_state, _async_state_lock,
                                  _async_dir_map, results),
                            daemon=True,
                        )
                        _rt.start()
                        _rt.join(timeout=_ASYNC_TASK_TIMEOUT)
                        if _rt.is_alive():
                            _retries = _task.get("_retries", 0)
                            if _retries < 2:
                                self._log(
                                    f"[Async] Iter {_task['iteration']} relic "
                                    f"{_task['step_i'] + 1} timed out — "
                                    f"requeueing (attempt {_retries + 2}/3)."
                                )
                                _async_relic_q.put(
                                    (_prio, {**_task, "_retries": _retries + 1}))
                            else:
                                self._log(
                                    f"[Async] Iter {_task['iteration']} relic "
                                    f"{_task['step_i'] + 1} timed out permanently."
                                )
                                self._mark_relic_failed(
                                    _task, _async_iter_state, _async_state_lock,
                                    _async_dir_map, results)
                    except Exception as _re:
                        self._log(f"ERROR in async relic worker: {_re}")
                        self._mark_relic_failed(
                            _task, _async_iter_state, _async_state_lock,
                            _async_dir_map, results)
                    finally:
                        _async_relic_q.task_done()

            for _wn in range(_async_workers):
                threading.Thread(target=_relic_worker, daemon=True,
                                 name=f"async-relic-worker-{_wn}").start()

            def _shutdown_async_workers():
                if not _async_shutdown_done[0]:
                    _async_shutdown_done[0] = True
                    for _ in range(_async_workers):
                        _async_relic_q.put(
                            ((float("inf"), float("inf")), None))

            def _async_join_timed():
                """Wait for the async relic queue to drain (1.5-min timeout)."""
                _done = threading.Event()
                def _waiter():
                    _async_relic_q.join()
                    _done.set()
                threading.Thread(target=_waiter, daemon=True).start()
                if not _done.wait(timeout=_ASYNC_TASK_TIMEOUT):
                    self._log(
                        f"WARNING: Async workers did not finish within "
                        f"{_ASYNC_TASK_TIMEOUT}s — proceeding anyway."
                    )

            # ── Overflow workers for previous batch tasks ──────────────── #
            # If the previous batch had leftover tasks when it was stopped, spawn
            # 2 independent workers to finish them without consuming new-batch slots.
            _ovf = self._overflow_handoff
            if _ovf is not None:
                self._overflow_handoff = None
                _ovf_q = queue.PriorityQueue()
                for _oi in _ovf["tasks"]:
                    _ovf_q.put(_oi)
                for _ in range(2):
                    _ovf_q.put(((float("inf"), float("inf")), None))

                def _overflow_worker(
                    _oq=_ovf_q,
                    _ois=_ovf["iter_state"],
                    _ol=_ovf["lock"],
                    _odm=_ovf["dir_map"],
                    _or=_ovf["results"],
                ):
                    while True:
                        _prio, _task = _oq.get()
                        if _task is None:
                            _oq.task_done()
                            break
                        try:
                            _rt = threading.Thread(
                                target=self._analyze_relic_task,
                                args=(_task, _ois, _ol, _odm, _or),
                                daemon=True,
                            )
                            _rt.start()
                            _rt.join(timeout=_ASYNC_TASK_TIMEOUT)
                            if _rt.is_alive():
                                _retries = _task.get("_retries", 0)
                                if _retries < 2:
                                    _oq.put((_prio, {**_task, "_retries": _retries + 1}))
                                else:
                                    self._mark_relic_failed(
                                        _task, _ois, _ol, _odm, _or)
                        except Exception:
                            self._mark_relic_failed(_task, _ois, _ol, _odm, _or)
                        finally:
                            _oq.task_done()

                for _wn in range(2):
                    threading.Thread(
                        target=_overflow_worker, daemon=True,
                        name=f"overflow-worker-{_wn}",
                    ).start()
                self._log("Overflow: 2 workers started for previous batch leftovers.")

        _MAX_RESTARTS       = 3    # abort after this many consecutive hung-game restarts
        _iter_restart_count = 0    # restarts for the current iteration (reset on new iter)
        _is_restart         = False  # True when retrying the same iteration after a hang

        while self.bot_running:
            # Check stopping condition
            if limit_type == "loops" and iteration >= int(limit_value):
                break
            if limit_type == "hours" and (time.time() - start_time) / 3600 >= limit_value:
                break

            if not _is_restart:
                iteration += 1
                _iter_restart_count = 0   # fresh iteration resets the hung counter
                self.attempt_count = iteration
                self.after(0, lambda n=iteration: self.attempt_var.set(f"Attempts: {n}"))
            else:
                _is_restart = False       # clear flag; counter already incremented

            # Overlay: batch progress
            if self._overlay:
                if limit_type == "loops":
                    _bs = f"Batch {iteration} / {int(limit_value)}"
                else:
                    _eh = (time.time() - start_time) / 3600
                    _bs = f"{_eh:.1f}h / {limit_value:.1f}h"
                ov = self._overlay
                self.after(0, lambda s=_bs: ov.update(
                    batch=s, relic_num="—", analysing="—",
                ) if ov._win else None)

            if not self.bot_running:
                break

            # Create the run folder on first use
            _ensure_run_dir()

            try:
                with open(live_log_path, "a", encoding="utf-8") as _f:
                    _f.write(f"\n--- Iteration {iteration} ---\n")
            except Exception:
                pass

            folder_name = f"{iteration:03d}"
            iter_dir = os.path.join(run_dir, folder_name)
            os.makedirs(iter_dir, exist_ok=True)

            if _iter_restart_count > 0:
                self._log(
                    f"--- Iteration {iteration} "
                    f"(restart {_iter_restart_count}/{_MAX_RESTARTS}) ---"
                )
            else:
                self._log(f"--- Iteration {iteration} ---")

            self._game_hung = False   # clear watchdog flag at the start of each attempt
            self._set_status(f"Iteration {iteration}: closing game…", "orange")
            if not self._close_game():
                self._log("ERROR: Could not close game.")
                self.after(0, self._reset_controls)
                return
            # Game is now closed — safe to copy the rolled save from the
            # previous iteration (file is no longer locked by the game).
            if _prev_save_dir is not None:
                # In async mode, the worker may have renamed the dir — use final path.
                _copy_dir = (_async_dir_map.get(iteration - 1, _prev_save_dir)
                             if _async_mode else _prev_save_dir)
                try:
                    shutil.copy2(save_path, os.path.join(_copy_dir, save_filename))
                except Exception as e:
                    self._log(f"WARNING: could not copy save to {_copy_dir}: {e}")
                _prev_save_dir = None
            try:
                save_manager.restore(save_path, backup_path)
                self._log("Save restored.")
            except Exception as e:
                self._log(f"ERROR restoring save: {e}")
                self.after(0, self._reset_controls)
                return
            self._set_status(f"Iteration {iteration}: launching game…", "orange")
            self._launch_game()
            confirm_key = self.confirm_key_var.get().strip() or "e"
            exe_name    = os.path.basename(self.game_exe_var.get().strip())

            # Wait for the game window to appear before starting the load timer.
            # Inputs sent before focus would go to the desktop, not the game.
            self._log("Waiting for game window to appear…")
            self._set_status(f"Iteration {iteration}: waiting for game window…", "orange")
            _game_focused = False
            while self.bot_running and not _game_focused:
                _game_focused = self._focus_game_window(exe_name, timeout=1.0)
                if not _game_focused:
                    time.sleep(0.5)
            if not self.bot_running:
                self.after(0, self._reset_controls)
                return

            # Game window confirmed — start load wait timer now.
            self._log(f"Game window focused. Waiting {load_wait}s for game to load (spamming confirm key)…")
            self._set_status(f"Iteration {iteration}: loading game…", "orange")
            for i in range(int(load_wait * 2)):
                if not self.bot_running:
                    self.after(0, self._reset_controls)
                    return
                if i % 10 == 0 and exe_name:
                    _game_focused = self._focus_game_window(exe_name, timeout=1.0)
                    if _game_focused:
                        self.player.tap("f")
                if _game_focused:
                    self.player.tap(confirm_key)
                time.sleep(0.45)

            # ── Phase -0.5: Confirm in-game state before Phase 0 ────────── #
            # Verifies the game has loaded past the title screen into the game
            # world using ESC → Equipment menu detection. Prevents Phase 0 from
            # firing on the wrong screen.
            self._set_status(f"Iteration {iteration}: confirming in-game state…", "orange")
            if not self._confirm_in_game(region, exe_name):
                _iter_restart_count += 1
                self._log(
                    f"[Phase -0.5] In-game confirmation failed "
                    f"(restart {_iter_restart_count}/{_MAX_RESTARTS}).")
                if _iter_restart_count >= _MAX_RESTARTS:
                    self._log(
                        f"Could not confirm in-game state after {_MAX_RESTARTS} attempts "
                        f"on iteration {iteration} — aborting.")
                    if _async_mode and _async_relic_q is not None:
                        _shutdown_async_workers()
                        _async_join_timed()
                    self.after(0, self._reset_controls)
                    return
                try:
                    shutil.rmtree(iter_dir, ignore_errors=True)
                except Exception:
                    pass
                _prev_save_dir = None
                _is_restart = True
                continue

            label = f"Iteration {iteration}"

            # ── Async mode: capture only, then push task to background worker ── #
            if _async_mode:
                captures = self._run_iteration_phases(
                    label, criteria, region, delay,
                    iter_dir=iter_dir, hit_min=hit_min,
                    live_log_path=live_log_path,
                    capture_only=True)

                if captures is None:
                    # Fatal capture error — shut down workers and abort
                    _shutdown_async_workers()
                    _async_join_timed()
                    self.after(0, self._reset_controls)
                    return

                if not self.bot_running:
                    break

                # User-requested soft nuke of this iteration
                if self._reset_iter_requested:
                    self._reset_iter_requested = False
                    self._log(f"[Reset] Discarding iteration {iteration} and restarting.")
                    self._close_game()
                    _rs = self.save_path_var.get()
                    _rb = os.path.join(self.backup_path_var.get(), os.path.basename(_rs))
                    try:
                        save_manager.restore(_rs, _rb)
                    except Exception as _rse:
                        self._log(f"  WARNING: save restore failed: {_rse}")
                    try:
                        shutil.rmtree(iter_dir, ignore_errors=True)
                    except Exception:
                        pass
                    _prev_save_dir = None
                    _iter_restart_count = 0
                    _is_restart = True
                    continue

                # Watchdog detected a hung game during this iteration
                if self._game_hung:
                    _iter_restart_count += 1
                    self._log(
                        f"[Watchdog] Game hung during iteration {iteration} — "
                        f"discarding (restart {_iter_restart_count}/{_MAX_RESTARTS})."
                    )
                    if _iter_restart_count >= _MAX_RESTARTS:
                        self._log(
                            f"Game hung {_MAX_RESTARTS} times on iteration {iteration} "
                            "— aborting."
                        )
                        _shutdown_async_workers()
                        _async_join_timed()
                        self.after(0, self._reset_controls)
                        return
                    try:
                        shutil.rmtree(iter_dir, ignore_errors=True)
                    except Exception:
                        pass
                    _prev_save_dir = None
                    _is_restart = True
                    continue

                # Register iteration completion state, then push individual relic tasks
                with _async_state_lock:
                    if len(captures) == 0:
                        _async_dir_map[iteration] = iter_dir
                    else:
                        _async_iter_state[iteration] = {
                            "total":          len(captures),
                            "done":           0,
                            "results":        [],
                            "iter_dir":       iter_dir,
                            "hit_min":        hit_min,
                            "live_log_path":  live_log_path,
                            "run_dir":        run_dir,
                            "criteria_summary": criteria_summary,
                            "mode_desc":      mode_desc,
                            "limit_value":    limit_value,
                            "save_filename":  save_filename,
                            "batch_id":       batch_id,
                        }
                for _si, _img, _pp in captures:
                    _async_relic_q.put(((iteration, _si), {
                        "iteration":      iteration,
                        "step_i":         _si,
                        "img_bytes":      _img,
                        "pending_path":   _pp,
                        "iter_dir":       iter_dir,
                        "criteria":       criteria,
                        "hit_min":        hit_min,
                        "live_log_path":  live_log_path,
                        "run_dir":        run_dir,
                        "criteria_summary": criteria_summary,
                        "mode_desc":      mode_desc,
                        "limit_value":    limit_value,
                        "save_filename":  save_filename,
                        "batch_id":       batch_id,
                        "_run_log_path":  batch_log_path,
                        "_retries":       0,
                    }))

                _prev_save_dir = iter_dir

                if self._stop_after_batch:
                    self._log("Batch capture done — stopping as requested "
                              "(analysis continuing in background).")
                    break

                continue   # skip normal post-processing

            # ── Normal mode: run phases + post-process inline ─────────── #
            relic_results = self._run_iteration_phases(
                label, criteria, region, delay,
                iter_dir=iter_dir, hit_min=hit_min,
                live_log_path=live_log_path)

            if relic_results is None:
                # Fatal error inside phases — abort
                self.after(0, self._reset_controls)
                return

            # User-requested soft nuke of this iteration
            if self._reset_iter_requested:
                self._reset_iter_requested = False
                self._log(f"[Reset] Discarding iteration {iteration} and restarting.")
                self._close_game()
                _rs = self.save_path_var.get()
                _rb = os.path.join(self.backup_path_var.get(), os.path.basename(_rs))
                try:
                    save_manager.restore(_rs, _rb)
                except Exception as _rse:
                    self._log(f"  WARNING: save restore failed: {_rse}")
                try:
                    shutil.rmtree(iter_dir, ignore_errors=True)
                except Exception:
                    pass
                _prev_save_dir = None
                _iter_restart_count = 0
                _is_restart = True
                continue

            # Watchdog detected a hung game during this iteration
            if self._game_hung:
                _iter_restart_count += 1
                self._log(
                    f"[Watchdog] Game hung during iteration {iteration} — "
                    f"discarding (restart {_iter_restart_count}/{_MAX_RESTARTS})."
                )
                if _iter_restart_count >= _MAX_RESTARTS:
                    self._log(
                        f"Game hung {_MAX_RESTARTS} times on iteration {iteration} "
                        "— aborting."
                    )
                    self.after(0, self._reset_controls)
                    return
                try:
                    shutil.rmtree(iter_dir, ignore_errors=True)
                except Exception:
                    pass
                _prev_save_dir = None
                _is_restart = True
                continue

            if not self.bot_running:
                break

            # Merge all relic results for this iteration into one summary result
            blocked_curses = self._get_blocked_curses()
            any_match = any(
                r.get("match") and not self._is_curse_blocked(r, blocked_curses)
                for r in relic_results
            )
            all_relics = [rf for r in relic_results for rf in r.get("relics_found", [])]
            all_near_misses = [nm for r in relic_results for nm in r.get("near_misses", [])]
            matched_result = next(
                (r for r in relic_results
                 if r.get("match") and not self._is_curse_blocked(r, blocked_curses)),
                None
            )
            matched_relic = matched_result.get("matched_relic") if matched_result else None
            matched_passives = matched_result.get("matched_passives", []) if matched_result else []
            matched_curses = matched_result.get("matched_relic_curses", []) if matched_result else []
            reason = "; ".join(r.get("reason", "") for r in relic_results if r.get("reason"))

            combined = {
                "match": any_match,
                "matched_relic": matched_relic,
                "matched_passives": matched_passives,
                "matched_relic_curses": matched_curses,
                "near_misses": all_near_misses,
                "relics_found": all_relics,
                "reason": reason,
            }

            # Effective tier: consider full matches AND near-misses with hit_min+ passives.
            # hit_min is 2 normally, but 3 when the user requires ALL passives to match —
            # in that case a 2/3 near-miss is not a HIT and won't get a folder rename.
            num_matched = len(matched_passives)
            if num_matched == 0 and all_near_misses:
                num_matched = max(
                    nm.get("matching_passive_count", len(nm.get("matching_passives", [])))
                    for nm in all_near_misses
                )

            # Screenshots already saved inside _run_iteration_phases as each relic was analyzed.
            screenshots = [rr.get("_screenshot_file", "") for rr in relic_results
                           if rr.get("_screenshot_file")]

            # Counters (hits_33 etc.) were already incremented per-relic
            # inside _run_iteration_phases as each analysis completed.
            # Recompute iteration totals here only for the best-batch scoreboard.
            iter_g3, iter_g2, iter_dud = self._count_relic_tiers(relic_results, hit_min)

            # Update best-batch scoreboard
            iter_total = iter_g3 + iter_g2
            if iter_g3 > 0:
                if self._best_33_iter is None or iter_g3 > self._best_33_iter["count"]:
                    self._best_33_iter = {"iteration": iteration, "count": iter_g3}
            if iter_total > 0:
                if self._best_hits_iter is None or iter_total > self._best_hits_iter["count"]:
                    self._best_hits_iter = {"iteration": iteration, "count": iter_total}

            # Push all stats to overlay
            if self._overlay:
                def _fmt_best(info, suffix):
                    if info is None:
                        return "N/A"
                    return f"Batch #{info['iteration']:03d}  —  {info['count']} {suffix}"

                ov = self._overlay
                h33, h23, dds = self._ov_hits_33, self._ov_hits_23, self._ov_duds
                at33, at23, atd = self._ov_at_33, self._ov_at_23, self._ov_at_duds
                b33  = _fmt_best(self._best_33_iter,   "★★★")
                bhit = _fmt_best(self._best_hits_iter, "hits")
                self.after(0, lambda: ov.update(
                    hits_33=h33, hits_23=h23, duds=dds,
                    at_33=at33, at_23=at23, at_duds=atd,
                    best_33=b33, best_hits=bhit,
                ) if ov._win else None)

            # Persist stats after every iteration
            self._save_stats()

            if num_matched >= 3:
                self._log(f"★★★ GOD ROLL — Iteration {iteration}: {matched_relic}")
            elif num_matched >= hit_min:
                hit_name = matched_relic or (
                    max(all_near_misses,
                        key=lambda nm: nm.get("matching_passive_count", 0),
                        default={}).get("relic_name", "Unknown")
                )
                self._log(f"★★ HIT — Iteration {iteration}: {hit_name}")

            _iter_total_hits = iter_g3 + iter_g2
            if _iter_total_hits > 0:
                self._log(
                    f"  Hits this iteration: {_iter_total_hits} "
                    f"({iter_g3}×3/3, {iter_g2}×2/3)"
                )

            # Write per-iteration info.txt (use combined summary)
            try:
                write_iter_info(iter_dir, iteration, relic_results, hit_min)
            except Exception as e:
                self._log(f"WARNING: could not write info.txt: {e}")

            # Rename folder based on effective tier
            if num_matched >= 3:
                tier_name = f"GOD ROLL {iteration:03d}"
            elif num_matched >= hit_min:
                tier_name = f"HIT {iteration:03d}"
            else:
                tier_name = None

            if tier_name:
                tier_dir = os.path.join(run_dir, tier_name)
                try:
                    os.rename(iter_dir, tier_dir)
                    iter_dir = tier_dir
                    folder_name = tier_name
                    self._log(f"Folder renamed to: {tier_name}")
                except Exception as e:
                    self._log(f"WARNING: could not rename folder: {e}")

            # Deferred save copy — set AFTER any rename so the path is always valid
            _prev_save_dir = iter_dir

            results.append({
                "iteration": iteration,
                "folder": folder_name,
                "match": any_match,
                "matched_relic": matched_relic,
                "matched_passives": matched_passives,
                "near_misses": all_near_misses,
                "reason": reason,
                "relics_found": all_relics,
                "screenshots": screenshots,
                "save_copy": save_filename,
                "hits_33": iter_g3,
                "hits_23": iter_g2,
            })

            # Write README after every iteration so a cancelled run is never lost
            try:
                generate_readme(run_dir, criteria_summary, mode_desc, limit_value, results, hit_min)
            except Exception:
                pass
            try:
                generate_priority_summary(run_dir, results)
            except Exception:
                pass

            # Graceful stop — user requested stop after this batch
            if self._stop_after_batch:
                self._log("Batch finished — stopping as requested.")
                break

        # Copy the last iteration's save (game is still running after final analysis).
        if _prev_save_dir is not None:
            self._set_status("Closing game to save final iteration…", "orange")
            self._close_game()
            _final_copy_dir = (_async_dir_map.get(iteration, _prev_save_dir)
                               if _async_mode else _prev_save_dir)
            try:
                shutil.copy2(save_path, os.path.join(_final_copy_dir, save_filename))
            except Exception as e:
                self._log(f"WARNING: could not copy final save: {e}")
            _prev_save_dir = None

        # ── Grace period: wait for async analysis to finish ───────────── #
        if _async_mode and _async_relic_q is not None:
            self._set_status("Waiting for background analysis to finish…", "orange")
            self._log("Grace period: waiting for async analysis to complete…")
            _shutdown_async_workers()
            _async_join_timed()
            self._log("Async analysis complete.")
            # Drain any tasks still in the queue (e.g. if grace period timed out)
            # and store them for overflow workers in the next batch.
            _remaining_overflow = []
            while True:
                try:
                    _oprio, _otask = _async_relic_q.get_nowait()
                    _async_relic_q.task_done()
                    if _otask is not None:
                        _remaining_overflow.append((_oprio, _otask))
                except queue.Empty:
                    break
            if _remaining_overflow:
                self._overflow_handoff = {
                    "tasks":      _remaining_overflow,
                    "iter_state": _async_iter_state,
                    "lock":       _async_state_lock,
                    "dir_map":    _async_dir_map,
                    "results":    results,
                }
                self._log(
                    f"  {len(_remaining_overflow)} task(s) handed off to next batch overflow workers."
                )

        # Batch finished – generate README and PRIORITY.txt
        if results and _run_dir_created[0]:
            try:
                generate_readme(run_dir, criteria_summary, mode_desc, limit_value, results, hit_min)
                self._log(f"README.txt written to {run_dir}")
            except Exception as e:
                self._log(f"WARNING: could not write README: {e}")
            try:
                generate_priority_summary(run_dir, results)
                self._log(f"PRIORITY.txt written to {run_dir}")
            except Exception as e:
                self._log(f"WARNING: could not write PRIORITY.txt: {e}")

        match_count  = sum(1 for r in results if r["match"])
        total_hits33 = sum(r.get("hits_33", 0) for r in results)
        total_hits23 = sum(r.get("hits_23", 0) for r in results)
        total_hits   = total_hits33 + total_hits23
        self._log(
            f"Batch complete. {len(results)} iterations run, {match_count} match(es) found."
        )
        if total_hits > 0:
            self._log(
                f"Total hits across all iterations: {total_hits} "
                f"({total_hits33}×3/3, {total_hits23}×2/3)"
            )
        self._set_status("Batch complete.", "gray")

        if results and _run_dir_created[0]:
            self.after(0, self._show_batch_summary, run_dir, len(results), match_count)
        else:
            self.after(0, self._reset_controls)

    def _show_batch_summary(self, run_dir: str, total: int, matches: int):
        self._reset_controls()
        messagebox.showinfo(
            "Batch Complete",
            f"Batch run finished!\n\n"
            f"Total iterations : {total}\n"
            f"Matches found    : {matches}\n\n"
            f"Results saved to:\n{run_dir}\n\n"
            "Review README.txt for the full breakdown.",
        )

    # ------------------------------------------------------------------ #
    #  BUY INPUT DIAGNOSTIC
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  ASYNC PER-RELIC ANALYSIS
    # ------------------------------------------------------------------ #

    def _analyze_relic_task(self, task: dict, iter_state: dict,
                            lock: threading.Lock, dir_map: dict,
                            results: list) -> None:
        """OCR-analyze one captured relic (called from async relic worker thread)."""
        iteration     = task["iteration"]
        step_i        = task["step_i"]
        img_bytes     = task["img_bytes"]
        pending_path  = task["pending_path"]
        iter_dir      = task["iter_dir"]
        criteria      = task["criteria"]
        hit_min       = task["hit_min"]
        live_log_path = task["live_log_path"]
        is_current_batch = task.get("batch_id") == self._current_batch_id

        try:
            result = relic_analyzer.analyze(img_bytes, criteria)
        except Exception as exc:
            if is_current_batch:
                self._log(f"  [Async iter {iteration}] ERROR relic {step_i + 1}: {exc}")
            self._mark_relic_failed(task, iter_state, lock, dir_map, results)
            return

        if pending_path and os.path.exists(pending_path):
            try:
                os.remove(pending_path)
            except Exception:
                pass

        # Route per-relic log output: current batch → UI panel; old batch → its own run_log
        if is_current_batch:
            self._log(f"  [Async iter {iteration}] Relic {step_i + 1}:")
            self._log_result(result)
            time.sleep(0.05)
        else:
            _old_run_log = task.get("_run_log_path", "")
            if _old_run_log:
                try:
                    relics = result.get("relics_found", [])
                    r0 = relics[0] if relics else {}
                    rname = r0.get("name", "Unknown") if isinstance(r0, dict) else str(r0)
                    passives_found = r0.get("passives", []) if isinstance(r0, dict) else []
                    status = "MATCH" if result.get("match") else "no match"
                    ts = time.strftime("%H:%M:%S")
                    with open(_old_run_log, "a", encoding="utf-8") as _f:
                        _f.write(
                            f"[{ts}]   [Overflow iter {iteration}] Relic {step_i + 1}: "
                            f"[{status}] {rname}  | {', '.join(passives_found) or '—'}\n"
                        )
                except Exception:
                    pass

        saved_fname = ""
        if iter_dir and img_bytes:
            is_match = result.get("match", False)
            best_nm = max(
                (nm.get("matching_passive_count",
                         len(nm.get("matching_passives", [])))
                 for nm in result.get("near_misses", [])),
                default=0,
            )
            tag = "MATCH" if is_match else ("HIT" if best_nm >= hit_min else "")
            if tag:
                saved_fname = f"relic_{step_i + 1:02d}_{tag}.jpg"
                try:
                    with open(os.path.join(iter_dir, saved_fname), "wb") as _f:
                        _f.write(img_bytes)
                    if is_current_batch:
                        self._log(f"  Screenshot saved: {saved_fname}")
                except Exception as _e:
                    if is_current_batch:
                        self._log(f"WARNING: could not save screenshot: {_e}")
                    saved_fname = ""

        result["_image_bytes"]    = None
        result["_screenshot_file"] = saved_fname

        # Always write per-relic result to the live_log (scoped to the task's own batch)
        if live_log_path:
            try:
                relics = result.get("relics_found", [])
                r0 = relics[0] if relics else {}
                rname = r0.get("name", "Unknown") if isinstance(r0, dict) else str(r0)
                passives_found = r0.get("passives", []) if isinstance(r0, dict) else []
                status = "MATCH" if result.get("match") else "no match"
                line = (f"  Relic {step_i + 1:02d}: [{status}] {rname}"
                        f"  | {', '.join(passives_found) or '—'}")
                if saved_fname:
                    line += f"  → {saved_fname}"
                with open(live_log_path, "a", encoding="utf-8") as _f:
                    _f.write(line + "\n")
            except Exception:
                pass

        # Only update current-batch overlay counters
        if is_current_batch:
            r_g3, r_g2, r_dud = self._count_relic_tiers([result], hit_min)
            self._ov_at_33   += r_g3
            self._ov_at_23   += r_g2
            self._ov_at_duds += r_dud
            if self._overlay:
                ov = self._overlay
                at33, at23, atd = self._ov_at_33, self._ov_at_23, self._ov_at_duds
                self.after(0, lambda at33=at33, at23=at23, atd=atd:
                           ov.update(at_33=at33, at_23=at23, at_duds=atd)
                           if ov._win else None)

        with lock:
            istate = iter_state.get(iteration)
            if istate is None:
                return
            istate["results"].append((step_i, result))
            istate["done"] += 1
            is_complete = istate["done"] >= istate["total"]

        if is_complete:
            self._finalize_async_iter_state(
                iteration, iter_state, lock, dir_map, results)

    def _mark_relic_failed(self, task: dict, iter_state: dict,
                           lock: threading.Lock, dir_map: dict,
                           results: list) -> None:
        """Count a permanently failed/timed-out relic as done; keep its screenshot."""
        iteration    = task["iteration"]
        step_i       = task["step_i"]
        pending_path = task["pending_path"]
        iter_dir     = task["iter_dir"]

        if pending_path and os.path.exists(pending_path):
            try:
                dest = os.path.join(
                    iter_dir,
                    f"relic_{step_i + 1:02d}_could_not_analyze.jpg")
                os.rename(pending_path, dest)
                self._log(
                    f"  [Async iter {iteration}] Relic {step_i + 1} kept as "
                    f"relic_{step_i + 1:02d}_could_not_analyze.jpg"
                )
            except Exception:
                pass

        with lock:
            istate = iter_state.get(iteration)
            if istate is None:
                return
            istate["done"] += 1
            is_complete = istate["done"] >= istate["total"]

        if is_complete:
            self._finalize_async_iter_state(
                iteration, iter_state, lock, dir_map, results)

    def _finalize_async_iter_state(self, iteration: int, iter_state: dict,
                                   lock: threading.Lock, dir_map: dict,
                                   results: list) -> None:
        """Post-process a completed async iteration (all relics analyzed/failed)."""
        with lock:
            istate = iter_state.get(iteration)
            if istate is None:
                return
            relic_results    = [r for _, r in sorted(istate["results"],
                                                     key=lambda x: x[0])]
            iter_dir         = istate["iter_dir"]
            hit_min          = istate["hit_min"]
            run_dir          = istate["run_dir"]
            criteria_summary = istate["criteria_summary"]
            mode_desc        = istate["mode_desc"]
            limit_value      = istate["limit_value"]
            save_filename    = istate["save_filename"]
            is_current_batch = istate.get("batch_id") == self._current_batch_id

        blocked_curses = self._get_blocked_curses()
        any_match = any(
            r.get("match") and not self._is_curse_blocked(r, blocked_curses)
            for r in relic_results
        )
        all_relics = [rf for r in relic_results
                      for rf in r.get("relics_found", [])]
        all_near_misses = [nm for r in relic_results
                           for nm in r.get("near_misses", [])]
        matched_result = next(
            (r for r in relic_results
             if r.get("match") and not self._is_curse_blocked(r, blocked_curses)),
            None
        )
        matched_relic    = matched_result.get("matched_relic") if matched_result else None
        matched_passives = (matched_result.get("matched_passives", [])
                            if matched_result else [])
        matched_curses   = (matched_result.get("matched_relic_curses", [])
                            if matched_result else [])
        reason      = "; ".join(r.get("reason", "") for r in relic_results
                                if r.get("reason"))
        screenshots = [rr.get("_screenshot_file", "") for rr in relic_results
                       if rr.get("_screenshot_file")]

        iter_g3, iter_g2, _ = self._count_relic_tiers(relic_results, hit_min)
        num_matched = len(matched_passives)
        if num_matched == 0 and all_near_misses:
            num_matched = max(
                nm.get("matching_passive_count",
                        len(nm.get("matching_passives", [])))
                for nm in all_near_misses
            )

        # Best-batch scoreboard and overlay — only update for current batch
        if is_current_batch:
            iter_total = iter_g3 + iter_g2
            if iter_g3 > 0:
                if self._best_33_iter is None or iter_g3 > self._best_33_iter["count"]:
                    self._best_33_iter = {"iteration": iteration, "count": iter_g3}
            if iter_total > 0:
                if (self._best_hits_iter is None
                        or iter_total > self._best_hits_iter["count"]):
                    self._best_hits_iter = {"iteration": iteration, "count": iter_total}

            if self._overlay:
                def _fmt_best(info, suffix):
                    if info is None:
                        return "N/A"
                    return f"Batch #{info['iteration']:03d}  —  {info['count']} {suffix}"
                ov   = self._overlay
                at33, at23, atd = self._ov_at_33, self._ov_at_23, self._ov_at_duds
                b33  = _fmt_best(self._best_33_iter,   "★★★")
                bhit = _fmt_best(self._best_hits_iter, "hits")
                self.after(0, lambda: ov.update(
                    at_33=at33, at_23=at23, at_duds=atd,
                    best_33=b33, best_hits=bhit,
                ) if ov._win else None)

            self._save_stats()

        # Hit / GOD ROLL log — always shown for current batch; shown for overflow
        # only if a hit was found (exception rule so user never misses a result).
        if num_matched >= 3:
            if is_current_batch:
                self._log(f"★★★ GOD ROLL — Iteration {iteration}: {matched_relic}")
            else:
                self._log(
                    f"[Overflow] ★★★ GOD ROLL — Prev batch Iter {iteration}: {matched_relic}"
                )
                self._ov_overflow_hits += 1
                if self._overlay:
                    _n = self._ov_overflow_hits
                    ov = self._overlay
                    self.after(0, lambda _n=_n: ov.set_overflow_hits(_n) if ov._win else None)
        elif num_matched >= hit_min:
            hit_name = matched_relic or (
                max(all_near_misses,
                    key=lambda nm: nm.get("matching_passive_count", 0),
                    default={}).get("relic_name", "Unknown")
            )
            if is_current_batch:
                self._log(f"★★ HIT — Iteration {iteration}: {hit_name}")
            else:
                self._log(
                    f"[Overflow] ★★ HIT — Prev batch Iter {iteration}: {hit_name}"
                )
                self._ov_overflow_hits += 1
                if self._overlay:
                    _n = self._ov_overflow_hits
                    ov = self._overlay
                    self.after(0, lambda _n=_n: ov.set_overflow_hits(_n) if ov._win else None)
        if is_current_batch and (iter_g3 + iter_g2) > 0:
            self._log(
                f"  Hits this iteration: {iter_g3 + iter_g2} "
                f"({iter_g3}×3/3, {iter_g2}×2/3)"
            )

        try:
            write_iter_info(iter_dir, iteration, relic_results, hit_min)
        except Exception as e:
            if is_current_batch:
                self._log(f"WARNING: could not write info.txt: {e}")

        folder_name = f"{iteration:03d}"
        tier_name   = (f"GOD ROLL {iteration:03d}" if num_matched >= 3
                       else f"HIT {iteration:03d}" if num_matched >= hit_min
                       else None)
        final_iter_dir = iter_dir
        if tier_name:
            tier_dir = os.path.join(run_dir, tier_name)
            try:
                os.rename(iter_dir, tier_dir)
                final_iter_dir = tier_dir
                folder_name    = tier_name
                if is_current_batch:
                    self._log(f"Folder renamed to: {tier_name}")
            except OSError as e:
                if is_current_batch:
                    self._log(f"WARNING: could not rename folder: {e}")

        with lock:
            dir_map[iteration] = final_iter_dir

        results.append({
            "iteration":       iteration,
            "folder":          folder_name,
            "match":           any_match,
            "matched_relic":   matched_relic,
            "matched_passives": matched_passives,
            "near_misses":     all_near_misses,
            "reason":          reason,
            "relics_found":    all_relics,
            "screenshots":     screenshots,
            "save_copy":       save_filename,
            "hits_33":         iter_g3,
            "hits_23":         iter_g2,
        })

        try:
            generate_readme(run_dir, criteria_summary, mode_desc,
                            limit_value, results, hit_min)
        except Exception:
            pass
        try:
            generate_priority_summary(run_dir, results)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  PHASE EXECUTION ENGINE
    # ------------------------------------------------------------------ #

    def _run_iteration_phases(self, label: str, criteria: dict,
                              region, delay: float,
                              iter_dir: str = "", hit_min: int = 2,
                              live_log_path: str = "",
                              capture_only: bool = False) -> list | None:
        """
        Run all configured sequence phases for one bot iteration.

        Phases:
          0 – Setup            : plays once
          1 – Buy Loop         : repeats until Phase 1 stop text detected (internal failsafe: 500)
          2 – Relic Rites Nav  : plays once — opens the Relic Rites sell screen
          3 – Navigate to Sell : automatic — OCR detects active tab, presses F2 N times;
                                 falls back to F2 loop if verification fails (failsafe: 15)
          4 – Review Step      : repeats; analyzes each relic (internal failsafe: 200)

        Returns a list of result dicts (one per relic analyzed).
        Each dict has the usual analyze() keys plus a private '_image_bytes' entry.
        Returns None on fatal error.
        """
        p1_stop   = self.phase_stop_text_vars[1].get().strip()
        _P1_FAILSAFE = 500          # internal only — never shown in UI
        p1_settle = float(self.phase_settle_vars[1].get() or "0")
        _P2_FAILSAFE = 30           # max navigation steps before giving up on sell page
        _P4_FAILSAFE = 200          # internal only — never shown in UI
        p4_settle = float(self.phase_settle_vars[4].get() or "0")
        murk_cost = 1800 if self.relic_type_var.get() == "night" else 600
        _p3_count = None            # set by murk read below; None = use failsafe
        _p0_exe   = os.path.basename(self.game_exe_var.get().strip())
        murk_val  = 0

        relic_results = []

        # Expected Phase 0 input count and exact key sequence (for validation)
        _p0_expected      = sum(1 for e in self.phase_events[0] if e["type"] == "key_press")
        _p0_expected_keys = [e["key"] for e in self.phase_events[0] if e["type"] == "key_press"]
        _P01_MAX_ATTEMPTS = 3   # max Phase 0+1 retries before aborting iteration

        # ── Phase 0 + Murk read + Phase 1 — with retry loop ────────────── #
        # Wrapped in a retry loop: if Phase 0 input count is short (play was
        # interrupted) or a reset is requested, ESC-recover and retry up to
        # _P01_MAX_ATTEMPTS times. Inputs use extra_delay=0.25 s per key to
        # prevent inputs being eaten during game-UI transition animations.
        _p01_success = False
        for _p01_att in range(_P01_MAX_ATTEMPTS):
            if not self.bot_running or self._reset_iter_requested:
                return relic_results

            # ── Phase 0: Setup ─────────────────────────────────────────── #
            if self.phase_events[0]:
                attempt_label = (f" (attempt {_p01_att + 1}/{_P01_MAX_ATTEMPTS})"
                                 if _p01_att > 0 else "")
                self._set_status(f"{label}: setup{attempt_label}…", "green")
                if _p0_exe:
                    self._focus_game_window(_p0_exe, timeout=3.0)
                if not self.bot_running or self._reset_iter_requested:
                    return relic_results
                _p0_sent, _p0_sent_keys = self.player.play(
                    self.phase_events[0], bypass_focus=True, extra_delay=0.25)
                if not self.bot_running or self._reset_iter_requested:
                    return relic_results

                # Validate input count AND exact key sequence.
                _p0_count_ok = (_p0_sent == _p0_expected)
                _p0_seq_ok   = (_p0_sent_keys == _p0_expected_keys)
                if not _p0_count_ok or not _p0_seq_ok:
                    if not _p0_count_ok:
                        _mismatch_desc = f"count {_p0_sent}/{_p0_expected}"
                    else:
                        _mismatch_desc = "sequence mismatch"
                    self._log(
                        f"  Phase 0: input validation failed ({_mismatch_desc}) "
                        f"— ESC recovery and retry.")
                    # Reset tracking vars so stale values can't cause a false positive
                    _p0_sent = 0
                    _p0_sent_keys = []
                    if _p01_att < _P01_MAX_ATTEMPTS - 1:
                        self._esc_to_game_screen(region)
                        continue
                    else:
                        self._log("  Phase 0 failed 3 times — aborting iteration.")
                        self._close_game()
                        try:
                            save_manager.restore(
                                self.save_path_var.get(),
                                os.path.join(self.backup_path_var.get(),
                                             os.path.basename(self.save_path_var.get())))
                        except Exception:
                            pass
                        return None

            # ── Murk read — calculates buy count ───────────────────────── #
            if self.phase_events[1] and self.phase_events[4]:
                self._set_status(f"{label}: waiting for shop screen…", "green")
                time.sleep(1.5)   # inter-phase buffer
                if not self.bot_running or self._reset_iter_requested:
                    return relic_results

                for attempt in range(1, 4):
                    if not self.bot_running or self._reset_iter_requested:
                        return relic_results
                    self._set_status(
                        f"{label}: reading murk (attempt {attempt}/3)…", "green")
                    self.after(0, self._flash_capture)
                    try:
                        murk_img = screen_capture.capture(region)
                        murk_val = relic_analyzer.read_murk(murk_img)
                    except Exception as e:
                        self._log(f"  Murk read attempt {attempt}/3 error: {e}")
                        murk_val = 0

                    if murk_val >= murk_cost:
                        _p3_count = murk_val // murk_cost
                        self._log(
                            f"  Murk: {murk_val:,}  →  {_p3_count} relic(s) to review "
                            f"({murk_cost} murk each).")
                        if self._overlay:
                            ov = self._overlay
                            mv, pc = murk_val, _p3_count
                            self.after(0, lambda: ov.update(
                                murk=f"{mv:,}",
                                est_murk_after=f"~{mv % murk_cost:,}",
                                to_buy=str(pc),
                                bought="0 / " + str(pc),
                                relic_num="—", analysing="—",
                            ) if ov._win else None)
                        break
                    elif murk_val > 0:
                        self._log(
                            f"  Murk read attempt {attempt}/3: {murk_val:,} — below relic cost "
                            f"({murk_cost}), retrying.")
                        murk_val = 0
                    else:
                        self._log(f"  Murk read attempt {attempt}/3 returned 0.")

                if _p3_count is None:
                    self._log(
                        "  WARNING: Murk could not be read — "
                        "falling back to failsafe buy mode (runs until stop condition).")
            else:
                time.sleep(1.5)   # inter-phase buffer even without murk read

            # ── Phase 1: Buy Loop ───────────────────────────────────────── #
            if self.phase_events[1]:
                if _p3_count is not None:
                    buy_count = math.ceil(_p3_count / 10)
                    self._set_status(
                        f"{label}: buying relics ({buy_count} batch(es) of 10)…", "green")
                    self._log(
                        f"  {_p3_count} relic(s) available → {buy_count} buy batch(es).")
                    for buy_i in range(buy_count):
                        if not self.bot_running or self._reset_iter_requested:
                            return relic_results
                        self.player.play_fast(self.phase_events[1], hold=0.05, gap=0.35)
                        if p1_settle > 0:
                            time.sleep(p1_settle)
                        if self._overlay:
                            ov = self._overlay
                            bought_n = min((buy_i + 1) * 10, _p3_count)
                            tot_n = _p3_count
                            self.after(0, lambda b=bought_n, t=tot_n: ov.update(
                                bought=f"{b} / {t}"
                            ) if ov._win else None)
                else:
                    self._set_status(f"{label}: buying relics…", "green")
                    for buy_i in range(_P1_FAILSAFE):
                        if not self.bot_running or self._reset_iter_requested:
                            return relic_results
                        self.player.play_fast(self.phase_events[1], hold=0.05, gap=0.35)
                        if p1_settle > 0:
                            time.sleep(p1_settle)
                        if not self.bot_running or self._reset_iter_requested:
                            return relic_results
                        if p1_stop:
                            self.after(0, self._flash_capture)
                            try:
                                img = screen_capture.capture(region)
                                stopped = relic_analyzer.check_condition(img, p1_stop)
                            except Exception as e:
                                self._log(f"WARNING: buy condition check failed: {e}")
                                stopped = False
                            if stopped:
                                self._log(
                                    f"  Buy stop condition met after {buy_i + 1} purchase(s).")
                                break
                if not self.bot_running or self._reset_iter_requested:
                    return relic_results

            _p01_success = True
            break   # Phase 0+1 completed — proceed to Phase 2

        if not _p01_success and self.bot_running and not self._reset_iter_requested:
            return relic_results   # all retry attempts exhausted without completion

        # ── Phase 2: Relic Rites Nav (Esc → M → down arrows → F) ───────── #
        # On input mismatch: ESC recovery → re-run Phase 0 → skip Phase 1
        # (Phase 1 already succeeded) → re-run Phase 2. Up to 3 attempts total.
        # Phase 1 skip is exclusive to this recovery path — it never skips otherwise.
        _p2_expected      = sum(1 for e in self.phase_events[2] if e["type"] == "key_press")
        _p2_expected_keys = [e["key"] for e in self.phase_events[2] if e["type"] == "key_press"]
        _P2_MAX_ATTEMPTS  = 3
        for _p2_att in range(_P2_MAX_ATTEMPTS):
            if not self.bot_running or self._reset_iter_requested:
                return relic_results

            # On retry: ESC recovery → Phase 0 (skip Phase 1 — already done) → Phase 2
            if _p2_att > 0:
                self._log(f"  Phase 2 retry {_p2_att}/{_P2_MAX_ATTEMPTS - 1}: ESC recovery → Phase 0 → Phase 2…")
                self._esc_to_game_screen(region)
                if not self.bot_running or self._reset_iter_requested:
                    return relic_results
                if self.phase_events[0]:
                    if _p0_exe:
                        self._focus_game_window(_p0_exe, timeout=3.0)
                    if not self.bot_running or self._reset_iter_requested:
                        return relic_results
                    self.player.play(self.phase_events[0], bypass_focus=True, extra_delay=0.25)
                    if not self.bot_running or self._reset_iter_requested:
                        return relic_results
                time.sleep(1.5)   # inter-phase buffer before Phase 2
                if not self.bot_running or self._reset_iter_requested:
                    return relic_results
            else:
                time.sleep(1.5)   # normal inter-phase buffer

            if not self.phase_events[2]:
                break

            attempt_label = (f" (attempt {_p2_att + 1}/{_P2_MAX_ATTEMPTS})" if _p2_att > 0 else "")
            self._set_status(f"{label}: navigating to Relic Rites menu{attempt_label}…", "green")
            _p2_sent, _p2_sent_keys = self.player.play(self.phase_events[2], extra_delay=0.25)
            if not self.bot_running or self._reset_iter_requested:
                return relic_results

            _p2_count_ok = (_p2_sent == _p2_expected)
            _p2_seq_ok   = (_p2_sent_keys == _p2_expected_keys)
            if not _p2_count_ok or not _p2_seq_ok:
                _p2_desc = (f"count {_p2_sent}/{_p2_expected}" if not _p2_count_ok
                            else "sequence mismatch")
                self._log(f"  Phase 2: input validation failed ({_p2_desc}) — recovering and retrying.")
                # Reset tracking vars so stale values can't carry over to next attempt
                _p2_sent = 0
                _p2_sent_keys = []
                continue
            break   # Phase 2 succeeded

        # ── Phase 3: Navigate to Sell (smart tab detection + targeted F2) ─ #
        # Runs whenever Phase 2 (Relic Rites Nav) is configured.
        # 1. Wait for the menu to finish loading, then screenshot and OCR to
        #    identify the active character tab.
        # 2. Press F2 exactly N times (0.20 s gap) to reach Sell.
        # 3. Verify we landed on Sell.  If not, run a fallback F2 loop.
        _P3_FAILSAFE = 15   # max extra F2 presses in the fallback loop
        if self.phase_events[2]:
            # Settle: let the Relic Rites menu finish animating before we
            # screenshot — without this the OCR fires before the UI loads and
            # falls back to the worst-case 10-press guess.
            time.sleep(1.5)
            self._set_status(f"{label}: detecting tab position…", "green")

            # Step 1 — detect current tab
            self.after(0, self._flash_capture)
            try:
                img = screen_capture.capture(region)
                tab_name, f2_count = relic_analyzer.detect_current_tab(img)
            except Exception as e:
                self._log(f"  WARNING: tab detection error: {e}")
                tab_name, f2_count = None, 10

            if tab_name:
                self._log(f"  Tab detected: {tab_name} — pressing F2 × {f2_count}.")
            else:
                self._log(f"  Tab detection inconclusive — pressing F2 × {f2_count} (worst-case).")

            # Step 2 — press F2 the calculated number of times
            self._set_status(f"{label}: navigating to sell page…", "green")
            for _ in range(f2_count):
                if not self.bot_running:
                    return relic_results
                self.player.tap("Key.f2", hold=0.05)
                time.sleep(0.20)

            # Step 3 — verify we landed on Sell
            if not self.bot_running:
                return relic_results
            time.sleep(0.20)
            self.after(0, self._flash_capture)
            try:
                img = screen_capture.capture(region)
                on_sell_page = relic_analyzer.check_condition(img, "sell")
            except Exception as e:
                self._log(f"  WARNING: sell verification error: {e}")
                on_sell_page = False

            if on_sell_page:
                self._log("  Sell page confirmed.")
            else:
                # Fallback — keep pressing F2 and checking until Sell appears
                self._log("  Sell page not confirmed — running F2 fallback loop…")
                sell_reached = False
                for nav_i in range(_P3_FAILSAFE):
                    if not self.bot_running:
                        return relic_results
                    self.player.tap("Key.f2", hold=0.05)
                    time.sleep(0.20)
                    self.after(0, self._flash_capture)
                    try:
                        img = screen_capture.capture(region)
                        on_sell_page = relic_analyzer.check_condition(img, "sell")
                    except Exception:
                        on_sell_page = False
                    if on_sell_page:
                        self._log(f"  Sell page reached after {nav_i + 1} fallback step(s).")
                        sell_reached = True
                        break
                if not sell_reached:
                    self._log("  WARNING: Sell page not detected after fallback — continuing anyway.")

            if not self.bot_running:
                return relic_results

        # ── Phase 4: Review Step Loop (analyze each relic) ─────────── #
        if self.phase_events[4]:
            total = _p3_count if _p3_count is not None else _P4_FAILSAFE

            # ── Capture-only mode (async analysis) ──────────────────── #
            if capture_only:
                captures = []
                for step_i in range(total):
                    if not self.bot_running:
                        return captures
                    if not self.bot_running:
                        return captures
                    if step_i > 0:
                        self.player.play_fast(self.phase_events[4])
                        if p4_settle > 0:
                            time.sleep(p4_settle)
                        if not self.bot_running:
                            return captures
                    self._set_status(
                        f"{label}: capturing relic {step_i + 1}/{total}…", "#006600")
                    if self._overlay:
                        ov = self._overlay
                        si, tot = step_i + 1, total
                        self.after(0, lambda si=si, tot=tot: ov.update(
                            relic_num=f"{si} / {tot}", analysing="queued",
                        ) if ov._win else None)
                    self.after(0, self._flash_capture)
                    try:
                        img = screen_capture.capture(region)
                    except Exception as e:
                        self._log(f"ERROR capturing relic {step_i + 1}: {e}")
                        return None
                    pending_path = ""
                    if iter_dir:
                        pending_fname = f"relic_{step_i + 1:02d}_pending.jpg"
                        pending_path = os.path.join(iter_dir, pending_fname)
                        try:
                            with open(pending_path, "wb") as _f:
                                _f.write(img)
                        except Exception as _e:
                            self._log(f"WARNING: could not save pending screenshot: {_e}")
                            pending_path = ""
                    captures.append((step_i, img, pending_path))
                return captures

            ordered = [None] * total

            # Pipelined capture + analysis: submit each screenshot for analysis
            # immediately after capturing it, so analysis runs in the background
            # while the bot navigates to the next relic.
            # Each worker thread gets its own EasyOCR reader (thread-local) so
            # multiple workers can safely run OCR in parallel.
            _workers = (max(2, min(8, self._parallel_workers_var.get()))
                        if self._parallel_enabled_var.get() else 1)
            if _workers > 1:
                self._log(f"  Brute Force Analysis: {_workers} parallel OCR workers.")

            # Priority queue: workers atomically claim the lowest-numbered
            # available relic — get() is atomic so only one worker ever owns
            # each item; workers always pull the smallest relic index first.
            _task_q       = queue.PriorityQueue()   # (relic_index, img_bytes)
            _done_q       = queue.Queue()            # (relic_index, img_bytes, result, exc)
            _capture_done = threading.Event()

            def _ocr_worker():
                while True:
                    try:
                        _si, _img = _task_q.get(timeout=0.3)
                    except queue.Empty:
                        if _capture_done.is_set() and _task_q.empty():
                            break
                        continue
                    try:
                        _res = relic_analyzer.analyze(_img, criteria)
                        _done_q.put((_si, _img, _res, None))
                    except Exception as _exc:
                        _done_q.put((_si, _img, None, _exc))

            _worker_threads = [
                threading.Thread(target=_ocr_worker, daemon=True,
                                 name=f"ocr-worker-{_n}")
                for _n in range(_workers)
            ]
            for _t in _worker_threads:
                _t.start()

            def _stop_workers():
                _capture_done.set()
                for _t in _worker_threads:
                    _t.join(timeout=1.0)

            _submitted = 0
            for step_i in range(total):
                if not self.bot_running:
                    _stop_workers()
                    return relic_results

                if not self.bot_running:
                    _stop_workers()
                    return relic_results

                if step_i > 0:
                    self.player.play_fast(self.phase_events[4])
                    if p4_settle > 0:
                        time.sleep(p4_settle)
                    if not self.bot_running:
                        _stop_workers()
                        return relic_results

                self._set_status(
                    f"{label}: capturing relic {step_i + 1}/{total}…", "#006600")
                if self._overlay:
                    ov = self._overlay
                    si, tot = step_i + 1, total
                    self.after(0, lambda si=si, tot=tot: ov.update(
                        relic_num=f"{si} / {tot}", analysing=str(si),
                    ) if ov._win else None)
                self.after(0, self._flash_capture)
                try:
                    img = screen_capture.capture(region)
                except Exception as e:
                    self._log(f"ERROR capturing relic {step_i + 1}: {e}")
                    _stop_workers()
                    return None

                # Atomically enqueue — lowest index always dequeued first;
                # exactly one worker will claim this item.
                _task_q.put((step_i, img))
                _submitted += 1

            _capture_done.set()   # no more tasks coming

            if not self.bot_running:
                for _t in _worker_threads:
                    _t.join(timeout=1.0)
                return relic_results

            # Collect results as workers complete them
            _collected = 0
            while _collected < _submitted:
                if not self.bot_running:
                    break
                try:
                    step_i, img, result, exc = _done_q.get(timeout=0.5)
                except queue.Empty:
                    if all(not _t.is_alive() for _t in _worker_threads):
                        break
                    continue

                _collected += 1
                _remaining = _submitted - _collected
                if _remaining > 0:
                    self._set_status(
                        f"{label}: finishing analysis ({_remaining} relic(s))…",
                        "#0066cc")

                if exc is not None:
                    self._log(f"ERROR analyzing relic {step_i + 1}: {exc}")
                    for _t in _worker_threads:
                        _t.join(timeout=1.0)
                    return None

                self._log(f"  [{label}] Relic {step_i + 1}:")
                self._log_result(result)
                time.sleep(0.05)   # let the main thread render the log line

                # Save screenshot if match or near-miss; discard otherwise
                saved_fname = ""
                if iter_dir and img:
                    is_match = result.get("match", False)
                    best_nm = max(
                        (nm.get("matching_passive_count",
                                len(nm.get("matching_passives", [])))
                         for nm in result.get("near_misses", [])),
                        default=0,
                    )
                    tag = "MATCH" if is_match else ("HIT" if best_nm >= hit_min else "")
                    if tag:
                        saved_fname = f"relic_{step_i + 1:02d}_{tag}.jpg"
                        try:
                            with open(os.path.join(iter_dir, saved_fname), "wb") as _f:
                                _f.write(img)
                            self._log(f"  Screenshot saved: {saved_fname}")
                        except Exception as _e:
                            self._log(f"WARNING: could not save screenshot: {_e}")
                            saved_fname = ""

                result["_image_bytes"] = None   # free memory
                result["_screenshot_file"] = saved_fname

                if live_log_path:
                    try:
                        relics = result.get("relics_found", [])
                        r0 = relics[0] if relics else {}
                        rname = r0.get("name", "Unknown") if isinstance(r0, dict) else str(r0)
                        passives_found = r0.get("passives", []) if isinstance(r0, dict) else []
                        status = "MATCH" if result.get("match") else "no match"
                        line = (f"  Relic {step_i + 1:02d}: [{status}] {rname}"
                                f"  | {', '.join(passives_found) or '—'}")
                        if saved_fname:
                            line += f"  → {saved_fname}"
                        with open(live_log_path, "a", encoding="utf-8") as _f:
                            _f.write(line + "\n")
                    except Exception:
                        pass

                ordered[step_i] = result

                # Live-update overlay tier counters after each relic
                r_g3, r_g2, r_dud = self._count_relic_tiers([result], hit_min)
                self._ov_hits_33 += r_g3
                self._ov_at_33   += r_g3
                self._ov_hits_23 += r_g2
                self._ov_at_23   += r_g2
                self._ov_duds    += r_dud
                self._ov_at_duds += r_dud
                if self._overlay:
                    ov = self._overlay
                    h33, h23, dds = self._ov_hits_33, self._ov_hits_23, self._ov_duds
                    at33, at23, atd = self._ov_at_33, self._ov_at_23, self._ov_at_duds
                    self.after(0, lambda h33=h33, h23=h23, dds=dds,
                               at33=at33, at23=at23, atd=atd:
                               ov.update(hits_33=h33, hits_23=h23, duds=dds,
                                         at_33=at33, at_23=at23, at_duds=atd)
                               if ov._win else None)

            for _t in _worker_threads:
                _t.join(timeout=2.0)

            for result in ordered:
                if result is not None:
                    relic_results.append(result)

            return relic_results

        # ── No Phase 4: fall back to single capture + analyze ────────── #
        if capture_only:
            return relic_results   # nothing to capture without Phase 4

        self._set_status(f"{label}: waiting for relic screen…", "green")
        time.sleep(delay)
        if not self.bot_running:
            return relic_results

        self._set_status(f"{label}: capturing…", "#006600")
        self.after(0, self._flash_capture)
        try:
            img = screen_capture.capture(region)
        except Exception as e:
            self._log(f"ERROR during capture: {e}")
            return None

        self._set_status(f"{label}: analyzing…", "#0066cc")
        try:
            result = relic_analyzer.analyze(img, criteria)
        except Exception as e:
            self._log(f"ERROR during analysis: {e}")
            return None

        result["_image_bytes"] = img
        self._log_result(result)
        relic_results.append(result)
        return relic_results

    # ------------------------------------------------------------------ #
    #  OVERLAY STATS PERSISTENCE
    # ------------------------------------------------------------------ #

    def _stats_path(self) -> str:
        output_dir = self.batch_output_var.get().strip() or os.path.join(_REPO_ROOT, "batch_output")
        return os.path.join(output_dir, "overlay_stats.txt")

    def _load_all_time_stats(self) -> None:
        """Load all-time counters and best-batch info from the stats file."""
        path = self._stats_path()
        if not os.path.exists(path):
            return
        try:
            section = None
            best33  = {}
            besthit = {}
            with open(path, encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if line.startswith("[") and line.endswith("]"):
                        section = line[1:-1]
                        continue
                    if "=" not in line or line.startswith("#"):
                        continue
                    key, _, val = line.partition("=")
                    key = key.strip(); val = val.strip()
                    if section == "All Time":
                        if key == "hits_33":   self._ov_at_33   = int(val)
                        elif key == "hits_23": self._ov_at_23   = int(val)
                        elif key == "duds":    self._ov_at_duds = int(val)
                    elif section == "Best Batches":
                        if key == "most_33_iteration":    best33["iteration"]  = int(val)
                        elif key == "most_33_count":      best33["count"]      = int(val)
                        elif key == "most_hits_iteration": besthit["iteration"] = int(val)
                        elif key == "most_hits_count":    besthit["count"]     = int(val)
            if "iteration" in best33 and "count" in best33:
                self._best_33_iter = best33
            if "iteration" in besthit and "count" in besthit:
                self._best_hits_iter = besthit
        except Exception:
            pass

    def _save_stats(self) -> None:
        """Write the stats file with this-run + all-time data + best batches."""
        import datetime
        path = self._stats_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"# Relic Bot Overlay Stats — Last Updated: {ts}\n")
                f.write("# This file carries stats between bot sessions. Safe to read; do not edit manually.\n\n")

                f.write("[This Run]\n")
                f.write(f"iterations = {self.attempt_count}\n")
                f.write(f"hits_33 = {self._ov_hits_33}\n")
                f.write(f"hits_23 = {self._ov_hits_23}\n")
                f.write(f"duds = {self._ov_duds}\n\n")

                f.write("[All Time]\n")
                f.write(f"hits_33 = {self._ov_at_33}\n")
                f.write(f"hits_23 = {self._ov_at_23}\n")
                f.write(f"duds = {self._ov_at_duds}\n\n")

                f.write("[Best Batches]\n")
                if self._best_33_iter:
                    f.write(f"most_33_iteration = {self._best_33_iter['iteration']}\n")
                    f.write(f"most_33_count = {self._best_33_iter['count']}\n")
                if self._best_hits_iter:
                    f.write(f"most_hits_iteration = {self._best_hits_iter['iteration']}\n")
                    f.write(f"most_hits_count = {self._best_hits_iter['count']}\n")
        except Exception:
            pass

    @staticmethod
    def _count_relic_tiers(relic_results: list, hit_min: int) -> tuple[int, int, int]:
        """Return (g3_count, g2_count, dud_count) for individual relics in this iteration."""
        g3 = g2 = dud = 0
        for r in relic_results:
            n = len(r.get("matched_passives", []))
            if n == 0 and r.get("near_misses"):
                n = max(
                    nm.get("matching_passive_count",
                           len(nm.get("matching_passives", [])))
                    for nm in r["near_misses"]
                )
            if n >= 3:
                g3 += 1
            elif n >= hit_min:
                g2 += 1
            else:
                dud += 1
        return g3, g2, dud

    # ------------------------------------------------------------------ #
    #  SHARED HELPERS
    # ------------------------------------------------------------------ #

    def _validate(self) -> bool:
        if not any(self.phase_events):
            messagebox.showwarning("No Sequence",
                "Record or load at least one phase sequence (Setup tab) first.")
            return False
        if not self.save_path_var.get():
            messagebox.showwarning("No Save Path", "Set the save file path.")
            return False
        if not self.backup_path_var.get():
            messagebox.showwarning("No Backup Path", "Set the backup file path.")
            return False
        if not self.relic_builder.is_valid():
            messagebox.showwarning("No Criteria", "Set your relic criteria (Build Exact Relic or Passive Pool tab).")
            return False
        if self.relic_builder.has_compat_errors():
            messagebox.showwarning(
                "Incompatible Passives",
                "One or more relic targets in the 'Build Exact Relic' tab contains "
                "passives that cannot appear on the same relic (same exclusive category).\n\n"
                "Please fix the highlighted conflicts before starting.",
            )
            return False

        if not self.game_exe_var.get().strip():
            messagebox.showwarning("No Game Executable",
                "Set the game executable path so the bot can close the game.")
            return False
        try:
            float(self.game_load_wait_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Load Wait", "Game load wait must be a number.")
            return False
        try:
            float(self.game_close_buffer_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Close Buffer", "Close buffer must be a number.")
            return False

        if not self.batch_output_var.get():
            messagebox.showwarning("No Output Folder", "Choose an output folder for batch results.")
            return False
        try:
            v = float(self.batch_limit_var.get())
            if v <= 0:
                raise ValueError
            limit_type = self.batch_limit_type.get()
            if limit_type == "loops" and v > 1000:
                messagebox.showwarning("Limit Too High", "Maximum allowed loops is 1000.")
                return False
            if limit_type == "hours" and v > 24:
                messagebox.showwarning("Limit Too High", "Maximum allowed run time is 24 hours.")
                return False
        except ValueError:
            messagebox.showwarning("Invalid Limit", "Batch limit must be a positive number.")
            return False
        try:
            float(self.batch_delay_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Delay", "Analysis delay must be a number.")
            return False
        return True

    def _flash_capture(self):
        """Briefly highlight the 📷 indicator when a screenshot is taken."""
        self.capture_lbl.config(foreground="green")
        self.after(600, lambda: self.capture_lbl.config(foreground="lightgray"))

    def _get_region(self):
        return None

    def _on_color_change(self):
        enabled = [c for c, v in self._color_vars.items() if v.get()]
        if not enabled:
            # Enforce at least one
            for var in self._color_vars.values():
                var.set(True)
            self._color_warn.configure(text="At least one color must be enabled.")
        else:
            self._color_warn.configure(text="")

    def _toggle_color(self, color: str):
        """Toggle a relic colour checkbox when its gem image is clicked."""
        var = self._color_vars.get(color)
        if var:
            var.set(not var.get())
            self._on_color_change()

    def _refresh_gem_images(self):
        """Update all gem image labels to match the current gem mode."""
        don = self._gem_mode_var.get() == "don"
        for color, lbl in self._gem_img_labels.items():
            photo = relic_images.get_gem(color, don=don)
            lbl.configure(image=photo)
            lbl.image = photo   # keep reference

    def _get_allowed_colors(self) -> list[str]:
        return [c for c, v in self._color_vars.items() if v.get()]

    def _curse_filter_list(self, *_):
        q = self._curse_search_var.get().strip().lower()
        self._curse_src_lb.delete(0, "end")
        for p in self._curse_all_passives:
            if not q or q in p.lower():
                self._curse_src_lb.insert("end", p)

    def _curse_add(self):
        sel = self._curse_src_lb.curselection()
        if sel:
            item = self._curse_src_lb.get(sel[0])
            if item not in self._blocked_curses_list:
                self._blocked_curses_list.append(item)
                self._blocked_curses_lb.insert("end", item)

    def _curse_remove(self):
        sel = self._blocked_curses_lb.curselection()
        if sel:
            idx = sel[0]
            self._blocked_curses_list.pop(idx)
            self._blocked_curses_lb.delete(idx)

    def _curse_clear(self):
        self._blocked_curses_list.clear()
        self._blocked_curses_lb.delete(0, "end")

    def _get_blocked_curses(self) -> list:
        return [c.lower() for c in self._blocked_curses_list]

    def _is_curse_blocked(self, relic_result: dict, blocked: list) -> bool:
        """Return True if any curse on this relic matches a blocked entry (substring match)."""
        if not blocked:
            return False
        curses = [c.lower() for c in relic_result.get("matched_relic_curses", [])]
        for curse in curses:
            for blocked_curse in blocked:
                if blocked_curse in curse or curse in blocked_curse:
                    return True
        return False

    def _reset_controls(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.bot_running = False
        self._batch_log_path = ""   # stop mirroring to file
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None

    def _set_status(self, text: str, color: str = "gray"):
        def _apply():
            self.status_var.set(f"Status: {text}")
            self.status_label.config(foreground=color)
        self.after(0, _apply)

    def _log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        def _write():
            self.log_box.config(state="normal")
            self.log_box.insert("end", line)
            self.log_box.see("end")
            self.log_box.config(state="disabled")
            if self._overlay:
                self._overlay.append_log(line.rstrip())
        self.after(0, _write)
        if self._batch_log_path:
            try:
                with open(self._batch_log_path, "a", encoding="utf-8") as _f:
                    _f.write(line)
            except Exception:
                pass

    def _log_result(self, result: dict):
        relics = result.get("relics_found", [])
        relic = relics[0] if relics else {}
        name = relic.get("name", "Unknown") if isinstance(relic, dict) else str(relic)
        passives = relic.get("passives", []) if isinstance(relic, dict) else []
        curses = relic.get("curses", []) if isinstance(relic, dict) else []
        match = result.get("match", False)
        matched_passives = result.get("matched_passives", [])

        status = "MATCH" if match else "No match"
        passive_str = ", ".join(passives) if passives else "—"
        self._log(f"  [{status}]  {name}")
        self._log(f"    Passives: {passive_str}")
        if curses:
            self._log(f"    Curses:   {', '.join(curses)}")
        if match and matched_passives:
            self._log(f"    Matched:  {', '.join(matched_passives)}")
        elif not match:
            nms = result.get("near_misses", [])
            if nms:
                nm = max(nms, key=lambda x: x.get("matching_passive_count", 0))
                nm_p = nm.get("matching_passives", [])
                if nm_p:
                    self._log(f"    Near miss: {', '.join(nm_p)}")
