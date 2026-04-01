"""
Main UI for the Elden Ring Nightreign Relic Bot.

Two modes:
  Live Mode  – runs continuously; pauses when a match is found and asks the
               user to keep it or keep searching.
  Batch Mode – runs for a fixed number of loops; saves every iteration's
               save file to its own folder, then writes a README.txt
               summarising matches (with passives + screenshots).
"""

import ctypes
import datetime
import gc
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
from tkinter import filedialog, messagebox, scrolledtext, ttk

from pynput import keyboard as _kb

from bot import input_controller, relic_analyzer, save_manager, screen_capture
from bot.diagnostic import DiagnosticLogger
from ui import theme, relic_images
from ui.relic_builder import RelicBuilderFrame


def _app_root() -> str:
    """Working root: folder containing the EXE when frozen, repo root in dev."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


_REPO_ROOT    = _app_root()
_PROFILES_DIR       = os.path.join(_REPO_ROOT, "profiles")
_LAST_PROFILE_FILE  = os.path.join(_PROFILES_DIR, ".last_profile")


# ─────────────────────────────────────────────────────────────────────────── #
#  README GENERATOR (Batch Mode)
# ─────────────────────────────────────────────────────────────────────────── #

def _fmt_rarity(p: float | None) -> str | None:
    """Return a short rarity string like '~1 in 245 relics  (0.41%)' or None."""
    if not p or p <= 0:
        return None
    import math as _m
    pct = p * 100
    if pct >= 10:
        pct_str = f"{pct:.1f}%"
    elif pct >= 1:
        pct_str = f"{pct:.2f}%"
    else:
        digits = max(1, -int(_m.floor(_m.log10(pct))) + 1)
        pct_str = f"{pct:.{digits}f}%"
    return f"~1 in {int(round(1 / p)):,} relics  ({pct_str})"


def generate_readme(
    output_dir: str,
    criteria: str,
    run_mode: str,
    run_limit,
    results: list,
    hit_min: int = 2,
    p_per_relic: float | None = None,
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

        rarity_str = _fmt_rarity(p_per_relic)
        if rarity_str:
            out.append(f"{indent}  Rarity: {rarity_str}")

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


def write_iter_info(iter_dir: str, iteration: int, relic_results: list, hit_min: int = 2,
                    p_per_relic: float | None = None) -> None:
    """Write info.txt inside an iteration folder.
    Uses per-relic results directly so the MATCH/NEAR MISS labels are always
    accurate regardless of whether multiple relics share the same OCR name."""
    lines = [f"Batch #{iteration:03d}", "=" * 40, ""]

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
        _rarity = _fmt_rarity(p_per_relic)
        for rn, tier, rname, passives, mark_ps in hit_entries:
            lines.append(f"  ★ Relic #{rn} [{tier}]  {rname}")
            if _rarity:
                lines.append(f"    Rarity: {_rarity}")
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
    def __init__(self, widget, text: str, wraplength: int = 280):
        self._widget = widget
        self._text = text
        self._wraplength = wraplength
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
            wraplength=self._wraplength, justify="left", padx=6, pady=4,
        ).pack()

    def _hide(self, _event=None):
        if self._win:
            self._win.destroy()
            self._win = None


# ── System RAM helper (Windows only) ──────────────────────────────────────── #

class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength",                ctypes.c_uint32),
        ("dwMemoryLoad",            ctypes.c_uint32),
        ("ullTotalPhys",            ctypes.c_uint64),
        ("ullAvailPhys",            ctypes.c_uint64),
        ("ullTotalPageFile",        ctypes.c_uint64),
        ("ullAvailPageFile",        ctypes.c_uint64),
        ("ullTotalVirtual",         ctypes.c_uint64),
        ("ullAvailVirtual",         ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]

def _available_ram_mb() -> float:
    """Return available physical RAM in MB using the Windows API (no extra deps)."""
    try:
        stat = _MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(stat)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return stat.ullAvailPhys / (1024 * 1024)
    except Exception:
        return 9999.0   # if the call fails, don't block


# ── Process helpers (Windows only, no subprocess) ─────────────────────────── #
#
# tasklist.exe and taskkill.exe are blocked/intercepted by some security
# software (and by EasyAntiCheat during game runs), causing subprocess.run()
# to hang indefinitely even with CREATE_NO_WINDOW.  These helpers use
# EnumProcesses + OpenProcess + QueryFullProcessImageNameW / TerminateProcess
# via ctypes — direct kernel32/psapi calls that bypass subprocess scanning.

def _pids_for_exe(exe_name: str) -> list:
    """Return a list of PIDs whose image name matches exe_name (case-insensitive)."""
    exe_lower = exe_name.lower()
    results = []
    try:
        _k32   = ctypes.windll.kernel32
        _psapi = ctypes.windll.psapi
        count  = 512
        while True:
            pids      = (ctypes.c_ulong * count)()
            cb_needed = ctypes.c_ulong(0)
            _psapi.EnumProcesses(pids, ctypes.sizeof(pids), ctypes.byref(cb_needed))
            n = cb_needed.value // ctypes.sizeof(ctypes.c_ulong)
            if n < count:
                break
            count *= 2
        for pid in list(pids)[:n]:
            if pid == 0:
                continue
            h = _k32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                continue
            buf = ctypes.create_unicode_buffer(260)
            sz  = ctypes.c_ulong(260)
            if _k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(sz)):
                if os.path.basename(buf.value).lower() == exe_lower:
                    results.append(pid)
            _k32.CloseHandle(h)
    except Exception:
        pass
    return results


def _kill_exe(exe_name: str) -> None:
    """Terminate all processes whose image name matches exe_name."""
    _k32 = ctypes.windll.kernel32
    for pid in _pids_for_exe(exe_name):
        h = _k32.OpenProcess(1, False, pid)   # PROCESS_TERMINATE
        if h:
            _k32.TerminateProcess(h, 1)
            _k32.CloseHandle(h)


def _boost_game_priority(exe_name: str) -> bool:
    """Raise the game process to HIGH priority class.
    Returns True if at least one process was boosted successfully."""
    _HIGH_PRIORITY_CLASS = 0x00000080
    _PROCESS_SET_INFORMATION = 0x0200
    _k32 = ctypes.windll.kernel32
    boosted = False
    for pid in _pids_for_exe(exe_name):
        h = _k32.OpenProcess(_PROCESS_SET_INFORMATION, False, pid)
        if h:
            if _k32.SetPriorityClass(h, _HIGH_PRIORITY_CLASS):
                boosted = True
            _k32.CloseHandle(h)
    return boosted


class RelicBotApp(tk.Tk):
    def __init__(self):
        # Must run before super().__init__() — Windows assigns the taskbar slot
        # on window creation, so this must fire first or the button gets grouped
        # under python.exe and iconbitmap has no effect on the taskbar icon.
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "PulgoMaster.RelicBot.v1.6.0"
            )
        except Exception:
            pass

        super().__init__()
        self.withdraw()   # keep window hidden until icon is set + UI is built; prevents flash

        self.title("Elden Ring Nightreign – Relic Bot v1.6.0  |  Made by Pulgo")
        self.resizable(True, True)

        # App icon (title-bar + alt-tab thumbnail)
        # When frozen by PyInstaller, assets are extracted to sys._MEIPASS.
        # In dev, fall back to the repo root (two dirs above this file).
        _icon_base = getattr(sys, "_MEIPASS",
                             os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _icon_path = os.path.join(_icon_base, "assets", "icon.ico")
        if os.path.exists(_icon_path):
            self.iconbitmap(_icon_path)

        # Input recording
        self.recorder = input_controller.InputRecorder()
        self.player = input_controller.InputPlayer()
        # Diagnostic logger (test build) — created per batch run, None between runs
        self._diag: DiagnosticLogger | None = None
        self._diag_cur_iter: int = 0
        # phase_events[0] = Setup, [1] = Buy+Preview (fast), [2] = Advance relic (RIGHT), [3] = Reset to shop (F), [4] = reserved
        self.phase_events: list = [[], [], [], [], []]
        self._phase1_alt_events: list = []   # safe buy sequence (no extra F — waits for auto-transition)

        # Adaptive path tracking
        self._last_cpu_pct: float   = 0.0   # CPU% from last sample
        self._cpu_idle_prev: int    = 0      # GetSystemTimes idle accumulator
        self._cpu_total_prev: int   = 0      # GetSystemTimes total accumulator
        self._active_phase: int = 0
        self._rec_blink = False

        # Relic type — controls murk cost per relic for the Phase 3 count calculation
        self.relic_type_var = tk.StringVar(value="normal")   # "night" or "normal"

        # Global hotkey (works even when the game window has focus)
        self._hotkey_str = "Key.f9"       # pynput key string
        self._hotkey_display = "F9"        # human-readable label
        self._global_kb_listener = None    # persistent pynput Listener
        # Overlay visibility toggle hotkey
        self._ov_hotkey_str     = "Key.f7"
        self._ov_hotkey_display = "F7"
        # Overlay matches view toggle hotkey
        self._matches_hotkey_str     = "Key.f8"
        self._matches_hotkey_display = "F8"

        # Bot state
        self.bot_thread: threading.Thread | None = None
        self.bot_running = False
        self.attempt_count = 0
        self._batch_log_path: str = ""        # set while a batch run is active (process log)
        self._batch_relic_log_path: str = ""  # set while a batch run is active (relic log)

        # Manual iteration reset (user-triggered soft nuke from overlay)
        self._reset_iter_requested = False

        # Elapsed seconds from game window focus to equipment-menu confirmation,
        # recorded by the adaptive load wait. Used to scale Phase 0 shop wait.
        self._last_load_elapsed: float = 45.0

        # Adaptive input-gap scaling — tracks game load-time as a proxy for
        # overall system performance. As the system slows under prolonged use,
        # load times grow and _perf_gap_mult rises proportionally, widening
        # all input gaps so dialogs have more time to open.
        self._first_load_elapsed: float = 0.0   # baseline (first successful load)
        self._load_history: list = []            # sliding window — last 5 load times
        self._perf_gap_mult: float = 1.0         # current multiplier (1.0 = baseline)
        # Per-iteration calibration counters (reset at start of each iteration)
        self._iter_p0_attempts: int       = 0     # Phase 0 attempts (1 = clean, >1 = retried)
        self._iter_p1_settle_retries: int = 0    # Phase 1 settle-check retries across batches
        self._iter_safe_path_used: bool   = False # True if any batch fell back to safe buy path
        self._iter_settle_poll_depth: int  = 0    # cumulative settle polls used across all batches
        self._iter_batches_settled: int    = 0    # how many batches reached a successful settle
        # Batch-level reliability accumulators (reset at batch start, logged at batch end)
        self._batch_p0_extra: int          = 0    # total extra Phase 0 attempts across all iterations
        self._batch_settle_retries: int    = 0    # total Phase 1 settle retries (ESC cycles)
        self._batch_safe_path_count: int   = 0    # iterations that used the safe buy path at least once
        self._batch_failed_settle: int     = 0    # batches where settle check exhausted all 8 polls
        self._batch_total_poll_depth: int  = 0    # cumulative settle poll depth across all iterations
        self._batch_total_settled: int     = 0    # cumulative batches that confirmed across all iters

        # Backup/startup ready event
        self._ready_event = threading.Event()

        # Overlay (Batch Mode only)
        self._overlay = None
        self._overlay_enabled_var    = tk.BooleanVar(value=True)
        # Overlay element visibility / behaviour
        self._ov_show_stats_var      = tk.BooleanVar(value=True)
        self._ov_show_rolls_var      = tk.BooleanVar(value=True)
        self._ov_show_overflow_var   = tk.BooleanVar(value=True)
        self._ov_show_proc_log_var   = tk.BooleanVar(value=True)
        self._ov_show_relic_log_var  = tk.BooleanVar(value=True)
        self._ov_elem_widgets: list  = []   # populated in _build_ui; toggled by overlay enable
        self._parallel_enabled_var  = tk.BooleanVar(value=False)
        self._parallel_workers_var  = tk.IntVar(value=2)
        self._async_enabled_var     = tk.BooleanVar(value=False)
        self._smart_throttle_var    = tk.BooleanVar(value=False)
        self._exclude_buy_phase_var = tk.BooleanVar(value=False)
        self._gpu_accel_var         = tk.BooleanVar(value=False)
        self._hw_ram_gb, self._hw_cpu_cores, self._hw_gpu_name = self._detect_hardware()
        self._hw_cuda_available, self._hw_cuda_error = self._check_cuda_available()
        self._hw_cuda_torch_installed = self._cuda_torch_installed()
        self._gpu_eligible, self._gpu_eligible_name, self._gpu_eligible_reason = \
            self._check_gpu_install_eligible()
        # Pre-seed adaptive timing from persisted calibration (if machine matches)
        _cal = self._load_calibration()
        if _cal.get("machine_id") == self._get_machine_id() and _cal.get("baseline_load_s", 0) > 0:
            self._first_load_elapsed = float(_cal["baseline_load_s"])
            self._perf_gap_mult      = float(_cal.get("perf_mult", 1.0))
        # Timing data — accumulated real measured timings per mode, persisted across sessions
        self._timing_data: dict       = self._load_timing_data()
        self._timing_data_lock        = threading.Lock()
        self._stop_after_batch      = False   # graceful stop flag
        self._game_hung             = False   # set True by watchdog when game freezes
        self._low_perf_mode_var     = tk.BooleanVar(value=False)
        self._backlog_mode_var           = tk.BooleanVar(value=False)
        self._intermittent_backlog_var   = tk.BooleanVar(value=False)
        self._intermittent_every_n_var   = tk.IntVar(value=5)
        self._hybrid_var                 = tk.BooleanVar(value=False)
        self._gpu_always_analyze_var     = tk.BooleanVar(value=False)
        self._prev_colors: set = {"Red", "Blue", "Green", "Yellow"}
        self._color_warn_job = None   # after() job for warning auto-dismiss
        self._mouse_blocker_hook   = None   # WH_MOUSE_LL hook handle
        self._mouse_blocker_cb     = None   # keep-alive for hook callback (prevent GC)
        self._mouse_blocker_thread = None   # daemon thread running hook message pump
        self._mouse_blocker_tid    = 0      # thread ID for PostThreadMessage to stop hook
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
        # Total relics finalized this run (duds + 2/3 + 3/3 combined; reset each START)
        self._ov_total_relics = 0
        # Screenshots captured/queued this run (backlog + async); reset each START
        self._ov_stored_count = 0
        self._async_relic_q: queue.PriorityQueue | None = None
        # Iterations cancelled mid-run (workers skip counter updates for these)
        self._async_cancelled_iters: set = set()
        # Per-iteration counter contributions for async rollback:
        # {iteration: {at_33, at_23, at_duds, total_relics}} — never touches other iterations
        self._iter_contributions: dict = {}
        self._iter_contrib_lock = threading.Lock()
        # Shared async state — set at run start, cleared at run end
        self._async_iter_state: dict | None = None
        self._async_dir_map: dict | None = None
        self._async_state_lock: threading.Lock | None = None
        self._async_results_list: list | None = None
        # OCR throttle event: set=workers run freely, clear=workers yield during input phases
        self._ocr_go_event: threading.Event | None = None

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
        self._auto_load_last_profile()
        self.after(0, self._on_relic_type_change)   # apply curse frame visibility after UI settles
        self.after(200, self._log_screen_resolution)
        self.after(300, self._log_calibration_status)
        self.deiconify()   # show window now that icon is set and UI is fully built

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
        inner.columnconfigure(0, weight=1)   # let column 0 stretch with window width
        _canvas_window = _canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_frame_configure(event):
            _canvas.configure(scrollregion=_canvas.bbox("all"))

        def _on_canvas_configure(event):
            _canvas.itemconfig(_canvas_window, width=event.width)

        inner.bind("<Configure>", _on_frame_configure)
        _canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse-wheel scrolling — yscrollincrement=20 means each "unit" = 20px;
        # delta/120 per notch * 3 units = 60px per scroll notch.
        # Only fires for events that originated inside the main window; events from
        # dialogs or the overlay Toplevel are skipped so those windows can handle
        # their own scrolling (Text widgets route natively when propagation is free).
        _canvas.configure(yscrollincrement=20)
        def _on_mousewheel(event):
            if event.widget.winfo_toplevel() is not self:
                return   # let dialogs / overlay handle their own scroll
            _canvas.yview_scroll(int(-1 * (event.delta / 120)) * 3, "units")
        _canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # All widgets go into `inner` instead of `self`
        self._inner = inner

        # ── Profile ─────────────────────────────────────────────────── #
        profile_frame = ttk.LabelFrame(inner, text="Profile")
        profile_frame.grid(row=0, column=0, sticky="ew", **pad)
        profile_frame.columnconfigure(1, weight=1)   # combobox stretches with window

        ttk.Label(profile_frame, text="Profile:").grid(row=0, column=0, sticky="w", **pad)
        self._profile_var = tk.StringVar()
        self._profile_cb = ttk.Combobox(
            profile_frame, textvariable=self._profile_var, state="readonly", width=30
        )
        self._profile_cb.grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(profile_frame, text="Load", command=self._load_profile).grid(row=0, column=2, **pad)
        ttk.Button(profile_frame, text="Save", command=self._save_profile).grid(row=0, column=3, **pad)
        ttk.Button(profile_frame, text="Save As…", command=self._save_profile_as).grid(row=0, column=4, **pad)
        ttk.Button(profile_frame, text="Delete", command=self._delete_profile).grid(row=0, column=5, **pad)
        ttk.Button(profile_frame, text="Restore Defaults", command=self._reset_to_defaults).grid(row=0, column=6, **pad)
        _export_diag_btn = ttk.Button(
            profile_frame, text="Export Diagnostics", command=self._export_diagnostics,
        )
        _export_diag_btn.grid(row=0, column=7, **pad)
        _Tooltip(_export_diag_btn,
                 "Generates a small diagnostics text file with system info, GPU status,\n"
                 "install logs, and recent run data. Useful for diagnosing issues without\n"
                 "transferring the full bot folder.")

        # Pre-initialize vars that are referenced by multiple sections below
        self.batch_output_var = tk.StringVar(value=os.path.join(_REPO_ROOT, "batch_output"))

        # ── Save File & Game Configuration ──────────────────────────── #
        save_frame = ttk.LabelFrame(inner, text="Save File & Game Configuration")
        save_frame.grid(row=1, column=0, sticky="ew", **pad)
        save_frame.columnconfigure(1, weight=1)   # entry column stretches with window

        ttk.Label(save_frame, text="Save file:").grid(row=0, column=0, sticky="w", **pad)
        self.save_path_var = tk.StringVar()
        ttk.Entry(save_frame, textvariable=self.save_path_var, width=52).grid(row=0, column=1, sticky="ew", **pad)
        _save_browse_btn = ttk.Button(save_frame, text="Browse", command=self._browse_save)
        _save_browse_btn.grid(row=0, column=2, **pad)
        _Tooltip(_save_browse_btn,
                 "Your Elden Ring save file. Typical path:\n"
                 "  C:\\Users\\[YourName]\\AppData\\Roaming\\EldenRing\\[SteamID]\\ER0000.sl2\n\n"
                 "The bot backs this file up before each iteration so you can restore\n"
                 "to any previous state. Always set this before starting.")

        ttk.Label(save_frame, text="Backup folder:").grid(row=1, column=0, sticky="w", **pad)
        self.backup_path_var = tk.StringVar(value=os.path.join(_REPO_ROOT, "save_backups"))
        ttk.Entry(save_frame, textvariable=self.backup_path_var, width=52).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(save_frame, text="Browse", command=self._browse_backup).grid(row=1, column=2, **pad)

        ttk.Label(save_frame, text="Output folder:").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(save_frame, textvariable=self.batch_output_var, width=52).grid(row=2, column=1, sticky="ew", **pad)
        ttk.Button(save_frame, text="Browse", command=self._browse_batch_output).grid(row=2, column=2, **pad)

        ttk.Label(save_frame, text="Game executable:").grid(row=3, column=0, sticky="w", **pad)
        self.game_exe_var = tk.StringVar()
        ttk.Entry(save_frame, textvariable=self.game_exe_var, width=52).grid(row=3, column=1, sticky="ew", **pad)
        _exe_browse_btn = ttk.Button(save_frame, text="Browse", command=self._browse_game_exe)
        _exe_browse_btn.grid(row=3, column=2, **pad)
        _Tooltip(_exe_browse_btn,
                 "Path to the Elden Ring game executable. Typical Steam path:\n"
                 "  C:\\Program Files (x86)\\Steam\\steamapps\\common\\ELDEN RING\\Game\\eldenring.exe\n\n"
                 "The bot uses this path to relaunch the game after each iteration.\n"
                 "Without this set, the bot cannot restart the game automatically.")

        ttk.Label(
            save_frame,
            text="\u26a0  The bot requires default in-game keybinds — F must be your confirm/interact key.",
        ).grid(row=4, column=0, columnspan=3, sticky="w", **pad)

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
        self.phase_settle_vars = [None, tk.StringVar(value="0"),
                                  None, None, tk.StringVar(value="0.25")]
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
        _Tooltip(self._manual_toggle_btn,
                 "\u26a0  Advanced users only.\n\n"
                 "This section lets you re-record or replace the input sequences\n"
                 "the bot replays during each iteration.\n\n"
                 "DO NOT modify any recordings unless you fully understand what\n"
                 "each phase does and why the inputs are timed the way they are.\n"
                 "An incorrect recording will cause the bot to navigate wrong menus,\n"
                 "buy wrong items, skip relics, or break the iteration entirely.\n\n"
                 "Most users should NEVER need to open this section.\n"
                 "The default auto-loaded sequences work for standard setups.")

        # Collapsible recording frame (hidden by default)
        self._manual_setup_frame = ttk.Frame(seq_frame)
        self._build_manual_setup_frame()

        # ── Relic Criteria (builder with Free Text / Exact / Pool tabs) ─ #
        self.relic_builder = RelicBuilderFrame(inner)
        self.relic_builder.grid(row=3, column=0, sticky="ew", **pad)

        # ── Curse Filter ─────────────────────────────────────────────── #
        self._curse_frame = ttk.LabelFrame(inner, text="Curse Filter  (relics with these curses are rejected)")
        self._curse_frame.grid(row=4, column=0, sticky="ew", **pad)
        curse_frame = self._curse_frame

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
        self._curse_src_lb.bind("<MouseWheel>",
            lambda e: (self._curse_src_lb.yview_scroll(int(-1*(e.delta/120)), "units"), "break")[1])
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
        self._blocked_curses_lb.bind("<MouseWheel>",
            lambda e: (self._blocked_curses_lb.yview_scroll(int(-1*(e.delta/120)), "units"), "break")[1])
        self._blocked_curses_list: list[str] = []

        # Curse odds impact label (Deep mode only)
        self._curse_odds_lbl = ttk.Label(
            curse_frame, text="", foreground=theme.TEXT_MUTED,
            wraplength=700, justify="left",
        )
        self._curse_odds_lbl.pack(anchor="w", padx=6, pady=(0, 4))

        self._excluded_passives_list: list[str] = []
        self._save_exclusion_matches_var = tk.BooleanVar(value=False)
        self._excl_dormant_var = tk.BooleanVar(value=False)
        self._smart_analyze_var = tk.BooleanVar(value=False)
        self._ov_smart_hits: int = 0

        # ── Excluded Passives ─────────────────────────────────────── #
        excl_frame = ttk.LabelFrame(
            inner,
            text="Excluded Passives  (relics with these passives are rejected, unless explicitly requested)")
        excl_frame.grid(row=5, column=0, sticky="ew", **pad)

        ttk.Label(
            excl_frame,
            text=(
                "Add passives to exclude. A relic that meets your match criteria but also carries "
                "an excluded passive will NOT be counted as a hit. "
                "Exception: if an excluded passive is also explicitly added to your Pool, "
                "Pairings, or Build targets, it takes precedence and the exclusion is ignored "
                "for that passive."
            ),
            foreground=theme.TEXT_MUTED, wraplength=700, justify="left",
        ).pack(anchor="w", padx=6, pady=(4, 2))

        excl_content = ttk.Frame(excl_frame)
        excl_content.pack(fill="both", expand=False, padx=6, pady=(0, 4))
        excl_content.columnconfigure(0, weight=3)
        excl_content.columnconfigure(2, weight=2)

        # Left: all passives searchable
        excl_left = ttk.LabelFrame(excl_content, text="Passives")
        excl_left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        from bot.passives import ALL_PASSIVES_SORTED as _ALL_PASSIVES_SORTED
        self._excl_search_var = tk.StringVar()
        self._excl_search_var.trace_add("write", self._excl_filter_list)
        _excl_entry = ttk.Entry(excl_left, textvariable=self._excl_search_var)
        _excl_entry.pack(fill="x", padx=4, pady=(4, 2))
        _Tooltip(_excl_entry, "Search passives to exclude. Relics containing an excluded passive will not count as hits.")

        excl_src_body = ttk.Frame(excl_left)
        excl_src_body.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._excl_src_lb = tk.Listbox(excl_src_body, height=5, selectmode="browse",
                                       exportselection=False, activestyle="none")
        _sl(self._excl_src_lb)
        excl_src_sb = ttk.Scrollbar(excl_src_body, orient="vertical", command=self._excl_src_lb.yview)
        self._excl_src_lb.configure(yscrollcommand=excl_src_sb.set)
        self._excl_src_lb.pack(side="left", fill="both", expand=True)
        excl_src_sb.pack(side="right", fill="y")
        self._excl_src_lb.bind("<MouseWheel>",
            lambda e: (self._excl_src_lb.yview_scroll(int(-1*(e.delta/120)), "units"), "break")[1])
        self._excl_all_passives = list(_ALL_PASSIVES_SORTED)
        for _p in self._excl_all_passives:
            self._excl_src_lb.insert("end", _p)

        # Centre: buttons
        excl_mid = ttk.Frame(excl_content)
        excl_mid.grid(row=0, column=1, padx=6)
        ttk.Button(excl_mid, text="Exclude →",  command=self._excl_add,    width=12).pack(pady=4)
        ttk.Button(excl_mid, text="← Remove",   command=self._excl_remove, width=12).pack(pady=4)
        ttk.Button(excl_mid, text="Clear All",   command=self._excl_clear,  width=12).pack(pady=8)
        ttk.Checkbutton(
            excl_mid, text="Excl. All Dormants",
            variable=self._excl_dormant_var,
            command=self._excl_toggle_dormant,
        ).pack(pady=4)

        # Right: excluded passives list
        excl_right = ttk.LabelFrame(excl_content, text="Excluded Passives")
        excl_right.grid(row=0, column=2, sticky="nsew")
        excl_body = ttk.Frame(excl_right)
        excl_body.pack(fill="both", expand=True, padx=4, pady=4)
        self._excluded_lb = tk.Listbox(excl_body, height=5, selectmode="browse",
                                       exportselection=False, activestyle="none")
        _sl(self._excluded_lb)
        excl_sb = ttk.Scrollbar(excl_body, orient="vertical", command=self._excluded_lb.yview)
        self._excluded_lb.configure(yscrollcommand=excl_sb.set)
        self._excluded_lb.pack(side="left", fill="both", expand=True)
        excl_sb.pack(side="right", fill="y")
        self._excluded_lb.bind("<MouseWheel>",
            lambda e: (self._excluded_lb.yview_scroll(int(-1*(e.delta/120)), "units"), "break")[1])

        # Opt-in: save excluded matches
        ttk.Checkbutton(
            excl_frame,
            text='Save "matched but excluded" relics to a separate folder (screenshot + summary)',
            variable=self._save_exclusion_matches_var,
        ).pack(anchor="w", padx=6, pady=(0, 6))

        # ── Batch Mode Settings ─────────────────────────────────────── #
        self.batch_frame = ttk.LabelFrame(inner, text="Batch Mode Settings")
        self.batch_frame.grid(row=6, column=0, sticky="ew", **pad)

        ttk.Label(self.batch_frame, text="Loops (max 1000):").grid(row=0, column=0, sticky="w", **pad)
        self.batch_limit_type = tk.StringVar(value="loops")   # kept for save/load compat; always "loops"
        self.batch_limit_var = tk.StringVar(value="20")
        _vcmd = (self.register(lambda v: v.isdigit() or v == ""), "%P")
        _batch_entry = ttk.Entry(self.batch_frame, textvariable=self.batch_limit_var,
                                 width=7, validate="key", validatecommand=_vcmd)
        _batch_entry.grid(row=0, column=1, **pad)

        def _batch_clamp(*_):
            try:
                v = int(self.batch_limit_var.get())
                clamped = max(1, min(1000, v))
                if clamped != v:
                    self.batch_limit_var.set(str(clamped))
            except ValueError:
                pass
            self._update_odds_viewer()

        self.batch_limit_var.trace_add("write", _batch_clamp)

        def _batch_inc(delta):
            try:
                v = max(1, min(1000, int(self.batch_limit_var.get()) + delta))
            except ValueError:
                v = 1
            self.batch_limit_var.set(str(v))

        _arrow_col = ttk.Frame(self.batch_frame)
        _arrow_col.grid(row=0, column=2, padx=(0, 8))
        ttk.Button(_arrow_col, text="▲", width=2, command=lambda: _batch_inc(1)).pack(side="top")
        ttk.Button(_arrow_col, text="▼", width=2, command=lambda: _batch_inc(-1)).pack(side="top")


        # Brute Force Analysis toggle
        bf_chk = ttk.Checkbutton(
            self.batch_frame, text="⚡ Brute Force Analysis",
            variable=self._parallel_enabled_var,
            command=self._on_parallel_toggle,
        )
        bf_chk.grid(row=4, column=0, columnspan=2, sticky="w", **pad)
        _Tooltip(bf_chk,
                 "Runs multiple CPU workers in parallel to speed up relic analysis.\n"
                 "Each worker loads its own OCR model into RAM (~200 MB each).\n"
                 "CPU cores are shared evenly so workers don't fight each other.\n\n"
                 "── With GPU Acceleration ON ─────────────────────\n"
                 "Brute Force is locked unless Hybrid GPU+CPU mode is also enabled.\n"
                 "GPU Acceleration already adds 1 fast GPU worker on its own.\n"
                 "Enable Hybrid to add CPU workers alongside it.\n\n"
                 "── Without GPU Acceleration (CPU mode) ──────────\n"
                 "Workers run truly in parallel on separate CPU cores.\n"
                 "Recommended workers by system RAM:\n"
                 "  8 GB   →  OFF (use single-threaded mode)\n"
                 " 12 GB   →  2 workers\n"
                 " 16 GB   →  2–3 workers\n"
                 " 24 GB   →  4–5 workers\n"
                 " 32 GB+  →  6–8 workers\n\n"
                 "Workers automatically pause if RAM drops critically low.\n"
                 "Leave OFF if you notice crashes, freezes, or system slowdowns.")
        ttk.Label(self.batch_frame, text="Workers:").grid(row=4, column=2, **pad)
        _worker_max = min(8, max(2, self._hw_cpu_cores or 8))
        self._parallel_spin = ttk.Spinbox(
            self.batch_frame, from_=2, to=_worker_max, width=4,
            textvariable=self._parallel_workers_var, state="disabled",
        )
        self._parallel_spin.grid(row=4, column=3, sticky="w", **pad)
        _Tooltip(self._parallel_spin,
                 f"Number of parallel CPU workers (2–{_worker_max}).\n"
                 "Each worker uses ~200 MB RAM and ~1 CPU core for OCR inference.\n\n"
                 "Only active when Hybrid GPU+CPU mode is enabled (with GPU Accel),\n"
                 "or when running in CPU-only mode (GPU Accel off).\n\n"
                 "Recommended by system RAM:\n"
                 "  8 GB  →  2 workers max\n"
                 " 16 GB  →  2–3 workers safe\n"
                 " 32 GB  →  4–6 workers\n\n"
                 "⚠ 4+ workers on 8 GB RAM: will exhaust RAM and cause crashes.\n"
                 "Workers automatically pause when system RAM is critically low.")
        self._ram_label_var = tk.StringVar(value="")
        self._ram_label = ttk.Label(self.batch_frame, textvariable=self._ram_label_var,
                                    foreground=theme.TEXT_MUTED)
        self._ram_label.grid(row=4, column=4, sticky="w", **pad)
        _Tooltip(self._ram_label,
                 "Shows estimated RAM usage and CPU core allocation for the current worker count.\n\n"
                 "Using all cores is not recommended — the bot and the game will fight for core\n"
                 "access, which can cause missed inputs, frame drops, or stuttering.\n\n"
                 "Leave at least 2–4 cores free for the game and OS.")
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

        # Smart Throttle toggle
        st_chk = ttk.Checkbutton(
            self.batch_frame, text="⚡ Smart Throttle",
            variable=self._smart_throttle_var,
        )
        st_chk.grid(row=5, column=2, sticky="w", **pad)
        _Tooltip(st_chk,
                 "Only throttle OCR workers during input phases when the system\n"
                 "is actually under stress (CPU > 70% or perf multiplier > 1.15×).\n\n"
                 "On a healthy machine: workers keep running during Phase 0/1/3\n"
                 "inputs for maximum throughput.\n\n"
                 "On a stressed machine: automatically falls back to hard throttle\n"
                 "so inputs are never starved.\n\n"
                 "Leave OFF if you want inputs always protected (safe default).")

        # Smart Analyze toggle
        sa_chk = ttk.Checkbutton(
            self.batch_frame, text="🔍 Smart Analyze",
            variable=self._smart_analyze_var,
        )
        sa_chk.grid(row=5, column=3, columnspan=2, sticky="w", **pad)
        _Tooltip(sa_chk,
                 "After OCR, evaluates non-matching relics against a set of curated rules.\n"
                 "Catches valuable combinations not in your target criteria — school stacks,\n"
                 "affinity doubles, weapon class combos, and more.\n\n"
                 "Smart hits are saved to a smart_hits/ subfolder inside the iteration folder.\n"
                 "The overlay shows a live counter of smart hits found this session.\n\n"
                 "Runs in the same worker thread — no extra RAM needed.\n"
                 "Has no effect on matched relics (God Rolls and HITs are unaffected).")

        # Exclude Analysis While Operations Are Happening sub-option (Async Analysis only)
        _ebp_chk = ttk.Checkbutton(
            self.batch_frame, text="⏸ Exclude Analysis While Operations Are Happening",
            variable=self._exclude_buy_phase_var,
        )
        _ebp_chk.grid(row=6, column=0, columnspan=3, sticky="w",
                      padx=(24, 4), pady=(0, 2))
        _Tooltip(_ebp_chk,
                 "Keeps all async workers paused from the moment the bot starts\n"
                 "buying until every relic screenshot has been captured.\n\n"
                 "Workers resume after Phase 2 completes, running freely during\n"
                 "Phase 3 (reset) and Phase 0 (shop nav) of the next cycle.\n\n"
                 "Provides maximum input stability during the buy+scan window\n"
                 "while still using Async Analysis for background processing.\n\n"
                 "Only has effect with Async Analysis enabled.")

        # Unified Hybrid GPU+CPU — works with Async and Backlog modes
        _hyb_chk = ttk.Checkbutton(
            self.batch_frame, text="⚡ Hybrid GPU+CPU Analysis",
            variable=self._hybrid_var,
        )
        _hyb_chk.grid(row=6, column=3, columnspan=2, sticky="w",
                      padx=(4, 4), pady=(0, 2))
        _Tooltip(_hyb_chk,
                 "Runs one dedicated GPU worker alongside the CPU worker pool.\n"
                 "Both pull from the same queue in parallel — throughput ≈ GPU + CPU speed.\n\n"
                 "Works with both Async Analysis and Backlog Analysis.\n\n"
                 "Requirements:\n"
                 "  • GPU Acceleration must be installed\n"
                 "  • Brute Force Analysis must be enabled (for CPU workers)\n\n"
                 "GPU worker uses CUDA; CPU workers use the processor.\n"
                 "CPU workers are capped at 4 in Hybrid mode.")

        # GPU Always Analyze — sub-option of Hybrid mode only
        _gpu_aa_chk = ttk.Checkbutton(
            self.batch_frame, text="🔓 GPU: Always Analyze",
            variable=self._gpu_always_analyze_var,
        )
        _gpu_aa_chk.grid(row=6, column=5, columnspan=3, sticky="w",
                         padx=(4, 4), pady=(0, 2))
        _Tooltip(_gpu_aa_chk,
                 "Allows the GPU worker to keep analyzing relics even while CPU workers are paused for game inputs.\n"
                 "GPU inference runs on the graphics card and does not compete for the CPU time inputs need.\n"
                 "Input timing and stability are unaffected.\n\n"
                 "── WHEN IT HELPS ──────────────────────────────────────────────────────────────────────────────\n"
                 "Best with 'Exclude Analysis While Operations Are Happening' — that mode pauses all workers for\n"
                 "the entire buy+scan window (up to 90s/cycle). This keeps the GPU draining the queue the whole\n"
                 "time. Without Excl.Ops the throttle gates are only a few seconds wide — minimal benefit.\n\n"
                 "Applies to Backlog Hybrid too. GPU backlog worker respects the gate by default; this bypasses it.\n\n"
                 "── HARDWARE GUIDANCE ──────────────────────────────────────────────────────────────────────────\n"
                 "RTX 3070+ / RX 6800+: Recommended — compute and graphics pipelines run independently.\n"
                 "RTX 3060 / GTX 1660 etc.: Caution — brief game frame drops during Phase 1 are possible.\n"
                 "Laptop GPU: Not recommended — combined load risks thermal throttling (slower OCR + game stutter).\n\n"
                 "── NOTE ───────────────────────────────────────────────────────────────────────────────────────\n"
                 "Enabling Hybrid GPU+CPU Analysis automatically disables Smart Throttle.\n"
                 "Requires: Hybrid GPU+CPU Analysis must be enabled.",
                 wraplength=560)

        def _update_bf_gpu_lock(*_):
            """Lock Brute Force + spinbox when GPU is on but Hybrid is not active.

            GPU on alone = exactly 1 GPU worker, no CPU workers.
            CPU workers only activate via Hybrid mode alongside the GPU worker.
            In Hybrid mode CPU workers are capped at 4 to prevent over-saturation.
            """
            _gpu = self._gpu_accel_var.get()
            _hyb = self._hybrid_var.get()
            if _gpu and not _hyb:
                bf_chk.config(state="disabled")
                self._parallel_spin.configure(state="disabled")
            else:
                bf_chk.config(state="normal")
                # Cap CPU workers at 4 in Hybrid mode
                _cap = min(4, _worker_max) if _hyb else _worker_max
                self._parallel_spin.configure(to=_cap)
                if self._parallel_workers_var.get() > _cap:
                    self._parallel_workers_var.set(_cap)
                if self._parallel_enabled_var.get():
                    self._parallel_spin.configure(state="normal")
                else:
                    self._parallel_spin.configure(state="disabled")

        _async_sub_updating = [False]

        def _update_async_sub_state(*_):
            if _async_sub_updating[0]:
                return
            _async_sub_updating[0] = True
            try:
                _on = self._async_enabled_var.get()

                # Excl.Ops is async-only
                _ebp_chk.config(state="normal" if _on else "disabled")

                # Unified Hybrid: requires GPU Accel + Brute Force — not mode-dependent
                _hyb_ok = (self._gpu_accel_var.get()
                           and self._parallel_enabled_var.get())
                _hyb_chk.config(state="normal" if _hyb_ok else "disabled")
                if not _hyb_ok:
                    self._hybrid_var.set(False)
                _hybrid_on = self._hybrid_var.get()

                # Smart Throttle: only valid when Async is on AND Hybrid is off.
                # Enabling Hybrid clears and disables Smart Throttle automatically.
                _st_ok = _on and not _hybrid_on
                if not _st_ok and self._smart_throttle_var.get():
                    self._smart_throttle_var.set(False)
                st_chk.config(state="normal" if _st_ok else "disabled")

                # GPU Always Analyze: available whenever Hybrid is on.
                # Smart Throttle is already cleared when Hybrid is on — no extra check needed.
                _gpu_aa_chk.config(state="normal" if _hybrid_on else "disabled")
                if not _hybrid_on:
                    self._gpu_always_analyze_var.set(False)

                _update_bf_gpu_lock()
            finally:
                _async_sub_updating[0] = False

        self._async_enabled_var.trace_add("write", _update_async_sub_state)
        self._gpu_accel_var.trace_add("write", _update_async_sub_state)
        self._parallel_enabled_var.trace_add("write", _update_async_sub_state)
        self._hybrid_var.trace_add("write", _update_async_sub_state)
        self._gpu_always_analyze_var.trace_add("write", _update_async_sub_state)
        self._smart_throttle_var.trace_add("write", _update_async_sub_state)
        _update_async_sub_state()

        # ── Overlay Elements sub-section ────────────────────────────── #
        ov_elem_lf = ttk.LabelFrame(self.batch_frame, text="Overlay Elements")
        ov_elem_lf.grid(row=11, column=0, columnspan=8, sticky="ew", **pad)

        # Show HUD toggle lives here as the parent of all element settings
        ov_chk = ttk.Checkbutton(
            ov_elem_lf, text="Show HUD overlay while bot is running",
            variable=self._overlay_enabled_var,
        )
        ov_chk.grid(row=0, column=0, columnspan=5, sticky="w", **pad)
        _Tooltip(ov_chk,
                 "Displays a translucent HUD in the bottom-left of your screen with live stats and log.\n"
                 "Requires the game to run in Borderless or Fullscreen.\n"
                 "Clicking the HUD does NOT steal focus from the game window.")

        self._ov_elem_widgets = []

        def _ov_chk_item(parent, text, var, row, col, tooltip=None):
            chk = ttk.Checkbutton(parent, text=text, variable=var,
                                  command=self._on_ov_settings_change)
            chk.grid(row=row, column=col, sticky="w", padx=(28, 8), pady=4)
            if tooltip:
                _Tooltip(chk, tooltip)
            self._ov_elem_widgets.append(chk)
            return chk

        _ov_chk_item(ov_elem_lf, "Show Stats  (Murk, Relics, Bought, etc.)",
                self._ov_show_stats_var, 1, 0,
                "Shows live counters in the HUD: Murk spent, relics scanned,\n"
                "relics bought, current iteration, and active mode.")
        # Row 1 of 2 — stats/counter elements (3 across)
        _ov_chk_item(ov_elem_lf, "Track Rolls  (God Roll / Good / Duds counters + Best Batches)",
                self._ov_show_rolls_var, 1, 1,
                "Tracks and displays per-session roll quality counts in the HUD:\n"
                "God Rolls (3/3), Good Hits (2/3), Duds (0–1/3), and the\n"
                "best-scoring iterations seen this session.")
        _ov_chk_item(ov_elem_lf, "Show Overflow Worker Hits",
                self._ov_show_overflow_var, 1, 2,
                "Lights up when a background overflow worker from a previous iteration\n"
                "finds a 2/3 or 3/3 hit.  Hidden when count is zero regardless of this setting.")
        # Row 2 of 2 — log panels (3 across, 3rd slot reserved)
        _ov_chk_item(ov_elem_lf, "Process Log",
                self._ov_show_proc_log_var, 2, 0,
                "The left log panel — shows bot phase events and actions.")
        _ov_chk_item(ov_elem_lf, "Relic Log",
                self._ov_show_relic_log_var, 2, 1,
                "The right log panel — shows per-relic OCR results.\n"
                "If only one log is enabled it expands to fill the full overlay width.")

        # Row 3 — Toggle Hotkey (sub-setting: disabled when overlay is off)
        _ov_hk_lbl1 = ttk.Label(ov_elem_lf, text="Toggle Hotkey:")
        _ov_hk_lbl1.grid(row=3, column=0, sticky="e", padx=(28, 4), pady=4)
        self._ov_hotkey_btn = ttk.Button(
            ov_elem_lf,
            text=f"Rec: {self._ov_hotkey_display}",
            command=self._set_ov_hotkey_dialog,
            width=10,
        )
        self._ov_hotkey_btn.grid(row=3, column=1, sticky="w", padx=(0, 8), pady=4)
        _Tooltip(self._ov_hotkey_btn,
                 "Press this key (default: F7) to toggle the overlay on/off without\n"
                 "interrupting the game or the bot.\n"
                 "Stats continue updating in the background while the overlay is hidden.\n\n"
                 "Click to record a different key.\n\n"
                 "Has no effect when Show HUD overlay is disabled.")
        self._ov_elem_widgets.extend([_ov_hk_lbl1, self._ov_hotkey_btn])

        # Row 4 — Matches Hotkey (sub-setting: disabled when overlay is off)
        _ov_hk_lbl2 = ttk.Label(ov_elem_lf, text="Matches Hotkey:")
        _ov_hk_lbl2.grid(row=4, column=0, sticky="e", padx=(28, 4), pady=4)
        self._matches_hotkey_btn = ttk.Button(
            ov_elem_lf,
            text=f"Rec: {self._matches_hotkey_display}",
            command=self._set_matches_hotkey_dialog,
            width=10,
        )
        self._matches_hotkey_btn.grid(row=4, column=1, sticky="w", padx=(0, 8), pady=4)
        _Tooltip(self._matches_hotkey_btn,
                 "Press this key (default: F8) to toggle the overlay between the\n"
                 "normal log view and the full-width Matched Relics panel.\n\n"
                 "Use this instead of clicking 'View Matches' so you never have\n"
                 "to move your mouse away from the game during a run.\n\n"
                 "Click to record a different key.\n\n"
                 "Has no effect when Show HUD overlay is disabled.")
        self._ov_elem_widgets.extend([_ov_hk_lbl2, self._matches_hotkey_btn])

        # Disable all element widgets when the overlay itself is off
        self._overlay_enabled_var.trace_add("write", self._on_overlay_enable_toggle)
        self._on_overlay_enable_toggle()

        # Low Performance Mode
        lpm_chk = ttk.Checkbutton(
            self.batch_frame,
            text="🐢 Low Performance Mode",
            variable=self._low_perf_mode_var,
            command=self._on_lpm_toggle,
        )
        lpm_chk.grid(row=9, column=2, columnspan=3, sticky="w", **pad)
        _Tooltip(lpm_chk,
                 "Applies conservative timing for slower systems or after extended runs\n"
                 "where the system has destabilised under load.\n\n"
                 "When enabled:\n"
                 "  • Phase 1 buy gap raised to 0.50 s base (dialog has more time to open)\n"
                 "  • Phase 4 initial settle raised to 2.0 s (Sell screen fully stabilises)\n"
                 "  • Brute Force Analysis disabled (reduces CPU / RAM pressure)\n"
                 "  • OCR limited to half of available CPU cores\n\n"
                 "Input gaps already scale automatically with observed game load time\n"
                 "(see [Adaptive] log entries). This mode raises the baseline floor\n"
                 "so the adaptive scaling starts from a safer starting point.")

        # Backlog Analysis
        backlog_chk = ttk.Checkbutton(
            self.batch_frame,
            text="📦 Backlog Analysis",
            variable=self._backlog_mode_var,
        )
        backlog_chk.grid(row=7, column=0, columnspan=5, sticky="w", **pad)
        _Tooltip(backlog_chk,
                 "Defers all OCR analysis until after the entire batch is complete.\n\n"
                 "During the run:\n"
                 "  • Screenshots are captured for each relic and saved to disk\n"
                 "  • No OCR is performed — zero CPU contention with the game\n"
                 "  • All phases (navigation, buying) run at full speed\n\n"
                 "After the run:\n"
                 "  • All saved screenshots are processed in one pass\n"
                 "  • Full analysis: hits, near-misses, Smart Analyze, All Hits folder\n"
                 "  • Game is not running during this phase — OCR gets all available CPU\n\n"
                 "Recommended for low-end systems where OCR causes input starvation.\n"
                 "Works alongside Low Performance Mode for maximum stability.")

        # ── Async ↔ Backlog mutual exclusion ─────────────────────────── #
        # These two modes are fundamentally incompatible.  Trying to enable
        # one while the other is active silently reverts the change and shows
        # a self-dismissing conflict tip for 5 seconds.
        def _conflict_tip(anchor_widget, message):
            """Show a self-dismissing warning near anchor_widget for 5 s."""
            tip = tk.Toplevel(self)
            tip.wm_overrideredirect(True)
            tip.wm_attributes("-topmost", True)
            tip.wm_geometry(
                f"+{anchor_widget.winfo_rootx() + 20}"
                f"+{anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 4}"
            )
            tk.Label(
                tip, text=message,
                background="#fff5b0", foreground="#333",
                relief="solid", borderwidth=1,
                wraplength=320, justify="left",
                font=("TkDefaultFont", 9),
            ).pack(ipadx=8, ipady=5)
            tip.after(5000, tip.destroy)

        def _on_async_toggle():
            if self._async_enabled_var.get() and self._backlog_mode_var.get():
                self._async_enabled_var.set(False)
                _conflict_tip(async_chk,
                               "Backlog Analysis is enabled — disable it to use Async Analysis.")

        def _on_backlog_toggle():
            if self._backlog_mode_var.get() and self._async_enabled_var.get():
                self._backlog_mode_var.set(False)
                _conflict_tip(backlog_chk,
                               "Async Analysis is enabled — disable it to use Backlog Analysis.")

        async_chk.config(command=_on_async_toggle)
        backlog_chk.config(command=_on_backlog_toggle)

        # Intermittent Backlog Analysis — sub-setting of Backlog Mode
        _ibl_frame = ttk.Frame(self.batch_frame)
        _ibl_frame.grid(row=8, column=0, columnspan=6, sticky="w",
                        padx=(28, 0), pady=(0, 2))

        _ibl_chk = ttk.Checkbutton(
            _ibl_frame,
            text="Intermittent Backlog Analysis",
            variable=self._intermittent_backlog_var,
        )
        _ibl_chk.grid(row=0, column=0, sticky="w")
        _Tooltip(_ibl_chk,
                 "Periodically pauses between iterations to drain the captured screenshot\n"
                 "queue before launching the next game session.\n\n"
                 "Instead of deferring ALL analysis to the very end, the bot will stop\n"
                 "after every N iterations, process all pending screenshots at full CPU\n"
                 "speed (no game running), then resume with the next iterations.\n\n"
                 "Benefits:\n"
                 "  • OCR gets 100% CPU during analysis breaks — faster per relic\n"
                 "  • No CPU competition at all during buy/scan phases\n"
                 "  • Results appear incrementally rather than only at the end\n\n"
                 "Requires Backlog Analysis to be enabled.")

        ttk.Label(_ibl_frame, text="   every").grid(row=0, column=1, sticky="w")
        _ibl_spin = ttk.Spinbox(
            _ibl_frame,
            from_=1, to=999, width=4,
            textvariable=self._intermittent_every_n_var,
        )
        _ibl_spin.grid(row=0, column=2, padx=(2, 2))
        ttk.Label(_ibl_frame, text="iteration(s)").grid(row=0, column=3, sticky="w")

        def _update_ibl_state(*_):
            _on = self._backlog_mode_var.get()
            _state = "normal" if _on else "disabled"
            _ibl_chk.config(state=_state)
            _ibl_spin.config(state=_state)
            if not _on:
                self._intermittent_backlog_var.set(False)

        self._backlog_mode_var.trace_add("write", _update_ibl_state)
        _update_ibl_state()   # initialise to current state

        # Hybrid GPU+CPU Backlog — sub-setting of Backlog Mode
        # GPU Acceleration toggle
        def _on_gpu_toggle(*_):
            from bot import relic_analyzer
            relic_analyzer.set_gpu_mode(self._gpu_accel_var.get())
            self._update_odds_viewer()
            _update_bf_gpu_lock()
            # Show/hide the "+1 GPU Worker" badge
            if self._gpu_accel_var.get():
                self._gpu_worker_lbl.grid()
            else:
                self._gpu_worker_lbl.grid_remove()

        gpu_chk = ttk.Checkbutton(
            self.batch_frame, text="🖥 GPU Acceleration (opt-in)",
            variable=self._gpu_accel_var,
            command=_on_gpu_toggle,
        )
        gpu_chk.grid(row=10, column=0, columnspan=2, sticky="w", **pad)
        _Tooltip(gpu_chk,
                 "Offloads OCR inference to your NVIDIA GPU (CUDA) instead of the CPU.\n"
                 "Adds exactly 1 dedicated GPU worker — CUDA inference does not benefit\n"
                 "from multiple workers competing for the same GPU context.\n\n"
                 "Speed: ~0.3 s/relic (GPU) vs ~3 s/relic (CPU) — ~10× faster.\n\n"
                 "When GPU Acceleration is on without Hybrid mode:\n"
                 "  • Only the GPU worker runs — Brute Force workers are ignored\n"
                 "  • Enable Hybrid GPU+CPU to run CPU workers alongside the GPU worker\n\n"
                 "Requirements:\n"
                 "  • NVIDIA GPU with CUDA support (GTX 10xx or newer)\n"
                 "  • PyTorch with CUDA installed (see Hardware panel below)\n\n"
                 "Leave OFF if you do not have an NVIDIA GPU or CUDA is not detected.\n"
                 "AMD and Intel GPUs are not supported.\n"
                 "GPU setting is saved in your profile.")

        # "+1 GPU Worker" badge — shown only when GPU Accel is enabled
        self._gpu_worker_lbl = ttk.Label(
            self.batch_frame, text="+1 GPU Worker",
            foreground="#7ec8f0",
        )
        self._gpu_worker_lbl.grid(row=10, column=2, columnspan=2, sticky="w", **pad)
        _Tooltip(self._gpu_worker_lbl,
                 "GPU Acceleration adds exactly 1 dedicated GPU worker to the pool.\n\n"
                 "EasyOCR CUDA inference serializes within one GPU context — extra\n"
                 "GPU workers fight over VRAM and slow each other down rather than\n"
                 "improving throughput.  1 GPU worker at ~0.3 s/relic is optimal.\n\n"
                 "To also run CPU workers alongside it, enable Hybrid GPU+CPU mode.")
        if not self._gpu_accel_var.get():
            self._gpu_worker_lbl.grid_remove()
        self._gpu_rec_lbl = ttk.Label(
            self.batch_frame,
            text="",
            foreground=theme.TEXT_MUTED,
        )
        self._gpu_rec_lbl.grid(row=10, column=4, columnspan=3, sticky="w", **pad)
        # Set recommendation label based on CUDA detection
        if self._hw_cuda_available:
            self._gpu_rec_lbl.configure(
                text=f"✓ Recommended — CUDA detected on {self._hw_gpu_name}",
                foreground="#7ec8f0",
            )
        elif self._hw_cuda_torch_installed:
            # CUDA torch files are present but torch.cuda.is_available() returned False.
            # Likely cause: _apply_gpu_upgrade() ran successfully but CUDA init still fails
            # (driver mismatch, missing system runtime, etc.). Show the actual error.
            _err_short = self._hw_cuda_error[:80] if self._hw_cuda_error else "unknown error"
            self._gpu_rec_lbl.configure(
                text=f"GPU torch installed — CUDA init failed: {_err_short}",
                foreground="#e0c050",
            )
        elif self._hw_cuda_error:
            self._gpu_rec_lbl.configure(
                text=f"CUDA unavailable: {self._hw_cuda_error[:80]}",
                foreground="#e09050",
            )
        else:
            self._gpu_rec_lbl.configure(
                text="No CUDA GPU detected — CPU mode only",
                foreground=theme.TEXT_MUTED,
            )

        # ── Install GPU Acceleration button ───────────────────────────── #
        # Enabled only when: NVIDIA GPU compatible (compute ≥ 6.1, driver ≥ 572.13)
        #                    AND CUDA is not already working.
        # Grayed out for: incompatible hardware, outdated drivers, or CUDA already installed.
        if self._hw_cuda_available:
            _ibtn_text  = "GPU Already Installed"
            _ibtn_state = "disabled"
            _ibtn_tip   = "CUDA is already available and working on this system."
        elif self._hw_cuda_torch_installed and self._gpu_eligible:
            # Files are present but CUDA failed — allow reinstall
            _ibtn_text  = "Reinstall GPU Acceleration"
            _ibtn_state = "normal"
            _ibtn_tip   = (
                f"GPU torch files are installed but CUDA initialization failed.\n"
                f"Click to reinstall PyTorch CUDA 12.6 for {self._gpu_eligible_name}.\n"
                f"RelicBot must be restarted after the install completes."
            )
        elif self._gpu_eligible:
            _ibtn_text  = "Install GPU Acceleration"
            _ibtn_state = "normal"
            _ibtn_tip   = (
                f"Downloads and installs PyTorch CUDA 12.6 for {self._gpu_eligible_name}.\n"
                f"Requires ~2.5 GB of disk space and an internet connection.\n"
                f"RelicBot must be restarted after the install completes."
            )
        else:
            # Not eligible — check whether it's a driver issue or hardware issue
            _driver_msg = "572.13"
            if (self._gpu_eligible_name and
                    "driver" in self._gpu_eligible_reason.lower()):
                _ibtn_text  = "Update Drivers to Install"
                _ibtn_state = "disabled"
                _ibtn_tip   = (
                    f"Compatible GPU detected ({self._gpu_eligible_name}) but your "
                    f"NVIDIA drivers are too old for CUDA 12.6.\n"
                    f"Please update your NVIDIA graphics drivers to version "
                    f"{_driver_msg} or newer, then restart RelicBot."
                )
            else:
                _ibtn_text  = "Not Available"
                _ibtn_state = "disabled"
                _ibtn_tip   = self._gpu_eligible_reason or "No compatible NVIDIA GPU detected."

        self._gpu_install_btn = ttk.Button(
            self.batch_frame,
            text=_ibtn_text,
            state=_ibtn_state,
            command=self._install_gpu_acceleration,
        )
        self._gpu_install_btn.grid(row=9, column=7, sticky="w", **pad)
        self._gpu_install_btn_tip = _Tooltip(self._gpu_install_btn, _ibtn_tip)

        # ── Hardware Recommendations ──────────────────────────────────── #
        _recs = self._get_hw_recommendations()
        hw_frame = ttk.LabelFrame(self.batch_frame, text="Recommended Settings for Your System")
        hw_frame.grid(row=11, column=0, columnspan=8, sticky="ew", **pad)

        ram_str  = f"{self._hw_ram_gb} GB" if self._hw_ram_gb else "unknown"
        cpu_str  = f"{self._hw_cpu_cores} logical cores" if self._hw_cpu_cores else "unknown"
        cuda_str = "CUDA available" if self._hw_cuda_available else "no CUDA"
        ttk.Label(
            hw_frame,
            text=(f"Detected:  {self._hw_gpu_name}  ({cuda_str})  |  "
                  f"RAM: {ram_str}  |  CPU: {cpu_str}\n"
                  f"Estimates based on hardware specs — results may vary."),
            foreground=theme.TEXT_MUTED, wraplength=820,
        ).grid(row=0, column=0, columnspan=6, sticky="w", **pad)

        def _rec_row(parent, grid_row, items):
            """Render a row of (label, rec_str, reason_str) triples."""
            for col, (lbl_text, rec, reason) in enumerate(items):
                ttk.Label(parent, text=lbl_text,
                          foreground=theme.TEXT_MUTED).grid(
                    row=grid_row, column=col * 3, sticky="e", padx=(8, 2), pady=2)
                color = "#7ec8f0" if rec not in ("OFF", "N/A", "?") else theme.TEXT_MUTED
                rec_lbl = ttk.Label(parent, text=rec, foreground=color)
                rec_lbl.grid(row=grid_row, column=col * 3 + 1, sticky="w", padx=(0, 4), pady=2)
                ttk.Label(parent, text=f"({reason})",
                          foreground=theme.TEXT_MUTED).grid(
                    row=grid_row, column=col * 3 + 2, sticky="w", padx=(0, 16), pady=2)
            return rec_lbl  # returns last one (used for GPU label reference)

        # Row 1: Brute Force | Workers | Async Analysis
        _rr = _recs
        _rec_row(hw_frame, 1, [
            ("⚡ Brute Force:",  _rr["brute"][0],   _rr["brute"][1]),
            ("Workers:",         _rr["workers_display"], "per RAM estimate"),
            ("⚑ Async Analysis:", _rr["async_"][0], _rr["async_"][1]),
        ])
        # Row 2: Smart Throttle | Excl. Analysis | GPU
        _last_gpu_lbl = None
        for col, (lbl_text, rec, reason) in enumerate([
            ("⚡ Smart Throttle:", _rr["smart_throttle"][0],    _rr["smart_throttle"][1]),
            ("⏸ Excl. Analysis:",  _rr["exclude_buy_phase"][0], _rr["exclude_buy_phase"][1]),
            ("🖥 GPU Accel:",       _rr["gpu"][0],               _rr["gpu"][1]),
        ]):
            ttk.Label(hw_frame, text=lbl_text,
                      foreground=theme.TEXT_MUTED).grid(
                row=2, column=col * 3, sticky="e", padx=(8, 2), pady=2)
            color = "#7ec8f0" if rec not in ("OFF", "N/A", "?") else theme.TEXT_MUTED
            _rl = ttk.Label(hw_frame, text=rec, foreground=color)
            _rl.grid(row=2, column=col * 3 + 1, sticky="w", padx=(0, 4), pady=2)
            ttk.Label(hw_frame, text=f"({reason})",
                      foreground=theme.TEXT_MUTED).grid(
                row=2, column=col * 3 + 2, sticky="w", padx=(0, 16), pady=2)
            if lbl_text.startswith("🖥"):
                self._hw_gpu_rec_lbl = _rl
        # Row 3: LPM | Backlog Analysis | Intermittent Backlog
        _rec_row(hw_frame, 3, [
            ("🐢 Low Perf Mode:",     _rr["lpm"][0],         _rr["lpm"][1]),
            ("📦 Backlog Analysis:",  _rr["backlog"][0],     _rr["backlog"][1]),
            ("⏸ Intermittent:",       _rr["intermittent"][0], _rr["intermittent"][1]),
        ])
        # Row 4: Use Together | Exclude These Modes
        _compat_frame = ttk.Frame(hw_frame)
        _compat_frame.grid(row=4, column=0, columnspan=9, sticky="ew", padx=8, pady=(4, 2))
        ttk.Label(_compat_frame, text="Use Together:",
                  foreground=theme.TEXT_MUTED).pack(side="left", padx=(0, 4))
        ttk.Label(_compat_frame, text=_recs["use_together"],
                  foreground="#7ec8f0").pack(side="left", padx=(0, 24))
        ttk.Label(_compat_frame, text="Exclude Together:",
                  foreground=theme.TEXT_MUTED).pack(side="left", padx=(0, 4))
        ttk.Label(_compat_frame, text=_recs["exclude_modes"],
                  foreground="#e09050").pack(side="left")

        # Row 5: Enable Recommended Settings button + calibration status
        _btn_frame = ttk.Frame(hw_frame)
        _btn_frame.grid(row=5, column=0, columnspan=9, sticky="ew", padx=8, pady=(4, 2))
        _apply_btn = ttk.Button(
            _btn_frame, text="✔ Enable Recommended Settings",
            command=self._apply_recommended_settings,
        )
        _apply_btn.pack(side="left", padx=(0, 16))
        _Tooltip(_apply_btn,
                 "Automatically applies all recommended settings for your hardware.\n"
                 "Input sequences are never modified.\n"
                 "You can adjust individual settings afterwards.")
        self._calib_status_lbl = ttk.Label(
            _btn_frame, text="", foreground=theme.TEXT_MUTED)
        self._calib_status_lbl.pack(side="left")
        _Tooltip(self._calib_status_lbl,
                 "Gap multiplier is adjusted automatically after each iteration.\n"
                 "Rises when Phase 0/1 retries or CPU stress is detected;\n"
                 "falls slowly when every iteration runs perfectly clean.\n"
                 "Saved to relicbot_calibration.json between sessions.")

        # Show calibration status if loaded
        _cal2 = self._load_calibration()
        if _cal2.get("machine_id") == self._get_machine_id() and _cal2.get("perf_mult"):
            _pm = _cal2["perf_mult"]
            self._calib_status_lbl.configure(
                text=f"Auto-calibration: gap mult {_pm:.2f}× (loaded from last session)",
                foreground="#7ec8f0")
        else:
            self._calib_status_lbl.configure(
                text="Auto-calibration: will calibrate on first run",
                foreground=theme.TEXT_MUTED)

        # ── Setting Stats ─────────────────────────────────────────────── #
        # Shows active mode effects and flags conflicting settings.
        # Updated by _update_odds_viewer whenever settings change.
        _ss_frame = ttk.LabelFrame(inner, text="Setting Stats")
        _ss_frame.grid(row=7, column=0, sticky="ew", **pad)
        _ss_bg = self.cget("background")
        self._setting_stats_txt = tk.Text(
            _ss_frame, height=4, state="disabled",
            background=_ss_bg, foreground="#7ec8f0",
            relief="flat", borderwidth=0, highlightthickness=0,
            font=("TkDefaultFont", 9), wrap="word",
        )
        self._setting_stats_txt.pack(fill="x", padx=8, pady=(4, 6))
        self._setting_stats_txt.tag_configure("muted",   foreground=theme.TEXT_MUTED)
        self._setting_stats_txt.tag_configure("active",  foreground="#7ec8f0")
        self._setting_stats_txt.tag_configure("warn",    foreground="#e05050")
        self._setting_stats_txt.tag_configure("heading", foreground=theme.TEXT_MUTED)

        # ── Odds Viewer ──────────────────────────────────────────────── #
        odds_viewer = ttk.LabelFrame(inner, text="Odds Viewer")
        odds_viewer.grid(row=8, column=0, sticky="ew", **pad)

        ov_top = ttk.Frame(odds_viewer)
        ov_top.pack(fill="x", padx=8, pady=(6, 2))

        ttk.Label(ov_top, text="Relics per iteration:").pack(side="left")
        self._ov_n_var = tk.IntVar(value=1)
        ttk.Button(ov_top, text="◀", width=2,
                   command=lambda: (self._ov_n_var.set(max(1, self._ov_n_var.get() - 1)),
                                    self._update_odds_viewer())
                   ).pack(side="left", padx=(8, 0))
        self._ov_slider = ttk.Scale(
            ov_top, from_=1, to=500, orient="horizontal",
            variable=self._ov_n_var, length=260,
            command=lambda _: self._update_odds_viewer(),
        )
        self._ov_slider.pack(side="left", padx=2)
        self.after(0, lambda: self._ov_slider.set(1))
        self._ov_key_repeat = None
        self._ov_slider.bind("<Left>",  lambda e: self._slider_key_press(-1))
        self._ov_slider.bind("<Right>", lambda e: self._slider_key_press(1))
        self._ov_slider.bind("<KeyRelease-Left>",  lambda e: self._slider_key_release())
        self._ov_slider.bind("<KeyRelease-Right>", lambda e: self._slider_key_release())
        ttk.Button(ov_top, text="▶", width=2,
                   command=lambda: (self._ov_n_var.set(min(500, self._ov_n_var.get() + 1)),
                                    self._update_odds_viewer())
                   ).pack(side="left", padx=(0, 4))
        self._ov_n_lbl = ttk.Label(ov_top, text="1", width=5)
        self._ov_n_lbl.pack(side="left")

        # Selectable read-only result display (tk.Text allows mouse selection + Ctrl+C)
        self._ov_result_txt = tk.Text(
            odds_viewer, height=6, state="disabled",
            background=_ss_bg, foreground="#90c890",
            relief="flat", borderwidth=0, highlightthickness=0,
            font=("TkDefaultFont", 9), wrap="word",
        )
        self._ov_result_txt.pack(fill="x", anchor="w", padx=8, pady=(0, 2))
        self._ov_result_txt.tag_configure("normal", foreground="#90c890")
        self._ov_result_txt.tag_configure("muted",  foreground=theme.TEXT_MUTED)

        ttk.Label(
            odds_viewer,
            text="Ideal conditions (no lag, no crashes).  "
                 "Rolling: ~2.0 s/relic buy+settle + ~0.30 s/relic nav (LPM: 2.5 s + 0.45 s).  "
                 "OCR: ~3.0 s/relic CPU · ~0.3 s GPU · Hybrid combines GPU+CPU throughput · GPU Always Analyze suppresses CPU workers (GPU only).  "
                 "Async overlaps OCR with game.  Backlog defers OCR until after the run.  Intermittent drains every N iterations.",
            foreground=theme.TEXT_MUTED, wraplength=760,
        ).pack(anchor="w", padx=8, pady=(0, 6))

        # Wire odds updates from relic_builder and all relevant settings
        self.relic_builder._on_odds_changed = lambda p: self._update_odds_viewer()
        for _ov_var in (self._low_perf_mode_var, self._parallel_enabled_var,
                        self._async_enabled_var, self._parallel_workers_var,
                        self._gpu_accel_var, self._backlog_mode_var,
                        self._intermittent_backlog_var, self._hybrid_var,
                        self._gpu_always_analyze_var, self._intermittent_every_n_var):
            _ov_var.trace_add("write", lambda *_: self._update_odds_viewer())

        # ── Bot Control ─────────────────────────────────────────────── #
        ctrl_frame = ttk.LabelFrame(inner, text="Bot Control")
        ctrl_frame.grid(row=9, column=0, sticky="ew", **pad)

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
        log_frame.grid(row=10, column=0, sticky="ew", **pad)
        self.log_box = scrolledtext.ScrolledText(
            log_frame, height=10, width=82, state="disabled", wrap="word"
        )
        theme.style_text(self.log_box)
        self.log_box.grid(row=0, column=0, **pad)

        # ── Resources ───────────────────────────────────────────────── #
        res_frame = ttk.LabelFrame(inner, text="Resources")
        res_frame.grid(row=11, column=0, sticky="ew", **pad)

        ttk.Button(
            res_frame,
            text="Relic Draw Rate Mathematics",
            command=self._open_draw_rate_doc,
        ).grid(row=0, column=0, **pad)

        ttk.Label(
            res_frame,
            text="In-depth probability analysis of relic passive draw rates, "
                 "category exclusion mechanics, and odds calculations.",
            foreground=theme.TEXT_MUTED,
            font=("Segoe UI", 8),
            wraplength=520,
            justify="left",
        ).grid(row=0, column=1, sticky="w", padx=(0, 8))

        # ── Credit ──────────────────────────────────────────────────── #
        ttk.Label(inner, text="Made by Pulgo",
                  foreground=theme.TEXT_MUTED,
                  font=("Segoe UI", 8)).grid(
            row=10, column=0, sticky="e", padx=12, pady=(0, 4)
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
                    "Phase 0 — Setup  (played once per iteration)\n"
                    "Navigates from Roundtable Hold to the Relic Rites merchant buy screen.\n\n"
                    "Inputs (default recording):\n"
                    "  • M         — opens the pause / world-map menu\n"
                    "  • DOWN ×6   — scrolls through menu options to the merchant / shop entry\n"
                    "  • F         — confirms and opens the shop\n"
                    "  (bot pauses here — OCR waits up to 30 s for 'Small Jar Bazaar' text)\n"
                    "  • UP ×1     — moves up to the Relic Rites item in the shop list\n"
                    "  • RIGHT ×2  — selects the correct relic type column\n\n"
                    "Why the timing matters:\n"
                    "  Each DOWN press must land after the previous menu animation completes.\n"
                    "  If a press fires too early it registers in the wrong layer and the bot\n"
                    "  ends up in a different menu (e.g. Collector Signboard, Change Garb).\n"
                    "  The bot adds adaptive extra delay after each key to compensate for\n"
                    "  slower systems or late-batch degradation.\n\n"
                    "\u26a0  If you don't have the DLC or not all shops are unlocked,\n"
                    "    RE-RECORD this phase to match your exact menu layout.\n"
                    "    Count the DOWN presses carefully — one too many or too few\n"
                    "    will land on the wrong menu option every iteration."
                ),
                False,
            ),
            (
                "Buy Loop",
                "Repeats — buys one batch of 10 relics. Stops on 'Insufficient murk' popup.",
                (
                    "Phase 1 — Buy Loop  (repeated until murk runs out)\n"
                    "Purchases one batch of 10 relics. The bot replays this once per batch.\n\n"
                    "Inputs (default recording):\n"
                    "  • F      — opens the purchase quantity dialog\n"
                    "  • DOWN   — selects ×10 (maximum quantity)\n"
                    "  • F      — confirms the purchase\n"
                    "  • F      — closes the purchase-complete / confirmation dialog\n\n"
                    "Why the timing matters:\n"
                    "  The gap between F (opens dialog) and DOWN is critical.\n"
                    "  The purchase dialog needs time to fully appear before DOWN fires.\n"
                    "  If DOWN fires too early — while the dialog is still animating —\n"
                    "  it falls through to the shop navigation layer and moves the cursor\n"
                    "  to a random shop item instead. The bot then cycles through wrong\n"
                    "  items for the rest of the iteration (the desync bug).\n"
                    "  The bot preserves the original recorded timing (~500 ms F-to-DOWN)\n"
                    "  and adds adaptive extra delay on stressed systems.\n\n"
                    "Works for all setups — no re-recording needed."
                ),
                True,
            ),
            (
                "Relic Rites Nav",
                "Plays once — opens the Relic Rites review screen (ESC recovery → Map → down × 3 → F).",
                (
                    "Phase 2 — Relic Rites Nav  (played once after buying)\n"
                    "After buying relics, closes the shop and opens the Relic Rites\n"
                    "review / sell screen.\n\n"
                    "How it works:\n"
                    "  The bot uses OCR-verified ESC recovery to close the shop: it presses\n"
                    "  ESC until the Equipment menu is detected, then presses ESC once more\n"
                    "  to return to the game world. Only after that is confirmed does it fire:\n"
                    "  • M        — opens the pause menu\n"
                    "  • DOWN ×3  — scrolls to the Relic Rites entry in the menu\n"
                    "  • F        — opens the Relic Rites screen\n\n"
                    "The ESC you record at the start of this phase is used only as a\n"
                    "placeholder — the bot replaces it with the full OCR-verified sequence.\n"
                    "The M + DOWN×3 + F timing is preserved from your recording.\n\n"
                    "\u26a0  If your menu has a different item order (e.g. different number of\n"
                    "    options between ESC and Relic Rites), RE-RECORD this phase.\n"
                    "    Test with '▶ Test' and watch that it lands on the Relic Rites screen."
                ),
                False,
            ),
            (
                "Navigate to Sell",
                "Automatic — OCR detects the active character tab, then presses F2 exactly N times.",
                (
                    "Phase 3 — Navigate to Sell  (fully automatic, no recording needed)\n"
                    "After the Relic Rites screen opens, navigates to the Sell tab.\n\n"
                    "How it works:\n"
                    "  1. Takes a screenshot and identifies the active character tab via OCR\n"
                    "     (reads the tab bar: Wylder, Guardian, Duchess … Undertaker, Sell).\n"
                    "  2. Calculates how many F2 presses are needed to reach Sell:\n"
                    "     Wylder = 10 presses, Guardian = 9, … Undertaker = 1, Sell = 0.\n"
                    "  3. Presses F2 the exact number of times.\n"
                    "  4. Verifies the Sell page is open via OCR. If not, runs a safety\n"
                    "     F2 recovery loop (up to 15 extra presses) to self-correct.\n\n"
                    "Why F2:\n"
                    "  F2 is the default 'next tab' key in Elden Ring Nightreign.\n"
                    "  The bot assumes default keybinds. If you've rebound F2, this\n"
                    "  phase will fail to navigate to the correct tab.\n\n"
                    "Change Garb recovery:\n"
                    "  Phase 2 (ESC → M → DOWN×3 → F) can land on 'Change Garb'\n"
                    "  if one DOWN input is dropped during the menu animation.\n"
                    "  Change Garb is one position above Relic Rites in the menu.\n"
                    "  Phase 3 detects 'Change Garb' text immediately at startup\n"
                    "  and triggers ESC recovery → Phase 0 → Phase 2 before\n"
                    "  entering the sell scan, saving the bought relics.\n\n"
                    "No recording required — adapts automatically to any starting tab."
                ),
                False,
            ),
            (
                "Review Step",
                "Repeats — advances to the next relic. Stops after reviewing all purchased relics.",
                (
                    "Phase 4 — Review Step  (repeated once per relic)\n"
                    "Advances through the relic list on the Sell screen to capture each\n"
                    "relic's name and passives via OCR.\n\n"
                    "Inputs (default recording):\n"
                    "  • RIGHT arrow — moves to the next relic in the list\n\n"
                    "How many times:\n"
                    "  The bot repeats this (murk spent ÷ relic cost) times — one press\n"
                    "  per relic. Relics are pre-loaded on the Sell screen so no wait is\n"
                    "  needed between advances; the list is already fully rendered.\n\n"
                    "Why the initial settle matters:\n"
                    "  Before the first press, the bot waits for the Sell screen to finish\n"
                    "  its opening animation (default 1 s, scaled up on degraded systems).\n"
                    "  Without this wait, the first RIGHT press can be swallowed, causing\n"
                    "  the bot to capture relic 1 twice and miss relic N.\n\n"
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

        # ── Auto-only phases: Load Skip and ESC Recovery ─────────────── #
        # These phases are handled automatically by the bot and cannot be
        # re-recorded, but are shown here so advanced users understand what
        # the bot is doing during those stages.

        _auto_tabs = [
            (
                "Load Skip (−0.5)",
                "Automatic — spams F during game load to skip title screens.",
                (
                    "Phase \u22120.5 — Load Skip  (fully automatic, no recording needed)\n"
                    "After each game launch, spams the confirm key (F) to skip title screens\n"
                    "and get into the game world as quickly as possible.\n\n"
                    "How it works:\n"
                    "  1. Bot waits up to 150 s for the game process to appear and its\n"
                    "     window to gain focus (using ctypes — no subprocess).\n"
                    "  2. Once the window is detected, F is spammed at 0.15 s intervals\n"
                    "     in 9 s bursts to advance through loading and title screens.\n"
                    "  3. After each burst, the bot checks whether the game is loaded enough\n"
                    "     to start Phase 0 navigation. If not, it spams another 9 s burst.\n"
                    "  4. If the game doesn't load within the maximum wait, the iteration\n"
                    "     is aborted and the bot retries from scratch.\n\n"
                    "Why F is hardcoded:\n"
                    "  F is the default confirm / interact key in Elden Ring Nightreign.\n"
                    "  Phase 0, Phase 1, and Phase 2 also all rely on F as the confirm key.\n"
                    "  The entire bot assumes default keybinds — if you've rebound confirm\n"
                    "  to a different key, the bot will not work correctly.\n\n"
                    "This phase is not re-recordable. It is hardcoded to work with default\n"
                    "Elden Ring Nightreign keybindings."
                ),
            ),
            (
                "ESC Recovery",
                "Automatic — presses ESC to return to the game screen when navigation goes wrong.",
                (
                    "ESC Recovery  (fully automatic, built into Phase 0 and Phase 2)\n"
                    "When the bot detects it has navigated to the wrong menu or screen,\n"
                    "it presses ESC to return to the main game world, then re-runs the\n"
                    "appropriate phase from scratch.\n\n"
                    "When it triggers:\n"
                    "  • Phase 0: the highlighted shop item does not match the expected\n"
                    "    relic type after navigation (bot landed on wrong item or menu).\n"
                    "  • Phase 2: the Relic Rites screen did not open after navigation\n"
                    "    (bot ended up in the wrong menu, e.g. Change Garb).\n"
                    "  • Either phase exceeds its maximum retry attempts.\n\n"
                    "How it works:\n"
                    "  1. Presses ESC to close the current menu / return to game world.\n"
                    "  2. Waits 0.5 s for the menu-close animation to complete.\n"
                    "  3. Runs a full OCR check to confirm the main game screen is visible.\n"
                    "  4. Re-runs Phase 0 (or Phase 2) from the beginning.\n"
                    "  5. If recovery fails after the maximum attempt count, the iteration\n"
                    "     is aborted and the batch resets for the next iteration.\n\n"
                    "This phase is not re-recordable — ESC is a single fixed keypress\n"
                    "used universally across all menus in the game."
                ),
            ),
        ]
        for auto_title, auto_hint, auto_tooltip in _auto_tabs:
            tab = ttk.Frame(nb)
            nb.add(tab, text=auto_title)
            hint_lbl = ttk.Label(tab, text=auto_hint, foreground=theme.TEXT_MUTED)
            hint_lbl.grid(row=0, column=0, sticky="w", padx=6, pady=2)
            _Tooltip(hint_lbl, auto_tooltip)
            ttk.Label(
                tab,
                text="This phase is handled automatically by the bot and cannot be re-recorded.",
                foreground=theme.TEXT_MUTED,
            ).grid(row=1, column=0, padx=6, pady=(0, 4), sticky="w")

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

        # Load safe buy alternative (F→DOWN→F, no extra F press)
        _alt_path = os.path.join(self._SEQ_DIR, "phase1_buy_alt.json")
        if os.path.exists(_alt_path):
            try:
                self.recorder.load(_alt_path)
                self._phase1_alt_events = list(self.recorder.events)
                self._log(f"Auto-loaded Phase 1 alt (safe buy): {len(self._phase1_alt_events)} events")
            except Exception as e:
                self._log(f"WARNING: Failed to load phase1_buy_alt.json: {e}")

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
        self.relic_builder.set_relic_context(rtype, self._get_allowed_colors())
        # Curse Filter is only relevant for Deep of Night — hide it in Normal mode
        if hasattr(self, "_curse_frame"):
            if rtype == "night":
                self._curse_frame.grid()
            else:
                self._curse_frame.grid_remove()
        self._update_curse_odds()
        self._update_odds_viewer()

    def _log_screen_resolution(self):
        """Log detected screen resolution in a background thread to avoid blocking mainloop."""
        def _query():
            try:
                from bot.screen_capture import get_screen_size
                w, h = get_screen_size()
                msg = (
                    f"Screen resolution detected: {w}×{h}. "
                    f"Relic panel crop: left={int(w*0.45)}px, top={int(h*0.65)}px "
                    f"→ {w - int(w*0.45)}×{h - int(h*0.65)}px region. "
                    f"Run in borderless or fullscreen for best results."
                )
            except Exception as e:
                msg = f"Screen resolution check failed: {e}"
            self.after(0, lambda: self._log(msg))
        threading.Thread(target=_query, daemon=True).start()

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

    def _on_overlay_enable_toggle(self, *_) -> None:
        """Gray out overlay element widgets when the overlay is disabled."""
        state = "normal" if self._overlay_enabled_var.get() else "disabled"
        for w in self._ov_elem_widgets:
            try:
                w.configure(state=state)
            except Exception:
                pass

    def _get_ov_settings(self) -> dict:
        return {
            "show_stats":       self._ov_show_stats_var.get(),
            "show_rolls":       self._ov_show_rolls_var.get(),
            "show_overflow":    self._ov_show_overflow_var.get(),
            "show_process_log": self._ov_show_proc_log_var.get(),
            "show_relic_log":   self._ov_show_relic_log_var.get(),
        }

    def _on_ov_settings_change(self) -> None:
        """Push overlay element settings to the live overlay (if running)."""
        if self._overlay:
            self._overlay.apply_settings(self._get_ov_settings())

    def _on_lpm_toggle(self) -> None:
        """Apply or remove Low Performance Mode preset."""
        if self._low_perf_mode_var.get():
            self._parallel_enabled_var.set(False)
            self._on_parallel_toggle()
            self._log(
                "[Low Performance Mode] ON — Phase 1 gap base 0.50 s, "
                "Phase 4 initial settle 2.0 s, Brute Force disabled, "
                "OCR limited to half CPU cores."
            )
            # Recommend GPU Acceleration if the system has an eligible GPU
            # but hasn't installed CUDA torch yet — GPU offloads OCR entirely,
            # making LPM unnecessary on systems with a capable GPU.
            if (self._gpu_eligible
                    and not self._hw_cuda_available
                    and not self._hw_cuda_torch_installed):
                self._log(
                    f"[GPU Recommendation] Compatible GPU detected "
                    f"({self._gpu_eligible_name}) — consider installing "
                    f"GPU Acceleration in Settings to offload OCR from the "
                    f"CPU entirely. This will eliminate input starvation on "
                    f"this system."
                )
        else:
            self._log("[Low Performance Mode] OFF — standard timing.")

    def _on_parallel_toggle(self):
        """Enable/disable the workers spinbox based on the Brute Force checkbox.

        Spinbox is always disabled when GPU is on without Hybrid — in that mode
        the GPU worker runs alone and CPU worker count is ignored.
        """
        _gpu_locked = (self._gpu_accel_var.get()
                       and not self._hybrid_var.get())
        if _gpu_locked:
            state = "disabled"
        else:
            state = "normal" if self._parallel_enabled_var.get() else "disabled"
        self._parallel_spin.config(state=state)
        self._update_ram_label()

    def _update_ram_label(self):
        """Update the RAM + CPU core estimate label next to the workers spinbox."""
        if not self._parallel_enabled_var.get():
            self._ram_label_var.set("")
            return
        try:
            w = int(self._parallel_workers_var.get())
        except (ValueError, tk.TclError):
            self._ram_label_var.set("")
            return
        mb         = w * 200
        total_cpus = self._hw_cpu_cores or 0
        cpu_str    = f"  {w}/{total_cpus} cores" if total_cpus else ""
        if w >= 4:
            self._ram_label_var.set(f"~{mb} MB RAM{cpu_str} — needs 16 GB+ ⚠")
            self._ram_label.configure(foreground="#c0392b")
        elif w >= 3:
            self._ram_label_var.set(f"~{mb} MB RAM{cpu_str} ⚠")
            self._ram_label.configure(foreground="#d4a843")
        else:
            self._ram_label_var.set(f"~{mb} MB RAM{cpu_str}")
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
            "batch_limit_type": self.batch_limit_type.get(),
            "batch_limit": self.batch_limit_var.get(),
            "batch_output": self.batch_output_var.get(),
            "relic_type": self.relic_type_var.get(),
            "hotkey_str": self._hotkey_str,
            "hotkey_display": self._hotkey_display,
            "blocked_curses": list(self._blocked_curses_list),
            "excluded_passives":      list(self._excluded_passives_list),
            "save_exclusion_matches": self._save_exclusion_matches_var.get(),
            "allowed_colors": self._get_allowed_colors(),
            "criteria": self.relic_builder.get_state(),
            "parallel_enabled": self._parallel_enabled_var.get(),
            "parallel_workers": self._parallel_workers_var.get(),
            "async_enabled":      self._async_enabled_var.get(),
            "smart_throttle":     self._smart_throttle_var.get(),
            "exclude_buy_phase":  self._exclude_buy_phase_var.get(),
            "smart_analyze":    self._smart_analyze_var.get(),
            "gpu_accel": self._gpu_accel_var.get(),
            "low_perf_mode": self._low_perf_mode_var.get(),
            "backlog_mode":              self._backlog_mode_var.get(),
            "intermittent_backlog":      self._intermittent_backlog_var.get(),
            "intermittent_every_n":      self._intermittent_every_n_var.get(),
            "hybrid":                    self._hybrid_var.get(),
            "gpu_always_analyze":        self._gpu_always_analyze_var.get(),
            "overlay_enabled":      self._overlay_enabled_var.get(),
            "ov_show_stats":        self._ov_show_stats_var.get(),
            "ov_show_rolls":        self._ov_show_rolls_var.get(),
            "ov_show_overflow":     self._ov_show_overflow_var.get(),
            "ov_show_process_log":  self._ov_show_proc_log_var.get(),
            "ov_show_relic_log":    self._ov_show_relic_log_var.get(),
            "ov_hotkey_str":        self._ov_hotkey_str,
            "ov_hotkey_display":    self._ov_hotkey_display,
            "matches_hotkey_str":   self._matches_hotkey_str,
            "matches_hotkey_display": self._matches_hotkey_display,
        }

    def _dict_to_profile(self, data: dict):
        _default_backup = os.path.join(_REPO_ROOT, "save_backups")
        _default_output = os.path.join(_REPO_ROOT, "batch_output")
        self.save_path_var.set(data.get("save_path", ""))
        self.backup_path_var.set(data.get("backup_folder", _default_backup))
        self.game_exe_var.set(data.get("game_executable", ""))
        self.batch_limit_type.set(data.get("batch_limit_type", "loops"))
        self.batch_limit_var.set(str(data.get("batch_limit", "20")))
        self.batch_output_var.set(data.get("batch_output", _default_output))
        # Input sequences (phase_events) are intentionally NOT loaded from profiles.
        # Sequences are recorded independently and must not be overwritten by profile
        # switches. If a user has recorded sequences they want to keep, they stay as-is.
        self.relic_type_var.set(data.get("relic_type", "night"))
        self._on_relic_type_change()
        self._parallel_enabled_var.set(data.get("parallel_enabled", False))
        self._parallel_workers_var.set(data.get("parallel_workers", 2))
        self._async_enabled_var.set(data.get("async_enabled", False))
        self._smart_throttle_var.set(data.get("smart_throttle", False))
        self._exclude_buy_phase_var.set(data.get("exclude_buy_phase", False))
        self._smart_analyze_var.set(data.get("smart_analyze", False))
        self._gpu_accel_var.set(data.get("gpu_accel", False))
        self._low_perf_mode_var.set(data.get("low_perf_mode", False))
        self._backlog_mode_var.set(data.get("backlog_mode", False))
        self._intermittent_backlog_var.set(data.get("intermittent_backlog", False))
        self._intermittent_every_n_var.set(data.get("intermittent_every_n", 5))
        # "hybrid" supersedes the old per-mode keys; fall back for old profiles
        _hybrid_val = data.get("hybrid",
                               data.get("async_hybrid", False)
                               or data.get("backlog_hybrid", False))
        self._hybrid_var.set(_hybrid_val)
        self._gpu_always_analyze_var.set(data.get("gpu_always_analyze", False))
        self._on_parallel_toggle()
        # Apply GPU setting immediately so the analyzer uses the correct mode
        from bot import relic_analyzer as _ra
        _ra.set_gpu_mode(self._gpu_accel_var.get())
        if "hotkey_str" in data:
            self._hotkey_str = data["hotkey_str"]
            self._hotkey_display = data.get("hotkey_display", self._hotkey_str.replace("Key.", "").upper())
            self._hotkey_btn.config(text=f"Rec Hotkey: {self._hotkey_display}")
            self._start_global_hotkey_listener()
        if "ov_hotkey_str" in data:
            self._ov_hotkey_str     = data["ov_hotkey_str"]
            self._ov_hotkey_display = data.get("ov_hotkey_display",
                                               self._ov_hotkey_str.replace("Key.", "").upper())
            self._ov_hotkey_btn.config(text=f"Rec: {self._ov_hotkey_display}")
            self._start_global_hotkey_listener()
        if "matches_hotkey_str" in data:
            self._matches_hotkey_str     = data["matches_hotkey_str"]
            self._matches_hotkey_display = data.get("matches_hotkey_display",
                                                    self._matches_hotkey_str.replace("Key.", "").upper())
            self._matches_hotkey_btn.config(text=f"Rec: {self._matches_hotkey_display}")
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
        if "excluded_passives" in data:
            self._excl_clear()
            for item in data["excluded_passives"]:
                if item and item not in self._excluded_passives_list:
                    self._excluded_passives_list.append(item)
                    self._excluded_lb.insert("end", item)
            # Sync dormant checkbox: checked if every dormant power is in the exclusion list
            from bot.passives import UI_CATEGORIES as _UCATS
            _dormant = _UCATS.get("Dormant Powers", [])
            self._excl_dormant_var.set(
                bool(_dormant) and all(d in self._excluded_passives_list for d in _dormant if d)
            )
        self._save_exclusion_matches_var.set(data.get("save_exclusion_matches", False))
        if "allowed_colors" in data:
            saved = data["allowed_colors"]
            for color, var in self._color_vars.items():
                var.set(color in saved)
        # gem images follow relic_type — sync after relic_type is loaded
        self._gem_mode_var.set("don" if self.relic_type_var.get() == "night" else "normal")
        self._refresh_gem_images()
        if "criteria" in data:
            self.relic_builder.set_state(data["criteria"])
        # Overlay settings
        self._overlay_enabled_var.set(data.get("overlay_enabled", True))
        self._ov_show_stats_var.set(data.get("ov_show_stats", True))
        self._ov_show_rolls_var.set(data.get("ov_show_rolls", True))
        self._ov_show_overflow_var.set(data.get("ov_show_overflow", True))
        self._ov_show_proc_log_var.set(data.get("ov_show_process_log", True))
        self._ov_show_relic_log_var.set(data.get("ov_show_relic_log", True))
        self._on_overlay_enable_toggle()

    def _auto_load_last_profile(self):
        """On startup, silently load the last-used profile if it still exists."""
        try:
            with open(_LAST_PROFILE_FILE, "r", encoding="utf-8") as f:
                name = f.read().strip()
            if not name:
                return
            path = self._profile_path(name)
            if not os.path.exists(path):
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._dict_to_profile(data)
            self._profile_var.set(name)
            self._log(f"Auto-loaded last profile: '{name}'")
        except Exception:
            pass  # No last profile or corrupt file — start with defaults

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
            try:
                os.makedirs(_PROFILES_DIR, exist_ok=True)
                with open(_LAST_PROFILE_FILE, "w", encoding="utf-8") as _lf:
                    _lf.write(name)
            except Exception:
                pass
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
            self._profile_var.set(name)
            self._log(f"Profile '{name}' saved.")
            try:
                with open(_LAST_PROFILE_FILE, "w", encoding="utf-8") as _lf:
                    _lf.write(name)
            except Exception:
                pass
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
        return len(_pids_for_exe(exe_name)) > 0

    def _close_game(self) -> bool:
        exe_path = self.game_exe_var.get().strip()
        if not exe_path:
            return True
        exe_name = os.path.basename(exe_path)
        if not self._is_game_running(exe_name):
            self._log("Game already not running — applying close buffer before relaunch…")
            time.sleep(5.0)
            return True
        self._log(f"Closing game ({exe_name})…")
        _kill_exe(exe_name)
        for _ in range(120):  # wait up to 60 s
            time.sleep(0.5)
            if not self.bot_running:
                return False
            if not self._is_game_running(exe_name):
                self._log("Game closed — waiting for cleanup…")
                time.sleep(5.0)
                return True
        self._log("WARNING: Game did not close within 60s.")
        return False

    _STEAM_APP_ID = "2622380"

    def _open_draw_rate_doc(self):
        path = os.path.join(_REPO_ROOT, "docs", "Relic Draw Rate Mathematics.txt")
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showerror("File Not Found",
                                 f"Could not locate:\n{path}")

    def _launch_game(self):
        self._log(f"Launching via Steam (App ID: {self._STEAM_APP_ID})…")
        subprocess.Popen(
            ["explorer.exe", f"steam://rungameid/{self._STEAM_APP_ID}"],
            close_fds=True
        )

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

        Attempts to focus the game window first so ESC inputs land in the game
        rather than the desktop or another application.

        Each ESC press is followed by a 0.5 s settle delay and a full OCR check.
        The next press fires only after the analysis completes — recovery speed
        is proportional to actual UI transition time rather than a fixed timer.

        Works regardless of how many menus deep the bot is stuck in (1–3 ESCs
        typically needed). Times out after 45 s.

        Returns True on success, False on timeout.
        """
        _exe = os.path.basename(self.game_exe_var.get().strip())
        if _exe:
            self._focus_game_window(_exe, timeout=3.0)
        self._log("[Recovery] ESC recovery — pressing ESC until Equipment menu appears…")
        deadline = time.time() + 45
        while time.time() < deadline:
            if not self.bot_running:
                return False
            # Re-focus before every ESC tap — a notification or alt-tab between
            # iterations would otherwise send ESC to the wrong window.
            if _exe:
                self._focus_game_window(_exe, timeout=1.0)
            self.player.tap("Key.esc")
            time.sleep(0.5)   # let UI transition settle before capturing
            _ocr_t0 = time.perf_counter()
            try:
                _rec_img = screen_capture.capture(region)
                _ocr_result = relic_analyzer.check_text_visible(_rec_img, "equipment", top_fraction=0.15)
                _ocr_dur = time.perf_counter() - _ocr_t0
                if self._diag:
                    self._diag.log_ocr(self._diag_cur_iter,
                                       "equipment (ESC recovery)", _ocr_result, _ocr_dur)
                if _ocr_result:
                    self._log("[Recovery] Equipment menu detected — pressing ESC to return to game.")
                    time.sleep(0.3)
                    self.player.tap("Key.esc")
                    _esc_settle = (3.5 if self._low_perf_mode_var.get() else 2.0) * max(1.0, self._perf_gap_mult)
                    time.sleep(_esc_settle)   # settle: ensure menu fully closes before next phase
                    return True
            except Exception as _re:
                _ocr_dur = time.perf_counter() - _ocr_t0
                if self._diag:
                    self._diag.log_ocr(self._diag_cur_iter,
                                       "equipment (ESC recovery)", None, _ocr_dur, error=str(_re))
                self._log(f"[Recovery] OCR error: {_re}")
        self._log("[Recovery] Could not find Equipment menu within 45 s — aborting.")
        return False

    def _confirm_in_game(self, region, exe_name: str) -> tuple:
        """Phase -0.5: adaptive game-load wait and in-game confirmation.

        Replaces the fixed Game Load Time wait. Each cycle:
          1. Spam F for 7 s at 0.15 s intervals (~47 presses) to advance through
             all title/splash/offline screens.
          2. Wait 1 s to let the game settle.
          3. Press ESC.
          4. Wait 1 s then OCR-check for the Equipment menu.
          5. If found: press ESC once to exit the menu, wait 2.5 s, return.
          6. If not found: repeat from step 1.

        Hard timeout: 150 s. Returns (True, elapsed_seconds) on success,
        (False, 0.0) on timeout.
        """
        _F_BURST    = 7.0    # seconds of F spam per cycle
        _F_INTERVAL = 0.15   # gap between F presses (seconds)
        _PRE_ESC    = 1.0    # settle after F burst before pressing ESC
        _POST_ESC   = 1.0    # settle after ESC before OCR check
        _MAX_WAIT   = 150.0  # hard timeout (seconds)

        _start = time.time()
        _cycle = 0

        self._log("[Phase -0.5] Adaptive load wait — watching for in-game state…")

        while True:
            if not self.bot_running:
                return False, 0.0
            if self._game_hung:
                self._log("[Phase -0.5] Game hung — aborting load wait.")
                return False, 0.0

            _elapsed = time.time() - _start
            if _elapsed >= _MAX_WAIT:
                self._log(
                    "[Phase -0.5] Could not confirm in-game state within 150 s — aborting.")
                return False, 0.0

            _cycle += 1
            self._set_status(
                f"Adaptive load wait — cycle {_cycle}…", "orange")
            # Focus the game window before each F burst so keypresses land in the
            # game rather than whatever window has focus (e.g. desktop, notification).
            if exe_name:
                self._focus_game_window(exe_name, timeout=2.0)

            # ── F-spam burst ──────────────────────────────────────────── #
            _burst_end = time.time() + _F_BURST
            while time.time() < _burst_end:
                if not self.bot_running:
                    return False, 0.0
                self.player.tap("f", hold=0.05)
                time.sleep(_F_INTERVAL)

            # ── Settle → ESC → settle → OCR ──────────────────────────── #
            time.sleep(_PRE_ESC)
            if not self.bot_running:
                return False, 0.0

            self.player.tap("Key.esc")
            time.sleep(_POST_ESC)
            if not self.bot_running:
                return False, 0.0

            try:
                _img = screen_capture.capture(region)
                if relic_analyzer.check_text_visible(_img, "equipment", top_fraction=0.15):
                    _elapsed = time.time() - _start
                    self._log(
                        f"[Phase -0.5] Equipment menu detected — in-game confirmed "
                        f"({_elapsed:.1f} s after window focus).")
                    _exe_bn = os.path.basename(self.game_exe_var.get().strip())
                    if _exe_bn and _boost_game_priority(_exe_bn):
                        self._log("[Phase -0.5] Game process boosted to HIGH priority.")
                    time.sleep(0.2)
                    self.player.tap("Key.esc")
                    # LPM needs more time for the menu-close animation.
                    _p05_esc_settle = (2.5 if self._low_perf_mode_var.get() else 1.5) * max(1.0, self._perf_gap_mult)
                    time.sleep(_p05_esc_settle)   # wait for menu to fully close before Phase 0
                    return True, _elapsed
            except Exception as _ce:
                self._log(f"[Phase -0.5] OCR error: {_ce}")

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
                    _kill_exe(exe_full)
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
            self._overlay.build(sw, sh, async_mode=self._async_enabled_var.get(),
                                backlog_mode=self._backlog_mode_var.get(),
                                settings=self._get_ov_settings())
            self._overlay.set_reset_iter_callback(self._request_reset_iter)
            self._overlay.set_stop_callback(self._request_stop_after_batch)
            self._overlay.set_force_stop_callback(self._stop_bot)
            self._overlay.set_close_game_callback(self._close_game)
            def _fmt_best(info, suffix):
                if info is None:
                    return "N/A"
                return f"Batch #{info['iteration']:03d}  —  {info['count']} {suffix}"
            self._overlay.update(
                at_33=self._ov_at_33, at_23=self._ov_at_23, at_duds=self._ov_at_duds,
                stored=0, analyzed=self._ov_total_relics,
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

        hotkey         = self._hotkey_str
        ov_hotkey      = self._ov_hotkey_str
        matches_hotkey = self._matches_hotkey_str

        def _on_press(key):
            try:
                k = key.char if (hasattr(key, "char") and key.char) else str(key)
            except Exception:
                k = str(key)
            if k == hotkey:
                self.after(0, self._hotkey_pressed)
            elif (k == ov_hotkey and self._overlay_enabled_var.get()
                  and self._overlay and getattr(self._overlay, "_win", None)):
                self.after(0, self._overlay.toggle_user_visibility)
            elif (k == matches_hotkey and self._overlay_enabled_var.get()
                  and self._overlay and getattr(self._overlay, "_win", None)):
                self.after(0, self._overlay._toggle_matches_view)

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

    def _set_ov_hotkey_dialog(self):
        """Open a key-capture dialog to set the overlay toggle hotkey."""
        dlg = tk.Toplevel(self)
        dlg.title("Set Overlay Toggle Hotkey")
        dlg.geometry("290x115")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self)

        tk.Label(dlg, text="Press any key to use as the\noverlay visibility toggle:").pack(pady=8)
        lbl = tk.Label(dlg, text="Waiting for key…", font=("", 11, "bold"))
        lbl.pack()

        done = [False]

        def _capture(key):
            if done[0]:
                return False
            done[0] = True
            try:
                k = key.char if (hasattr(key, "char") and key.char) else str(key)
            except Exception:
                k = str(key)
            display = k.replace("Key.", "").upper() if k.startswith("Key.") else k.upper()
            self._ov_hotkey_str     = k
            self._ov_hotkey_display = display

            def _finish():
                lbl.config(text=f"Set to: {display}")
                self._ov_hotkey_btn.config(text=f"Rec: {display}")
                self._start_global_hotkey_listener()
                dlg.after(700, dlg.destroy)

            self.after(0, _finish)
            return False

        listener = _kb.Listener(on_press=_capture, daemon=True)
        listener.start()
        dlg.protocol("WM_DELETE_WINDOW", lambda: (listener.stop(), dlg.destroy()))

    def _set_matches_hotkey_dialog(self):
        """Open a key-capture dialog to set the matches view toggle hotkey."""
        dlg = tk.Toplevel(self)
        dlg.title("Set Matches View Hotkey")
        dlg.geometry("290x115")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self)

        tk.Label(dlg, text="Press any key to use as the\nmatches view toggle:").pack(pady=8)
        lbl = tk.Label(dlg, text="Waiting for key…", font=("", 11, "bold"))
        lbl.pack()

        done = [False]

        def _capture(key):
            if done[0]:
                return False
            done[0] = True
            try:
                k = key.char if (hasattr(key, "char") and key.char) else str(key)
            except Exception:
                k = str(key)
            display = k.replace("Key.", "").upper() if k.startswith("Key.") else k.upper()
            self._matches_hotkey_str     = k
            self._matches_hotkey_display = display

            def _finish():
                lbl.config(text=f"Set to: {display}")
                self._matches_hotkey_btn.config(text=f"Rec: {display}")
                self._start_global_hotkey_listener()
                dlg.after(700, dlg.destroy)

            self.after(0, _finish)
            return False

        listener = _kb.Listener(on_press=_capture, daemon=True)
        listener.start()
        dlg.protocol("WM_DELETE_WINDOW", lambda: (listener.stop(), dlg.destroy()))

    def _request_reset_iter(self):
        """Overlay Reset Iteration button: signal the batch loop to soft-nuke this iteration."""
        if not self.bot_running:
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
        self._ov_smart_hits  = 0
        self._best_33_iter          = None
        self._best_hits_iter        = None
        self._ov_total_relics       = 0
        self._ov_stored_count       = 0
        self._async_relic_q         = None
        self._async_cancelled_iters = set()
        self._iter_contributions    = {}
        self._reset_iter_requested  = False
        # Reset adaptive performance state — seed from saved calibration if available
        _cal_start = self._load_calibration()
        if (_cal_start.get("machine_id") == self._get_machine_id()
                and _cal_start.get("baseline_load_s", 0) > 0):
            self._first_load_elapsed = float(_cal_start["baseline_load_s"])
            self._perf_gap_mult      = float(_cal_start.get("perf_mult", 1.0))
        else:
            self._first_load_elapsed = 0.0
            self._perf_gap_mult      = 1.0
        self._load_history = []
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
        self._log("Stop requested — will finish current iteration then exit.")
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
        # Raise bot thread priority so input sends are never starved by OCR
        # threads running in the background.  THREAD_PRIORITY_ABOVE_NORMAL = 1.
        try:
            ctypes.windll.kernel32.SetThreadPriority(
                ctypes.windll.kernel32.GetCurrentThread(), 1)
        except Exception:
            pass

        save_path = self.save_path_var.get()
        _backup_folder = self.backup_path_var.get()
        run_stamp = time.strftime("%Y-%m-%d_%H%M%S")
        batch_id  = time.strftime("%Y%m%d_%H%M%S")
        _backup_dir  = save_manager.make_backup_dir(_backup_folder, batch_id)
        backup_path  = os.path.join(_backup_dir, os.path.basename(save_path))
        self._run_backup_path = backup_path   # accessible to _run_iteration_phases
        criteria = self.relic_builder.get_criteria_dict()
        criteria_summary = self.relic_builder.get_criteria_summary()
        criteria["allowed_colors"] = self._get_allowed_colors()
        region = self._get_region()
        limit_type = self.batch_limit_type.get()
        limit_value = float(self.batch_limit_var.get())
        mode_desc = "loops"
        base_output = self.batch_output_var.get()
        # Minimum passive count for a result to be labelled a "HIT" tier.
        # If the user's criteria requires all 3 passives, 2/3 near-misses are
        # not counted as hits and won't get a HIT folder or ★★ log message.
        hit_min = self.relic_builder.get_min_hit_threshold()

        # The run folder is created lazily — only when the first iteration actually runs.
        # This prevents empty batch_run_* folders when the bot is stopped before any iteration.
        self._current_batch_id = batch_id
        self._ov_overflow_hits = 0
        self._global_murk_expected = None   # murk verified against each iteration; None = first run
        self._murk_region          = None   # pinned crop from first successful murk read
        # Reset batch-level reliability accumulators for this run
        self._batch_p0_extra        = 0
        self._batch_settle_retries  = 0
        self._batch_safe_path_count = 0
        self._batch_failed_settle   = 0
        self._batch_total_poll_depth = 0
        self._batch_total_settled   = 0
        run_dir = os.path.join(base_output, f"batch_run_{run_stamp}")
        live_log_path = os.path.join(run_dir, "live_log.txt")
        batch_log_path = os.path.join(run_dir, "run_log.txt")
        matches_log_path = os.path.join(run_dir, "matches_log.txt")
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
                # live_log.txt: relic analysis output only
                try:
                    with open(live_log_path, "w", encoding="utf-8") as _f:
                        _f.write(f"Relic Analysis Log — {run_stamp}\n")
                        _f.write("=" * 60 + "\n")
                    self._batch_relic_log_path = live_log_path
                except Exception:
                    pass
                # matches_log.txt: matched relics summary only
                try:
                    with open(matches_log_path, "w", encoding="utf-8") as _f:
                        _f.write(f"Matched Relics Log — {run_stamp}\n")
                        _f.write("=" * 60 + "\n\n")
                except Exception:
                    pass
                self._log(f"Batch output folder: {run_dir}")
                # ── Diagnostic logger (input-test build) ──────────────────
                try:
                    self._diag = DiagnosticLogger(run_dir)
                    self._diag.log_hardware()
                    self._diag.log_settings(self)
                    self._diag.start_interference_monitor()
                    self.player.diag = self._diag
                except Exception as _de:
                    self._log(f"[DIAG] Logger init failed: {_de}")

        def _write_match_entry(iteration: int, relic_num: int, tier: str,
                               result: dict) -> None:
            """Append a formatted match entry to matches_log.txt and the overlay panel."""
            relics = result.get("relics_found", [])
            r0 = relics[0] if relics else {}
            rname    = r0.get("name", "Unknown") if isinstance(r0, dict) else "Unknown"
            passives = r0.get("passives", []) if isinstance(r0, dict) else []
            curses   = r0.get("curses",   []) if isinstance(r0, dict) else []

            sep  = "─" * 40
            lines = [
                sep,
                f"  {tier}  |  Iter #{iteration:03d}  ·  Relic {relic_num}",
                f"  Relic : {rname}",
            ]
            if passives:
                for p in passives:
                    lines.append(f"  + {p}")
            if curses:
                for c in curses:
                    lines.append(f"  ✗ {c}  (curse)")
            lines.append("")

            text = "\n".join(lines) + "\n"
            try:
                with open(matches_log_path, "a", encoding="utf-8") as _f:
                    _f.write(text)
            except Exception:
                pass
            if self._overlay:
                ov = self._overlay
                self.after(0, lambda t=text: ov.append_matches_log(t)
                           if ov._win else None)

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

        # ── Backlog mode: defer all OCR until after the batch ─────────── #
        _backlog_mode         = self._backlog_mode_var.get()
        _intermittent_mode    = _backlog_mode and self._intermittent_backlog_var.get()
        _intermittent_every_n = max(1, self._intermittent_every_n_var.get())
        _iters_since_drain    = 0   # how many iterations since last intermittent drain

        # GPU Always Analyze + Intermittent: persistent GPU worker runs throughout
        # the entire capture phase — enqueued immediately after each iteration,
        # no game-close needed for GPU.  CPU workers are gated: released every N
        # iterations to handle any remainder the GPU hasn't reached yet.
        _gpu_aa_bl = (self._gpu_always_analyze_var.get()
                      and self._hybrid_var.get()
                      and self._gpu_accel_var.get()
                      and self._parallel_enabled_var.get())
        _bg_gpu_active  = _backlog_mode and _intermittent_mode and _gpu_aa_bl
        _bg_gpu_q       = queue.PriorityQueue() if _bg_gpu_active else None
        _bg_bl_state: dict = {}
        _bg_bl_lock     = threading.Lock()
        _bg_bl_dmap: dict = {}
        _bg_done_ev     = threading.Event()
        _bg_cpu_go_ev   = threading.Event()   # CPU gate: set when N iters reached
        _bg_worker      = None
        _bg_cpu_threads: list = []

        if _bg_gpu_active:
            from bot import relic_analyzer as _bg_ra
            _bg_ra.set_gpu_mode(True)

            def _make_bg_worker(use_gpu, gate_ev=None):
                from bot import relic_analyzer as _bra
                _cached_rdr = [None]
                def _worker():
                    _bra.set_thread_device(use_gpu)
                    while True:
                        if gate_ev is not None:
                            # CPU worker: wait for gate before each task
                            while not gate_ev.is_set():
                                if _bg_done_ev.is_set() and _bg_gpu_q.empty():
                                    return
                                gate_ev.wait(timeout=1.0)
                        if _bg_done_ev.is_set() and _bg_gpu_q.empty():
                            break
                        try:
                            _prio, _task = _bg_gpu_q.get(timeout=0.3)
                        except queue.Empty:
                            if gate_ev is not None and _bg_gpu_q.empty():
                                # Queue drained — re-block until next N-iter gate open
                                gate_ev.clear()
                            continue
                        if _cached_rdr[0] is None:
                            _cached_rdr[0] = _bra._get_reader()
                        try:
                            _rdr = _cached_rdr[0]
                            def _inner(_t=_task, _r=_rdr):
                                _bra.prime_thread_reader(_r, use_gpu)
                                self._analyze_relic_task(
                                    _t, _bg_bl_state, _bg_bl_lock, _bg_bl_dmap, results)
                            _rt = threading.Thread(target=_inner, daemon=True)
                            _rt.start()
                            _rt.join(timeout=90)
                            if _rt.is_alive():
                                self._log("  [BG-GPU] Relic analysis timed out — skipping.")
                        except Exception as _bge:
                            self._log(f"  [BG-GPU] Worker error: {_bge}")
                        finally:
                            _bg_gpu_q.task_done()
                return _worker

            _bg_worker = threading.Thread(
                target=_make_bg_worker(True), daemon=True, name="bg-gpu-worker")
            _bg_worker.start()

            _bg_w_max = min(8, max(2, self._hw_cpu_cores or 8))
            _bg_n_cpu = (max(2, min(_bg_w_max, self._parallel_workers_var.get()))
                         if self._parallel_enabled_var.get() else 1)
            _bg_cpu_threads = [
                threading.Thread(target=_make_bg_worker(False, _bg_cpu_go_ev),
                                 daemon=True, name=f"bg-cpu-worker-{_n}")
                for _n in range(_bg_n_cpu)
            ]
            for _t in _bg_cpu_threads:
                _t.start()
            self._log(
                f"  [BG-GPU] Persistent GPU+CPU workers started "
                f"(GPU always on, {_bg_n_cpu} CPU worker(s) gated every "
                f"{_intermittent_every_n} iteration(s)).")

        # ── Async mode setup ──────────────────────────────────────────── #
        # Backlog mode takes priority — skip async workers during the run.
        _async_mode = self._async_enabled_var.get() and not _backlog_mode
        # Exclude Analysis While Operations Are Happening: workers run ONLY during
        # the game-close → Phase -0.5 window.  Hard gate managed by the batch loop;
        # all in-phase throttle releases inside _run_iteration_phases are suppressed.
        _excl_ops_mode = _async_mode and self._exclude_buy_phase_var.get()
        _async_relic_q: queue.PriorityQueue | None = None
        _async_dir_map:    dict = {}   # iteration → final dir (after any rename)
        _async_iter_state: dict = {}   # iteration → per-iter completion tracking
        _async_state_lock = threading.Lock()
        _async_shutdown_done = [False]
        _ASYNC_TASK_TIMEOUT  = 90      # seconds per relic before requeueing

        if _async_mode:
            _async_relic_q = self._async_relic_q = queue.PriorityQueue()
            # Store shared state refs on self so _run_iteration_phases can access them
            self._async_iter_state  = _async_iter_state
            self._async_dir_map     = _async_dir_map
            self._async_state_lock  = _async_state_lock
            self._async_results_list = results
            # OCR throttle: cleared before input phases, set before Phase 2 scan
            self._ocr_go_event = threading.Event()
            self._ocr_go_event.set()
            _gpu_on          = self._gpu_accel_var.get()
            _async_hybrid    = (_gpu_on
                                and self._hybrid_var.get()
                                and self._parallel_enabled_var.get())
            _worker_max      = min(8, max(2, self._hw_cpu_cores or 8))
            # CPU worker count — only used when Hybrid is on or GPU is off.
            # When GPU is on without Hybrid, the GPU worker runs alone.
            _async_workers   = (max(1, min(_worker_max, self._parallel_workers_var.get()))
                                if self._parallel_enabled_var.get() else 1)

            # CPU core allocation:
            #   Core 0 is reserved as the "input core" — the bot thread runs
            #   at ABOVE_NORMAL priority and OCR workers are pinned to all
            #   other cores so inputs are never starved during inference.
            #   LPM further limits OCR to half the total cores to keep the
            #   system responsive on low-end hardware.
            _cpu_cores   = os.cpu_count() or 4
            _lpm_active  = self._low_perf_mode_var.get()
            _ocr_cores   = max(1, (_cpu_cores // 2) if _lpm_active else (_cpu_cores - 1))
            # GPU-only: 1 GPU worker uses CUDA, CPU thread count is less relevant
            _effective_cpu_workers = _async_workers if (not _gpu_on or _async_hybrid) else 1
            _torch_t     = max(1, _ocr_cores // _effective_cpu_workers)
            relic_analyzer.configure_torch_threads(_torch_t)

            # Pin OCR worker threads to all cores except core 0 (input core).
            # The bot thread (sends inputs) keeps core 0 free for itself.
            _all_mask  = (1 << _cpu_cores) - 1
            _ocr_mask  = _all_mask & ~1   # exclude bit 0 (core 0)
            if _cpu_cores > 1 and _ocr_mask:
                relic_analyzer.configure_ocr_affinity(_ocr_mask)

            _mode_tag = "LPM" if _lpm_active else "normal"
            if _async_hybrid:
                _worker_desc  = f"1 GPU + {_async_workers} CPU worker(s) [Hybrid]"
                _total_workers = _async_workers + 1
            elif _gpu_on:
                _worker_desc  = "1 GPU worker"
                _total_workers = 1
            else:
                _worker_desc  = f"{_async_workers} CPU worker(s)"
                _total_workers = _async_workers
            _gpu_aa_active = _async_hybrid and self._gpu_always_analyze_var.get()
            self._log(
                f"Async Analysis enabled — {_worker_desc}; "
                + f"OCR cores: {_ocr_cores}/{_cpu_cores} ({_mode_tag}); "
                f"PyTorch threads per inference: {_torch_t}; "
                f"input core 0 reserved."
                + ("; GPU worker: always analyze (throttle bypass active)" if _gpu_aa_active else "")
            )

            def _make_relic_worker(use_gpu):  # noqa: E306
                """Return an async worker function pinned to the given device.

                use_gpu=True  → GPU reader (CUDA); use_gpu=None → global flag.

                The outer (long-lived) worker thread pre-warms its EasyOCR Reader
                once on first task.  Each inner _rt analysis thread is primed with
                that cached reader via prime_thread_reader() so the ~2-3s per-thread
                model reload is skipped for every subsequent relic.
                """
                from bot import relic_analyzer as _ra
                _cached_reader = [None]   # reader warmed once in the outer thread

                def _worker():
                    while True:
                        _gpu_aa = self._gpu_always_analyze_var.get()
                        if _gpu_aa and not use_gpu:
                            # GPU AA on, CPU worker: wait for gate BEFORE dequeuing.
                            # Post-dequeue waiting would hold the task, preventing the
                            # GPU worker (which bypasses the gate) from reaching it.
                            # Pre-checking keeps the task in the queue where GPU can grab it.
                            # Loop with 1 s polls — indefinite, no escape (Phase -0.5 +
                            # Phase 0 together can exceed 70 s).
                            _go_ev = self._ocr_go_event
                            if _go_ev is not None and not _go_ev.is_set():
                                while not _go_ev.wait(timeout=1.0):
                                    pass
                        _prio, _task = _async_relic_q.get()
                        if _task is None:   # sentinel
                            _async_relic_q.task_done()
                            break
                        if not _gpu_aa:
                            # GPU AA off: all workers use post-dequeue gate check
                            # (original behavior — workers finish current task first,
                            # only the next task is held while gate is closed).
                            _go_ev = self._ocr_go_event
                            if _go_ev is not None and not _go_ev.is_set():
                                while not _go_ev.wait(timeout=1.0):
                                    pass
                        # GPU AA on: GPU worker bypasses gate entirely; CPU workers
                        # already waited before dequeue above — no post-check needed.
                        # Pre-warm the EasyOCR reader in this (outer) worker thread
                        # the first time a task is dequeued.  Subsequent tasks reuse it.
                        if _cached_reader[0] is None:
                            _ra.set_thread_device(use_gpu)
                            _cached_reader[0] = _ra._get_reader()
                        # Overflow tasks embed their own state so main workers can
                        # handle them without extra threads.
                        _ovf = _task.pop("_ovf_state", None)
                        _w_state, _w_lock, _w_dmap, _w_res = (
                            _ovf if _ovf
                            else (_async_iter_state, _async_state_lock,
                                  _async_dir_map, results)
                        )
                        try:
                            _reader = _cached_reader[0]
                            def _inner(_t=_task, _ws=_w_state, _wl=_w_lock,
                                       _wd=_w_dmap, _wr=_w_res, _rdr=_reader):
                                # Prime this inner thread with the pre-warmed reader so
                                # _get_reader() returns immediately without reloading.
                                _ra.prime_thread_reader(_rdr, use_gpu)
                                self._analyze_relic_task(_t, _ws, _wl, _wd, _wr)
                            _rt = threading.Thread(target=_inner, daemon=True)
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
                                        _task, _w_state, _w_lock, _w_dmap, _w_res)
                        except Exception as _re:
                            self._log(f"ERROR in async relic worker: {_re}")
                            self._mark_relic_failed(
                                _task, _w_state, _w_lock, _w_dmap, _w_res)
                        finally:
                            _async_relic_q.task_done()
                return _worker

            if _async_hybrid:
                # 1 GPU worker + N CPU workers — all pull from the same queue.
                # CPU workers explicitly pass False (not None) so they build a
                # CPU reader even though _gpu_mode_enabled is True globally.
                threading.Thread(target=_make_relic_worker(True), daemon=True,
                                 name="async-relic-worker-gpu").start()
                for _wn in range(_async_workers):
                    threading.Thread(target=_make_relic_worker(False), daemon=True,
                                     name=f"async-relic-worker-cpu-{_wn}").start()
            elif _gpu_on:
                # GPU only — 1 dedicated GPU worker, no CPU workers.
                threading.Thread(target=_make_relic_worker(True), daemon=True,
                                 name="async-relic-worker-gpu").start()
            else:
                # CPU only — N workers from the Brute Force spinbox (or 1 if off).
                for _wn in range(_async_workers):
                    threading.Thread(target=_make_relic_worker(None), daemon=True,
                                     name=f"async-relic-worker-{_wn}").start()

            def _shutdown_async_workers():
                if not _async_shutdown_done[0]:
                    _async_shutdown_done[0] = True
                    # Unblock any waiting workers so sentinels can be received
                    if self._ocr_go_event is not None:
                        self._ocr_go_event.set()
                    for _ in range(_total_workers):
                        _async_relic_q.put(
                            ((float("inf"), float("inf")), None))

            def _async_join_timed(grace: float | None = None):
                """Wait for the async relic queue to drain.

                grace — explicit timeout in seconds.  If None the per-task
                timeout (_ASYNC_TASK_TIMEOUT) is used.  End-of-batch callers
                pass a queue-size-scaled value so slow hardware gets enough
                time to process all pending relics.
                """
                _timeout = grace if grace is not None else _ASYNC_TASK_TIMEOUT
                _done = threading.Event()
                def _waiter():
                    _async_relic_q.join()
                    _done.set()
                threading.Thread(target=_waiter, daemon=True).start()
                if not _done.wait(timeout=_timeout):
                    self._log(
                        f"WARNING: Async workers did not finish within "
                        f"{_timeout:.0f}s — proceeding anyway."
                    )

            # ── Overflow workers for previous batch tasks ──────────────── #
            # Default: 2 dedicated overflow workers (independent threads).
            # RAM-sensitive: if free RAM < 1 GB, skip dedicated workers entirely
            # and route tasks directly through the main worker queue instead —
            # no extra threads or model instances are loaded.
            # 1-worker mode: overflow is dropped to avoid adding pressure on an
            # already-constrained machine.
            _ovf = self._overflow_handoff
            if _ovf is not None:
                self._overflow_handoff = None
                _ovf_ram_mb = _available_ram_mb()
                _use_dedicated_ovf = _ovf_ram_mb >= 1000 or _async_workers < 2

                if _use_dedicated_ovf and _async_workers >= 2:
                    # Plenty of RAM — spawn 2 independent overflow worker threads
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
                            except Exception as _oexc:
                                self._log(
                                    f"  [Overflow worker] Unhandled error on relic "
                                    f"{_task.get('step_i', '?') + 1} "
                                    f"(iter {_task.get('iteration', '?')}): {_oexc}",
                                    overlay=False)
                                self._mark_relic_failed(_task, _ois, _ol, _odm, _or)
                            finally:
                                _oq.task_done()

                    for _wn in range(2):
                        threading.Thread(
                            target=_overflow_worker, daemon=True,
                            name=f"overflow-worker-{_wn}",
                        ).start()
                    self._log("Overflow: 2 dedicated workers started for previous batch leftovers.")

                elif _async_workers >= 2:
                    # RAM is low — route overflow tasks through main worker queue.
                    # Embeds the previous batch's state in each task so main workers
                    # can resolve them without loading extra OCR model instances.
                    _ois = _ovf["iter_state"]
                    _ol  = _ovf["lock"]
                    _odm = _ovf["dir_map"]
                    _or  = _ovf["results"]
                    _n_routed = 0
                    for _prio, _task in _ovf["tasks"]:
                        if _task is not None:
                            _task["_ovf_state"] = (_ois, _ol, _odm, _or)
                            _async_relic_q.put((_prio, _task))
                            _n_routed += 1
                    self._log(
                        f"Overflow: RAM low ({_ovf_ram_mb:.0f} MB free) — "
                        f"{_n_routed} leftover task(s) routed to main workers "
                        f"(no extra threads spawned)."
                    )

                else:
                    # 1 worker + low RAM — skip overflow to avoid extra pressure.
                    self._log(
                        f"Overflow: RAM low ({_ovf_ram_mb:.0f} MB free) and only "
                        f"1 main worker — previous batch leftovers dropped."
                    )

        _MAX_RESTARTS           = 3    # abort after this many hung-game restarts on same iteration
        _MAX_P0_ITER_RESTARTS   = 3    # abort if Phase 0 fails this many restarts of same iteration
        _iter_restart_count     = 0    # hung-game restarts for current iteration (reset on advance)
        _phase0_iter_restarts   = 0    # Phase 0 restarts for current iteration (reset on advance)
        _is_restart             = False  # True when retrying the same iteration

        # ── Diagnostic helper — call before every restart/abort continue ──
        def _diag_end(outcome: str = "restart"):
            if self._diag:
                try:
                    self._diag.iteration_end(self._diag_cur_iter, outcome)
                except Exception:
                    pass

        # ── Overlay mode tag — shown in header for the duration of this run ─
        if self._overlay:
            _mode_parts = []
            if _backlog_mode:
                _mode_parts.append("Backlog")
                if _intermittent_mode:
                    _mode_parts.append(f"Intermittent/{_intermittent_every_n}")
                if self._gpu_always_analyze_var.get():
                    _mode_parts.append("GPU.Always")
            elif _async_mode:
                _mode_parts.append("Async")
                if _excl_ops_mode:
                    _mode_parts.append("Excl.Ops")
                if self._gpu_always_analyze_var.get():
                    _mode_parts.append("GPU.Always")
            else:
                _mode_parts.append("Brute Force")
            if self._smart_throttle_var.get():
                _mode_parts.append("SmartThrottle")
            if self._smart_analyze_var.get():
                _mode_parts.append("SmartAnalyze")
            _mt = " · ".join(_mode_parts)
            _ov_mt = self._overlay
            self.after(0, lambda t=_mt: _ov_mt.update(mode_tag=t) if _ov_mt._win else None)

        while self.bot_running:
            # Check stopping condition
            if limit_type == "loops" and iteration >= int(limit_value):
                break

            if not _is_restart:
                iteration += 1
                _iter_restart_count   = 0   # fresh iteration resets the hung counter
                _phase0_iter_restarts = 0   # fresh iteration resets the Phase 0 restart counter
                self.attempt_count = iteration
                self.after(0, lambda n=iteration: self.attempt_var.set(f"Attempts: {n}"))
            else:
                _is_restart = False       # clear flag; counter already incremented

            # Overlay: batch progress
            if self._overlay:
                _bs = f"Batch {iteration} / {int(limit_value)}"
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
                    _f.write(f"\n--- Batch {iteration} ---\n")
            except Exception:
                pass

            # ── Diagnostic: iteration start ────────────────────────────
            self._diag_cur_iter = iteration
            if self._diag:
                self._diag.iteration_start(iteration)
                self.player._diag_iter = iteration

            folder_name = f"{iteration:03d}"
            iter_dir = os.path.join(run_dir, folder_name)
            os.makedirs(iter_dir, exist_ok=True)

            if _iter_restart_count > 0:
                self._log(
                    f"--- Batch {iteration} "
                    f"(restart {_iter_restart_count}/{_MAX_RESTARTS}) ---"
                )
            else:
                self._log(f"--- Batch {iteration} ---")

            self._game_hung = False   # clear watchdog flag at the start of each attempt
            # Release workers before game closes so they can analyse during
            # the close → restore → launch → Phase -0.5 window.
            if _excl_ops_mode:
                self._set_ocr_throttle(False)
            self._set_status(f"Batch {iteration}: closing game…", "orange")
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
            self._set_status(f"Batch {iteration}: launching game…", "orange")
            confirm_key = "f"
            exe_name    = os.path.basename(self.game_exe_var.get().strip())

            # Wait for the game window to appear before starting the load timer.
            # Inputs sent before focus would go to the desktop, not the game.
            #
            # Three states after a launch command:
            #   A) Window visible          → focus and proceed (normal)
            #   B) Process running, no window → game is loading slowly; keep waiting,
            #                                   never relaunch while process exists
            #   C) Process not found       → Steam may have dropped the request,
            #                                but give a 15 s grace period first in
            #                                case the process just hasn't spawned yet
            #                                before deciding to relaunch
            #
            # _launch_attempts counts actual launch() calls. Up to 3 before aborting.
            _FOCUS_POLL_INTERVAL  = 20   # s between "check process / window" cycles
            _PROCESS_GRACE        = 15   # s to wait for process to appear before relaunch
            _LAUNCH_MAX_ATTEMPTS  = 3
            _NO_WINDOW_MAX        = 180  # s before assuming crashed process with no window

            _game_focused      = False
            _launch_attempts   = 0
            _no_window_since   = None   # timestamp of first "process running, no window" observation

            while self.bot_running and not _game_focused:
                # Only fire the launch command if the process is not already running.
                # This prevents double-launching when the game is just slow to start.
                if not self._is_game_running(exe_name):
                    if _launch_attempts >= _LAUNCH_MAX_ATTEMPTS:
                        self._log(
                            f"ERROR: Game failed to open after {_launch_attempts} "
                            f"launch attempt(s) — cancelling batch.")
                        if _async_mode and _async_relic_q is not None:
                            _shutdown_async_workers()
                            _async_join_timed()
                        self.after(0, self._reset_controls)
                        return
                    _launch_attempts += 1
                    self._log(
                        f"Launching game "
                        f"(attempt {_launch_attempts}/{_LAUNCH_MAX_ATTEMPTS})…")
                    self._launch_game()
                    self._set_status(
                        f"Batch {iteration}: waiting for game window…", "orange")

                    # Grace period: give Steam time to spawn the process before we
                    # check whether it took. Poll for both process and window.
                    _grace_end = time.time() + _PROCESS_GRACE
                    while self.bot_running and time.time() < _grace_end:
                        _game_focused = self._focus_game_window(exe_name, timeout=1.0)
                        if _game_focused:
                            break
                        if self._is_game_running(exe_name):
                            break   # process appeared — fall through to window poll
                        time.sleep(0.5)
                    if _game_focused:
                        break
                else:
                    self._set_status(
                        f"Batch {iteration}: waiting for game window…", "orange")

                # Process is (or just became) running — poll for window up to
                # _FOCUS_POLL_INTERVAL seconds, then loop back to re-check state.
                _poll_end = time.time() + _FOCUS_POLL_INTERVAL
                while self.bot_running and time.time() < _poll_end:
                    _game_focused = self._focus_game_window(exe_name, timeout=1.0)
                    if _game_focused:
                        break
                    time.sleep(0.5)

                if not _game_focused and self.bot_running:
                    if self._is_game_running(exe_name):
                        if _no_window_since is None:
                            _no_window_since = time.time()
                        elapsed_no_win = time.time() - _no_window_since
                        if elapsed_no_win >= _NO_WINDOW_MAX:
                            self._log(
                                f"  Game process has been running without a window for "
                                f"{int(elapsed_no_win)}s — assuming crash. Force-killing…")
                            self._close_game()
                            _no_window_since = None
                        else:
                            self._log(
                                "  Game process running but window not visible yet "
                                "— still waiting…")
                    else:
                        _no_window_since = None   # process gone — reset timer
                    # loop continues: if process gone → relaunch; if running → wait more

            if not self.bot_running:
                self.after(0, self._reset_controls)
                return

            # Game window confirmed — begin adaptive load wait (Phase -0.5).
            self._log("Game window focused — starting adaptive load wait…")
            if self._diag:
                try:
                    self._diag.phase_start("Phase -0.5 (game load)")
                except Exception:
                    pass
            _in_game_ok, _load_elapsed = self._confirm_in_game(region, exe_name)
            if _in_game_ok:
                # Diagnostic: log in-game confirmation milestone with load time
                if self._diag:
                    try:
                        self._diag.phase_end("Phase -0.5 (game load)",
                                             load_elapsed=f"{_load_elapsed:.1f}s",
                                             perf_mult=self._perf_gap_mult)
                    except Exception:
                        pass
                # Only update on success — don't let a timed-out attempt (0.0)
                # clobber the last known good value and starve the Phase 0 window.
                self._last_load_elapsed = _load_elapsed
                # Adaptive gap scaling: track load time as a system-health proxy.
                # As the system slows over a long run, load times grow and the
                # multiplier rises so all input gaps widen proportionally.
                if self._first_load_elapsed == 0.0:
                    self._first_load_elapsed = _load_elapsed
                    # Persist baseline so next session starts calibrated
                    self._save_calibration({
                        "machine_id":      self._get_machine_id(),
                        "baseline_load_s": round(_load_elapsed, 2),
                        "perf_mult":       1.0,
                        "last_updated":    datetime.datetime.now().isoformat(),
                    })
                self._load_history.append(_load_elapsed)
                if len(self._load_history) > 5:
                    self._load_history.pop(0)
                if self._first_load_elapsed > 0 and len(self._load_history) >= 2:
                    _recent = self._load_history[-min(3, len(self._load_history)):]
                    _new_mult = max(1.0, min(2.5,
                        (sum(_recent) / len(_recent)) / self._first_load_elapsed))
                    if abs(_new_mult - self._perf_gap_mult) >= 0.05:
                        self._perf_gap_mult = _new_mult
                        self._log(
                            f"  [Adaptive] System factor updated: {_new_mult:.2f}× "
                            f"(recent avg {sum(_recent)/len(_recent):.1f} s vs "
                            f"baseline {self._first_load_elapsed:.1f} s) — "
                            f"input gaps scaled accordingly."
                        )
                        # Keep persisted mult in sync
                        self._save_calibration({
                            "machine_id": self._get_machine_id(),
                            "perf_mult":  round(_new_mult, 3),
                            "last_updated": datetime.datetime.now().isoformat(),
                        })
                    else:
                        self._perf_gap_mult = _new_mult
            if not _in_game_ok:
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
                _diag_end(); _is_restart = True
                continue

            # Phase -0.5 concluded — block workers for all in-game operations.
            if _excl_ops_mode:
                self._set_ocr_throttle(True)

            label = f"Batch {iteration}"

            # ── Async mode: capture only, then push task to background worker ── #
            if _async_mode:
                self.after(0, self._show_mouse_blocker)
                captures = self._run_iteration_phases(
                    label, criteria, region,
                    iter_dir=iter_dir, hit_min=hit_min,
                    live_log_path=live_log_path,
                    capture_only=True, iteration=iteration,
                    async_iter_meta={
                        "run_dir":          run_dir,
                        "criteria_summary": criteria_summary,
                        "mode_desc":        mode_desc,
                        "limit_value":      limit_value,
                        "save_filename":    save_filename,
                        "batch_id":         batch_id,
                        "matches_log_path": matches_log_path,
                    })
                self.after(0, self._hide_mouse_blocker)

                # In the P2-async path, _run_iteration_phases returns slot-0
                # analyze result dicts (not Phase-4 capture tuples).  All relics
                # were already handled inline or via _async_relic_q — the outer
                # loop must see an empty list so it takes the len==0 branch and
                # doesn't try to unpack dicts as (step_i, img, path) 3-tuples
                # (which would raise ValueError and silently crash the bot thread).
                # This covers every early-return path inside _run_iteration_phases.
                if captures and isinstance(captures[0], dict):
                    captures = []

                self._calibrate_from_iteration()   # adjust gap mult from this iteration

                if captures is None:
                    # Fatal capture error — shut down workers and abort
                    _shutdown_async_workers()
                    _async_join_timed()
                    self.after(0, self._reset_controls)
                    return

                # Phase 0 failed 3 times — restart the same iteration
                if self._phase0_skipped:
                    _phase0_iter_restarts += 1
                    self._cancel_and_rollback_iteration(iteration)
                    if _phase0_iter_restarts >= _MAX_P0_ITER_RESTARTS:
                        self._log(
                            f"Phase 0 failed on all {_MAX_P0_ITER_RESTARTS} attempts "
                            f"of iteration {iteration} — aborting batch.")
                        _shutdown_async_workers()
                        _async_join_timed()
                        self.after(0, self._reset_controls)
                        return
                    self._log(
                        f"  Phase 0 failed — restarting iteration {iteration} "
                        f"(attempt {_phase0_iter_restarts + 1}/{_MAX_P0_ITER_RESTARTS}).")
                    try:
                        shutil.rmtree(iter_dir, ignore_errors=True)
                    except Exception:
                        pass
                    _prev_save_dir = None
                    _diag_end(); _is_restart = True
                    # Allow workers from fresh attempt to update counters again
                    self._async_cancelled_iters.discard(iteration)
                    continue

                if not self.bot_running:
                    break

                # User-requested soft nuke of this iteration
                if self._reset_iter_requested:
                    self._reset_iter_requested = False
                    self._log(f"[Reset] Discarding iteration {iteration} and restarting.")
                    self._cancel_and_rollback_iteration(iteration)
                    self._close_game()
                    try:
                        save_manager.restore(save_path, backup_path)
                    except Exception as _rse:
                        self._log(f"  WARNING: save restore failed: {_rse}")
                    try:
                        shutil.rmtree(iter_dir, ignore_errors=True)
                    except Exception:
                        pass
                    _prev_save_dir = None
                    _iter_restart_count = 0
                    _diag_end(); _is_restart = True
                    # Allow the restarted iteration to accumulate fresh contributions
                    self._async_cancelled_iters.discard(iteration)
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
                    _diag_end(); _is_restart = True
                    continue

                # Register iteration completion state, then push individual relic tasks
                with _async_state_lock:
                    if len(captures) == 0:
                        # Phase 2 async may have already registered this iteration —
                        # only do immediate dir finalization if it hasn't.
                        if iteration not in _async_iter_state:
                            _async_dir_map[iteration] = iter_dir
                    else:
                        # Phase 4 captures (legacy path — Phase 4 is empty in new arch)
                        _async_iter_state[iteration] = {
                            "total":          len(captures),
                            "done":           0,
                            "_finalized":     False,
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
                        "iteration":        iteration,
                        "step_i":           _si,
                        "img_bytes":        _img,
                        "pending_path":     _pp,
                        "iter_dir":         iter_dir,
                        "criteria":         criteria,
                        "hit_min":          hit_min,
                        "live_log_path":    live_log_path,
                        "matches_log_path": matches_log_path,
                        "run_dir":          run_dir,
                        "criteria_summary": criteria_summary,
                        "mode_desc":        mode_desc,
                        "limit_value":      limit_value,
                        "save_filename":    save_filename,
                        "batch_id":         batch_id,
                        "_run_log_path":    batch_log_path,
                        "_retries":         0,
                    }))

                _prev_save_dir = iter_dir

                if self._stop_after_batch:
                    self._log("Iteration capture done — stopping as requested "
                              "(analysis continuing in background).")
                    break

                continue   # skip normal post-processing

            # ── Backlog mode: capture-only, save screenshots to disk ───── #
            if _backlog_mode:
                self.after(0, self._show_mouse_blocker)
                captures = self._run_iteration_phases(
                    label, criteria, region,
                    iter_dir=iter_dir, hit_min=hit_min,
                    live_log_path=live_log_path,
                    capture_only=True, iteration=iteration)
                self.after(0, self._hide_mouse_blocker)
                self._calibrate_from_iteration()   # adjust gap mult from this iteration

                if captures is None:
                    self._log("[Backlog] Fatal capture error — aborting.")
                    self.after(0, self._reset_controls)
                    return

                if self._phase0_skipped:
                    _phase0_iter_restarts += 1
                    self._cancel_and_rollback_iteration(iteration)
                    if _phase0_iter_restarts >= _MAX_P0_ITER_RESTARTS:
                        self._log(
                            f"Phase 0 failed on all {_MAX_P0_ITER_RESTARTS} attempts "
                            f"of iteration {iteration} — aborting batch.")
                        self.after(0, self._reset_controls)
                        return
                    self._log(
                        f"  Phase 0 failed — restarting iteration {iteration} "
                        f"(attempt {_phase0_iter_restarts + 1}/{_MAX_P0_ITER_RESTARTS}).")
                    try:
                        shutil.rmtree(iter_dir, ignore_errors=True)
                    except Exception:
                        pass
                    _prev_save_dir = None
                    _is_restart = True
                    continue

                if self._reset_iter_requested:
                    self._reset_iter_requested = False
                    self._log(f"[Reset] Discarding iteration {iteration}.")
                    self._cancel_and_rollback_iteration(iteration)
                    self._close_game()
                    try:
                        save_manager.restore(save_path, backup_path)
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

                if captures:
                    import json as _json
                    try:
                        os.makedirs(iter_dir, exist_ok=True)

                        # GPU Always Analyze: initialise the iteration state entry
                        # before the save loop so each image can be enqueued the
                        # instant it is written to disk — GPU worker can start on
                        # relic 1 while relic 2 is still being saved.
                        if _bg_gpu_active and _bg_gpu_q is not None:
                            with _bg_bl_lock:
                                _bg_bl_state[iteration] = {
                                    "total":            len(captures),
                                    "done":             0,
                                    "results":          [],
                                    "iter_dir":         iter_dir,
                                    "hit_min":          hit_min,
                                    "live_log_path":    live_log_path,
                                    "run_dir":          run_dir,
                                    "criteria_summary": criteria_summary,
                                    "mode_desc":        mode_desc,
                                    "limit_value":      limit_value,
                                    "save_filename":    save_filename,
                                    "batch_id":         batch_id,
                                    "matches_log_path": matches_log_path,
                                    "_run_log_path":    batch_log_path,
                                }
                                _bg_bl_dmap[iteration] = iter_dir

                        for _si, _img, _pp in captures:
                            # Name includes iteration so each file is uniquely
                            # identifiable without needing a subfolder.
                            _bl_fname = f"Iter_{iteration}_Relic_{_si + 1}.jpg"
                            _bl_fpath = os.path.join(iter_dir, _bl_fname)
                            with open(_bl_fpath, "wb") as _f:
                                _f.write(_img)
                            if _pp and os.path.exists(_pp):
                                try:
                                    os.remove(_pp)
                                except Exception:
                                    pass
                            # GPU Always Analyze: enqueue immediately after saving —
                            # GPU worker can start on this image right now.
                            if _bg_gpu_active and _bg_gpu_q is not None:
                                _bg_gpu_q.put(((iteration, _si), {
                                    "iteration":         iteration,
                                    "step_i":            _si,
                                    "img_bytes":         _img,
                                    "pending_path":      "",
                                    "_backlog_img_path": _bl_fpath,
                                    "iter_dir":          iter_dir,
                                    "criteria":          criteria,
                                    "hit_min":           hit_min,
                                    "live_log_path":     live_log_path,
                                    "matches_log_path":  matches_log_path,
                                    "run_dir":           run_dir,
                                    "criteria_summary":  criteria_summary,
                                    "mode_desc":         mode_desc,
                                    "limit_value":       limit_value,
                                    "save_filename":     save_filename,
                                    "batch_id":          batch_id,
                                    "_run_log_path":     batch_log_path,
                                    "crop_left":         relic_analyzer._PREVIEW_CROP_LEFT_FRAC,
                                    "crop_top":          relic_analyzer._PREVIEW_CROP_TOP_FRAC,
                                    "_retries":          0,
                                }))

                        _bl_meta = {
                            "iteration":        iteration,
                            "total_relics":     len(captures),
                            "iter_dir":         iter_dir,
                            "hit_min":          hit_min,
                            "live_log_path":    live_log_path,
                            "run_dir":          run_dir,
                            "criteria_summary": criteria_summary,
                            "mode_desc":        mode_desc,
                            "limit_value":      limit_value,
                            "save_filename":    save_filename,
                            "batch_id":         batch_id,
                            "matches_log_path": matches_log_path,
                            "_run_log_path":    batch_log_path,
                            "criteria":         criteria,
                        }
                        with open(os.path.join(iter_dir, "backlog_meta.json"),
                                  "w", encoding="utf-8") as _f:
                            _json.dump(_bl_meta, _f, indent=2)
                        if _bg_gpu_active:
                            self._log(
                                f"  [Backlog] {len(captures)} screenshot(s) saved "
                                f"for iteration {iteration} — "
                                f"{len(captures)} queued for GPU analysis immediately.")
                        else:
                            self._log(
                                f"  [Backlog] {len(captures)} screenshot(s) saved "
                                f"for iteration {iteration} — analysis deferred.")
                        # Count only iterations that successfully wrote a meta file.
                        # Iterations with empty captures (Phase 1 abort, settle fail)
                        # do not produce a meta and must not count toward the drain
                        # threshold — otherwise the drain fires short by however many
                        # empty iterations occurred.
                        _iters_since_drain += 1
                    except Exception as _ble:
                        self._log(f"  [Backlog] WARNING: could not save backlog: {_ble}")

                _prev_save_dir = iter_dir

                if self._stop_after_batch:
                    self._log("Iteration capture done — stopping as requested.")
                    break

                # Full abort — captures already saved above; break before drain.
                # _process_backlog_run at the end of the batch will handle them.
                if not self.bot_running:
                    break

                # ── Intermittent backlog drain ───────────────────────── #
                if _intermittent_mode and _iters_since_drain >= _intermittent_every_n:
                    if _bg_gpu_active:
                        # GPU AA mode: GPU has been working continuously — no game-close
                        # needed.  Just open the CPU gate so CPU workers can pick up any
                        # remainder the GPU hasn't reached yet.  CPU workers re-block
                        # themselves once the queue is empty.
                        self._log(
                            f"[Intermittent] {_iters_since_drain} iteration(s) captured — "
                            f"opening CPU gate for remainder (GPU already processing).")
                        _bg_cpu_go_ev.set()
                    else:
                        self._log(
                            f"[Intermittent] {_iters_since_drain} iteration(s) captured — "
                            f"closing game for analysis…")
                        self._set_status("Intermittent: closing game…", "#0066cc")
                        self._close_game()
                        self._set_status("Intermittent: clearing backlog…", "#0066cc")
                        self._process_backlog_run(
                            run_dir, criteria, hit_min,
                            matches_log_path, batch_log_path,
                            criteria_summary, mode_desc, limit_value,
                            save_filename, batch_id, results)
                    _iters_since_drain = 0

                continue

            # ── Normal mode: run phases + post-process inline ─────────── #
            self.after(0, self._show_mouse_blocker)
            relic_results = self._run_iteration_phases(
                label, criteria, region,
                iter_dir=iter_dir, hit_min=hit_min,
                live_log_path=live_log_path, iteration=iteration)
            self.after(0, self._hide_mouse_blocker)
            self._calibrate_from_iteration()   # adjust gap mult from this iteration's data

            if relic_results is None:
                # Fatal error inside phases — abort
                self.after(0, self._reset_controls)
                return

            # Phase 0 failed 3 times — restart the same iteration
            if self._phase0_skipped:
                _phase0_iter_restarts += 1
                self._cancel_and_rollback_iteration(iteration)
                if _phase0_iter_restarts >= _MAX_P0_ITER_RESTARTS:
                    self._log(
                        f"Phase 0 failed on all {_MAX_P0_ITER_RESTARTS} attempts "
                        f"of iteration {iteration} — aborting batch.")
                    self.after(0, self._reset_controls)
                    return
                self._log(
                    f"  Phase 0 failed — restarting iteration {iteration} "
                    f"(attempt {_phase0_iter_restarts + 1}/{_MAX_P0_ITER_RESTARTS}).")
                try:
                    shutil.rmtree(iter_dir, ignore_errors=True)
                except Exception:
                    pass
                _prev_save_dir = None
                _diag_end(); _is_restart = True
                self._async_cancelled_iters.discard(iteration)
                continue

            # User-requested soft nuke of this iteration
            if self._reset_iter_requested:
                self._reset_iter_requested = False
                self._log(f"[Reset] Discarding iteration {iteration} and restarting.")
                self._cancel_and_rollback_iteration(iteration)
                self._close_game()
                try:
                    save_manager.restore(save_path, backup_path)
                except Exception as _rse:
                    self._log(f"  WARNING: save restore failed: {_rse}")
                try:
                    shutil.rmtree(iter_dir, ignore_errors=True)
                except Exception:
                    pass
                _prev_save_dir = None
                _iter_restart_count = 0
                _diag_end(); _is_restart = True
                self._async_cancelled_iters.discard(iteration)
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
                _diag_end(); _is_restart = True
                continue

            if not self.bot_running:
                break

            # Merge all relic results for this iteration into one summary result
            blocked_curses     = self._get_blocked_curses()
            excluded_passives  = self._get_excluded_passives()
            explicitly_included = self._get_explicitly_included_passives()

            _excl_match_results = [
                (i + 1, r) for i, r in enumerate(relic_results)
                if r.get("match")
                and (self._is_curse_blocked(r, blocked_curses)
                     or self._is_passive_excluded(r, excluded_passives, explicitly_included))
            ]
            any_match = any(
                r.get("match")
                and not self._is_curse_blocked(r, blocked_curses)
                and not self._is_passive_excluded(r, excluded_passives, explicitly_included)
                for r in relic_results
            )
            all_relics = [rf for r in relic_results for rf in r.get("relics_found", [])]
            all_near_misses = [nm for r in relic_results for nm in r.get("near_misses", [])]
            matched_result = next(
                (r for r in relic_results
                 if r.get("match")
                 and not self._is_curse_blocked(r, blocked_curses)
                 and not self._is_passive_excluded(r, excluded_passives, explicitly_included)),
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
            # Pairing matches (↔) are labelled HIT at most — never GOD ROLL
            if num_matched > 2 and any("\u2194" in str(p) for p in matched_passives):
                num_matched = 2
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
                tot  = self._ov_total_relics
                q_sto = self._async_relic_q.qsize() if self._async_relic_q else 0
                b33  = _fmt_best(self._best_33_iter,   "★★★")
                bhit = _fmt_best(self._best_hits_iter, "hits")
                self.after(0, lambda: ov.update(
                    hits_33=h33, hits_23=h23, duds=dds,
                    at_33=at33, at_23=at23, at_duds=atd,
                    stored=q_sto, analyzed=tot, best_33=b33, best_hits=bhit,
                ) if ov._win else None)

            # Persist stats after every iteration
            self._save_stats()

            if num_matched >= 3:
                self._log(f"★★★ GOD ROLL — Batch {iteration}: {matched_relic}")
            elif num_matched >= hit_min:
                hit_name = matched_relic or (
                    max(all_near_misses,
                        key=lambda nm: nm.get("matching_passive_count", 0),
                        default={}).get("relic_name", "Unknown")
                )
                self._log(f"★★ HIT — Batch {iteration}: {hit_name}")

            _iter_total_hits = iter_g3 + iter_g2
            if _iter_total_hits > 0:
                self._log(
                    f"  Hits this iteration: {_iter_total_hits} "
                    f"({iter_g3}×3/3, {iter_g2}×2/3)"
                )

            # Write per-iteration info.txt (use combined summary)
            try:
                write_iter_info(iter_dir, iteration, relic_results, hit_min,
                                p_per_relic=self.relic_builder.get_current_p_per_relic())
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

            # ── All Hits folder ───────────────────────────────────────── #
            if num_matched >= hit_min:
                try:
                    _all_hits_dir = os.path.join(run_dir, "All Hits")
                    os.makedirs(_all_hits_dir, exist_ok=True)
                    _hits_summary_path = os.path.join(_all_hits_dir, "hits_summary.txt")
                    for _ah_idx, _ah_rr in enumerate(relic_results):
                        _ah_fname = _ah_rr.get("_screenshot_file", "")
                        if not (_ah_fname and ("HIT" in _ah_fname or "MATCH" in _ah_fname)):
                            continue
                        _ah_src = os.path.join(iter_dir, _ah_fname)
                        if not os.path.exists(_ah_src):
                            continue
                        _ah_rf = (_ah_rr.get("relics_found") or [{}])[0]
                        _ah_passives = _ah_rf.get("passives", []) if isinstance(_ah_rf, dict) else []
                        _ah_curses   = _ah_rf.get("curses",   []) if isinstance(_ah_rf, dict) else []
                        _ah_dst = os.path.join(_all_hits_dir, f"iter_{iteration:03d}_relic_{_ah_idx + 1:03d}.jpg")
                        shutil.copy2(_ah_src, _ah_dst)
                        _write_header = not os.path.exists(_hits_summary_path)
                        with open(_hits_summary_path, "a", encoding="utf-8") as _hf:
                            if _write_header:
                                _hf.write("Matches Found\n")
                                _hf.write("=" * 40 + "\n\n")
                            _hf.write(f"Batch {iteration:03d}  Relic #{_ah_idx + 1:03d}\n")
                            _hf.write("  Passives:\n")
                            for _p in _ah_passives:
                                _hf.write(f"    {_p}\n")
                            if not _ah_passives:
                                _hf.write("    (none)\n")
                            _hf.write("  Curses:\n")
                            for _c in _ah_curses:
                                _hf.write(f"    {_c}\n")
                            if not _ah_curses:
                                _hf.write("    (none)\n")
                            _hf.write("\n")
                except Exception as _ahe:
                    self._log(f"WARNING: could not write to All Hits folder: {_ahe}")

            # ── Excluded Hits folder (opt-in) ─────────────────────────── #
            if _excl_match_results and self._save_exclusion_matches_var.get():
                try:
                    _mex_dir = os.path.join(run_dir, "Excluded Hits")
                    os.makedirs(_mex_dir, exist_ok=True)
                    _mex_info_path = os.path.join(_mex_dir, "Excluded Hits Info.txt")
                    _mex_sep = "─" * 40
                    for _mex_rnum, _mex_rr in _excl_match_results:
                        _mex_fname = _mex_rr.get("_screenshot_file", "")
                        _mex_rf = (_mex_rr.get("relics_found") or [{}])[0]
                        _mex_rname    = _mex_rf.get("name", "Unknown") if isinstance(_mex_rf, dict) else "Unknown"
                        _mex_passives = _mex_rf.get("passives", []) if isinstance(_mex_rf, dict) else []
                        _mex_curses   = _mex_rf.get("curses",   []) if isinstance(_mex_rf, dict) else []
                        _mex_excl_names = set(self._get_excluded_passive_names(
                            _mex_rr, excluded_passives, explicitly_included))
                        _mex_dst_fname = f"Iter_{iteration}_Relic_{_mex_rnum}_EXCL.jpg"
                        if _mex_fname:
                            _mex_src = os.path.join(iter_dir, _mex_fname)
                            if os.path.exists(_mex_src):
                                _mex_dst = os.path.join(_mex_dir, _mex_dst_fname)
                                try:
                                    shutil.move(_mex_src, _mex_dst)
                                except Exception:
                                    shutil.copy2(_mex_src, _mex_dst)
                        with open(_mex_info_path, "a", encoding="utf-8") as _ef:
                            _ef.write(
                                f"{_mex_sep}\n"
                                f"  Iter #{iteration:03d}  ·  Relic {_mex_rnum}"
                                f"  [{_mex_dst_fname}]\n"
                                f"  Relic : {_mex_rname}\n"
                                + "".join(
                                    f"  + {p}{'  [EXCLUDED]' if p in _mex_excl_names else ''}\n"
                                    for p in _mex_passives)
                                + ("  (no passives)\n" if not _mex_passives else "")
                                + "".join(f"  ✗ {c}  (curse)\n" for c in _mex_curses)
                                + "\n"
                            )
                    if _excl_match_results:
                        self._log(
                            f"  {len(_excl_match_results)} relic(s) matched criteria but had "
                            f"excluded passive(s) — saved to 'Excluded Hits' folder.")
                except Exception as _mexe:
                    self._log(f"WARNING: could not write to Excluded Hits folder: {_mexe}")
            elif _excl_match_results:
                self._log(
                    f"  {len(_excl_match_results)} relic(s) matched criteria but had "
                    f"excluded passive(s) (opt-in folder disabled).")

            # Deferred save copy — set AFTER any rename so the path is always valid
            _prev_save_dir = iter_dir
            _diag_end("ok")

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
                generate_readme(run_dir, criteria_summary, mode_desc, limit_value, results, hit_min,
                                p_per_relic=self.relic_builder.get_current_p_per_relic())
            except Exception:
                pass
            try:
                generate_priority_summary(run_dir, results)
            except Exception:
                pass

            # Graceful stop — user requested stop after this iteration
            if self._stop_after_batch:
                self._log("Iteration finished — stopping as requested.")
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
        # Release workers blocked by excl-ops mode so they can drain the queue.
        if _excl_ops_mode:
            self._set_ocr_throttle(False)
        if _async_mode and _async_relic_q is not None:
            self._set_status("Waiting for background analysis to finish…", "orange")
            self._log("Grace period: waiting for async analysis to complete…")
            _shutdown_async_workers()
            # Scale grace period by remaining queue size so slow/CPU-only hardware
            # gets enough time to process all pending relics.  Each relic is budgeted
            # 20 s; floor is the per-task timeout so small queues are unaffected.
            _q_remaining = _async_relic_q.qsize()
            _end_grace   = max(_ASYNC_TASK_TIMEOUT, _q_remaining * 20)
            _async_join_timed(grace=_end_grace)
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

        # ── Clear async state refs (no longer needed after workers done) ──
        self._ocr_go_event       = None
        self._async_iter_state   = None
        self._async_dir_map      = None
        self._async_state_lock   = None
        self._async_results_list = None

        # ── Diagnostic: close logger (writes summary, stops hook monitor) ──
        if self._diag:
            try:
                self._diag.close()
            except Exception:
                pass
            finally:
                self._diag = None
                self.player.diag = None

        # ── Backlog mode: process all deferred screenshots ─────────────── #
        if _backlog_mode and _run_dir_created[0]:
            if _bg_gpu_active and _bg_gpu_q is not None:
                # Drain the persistent background GPU+CPU workers.
                # Open CPU gate one final time so CPU workers clear any remainder,
                # then signal done and wait for the queue to empty.
                self._log("[BG-GPU] Waiting for background workers to drain…")
                self._set_status("Background GPU: draining queue…", "#0066cc")
                _bg_cpu_go_ev.set()
                _bg_done_ev.set()
                _bg_gpu_q.join()
                for _bgt in [_bg_worker] + _bg_cpu_threads:
                    if _bgt:
                        _bgt.join(timeout=5.0)

                # ── Retry pass for GPU-failed relics ──────────────────── #
                _bg_retry_dir = os.path.join(run_dir, "_retry_staging")
                if os.path.isdir(_bg_retry_dir):
                    _bg_retry_files = sorted(
                        f for f in os.listdir(_bg_retry_dir) if f.endswith(".jpg"))
                    _bg_valid = []
                    for _brf in _bg_retry_files:
                        _brp = _brf.replace(".jpg", "").split("_")
                        if (len(_brp) != 4 or _brp[0] != "Iter"
                                or _brp[2] != "Relic"):
                            continue
                        try:
                            _br_iter = int(_brp[1])
                            _br_si   = int(_brp[3]) - 1
                        except ValueError:
                            continue
                        if _br_iter not in _bg_bl_state:
                            continue
                        _bg_valid.append(
                            (_br_iter, _br_si, os.path.join(_bg_retry_dir, _brf)))
                    if _bg_valid:
                        self._log(
                            f"[BG-GPU] Retry pass: {len(_bg_valid)} relic(s).")
                        self._set_status("Background GPU: retry pass…", "#0066cc")
                        relic_analyzer.set_thread_device(False)
                        try:
                            for _br_iter, _br_si, _br_path in _bg_valid:
                                if not os.path.exists(_br_path):
                                    continue
                                _brs = _bg_bl_state[_br_iter]
                                try:
                                    with open(_br_path, "rb") as _brf2:
                                        _br_img = _brf2.read()
                                except Exception:
                                    continue
                                _br_task = {
                                    "iteration":         _br_iter,
                                    "step_i":            _br_si,
                                    "img_bytes":         _br_img,
                                    "pending_path":      "",
                                    "_backlog_img_path": _br_path,
                                    "_retry_pass":       True,
                                    "iter_dir":          _brs["iter_dir"],
                                    "criteria":          criteria,
                                    "hit_min":           _brs["hit_min"],
                                    "live_log_path":     _brs["live_log_path"],
                                    "matches_log_path":  _brs["matches_log_path"],
                                    "run_dir":           run_dir,
                                    "criteria_summary":  _brs["criteria_summary"],
                                    "mode_desc":         _brs["mode_desc"],
                                    "limit_value":       _brs["limit_value"],
                                    "save_filename":     _brs["save_filename"],
                                    "batch_id":          _brs["batch_id"],
                                    "_run_log_path":     _brs["_run_log_path"],
                                    "_retries":          0,
                                }
                                try:
                                    self._analyze_relic_task(
                                        _br_task, _bg_bl_state, _bg_bl_lock,
                                        _bg_bl_dmap, results)
                                except Exception as _bre:
                                    self._log(f"  [BG-GPU Retry] Error: {_bre}")
                        finally:
                            relic_analyzer.set_thread_device(None)
                        self._log("[BG-GPU] Retry pass complete.")
                    try:
                        shutil.rmtree(_bg_retry_dir)
                    except Exception:
                        pass

                # Mark all GPU-processed iterations as done so
                # _process_backlog_run skips them.
                for _bg_iter_num, _bg_idata in _bg_bl_state.items():
                    _bg_src = os.path.join(_bg_idata["iter_dir"], "backlog_meta.json")
                    _bg_dst = os.path.join(_bg_idata["iter_dir"], "backlog_meta_done.json")
                    try:
                        if os.path.exists(_bg_src):
                            os.rename(_bg_src, _bg_dst)
                    except Exception:
                        pass

                _bg_total = sum(v["done"] for v in _bg_bl_state.values())
                self._log(
                    f"[BG-GPU] Complete — {_bg_total} relic(s) analyzed by "
                    f"background GPU worker.")

            # Always call _process_backlog_run: handles any iterations that were
            # not processed by the background GPU worker (e.g. partial final batch
            # if the run was stopped early) and the retry pass for those.
            self._process_backlog_run(
                run_dir, criteria, hit_min,
                matches_log_path, batch_log_path,
                criteria_summary, mode_desc, limit_value,
                save_filename, batch_id, results)

        # Batch finished – generate README and PRIORITY.txt
        if results and _run_dir_created[0]:
            try:
                generate_readme(run_dir, criteria_summary, mode_desc, limit_value, results, hit_min,
                                p_per_relic=self.relic_builder.get_current_p_per_relic())
                self._log(f"README.txt written to {run_dir}")
            except Exception as e:
                self._log(f"WARNING: could not write README: {e}")
            try:
                generate_priority_summary(run_dir, results)
                self._log(f"PRIORITY.txt written to {run_dir}")
            except Exception as e:
                self._log(f"WARNING: could not write PRIORITY.txt: {e}")

        self._run_backup_path = None   # clear so stale path can't be reused

        # ── Restore save to original clean state ──────────────────────── #
        # Done after all analysis so the live save is always left as it was
        # before the run started, regardless of how the run ended.
        try:
            save_manager.restore(save_path, backup_path)
            self._log("Save file restored to original state.")
        except Exception as _sre:
            self._log(f"WARNING: could not restore save at run end: {_sre}")

        # ── Finalise backup folder name with actual iteration count ────── #
        _actual_iters = len(results)
        _final_bk_dir = save_manager.finalize_backup_dir(_backup_dir, _actual_iters)
        self._log(f"Backup saved: {os.path.basename(_final_bk_dir)}")

        match_count  = sum(1 for r in results if r["match"])
        total_hits33 = sum(r.get("hits_33", 0) for r in results)
        total_hits23 = sum(r.get("hits_23", 0) for r in results)
        total_hits   = total_hits33 + total_hits23
        # ── Batch reliability summary ─────────────────────────────────── #
        _n_iters = len(results)
        _avg_poll = (
            f"{self._batch_total_poll_depth / self._batch_total_settled:.1f}"
            if self._batch_total_settled > 0 else "n/a"
        )
        self._log("=" * 60)
        self._log(f"[Reliability Summary]  {_n_iters} batch(es) completed")
        self._log(f"  Phase 0 extra attempts : {self._batch_p0_extra}")
        self._log(f"  Phase 1 settle retries : {self._batch_settle_retries}")
        self._log(f"  Safe buy path used     : {self._batch_safe_path_count} iter(s)")
        self._log(f"  Avg settle poll depth  : {_avg_poll}  (1.0 = instant, 8 = worst)")
        self._log(f"  Final gap mult         : {self._perf_gap_mult:.3f}×")
        self._log("=" * 60)

        self._log(
            f"Run complete. {len(results)} batch(es) run, {match_count} match(es) found."
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

    def _process_backlog_run(self, run_dir: str, criteria: dict, hit_min: int,
                             matches_log_path: str, batch_log_path: str,
                             criteria_summary: str, mode_desc: str,
                             limit_value: float, save_filename: str,
                             batch_id: str, results: list) -> None:
        """Process all screenshots saved during a Backlog Analysis run.

        Scans run_dir for iter*/backlog/ folders, reconstructs async worker
        state for each iteration, and processes each saved screenshot through
        the full _analyze_relic_task pipeline (hits, Smart Analyze, All Hits
        folder, etc.).  Runs while the game is not competing for CPU.
        """
        import json as _json

        # ── Collect all backlog items grouped by iteration ─────────── #
        backlog_by_iter: dict[int, dict] = {}
        try:
            for entry in sorted(os.listdir(run_dir)):
                iter_d    = os.path.join(run_dir, entry)
                meta_path = os.path.join(iter_d, "backlog_meta.json")
                done_path = os.path.join(iter_d, "backlog_meta_done.json")
                if not os.path.isdir(iter_d) or not os.path.exists(meta_path):
                    continue
                # Skip folders already processed by a previous intermittent drain
                if os.path.exists(done_path):
                    continue
                try:
                    with open(meta_path, encoding="utf-8") as _f:
                        meta = _json.load(_f)
                except Exception as _me:
                    self._log(f"  [Backlog] Could not read metadata in {iter_d}: {_me}")
                    continue
                # Collect (step_i, img_path) pairs sorted by relic index.
                # File naming: Iter_{n}_Relic_{r}.jpg  e.g. Iter_1_Relic_3.jpg
                relics = []
                for img_name in sorted(os.listdir(iter_d)):
                    if not img_name.endswith(".jpg"):
                        continue
                    # Only pick up unprocessed captures: Iter_N_Relic_R.jpg
                    # Skip files already tagged _MATCH/_HIT/_SMART etc.
                    _parts = img_name.replace(".jpg", "").split("_")
                    if (len(_parts) != 4
                            or _parts[0] != "Iter"
                            or _parts[2] != "Relic"):
                        continue
                    try:
                        _si = int(_parts[3]) - 1
                    except ValueError:
                        continue
                    relics.append((_si, os.path.join(iter_d, img_name)))
                if relics:
                    backlog_by_iter[meta["iteration"]] = {
                        "meta":   meta,
                        "relics": relics,
                    }
        except Exception as _se:
            self._log(f"  [Backlog] Error scanning run dir: {_se}")
            return

        if not backlog_by_iter:
            self._log("  [Backlog] No saved screenshots found — nothing to process.")
            return

        total_relics = sum(len(v["relics"]) for v in backlog_by_iter.values())
        self._log(
            f"[Backlog] Starting post-run analysis: "
            f"{total_relics} relic(s) across {len(backlog_by_iter)} iteration(s).")
        self._set_status("Backlog: running post-run analysis…", "#0066cc")

        # ── Set up async-style state for _analyze_relic_task ───────── #
        _bl_state: dict = {}
        _bl_lock  = threading.Lock()
        _bl_dmap: dict = {}

        for iteration, item in backlog_by_iter.items():
            meta = item["meta"]
            _bl_state[iteration] = {
                "total":          len(item["relics"]),
                "done":           0,
                "results":        [],
                "iter_dir":       meta.get("iter_dir", ""),
                "hit_min":        meta.get("hit_min", hit_min),
                "live_log_path":  meta.get("live_log_path", ""),
                "run_dir":        run_dir,
                "criteria_summary": meta.get("criteria_summary", criteria_summary),
                "mode_desc":      meta.get("mode_desc", mode_desc),
                "limit_value":    meta.get("limit_value", limit_value),
                "save_filename":  meta.get("save_filename", save_filename),
                "batch_id":       meta.get("batch_id", batch_id),
                "matches_log_path": meta.get("matches_log_path", matches_log_path),
                "_run_log_path":  meta.get("_run_log_path", batch_log_path),
            }
            _bl_dmap[iteration] = meta.get("iter_dir", "")

        # ── Worker pool: process images from disk ───────────────────── #
        _bl_gpu_on  = self._gpu_accel_var.get()
        _worker_max = min(8, max(2, self._hw_cpu_cores or 8))
        _workers    = (max(2, min(_worker_max, self._parallel_workers_var.get()))
                       if self._parallel_enabled_var.get() else 1)
        _hybrid     = (_bl_gpu_on
                       and self._hybrid_var.get()
                       and self._parallel_enabled_var.get())
        # Sync global GPU mode with the backlog run's intended device so
        # the retry-pass (which runs on the bot thread without a thread-local
        # override) falls back to the correct device rather than whatever the
        # last UI toggle left behind.
        relic_analyzer.set_gpu_mode(_bl_gpu_on)
        _bl_q    = queue.PriorityQueue()
        _done_ev = threading.Event()

        def _make_bl_worker(use_gpu):
            from bot import relic_analyzer as _ra
            def _worker():
                _ra.set_thread_device(use_gpu)   # pin this thread's device before first analyze()
                while True:
                    try:
                        _prio, _task = _bl_q.get(timeout=0.3)
                    except queue.Empty:
                        if _done_ev.is_set() and _bl_q.empty():
                            break
                        continue
                    # When GPU Always Analyze is on, the GPU worker skips the
                    # gate entirely — GPU inference doesn't compete for CPU time.
                    # All other workers (CPU workers, or GPU worker with AA off)
                    # respect the shared gate as normal.
                    if not (use_gpu and self._gpu_always_analyze_var.get()):
                        _go_ev = self._ocr_go_event
                        if _go_ev is not None and not _go_ev.is_set():
                            while not _go_ev.wait(timeout=1.0):
                                pass
                    try:
                        self._analyze_relic_task(
                            _task, _bl_state, _bl_lock, _bl_dmap, results)
                    except Exception as _we:
                        self._log(f"  [Backlog] Worker error: {_we}")
                    finally:
                        _bl_q.task_done()
            return _worker

        if _hybrid:
            _gpu_aa_bl = self._gpu_always_analyze_var.get()
            if _gpu_aa_bl:
                # GPU Always Analyze on: GPU worker handles all tasks alone.
                # In backlog mode there is no throttle gate to bypass (unlike
                # async), so "Always Analyze" is implemented by suppressing the
                # CPU workers entirely — GPU does 100% of the analysis.
                self._log("  [Backlog] Hybrid GPU+CPU + GPU Always Analyze: GPU worker only (CPU suppressed).")
                _bl_threads = [
                    threading.Thread(target=_make_bl_worker(True), daemon=True,
                                     name="backlog-worker-gpu"),
                ]
            else:
                # 1 GPU worker + N CPU workers — both pull from the same queue.
                self._log(f"  [Backlog] Hybrid GPU+CPU: 1 GPU worker + {_workers} CPU worker(s).")
                _bl_threads = [
                    threading.Thread(target=_make_bl_worker(True), daemon=True,
                                     name="backlog-worker-gpu"),
                ] + [
                    threading.Thread(target=_make_bl_worker(False), daemon=True,
                                     name=f"backlog-worker-cpu-{_n}")
                    for _n in range(_workers)
                ]
        elif _bl_gpu_on:
            # GPU only — 1 dedicated GPU worker, no CPU workers.
            self._log("  [Backlog] GPU mode: 1 GPU worker.")
            _bl_threads = [
                threading.Thread(target=_make_bl_worker(True), daemon=True,
                                 name="backlog-worker-gpu"),
            ]
        else:
            # CPU only — N workers from the Brute Force spinbox (or 1 if off).
            _bl_threads = [
                threading.Thread(target=_make_bl_worker(None), daemon=True,
                                 name=f"backlog-worker-{_n}")
                for _n in range(_workers)
            ]
        for _t in _bl_threads:
            _t.start()

        # ── Enqueue all relic tasks ─────────────────────────────────── #
        _enqueued = 0
        for iteration in sorted(backlog_by_iter):
            item = backlog_by_iter[iteration]
            meta = item["meta"]
            _iter_criteria = meta.get("criteria", criteria)
            _iter_live_log = _bl_state[iteration]["live_log_path"]

            for _si, img_path in item["relics"]:
                if not self.bot_running:
                    break
                try:
                    with open(img_path, "rb") as _f:
                        _img = _f.read()
                except Exception as _re:
                    self._log(
                        f"  [Backlog] Could not load {img_path}: {_re}")
                    # Decrement expected total so iter can still finalize
                    with _bl_lock:
                        if iteration in _bl_state:
                            _bl_state[iteration]["total"] = max(
                                0, _bl_state[iteration]["total"] - 1)
                    continue

                _task = {
                    "iteration":         iteration,
                    "step_i":            _si,
                    "img_bytes":         _img,
                    "pending_path":      "",
                    "_backlog_img_path": img_path,   # on-disk file to manage after analysis
                    "iter_dir":          _bl_state[iteration]["iter_dir"],
                    "criteria":          _iter_criteria,
                    "hit_min":           _bl_state[iteration]["hit_min"],
                    "live_log_path":     _iter_live_log,
                    "matches_log_path":  _bl_state[iteration]["matches_log_path"],
                    "run_dir":           run_dir,
                    "criteria_summary":  _bl_state[iteration]["criteria_summary"],
                    "mode_desc":         _bl_state[iteration]["mode_desc"],
                    "limit_value":       _bl_state[iteration]["limit_value"],
                    "save_filename":     _bl_state[iteration]["save_filename"],
                    "batch_id":          _bl_state[iteration]["batch_id"],
                    "_run_log_path":     _bl_state[iteration]["_run_log_path"],
                    "crop_left":         relic_analyzer._PREVIEW_CROP_LEFT_FRAC,
                    "crop_top":          relic_analyzer._PREVIEW_CROP_TOP_FRAC,
                    "_retries":          0,
                }
                _bl_q.put(((iteration, _si), _task))
                _enqueued += 1

                _done_so_far = sum(
                    v["done"] for v in _bl_state.values())
                self._set_status(
                    f"Backlog: analyzed {_done_so_far}/{total_relics} relic(s)…",
                    "#0066cc")

        _done_ev.set()

        # ── Wait for all workers ────────────────────────────────────── #
        _bl_q.join()
        for _t in _bl_threads:
            _t.join(timeout=2.0)

        _done_count = sum(v["done"] for v in _bl_state.values())
        self._log(
            f"[Backlog] Analysis complete — {_done_count}/{total_relics} "
            f"relic(s) processed.")

        # ── Retry staging pass ──────────────────────────────────────────── #
        # Any relics whose initial OCR failed were moved to _retry_staging/
        # by _mark_relic_failed, preserving their Iter_N_Relic_R.jpg name.
        # We process them here unconditionally — even if the user stopped the
        # bot — so the staging folder is always cleaned up at the end.
        _retry_dir = os.path.join(run_dir, "_retry_staging")
        if os.path.isdir(_retry_dir):
            _retry_files = sorted(
                f for f in os.listdir(_retry_dir) if f.endswith(".jpg"))
            _valid_retries = []
            for _rf in _retry_files:
                _rparts = _rf.replace(".jpg", "").split("_")
                if (len(_rparts) != 4
                        or _rparts[0] != "Iter"
                        or _rparts[2] != "Relic"):
                    continue
                try:
                    _r_iter = int(_rparts[1])
                    _r_si   = int(_rparts[3]) - 1
                except ValueError:
                    continue
                if _r_iter not in _bl_state:
                    continue
                _valid_retries.append(
                    (_r_iter, _r_si, os.path.join(_retry_dir, _rf)))

            if _valid_retries:
                self._log(
                    f"[Backlog] Retry pass: {len(_valid_retries)} relic(s) "
                    f"that failed initial analysis.")
                self._set_status("Backlog: retry pass…", "#0066cc")

                def _run_retry_pass(retry_entries, pass_label):
                    """Process one list of (iter, si, path) retry entries.

                    Retries always run on CPU regardless of the global GPU mode.
                    Tasks that reached retry staging already failed once (possibly
                    due to GPU init / CUDA issues); CPU is the reliable fallback.
                    """
                    relic_analyzer.set_thread_device(False)   # pin retry pass to CPU
                    try:
                        for _r_iter, _r_si, _r_path in retry_entries:
                            if not os.path.exists(_r_path):
                                continue   # already handled somehow
                            _r_istate   = _bl_state[_r_iter]
                            _r_iter_dir = _bl_dmap.get(_r_iter, _r_istate.get("iter_dir", ""))
                            _r_meta     = backlog_by_iter.get(_r_iter, {}).get("meta", {})
                            try:
                                with open(_r_path, "rb") as _f:
                                    _r_img = _f.read()
                            except Exception as _rle:
                                self._log(
                                    f"  [{pass_label}] Could not load"
                                    f" Iter {_r_iter} Relic {_r_si + 1}: {_rle}")
                                continue
                            # Build a fresh task dict — img_bytes is zeroed by
                            # _analyze_relic_task on completion.
                            _retry_task = {
                                "iteration":         _r_iter,
                                "step_i":            _r_si,
                                "img_bytes":         _r_img,
                                "pending_path":      "",
                                "_backlog_img_path": _r_path,
                                "_retry_pass":       True,
                                "iter_dir":          _r_iter_dir,
                                "criteria":          _r_meta.get("criteria", criteria),
                                "hit_min":           _r_istate["hit_min"],
                                "live_log_path":     _r_istate["live_log_path"],
                                "matches_log_path":  _r_istate["matches_log_path"],
                                "run_dir":           run_dir,
                                "criteria_summary":  _r_istate["criteria_summary"],
                                "mode_desc":         _r_istate["mode_desc"],
                                "limit_value":       _r_istate["limit_value"],
                                "save_filename":     _r_istate["save_filename"],
                                "batch_id":          _r_istate["batch_id"],
                                "_run_log_path":     _r_istate["_run_log_path"],
                                "_retries":          0,
                            }
                            try:
                                self._analyze_relic_task(
                                    _retry_task, _bl_state, _bl_lock, _bl_dmap, results)
                            except Exception as _rte:
                                self._log(
                                    f"  [{pass_label}] Unexpected error"
                                    f" Iter {_r_iter} Relic {_r_si + 1}: {_rte}")
                    finally:
                        relic_analyzer.set_thread_device(None)   # restore thread-local state

                # ── Pass 1: files in _retry_staging/ ────────────────────── #
                _run_retry_pass(_valid_retries, "Backlog Retry")

                # ── Pass 2: any that _mark_relic_failed escalated to
                #    retry_last_try/ during pass 1 ─────────────────────── #
                _last_try_dir = os.path.join(_retry_dir, "retry_last_try")
                if os.path.isdir(_last_try_dir):
                    _lt_files = sorted(
                        f for f in os.listdir(_last_try_dir) if f.endswith(".jpg"))
                    _lt_entries = []
                    for _ltf in _lt_files:
                        _ltp = _ltf.replace(".jpg", "").split("_")
                        if (len(_ltp) != 4
                                or _ltp[0] != "Iter"
                                or _ltp[2] != "Relic"):
                            continue
                        try:
                            _lt_iter = int(_ltp[1])
                            _lt_si   = int(_ltp[3]) - 1
                        except ValueError:
                            continue
                        if _lt_iter not in _bl_state:
                            continue
                        _lt_entries.append(
                            (_lt_iter, _lt_si,
                             os.path.join(_last_try_dir, _ltf)))
                    if _lt_entries:
                        self._log(
                            f"[Backlog] Last-try pass: {len(_lt_entries)} relic(s).")
                        _run_retry_pass(_lt_entries, "Backlog Last-Try")

                self._log("[Backlog] Retry pass complete.")

            # Always delete the staging folder — empty or not
            try:
                shutil.rmtree(_retry_dir)
            except Exception:
                pass

        # ── Mark processed iter folders so re-runs don't double-process ── #
        for _iter_num, _item in backlog_by_iter.items():
            _iter_d = _item["meta"].get("iter_dir", "")
            _src = os.path.join(_iter_d, "backlog_meta.json")
            _dst = os.path.join(_iter_d, "backlog_meta_done.json")
            try:
                if os.path.exists(_src):
                    os.rename(_src, _dst)
            except Exception as _re:
                self._log(
                    f"  [Backlog] Warning: could not mark iter {_iter_num} "
                    f"as processed: {_re}")

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

    def _write_match_log(self, matches_log_path: str, iteration: int,
                         relic_num: int, tier: str, result: dict) -> None:
        """Write a match entry to matches_log.txt and push it to the overlay.

        Called from async worker threads — uses only self.after() for UI
        updates so it is safe to call from any thread.
        """
        relics = result.get("relics_found", [])
        r0 = relics[0] if relics else {}
        rname    = r0.get("name", "Unknown") if isinstance(r0, dict) else "Unknown"
        passives = r0.get("passives", []) if isinstance(r0, dict) else []
        curses   = r0.get("curses",   []) if isinstance(r0, dict) else []

        sep   = "─" * 40
        lines = [
            sep,
            f"  {tier}  |  Iter #{iteration:03d}  ·  Relic {relic_num}",
            f"  Relic : {rname}",
        ]
        for p in passives:
            lines.append(f"  + {p}")
        for c in curses:
            lines.append(f"  ✗ {c}  (curse)")
        lines.append("")

        text = "\n".join(lines) + "\n"
        if matches_log_path:
            try:
                with open(matches_log_path, "a", encoding="utf-8") as _f:
                    _f.write(text)
            except Exception:
                pass
        if self._overlay:
            ov = self._overlay
            self.after(0, lambda t=text: ov.append_matches_log(t)
                       if ov._win else None)

    def _analyze_relic_task(self, task: dict, iter_state: dict,
                            lock: threading.Lock, dir_map: dict,
                            results: list) -> None:
        """OCR-analyze one captured relic (called from async relic worker thread)."""
        iteration          = task["iteration"]
        step_i             = task["step_i"]
        img_bytes          = task["img_bytes"]
        task["img_bytes"]  = None  # release from queue task dict immediately — don't hold
                                   # two copies of the screenshot while OCR is running
        pending_path       = task["pending_path"]
        iter_dir           = task["iter_dir"]
        run_dir            = task.get("run_dir", os.path.dirname(iter_dir))
        # Backlog mode: path of the on-disk file that was pre-saved during capture.
        # When set, file management (rename/move/delete) replaces in-memory writes.
        _backlog_img_path  = task.get("_backlog_img_path", "")
        criteria      = task["criteria"]
        hit_min       = task["hit_min"]
        live_log_path = task["live_log_path"]
        is_current_batch = task.get("batch_id") == self._current_batch_id

        # Memory pressure gate: if available RAM is critically low, hold off until
        # it recovers. The game loading during iteration N+1 can consume several GB
        # which leaves PyTorch/EasyOCR unable to allocate even small tensors.
        _MEM_THRESHOLD_MB = 400
        _mem_wait_logged  = False
        while _available_ram_mb() < _MEM_THRESHOLD_MB:
            if not self.bot_running:
                return
            if not _mem_wait_logged:
                self._log(
                    f"  [Worker] Low RAM — pausing OCR for relic {step_i + 1} "
                    f"(iter {iteration}) until memory recovers…", overlay=False)
                _mem_wait_logged = True
            time.sleep(1.0)

        crop_left  = task.get("crop_left",  relic_analyzer._CROP_LEFT_FRAC)
        crop_top   = task.get("crop_top",   relic_analyzer._CROP_TOP_FRAC)
        relic_type = task.get("relic_type", "")
        try:
            _ocr_t0 = time.perf_counter()
            result = relic_analyzer.analyze(img_bytes, criteria,
                                            crop_left=crop_left,
                                            crop_top=crop_top,
                                            relic_type=relic_type)
            _ocr_dur = time.perf_counter() - _ocr_t0
            _gpu_was_on = bool(getattr(self, "_gpu_accel_var", None)
                               and self._gpu_accel_var.get())
            self._record_ocr_timing(_ocr_dur, gpu=_gpu_was_on)
        except Exception as exc:
            if is_current_batch:
                self._log(f"  [Async iter {iteration}] ERROR relic {step_i + 1}: {exc}")
            self._mark_relic_failed(task, iter_state, lock, dir_map, results)
            img_bytes = None
            gc.collect()
            return
        finally:
            gc.collect()   # return freed tensor memory to the OS promptly

        if pending_path and os.path.exists(pending_path):
            try:
                os.remove(pending_path)
            except Exception:
                pass

        # Log raw OCR token dump to DiagnosticLogger
        _ocr_tokens = result.pop("_ocr_tokens", None)
        if _ocr_tokens and self._diag is not None:
            try:
                self._diag.log_ocr_dump(iteration, step_i, _ocr_tokens)
            except Exception:
                pass

        # Route per-relic log output: current batch → UI panel; old batch → its own run_log
        if is_current_batch:
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

        # Smart Analyze: evaluate non-matching relics against curated rules
        _smart_reasons: list[str] = []
        _smart_file_handled = False   # set when backlog file moved to smart dir
        if (self._smart_analyze_var.get()
                and is_current_batch
                and not result.get("match", False)):
            try:
                from bot.smart_rules import evaluate_relic as _eval_relic
                relics_sa = result.get("relics_found", [])
                r0_sa = relics_sa[0] if relics_sa else {}
                passives_sa = (r0_sa.get("passives", [])
                               if isinstance(r0_sa, dict) else [])
                _smart_reasons = _eval_relic(passives_sa)
                if _smart_reasons and iter_dir:
                    smart_dir = os.path.join(run_dir, "Smart Analyze Hits")
                    os.makedirs(smart_dir, exist_ok=True)
                    sa_fname = f"Iter_{iteration}_Relic_{step_i + 1}_SMART.jpg"
                    try:
                        if _backlog_img_path and os.path.exists(_backlog_img_path):
                            # Backlog: move the pre-saved file instead of writing bytes again
                            import shutil as _shutil
                            _shutil.move(_backlog_img_path,
                                         os.path.join(smart_dir, sa_fname))
                            _smart_file_handled = True
                        elif img_bytes:
                            with open(os.path.join(smart_dir, sa_fname), "wb") as _f:
                                _f.write(img_bytes)
                        _sa_relics = result.get("relics_found", [])
                        _sa_r0 = _sa_relics[0] if _sa_relics else {}
                        _sa_rname = _sa_r0.get("name", "Unknown") if isinstance(_sa_r0, dict) else "Unknown"
                        _sa_pass  = _sa_r0.get("passives", []) if isinstance(_sa_r0, dict) else []
                        _sa_curse = _sa_r0.get("curses",   []) if isinstance(_sa_r0, dict) else []
                        _sa_sep   = "─" * 40
                        with open(os.path.join(smart_dir, "Smart Analyze Info.txt"), "a",
                                  encoding="utf-8") as _f:
                            _f.write(
                                f"{_sa_sep}\n"
                                f"  Iter #{iteration:03d}  ·  Relic {step_i + 1}"
                                f"  [{sa_fname}]\n"
                                f"  Relic : {_sa_rname}\n"
                                + "".join(f"  + {p}\n" for p in _sa_pass)
                                + "".join(f"  ✗ {c}  (curse)\n" for c in _sa_curse)
                                + "  Smart rules:\n"
                                + "".join(f"    • {r}\n" for r in _smart_reasons)
                                + "\n"
                            )
                        self._log(
                            f"  [Smart] Relic {step_i + 1} — {'; '.join(_smart_reasons)}",
                            overlay=True)
                    except Exception:
                        pass
                    self._ov_smart_hits += 1
                    if self._overlay:
                        _sh = self._ov_smart_hits
                        self.after(0, lambda _sh=_sh:
                                   self._overlay.update(smart_hits=_sh)
                                   if self._overlay and self._overlay._win else None)
            except Exception:
                pass

        saved_fname = ""
        is_match = result.get("match", False)
        best_nm = max(
            (nm.get("matching_passive_count",
                     len(nm.get("matching_passives", [])))
             for nm in result.get("near_misses", [])),
            default=0,
        )
        tag = "MATCH" if is_match else ("HIT" if best_nm >= hit_min else "")

        if iter_dir and tag:
            if _backlog_img_path and os.path.exists(_backlog_img_path):
                # Backlog: rename the pre-saved file to add the result tag.
                # No duplicate write needed — content is already on disk.
                saved_fname = f"Iter_{iteration}_Relic_{step_i + 1}_{tag}.jpg"
                try:
                    os.rename(_backlog_img_path,
                              os.path.join(iter_dir, saved_fname))
                    if is_current_batch:
                        self._log(f"  Screenshot saved: {saved_fname}", overlay=False)
                except Exception as _e:
                    if is_current_batch:
                        self._log(f"WARNING: could not rename screenshot: {_e}")
                    saved_fname = ""
            elif img_bytes:
                saved_fname = f"Iter_{iteration}_Relic_{step_i + 1}_{tag}.jpg"
                try:
                    with open(os.path.join(iter_dir, saved_fname), "wb") as _f:
                        _f.write(img_bytes)
                    if is_current_batch:
                        self._log(f"  Screenshot saved: {saved_fname}", overlay=False)
                except Exception as _e:
                    if is_current_batch:
                        self._log(f"WARNING: could not save screenshot: {_e}")
                    saved_fname = ""

        # Backlog only: delete the on-disk file if this relic is neither a
        # match/HIT nor a Smart Analyze hit — no reason to keep it.
        if (_backlog_img_path
                and not _smart_file_handled
                and not saved_fname
                and os.path.exists(_backlog_img_path)):
            try:
                os.remove(_backlog_img_path)
            except Exception:
                pass

        img_bytes = None   # release screenshot bytes after saving (or skipping if not a hit)

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

        # Only update current-batch overlay counters; skip if this iteration was cancelled
        if is_current_batch and iteration not in self._async_cancelled_iters:
            r_g3, r_g2, r_dud = self._count_relic_tiers([result], hit_min)
            self._ov_at_33        += r_g3
            self._ov_at_23        += r_g2
            self._ov_at_duds      += r_dud
            self._ov_total_relics += r_g3 + r_g2 + r_dud
            # Track this iteration's contributions so it can be rolled back on cancel
            with self._iter_contrib_lock:
                c = self._iter_contributions.setdefault(iteration, {})
                c["at_33"]        = c.get("at_33",        0) + r_g3
                c["at_23"]        = c.get("at_23",        0) + r_g2
                c["at_duds"]      = c.get("at_duds",      0) + r_dud
                c["total_relics"] = c.get("total_relics", 0) + r_g3 + r_g2 + r_dud
            if self._overlay:
                ov = self._overlay
                at33, at23, atd = self._ov_at_33, self._ov_at_23, self._ov_at_duds
                tot = self._ov_total_relics
                self._ov_stored_count = max(0, self._ov_stored_count - 1)
                sto = self._ov_stored_count
                self.after(0, lambda at33=at33, at23=at23, atd=atd, tot=tot, sto=sto:
                           ov.update(at_33=at33, at_23=at23, at_duds=atd, stored=sto, analyzed=tot)
                           if ov._win else None)
            if r_g3 > 0 or r_g2 > 0:
                # Check if this relic would be excluded at finalization so the
                # per-relic log message correctly labels it rather than announcing
                # a full match that will later be moved to Excluded Hits.
                _excl_passives = self._get_excluded_passives()
                _excl_incl     = self._get_explicitly_included_passives()
                _is_excl       = (self._is_passive_excluded(result, _excl_passives, _excl_incl)
                                  or self._is_curse_blocked(result, self._get_blocked_curses()))
                if r_g3 > 0:
                    if _is_excl:
                        self._log(
                            f"  [EXCL] Batch {iteration} · Relic {step_i + 1} — 3/3 match"
                            f" but has excluded passive — saved to Excluded Hits folder.")
                    else:
                        self._log(
                            f"★★★ Match Found!  Batch {iteration} · Relic {step_i + 1} — 3/3")
                        self._write_match_log(
                            task.get("matches_log_path", ""),
                            iteration, step_i + 1, "★★★ GOD ROLL (3/3)", result)
                elif r_g2 > 0:
                    if _is_excl:
                        self._log(
                            f"  [EXCL] Batch {iteration} · Relic {step_i + 1} — 2/3 match"
                            f" but has excluded passive — saved to Excluded Hits folder.")
                    else:
                        self._log(
                            f"★★ Match Found!  Batch {iteration} · Relic {step_i + 1} — 2/3")
                        self._write_match_log(
                            task.get("matches_log_path", ""),
                            iteration, step_i + 1, "★★  HIT (2/3)", result)

        if task.get("_retry_pass"):
            # Retry pass: iteration already finalized during the main pass.
            # Skip state update and finalization to avoid double-counting.
            return

        _should_finalize = False
        with lock:
            istate = iter_state.get(iteration)
            if istate is None:
                return
            istate["results"].append((step_i, result))
            istate["done"] += 1
            is_complete = istate["done"] >= istate["total"]
            if is_complete and not istate.get("_finalized"):
                istate["_finalized"] = True
                _should_finalize = True

        if _should_finalize:
            self._finalize_async_iter_state(
                iteration, iter_state, lock, dir_map, results)

    def _mark_relic_failed(self, task: dict, iter_state: dict,
                           lock: threading.Lock, dir_map: dict,
                           results: list) -> None:
        """Count a permanently failed/timed-out relic as done; keep its screenshot."""
        iteration         = task["iteration"]
        step_i            = task["step_i"]
        pending_path      = task["pending_path"]
        iter_dir          = task["iter_dir"]
        _backlog_img_path = task.get("_backlog_img_path", "")
        _task_run_dir     = task.get("run_dir", "")

        if _backlog_img_path and os.path.exists(_backlog_img_path) and _task_run_dir:
            # Backlog task: escalate the screenshot through the retry hierarchy.
            #   Main pass failure      → _retry_staging/
            #   Retry pass failure     → _retry_staging/retry_last_try/
            #   Last-try pass failure  → do nothing; rmtree will clean up
            try:
                _retry_dir    = os.path.join(_task_run_dir, "_retry_staging")
                _last_try_dir = os.path.join(_retry_dir, "retry_last_try")
                _cur_dir      = os.path.dirname(os.path.abspath(_backlog_img_path))
                if _cur_dir == os.path.abspath(_last_try_dir):
                    # Already in last-try — delete immediately so the folder
                    # drains to empty once all processing is done.
                    try:
                        os.remove(_backlog_img_path)
                    except Exception:
                        pass
                    self._log(
                        f"  [Backlog] Iter {iteration} Relic {step_i + 1}"
                        f" — all retry attempts exhausted; screenshot discarded.")
                elif _cur_dir == os.path.abspath(_retry_dir):
                    # In first-retry staging → escalate to last-try.
                    os.makedirs(_last_try_dir, exist_ok=True)
                    shutil.move(_backlog_img_path,
                                os.path.join(_last_try_dir,
                                             os.path.basename(_backlog_img_path)))
                    self._log(
                        f"  [Backlog] Iter {iteration} Relic {step_i + 1}"
                        f" — retry failed, one last attempt queued.")
                else:
                    # First failure from the main pass → move to retry staging.
                    os.makedirs(_retry_dir, exist_ok=True)
                    shutil.move(_backlog_img_path,
                                os.path.join(_retry_dir,
                                             os.path.basename(_backlog_img_path)))
                    self._log(
                        f"  [Backlog] Iter {iteration} Relic {step_i + 1}"
                        f" — analysis failed, queued for retry.")
            except Exception:
                pass
        elif pending_path and os.path.exists(pending_path):
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

        _should_finalize = False
        with lock:
            istate = iter_state.get(iteration)
            if istate is None:
                return
            istate["done"] += 1
            is_complete = istate["done"] >= istate["total"]
            if is_complete and not istate.get("_finalized"):
                istate["_finalized"] = True
                _should_finalize = True

        if _should_finalize:
            self._finalize_async_iter_state(
                iteration, iter_state, lock, dir_map, results)

    def _cancel_and_rollback_iteration(self, iteration: int) -> None:
        """Cancel in-flight workers for `iteration` and subtract its counter contributions.

        Safe to call from either sync or async mode — contributions dict tracks both.
        Must be called on the main thread or with counters already thread-safe.
        """
        # 1. Prevent any still-running workers for this iteration from updating counters
        self._async_cancelled_iters.add(iteration)

        # 2. Extract accumulated contributions for this iteration
        with self._iter_contrib_lock:
            contrib = self._iter_contributions.pop(iteration, {})

        if not contrib:
            return  # nothing was counted yet — nothing to roll back

        # 3. Subtract from live counters (clamp at zero to absorb any tiny races)
        self._ov_at_33        = max(0, self._ov_at_33   - contrib.get("at_33",   0))
        self._ov_at_23        = max(0, self._ov_at_23   - contrib.get("at_23",   0))
        self._ov_at_duds      = max(0, self._ov_at_duds - contrib.get("at_duds", 0))
        self._ov_hits_33      = max(0, self._ov_hits_33 - contrib.get("hits_33", 0))
        self._ov_hits_23      = max(0, self._ov_hits_23 - contrib.get("hits_23", 0))
        self._ov_duds         = max(0, self._ov_duds    - contrib.get("duds",    0))
        self._ov_total_relics = max(0, self._ov_total_relics - contrib.get("total_relics", 0))

        # 4. Clear best-batch records that pointed to this iteration
        if self._best_33_iter and self._best_33_iter["iteration"] == iteration:
            self._best_33_iter = None
        if self._best_hits_iter and self._best_hits_iter["iteration"] == iteration:
            self._best_hits_iter = None

        # 5. Push rolled-back numbers to the overlay
        if self._overlay:
            def _fmt_best(info, suffix):
                if info is None:
                    return "N/A"
                return f"Batch #{info['iteration']:03d}  —  {info['count']} {suffix}"
            ov = self._overlay
            h33, h23, dds = self._ov_hits_33, self._ov_hits_23, self._ov_duds
            at33, at23, atd = self._ov_at_33, self._ov_at_23, self._ov_at_duds
            tot  = self._ov_total_relics
            q_sto = self._async_relic_q.qsize() if self._async_relic_q else 0
            b33  = _fmt_best(self._best_33_iter,   "★★★")
            bhit = _fmt_best(self._best_hits_iter, "hits")
            self.after(0, lambda: ov.update(
                hits_33=h33, hits_23=h23, duds=dds,
                at_33=at33, at_23=at23, at_duds=atd,
                stored=q_sto, analyzed=tot, best_33=b33, best_hits=bhit,
            ) if ov._win else None)

    def _is_system_stressed(self) -> bool:
        """Return True when live metrics indicate the system is under load.

        Used by Smart Throttling to decide whether to gate OCR workers during
        input phases.  Thresholds are intentionally conservative — a system that
        passes this check is genuinely comfortable, not merely 'not terrible'.
        """
        return (
            self._perf_gap_mult > 1.15
            or getattr(self, "_last_cpu_pct", 0) > 70
        )

    def _set_ocr_throttle(self, paused: bool) -> None:
        """Pause (True) or resume (False) async OCR workers during input phases.

        When paused, workers finish their current task but wait before starting
        the next one — inputs get full CPU without killing background analysis.
        No-op when async mode is not active.

        With Smart Throttling enabled, the pause is skipped when the system is
        not under stress — workers keep running freely during input phases on
        healthy machines, falling back to hard throttle when load climbs.
        """
        ev = self._ocr_go_event
        if ev is None:
            return
        if paused:
            if (self._smart_throttle_var.get()
                    and not self._is_system_stressed()):
                return   # system is fine — let workers continue during inputs
            ev.clear()
        else:
            ev.set()

    def _async_iter_abort_cleanup(self, iteration: int, p2_submitted: int) -> None:
        """Correct the over-estimated async iter total on early exit from the buy loop.

        Called whenever _run_iteration_phases returns early (bot stopped, phase 1
        failure, etc.) while async mode is active.  Without this, _istate["total"]
        stays at the initial over-estimate and workers can never satisfy
        done >= total, so _finalize_async_iter_state never fires and info.txt is
        never written for the iteration.
        """
        if self._async_state_lock is None or self._async_iter_state is None:
            return
        _p2_finalize_now = False
        with self._async_state_lock:
            _istate = self._async_iter_state.get(iteration)
            if _istate is None or _istate.get("_finalized"):
                return
            if p2_submitted == 0:
                # Nothing was queued — finalize immediately so the iteration
                # doesn't dangle.  Workers won't fire because there's no work.
                _istate["total"] = 0
                _istate["_finalized"] = True
                _p2_finalize_now = True
            else:
                # Correct the over-estimate so workers can trigger finalization
                # when the last task completes.
                _istate["total"] = p2_submitted
                if _istate["done"] >= p2_submitted:
                    _istate["_finalized"] = True
                    _p2_finalize_now = True
        if _p2_finalize_now and self._async_results_list is not None:
            self._finalize_async_iter_state(
                iteration, self._async_iter_state,
                self._async_state_lock, self._async_dir_map,
                self._async_results_list)

    def _finalize_async_iter_state(self, iteration: int, iter_state: dict,
                                   lock: threading.Lock, dir_map: dict,
                                   results: list) -> None:
        """Post-process a completed async iteration (all relics analyzed/failed)."""
        # If this iteration was cancelled mid-run, skip scoreboard / log updates
        if iteration in self._async_cancelled_iters:
            with lock:
                iter_state.pop(iteration, None)
            return

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

        blocked_curses      = self._get_blocked_curses()
        excluded_passives   = self._get_excluded_passives()
        explicitly_included = self._get_explicitly_included_passives()

        _excl_match_results = [
            (i + 1, r) for i, r in enumerate(relic_results)
            if r.get("match")
            and (self._is_curse_blocked(r, blocked_curses)
                 or self._is_passive_excluded(r, excluded_passives, explicitly_included))
        ]
        any_match = any(
            r.get("match")
            and not self._is_curse_blocked(r, blocked_curses)
            and not self._is_passive_excluded(r, excluded_passives, explicitly_included)
            for r in relic_results
        )
        all_relics = [rf for r in relic_results
                      for rf in r.get("relics_found", [])]
        all_near_misses = [nm for r in relic_results
                           for nm in r.get("near_misses", [])]
        matched_result = next(
            (r for r in relic_results
             if r.get("match")
             and not self._is_curse_blocked(r, blocked_curses)
             and not self._is_passive_excluded(r, excluded_passives, explicitly_included)),
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
        # Pairing matches (↔) are labelled HIT at most — never GOD ROLL
        if num_matched > 2 and any("\u2194" in str(p) for p in matched_passives):
            num_matched = 2
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
                tot  = self._ov_total_relics
                q_sto = self._async_relic_q.qsize() if self._async_relic_q else 0
                b33  = _fmt_best(self._best_33_iter,   "★★★")
                bhit = _fmt_best(self._best_hits_iter, "hits")
                self.after(0, lambda: ov.update(
                    at_33=at33, at_23=at23, at_duds=atd,
                    stored=q_sto, analyzed=tot, best_33=b33, best_hits=bhit,
                ) if ov._win else None)

            self._save_stats()

        # Hit / GOD ROLL log — always shown for current batch; shown for overflow
        # only if a hit was found (exception rule so user never misses a result).
        if num_matched >= 3:
            if is_current_batch:
                self._log(f"★★★ GOD ROLL — Batch {iteration}: {matched_relic}")
            else:
                self._log(
                    f"[Overflow] ★★★ GOD ROLL — Prev batch Batch {iteration}: {matched_relic}"
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
                self._log(f"★★ HIT — Batch {iteration}: {hit_name}")
            else:
                self._log(
                    f"[Overflow] ★★ HIT — Prev batch Batch {iteration}: {hit_name}"
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
            write_iter_info(iter_dir, iteration, relic_results, hit_min,
                            p_per_relic=self.relic_builder.get_current_p_per_relic())
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

        # ── All Hits folder ───────────────────────────────────────────── #
        if num_matched >= hit_min:
            try:
                _all_hits_dir = os.path.join(run_dir, "All Hits")
                os.makedirs(_all_hits_dir, exist_ok=True)
                _hits_summary_path = os.path.join(_all_hits_dir, "hits_summary.txt")
                for _ah_idx, _ah_rr in enumerate(relic_results):
                    _ah_fname = _ah_rr.get("_screenshot_file", "")
                    if not (_ah_fname and ("HIT" in _ah_fname or "MATCH" in _ah_fname)):
                        continue
                    _ah_src = os.path.join(final_iter_dir, _ah_fname)
                    if not os.path.exists(_ah_src):
                        continue
                    _ah_rf = (_ah_rr.get("relics_found") or [{}])[0]
                    _ah_passives = _ah_rf.get("passives", []) if isinstance(_ah_rf, dict) else []
                    _ah_curses   = _ah_rf.get("curses",   []) if isinstance(_ah_rf, dict) else []
                    _ah_dst = os.path.join(
                        _all_hits_dir, f"iter_{iteration:03d}_relic_{_ah_idx + 1:03d}.jpg")
                    shutil.copy2(_ah_src, _ah_dst)
                    _write_header = not os.path.exists(_hits_summary_path)
                    with open(_hits_summary_path, "a", encoding="utf-8") as _hf:
                        if _write_header:
                            _hf.write("Matches Found\n")
                            _hf.write("=" * 40 + "\n\n")
                        _hf.write(f"Batch {iteration:03d}  Relic #{_ah_idx + 1:03d}\n")
                        _hf.write("  Passives:\n")
                        for _p in _ah_passives:
                            _hf.write(f"    {_p}\n")
                        if not _ah_passives:
                            _hf.write("    (none)\n")
                        _hf.write("  Curses:\n")
                        for _c in _ah_curses:
                            _hf.write(f"    {_c}\n")
                        if not _ah_curses:
                            _hf.write("    (none)\n")
                        _hf.write("\n")
            except Exception as _ahe:
                if is_current_batch:
                    self._log(f"WARNING: could not write to All Hits folder: {_ahe}")

        # ── Excluded Hits folder (opt-in) ─────────────────────────────── #
        if _excl_match_results and self._save_exclusion_matches_var.get():
            try:
                _mex_dir = os.path.join(run_dir, "Excluded Hits")
                os.makedirs(_mex_dir, exist_ok=True)
                _mex_info_path = os.path.join(_mex_dir, "Excluded Hits Info.txt")
                _mex_sep = "─" * 40
                for _mex_rnum, _mex_rr in _excl_match_results:
                    _mex_fname = _mex_rr.get("_screenshot_file", "")
                    _mex_rf = (_mex_rr.get("relics_found") or [{}])[0]
                    _mex_rname    = _mex_rf.get("name", "Unknown") if isinstance(_mex_rf, dict) else "Unknown"
                    _mex_passives = _mex_rf.get("passives", []) if isinstance(_mex_rf, dict) else []
                    _mex_curses   = _mex_rf.get("curses",   []) if isinstance(_mex_rf, dict) else []
                    _mex_excl_names = set(self._get_excluded_passive_names(
                        _mex_rr, excluded_passives, explicitly_included))
                    _mex_dst_fname = f"Iter_{iteration}_Relic_{_mex_rnum}_EXCL.jpg"
                    if _mex_fname:
                        _mex_src = os.path.join(final_iter_dir, _mex_fname)
                        if os.path.exists(_mex_src):
                            _mex_dst = os.path.join(_mex_dir, _mex_dst_fname)
                            try:
                                shutil.move(_mex_src, _mex_dst)
                            except Exception:
                                shutil.copy2(_mex_src, _mex_dst)
                    with open(_mex_info_path, "a", encoding="utf-8") as _ef:
                        _ef.write(
                            f"{_mex_sep}\n"
                            f"  Iter #{iteration:03d}  ·  Relic {_mex_rnum}"
                            f"  [{_mex_dst_fname}]\n"
                            f"  Relic : {_mex_rname}\n"
                            + "".join(
                                f"  + {p}{'  [EXCLUDED]' if p in _mex_excl_names else ''}\n"
                                for p in _mex_passives)
                            + ("  (no passives)\n" if not _mex_passives else "")
                            + "".join(f"  ✗ {c}  (curse)\n" for c in _mex_curses)
                            + "\n"
                        )
                if is_current_batch and _excl_match_results:
                    self._log(
                        f"  {len(_excl_match_results)} relic(s) matched criteria but had "
                        f"excluded passive(s) — saved to 'Excluded Hits' folder.")
            except Exception as _mexe:
                if is_current_batch:
                    self._log(f"WARNING: could not write to Excluded Hits folder: {_mexe}")
        elif _excl_match_results and is_current_batch:
            self._log(
                f"  {len(_excl_match_results)} relic(s) matched criteria but had "
                f"excluded passive(s) (opt-in folder disabled).")

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
                            limit_value, results, hit_min,
                            p_per_relic=self.relic_builder.get_current_p_per_relic())
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
                              region,
                              iter_dir: str = "", hit_min: int = 2,
                              live_log_path: str = "",
                              capture_only: bool = False,
                              iteration: int = 0,
                              async_iter_meta: dict | None = None) -> list | None:
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

        # ── Adaptive timing ───────────────────────────────────────────── #
        # _perf_gap_mult rises above 1.0 as game load times grow (system
        # degrading under sustained use). All input gaps are multiplied by
        # this factor so dialogs and menus have proportionally more time.
        _lpm = self._low_perf_mode_var.get()
        # Phase 1: use play() with original human-recorded within-sequence timing
        # (~504 ms F-to-DOWN as recorded). extra_delay adds a small buffer after
        # each key_release on top of the natural gap so dialogs have more room to
        # open under load. LPM adds a flat 100 ms floor even at baseline.
        _p1_extra_delay  = round(
            (0.10 if _lpm else 0.0) + 0.05 * max(0.0, self._perf_gap_mult - 1.0), 3)
        # Phase 0/2: play_split already uses original recorded timing; extra_delay
        # adds proportional buffer after each key so menus that open slowly don't
        # swallow the next input. Scales with perf_mult (floor 0.10 s).
        _p02_extra_delay = round(max(0.10, 0.10 * self._perf_gap_mult), 3)
        _gpu_on = getattr(self, "_gpu_accel_var", None) and self._gpu_accel_var.get()
        # Phase 4 advance gap and settle
        _P4_FAILSAFE = 200          # internal only — never shown in UI
        p4_settle = float(self.phase_settle_vars[4].get() or "0")
        _p4_advance_gap  = 0.20 if _lpm else (0.07 if _gpu_on else 0.10)
        _p4_init_settle  = (2.0 if _lpm else 1.0) * max(1.0, self._perf_gap_mult)
        _p4_init_settle  = min(_p4_init_settle, 4.0)  # cap at 4 s
        murk_cost = 1800 if self.relic_type_var.get() == "night" else 600
        _p3_count    = None   # set by murk read below; None = use failsafe
        _actual_bought = None   # set after Phase 1 via murk re-read; used for Phase 4 count
        _p0_exe   = os.path.basename(self.game_exe_var.get().strip())
        murk_val  = 0

        relic_results = []
        self._phase0_skipped    = False   # set True if Phase 0 fails 3 times this iteration
        # Reset per-iteration calibration counters
        self._iter_p0_attempts       = 0
        self._iter_p1_settle_retries = 0
        self._iter_safe_path_used    = False
        self._iter_settle_poll_depth = 0
        self._iter_batches_settled   = 0

        # Expected Phase 0 input count and exact key sequence (for validation)
        _p0_expected      = sum(1 for e in self.phase_events[0] if e["type"] == "key_press")
        _p0_expected_keys = [e["key"] for e in self.phase_events[0] if e["type"] == "key_press"]
        _P01_MAX_ATTEMPTS = 3   # max Phase 0+1 retries before aborting iteration

        # Dynamic wait for Phase 0: polls for "Small Jar Bazaar" text in the top
        # portion of the screen for up to 30 s before firing section 2 of Phase 0.
        # _shop_found[0] is set True only if the text is detected — used as a hard
        # validation gate after play_split() returns.
        _shop_found = [False]

        def _p0_shop_wait():
            _shop_found[0] = False
            # Settle before polling: the menu-close animation briefly keeps "Small
            # Jar Bazaar" visible on screen even if F was pressed on the wrong item.
            # Waiting 1 s lets the transition complete so the check reflects the
            # actual loaded screen, not a transient menu frame.
            time.sleep(1.0)
            if not self.bot_running or self._reset_iter_requested:
                return
            # Scale the shop-detection window with the observed game load time:
            # faster machines get a shorter window; slower machines more time.
            # Min 35 s, max 70 s, scaled at 60% of last load elapsed time.
            _shop_secs = max(35, min(70, round(self._last_load_elapsed * 0.6)))
            _deadline = time.time() + _shop_secs - 1   # 1 s already spent on settle
            while time.time() < _deadline:
                if not self.bot_running or self._reset_iter_requested:
                    return
                try:
                    _si = screen_capture.capture(region)
                    if relic_analyzer.check_text_visible(_si, "small jar bazaar", top_fraction=0.15):
                        self._log("  Shop screen detected.")
                        _shop_found[0] = True
                        # Shop header text appears before the UI is fully settled
                        # (tooltip and cursor need more time to load). Wait here
                        # so the remaining Phase 0 navigation keys fire into a
                        # fully-ready shop. LPM uses a longer base.
                        time.sleep((3.0 if _lpm else 1.5) * max(1.0, self._perf_gap_mult))
                        return
                except Exception:
                    pass
                time.sleep(0.2)
            self._log(f"  WARNING: Shop screen not detected within {_shop_secs} s.")

        # ── Phase 0 + Murk read + Phase 1 — with retry loop ────────────── #
        # Wrapped in a retry loop: if Phase 0 input count is short (play was
        # interrupted) or a reset is requested, ESC-recover and retry up to
        # _P01_MAX_ATTEMPTS times. Inputs use extra_delay=0.25 s per key to
        # prevent inputs being eaten during game-UI transition animations.
        _p01_success = False
        # Pre-initialize using async presence + checkbox so the Phase 0 throttle
        # guard is correct from the first key press.  Re-assigned at Phase 2 setup
        # (line 5792) once _p2_async is confirmed — same intent, tighter condition.
        _exclude_buy_phase = (
            async_iter_meta is not None and self._exclude_buy_phase_var.get()
        )
        for _p01_att in range(_P01_MAX_ATTEMPTS):
            if not self.bot_running or self._reset_iter_requested:
                return relic_results

            # ── Phase 0: Setup ─────────────────────────────────────────── #
            if self.phase_events[0]:
                if self._diag:
                    self._diag.phase_start("Phase 0 (shop nav)",
                                           f"attempt={_p01_att + 1}")
                self._iter_p0_attempts += 1   # count each attempt for calibration
                attempt_label = (f" (attempt {_p01_att + 1}/{_P01_MAX_ATTEMPTS})"
                                 if _p01_att > 0 else "")
                self._set_status(f"{label}: setup{attempt_label}…", "green")
                if _p0_exe:
                    self._focus_game_window(_p0_exe, timeout=3.0)
                if not self.bot_running or self._reset_iter_requested:
                    return relic_results
                # play_split: fire M + down×6 + F (8 keys), poll for "Small Jar
                # Bazaar" text (up to 30 s) to confirm shop loaded, then fire the
                # remaining shop-nav inputs.
                # extra_delay adds buffer after each key release so down arrows
                # don't fire during the menu-open animation and get eaten.
                # Scales with _p02_extra_delay so slower/degraded systems get
                # proportionally more room. Applies to both Phase 0 recordings.
                self._set_ocr_throttle(True)   # pause workers during Phase 0 inputs
                _p0_t_start = time.perf_counter()
                _p0_sent, _p0_sent_keys = self.player.play_split(
                    self.phase_events[0], split_after_n_keys=8,
                    wait_fn=_p0_shop_wait, bypass_focus=True,
                    extra_delay=_p02_extra_delay)
                _p0_t_end = time.perf_counter()
                if not _exclude_buy_phase:   # excl-ops: batch loop releases at close_game
                    self._set_ocr_throttle(False)  # resume after Phase 0 done
                if not self.bot_running or self._reset_iter_requested:
                    return relic_results

                # Validate input count, key sequence, shop screen detection,
                # AND highlighted item identity.
                # Shop detection is the real gate — pynput always succeeds at the OS
                # level regardless of whether the game processed the inputs.
                _p0_count_ok = (_p0_sent == _p0_expected)
                _p0_seq_ok   = (_p0_sent_keys == _p0_expected_keys)
                _p0_shop_ok  = _shop_found[0]

                # ── Shop item verification (ARCHIVED — not active) ────────────
                # verify_shop_item() OCRs the tooltip panel to confirm the cursor
                # landed on the correct relic and that it is not the old-version
                # (1.02) variant.  Archived pending proper testing/tuning.
                # To re-enable: remove the `if False:` wrapper below.
                #
                # Retry logic (when re-enabled):
                # • Definitive wrong item detected → bail immediately (ESC reset).
                # • Inconclusive OCR → retry every 1.5 s for up to 30 s, then ESC
                #   reset and restart the iteration from a fresh state.
                _p0_item_ok     = True
                _p0_item_reason = ""
                if False:   # ARCHIVED
                    if _p0_count_ok and _p0_seq_ok and _p0_shop_ok:
                        _tooltip_settle = (1.0 if _lpm else 0.5) * max(1.0, self._perf_gap_mult)
                        time.sleep(_tooltip_settle)
                        _ITEM_VERIFY_TIMEOUT = 30.0
                        _item_deadline = time.monotonic() + _ITEM_VERIFY_TIMEOUT
                        _item_attempt  = 0
                        while self.bot_running and not self._reset_iter_requested:
                            _item_attempt += 1
                            try:
                                _item_img = screen_capture.capture(region)
                                _p0_item_ok, _p0_item_reason = relic_analyzer.verify_shop_item(
                                    _item_img, self.relic_type_var.get())
                            except Exception as _p0ie:
                                self._log(
                                    f"  Phase 0: shop item check error: {_p0ie} — proceeding.")
                                _p0_item_ok = True
                                break

                            if _p0_item_ok:
                                self._log(
                                    f"  Phase 0: shop item verified — {_p0_item_reason}.")
                                break

                            if "inconclusive" not in _p0_item_reason.lower():
                                self._log(
                                    f"  Phase 0: shop item check FAILED — {_p0_item_reason}.")
                                break

                            if time.monotonic() >= _item_deadline:
                                self._log(
                                    f"  Phase 0: item not detected after "
                                    f"{_ITEM_VERIFY_TIMEOUT:.0f}s — resetting iteration.")
                                _p0_item_ok   = False
                                _p0_item_reason = (
                                    f"item not detected after {_ITEM_VERIFY_TIMEOUT:.0f}s")
                                break

                            _remaining = max(0.0, _item_deadline - time.monotonic())
                            self._log(
                                f"  Phase 0: item not yet visible "
                                f"(attempt {_item_attempt}, {_remaining:.0f}s remaining)"
                                f" — retrying…")
                            time.sleep(1.5)

                # Record Phase 0 duration on clean first-attempt success only
                # (retried runs include recovery waits — not representative).
                if _p01_att == 0 and _p0_count_ok and _p0_seq_ok and _p0_shop_ok and _p0_item_ok:
                    _timing_p0_secs = _p0_t_end - _p0_t_start

                if not _p0_count_ok or not _p0_seq_ok or not _p0_shop_ok or not _p0_item_ok:
                    if not _p0_count_ok:
                        _mismatch_desc = f"count {_p0_sent}/{_p0_expected}"
                    elif not _p0_seq_ok:
                        _mismatch_desc = "sequence mismatch"
                    elif not _p0_shop_ok:
                        _mismatch_desc = "shop screen not detected"
                    else:
                        _mismatch_desc = f"wrong shop item ({_p0_item_reason})"
                    self._log(
                        f"  Phase 0: validation failed ({_mismatch_desc}) "
                        f"— ESC recovery and retry.")
                    # Reset tracking vars so stale values can't cause a false positive
                    _p0_sent = 0
                    _p0_sent_keys = []
                    if _p01_att < _P01_MAX_ATTEMPTS - 1:
                        self._esc_to_game_screen(region)
                        continue
                    else:
                        self._log("  Phase 0 failed 3 times — restarting iteration.")
                        self._phase0_skipped = True
                        self._close_game()
                        try:
                            save_manager.restore(
                                self.save_path_var.get(),
                                getattr(self, "_run_backup_path",
                                        os.path.join(self.backup_path_var.get(),
                                                     os.path.basename(self.save_path_var.get()))))
                        except Exception:
                            pass
                        return relic_results

            # ── Murk read — calculates buy count ───────────────────────── #
            if self.phase_events[1]:
                self._set_status(f"{label}: waiting for shop screen…", "green")
                time.sleep(0.5)   # brief settle after shop detection confirmed
                if not self.bot_running or self._reset_iter_requested:
                    return relic_results

                _murk_below_cost = False
                for attempt in range(1, 4):
                    if not self.bot_running or self._reset_iter_requested:
                        return relic_results
                    self._set_status(
                        f"{label}: reading murk (attempt {attempt}/3)…", "green")
                    self.after(0, self._flash_capture)
                    try:
                        murk_img = screen_capture.capture(region)
                        murk_val, self._murk_region = relic_analyzer.read_murk(murk_img)
                    except Exception as e:
                        self._log(f"  Murk read attempt {attempt}/3 error: {e}")
                        murk_val = 0

                    if murk_val >= murk_cost:
                        _p3_count = murk_val // murk_cost
                        self._log(
                            f"  Murk: {murk_val:,}  →  {_p3_count} relic(s) to review "
                            f"({murk_cost} murk each).")
                        # Global murk check: first iteration sets expected value;
                        # subsequent iterations verify save restore returned the same amount.
                        if self._global_murk_expected is None:
                            self._global_murk_expected = murk_val
                        elif murk_val != self._global_murk_expected:
                            # One retry to rule out OCR noise before aborting.
                            self._log(
                                f"  Murk mismatch ({murk_val:,} ≠ {self._global_murk_expected:,})"
                                " — re-reading to confirm…")
                            time.sleep(0.5)
                            try:
                                _recheck_img = screen_capture.capture(region)
                                _recheck_val, _ = relic_analyzer.read_murk(
                                    _recheck_img, region=self._murk_region)
                            except Exception:
                                _recheck_val = murk_val   # treat read failure as same result
                            if _recheck_val == self._global_murk_expected:
                                self._log("  Re-read matched — OCR noise, continuing.")
                                murk_val  = _recheck_val
                                _p3_count = murk_val // murk_cost
                            else:
                                self._log(
                                    f"  Re-read also mismatched ({_recheck_val:,}). "
                                    "Save restore may have failed — restoring and restarting.")
                                try:
                                    _sp = self.save_path_var.get()
                                    save_manager.restore(
                                        _sp,
                                        getattr(self, "_run_backup_path",
                                                os.path.join(self.backup_path_var.get(),
                                                             os.path.basename(_sp))))
                                except Exception as _gme:
                                    self._log(f"  Save restore failed: {_gme}")
                                return relic_results
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
                        _murk_below_cost = True
                        murk_val = 0
                    else:
                        self._log(f"  Murk read attempt {attempt}/3 returned 0.")

                if _p3_count is None:
                    if _murk_below_cost:
                        self._log(
                            f"  Murk is below relic cost ({murk_cost:,} each) — "
                            "no relics available to buy. Ending iteration.")
                        return relic_results
                    else:
                        self._log(
                            "  WARNING: Murk could not be read — "
                            "falling back to failsafe buy mode (runs until stop condition).")
            else:
                time.sleep(1.5)   # inter-phase buffer even without murk read

            if self._diag:
                self._diag.phase_end("Phase 0 (shop nav)")
            _p01_success = True
            break   # Phase 0 complete — proceed to per-batch buy+scan+reset loop

        if not _p01_success and self.bot_running and not self._reset_iter_requested:
            return relic_results   # all retry attempts exhausted without completion

        # ── Per-batch loop: Buy → Scan → Reset ──────────────────────────── #
        # Each batch: Phase 1 buys up to 10 relics and enters the inspect
        # preview screen, Phase 2 scans them (RIGHT × batch_size-1 + capture),
        # Phase 3 resets back to the shop with a single F press.
        # Batch count is driven by murk read; falls back to failsafe if unknown.
        if self.phase_events[1]:
            if _p3_count is not None:
                _MAX_BUY_BATCHES = math.ceil(1950 / 10)
                _buy_count = min(math.ceil(_p3_count / 10), _MAX_BUY_BATCHES)
                self._log(f"  {_p3_count} relic(s) available → {_buy_count} cycle(s).")
            else:
                _buy_count  = _P1_FAILSAFE
                _p3_count   = _buy_count * 10   # upper-bound estimate for overlay
                self._log("  Murk unknown — running in failsafe mode.")

            _relics_scanned = 0
            _bl_captures    = []   # backlog mode: (step_i, img_bytes, "") tuples

            # ── Async Phase 2 setup ──────────────────────────────────────── #
            # When async_iter_meta is provided the caller is in async mode.
            # Register the iteration in iter_state now (total estimated from murk
            # read) so workers can start finalization as tasks complete.
            # Slot 0 of each batch is always processed inline (settle result);
            # slots 1+ are submitted to the queue without waiting.
            _p2_async = (
                async_iter_meta is not None
                and self._async_relic_q is not None
                and self._async_iter_state is not None
                and bool(self.phase_events[2])
            )
            _p2_submitted = 0   # tracks actual tasks submitted to queue
            _p2_settle_skip_count = 0    # per-iteration: cycles where preview had no passives
            _MAX_P2_SETTLE_SKIPS  = 4   # reset iteration after this many no-passive skips
            # Timing accumulators for this iteration (fed to _record_timing_sample at end)
            _timing_p0_secs:       float | None       = None   # Phase 0 duration (clean run only)
            _timing_p1_samples:    list[float]         = []     # Phase 1 sec/relic per cycle
            _timing_p2_samples:    list[float]         = []     # Phase 2 sec/relic per cycle
            # When True, workers stay throttled from Phase 1 start through the end of
            # Phase 2 (all screenshots captured). They then run freely during Phase 3
            # and Phase 0 of the next cycle.  Sub-option of Async Analysis only.
            _exclude_buy_phase = _p2_async and self._exclude_buy_phase_var.get()

            if _p2_async:
                # Slot 0 of each batch is inline; the rest are queued.
                # _p3_count is a safe over-estimate (actual total corrected after loop).
                # Workers won't finalize early because done can't exceed submitted.
                _p2_estimated = max(1, _p3_count if _p3_count else _buy_count * 10)
                with self._async_state_lock:
                    self._async_iter_state[iteration] = {
                        "total":            _p2_estimated,
                        "done":             0,
                        "_finalized":       False,
                        "results":          [],
                        "iter_dir":         iter_dir,
                        "hit_min":          hit_min,
                        "live_log_path":    live_log_path,
                        **async_iter_meta,
                    }

            _buy_loop_done = False   # set True when "Insufficient murk" detected mid-cycle
            for _batch_i in range(_buy_count):
                if _buy_loop_done:
                    break
                if not self.bot_running or self._reset_iter_requested:
                    if _p2_async:
                        self._async_iter_abort_cleanup(iteration, _p2_submitted)
                    if not self.bot_running and capture_only and not _p2_async:
                        return _bl_captures
                    return relic_results

                # How many relics will this batch buy?
                _remaining        = (_p3_count - _batch_i * 10) if _p3_count else 10
                _batch_size       = min(10, _remaining)
                _advance_presses  = max(0, _batch_size - 1)

                # ── Phase 1: Buy + enter relic preview (with retry on miss) ── #
                # After playing the buy sequence we poll analyze() with the
                # preview-screen crop to confirm we're actually looking at a
                # relic.  If we're not (buy failed / wrong screen), we ESC to
                # the game world, replay Phase 0 to get back to the shop, then
                # retry Phase 1.  Max 2 retries per batch before aborting.
                _P1_BATCH_RETRIES = 1
                _settle_img    = None
                _settle_result = None
                _p1_ok         = False
                _p1_scan       = False   # True only when preview has a real relic with passives

                for _p1_try in range(_P1_BATCH_RETRIES + 1):
                    if not self.bot_running or self._reset_iter_requested:
                        if not self.bot_running and capture_only and not _p2_async:
                            return _bl_captures
                        return relic_results

                    self._set_status(
                        f"{label}: cycle {_batch_i + 1}/{_buy_count} — buying…",
                        "green")
                    if self._diag:
                        self._diag.phase_start(
                            f"Cycle {_batch_i + 1} Phase 1 (buy)",
                            f"try={_p1_try + 1}  batch_size={_batch_size}")
                    if _p0_exe:
                        self._focus_game_window(_p0_exe, timeout=2.0)
                    if not self.bot_running or self._reset_iter_requested:
                        if not self.bot_running and capture_only and not _p2_async:
                            return _bl_captures
                        return relic_results

                    if _p1_try > 0:
                        self._iter_p1_settle_retries += 1  # each retry = settle missed
                    self._iter_safe_path_used = True   # alt sequence always used
                    self._set_ocr_throttle(True)   # pause workers during Phase 1 buy inputs
                    # Always use alt sequence (F→DOWN→F) — more reliable than the fast
                    # path (F→DOWN→F→F) which can miss the preview on slow machines or
                    # when the last cycle has fewer relics.  No fixed sleep after play —
                    # the settle poll below waits until the relic screen is detected.
                    _safe_seq = self._phase1_alt_events or self.phase_events[1]
                    _t_p1_start = time.perf_counter()
                    self.player.play(_safe_seq, extra_delay=_p1_extra_delay)
                    _path_name = f"alt (mult {self._perf_gap_mult:.2f}×)"
                    # Keep throttle ON through the settle poll below.
                    # Releasing it here lets async workers run OCR concurrently,
                    # which saturates CPU and causes analyze() in the settle loop
                    # to take 3-5s per call instead of ~1.5s — leading to 50-second
                    # settle timeouts, ESC recovery, and skipped relics.
                    # Throttle is released after settle confirms (or on any exit).

                    if not self.bot_running or self._reset_iter_requested:
                        self._set_ocr_throttle(False)
                        if not self.bot_running and capture_only and not _p2_async:
                            return _bl_captures
                        return relic_results

                    # No pre-poll delay — we poll every 3 s within the settle loop,
                    # so the loop itself handles the wait.  The first iteration may
                    # capture a blank/partial frame; that's fine — it will not pass
                    # the passive-token check and we'll retry after 3 s.

                    # Poll for relic inspect screen — up to 15 s.
                    # analyze() with preview crop doubles as slot-0 capture.
                    # Require at least one PASSIVE token or relics_found with passives
                    # to avoid accepting a Scenic Flatstone shop-tooltip as confirmation.
                    _settle_ok               = False
                    _settle_no_passives      = False   # relic name seen but zero passives
                    _settle_insufficient_murk = False  # buy failed — no murk left
                    _settle_deadline = time.monotonic() + 15.0
                    _sc = 0
                    while time.monotonic() < _settle_deadline:
                        if not self.bot_running or self._reset_iter_requested:
                            self._set_ocr_throttle(False)
                            if not self.bot_running and capture_only and not _p2_async:
                                return _bl_captures
                            return relic_results
                        try:
                            _settle_img = screen_capture.capture(region)
                            # Check for "Insufficient murk" popup using the already-captured
                            # frame — reuses the screenshot, no extra capture needed.
                            if relic_analyzer.check_text_visible(
                                    _settle_img, "insufficient murk", top_fraction=0.85):
                                _settle_insufficient_murk = True
                                self._log(
                                    f"  Cycle {_batch_i + 1}: 'Insufficient murk' detected"
                                    f" — all relics purchased.")
                                break
                            _settle_result = relic_analyzer.analyze(
                                _settle_img, criteria,
                                crop_left=relic_analyzer._PREVIEW_CROP_LEFT_FRAC,
                                crop_top=relic_analyzer._PREVIEW_CROP_TOP_FRAC,
                                relic_type=self.relic_type_var.get(),
                            )
                            _toks = _settle_result.get("_ocr_tokens", [])
                            # Require at least one passive — a PASSIVE token, or
                            # relics_found[0] with a non-empty passives list.
                            _has_passive_tok  = any(t.get("status") == "PASSIVE" for t in _toks)
                            _rf               = _settle_result.get("relics_found") or []
                            _has_relic_passives = (
                                bool(_rf) and bool((_rf[0] or {}).get("passives"))
                            )
                            if _has_passive_tok or _has_relic_passives:
                                self._iter_settle_poll_depth += _sc + 1
                                self._iter_batches_settled   += 1
                                _settle_ok = True
                                break
                            # Relic name found but no passives — may be a
                            # Scenic Flatstone tooltip or bare name OCR bleed.
                            if bool(_rf) or any(t.get("status") == "RELIC_NAME"
                                                for t in _toks):
                                _settle_no_passives = True
                        except Exception as _se:
                            self._log(f"  Cycle {_batch_i+1}: settle check err: {_se}")
                        time.sleep(1.0)
                        _sc += 1

                    # Settle loop done.
                    # Normal mode: release workers now so they can run during
                    # the settle_no_passives verify and Phase 2 scanning.
                    # Exclude-buy-phase mode: keep throttle ON — workers stay
                    # paused through the entire Phase 2 capture window and are
                    # released after the last screenshot is taken.
                    if not _exclude_buy_phase:
                        self._set_ocr_throttle(False)

                    # Failsafe: "Insufficient murk" popup detected in settle poll —
                    # all relics were purchased; exit buy loop without retrying.
                    if _settle_insufficient_murk:
                        if self._diag:
                            self._diag.phase_end(f"Cycle {_batch_i + 1} Phase 1 (buy)",
                                                 note="murk exhausted")
                        _p1_ok = True       # don't trigger abort path
                        _buy_loop_done = True   # signal outer _batch_i loop to stop
                        if _exclude_buy_phase:
                            self._set_ocr_throttle(False)
                        break   # break _p1_try loop

                    # If the relic name was seen during polling but passives never
                    # confirmed (OCR miss or fast tooltip), accept it as settled rather
                    # than ESC-recovering — Phase 2 will do the proper passive scan.
                    if not _settle_ok and _settle_no_passives:
                        _settle_ok = True
                        self._log(
                            f"  Cycle {_batch_i + 1}: settle accepted — relic name"
                            f" detected but no passives in {_sc} poll(s); proceeding"
                            f" to Phase 2.")

                    if _settle_ok:
                        self._log(
                            f"  Cycle {_batch_i + 1}: {_path_name} — relic screen confirmed"
                            + (f" (retry {_p1_try})" if _p1_try else "") + ".")
                        if self._diag:
                            self._diag.phase_end(f"Cycle {_batch_i + 1} Phase 1 (buy)")
                        # Record Phase 1 timing on clean settle (first try only — retries
                        # include recovery waits that inflate the measurement).
                        if _p1_try == 0:
                            _timing_p1_samples.append(
                                (time.perf_counter() - _t_p1_start) / max(1, _batch_size))
                        _p1_ok   = True
                        _p1_scan = True
                        break   # proceed to Phase 2 with full scan

                    if _settle_no_passives:
                        # We are still in the shop menu (Scenic / Deep Scenic Flatstone
                        # tooltip visible — player-owned relics never carry that name).
                        # Phase 1 failed to navigate into the preview.
                        # ── Shop item re-verify (ARCHIVED — not active) ──────────
                        # When active: calls verify_shop_item() to decide whether to
                        # retry Phase 1 in place (still on correct item) or fall
                        # through to ESC + Phase 0 recovery (wrong item/inconclusive).
                        # Archived pending proper testing/tuning alongside Phase 0
                        # verify.  To re-enable: remove the `if False:` wrapper.
                        _shop_item_ok     = False
                        _shop_verify_reason = "not checked"
                        if False:   # ARCHIVED
                            try:
                                _verify_img = screen_capture.capture(region)
                                _shop_item_ok, _shop_verify_reason = (
                                    relic_analyzer.verify_shop_item(
                                        _verify_img, self.relic_type_var.get()))
                            except Exception as _ve:
                                _shop_verify_reason = f"error: {_ve}"

                        if _shop_item_ok:
                            # Still on the correct shop item, correct version.
                            # Retry Phase 1 from this position — no ESC needed.
                            _p2_settle_skip_count += 1
                            self._log(
                                f"  Cycle {_batch_i + 1}: Phase 1 did not open preview"
                                f" — still on correct shop item"
                                f" (fail {_p2_settle_skip_count}/{_MAX_P2_SETTLE_SKIPS})"
                                f" — retrying Phase 1 in place.")
                            if _p2_settle_skip_count >= _MAX_P2_SETTLE_SKIPS:
                                self._log(
                                    f"  {_MAX_P2_SETTLE_SKIPS} Phase 1 failures on correct"
                                    f" item — ESC recovery then resetting iteration.")
                                self._esc_to_game_screen(region)
                                # Correct async total to actual submitted count so
                                # workers can finalize this iteration (over-estimate
                                # would prevent done >= total from ever being true).
                                if _p2_async and self._async_state_lock is not None:
                                    with self._async_state_lock:
                                        _istate = (self._async_iter_state or {}).get(iteration)
                                        if _istate is not None:
                                            _istate["total"] = _p2_submitted
                                if _exclude_buy_phase:
                                    self._set_ocr_throttle(False)
                                return relic_results
                            continue   # retry the _p1_try loop without ESC recovery
                        else:
                            # Wrong item, wrong version, OCR inconclusive, or verify
                            # archived — fall through to ESC + Phase 0 recovery below.
                            self._log(
                                f"  Cycle {_batch_i + 1}: Phase 1 failed — shop item"
                                f" check: {_shop_verify_reason} — ESC recovery.")

                    # Nothing detected at all OR shop item wrong/wrong version
                    # → ESC + Phase 0 recovery, then retry
                    if _p1_try < _P1_BATCH_RETRIES:
                        self._log(
                            f"  Cycle {_batch_i + 1}: relic screen not found"
                            f" (try {_p1_try + 1}/{_P1_BATCH_RETRIES + 1})"
                            f" — ESC + Phase 0 recovery.")
                        self._esc_to_game_screen(region)
                        if self.phase_events[0]:
                            # Replay Phase 0 to return to the shop.
                            # No split needed — ESC left us in the game world.
                            self.player.play(
                                self.phase_events[0], extra_delay=_p02_extra_delay)
                            # Wait for shop screen before retrying Phase 1
                            _shop_back = False
                            for _sw in range(20):
                                if not self.bot_running or self._reset_iter_requested:
                                    if _exclude_buy_phase:
                                        self._set_ocr_throttle(False)
                                    if not self.bot_running and capture_only and not _p2_async:
                                        return _bl_captures
                                    return relic_results
                                try:
                                    _sw_img = screen_capture.capture(region)
                                    if relic_analyzer.check_text_visible(
                                            _sw_img, "small jar bazaar", top_fraction=0.15):
                                        time.sleep((3.0 if _lpm else 1.5) * max(1.0, self._perf_gap_mult))
                                        _shop_back = True
                                        break
                                except Exception:
                                    pass
                                time.sleep(0.20)
                            if not _shop_back:
                                self._log("  WARNING: shop not re-detected after"
                                          " Phase 0 recovery — proceeding anyway.")
                            # Murk validation: re-read murk and confirm it is
                            # still a clean multiple of relic cost.  Only fires
                            # here (ESC recovery path) — never on a clean run.
                            # _mval > 0 guard skips the check if OCR can't read.
                            try:
                                _mval_img = screen_capture.capture(region)
                                _mval, _ = relic_analyzer.read_murk(_mval_img)
                                if _mval <= 0:
                                    self._log(
                                        f"  Cycle {_batch_i + 1}: murk validation"
                                        f" failed after ESC recovery — OCR returned"
                                        f" {_mval:,} — resetting iteration.")
                                    if _exclude_buy_phase:
                                        self._set_ocr_throttle(False)
                                    if _p2_async:
                                        self._async_iter_abort_cleanup(
                                            iteration, _p2_submitted)
                                    return relic_results
                            except Exception as _mce:
                                self._log(
                                    f"  Cycle {_batch_i + 1}: murk re-check error:"
                                    f" {_mce} — proceeding.")
                    else:
                        if _batch_i == _buy_count - 1:
                            # Last cycle — all expected purchases are done.
                            # Settle failure here means the preview didn't confirm
                            # (timing or nothing-left-to-highlight edge case), but
                            # the relics WERE bought. Exit the buy loop cleanly
                            # rather than aborting the whole iteration.
                            self._log(
                                f"  Cycle {_batch_i + 1}: last cycle — settle not"
                                f" confirmed after {_P1_BATCH_RETRIES + 1} attempt(s)"
                                f" — buy loop complete.")
                            if _exclude_buy_phase:
                                self._set_ocr_throttle(False)
                            _p1_ok = True
                            _buy_loop_done = True
                        else:
                            self._log(
                                f"  Cycle {_batch_i + 1}: relic screen not found after"
                                f" {_P1_BATCH_RETRIES + 1} attempts — aborting iteration.")
                            if _exclude_buy_phase:
                                self._set_ocr_throttle(False)
                            return relic_results

                if not _p1_ok:
                    if _exclude_buy_phase:
                        self._set_ocr_throttle(False)
                    if _p2_async:
                        self._async_iter_abort_cleanup(iteration, _p2_submitted)
                    return relic_results

                # Update overlay bought count
                if self._overlay:
                    ov = self._overlay
                    _bought_so_far = min((_batch_i + 1) * 10, _p3_count or 0)
                    _tot           = _p3_count or 0
                    self.after(0, lambda b=_bought_so_far, t=_tot: ov.update(
                        bought=f"{b} / {t}") if ov._win else None)

                # ── Phase 2: Scan relics ─────────────────────────────────── #
                # Slot 0 reuses the last settle capture as image bytes (no extra
                # screenshot needed). Slots 1+ tap RIGHT directly (the recorded
                # phase2 sequence has a
                # ~0.914 s pre-press gap from the recording session that is not
                # needed in automation), wait a short settle, then capture+analyze.
                # Skipped entirely if _p1_scan is False (no-passive preview batch).
                if self.phase_events[2] and _p1_scan:
                    if self._diag:
                        self._diag.phase_start(
                            f"Cycle {_batch_i + 1} Phase 2 (scan)",
                            f"slots={_batch_size}")
                    self._set_status(
                        f"{label}: cycle {_batch_i + 1} — scanning "
                        f"{_batch_size} relic(s)…", "#006600")
                    _t_p2_start = time.perf_counter()

                    for _slot in range(_batch_size):
                        if not self.bot_running or self._reset_iter_requested:
                            if _exclude_buy_phase:
                                self._set_ocr_throttle(False)
                            if not self.bot_running and capture_only and not _p2_async:
                                return _bl_captures
                            return relic_results

                        # Advance RIGHT for every slot after the first.
                        # Use a direct tap rather than replaying the recorded sequence —
                        # the recording has a ~0.914 s pre-press idle gap that adds no
                        # value in automation. The settle after RIGHT is kept and scaled
                        # so the preview transition completes before capture.
                        if _slot > 0:
                            self.player.tap("Key.right", hold=0.05)
                            _p2_advance_settle = (0.25 if _lpm else 0.15) * max(1.0, self._perf_gap_mult)
                            time.sleep(_p2_advance_settle)
                            if not self.bot_running or self._reset_iter_requested:
                                if _exclude_buy_phase:
                                    self._set_ocr_throttle(False)
                                if not self.bot_running and capture_only and not _p2_async:
                                    return _bl_captures
                                return relic_results

                        # Capture this relic
                        _relic_num = _relics_scanned + 1
                        self._set_status(
                            f"{label}: relic {_relic_num}…", "#006600")
                        if self._overlay:
                            ov = self._overlay
                            _rn = _relic_num
                            self.after(0, lambda r=_rn: ov.update(
                                relic_num=str(r), analysing=str(r),
                            ) if ov._win else None)
                        self.after(0, self._flash_capture)

                        if _slot == 0 and _settle_img is not None:
                            # Reuse the settle-check capture — no extra screenshot
                            img    = _settle_img
                            result = _settle_result
                        else:
                            try:
                                img = screen_capture.capture(region)
                            except Exception as _ce:
                                self._log(f"  ERROR capturing relic {_relic_num}: {_ce}")
                                img = None
                            result = None

                        # Backlog capture-only mode: save image bytes without analysing.
                        # capture_only=True with no async_iter_meta means pure backlog
                        # mode — no OCR should happen mid-iteration; all analysis is
                        # deferred to _process_backlog_run after the batch ends.
                        if capture_only and not _p2_async:
                            if img is not None:
                                _bl_captures.append((_relics_scanned, img, ""))
                                self._ov_stored_count += 1
                                if self._overlay:
                                    _sto = self._ov_stored_count
                                    self.after(0, lambda s=_sto: (
                                        self._overlay.update(stored=s)
                                        if self._overlay and self._overlay._win else None))
                            _relics_scanned += 1
                            continue

                        # Async mode: ALL slots go straight to the worker queue —
                        # bot advances immediately without waiting for OCR.
                        # Slot 0 uses the settle-check capture for the image bytes
                        # but is still queued (not processed inline) — the settle
                        # result was only used to confirm the screen, not to analyze.
                        if _p2_async:
                            if img is not None:
                                self._async_relic_q.put(
                                    ((iteration, _relics_scanned), {
                                        "iteration":        iteration,
                                        "step_i":           _relics_scanned,
                                        "img_bytes":        img,
                                        "pending_path":     "",
                                        "iter_dir":         iter_dir,
                                        "criteria":         criteria,
                                        "hit_min":          hit_min,
                                        "live_log_path":    live_log_path,
                                        "crop_left":        relic_analyzer._PREVIEW_CROP_LEFT_FRAC,
                                        "crop_top":         relic_analyzer._PREVIEW_CROP_TOP_FRAC,
                                        "relic_type":       self.relic_type_var.get(),
                                        "batch_id":         async_iter_meta.get("batch_id"),
                                        "_run_log_path":    "",
                                        "_retries":         0,
                                        **{k: v for k, v in async_iter_meta.items()
                                           if k in ("run_dir", "criteria_summary",
                                                    "mode_desc", "limit_value",
                                                    "save_filename", "matches_log_path")},
                                    })
                                )
                                _p2_submitted += 1
                                self._ov_stored_count += 1
                                if self._overlay:
                                    _sto = self._ov_stored_count
                                    self.after(0, lambda s=_sto: (
                                        self._overlay.update(stored=s)
                                        if self._overlay and self._overlay._win else None))
                            _relics_scanned += 1
                            continue   # skip inline processing for this slot

                        # Normal (non-async) mode: analyze inline if not already done.
                        if img is not None and result is None:
                            self._ov_stored_count += 1
                            if self._overlay:
                                _sto = self._ov_stored_count
                                self.after(0, lambda s=_sto: (
                                    self._overlay.update(stored=s)
                                    if self._overlay and self._overlay._win else None))
                            try:
                                result = relic_analyzer.analyze(
                                    img, criteria,
                                    crop_left=relic_analyzer._PREVIEW_CROP_LEFT_FRAC,
                                    crop_top=relic_analyzer._PREVIEW_CROP_TOP_FRAC,
                                    relic_type=self.relic_type_var.get(),
                                )
                            except Exception as _ae:
                                self._log(f"  ERROR analyzing relic {_relic_num}: {_ae}")
                                result = None
                            self._ov_stored_count = max(0, self._ov_stored_count - 1)
                            if self._overlay:
                                _sto = self._ov_stored_count
                                self.after(0, lambda s=_sto: (
                                    self._overlay.update(stored=s)
                                    if self._overlay and self._overlay._win else None))

                        # Process result — runs for slot 0 always, and for all slots
                        # in normal mode (slots 1+ in async mode skipped via continue above).
                        if result is not None:
                            self._log_result(result)

                            # Smart Analyze
                            if (self._smart_analyze_var.get()
                                    and not result.get("match", False)):
                                try:
                                    from bot.smart_rules import evaluate_relic as _eval_relic
                                    _r0_sa = (result.get("relics_found", [{}]) or [{}])[0]
                                    _pass_sa = (_r0_sa.get("passives", [])
                                                if isinstance(_r0_sa, dict) else [])
                                    _curse_sa = (_r0_sa.get("curses", [])
                                                 if isinstance(_r0_sa, dict) else [])
                                    _name_sa  = (_r0_sa.get("name", "Unknown")
                                                 if isinstance(_r0_sa, dict) else "Unknown")
                                    _smart_reasons = _eval_relic(_pass_sa)
                                    if _smart_reasons and iter_dir and img:
                                        _smart_dir = os.path.join(
                                            os.path.dirname(iter_dir), "Smart Analyze Hits")
                                        os.makedirs(_smart_dir, exist_ok=True)
                                        _sa_fname = f"Iter_{iteration}_Relic_{_relic_num}_SMART.jpg"
                                        _sa_sep   = "─" * 40
                                        try:
                                            with open(os.path.join(_smart_dir, _sa_fname), "wb") as _f:
                                                _f.write(img)
                                            with open(os.path.join(
                                                    _smart_dir, "Smart Analyze Info.txt"),
                                                    "a", encoding="utf-8") as _f:
                                                _f.write(
                                                    f"{_sa_sep}\n"
                                                    f"  Iter #{iteration:03d}  ·  Relic {_relic_num}"
                                                    f"  [{_sa_fname}]\n"
                                                    f"  Relic : {_name_sa}\n"
                                                    + "".join(f"  + {p}\n" for p in _pass_sa)
                                                    + "".join(f"  ✗ {c}  (curse)\n" for c in _curse_sa)
                                                    + "  Smart rules:\n"
                                                    + "".join(f"    • {r}\n" for r in _smart_reasons)
                                                    + "\n")
                                            self._log(
                                                f"  [Smart] Relic {_relic_num} — "
                                                f"{'; '.join(_smart_reasons)}", overlay=True)
                                        except Exception:
                                            pass
                                        self._ov_smart_hits += 1
                                        if self._overlay:
                                            _sh = self._ov_smart_hits
                                            self.after(0, lambda _sh=_sh:
                                                       self._overlay.update(smart_hits=_sh)
                                                       if self._overlay and self._overlay._win else None)
                                except Exception:
                                    pass

                            # Save screenshot if match or near-miss
                            _saved_fname = ""
                            if iter_dir and img:
                                _is_match = result.get("match", False)
                                _best_nm  = max(
                                    (nm.get("matching_passive_count",
                                            len(nm.get("matching_passives", [])))
                                     for nm in result.get("near_misses", [])),
                                    default=0)
                                _tag = "MATCH" if _is_match else ("HIT" if _best_nm >= hit_min else "")
                                if _tag:
                                    _saved_fname = f"Iter_{iteration}_Relic_{_relic_num}_{_tag}.jpg"
                                    try:
                                        with open(os.path.join(iter_dir, _saved_fname), "wb") as _f:
                                            _f.write(img)
                                    except Exception as _se:
                                        self._log(f"  WARNING: could not save screenshot: {_se}")
                                        _saved_fname = ""

                            result["_image_bytes"]     = None
                            result["_screenshot_file"] = _saved_fname

                            if live_log_path:
                                try:
                                    _relics_f   = result.get("relics_found", [])
                                    _r0f        = _relics_f[0] if _relics_f else {}
                                    _rname_f    = (_r0f.get("name", "Unknown")
                                                   if isinstance(_r0f, dict) else str(_r0f))
                                    _pass_f     = (_r0f.get("passives", [])
                                                   if isinstance(_r0f, dict) else [])
                                    _status_f   = "MATCH" if result.get("match") else "no match"
                                    _line_f     = (f"  Relic {_relic_num:02d}: [{_status_f}] "
                                                   f"{_rname_f}  | {', '.join(_pass_f) or '—'}")
                                    if _saved_fname:
                                        _line_f += f"  → {_saved_fname}"
                                    with open(live_log_path, "a", encoding="utf-8") as _f:
                                        _f.write(_line_f + "\n")
                                except Exception:
                                    pass

                            relic_results.append(result)

                            # In async mode, slot 0 is processed inline but must
                            # also be added to the iter state so _finalize_async_iter_state
                            # sees it alongside the async slot 1+ results.
                            if _p2_async and iteration and _slot == 0:
                                with self._async_state_lock:
                                    _s0_istate = self._async_iter_state.get(iteration)
                                    if _s0_istate is not None:
                                        _s0_istate["results"].append((-1, result))

                            # Overlay tier counters
                            _r_g3, _r_g2, _r_dud = self._count_relic_tiers([result], hit_min)
                            self._ov_hits_33      += _r_g3
                            self._ov_at_33        += _r_g3
                            self._ov_hits_23      += _r_g2
                            self._ov_at_23        += _r_g2
                            self._ov_duds         += _r_dud
                            self._ov_at_duds      += _r_dud
                            self._ov_total_relics += _r_g3 + _r_g2 + _r_dud
                            if _r_g3 > 0 or _r_g2 > 0:
                                _excl_p  = self._get_excluded_passives()
                                _excl_i  = self._get_explicitly_included_passives()
                                _is_excl = (
                                    self._is_passive_excluded(result, _excl_p, _excl_i)
                                    or self._is_curse_blocked(result, self._get_blocked_curses()))
                                if _r_g3 > 0:
                                    if _is_excl:
                                        self._log(
                                            f"  [EXCL] Batch {iteration} · Relic {_relic_num}"
                                            f" — 3/3 match but has excluded passive.")
                                    else:
                                        self._log(
                                            f"★★★ Match Found!  Batch {iteration} · "
                                            f"Relic {_relic_num} — 3/3")
                                        _write_match_entry(iteration, _relic_num,
                                                           "★★★ GOD ROLL (3/3)", result)
                                elif _r_g2 > 0:
                                    if _is_excl:
                                        self._log(
                                            f"  [EXCL] Batch {iteration} · Relic {_relic_num}"
                                            f" — 2/3 match but has excluded passive.")
                                    else:
                                        self._log(
                                            f"★★ Match Found!  Batch {iteration} · "
                                            f"Relic {_relic_num} — 2/3")
                                        _write_match_entry(iteration, _relic_num,
                                                           "★★  HIT (2/3)", result)
                            if iteration:
                                with self._iter_contrib_lock:
                                    c = self._iter_contributions.setdefault(iteration, {})
                                    c["at_33"]        = c.get("at_33",        0) + _r_g3
                                    c["at_23"]        = c.get("at_23",        0) + _r_g2
                                    c["at_duds"]      = c.get("at_duds",      0) + _r_dud
                                    c["hits_33"]      = c.get("hits_33",      0) + _r_g3
                                    c["hits_23"]      = c.get("hits_23",      0) + _r_g2
                                    c["duds"]         = c.get("duds",         0) + _r_dud
                                    c["total_relics"] = c.get("total_relics", 0) + _r_g3 + _r_g2 + _r_dud
                            if self._overlay:
                                ov = self._overlay
                                h33, h23, dds = self._ov_hits_33, self._ov_hits_23, self._ov_duds
                                at33, at23, atd = self._ov_at_33, self._ov_at_23, self._ov_at_duds
                                tot = self._ov_total_relics
                                self.after(0, lambda h33=h33, h23=h23, dds=dds,
                                           at33=at33, at23=at23, atd=atd, tot=tot:
                                           ov.update(hits_33=h33, hits_23=h23, duds=dds,
                                                     at_33=at33, at_23=at23, at_duds=atd,
                                                     stored=0, analyzed=tot)
                                           if ov._win else None)

                        _relics_scanned += 1

                    if self._diag:
                        self._diag.phase_end(
                            f"Cycle {_batch_i + 1} Phase 2 (scan)",
                            slots_scanned=_batch_size)
                    # Record Phase 2 per-relic time for this cycle.
                    if _batch_size > 0:
                        _timing_p2_samples.append(
                            (time.perf_counter() - _t_p2_start) / _batch_size)

                # In excl-ops mode the throttle stays ON through Phase 3 —
                # the batch loop releases it at the close_game call.

                # ── Phase 3: Reset — F to exit preview, back to shop ──────── #
                # Use a direct tap rather than replaying the recorded sequence;
                # the recording has a ~1.0 s pre-press gap that adds no value here.
                if self.phase_events[3]:
                    if not self.bot_running or self._reset_iter_requested:
                        if _p2_async:
                            self._async_iter_abort_cleanup(iteration, _p2_submitted)
                        return relic_results
                    if self._diag:
                        self._diag.phase_start(
                            f"Cycle {_batch_i + 1} Phase 3 (reset)",
                            f"cycle={_batch_i + 1}")
                    self._set_status(f"{label}: resetting to shop…", "green")
                    self._set_ocr_throttle(True)   # pause workers during Phase 3 F press
                    self.player.tap("f", hold=0.05)
                    if not _exclude_buy_phase:     # excl-ops: batch loop releases at close_game
                        self._set_ocr_throttle(False)  # resume — workers can run during shop settle
                    time.sleep(0.40)   # shop ready within ~239ms of F release
                    if self._diag:
                        self._diag.phase_end(f"Cycle {_batch_i + 1} Phase 3 (reset)")

            self._log(f"  Scan loop complete — {_relics_scanned} relic(s) scanned.")

            # ── Async Phase 2: finalize iter_state total ─────────────── #
            # Now we know the exact count submitted. Update total so workers
            # know when finalization should fire. If all tasks already finished
            # while we were still in the loop, finalize immediately.
            if _p2_async:
                _p2_finalize_now = False
                with self._async_state_lock:
                    _istate = self._async_iter_state.get(iteration)
                    if _istate is not None:
                        if _p2_submitted == 0:
                            # Nothing was queued — all batches failed settle check.
                            # Finalize immediately so the iteration isn't left dangling.
                            _istate["total"] = 0
                            if not _istate.get("_finalized"):
                                _istate["_finalized"] = True
                                _p2_finalize_now = True
                        else:
                            _istate["total"] = _p2_submitted
                            if (_istate["done"] >= _p2_submitted
                                    and not _istate.get("_finalized")):
                                _istate["_finalized"] = True
                                _p2_finalize_now = True
                if _p2_finalize_now and self._async_results_list is not None:
                    self._finalize_async_iter_state(
                        iteration, self._async_iter_state,
                        self._async_state_lock, self._async_dir_map,
                        self._async_results_list)

        if not self.bot_running or self._reset_iter_requested:
            return relic_results

        # ── Phase 4: Review Step Loop (analyze each relic) ─────────── #
        if self.phase_events[4]:
            _p4_count = _actual_bought if _actual_bought is not None else _p3_count
            total = _p4_count if _p4_count is not None else _P4_FAILSAFE
            if _p0_exe:
                self._focus_game_window(_p0_exe, timeout=2.0)

            # Initial settle — lets the Sell screen fully stabilise after
            # Phase 3's F2 navigation before the first advance input fires.
            # Without this, the RIGHT arrow at step 1 can be swallowed by a
            # still-animating menu transition, causing relic 1 to be captured
            # twice. Scaled by _perf_gap_mult so slower systems wait longer.
            time.sleep(_p4_init_settle)
            if not self.bot_running or self._reset_iter_requested:
                return relic_results if not capture_only else []

            # ── Capture-only mode (async analysis) ──────────────────── #
            if capture_only:
                captures = []
                for step_i in range(total):
                    if not self.bot_running:
                        return captures
                    if not self.bot_running:
                        return captures
                    if step_i > 0:
                        self.player.play_fast(self.phase_events[4], gap=_p4_advance_gap)
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
            _gpu_worker_cap = 4 if self._gpu_accel_var.get() else 8
            _workers = (max(2, min(_gpu_worker_cap, self._parallel_workers_var.get()))
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
                    self.player.play_fast(self.phase_events[4], gap=_p4_advance_gap)
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

                self._log_result(result)
                time.sleep(0.05)   # let the main thread render the log line

                # Smart Analyze: evaluate non-matching relics against curated rules
                if (self._smart_analyze_var.get()
                        and not result.get("match", False)):
                    try:
                        from bot.smart_rules import evaluate_relic as _eval_relic
                        _r0_sa = (result.get("relics_found", [{}]) or [{}])[0]
                        _passives_sa = (_r0_sa.get("passives", [])
                                        if isinstance(_r0_sa, dict) else [])
                        _smart_reasons = _eval_relic(_passives_sa)
                        if _smart_reasons and iter_dir and img:
                            _smart_dir = os.path.join(
                                os.path.dirname(iter_dir), "Smart Analyze Hits")
                            os.makedirs(_smart_dir, exist_ok=True)
                            _sa_fname = f"iter_{iteration:03d}_relic_{step_i + 1:02d}_SMART.jpg"
                            try:
                                with open(os.path.join(_smart_dir, _sa_fname), "wb") as _f:
                                    _f.write(img)
                                with open(os.path.join(_smart_dir, "smart_hits.log"), "a",
                                          encoding="utf-8") as _f:
                                    _f.write(
                                        f"Batch {iteration} · Relic {step_i + 1}  [{_sa_fname}]\n"
                                        + "".join(f"  • {r}\n" for r in _smart_reasons)
                                    )
                                self._log(
                                    f"  [Smart] Relic {step_i + 1} — {'; '.join(_smart_reasons)}",
                                    overlay=True)
                            except Exception:
                                pass
                            self._ov_smart_hits += 1
                            if self._overlay:
                                _sh = self._ov_smart_hits
                                self.after(0, lambda _sh=_sh:
                                           self._overlay.update(smart_hits=_sh)
                                           if self._overlay and self._overlay._win else None)
                    except Exception:
                        pass

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
                            self._log(f"  Screenshot saved: {saved_fname}", overlay=False)
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
                self._ov_hits_33      += r_g3
                self._ov_at_33        += r_g3
                self._ov_hits_23      += r_g2
                self._ov_at_23        += r_g2
                self._ov_duds         += r_dud
                self._ov_at_duds      += r_dud
                self._ov_total_relics += r_g3 + r_g2 + r_dud
                if r_g3 > 0:
                    self._log(
                        f"★★★ Match Found!  Batch {iteration} · Relic {step_i + 1} — 3/3")
                    _write_match_entry(iteration, step_i + 1, "★★★ GOD ROLL (3/3)", result)
                elif r_g2 > 0:
                    self._log(
                        f"★★ Match Found!  Batch {iteration} · Relic {step_i + 1} — 2/3")
                    _write_match_entry(iteration, step_i + 1, "★★  HIT (2/3)", result)
                # Track per-iteration contributions for rollback on reset
                if iteration:
                    with self._iter_contrib_lock:
                        c = self._iter_contributions.setdefault(iteration, {})
                        c["at_33"]        = c.get("at_33",        0) + r_g3
                        c["at_23"]        = c.get("at_23",        0) + r_g2
                        c["at_duds"]      = c.get("at_duds",      0) + r_dud
                        c["hits_33"]      = c.get("hits_33",      0) + r_g3
                        c["hits_23"]      = c.get("hits_23",      0) + r_g2
                        c["duds"]         = c.get("duds",         0) + r_dud
                        c["total_relics"] = c.get("total_relics", 0) + r_g3 + r_g2 + r_dud
                if self._overlay:
                    ov = self._overlay
                    h33, h23, dds = self._ov_hits_33, self._ov_hits_23, self._ov_duds
                    at33, at23, atd = self._ov_at_33, self._ov_at_23, self._ov_at_duds
                    tot = self._ov_total_relics
                    self.after(0, lambda h33=h33, h23=h23, dds=dds,
                               at33=at33, at23=at23, atd=atd, tot=tot:
                               ov.update(hits_33=h33, hits_23=h23, duds=dds,
                                         at_33=at33, at_23=at23, at_duds=atd,
                                         stored=0, analyzed=tot)
                               if ov._win else None)

            for _t in _worker_threads:
                _t.join(timeout=2.0)

            for result in ordered:
                if result is not None:
                    relic_results.append(result)

            return relic_results

        # ── No Phase 4: fall back to single capture + analyze ────────── #
        if capture_only:
            # In the P2-async path (async_iter_meta passed, Phase 4 empty),
            # slot 0 of each batch was already analyzed inline and slots 1+
            # were already submitted to _async_relic_q.  The outer async loop
            # checks len(captures)==0 to know all submissions are in the queue
            # — returning relic_results (analyze dicts) would make len != 0
            # and cause a ValueError when the outer loop tries to unpack them
            # as (step_i, img_bytes, pending_path) tuples, silently crashing
            # the bot thread and leaving the game window open forever.
            if capture_only and not _p2_async:
                return _bl_captures   # backlog mode: return captured images, no analysis done
            # Flush iteration timing sample — only on clean completion (not early abort).
            if _timing_p1_samples or _timing_p2_samples:
                self._record_timing_sample(
                    lpm=_lpm,
                    phase0_secs=_timing_p0_secs,
                    phase1_per_relic=(sum(_timing_p1_samples) / len(_timing_p1_samples)
                                      if _timing_p1_samples else None),
                    phase2_per_relic=(sum(_timing_p2_samples) / len(_timing_p2_samples)
                                      if _timing_p2_samples else None),
                )
            return [] if _p2_async else relic_results

        self._set_status(f"{label}: waiting for relic screen…", "green")
        time.sleep(3.0)
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
                        elif key == "hits_23":       self._ov_at_23        = int(val)
                        elif key == "duds":          self._ov_at_duds      = int(val)
                        elif key == "total_relics":  self._ov_total_relics = int(val)
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
                f.write(f"duds = {self._ov_at_duds}\n")
                f.write(f"total_relics = {self._ov_total_relics}\n\n")

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
            _mp = r.get("matched_passives", [])
            n = len(_mp)
            # Pairing matches (↔) are labelled HIT at most — never GOD ROLL
            if n > 2 and any("\u2194" in str(p) for p in _mp):
                n = 2
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
        if not self.batch_output_var.get():
            messagebox.showwarning("No Output Folder", "Choose an output folder for batch results.")
            return False
        try:
            v = int(self.batch_limit_var.get())
            if v <= 0:
                raise ValueError
            if v > 1000:
                messagebox.showwarning("Limit Too High", "Maximum allowed loops is 1000.")
                return False
        except ValueError:
            messagebox.showwarning("Invalid Limit", "Loop count must be a number between 1 and 1000.")
            return False
        return True

    def _flash_capture(self):
        """Briefly highlight the 📷 indicator when a screenshot is taken."""
        self.capture_lbl.config(foreground="green")
        self.after(600, lambda: self.capture_lbl.config(foreground="lightgray"))

    def _get_region(self):
        return None

    def _on_color_change(self):
        enabled = {c for c, v in self._color_vars.items() if v.get()}
        if not enabled:
            # Keep only the last enabled color — don't re-enable the others
            for c in self._prev_colors:
                self._color_vars[c].set(True)
            # Cancel any pending dismiss job and start a fresh one
            if self._color_warn_job:
                self.after_cancel(self._color_warn_job)
            self._color_warn.configure(text="At least one color must be enabled.")
            self._color_warn_job = self.after(
                5000, lambda: self._color_warn.configure(text=""))
        else:
            self._prev_colors = enabled
            self._color_warn.configure(text="")
            if self._color_warn_job:
                self.after_cancel(self._color_warn_job)
                self._color_warn_job = None
        self.relic_builder.set_relic_context(
            self.relic_type_var.get(), self._get_allowed_colors())

    def _slider_key_press(self, delta: int):
        """Move the Odds Viewer slider by delta on arrow key press, with hold-repeat."""
        v = int(round(self._ov_slider.get()))
        new_v = max(1, min(500, v + delta))
        self._ov_slider.set(new_v)
        self._ov_n_var.set(new_v)
        self._update_odds_viewer()
        if self._ov_key_repeat:
            self.after_cancel(self._ov_key_repeat)
        self._ov_key_repeat = self.after(400, lambda: self._slider_key_repeat(delta))

    def _slider_key_repeat(self, delta: int):
        """Continue moving slider while key is held."""
        v = int(round(self._ov_slider.get()))
        new_v = max(1, min(500, v + delta))
        self._ov_slider.set(new_v)
        self._ov_n_var.set(new_v)
        self._update_odds_viewer()
        self._ov_key_repeat = self.after(50, lambda: self._slider_key_repeat(delta))

    def _slider_key_release(self):
        if self._ov_key_repeat:
            self.after_cancel(self._ov_key_repeat)
            self._ov_key_repeat = None

    def _update_odds_viewer(self):
        """Refresh the Odds Viewer panel from the current criteria probability and slider."""
        try:
            p = self.relic_builder.get_current_p_per_relic()
            n = int(self._ov_n_var.get())
        except Exception:
            return

        self._ov_n_lbl.configure(text=str(n))

        if not p or p <= 0:
            _txt = self._ov_result_txt
            _txt.configure(state="normal")
            _txt.delete("1.0", "end")
            _txt.insert("end", "Set relic criteria (Build Exact Relic or Passive Pool) to see projections.", "muted")
            _txt.configure(state="disabled")
            return

        from bot.probability_engine import prob_success_in_n, format_duration, prob_curse_pass

        # ── Curse filter adjustment (Deep mode only) ───────────────────────── #
        rtype = self.relic_type_var.get()
        n_blocked_curses = len(getattr(self, "_blocked_curses_list", []))
        if rtype == "night" and n_blocked_curses > 0:
            p_curse = prob_curse_pass(n_blocked_curses, rtype)
            p = p * p_curse  # adjust base probability for curse exclusions

        if p <= 0:
            _txt = self._ov_result_txt
            _txt.configure(state="normal")
            _txt.delete("1.0", "end")
            _txt.insert("end", "Set relic criteria (Build Exact Relic or Passive Pool) to see projections.", "muted")
            _txt.configure(state="disabled")
            return

        # ── Timing model ──────────────────────────────────────────────────── #
        lpm_on      = getattr(self, "_low_perf_mode_var", None)
        parallel_on = getattr(self, "_parallel_enabled_var", None)
        async_on    = getattr(self, "_async_enabled_var", None)
        workers_var = getattr(self, "_parallel_workers_var", None)
        gpu_accel   = getattr(self, "_gpu_accel_var", None) and self._gpu_accel_var.get()
        hybrid_on   = gpu_accel and getattr(self, "_hybrid_var", None) and self._hybrid_var.get()
        gpu_aa_on   = hybrid_on and getattr(self, "_gpu_always_analyze_var", None) and self._gpu_always_analyze_var.get()

        # Timing model — buy-phase scanning architecture (Proposal 1):
        #   Phase 0: shop nav once per iteration (~20 s flat)
        #   Phase 1: buy + settle per relic (~2.0 s avg, ~2.5 s LPM)
        #   Phase 2: RIGHT + gap + capture per relic (0.30 s normal, 0.45 s LPM)
        #   OCR: 3.0 s/relic CPU; 0.3 s/relic GPU; divided by worker count (Brute Force)
        #   Hybrid: 1 GPU + N CPU workers sharing queue; GPU AA suppresses CPU workers
        #   Async: overlaps OCR with next iteration's game time
        #   Backlog: zero OCR during game; all analysis runs after run ends
        backlog_var = getattr(self, "_backlog_mode_var", None)
        is_backlog  = backlog_var and backlog_var.get()
        lpm         = lpm_on and lpm_on.get()

        # ── Use measured timings if enough samples exist ──────────────────── #
        _MIN_SAMPLES   = 3
        _td            = getattr(self, "_timing_data", {})
        _lpm_key       = "lpm_on" if lpm else "lpm_off"
        _gi            = _td.get("game_inputs", {}).get(_lpm_key, {})
        _ocr_td        = _td.get("ocr", {})
        _ocr_key       = "gpu" if gpu_accel else "cpu"

        def _calibrated(entry: dict, fallback: float) -> tuple[float, int]:
            """Return (value, sample_count) — value is measured if enough samples."""
            n = entry.get("n", 0)
            s = entry.get("sum", 0.0)
            if n >= _MIN_SAMPLES and s > 0:
                return s / n, n
            return fallback, 0

        _p0_entry  = _gi.get("phase0", {})
        _p1_entry  = _gi.get("phase1", {})
        _p2_entry  = _gi.get("phase2", {})
        _ocr_entry = _ocr_td.get(_ocr_key, {})

        sec_fixed,     _n_p0  = _calibrated(_p0_entry,  20.0)
        sec_buy_relic, _n_p1  = _calibrated(_p1_entry,  2.5 if lpm else 2.0)
        sec_nav_relic, _n_p2  = _calibrated(_p2_entry,  0.45 if lpm else 0.30)

        # Per-relic OCR cost
        workers = (workers_var.get() if (workers_var and parallel_on and parallel_on.get()) else 1)
        if gpu_aa_on:
            # GPU Always Analyze → CPU workers suppressed → 1 GPU worker only
            _ocr_fallback = 0.3
            sec_analyze_raw, _n_ocr = _calibrated(_ocr_entry, _ocr_fallback)
            sec_analyze = sec_analyze_raw
        elif hybrid_on:
            # 1 GPU (0.3 s) + workers CPU (3.0 s each) sharing queue — combined throughput
            _gpu_rate = 1.0 / 0.3
            _cpu_rate = workers / 3.0
            sec_analyze = 1.0 / (_gpu_rate + _cpu_rate)
            _n_ocr = 0
        elif gpu_accel:
            # GPU only
            _ocr_fallback = 0.3
            sec_analyze_raw, _n_ocr = _calibrated(_ocr_entry, _ocr_fallback)
            sec_analyze = sec_analyze_raw
        else:
            # CPU only — Brute Force workers reduce wall-clock time proportionally
            _ocr_fallback = {1: 3.0, 2: 1.5, 3: 1.0, 4: 0.8}.get(min(workers, 4), 0.6)
            sec_analyze_raw, _n_ocr = _calibrated(_ocr_entry, _ocr_fallback)
            sec_analyze = sec_analyze_raw / max(1, workers)

        # Calibration note for display — show count of game-input samples
        _game_cal_n = min(v for v in (_n_p0, _n_p1, _n_p2) if v >= _MIN_SAMPLES) \
            if any(v >= _MIN_SAMPLES for v in (_n_p0, _n_p1, _n_p2)) else 0
        _cal_note = f"  ·  calibrated from {_game_cal_n} run(s)" if _game_cal_n else ""

        is_async = (async_on and async_on.get()) and not is_backlog

        # Rolling time (game inputs only, no OCR)
        sec_rolling_total = sec_fixed + n * (sec_buy_relic + sec_nav_relic)

        if is_backlog:
            # Game runs at full speed — no OCR overhead per iteration
            sec_per_iter_ideal = sec_rolling_total
        elif is_async:
            # OCR overlaps with game inputs — iteration wall-clock ≈ rolling only
            sec_per_iter_ideal = sec_rolling_total
        else:
            # Synchronous: OCR blocks after each iteration
            sec_per_iter_ideal = sec_rolling_total + n * sec_analyze

        sec_roll_display = sec_rolling_total / n if n > 0 else sec_buy_relic + sec_nav_relic

        try:
            loops = max(1, int(self.batch_limit_var.get()))
        except (AttributeError, ValueError):
            loops = 1

        if is_backlog:
            # All OCR runs after the batch ends (game not running — workers get full CPU)
            total_batch_sec = loops * sec_per_iter_ideal + loops * n * sec_analyze
        elif is_async:
            # Tail: last iteration's analysis runs after game stops
            total_batch_sec = loops * sec_per_iter_ideal + n * sec_analyze
        else:
            total_batch_sec = loops * sec_per_iter_ideal

        # ── Probability stats ─────────────────────────────────────────────── #
        p_at_n     = prob_success_in_n(p, n)
        exp_relics = 1.0 / p
        exp_iters  = exp_relics / n

        murk_per_relic = 1800 if rtype == "night" else 600
        murk_per_iter  = n * murk_per_relic

        # Precise % formatting — show enough decimal places for the first non-zero digit
        import math as _math
        def _fmt_pct(v: float) -> str:
            pct = v * 100
            if pct <= 0:
                return "0%"
            if pct >= 10:
                return f"{pct:.1f}%"
            if pct >= 1:
                return f"{pct:.2f}%"
            digits = max(1, -int(_math.floor(_math.log10(pct))) + 1)
            return f"{pct:.{digits}f}%"

        curse_note = (f"  |  {n_blocked_curses} curse(s) blocked"
                      if n_blocked_curses > 0 and rtype == "night" else "")

        result_lines = [
            f"  Odds of finding a desired relic in {n:,}-relic iteration:  "
            f"{_fmt_pct(p_at_n)}  (~1 in {int(round(1/p)):,} relics expected{curse_note})",
            f"  Expected iterations to find a match:  ~{exp_iters:.1f}",
            f"  Total Murk Cost for {n:,} relics:  {murk_per_iter:,} murk",
            f"  Ideal time per iteration ({n:,} relics, ~{sec_roll_display:.1f} s/relic amortised):  "
            f"{format_duration(sec_per_iter_ideal)}{_cal_note}",
            f"  Expected time for {loops:,} loops:  {format_duration(total_batch_sec)}",
        ]
        if is_backlog:
            result_lines.append(
                f"  Backlog OCR tail:  ~{format_duration(loops * n * sec_analyze)}"
                f" after run ends (game not running — full CPU)"
            )

        # ── Update Odds Viewer text (selectable) ──────────────────────────── #
        _txt = self._ov_result_txt
        _txt.configure(state="normal")
        _txt.delete("1.0", "end")
        _txt.insert("end", "\n".join(result_lines), "normal")
        _txt.configure(state="disabled")

        # ── Setting Stats panel ───────────────────────────────────────────── #
        # Detect conflicting settings (mutual exclusion should prevent this,
        # but show a warning if both somehow end up active simultaneously).
        _async_active   = is_async
        _backlog_active = is_backlog
        _lpm_active     = lpm
        _bf_active      = parallel_on and parallel_on.get()

        conflicts = []
        if _async_active and _backlog_active:
            conflicts.append("Async Analysis and Backlog Analysis are both ON — disable one.")
        if _lpm_active and _bf_active:
            conflicts.append("Low Performance Mode disables Brute Force — disable one.")

        ss_lines = []   # list of (text, tag)
        ss_lines.append(("Active modes:\n", "heading"))

        _intermittent_active = _backlog_active and getattr(self, "_intermittent_backlog_var", None) and self._intermittent_backlog_var.get()
        _every_n = getattr(self, "_intermittent_every_n_var", None) and self._intermittent_every_n_var.get()

        active_parts = []
        if gpu_accel:
            active_parts.append(f"GPU Acceleration (~0.3 s/relic OCR, {self._hw_gpu_name})")
        if hybrid_on:
            if gpu_aa_on:
                active_parts.append(f"Hybrid GPU+CPU + GPU Always Analyze (GPU worker only, ~0.3 s/relic)")
            else:
                active_parts.append(f"Hybrid GPU+CPU (1 GPU + {workers} CPU worker(s), ~{sec_analyze:.2f} s/relic effective)")
        if _async_active:
            active_parts.append("Async Analysis (OCR overlaps game navigation)")
        if _backlog_active:
            if _intermittent_active:
                active_parts.append(f"Intermittent Backlog (drain every {_every_n} iteration(s), OCR after each drain)")
            else:
                active_parts.append("Backlog Analysis (OCR deferred until after run)")
        if _bf_active and not hybrid_on:
            active_parts.append(f"Brute Force Analysis ({workers} workers)")
        if _lpm_active:
            active_parts.append("Low Performance Mode (+0.5 s/relic buy, +0.15 s/relic nav)")
        if n_blocked_curses > 0 and rtype == "night":
            active_parts.append(f"{n_blocked_curses} curse filter(s) active (probability adjusted)")

        if active_parts:
            for part in active_parts:
                ss_lines.append((f"  • {part}\n", "active"))
        else:
            ss_lines.append(("  No special modes active — standard sync CPU analysis.\n", "muted"))

        if conflicts:
            ss_lines.append(("\nConflicting settings detected:\n", "warn"))
            for c in conflicts:
                ss_lines.append((f"  ⚠ {c}\n", "warn"))

        _ss = self._setting_stats_txt
        _ss.configure(state="normal")
        _ss.delete("1.0", "end")
        for text, tag in ss_lines:
            _ss.insert("end", text, tag)
        # Resize height to fit content
        line_count = int(_ss.index("end-1c").split(".")[0])
        _ss.configure(height=max(3, line_count), state="disabled")

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

    @staticmethod
    def _detect_hardware() -> tuple[int, int, str]:
        """Return (ram_gb, cpu_cores, gpu_name). Never raises."""
        ram_gb = 0
        try:
            import ctypes
            class _MEMSTAT(ctypes.Structure):
                _fields_ = [
                    ("dwLength",               ctypes.c_ulong),
                    ("dwMemoryLoad",           ctypes.c_ulong),
                    ("ullTotalPhys",           ctypes.c_ulonglong),
                    ("ullAvailPhys",           ctypes.c_ulonglong),
                    ("ullTotalPageFile",       ctypes.c_ulonglong),
                    ("ullAvailPageFile",       ctypes.c_ulonglong),
                    ("ullTotalVirtual",        ctypes.c_ulonglong),
                    ("ullAvailVirtual",        ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = _MEMSTAT()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            ram_gb = int(stat.ullTotalPhys // (1024 ** 3))
        except Exception:
            pass

        cpu_cores = 0
        try:
            import os
            cpu_cores = os.cpu_count() or 0
        except Exception:
            pass

        gpu_name = "Unknown GPU"
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name", "/value"],
                capture_output=True, text=True, timeout=3,
            )
            names = [
                line.split("=", 1)[1].strip()
                for line in result.stdout.splitlines()
                if line.startswith("Name=") and line.split("=", 1)[1].strip()
            ]
            # Prefer NVIDIA/AMD discrete GPU if present
            discrete = [n for n in names if any(k in n for k in ("NVIDIA", "Radeon RX", "RTX", "GTX"))]
            gpu_name = discrete[0] if discrete else (names[0] if names else "Unknown GPU")
        except Exception:
            pass

        return ram_gb, cpu_cores, gpu_name

    @staticmethod
    def _check_cuda_available() -> tuple[bool, str]:
        """Return (available, error_message). Never raises."""
        try:
            import torch
            if torch.cuda.is_available():
                return True, ""
            # Attempt init to capture the specific failure reason
            try:
                torch.cuda.init()
                return True, ""
            except Exception as e:
                return False, str(e)
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _cuda_torch_installed() -> bool:
        """
        Return True if CUDA torch files appear to be installed next to the EXE.
        Checks for cudart64_12.dll in _internal/torch/lib/, which is only present
        after a successful GPU Acceleration install (the CPU torch bundle omits it).
        Used to distinguish "never installed" from "installed but CUDA init failed".
        """
        try:
            import sys as _sys
            import pathlib as _pl
            if getattr(_sys, 'frozen', False):
                exe_dir = _pl.Path(_sys.executable).parent
            else:
                exe_dir = _pl.Path(__file__).parent.parent
            cudart = exe_dir / "_internal" / "torch" / "lib" / "cudart64_12.dll"
            return cudart.exists()
        except Exception:
            return False

    @staticmethod
    def _check_gpu_install_eligible() -> tuple[bool, str, str]:
        """
        Check whether this system can install GPU Acceleration.
        Uses nvidia-smi to read compute capability and driver version.
        Returns (eligible, gpu_name, reason).

        Requirements (PyTorch cu126 on Windows):
          compute ≥ 6.1  — GTX 10-series (Pascal) minimum; GTX 900-series excluded
          driver  ≥ 572.13 — Windows R570, CUDA 12.6 minimum
        """
        _MIN_COMPUTE = 6.1
        _MIN_DRIVER  = 572.13
        try:
            result = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=name,driver_version,compute_cap",
                 "--format=csv,noheader"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return False, "", "No NVIDIA GPU detected."
            line  = result.stdout.strip().split("\n")[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                return False, "", "Unexpected nvidia-smi output."
            name, driver_str, compute_str = parts[0], parts[1], parts[2]
            try:
                compute = float(compute_str)
            except ValueError:
                return False, name, f"Could not read compute capability: {compute_str}"
            try:
                d = driver_str.split(".")
                driver = float(f"{d[0]}.{d[1]}")
            except (ValueError, IndexError):
                return False, name, f"Could not read driver version: {driver_str}"
            if compute < _MIN_COMPUTE:
                return False, name, (
                    f"{name} (compute {compute_str}) is not supported by PyTorch CUDA 12.6. "
                    f"GPU Acceleration requires a GTX 10-series or newer."
                )
            if driver < _MIN_DRIVER:
                return False, name, (
                    f"Driver {driver_str} is below the minimum for CUDA 12.6 "
                    f"(requires {_MIN_DRIVER}+). Update your NVIDIA drivers."
                )
            return True, name, f"{name} (compute {compute_str}, driver {driver_str})"
        except FileNotFoundError:
            return False, "", "NVIDIA drivers not installed (nvidia-smi not found)."
        except subprocess.TimeoutExpired:
            return False, "", "GPU check timed out."
        except Exception as e:
            return False, "", f"GPU check error: {e}"

    def _export_diagnostics(self):
        """
        Collect system/GPU/file diagnostics into a small text file and open it.
        The user can then share this file for remote diagnosis without
        needing to copy the entire bot folder.
        """
        import datetime
        import pathlib as _pl

        lines = []
        lines.append("=== RelicBot Diagnostics Report ===")
        lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # ── Bot / exe info ────────────────────────────────────────────── #
        lines.append("=== Bot Info ===")
        frozen = getattr(sys, "frozen", False)
        lines.append(f"Frozen EXE: {frozen}")
        if frozen:
            exe_dir = _pl.Path(sys.executable).parent
            lines.append(f"EXE path:   {sys.executable}")
        else:
            exe_dir = _pl.Path(__file__).parent.parent
            lines.append(f"Source dir: {exe_dir}")
        lines.append("")

        # ── Hardware / CUDA ───────────────────────────────────────────── #
        lines.append("=== Hardware & CUDA ===")
        lines.append(f"GPU name:              {self._hw_gpu_name or 'unknown'}")
        lines.append(f"RAM:                   {self._hw_ram_gb or 'unknown'} GB")
        lines.append(f"CPU cores:             {self._hw_cpu_cores or 'unknown'}")
        lines.append(f"CUDA available:        {self._hw_cuda_available}")
        lines.append(f"CUDA error:            {self._hw_cuda_error or 'none'}")
        lines.append(f"CUDA torch installed:  {self._hw_cuda_torch_installed}")
        lines.append(f"GPU eligible to install: {self._gpu_eligible}")
        if self._gpu_eligible_name:
            lines.append(f"GPU eligible name:     {self._gpu_eligible_name}")
        if self._gpu_eligible_reason:
            lines.append(f"GPU eligible reason:   {self._gpu_eligible_reason}")
        lines.append("")

        # ── Key file presence ─────────────────────────────────────────── #
        lines.append("=== Key Files ===")
        _check_paths = [
            exe_dir / "_internal" / "torch" / "lib" / "cudart64_12.dll",
            exe_dir / "_internal" / "torch" / "lib" / "torch_cuda.dll",
            exe_dir / "_internal" / "torch" / "lib" / "c10_cuda.dll",
            exe_dir / "_internal" / "torch" / "lib" / "c10.dll",
            exe_dir / "gpu_upgrade_ready",
            exe_dir / "gpu_upgrade.log",
            exe_dir / "gpu_torch_staging",
            exe_dir / "gpu_torch_download",
        ]
        for p in _check_paths:
            rel = p.relative_to(exe_dir) if frozen else p.name
            try:
                if p.is_dir():
                    n = sum(1 for _ in p.rglob("*") if _.is_file())
                    lines.append(f"  {rel}/  DIR ({n} files)")
                elif p.exists():
                    sz_mb = p.stat().st_size / (1024 * 1024)
                    lines.append(f"  {rel}  EXISTS ({sz_mb:.1f} MB)")
                else:
                    lines.append(f"  {rel}  not found")
            except Exception as e:
                lines.append(f"  {rel}  error: {e}")
        lines.append("")

        # ── gpu_upgrade.log ───────────────────────────────────────────── #
        lines.append("=== gpu_upgrade.log ===")
        _log_file = exe_dir / "gpu_upgrade.log"
        if _log_file.exists():
            try:
                lines.append(_log_file.read_text(encoding="utf-8", errors="replace"))
            except Exception as e:
                lines.append(f"[read error: {e}]")
        else:
            lines.append("[file not found — no upgrade has been attempted this session]")
        lines.append("")

        # ── Current settings snapshot ─────────────────────────────────── #
        lines.append("=== Current Settings ===")
        try:
            lines.append(f"Relic type:              {self.relic_type_var.get()}")
            lines.append(f"GPU Acceleration:        {self._gpu_accel_var.get()}")
            lines.append(f"Low Perf Mode:           {self._low_perf_mode_var.get()}")
            lines.append(f"Parallel workers:        {self._parallel_enabled_var.get()} ({self._parallel_workers_var.get()} workers)")
            lines.append(f"Async Analysis:          {self._async_enabled_var.get()}")
            lines.append(f"Smart Throttle:          {self._smart_throttle_var.get()}")
            lines.append(f"Excl. Analysis (ops):    {self._exclude_buy_phase_var.get()}")
            lines.append(f"Smart Analyze:           {self._smart_analyze_var.get()}")
            lines.append(f"Backlog Mode:            {self._backlog_mode_var.get()}")
            lines.append(f"Intermittent Backlog:    {self._intermittent_backlog_var.get()} (every {self._intermittent_every_n_var.get()} batches)")
            lines.append(f"Perf gap mult:           {self._perf_gap_mult:.3f}×  (1.0 = baseline, rises with load time)")
            lines.append(f"Phase 0 configured:      {bool(self.phase_events[0])}")
            lines.append(f"Phase 1 configured:      {bool(self.phase_events[1])}")
            lines.append(f"Phase 2 configured:      {bool(self.phase_events[2])}")
            lines.append(f"Phase 3 configured:      {bool(self.phase_events[3])}")
        except Exception as e:
            lines.append(f"[settings read error: {e}]")
        lines.append("")

        # ── Most recent .diag file ────────────────────────────────────── #
        lines.append("=== Most Recent Batch .diag File ===")
        try:
            _batch_dir = _pl.Path(self.batch_output_var.get())
            _diag_files = sorted(_batch_dir.rglob("*.diag"), key=lambda f: f.stat().st_mtime)
            if _diag_files:
                _latest = _diag_files[-1]
                lines.append(f"File: {_latest}")
                lines.append(_latest.read_text(encoding="utf-8", errors="replace"))
            else:
                lines.append("[no .diag files found in batch output folder]")
        except Exception as e:
            lines.append(f"[error reading .diag: {e}]")
        lines.append("")

        # ── Write and open ────────────────────────────────────────────── #
        _ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        _out_path = exe_dir / f"relicbot_diag_{_ts}.txt"
        try:
            _out_path.write_text("\n".join(lines), encoding="utf-8")
            # Open the file's folder and select the file
            import subprocess as _sp
            _sp.Popen(["explorer", "/select,", str(_out_path)])
            tk.messagebox.showinfo(
                "Diagnostics Exported",
                f"Saved to:\n{_out_path}\n\nThe folder has been opened with the file selected."
            )
        except Exception as e:
            tk.messagebox.showerror("Export Failed", f"Could not write diagnostics file:\n{e}")

    def _install_gpu_acceleration(self):
        """Show the GPU install dialog and run pip CUDA torch install in a thread."""
        import threading
        import pathlib as _pl

        _exe_dir     = _pl.Path(sys.executable).parent
        _staging_dir = str(_exe_dir / "gpu_torch_staging")
        # Phase 1 resolve cmd — pip --dry-run --report gives us the wheel URL
        # Phase 2 downloads via urllib (real live progress)
        # Phase 3 installs from local wheel via pip --no-index
        # Phase 4 removes test/distributed folders (safe — no DLL deps)
        _resolve_cmd_base = [
            sys.executable, "--run-pip", "install", "torch",
            "--index-url", "https://download.pytorch.org/whl/cu126",
            "--no-deps", "--dry-run", "--report",  # <report_path> appended at runtime
        ]

        dlg = tk.Toplevel(self)
        dlg.title("Install GPU Acceleration")
        dlg.resizable(False, False)
        dlg.grab_set()

        ttk.Label(
            dlg,
            text=(
                f"Installing PyTorch CUDA 12.6 for {self._gpu_eligible_name}.\n"
                "4 steps: Resolve  →  Download (~2.5 GB)  →  Extract  →  Optimize\n"
                "Step 1 (Resolve) contacts PyTorch servers and may take 30–90 s\n"
                "before the download begins.  Do not close this window."
            ),
            wraplength=520, justify="left",
        ).pack(padx=16, pady=(12, 4))

        # ── Download progress area ────────────────────────────────────────── #
        prog_frame = ttk.Frame(dlg)
        prog_frame.pack(padx=16, pady=(2, 0), fill="x")

        download_file_var = tk.StringVar(value="Connecting…")
        ttk.Label(prog_frame, textvariable=download_file_var,
                  foreground="#7ec8f0", anchor="w").pack(fill="x")

        progress_bar = ttk.Progressbar(prog_frame, mode="indeterminate", length=480)
        progress_bar.pack(fill="x", pady=2)
        progress_bar.start(15)

        download_info_var = tk.StringVar(value="")
        ttk.Label(prog_frame, textvariable=download_info_var,
                  foreground="#c0c0c0", anchor="w", font=("Consolas", 9)).pack(fill="x")
        # ─────────────────────────────────────────────────────────────────── #

        from tkinter.scrolledtext import ScrolledText as _ST
        log_box = _ST(
            dlg, width=72, height=14, state="disabled",
            background="#0d0d1a", foreground="#90c890",
            font=("Consolas", 9),
        )
        log_box.pack(padx=12, pady=(6, 2), fill="both", expand=True)

        status_var = tk.StringVar(value="Starting download…")
        ttk.Label(dlg, textvariable=status_var, foreground="#7ec8f0").pack(padx=16, pady=4)

        _proc      = [None]
        _done      = [False]
        _cancelled = [False]

        btn = ttk.Button(dlg, text="Cancel")
        btn.pack(padx=16, pady=(4, 12))

        def _append(text):
            log_box.configure(state="normal")
            log_box.insert("end", text)
            log_box.see("end")
            log_box.configure(state="disabled")

        def _cancel():
            if _done[0]:
                # Install completed — just close, don't touch staged files
                dlg.destroy()
                return
            _cancelled[0] = True
            if _proc[0] and _proc[0].poll() is None:
                _proc[0].terminate()
            dlg.destroy()

        btn.configure(command=_cancel)

        # Diagnostic: note install start (diag may be None if no batch is running)
        _diag_ref = self._diag
        if _diag_ref:
            _diag_ref.log_gpu_install("started", gpu=getattr(self, "_gpu_eligible_name", "?"))

        def _run():
            import json          as _json
            import time          as _time
            import tempfile      as _tmp
            import ssl           as _ssl
            import urllib.error  as _ue
            import os            as _os
            import urllib.request as _ur
            import shutil        as _sh

            def _mb(b):     return f"{b / 1048576:.0f} MB"
            def _spd(bps):
                if bps >= 1048576: return f"{bps/1048576:.1f} MB/s"
                if bps >= 1024:    return f"{bps/1024:.0f} KB/s"
                return f"{bps:.0f} B/s"
            def _eta(s):
                if s >= 3600: return f"{int(s/3600)}h {int((s%3600)/60)}m"
                if s >= 60:   return f"{int(s/60)}m {int(s%60)}s"
                return f"{int(s)}s"

            # ── Phase 1: Resolve wheel URL ─────────────────────────────── #
            self.after(0, status_var.set,       "Step 1 of 4: Resolving package…")
            self.after(0, download_file_var.set,
                "Contacting PyTorch servers — this may take 30–90 s…")
            self.after(0, _append,
                "━━━  Step 1 — Resolve  ━━━\n"
                "Contacting PyTorch servers to find the correct wheel.\n"
                "This step may take 30–90 s before anything downloads — please wait.\n\n")

            fd, report_path = _tmp.mkstemp(suffix=".json")
            _os.close(fd)
            resolve_cmd = _resolve_cmd_base + [report_path, "--quiet"]

            try:
                _proc[0] = subprocess.Popen(
                    resolve_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                out_bytes, _ = _proc[0].communicate()
                rc = _proc[0].returncode
            except Exception as e:
                if _cancelled[0]: return
                self.after(0, _append, f"Error during resolve: {e}\n")
                self.after(0, status_var.set, "Installation failed.")
                self.after(0, progress_bar.stop)
                self.after(0, lambda: btn.configure(text="Close", command=dlg.destroy))
                if _diag_ref: _diag_ref.log_gpu_install("failed", reason=str(e)[:120])
                return

            if _cancelled[0]: return

            if rc != 0:
                msg = out_bytes.decode("utf-8", errors="replace") if out_bytes else ""
                self.after(0, _append, f"Resolve failed (exit {rc}):\n{msg}\n")
                self.after(0, status_var.set, "Installation failed — see log above.")
                self.after(0, progress_bar.stop)
                self.after(0, lambda: btn.configure(text="Close", command=dlg.destroy))
                if _diag_ref: _diag_ref.log_gpu_install("failed", returncode=rc)
                return

            wheel_url = None
            try:
                with open(report_path, "r") as f:
                    rpt = _json.load(f)
                for item in rpt.get("install", []):
                    if item.get("metadata", {}).get("name", "").lower() == "torch":
                        wheel_url = item.get("download_info", {}).get("url")
                        break
            except Exception as e:
                self.after(0, _append, f"Warning: could not parse pip report: {e}\n")
            finally:
                try: _os.unlink(report_path)
                except Exception: pass

            if not wheel_url:
                self.after(0, _append, "Could not determine wheel URL from pip report.\n")
                self.after(0, status_var.set, "Installation failed — could not resolve URL.")
                self.after(0, progress_bar.stop)
                self.after(0, lambda: btn.configure(text="Close", command=dlg.destroy))
                if _diag_ref: _diag_ref.log_gpu_install("failed", reason="no wheel url")
                return

            wheel_name = wheel_url.split("/")[-1].split("?")[0]
            self.after(0, _append, f"Resolved: {wheel_name}\n\n")

            # ── Phase 2: Download (with resume + auto-retry) ───────────── #
            self.after(0, status_var.set,       "Step 2 of 4: Downloading…")
            self.after(0, download_file_var.set, f"Downloading {wheel_name}")
            self.after(0, _append,
                "━━━  Step 2 — Download  ━━━\n"
                f"Downloading {wheel_name}…\n")

            def _set_det():
                progress_bar.stop()
                progress_bar.configure(mode="determinate", value=0)
            self.after(0, _set_det)

            dl_dir     = _pl.Path(_staging_dir).parent / "gpu_torch_download"
            dl_dir.mkdir(parents=True, exist_ok=True)
            wheel_path = dl_dir / wheel_name

            _MAX_RETRIES = 3
            _dl_done     = False

            for _attempt in range(1, _MAX_RETRIES + 1):
                # Resume from partial file if one exists
                resume_from = wheel_path.stat().st_size if wheel_path.exists() else 0
                if resume_from > 0:
                    self.after(0, _append,
                               f"Resuming from {_mb(resume_from)}"
                               f" (attempt {_attempt}/{_MAX_RETRIES})…\n")
                elif _attempt > 1:
                    self.after(0, _append,
                               f"Retrying download"
                               f" (attempt {_attempt}/{_MAX_RETRIES})…\n")

                try:
                    ssl_ctx = _ssl.create_default_context()
                    headers = {"User-Agent": "RelicBot/1.5"}
                    if resume_from > 0:
                        headers["Range"] = f"bytes={resume_from}-"

                    req = _ur.Request(wheel_url, headers=headers)
                    with _ur.urlopen(req, context=ssl_ctx) as resp:
                        # Determine total size (Content-Range if resuming, else Content-Length)
                        cr = resp.headers.get("Content-Range", "")
                        if cr and "/" in cr:
                            total = int(cr.split("/")[-1])
                        else:
                            cl = int(resp.headers.get("Content-Length", 0) or 0)
                            total = cl + resume_from

                        # Server ignored Range header (returned 200) — restart from scratch
                        if resume_from > 0 and resp.status == 200:
                            resume_from = 0
                            try: wheel_path.unlink(missing_ok=True)
                            except Exception: pass

                        got    = resume_from
                        t_last = _time.time()
                        b_last = got
                        chunk  = 65536

                        fmode = "ab" if resume_from > 0 else "wb"
                        with open(str(wheel_path), fmode) as fout:
                            while True:
                                if _cancelled[0]:
                                    break
                                data = resp.read(chunk)
                                if not data:
                                    break
                                fout.write(data)
                                got += len(data)

                                now = _time.time()
                                if now - t_last >= 0.5:
                                    dt    = now - t_last
                                    speed = (got - b_last) / dt if dt > 0 else 0
                                    t_last, b_last = now, got
                                    pct   = got / total * 100 if total else 0
                                    if speed > 0 and total > got:
                                        eta_str = _eta((total - got) / speed)
                                    else:
                                        eta_str = "–"
                                    if total:
                                        info = (f"{_mb(got)} / {_mb(total)}"
                                                f"  ·  {pct:.1f}%"
                                                f"  ·  {_spd(speed)}"
                                                f"  ·  ETA {eta_str}")
                                    else:
                                        info = f"{_mb(got)}  ·  {_spd(speed)}"

                                    def _upd(p=pct, i=info):
                                        progress_bar["value"] = p
                                        download_info_var.set(i)
                                    self.after(0, _upd)

                    _dl_done = True
                    break   # success — exit retry loop

                except Exception as e:
                    if _cancelled[0]:
                        try: wheel_path.unlink(missing_ok=True)
                        except Exception: pass
                        try: dl_dir.rmdir()
                        except Exception: pass
                        if _diag_ref: _diag_ref.log_gpu_install("cancelled")
                        return

                    _is_conn = isinstance(e, (
                        _ssl.SSLError, _ue.URLError,
                        ConnectionResetError, ConnectionRefusedError,
                        ConnectionAbortedError, TimeoutError, OSError,
                    ))

                    if _is_conn and _attempt < _MAX_RETRIES:
                        self.after(0, _append,
                                   f"\nConnection interrupted: {e}\n"
                                   f"Resuming automatically in 3 s…\n")
                        self.after(0, status_var.set,
                                   f"Interrupted — resuming ({_attempt}/{_MAX_RETRIES})…")
                        _time.sleep(3)
                        continue   # next attempt, partial file stays on disk

                    # Final failure
                    if _is_conn:
                        self.after(0, _append,
                                   f"\nDownload failed after {_attempt} attempt(s): {e}\n\n"
                                   "Unstable Connection — reconnect and try to download again.\n")
                        self.after(0, status_var.set, "Connection error.")
                        self.after(0, download_file_var.set,
                                   "Unstable Connection — reconnect and try to download again.")
                    else:
                        self.after(0, _append, f"\nDownload failed: {e}\n")
                        self.after(0, status_var.set, "Download failed.")
                    self.after(0, progress_bar.stop)
                    self.after(0, lambda: btn.configure(text="Close", command=dlg.destroy))
                    if _diag_ref:
                        _diag_ref.log_gpu_install("failed", reason=f"download: {str(e)[:120]}")
                    return

            dl_size = wheel_path.stat().st_size if wheel_path.exists() else 0
            self.after(0, lambda: progress_bar.configure(value=100))
            self.after(0, download_info_var.set,
                       f"Download complete — {_mb(dl_size)} received.")
            self.after(0, _append, f"Download complete: {_mb(dl_size)}\n\n")

            # ── Phase 3: Extract ───────────────────────────────────────── #
            self.after(0, status_var.set,        "Step 3 of 4: Extracting…")
            self.after(0, download_file_var.set, "Extracting PyTorch into staging area…")
            self.after(0, download_info_var.set, "")
            self.after(0, _append,
                "━━━  Step 3 — Extract  ━━━\n"
                "Installing from downloaded wheel (no network needed)…\n")

            def _set_indet():
                progress_bar.stop()
                progress_bar.configure(mode="indeterminate")
                progress_bar.start(15)
            self.after(0, _set_indet)

            _pl.Path(_staging_dir).mkdir(parents=True, exist_ok=True)
            extract_cmd = [
                sys.executable, "--run-pip", "install", str(wheel_path),
                "--no-index", "--no-deps",
                "--target", _staging_dir,
            ]
            try:
                _proc[0] = subprocess.Popen(
                    extract_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                out_bytes, _ = _proc[0].communicate()
                extract_rc   = _proc[0].returncode
                if out_bytes:
                    self.after(0, _append,
                               out_bytes.decode("utf-8", errors="replace"))
            except Exception as e:
                if _cancelled[0]: return
                self.after(0, _append, f"\nExtract error: {e}\n")
                self.after(0, status_var.set, "Extraction failed.")
                self.after(0, progress_bar.stop)
                self.after(0, lambda: btn.configure(text="Close", command=dlg.destroy))
                if _diag_ref:
                    _diag_ref.log_gpu_install("failed", reason=f"extract: {str(e)[:120]}")
                return
            finally:
                try: wheel_path.unlink(missing_ok=True)
                except Exception: pass
                try: dl_dir.rmdir()
                except Exception: pass

            if _cancelled[0]:
                if _diag_ref: _diag_ref.log_gpu_install("cancelled")
                return

            if extract_rc != 0:
                self.after(0, status_var.set, "Extraction failed — see log above.")
                self.after(0, progress_bar.stop)
                self.after(0, lambda: btn.configure(text="Close", command=dlg.destroy))
                if _diag_ref: _diag_ref.log_gpu_install("failed", returncode=extract_rc)
                _done[0] = True
                return

            self.after(0, progress_bar.stop)
            self.after(0, lambda: progress_bar.configure(mode="determinate", value=100))
            self.after(0, _append, "\nExtraction complete.\n\n")

            # ── Phase 4: Optimize ──────────────────────────────────────── #
            self.after(0, status_var.set,        "Step 4 of 4: Optimizing…")
            self.after(0, download_file_var.set, "Removing unused folders…")
            self.after(0, download_info_var.set, "")
            self.after(0, _append,
                "━━━  Step 4 — Optimize  ━━━\n"
                "Removing unused folders to reduce install size…\n")

            def _set_indet2():
                progress_bar.configure(mode="indeterminate", value=0)
                progress_bar.start(15)
            self.after(0, _set_indet2)

            staging_path = _pl.Path(_staging_dir)
            saved        = 0
            stripped_n   = 0

            _STRIP_DIRS = [
                ("torch/test",        "test suite — not needed at runtime"),
                ("torch/distributed", "distributed-training libs — not needed"),
            ]
            for rel_dir, desc in _STRIP_DIRS:
                p = staging_path / rel_dir
                if p.exists():
                    try:
                        sz = sum(f.stat().st_size
                                 for f in p.rglob("*") if f.is_file())
                        self.after(0, _append,
                            f"  Removing {rel_dir}/  ({_mb(sz)} — {desc})…\n")
                        _sh.rmtree(str(p))
                        saved += sz
                    except Exception as e:
                        self.after(0, _append,
                            f"  Warning: could not remove {rel_dir}/: {e}\n")

            self.after(0, _append, f"\nOptimize complete.  Freed ~{_mb(saved)} total.\n")
            self.after(0, progress_bar.stop)
            self.after(0, lambda: progress_bar.configure(mode="determinate", value=100))

            # Write flag — main.py swaps staged torch into _internal/ on next start
            try:
                (_exe_dir / "gpu_upgrade_ready").write_text("ready")
            except Exception as e:
                self.after(0, _append, f"Warning: could not write upgrade flag: {e}\n")

            _done[0] = True   # set BEFORE auto-close so _cancel() won't touch files
            self.after(0, lambda: self._gpu_install_btn.configure(
                text="Restart Required", state="disabled"))
            self.after(0, lambda: setattr(
                self._gpu_install_btn_tip, "_text",
                "GPU Acceleration staged.\nRestart RelicBot to activate it."))
            _gname = getattr(self, "_gpu_eligible_name", self._hw_gpu_name)
            self.after(0, lambda n=_gname: self._hw_gpu_rec_lbl.configure(
                text=f"Restart required to activate  ({n})",
                foreground="#e0c050"))
            if _diag_ref:
                _diag_ref.log_gpu_install(
                    "completed", saved_mb=int(saved / 1048576))

            def _finish():
                if dlg.winfo_exists():
                    dlg.destroy()
                tk.messagebox.showinfo(
                    "GPU Acceleration Ready",
                    "All files for GPU Acceleration downloaded successfully.\n\n"
                    "Restart RelicBot for the change to take effect.",
                )
            self.after(0, _finish)

        threading.Thread(target=_run, daemon=True).start()

    def _get_hw_recommendations(self) -> dict:
        """Return a dict of per-setting recommendations based on detected hardware.

        Keys: brute, workers_val, workers_display, async_, smart_throttle,
              exclude_buy_phase, gpu, lpm, backlog, intermittent,
              use_together, exclude_modes.
        Each setting value is a (rec_str, reason_str) tuple except workers_val (int).
        """
        ram      = self._hw_ram_gb
        cpus     = self._hw_cpu_cores
        has_cuda = getattr(self, "_hw_cuda_available", False)

        _unknown = ("?", "hardware not detected")
        if not ram or not cpus:
            return {k: _unknown for k in (
                "brute", "async_", "smart_throttle", "exclude_buy_phase",
                "gpu", "lpm", "backlog", "intermittent",
            )} | {"workers_val": 2, "workers_display": "?",
                  "use_together": "—", "exclude_modes": "—"}

        # ── Brute Force + Workers ──────────────────────────────────────── #
        if ram <= 8:
            brute        = ("OFF", "insufficient RAM for multiple OCR models")
            workers_val  = 1
            workers_disp = "N/A"
        elif has_cuda:
            # GPU mode: CUDA serializes above 4 workers — cap there, sweet spot is 2–3
            brute = ("ON", "2–3 workers recommended (GPU mode caps at 4)")
            if ram <= 12:
                workers_val  = 2
                workers_disp = "2"
            else:
                workers_val  = 3
                workers_disp = "2–3"
        elif ram <= 12:
            brute        = ("ON", "2 workers recommended")
            workers_val  = 2
            workers_disp = "2"
        elif ram <= 20:
            brute        = ("ON", "2–3 workers recommended")
            workers_val  = 2
            workers_disp = "2–3"
        elif ram <= 32:
            brute        = ("ON", "4–5 workers recommended")
            workers_val  = 4
            workers_disp = "4–5"
        else:
            brute        = ("ON", "6–8 workers recommended")
            workers_val  = 6
            workers_disp = "6–8"

        # ── Async Analysis ─────────────────────────────────────────────── #
        if cpus >= 8:
            async_ = ("ON", "enough cores to overlap analysis with game inputs")
        else:
            async_ = ("OFF", "low core count — use Backlog Analysis instead")

        # ── Smart Throttle ──────────────────────────────────────────────── #
        # Useful on any system where workers can starve inputs during buy phases
        if not has_cuda and cpus < 16:
            smart_throttle = ("ON", "adaptive throttle helps on mid-range CPU-only systems")
        else:
            smart_throttle = ("OFF", "high-end hardware — workers won't starve inputs")

        # ── Exclude Analysis While Operations Are Happening (Async sub) ── #
        if async_[0] == "ON" and not has_cuda:
            exclude_buy_phase = ("ON", "protects buy inputs on CPU-only systems")
        elif async_[0] == "ON" and has_cuda:
            exclude_buy_phase = ("OFF", "GPU fast enough — less benefit, more idle workers")
        else:
            exclude_buy_phase = ("OFF", "N/A — Async Analysis not recommended")

        # ── GPU Acceleration ──────────────────────────────────────────── #
        if has_cuda:
            gpu = ("ON", f"CUDA detected — {self._hw_gpu_name}")
        elif getattr(self, "_gpu_eligible", False):
            gpu = ("Install", f"compatible GPU found — use Install button ({self._gpu_eligible_name})")
        elif getattr(self, "_gpu_eligible_name", ""):
            gpu = ("OFF", self._gpu_eligible_reason or "see GPU status above")
        else:
            gpu = ("OFF", "no compatible NVIDIA GPU detected")

        # ── Low Performance Mode ───────────────────────────────────────── #
        if ram < 12 or cpus < 8:
            lpm = ("ON", "limited hardware — conservative timing prevents missed inputs")
        elif has_cuda:
            lpm = ("OFF", "GPU + adequate CPU/RAM — normal timing is fine")
        else:
            lpm = ("OFF", "adequate hardware — normal timing is fine")

        # ── Backlog Analysis ──────────────────────────────────────────── #
        # Recommended only when Async is not viable (low core count)
        if async_[0] == "OFF":
            backlog = ("ON", "zero CPU contention during game — analyze after run")
        else:
            backlog = ("OFF", "Async Analysis covers this — use that instead")

        # ── Intermittent Backlog (Backlog sub) ──────────────────────────── #
        if backlog[0] == "ON" and ram >= 12:
            intermittent = ("ON", "process every 5 iterations — incremental results")
        elif backlog[0] == "ON":
            intermittent = ("OFF", "low RAM — process everything at end of batch")
        else:
            intermittent = ("OFF", "N/A — Backlog Analysis not recommended")

        # ── Mode groupings ─────────────────────────────────────────────── #
        if has_cuda:
            use_together  = "Brute Force + Async Analysis + GPU Acceleration"
            exclude_modes = "Async ↔ Backlog Analysis  |  LPM ↔ Brute Force"
        elif async_[0] == "ON":
            use_together  = "Brute Force + Async Analysis (+ Smart Throttle on mid-range CPU)"
            exclude_modes = "Async ↔ Backlog Analysis  |  LPM ↔ Brute Force"
        else:
            use_together  = "Backlog Analysis + Low Performance Mode"
            exclude_modes = "Async ↔ Backlog Analysis (mutually exclusive)  |  LPM disables Brute Force"

        return {
            "brute":             brute,
            "workers_val":       workers_val,
            "workers_display":   workers_disp,
            "async_":            async_,
            "smart_throttle":    smart_throttle,
            "exclude_buy_phase": exclude_buy_phase,
            "gpu":               gpu,
            "lpm":               lpm,
            "backlog":           backlog,
            "intermittent":      intermittent,
            "use_together":      use_together,
            "exclude_modes":     exclude_modes,
        }

    def _apply_recommended_settings(self) -> None:
        """Apply all hardware-recommended settings in one click."""
        recs = self._get_hw_recommendations()

        brute_on = recs["brute"][0] == "ON"
        self._parallel_enabled_var.set(brute_on)
        if brute_on:
            self._parallel_workers_var.set(recs["workers_val"])

        async_on = recs["async_"][0] == "ON"
        self._async_enabled_var.set(async_on)
        self._smart_throttle_var.set(recs["smart_throttle"][0] == "ON")
        self._exclude_buy_phase_var.set(async_on and recs["exclude_buy_phase"][0] == "ON")

        backlog_on = recs["backlog"][0] == "ON"
        self._backlog_mode_var.set(backlog_on)
        self._intermittent_backlog_var.set(backlog_on and recs["intermittent"][0] == "ON")

        self._low_perf_mode_var.set(recs["lpm"][0] == "ON")

        # GPU: only enable if CUDA is actually working on this machine
        gpu_on = recs["gpu"][0] == "ON" and self._hw_cuda_available
        self._gpu_accel_var.set(gpu_on)

        # Trigger all cascading callbacks
        self._on_parallel_toggle()
        self._on_lpm_toggle()
        from bot import relic_analyzer as _ra
        _ra.set_gpu_mode(gpu_on)
        self._update_odds_viewer()

    # ── Calibration helpers ───────────────────────────────────────────── #

    def _log_calibration_status(self) -> None:
        """Log calibration state at startup so the user can see what was loaded."""
        _cal = self._load_calibration()
        if _cal.get("machine_id") == self._get_machine_id() and _cal.get("perf_mult"):
            _pm = _cal["perf_mult"]
            _bl = _cal.get("baseline_load_s", 0)
            _bl_str = f", baseline load {_bl:.1f}s" if _bl else ""
            self._log(
                f"[Calibration] Loaded — gap mult {_pm:.2f}×{_bl_str} "
                f"(machine fingerprint matched)")
        else:
            self._log(
                "[Calibration] No saved calibration for this machine — "
                "gap mult will auto-calibrate from the first iteration")

    def _get_machine_id(self) -> str:
        """Stable machine fingerprint: CPU core count + GPU name + RAM."""
        return (f"{os.cpu_count()}|"
                f"{getattr(self, '_hw_gpu_name', '')}|"
                f"{getattr(self, '_hw_ram_gb', 0)}")

    def _calibration_path(self):
        import pathlib as _pl
        if getattr(sys, "frozen", False):
            return _pl.Path(sys.executable).parent / "relicbot_calibration.json"
        return _pl.Path(__file__).parent.parent / "relicbot_calibration.json"

    # ── Timing data helpers ───────────────────────────────────────────── #

    def _timing_path(self):
        import pathlib as _pl
        if getattr(sys, "frozen", False):
            return _pl.Path(sys.executable).parent / "relicbot_timing.json"
        return _pl.Path(__file__).parent.parent / "relicbot_timing.json"

    def _load_timing_data(self) -> dict:
        """Return persisted timing dict, or a fresh empty structure."""
        try:
            import json as _json
            _p = self._timing_path()
            if _p.exists():
                _d = _json.loads(_p.read_text(encoding="utf-8"))
                if _d.get("version") == 1:
                    return _d
        except Exception:
            pass
        return {
            "version": 1,
            "machine_id": "",
            "game_inputs": {
                "lpm_off": {
                    "phase0": {"n": 0, "sum": 0.0},
                    "phase1": {"n": 0, "sum": 0.0},
                    "phase2": {"n": 0, "sum": 0.0},
                },
                "lpm_on": {
                    "phase0": {"n": 0, "sum": 0.0},
                    "phase1": {"n": 0, "sum": 0.0},
                    "phase2": {"n": 0, "sum": 0.0},
                },
            },
            "ocr": {
                "cpu": {"n": 0, "sum": 0.0},
                "gpu": {"n": 0, "sum": 0.0},
            },
        }

    def _save_timing_data(self) -> None:
        """Persist self._timing_data to disk (best-effort, non-blocking)."""
        try:
            import json as _json
            self._timing_data["machine_id"] = self._get_machine_id()
            self._timing_path().write_text(
                _json.dumps(self._timing_data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _record_timing_sample(
        self,
        lpm: bool,
        phase0_secs: float | None = None,
        phase1_per_relic: float | None = None,
        phase2_per_relic: float | None = None,
    ) -> None:
        """Add a single iteration's measured timings to the accumulator and persist."""
        _lpm_key = "lpm_on" if lpm else "lpm_off"
        with self._timing_data_lock:
            _gi = self._timing_data.setdefault("game_inputs", {}).setdefault(
                _lpm_key, {
                    "phase0": {"n": 0, "sum": 0.0},
                    "phase1": {"n": 0, "sum": 0.0},
                    "phase2": {"n": 0, "sum": 0.0},
                })
            # Sanity bounds: reject obvious outliers (game freeze, user alt-tab, etc.)
            if phase0_secs is not None and 5.0 < phase0_secs < 90.0:
                _gi["phase0"]["n"]   += 1
                _gi["phase0"]["sum"] += phase0_secs
            if phase1_per_relic is not None and 0.3 < phase1_per_relic < 15.0:
                _gi["phase1"]["n"]   += 1
                _gi["phase1"]["sum"] += phase1_per_relic
            if phase2_per_relic is not None and 0.02 < phase2_per_relic < 5.0:
                _gi["phase2"]["n"]   += 1
                _gi["phase2"]["sum"] += phase2_per_relic
            self._save_timing_data()

    def _record_ocr_timing(self, secs: float, gpu: bool) -> None:
        """Record a single OCR analysis duration (thread-safe)."""
        _key = "gpu" if gpu else "cpu"
        # Sanity bounds: reject sub-10ms (cache hit?) and >30s (freeze/timeout)
        if not (0.01 < secs < 30.0):
            return
        with self._timing_data_lock:
            _entry = self._timing_data.setdefault("ocr", {}).setdefault(
                _key, {"n": 0, "sum": 0.0})
            _entry["n"]   += 1
            _entry["sum"] += secs
            self._save_timing_data()

    def _load_calibration(self) -> dict:
        """Return persisted calibration dict, or {} if not found / unreadable."""
        try:
            import json as _json
            _p = self._calibration_path()
            if _p.exists():
                return _json.loads(_p.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_calibration(self, data: dict) -> None:
        """Merge *data* into the calibration file (non-blocking, best-effort)."""
        try:
            import json as _json
            _p = self._calibration_path()
            existing = {}
            if _p.exists():
                try:
                    existing = _json.loads(_p.read_text(encoding="utf-8"))
                except Exception:
                    pass
            existing.update(data)
            _p.write_text(_json.dumps(existing, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _calibrate_from_iteration(self) -> None:
        """Adjust _perf_gap_mult based on how the last iteration went.

        Called once after each iteration completes (success or failure).
        Increments the multiplier when Phase 0/1 needed retries or the safe
        buy path was forced; decrements slowly when everything ran clean.
        Changes of < 0.05 are ignored so the value stays stable on healthy runs.
        """
        # ── Per-iteration reliability log (always fires) ──────────────── #
        _failed_settle = self._iter_batches_settled  # settled batches
        _total_batches = self._iter_batches_settled + (
            1 if self._iter_p1_settle_retries > 0 and self._iter_batches_settled == 0 else 0)
        _avg_depth_str = (
            f"{self._iter_settle_poll_depth / self._iter_batches_settled:.1f}"
            if self._iter_batches_settled > 0 else "n/a"
        )
        _clean = (self._iter_p0_attempts <= 1
                  and self._iter_p1_settle_retries == 0
                  and not self._iter_safe_path_used)
        if not _clean:
            self._log(
                f"  [Reliability] p0_att={self._iter_p0_attempts}"
                f"  settle_retry={self._iter_p1_settle_retries}"
                f"  poll_depth={self._iter_settle_poll_depth}/{self._iter_batches_settled}b"
                f" (avg {_avg_depth_str})"
                f"  safe={'y' if self._iter_safe_path_used else 'n'}"
                f"  cpu={getattr(self, '_last_cpu_pct', 0):.0f}%"
            )

        # ── Accumulate into batch totals ─────────────────────────────── #
        self._batch_p0_extra        += max(0, self._iter_p0_attempts - 1)
        self._batch_settle_retries  += self._iter_p1_settle_retries
        if self._iter_safe_path_used:
            self._batch_safe_path_count += 1
        self._batch_total_poll_depth += self._iter_settle_poll_depth
        self._batch_total_settled    += self._iter_batches_settled

        # Build a stress score from per-iteration counters
        stress = 0.0
        if self._iter_p0_attempts > 1:
            # Each extra Phase 0 attempt beyond the first = significant distress
            stress += 0.20 * min(2, self._iter_p0_attempts - 1)
        if self._iter_p1_settle_retries > 0:
            # Settle check misses mean the preview screen took longer than expected
            stress += 0.15 * min(2, self._iter_p1_settle_retries)
        if self._iter_safe_path_used:
            # Bot judged the system too slow for the fast buy path
            stress += 0.10
        if self._iter_batches_settled > 0:
            # Average settle poll depth per batch. Poll 1 = instant confirm (healthy).
            # Average > 4 means the preview screen was consistently slow to appear.
            _avg_depth = self._iter_settle_poll_depth / self._iter_batches_settled
            if _avg_depth > 4.0:
                stress += 0.05 * min(4, int(_avg_depth - 4) // 2 + 1)
        if getattr(self, "_last_cpu_pct", 0) > 80:
            # High CPU during the iteration — future inputs may also be affected
            stress += 0.10

        old_mult = self._perf_gap_mult
        if stress >= 0.30:
            # Clear distress — widen input gaps
            bump = round(min(0.20, 0.05 + stress * 0.15), 2)
            new_mult = round(min(2.5, old_mult + bump), 3)
        elif stress == 0.0 and self._iter_p0_attempts <= 1:
            # Perfectly clean — nudge gaps tighter (slowly)
            new_mult = round(max(1.0, old_mult - 0.05), 3)
        else:
            return   # mild stress or incomplete data — hold position

        if abs(new_mult - old_mult) < 0.05:
            return

        self._perf_gap_mult = new_mult
        self._save_calibration({
            "machine_id":   self._get_machine_id(),
            "perf_mult":    new_mult,
            "last_updated": datetime.datetime.now().isoformat(),
        })
        direction = "↑" if new_mult > old_mult else "↓"
        self._log(
            f"  [Calibration] gap mult {direction} {old_mult:.2f}× → {new_mult:.2f}× "
            f"(p0={self._iter_p0_attempts}, "
            f"p1_retries={self._iter_p1_settle_retries}, "
            f"poll_depth={self._iter_settle_poll_depth}/{self._iter_batches_settled}b, "
            f"safe={'y' if self._iter_safe_path_used else 'n'}, "
            f"cpu={getattr(self, '_last_cpu_pct', 0):.0f}%)"
        )
        if hasattr(self, "_calib_status_lbl"):
            self.after(0, lambda m=new_mult, d=direction: self._calib_status_lbl.configure(
                text=f"Auto-calibration: gap mult {d} {m:.2f}×",
                foreground="#7ec8f0"))

    # ------------------------------------------------------------------ #
    #  ADAPTIVE BUY PATH
    # ------------------------------------------------------------------ #

    def _sample_cpu_pct(self) -> float:
        """
        Sample system-wide CPU usage since the last call.
        Uses GetSystemTimes (no psutil). Safe to call from any thread.
        Returns a float 0–100. Stores state between calls on self.
        """
        import ctypes
        class _FT(ctypes.Structure):
            _fields_ = [("lo", ctypes.c_ulong), ("hi", ctypes.c_ulong)]
        idle, kern, user = _FT(), _FT(), _FT()
        try:
            ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
        except Exception:
            return self._last_cpu_pct
        new_idle  = (idle.hi << 32) | idle.lo
        new_total = ((kern.hi << 32) | kern.lo) + ((user.hi << 32) | user.lo)
        d_idle  = new_idle  - self._cpu_idle_prev
        d_total = new_total - self._cpu_total_prev
        self._cpu_idle_prev  = new_idle
        self._cpu_total_prev = new_total
        if d_total > 0:
            self._last_cpu_pct = max(0.0, min(100.0, (1.0 - d_idle / d_total) * 100))
        return self._last_cpu_pct

    def _should_use_fast_buy_path(self) -> bool:
        """
        Returns True if system is healthy enough to use the fast buy sequence
        (F→DOWN→F→F, extra F skips the 2-second auto-transition).
        Falls back to safe path (F→DOWN→F + 2.5s settle) when stressed.
        Thresholds: perf_gap_mult ≤ 1.3 AND recent CPU < 70%.
        """
        if not self._phase1_alt_events:
            return True   # no alt sequence loaded — always use fast
        mult_ok = self._perf_gap_mult <= 1.3
        cpu_ok  = self._last_cpu_pct < 70.0
        return mult_ok and cpu_ok

    def _curse_filter_list(self, *_):
        q = self._curse_search_var.get().strip().lower()
        self._curse_src_lb.delete(0, "end")
        for p in self._curse_all_passives:
            if not q or q in p.lower():
                self._curse_src_lb.insert("end", p)

    def _curse_add(self):
        from bot.probability_engine import NUM_CURSES, MIN_UNBLOCKED_CURSES
        sel = self._curse_src_lb.curselection()
        if sel:
            item = self._curse_src_lb.get(sel[0])
            if item not in self._blocked_curses_list:
                if len(self._blocked_curses_list) >= NUM_CURSES - MIN_UNBLOCKED_CURSES:
                    self._curse_odds_lbl.configure(
                        text=f"Cannot block more curses — at least {MIN_UNBLOCKED_CURSES} must remain unblocked.",
                        foreground="#e05050",
                    )
                    return
                self._blocked_curses_list.append(item)
                self._blocked_curses_lb.insert("end", item)
                self._update_curse_odds()
                self._update_odds_viewer()

    def _curse_remove(self):
        sel = self._blocked_curses_lb.curselection()
        if sel:
            idx = sel[0]
            self._blocked_curses_list.pop(idx)
            self._blocked_curses_lb.delete(idx)
            self._update_curse_odds()
            self._update_odds_viewer()

    def _curse_clear(self):
        self._blocked_curses_list.clear()
        self._blocked_curses_lb.delete(0, "end")
        self._update_curse_odds()
        self._update_odds_viewer()

    def _update_curse_odds(self):
        """Refresh the curse odds impact label below the Curse Filter panel."""
        from bot.probability_engine import (
            prob_curse_pass, NUM_CURSES, MIN_UNBLOCKED_CURSES,
        )
        rtype = self.relic_type_var.get()
        n_blocked = len(self._blocked_curses_list)
        n_remaining = NUM_CURSES - n_blocked

        if rtype != "night":
            self._curse_odds_lbl.configure(
                text="Curse filter only applies to Deep of Night relics.",
                foreground=theme.TEXT_MUTED,
            )
            return

        if n_blocked == 0:
            self._curse_odds_lbl.configure(text="", foreground="")
            return

        if n_remaining < MIN_UNBLOCKED_CURSES:
            self._curse_odds_lbl.configure(
                text=f"Warning: only {n_remaining} curse(s) unblocked. At least {MIN_UNBLOCKED_CURSES} must remain.",
                foreground="#e05050",
            )
            return

        p_pass = prob_curse_pass(n_blocked, "night")
        pct = p_pass * 100
        n_in = int(round(1.0 / p_pass)) if p_pass > 0 else 0
        self._curse_odds_lbl.configure(
            text=(
                f"With {n_blocked} curse(s) blocked ({n_remaining} unblocked): "
                f"~{pct:.1f}% of Deep relics pass the curse filter "
                f"(~1 in {n_in:,} relics will have a blocked curse).  "
                f"Odds Viewer factors this in automatically."
            ),
            foreground=theme.TEXT_MUTED,
        )

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

    # ── Excluded passives helpers ──────────────────────────────────── #

    def _excl_filter_list(self, *_):
        q = self._excl_search_var.get().strip().lower()
        self._excl_src_lb.delete(0, "end")
        for p in self._excl_all_passives:
            if not q or q in p.lower():
                self._excl_src_lb.insert("end", p)

    def _excl_add(self):
        sel = self._excl_src_lb.curselection()
        if sel:
            item = self._excl_src_lb.get(sel[0])
            if item not in self._excluded_passives_list:
                self._excluded_passives_list.append(item)
                self._excluded_lb.insert("end", item)

    def _excl_remove(self):
        sel = self._excluded_lb.curselection()
        if sel:
            idx = sel[0]
            self._excluded_passives_list.pop(idx)
            self._excluded_lb.delete(idx)

    def _excl_clear(self):
        self._excluded_passives_list.clear()
        self._excluded_lb.delete(0, "end")

    def _excl_toggle_dormant(self):
        """Add or remove all Dormant Powers from the exclusion list."""
        from bot.passives import UI_CATEGORIES as _UCATS
        dormant = _UCATS.get("Dormant Powers", [])
        if self._excl_dormant_var.get():
            for d in dormant:
                if d and d not in self._excluded_passives_list:
                    self._excluded_passives_list.append(d)
                    self._excluded_lb.insert("end", d)
        else:
            to_remove = set(dormant)
            keep = [p for p in self._excluded_passives_list if p not in to_remove]
            self._excluded_passives_list.clear()
            self._excluded_lb.delete(0, "end")
            for p in keep:
                self._excluded_passives_list.append(p)
                self._excluded_lb.insert("end", p)

    def _get_excluded_passives(self) -> set:
        return set(self._excluded_passives_list)

    def _get_explicitly_included_passives(self) -> set:
        """All passives the user explicitly added to Pool, Pairings, or Build targets."""
        try:
            criteria = self.relic_builder.get_criteria_dict()
        except Exception:
            return set()
        included: set = set()

        def _from_exact(d):
            for t in d.get("targets", []):
                included.update(p for p in t.get("passives", []) if p)

        def _from_pool(d):
            for e in d.get("entries", []):
                included.update(e.get("accepted", []))
            for pair in d.get("pairings", []):
                included.update(pair.get("left", []))
                included.update(pair.get("right", []))

        mode = criteria.get("mode", "")
        if mode == "exact":
            _from_exact(criteria)
        elif mode == "pool":
            _from_pool(criteria)
        elif mode == "combine":
            _from_exact(criteria.get("exact", {}))
            _from_pool(criteria.get("pool", {}))
        return included

    def _is_passive_excluded(self, relic_result: dict,
                              excluded: set, explicitly_included: set) -> bool:
        """Return True if the relic carries an excluded passive not overridden by explicit inclusion."""
        if not excluded:
            return False
        relics = relic_result.get("relics_found", [])
        relic = relics[0] if relics else {}
        if not isinstance(relic, dict):
            return False
        for p in relic.get("passives", []):
            if p in excluded and p not in explicitly_included:
                return True
        return False

    def _get_excluded_passive_names(self, relic_result: dict,
                                    excluded: set, explicitly_included: set) -> list:
        """Return list of excluded passives present on relic (for summary labelling)."""
        relics = relic_result.get("relics_found", [])
        relic = relics[0] if relics else {}
        if not isinstance(relic, dict):
            return []
        return [p for p in relic.get("passives", [])
                if p in excluded and p not in explicitly_included]

    def _show_mouse_blocker(self):
        """Install a low-level mouse hook (WH_MOUSE_LL) that swallows mouse button
        click events during menu-navigation phases (Phase 0 – 4).  Mouse movement
        is unaffected.  The hook intercepts at the OS message-pump level, so it
        blocks clicks before any application (including the game) sees them.
        Runs on a dedicated daemon thread with its own GetMessage loop."""
        if self._mouse_blocker_thread and self._mouse_blocker_thread.is_alive():
            return  # already active
        try:
            import ctypes.wintypes as _wt
            import threading as _thr

            _WH_MOUSE_LL = 14
            # Mouse button messages to swallow (down + up for left/right/middle/X)
            _BLOCK_MSGS = {0x0201, 0x0202, 0x0204, 0x0205,
                           0x0207, 0x0208, 0x020B, 0x020C}
            _HookProc = ctypes.WINFUNCTYPE(
                ctypes.c_long, ctypes.c_int, _wt.WPARAM, _wt.LPARAM)

            def _hook_fn(nCode, wParam, lParam):
                if nCode >= 0 and wParam in _BLOCK_MSGS:
                    return 1   # swallow — game never sees this click
                return ctypes.windll.user32.CallNextHookEx(None, nCode, wParam, lParam)

            cb = _HookProc(_hook_fn)
            _tid_holder = [0]
            _ready = _thr.Event()

            def _pump():
                _tid_holder[0] = ctypes.windll.kernel32.GetCurrentThreadId()
                hook = ctypes.windll.user32.SetWindowsHookExW(
                    _WH_MOUSE_LL, cb, None, 0)
                self._mouse_blocker_hook = hook
                _ready.set()
                msg = _wt.MSG()
                while ctypes.windll.user32.GetMessageW(
                        ctypes.byref(msg), None, 0, 0) > 0:
                    pass
                if hook:
                    ctypes.windll.user32.UnhookWindowsHookEx(hook)
                    self._mouse_blocker_hook = None

            t = _thr.Thread(target=_pump, daemon=True, name="MouseBlockHook")
            t.start()
            _ready.wait(timeout=1.0)
            self._mouse_blocker_cb     = cb          # prevent GC while hook is live
            self._mouse_blocker_thread = t
            self._mouse_blocker_tid    = _tid_holder[0]
        except Exception:
            pass   # blocker is protective, not critical — never abort the bot

    def _hide_mouse_blocker(self):
        """Uninstall the low-level mouse hook (called after menu phases complete)."""
        tid = self._mouse_blocker_tid
        self._mouse_blocker_tid    = 0
        self._mouse_blocker_thread = None
        self._mouse_blocker_cb     = None
        if tid:
            # WM_QUIT (0x0012) causes GetMessage to return 0, ending the pump loop
            ctypes.windll.user32.PostThreadMessageW(tid, 0x0012, 0, 0)

    def _reset_controls(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.bot_running = False
        self._batch_log_path = ""        # stop mirroring to process log
        self._batch_relic_log_path = ""  # stop mirroring to relic log
        self._hide_mouse_blocker()
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None

    def _set_status(self, text: str, color: str = "gray"):
        def _apply():
            self.status_var.set(f"Status: {text}")
            self.status_label.config(foreground=color)
        self.after(0, _apply)

    def _log(self, message: str, overlay: bool = True):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        def _write():
            self.log_box.config(state="normal")
            self.log_box.insert("end", line)
            self.log_box.see("end")
            self.log_box.config(state="disabled")
            if overlay and self._overlay:
                self._overlay.append_log(line.rstrip())
        self.after(0, _write)
        if self._batch_log_path:
            try:
                with open(self._batch_log_path, "a", encoding="utf-8") as _f:
                    _f.write(line)
            except Exception:
                pass

    def _log_relic(self, message: str):
        """Log a relic analysis line: main UI box + overlay relic panel + live_log.txt."""
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        def _write():
            self.log_box.config(state="normal")
            self.log_box.insert("end", line)
            self.log_box.see("end")
            self.log_box.config(state="disabled")
            if self._overlay:
                self._overlay.append_relic_log(line.rstrip())
        self.after(0, _write)
        if self._batch_relic_log_path:
            try:
                with open(self._batch_relic_log_path, "a", encoding="utf-8") as _f:
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
        self._log_relic(f"  [{status}]  {name}")
        self._log_relic(f"    Passives: {passive_str}")
        if curses:
            self._log_relic(f"    Curses:   {', '.join(curses)}")
        if match and matched_passives:
            self._log_relic(f"    Matched:  {', '.join(matched_passives)}")
        elif not match:
            nms = result.get("near_misses", [])
            if nms:
                nm = max(nms, key=lambda x: x.get("matching_passive_count", 0))
                nm_p = nm.get("matching_passives", [])
                if nm_p:
                    self._log_relic(f"    Near miss: {', '.join(nm_p)}")
