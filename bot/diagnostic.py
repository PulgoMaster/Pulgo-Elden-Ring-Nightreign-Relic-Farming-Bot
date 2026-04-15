"""
RelicBot Diagnostic Logger — input-test build only.

Collects and writes a structured .diag file alongside each batch run covering:
  - Full hardware profile (OS, CPU, RAM, GPU, CUDA, display)
  - Bot settings snapshot at run start (so we can correlate failures with
    non-recommended settings)
  - Per-iteration timing with phase breakdown and session-age column
    (lets you spot reliability degradation correlated with uptime)
  - Per-key SendInput results (press + release, scan code, Windows return value)
  - play() sequence result summaries (sent vs expected)
  - OCR call results with timing (check type, True/False/ERROR, duration)
  - GPU Acceleration install events (start, progress, success/fail, DLL strip)
  - User-interference detection via OS-level low-level keyboard + mouse hooks.
    The LLKHF_INJECTED / LLMHF_INJECTED flag distinguishes real hardware input
    from synthetic SendInput events — any non-injected event while the bot is
    running is logged as user interference with timestamp and key/button.
  - Session summary at close (aggregate input reliability %, OCR error rate,
    interference event count, per-iteration time variance)

Usage (from app.py):
    from bot.diagnostic import DiagnosticLogger

    diag = DiagnosticLogger(run_dir)
    diag.log_hardware()
    diag.log_settings(app_instance)
    diag.start_interference_monitor()

    diag.iteration_start(n)
    diag.phase_start("Phase 0")
    ...
    diag.phase_end("Phase 0", sent=5, expected=5)
    diag.iteration_end(n, outcome="ok")

    diag.close()          # stops monitor, writes summary
"""

import ctypes
import ctypes.wintypes as _wt
import datetime
import os
import platform
import subprocess
import sys
import threading
import time

from bot.failure_classifier import (
    classify, FailureAggregator,
    SYSTEM, INPUT, OCR, STATE, USER,
    INFO, WARN, ERROR, FATAL,
)


# Verbosity levels for the spammy per-event loggers (slot OCR, door checks,
# match cutoff misses, advance results).  "low" suppresses all of them,
# "normal" suppresses only the most spammy (per-token), "high" logs
# everything.  Other event categories are always on regardless of level.
VERBOSITY_LOW    = "low"
VERBOSITY_NORMAL = "normal"
VERBOSITY_HIGH   = "high"
_VERBOSITY_RANK  = {VERBOSITY_LOW: 0, VERBOSITY_NORMAL: 1, VERBOSITY_HIGH: 2}


# ─────────────────────────────────────────────────────────────────────────── #
# Persistent last-run snapshot
# ─────────────────────────────────────────────────────────────────────────── #
# Saved next to the bot exe (or src dir in dev) as last_run_diag.json so the
# Export Diagnostics button can render the previous run's counters and
# failure breakdown even after the user closed and reopened the bot.
# Cleared only when a NEW batch run starts.

def _persist_path() -> str:
    """Return the absolute path of the persistent last-run snapshot file.

    Lives next to the executable (frozen) or in the project root (dev).
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        # bot/diagnostic.py → project root
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "last_run_diag.json")


def persist_run_state(counters: dict, failures: dict,
                      runtime: dict | None = None) -> None:
    """Write a JSON snapshot of the last run's diagnostic state.

    Called by DiagnosticLogger on iteration_end and close so the snapshot
    is always at most one iteration stale, and survives across app
    restarts until the next batch run wipes it.
    """
    import json
    payload = {
        "counters":    counters or {},
        "failures":    failures or {},
        "runtime":     runtime or {},
        "finished_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        with open(_persist_path(), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass   # never let persistence break the run


def load_persisted_run_state() -> dict | None:
    """Load the persisted last-run snapshot, or None if missing/corrupt."""
    import json
    p = _persist_path()
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def clear_persisted_run_state() -> None:
    """Delete the persisted snapshot.  Called when a NEW batch run starts."""
    p = _persist_path()
    try:
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────── #


class DiagnosticLogger:
    """Thread-safe diagnostic file logger for the input-test build."""

    # ── construction ──────────────────────────────────────────────────────── #

    def __init__(self, run_dir: str):
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self._path = os.path.join(run_dir, f"diagnostic_{ts}.diag")
        self._lock = threading.Lock()
        self._session_start = time.time()

        # Per-iteration tracking
        self._iter_starts: dict = {}        # iter_num → perf_counter
        self._iter_stats:  dict = {}        # iter_num → {input_ok, input_fail, ocr_*}
        self._all_iter_times: list = []     # completed iteration durations (s)

        # Phase tracking
        self._phase_starts: dict = {}       # name → perf_counter

        # Input aggregate stats
        self._inp = {"press_total": 0, "press_ok": 0, "press_fail": 0}

        # OCR aggregate stats
        self._ocr = {"total": 0, "true": 0, "false": 0, "error": 0,
                     "total_time": 0.0}

        # User interference tracking
        self._user_events: list = []        # (ts_float, description)

        # Interference hook thread
        self._hook_stop = threading.Event()
        self._hook_thread: threading.Thread | None = None
        self._hook_thread_id = 0

        # GPU install tracking
        self._gpu_install_started = False
        self._gpu_install_ok = False

        # Optional runtime-snapshot provider — caller (app.py) sets this
        # so persist_run_state() can capture live app state alongside the
        # counters and failure aggregator.  Signature: callable() -> dict.
        self._runtime_snapshot_fn = None

        # ── v1.7.x feature counters & state ───────────────────────────── #
        # Verbosity knob (caller can set via .verbosity = "high" before run)
        self.verbosity = VERBOSITY_NORMAL

        # Failure classification
        self._failures = FailureAggregator(recent_cap=50)

        # Aggregate counters for new event types
        self._ev = {
            # Settle / Phase 1
            "settle_total":         0,
            "settle_empty_slot0":   0,
            "settle_right_skipped": 0,
            "settle_accepted":      0,
            "settle_fallthrough":   0,
            "settle_murk_recheck":  0,
            "buy_fail_in_place":    0,

            # Phase 1 buy-quantity verification (X/N OCR)
            "buy_qty_verified":      0,
            "buy_qty_corrected_q":   0,
            "buy_qty_corrected_esc": 0,
            "buy_qty_unrecoverable": 0,
            "buy_qty_ocr_fail":      0,
            "buy_qty_drift_detected": 0,
            "buy_qty_fallback_murk": 0,

            # Phase 2 / advance
            "advance_total":        0,
            "advance_dup_accepted": 0,
            "advance_drop":         0,
            "p2_wraparound_skip":   0,   # cur capture matched an EARLIER (not immediate) slot
            "p2_endwrap_clamp":     0,   # end-of-list wrap detected; batch_size clamped down
            "p2_input_drop_skip":   0,   # cur capture matched the IMMEDIATELY previous slot
            "p2_recovery_attempts": 0,   # extra RIGHT presses beyond batch_size used to find missed relics
            "p2_recovery_success":  0,   # cycles where recovery found all batch_size unique
            "p2_relics_lost":       0,   # relics permanently lost (cycle ended without finding all)
            "p2_cycles_short":      0,   # cycles that ended with confirmed < batch_size

            # Phase 3
            "p3_tooltip_retry_ok":   0,
            "p3_tooltip_retry_fail": 0,
            "p3_esc_timeout":        0,
            "p3_consecutive_fails":  0,
            "p3_iter_restart":       0,

            # Phase -0.5 / load
            "black_frame_extends":  0,
            "black_frame_ceiling":  0,

            # MenuNav
            "menunav_recalcs":       0,
            "menunav_doubling_hits": 0,
            "menunav_budget_busted": 0,

            # GPU AA
            "gpu_aa_suppressions":   0,
            "gpu_aa_re_enables":     0,
            "gpu_aa_final_latches":  0,

            # Input GPU yield
            "input_yield_calls":     0,
            "input_yield_wait_ms":   0.0,
            "input_yield_max_ms":    0.0,

            # Nav worker
            "nav_worker_starts":     0,
            "nav_worker_timeouts":   0,
            "nav_worker_deaths":     0,
            "nav_worker_restarts":   0,
            "nav_worker_inline_fb":  0,

            # Async / backlog
            "async_submits":         0,
            "async_completes":       0,
            "async_errors":          0,
            "async_hits":            0,
            "backlog_flushes":       0,

            # OCR pipeline detail
            "slot_ocr_calls":        0,
            "slot_ocr_passive_hits": 0,
            "slot_ocr_curse_hits":   0,
            "curse_misses":          0,

            # Door / match
            "door_gen_calls":        0,
            "door_total_generated":  0,
            "compat_rejects":        0,
            "duplicate_skips":       0,

            # Game state
            "game_launches":         0,
            "game_launch_fails":     0,
            "save_restores":         0,
            "perf_recalibrations":   0,
        }

        # Open file, write header
        with open(self._path, "w", encoding="utf-8") as f:
            f.write(f"RelicBot Diagnostic Log\n")
            f.write(f"Generated : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Build     : input-test (ctypes SendInput + scan codes)\n")
            f.write("=" * 72 + "\n\n")

    # ── internal write helpers ────────────────────────────────────────────── #

    def _ts(self) -> str:
        return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def _write(self, line: str):
        """Append a timestamped line. Thread-safe."""
        entry = f"[{self._ts()}] {line}\n"
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(entry)

    def _write_block(self, text: str):
        """Append a raw block (no timestamp prefix). Thread-safe."""
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(text + "\n")

    # ── hardware profile ──────────────────────────────────────────────────── #

    def log_hardware(self):
        """Write full hardware and environment profile at session start."""
        lines = ["=== HARDWARE PROFILE ==="]

        # OS / CPU
        u = platform.uname()
        lines.append(f"OS         : {u.system} {u.release} build {u.version}")
        lines.append(f"CPU        : {u.processor or u.machine}")
        lines.append(f"CPU cores  : {os.cpu_count()} logical")

        # RAM (via GlobalMemoryStatusEx — no psutil dependency)
        try:
            class _MEMSTATUS(ctypes.Structure):
                _fields_ = [
                    ("dwLength",                ctypes.c_ulong),
                    ("dwMemoryLoad",            ctypes.c_ulong),
                    ("ullTotalPhys",            ctypes.c_ulonglong),
                    ("ullAvailPhys",            ctypes.c_ulonglong),
                    ("ullTotalPageFile",        ctypes.c_ulonglong),
                    ("ullAvailPageFile",        ctypes.c_ulonglong),
                    ("ullTotalVirtual",         ctypes.c_ulonglong),
                    ("ullAvailVirtual",         ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            ms = _MEMSTATUS()
            ms.dwLength = ctypes.sizeof(_MEMSTATUS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            total = ms.ullTotalPhys / (1024 ** 3)
            avail = ms.ullAvailPhys / (1024 ** 3)
            lines.append(f"RAM        : {total:.1f} GB total  /  {avail:.1f} GB available")
        except Exception as e:
            lines.append(f"RAM        : (unavailable: {e})")

        # GPU + CUDA via nvidia-smi
        try:
            r = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=name,driver_version,compute_cap,memory.total,memory.free",
                 "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                for gpu_line in r.stdout.strip().splitlines():
                    parts = [p.strip() for p in gpu_line.split(",")]
                    if len(parts) >= 5:
                        lines.append(f"GPU        : {parts[0]}")
                        lines.append(f"GPU driver : {parts[1]}")
                        lines.append(f"Compute cap: {parts[2]}")
                        lines.append(f"VRAM       : {parts[3]}  (free: {parts[4]})")
            else:
                lines.append("GPU        : (nvidia-smi unavailable — no NVIDIA GPU or driver)")
        except Exception as e:
            lines.append(f"GPU        : (nvidia-smi error: {e})")

        # PyTorch / CUDA / EasyOCR device
        try:
            import torch
            lines.append(f"Torch      : {torch.__version__}")
            if torch.cuda.is_available():
                dev = torch.cuda.get_device_name(0)
                lines.append(f"CUDA       : available — {dev}")
                lines.append(f"OCR device : cuda")
            else:
                lines.append("CUDA       : not available — CPU mode")
                lines.append("OCR device : cpu")
        except ImportError:
            lines.append("Torch      : not imported")
        except Exception as e:
            lines.append(f"Torch      : import error — {e}")

        # Display resolution
        try:
            w = ctypes.windll.user32.GetSystemMetrics(0)   # SM_CXSCREEN
            h = ctypes.windll.user32.GetSystemMetrics(1)   # SM_CYSCREEN
            lines.append(f"Display    : {w} × {h}")
        except Exception:
            pass

        # Python / runtime
        lines.append(f"Python     : {sys.version.split()[0]}")
        lines.append(f"Frozen     : {getattr(sys, 'frozen', False)}")
        lines.append(f"Input API  : ctypes SendInput  (KEYEVENTF_SCANCODE)")
        lines.append("")

        self._write_block("\n".join(lines))

    # ── bot settings snapshot ─────────────────────────────────────────────── #

    def log_settings(self, app):
        """
        Capture bot settings from the running app instance.
        Call this at the start of each batch run (after hardware is logged).
        """
        lines = ["=== BOT SETTINGS (at run start) ==="]

        def _get(var_name, default="?"):
            try:
                v = getattr(app, var_name, None)
                return v.get() if v is not None else default
            except Exception:
                return default

        # Relic type & mode
        lines.append(f"Relic type     : {_get('relic_type_var')}")

        # Phase configuration
        for i, name in [(0, "Phase 0 (shop nav)"),
                        (1, "Phase 1 (buy)"),
                        (2, "Phase 2 (scan)"),
                        (3, "Phase 3 (reset)")]:
            try:
                configured = bool(app.phase_events[i])
                lines.append(f"{name:20s}: {'configured' if configured else 'NOT configured'}")
            except Exception:
                lines.append(f"{name:20s}: ?")

        # GPU / CUDA
        cuda_ok  = getattr(app, "_hw_cuda_available", False)
        cuda_err = getattr(app, "_hw_cuda_error", "")
        lines.append(f"GPU accel      : {'ACTIVE (CUDA)' if cuda_ok else ('disabled — ' + cuda_err[:60] if cuda_err else 'disabled (CPU only)')}")

        # Key timing / performance settings
        perf_mult = getattr(app, "_perf_gap_mult", "?")
        lines.append(f"Perf gap mult  : {perf_mult}  (input gap scaling; 1.0 = baseline)")
        lines.append(f"Async analysis : {_get('_async_enabled_var', '?')}")
        lines.append(f"Smart Throttle : {_get('_smart_throttle_var', '?')}")
        lines.append(f"Excl. Analysis : {_get('_exclude_buy_phase_var', '?')}")
        lines.append(f"Smart Analyze  : {_get('_smart_analyze_var', '?')}")
        lines.append(f"Backlog mode   : {_get('_backlog_mode_var', '?')}")
        lines.append(f"Intermittent   : {_get('_intermittent_backlog_var', '?')} every {_get('_intermittent_every_n_var', '?')} batch(es)")
        lines.append(f"Brute force    : {_get('_parallel_enabled_var', '?')}")
        lines.append(f"Parallel workers: {_get('_parallel_workers_var', '?')}")
        lines.append(f"Low Perf Mode  : {_get('_low_perf_mode_var', '?')}")

        # OCR region
        try:
            region = app._get_region()
            lines.append(f"OCR region     : {region}")
        except Exception:
            lines.append("OCR region     : ?")

        # Hardware recommendations vs actual (brute, workers, async, lpm, gpu)
        try:
            recs = app._get_hw_recommendations()
            lines.append(f"HW rec GPU     : {recs[4]}")
            lines.append(f"HW rec async   : {recs[2]}")
            lines.append(f"HW rec brute   : {recs[0]}")
        except Exception:
            pass

        lines.append("")
        self._write_block("\n".join(lines))

    # ── iteration timing ──────────────────────────────────────────────────── #

    def iteration_start(self, n: int):
        self._iter_starts[n] = time.perf_counter()
        self._iter_stats[n] = {"inp_ok": 0, "inp_fail": 0,
                                "ocr_true": 0, "ocr_false": 0, "ocr_err": 0}
        age = time.time() - self._session_start
        self._write(f"=== BATCH {n} START  (session age: {age:.0f}s / {age/60:.1f}min) ===")

    def iteration_end(self, n: int, outcome: str = "ok"):
        t0 = self._iter_starts.pop(n, None)
        elapsed = (time.perf_counter() - t0) if t0 else 0.0
        self._all_iter_times.append(elapsed)
        s = self._iter_stats.pop(n, {})
        self._write(
            f"=== BATCH {n} END  "
            f"{elapsed:.2f}s  outcome={outcome}  "
            f"inputs ok/fail={s.get('inp_ok',0)}/{s.get('inp_fail',0)}  "
            f"ocr T/F/E={s.get('ocr_true',0)}/{s.get('ocr_false',0)}/{s.get('ocr_err',0)} ===\n"
        )
        # Persist a snapshot at every iteration boundary so the
        # last_run_diag.json file is at most one iteration stale.
        try:
            _rt = self._runtime_snapshot_fn() if self._runtime_snapshot_fn else {}
        except Exception:
            _rt = {}
        try:
            persist_run_state(self._ev, self._failures.snapshot(), _rt)
        except Exception:
            pass

    # ── phase timing ──────────────────────────────────────────────────────── #

    def phase_start(self, name: str, detail: str = ""):
        self._phase_starts[name] = time.perf_counter()
        self._write(f"  [{name}] start{('  ' + detail) if detail else ''}")

    def phase_end(self, name: str, **kwargs):
        t0 = self._phase_starts.pop(name, None)
        elapsed = (time.perf_counter() - t0) if t0 else 0.0
        kv = "  ".join(f"{k}={v}" for k, v in kwargs.items())
        self._write(f"  [{name}] end  {elapsed:.3f}s  {kv}")

    # ── input event logging ───────────────────────────────────────────────── #

    def log_input(self, current_iter: int, key: str, event_type: str,
                  scan: int = 0, ok: bool = True, extended: bool = False):
        """
        Log one SendInput keyboard event from the bot.
        event_type: "press" or "release"
        ok: True if SendInput returned 1 (event accepted by Windows).
        """
        scan_str = f"0x{scan:02X}{'|EXT' if extended else ''}" if scan else "?"
        status = "OK  " if ok else "FAIL"
        self._write(
            f"  INPUT  BOT  {event_type:7s}  {key:22s}  scan={scan_str}  {status}"
        )
        if event_type == "press":
            self._inp["press_total"] += 1
            if ok:
                self._inp["press_ok"] += 1
                s = self._iter_stats.get(current_iter)
                if s is not None:
                    s["inp_ok"] += 1
            else:
                self._inp["press_fail"] += 1
                s = self._iter_stats.get(current_iter)
                if s is not None:
                    s["inp_fail"] += 1

    def log_input_sequence(self, label: str, sent: int, expected: int,
                           sent_keys: list, expected_keys: list):
        """Log the aggregate result of a play() call."""
        ok = (sent == expected and sent_keys == expected_keys)
        status = "OK" if ok else "MISMATCH"
        missing = [k for k in expected_keys if k not in sent_keys] if not ok else []
        self._write(
            f"  SEQ  {label:20s}  sent={sent}/{expected}  {status}"
            + (f"  missing={missing}" if missing else "")
        )

    # ── OCR event logging ─────────────────────────────────────────────────── #

    def log_ocr(self, current_iter: int, check: str, result,
                duration: float, error: str = ""):
        """Log one OCR check result."""
        self._ocr["total"] += 1
        self._ocr["total_time"] += duration
        s = self._iter_stats.get(current_iter, {})

        if error:
            self._ocr["error"] += 1
            s["ocr_err"] = s.get("ocr_err", 0) + 1
            self._write(
                f"  OCR   {check:28s}  ERROR  ({duration:.3f}s)  {error[:80]}")
        elif result:
            self._ocr["true"] += 1
            s["ocr_true"] = s.get("ocr_true", 0) + 1
            self._write(
                f"  OCR   {check:28s}  TRUE   ({duration:.3f}s)")
        else:
            self._ocr["false"] += 1
            s["ocr_false"] = s.get("ocr_false", 0) + 1
            self._write(
                f"  OCR   {check:28s}  false  ({duration:.3f}s)")

    def log_ocr_dump(self, current_iter: int, step_i: int, tokens: list):
        """
        Write a full raw-OCR token dump for one relic to the .diag file.

        Each token is a dict: {text, conf, y, status, reason, matched}
        Status values:
          PASSIVE    — matched to known passive (matched = canonical name)
          CURSE      — matched to known curse   (matched = canonical name)
          RELIC_NAME — taken as the relic name
          NO_MATCH   — passed confidence but matched nothing
          DROPPED    — filtered before matching (conf<0.35 or too short)
        """
        if not tokens:
            return
        import datetime as _dt
        _ts = _dt.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        lines = [
            f"",
            f"  OCR_DUMP  batch={current_iter:03d}  relic={step_i + 1:03d}  [{_ts}]"
            f"  ({len(tokens)} tokens)",
        ]
        for t in tokens:
            status = t.get("status", "?")
            conf   = t.get("conf", 0.0)
            y      = t.get("y", -1)
            raw    = (t.get("text") or "")[:60]
            matched = t.get("matched")
            reason  = t.get("reason", "")
            tag = {
                "PASSIVE":    "PASS ",
                "CURSE":      "CURSE",
                "RELIC_NAME": "NAME ",
                "NO_MATCH":   "MISS ",
                "DROPPED":    "DROP ",
            }.get(status, status[:5].ljust(5))
            if status == "DROPPED":
                lines.append(f"    [{tag} {conf:.2f} y={y:4d}] {raw!r:<50}  ← {reason}")
            elif matched and matched != raw:
                lines.append(f"    [{tag} {conf:.2f} y={y:4d}] {raw!r:<50}  → {matched!r}")
            else:
                lines.append(f"    [{tag} {conf:.2f} y={y:4d}] {raw!r}")
        self._write("\n".join(lines))
        # Update OCR drop counter for summary stats
        dropped = sum(1 for t in tokens if t.get("status") == "DROPPED")
        self._ocr.setdefault("dropped", 0)
        self._ocr["dropped"] += dropped

    # ── GPU install event logging ──────────────────────────────────────────── #

    def log_gpu_install(self, event: str, **kwargs):
        """
        Log a GPU Acceleration install lifecycle event.
        event examples: "started", "pip_done", "dll_strip", "completed", "failed", "cancelled"
        """
        kv = "  ".join(f"{k}={v}" for k, v in kwargs.items())
        self._write(f"  GPU_INSTALL  {event:12s}  {kv}")
        if event == "started":
            self._gpu_install_started = True
        elif event == "completed":
            self._gpu_install_ok = True

    # ── user interference monitor ─────────────────────────────────────────── #

    def start_interference_monitor(self):
        """
        Install OS-level WH_KEYBOARD_LL and WH_MOUSE_LL hooks in a background
        thread.  Events with LLKHF_INJECTED / LLMHF_INJECTED bit CLEAR are real
        hardware events — logged as USER INTERFERENCE with timestamp.
        SendInput events (bot inputs) always have the injected bit SET and are
        silently skipped by the hook.
        """
        if self._hook_thread and self._hook_thread.is_alive():
            return
        self._hook_stop.clear()
        self._hook_thread = threading.Thread(
            target=self._hook_loop, daemon=True, name="DiagHookThread")
        self._hook_thread.start()
        self._write("  [MONITOR] User-interference monitor started.")

    def stop_interference_monitor(self):
        """Stop the hook thread cleanly."""
        self._hook_stop.set()
        if self._hook_thread_id:
            # WM_QUIT = 0x0012: wake the hook thread's message loop
            ctypes.windll.user32.PostThreadMessageW(self._hook_thread_id, 0x0012, 0, 0)
        if self._hook_thread:
            self._hook_thread.join(timeout=3.0)
            self._hook_thread = None
        self._hook_thread_id = 0

    def _hook_loop(self):
        """Background thread: install hooks and pump messages."""
        WH_KEYBOARD_LL = 13
        WH_MOUSE_LL    = 14
        WM_KEYDOWN     = 0x0100
        WM_SYSKEYDOWN  = 0x0104
        WM_LBUTTONDOWN = 0x0201
        WM_RBUTTONDOWN = 0x0204
        LLKHF_INJECTED = 0x10   # keyboard hook: bit 4 set = synthetic
        LLMHF_INJECTED = 0x01   # mouse hook:    bit 0 set = synthetic

        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("vkCode",      _wt.DWORD),
                ("scanCode",    _wt.DWORD),
                ("flags",       _wt.DWORD),
                ("time",        _wt.DWORD),
                ("dwExtraInfo", ctypes.c_size_t),
            ]

        class MSLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("pt",          _wt.POINT),
                ("mouseData",   _wt.DWORD),
                ("flags",       _wt.DWORD),
                ("time",        _wt.DWORD),
                ("dwExtraInfo", ctypes.c_size_t),
            ]

        HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int,
                                       _wt.WPARAM, _wt.LPARAM)

        def _kb_proc(nCode, wParam, lParam):
            if nCode >= 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if not (kb.flags & LLKHF_INJECTED):
                    # Real hardware keystroke while bot is active
                    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    entry = (f"[{ts}]   INTERFERENCE  USER_KEY    "
                             f"VK=0x{kb.vkCode:02X}  scan=0x{kb.scanCode:02X}\n")
                    self._user_events.append((time.time(), f"KEY VK=0x{kb.vkCode:02X}"))
                    with self._lock:
                        with open(self._path, "a", encoding="utf-8") as f:
                            f.write(entry)
            return ctypes.windll.user32.CallNextHookEx(None, nCode, wParam, lParam)

        def _ms_proc(nCode, wParam, lParam):
            if nCode >= 0 and wParam in (WM_LBUTTONDOWN, WM_RBUTTONDOWN):
                ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                if not (ms.flags & LLMHF_INJECTED):
                    btn = "LEFT" if wParam == WM_LBUTTONDOWN else "RIGHT"
                    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    entry = (f"[{ts}]   INTERFERENCE  USER_MOUSE  "
                             f"{btn}  x={ms.pt.x} y={ms.pt.y}\n")
                    self._user_events.append(
                        (time.time(), f"MOUSE_{btn} x={ms.pt.x} y={ms.pt.y}"))
                    with self._lock:
                        with open(self._path, "a", encoding="utf-8") as f:
                            f.write(entry)
            return ctypes.windll.user32.CallNextHookEx(None, nCode, wParam, lParam)

        _kb_cb = HOOKPROC(_kb_proc)
        _ms_cb = HOOKPROC(_ms_proc)

        self._hook_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        kb_hook = ctypes.windll.user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, _kb_cb, None, 0)
        ms_hook = ctypes.windll.user32.SetWindowsHookExW(
            WH_MOUSE_LL, _ms_cb, None, 0)

        # Message pump: low-level hooks require the installing thread to pump
        # messages.  PeekMessage with PM_REMOVE processes hook callbacks.
        msg = _wt.MSG()
        PM_REMOVE = 1
        while not self._hook_stop.is_set():
            if ctypes.windll.user32.PeekMessageW(
                    ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                if msg.message == 0x0012:   # WM_QUIT
                    break
                ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(0.005)

        if kb_hook:
            ctypes.windll.user32.UnhookWindowsHookEx(kb_hook)
        if ms_hook:
            ctypes.windll.user32.UnhookWindowsHookEx(ms_hook)

    # ── verbosity gate ────────────────────────────────────────────────────── #

    def _verb_at_least(self, level: str) -> bool:
        return _VERBOSITY_RANK.get(self.verbosity, 1) >= _VERBOSITY_RANK.get(level, 1)

    # ── failure classification ────────────────────────────────────────────── #

    def log_failure(self, category: str, subcategory: str,
                    evidence: dict | None = None,
                    severity: str = WARN) -> None:
        """Classify a failure event and append to .diag.

        Use this whenever a recovery path triggers, an OCR call returns
        unusable data, an input fails to land, or the game state diverges
        from what we expected.  See bot/failure_classifier.py for category
        and severity definitions.
        """
        rec = classify(category, subcategory, evidence, severity)
        self._failures.add(rec)
        ev_str = "  ".join(f"{k}={v}" for k, v in rec["evidence"].items())
        self._write(
            f"  FAILURE  {rec['severity']:5s}  "
            f"{rec['category']}/{rec['subcategory']:32s}  {ev_str}"
        )

    # ── settle / Phase 1 events ──────────────────────────────────────────── #

    def log_settle(self, slot: int, outcome: str, duration_s: float = 0.0,
                   gap_mult: float = 0.0, scaled_budget_s: float = 0.0,
                   note: str = "") -> None:
        """Settle event during Phase 1.

        outcome: "accepted" | "empty_slot0" | "right_skipped"
                 | "fallthrough" | "murk_recheck" | "rejected"
        """
        self._ev["settle_total"] += 1
        key = f"settle_{outcome}" if outcome != "rejected" else "settle_fallthrough"
        if key in self._ev:
            self._ev[key] += 1
        self._write(
            f"  SETTLE  slot={slot}  {outcome:14s}  "
            f"dur={duration_s:.2f}s  gap_mult={gap_mult:.2f}  "
            f"budget={scaled_budget_s:.2f}s"
            + (f"  {note}" if note else "")
        )
        if outcome in ("fallthrough", "rejected"):
            self.log_failure(STATE, "settle_passive_region_empty",
                             {"slot": slot, "duration_s": round(duration_s, 2),
                              "gap_mult": round(gap_mult, 2)},
                             severity=ERROR)

    def log_buy_fail_in_place(self, cycle: int, evidence: dict | None = None) -> None:
        self._ev["buy_fail_in_place"] += 1
        self._write(f"  BUY_FAIL_IN_PLACE  cycle={cycle}")
        self.log_failure(INPUT, "buy_f_press_drop",
                         {"cycle": cycle, **(evidence or {})},
                         severity=WARN)

    def log_buy_qty(self, event: str, cycle: int = 0, expected: int = 0,
                    got: int = 0, n_cap: int = 0, conf: float = 0.0,
                    cost: int = 0, attempt: int = 0,
                    note: str = "") -> None:
        """event: verified | corrected_q | corrected_esc | unrecoverable
                  | ocr_fail | drift_detected | fallback_murk

        verified       — X==expected, no correction needed
        corrected_q    — X != expected, Q-back retry succeeded
        corrected_esc  — Q retries exhausted, ESC reset retry succeeded
        unrecoverable  — both Q and ESC paths exhausted, abort iteration
        ocr_fail       — OCR returned nothing parseable
        drift_detected — X/N and murk-cost cross-check disagreed
        fallback_murk  — X/N OCR uncertain, used murk-derived value instead
        """
        key = f"buy_qty_{event}"
        if key in self._ev:
            self._ev[key] += 1
        self._write(
            f"  BUY_QTY  {event:18s}  cyc={cycle}  exp={expected}  "
            f"got={got}/{n_cap}  conf={conf:.2f}  cost={cost}  att={attempt}"
            + (f"  {note}" if note else "")
        )
        if event == "ocr_fail":
            self.log_failure(OCR, "buy_qty_ocr_fail",
                             {"cycle": cycle, "expected": expected,
                              "attempt": attempt}, severity=WARN)
        elif event == "drift_detected":
            self.log_failure(OCR, "buy_qty_drift",
                             {"cycle": cycle, "got": got, "cost": cost},
                             severity=WARN)
        elif event == "unrecoverable":
            self.log_failure(STATE, "buy_qty_unrecoverable",
                             {"cycle": cycle, "expected": expected,
                              "got": got}, severity=ERROR)

    # ── Phase 2 / advance ────────────────────────────────────────────────── #

    def log_advance(self, cycle: int, idx: int, outcome: str,
                    retries: int = 0, note: str = "") -> None:
        """outcome: confirmed | duplicate | drop | dup_accepted
                    | wraparound_skip | endwrap_clamp | input_drop_skip
                    | recovery_success | relic_lost | cycle_short"""
        self._ev["advance_total"] += 1
        if outcome == "dup_accepted":
            self._ev["advance_dup_accepted"] += 1
        elif outcome == "drop":
            self._ev["advance_drop"] += 1
        elif outcome == "wraparound_skip":
            self._ev["p2_wraparound_skip"] += 1
        elif outcome == "endwrap_clamp":
            self._ev["p2_endwrap_clamp"] += 1
        elif outcome == "input_drop_skip":
            self._ev["p2_input_drop_skip"] += 1
        elif outcome == "recovery_success":
            self._ev["p2_recovery_success"] += 1
        elif outcome == "relic_lost":
            self._ev["p2_relics_lost"] += 1
        elif outcome == "cycle_short":
            self._ev["p2_cycles_short"] += 1
        if not self._verb_at_least(VERBOSITY_HIGH) and outcome == "confirmed":
            return
        self._write(
            f"  ADVANCE  cyc={cycle}  idx={idx}  {outcome:18s}  retries={retries}"
            + (f"  {note}" if note else "")
        )
        if outcome == "drop":
            self.log_failure(INPUT, "right_advance_drop",
                             {"cycle": cycle, "idx": idx, "retries": retries},
                             severity=WARN)
        elif outcome == "wraparound_skip":
            self.log_failure(INPUT, "end_of_list_wrap",
                             {"cycle": cycle, "idx": idx},
                             severity=WARN)
        elif outcome == "relic_lost":
            self.log_failure(STATE, "p2_relic_unrecoverable",
                             {"cycle": cycle, "idx": idx, "note": note},
                             severity=WARN)

    def log_cycle_summary(self, cycle: int, confirmed: int,
                          duplicate: int, dropped: int = 0) -> None:
        self._write(
            f"  CYCLE_SUMMARY  cyc={cycle}  confirmed={confirmed}  "
            f"duplicate={duplicate}  dropped={dropped}"
        )

    # ── Phase 3 events ───────────────────────────────────────────────────── #

    def log_phase3(self, event: str, cycle: int = 0, attempt: int = 0,
                   note: str = "") -> None:
        """event: tooltip_ok | tooltip_retry_ok | tooltip_retry_fail
                  | esc_recovery | esc_timeout | consecutive_fails
                  | iter_restart"""
        if event == "tooltip_retry_ok":
            self._ev["p3_tooltip_retry_ok"] += 1
        elif event == "tooltip_retry_fail":
            self._ev["p3_tooltip_retry_fail"] += 1
        elif event == "esc_timeout":
            self._ev["p3_esc_timeout"] += 1
        elif event == "consecutive_fails":
            self._ev["p3_consecutive_fails"] += 1
        elif event == "iter_restart":
            self._ev["p3_iter_restart"] += 1
        self._write(f"  PHASE3  {event:22s}  cyc={cycle}  att={attempt}"
                    + (f"  {note}" if note else ""))
        if event == "esc_timeout":
            self.log_failure(STATE, "p3_esc_recovery_timeout",
                             {"cycle": cycle}, severity=ERROR)
        elif event == "iter_restart":
            self.log_failure(STATE, "p3_consecutive_fails_escalation",
                             {"cycle": cycle}, severity=ERROR)
        elif event == "tooltip_retry_fail":
            self.log_failure(OCR, "p3_tooltip_retry_failed",
                             {"cycle": cycle}, severity=WARN)

    # ── Phase -0.5 / load ─────────────────────────────────────────────────── #

    def log_load(self, event: str, total_extended_s: float = 0.0,
                 note: str = "") -> None:
        """event: black_frame_detected | black_frame_extend | ceiling_reached
                  | in_game_confirmed"""
        if event == "black_frame_extend":
            self._ev["black_frame_extends"] += 1
        elif event == "ceiling_reached":
            self._ev["black_frame_ceiling"] += 1
        self._write(
            f"  LOAD  {event:22s}  extended_total={total_extended_s:.1f}s"
            + (f"  {note}" if note else "")
        )
        if event == "ceiling_reached":
            self.log_failure(SYSTEM, "black_frame_ceiling",
                             {"total_extended_s": round(total_extended_s, 1)},
                             severity=FATAL)

    # ── MenuNav events ───────────────────────────────────────────────────── #

    def log_menunav(self, event: str, from_row: str = "", expected: str = "",
                    got: str = "", recalc_n: int = 0, budget: int = 0,
                    note: str = "") -> None:
        """event: start | confirmed | recalc_on_doubling | recalc_path
                  | budget_exhausted | esc_fallback"""
        if event == "recalc_on_doubling":
            self._ev["menunav_recalcs"] += 1
            self._ev["menunav_doubling_hits"] += 1
        elif event == "recalc_path":
            self._ev["menunav_recalcs"] += 1
        elif event == "budget_exhausted":
            self._ev["menunav_budget_busted"] += 1
        self._write(
            f"  MENUNAV  {event:22s}  from={from_row}  exp={expected}  "
            f"got={got}  recalc={recalc_n}/{budget}"
            + (f"  {note}" if note else "")
        )
        if event == "recalc_on_doubling":
            self.log_failure(INPUT, "menunav_input_doubling",
                             {"from": from_row, "expected": expected,
                              "got": got, "recalc_n": recalc_n},
                             severity=WARN)
        elif event == "budget_exhausted":
            self.log_failure(STATE, "menunav_budget_exhausted",
                             {"from": from_row, "expected": expected,
                              "recalc_n": recalc_n},
                             severity=ERROR)

    # ── GPU AA suppression / latch ────────────────────────────────────────── #

    def log_gpu_aa(self, event: str, current_iter: int = 0,
                   drops: int = 0, suppress_count: int = 0,
                   note: str = "") -> None:
        """event: auto_suppress | re_enable | final_latch"""
        if event == "auto_suppress":
            self._ev["gpu_aa_suppressions"] += 1
        elif event == "re_enable":
            self._ev["gpu_aa_re_enables"] += 1
        elif event == "final_latch":
            self._ev["gpu_aa_final_latches"] += 1
        self._write(
            f"  GPU_AA  {event:14s}  iter={current_iter}  drops={drops}  "
            f"suppress_count={suppress_count}"
            + (f"  {note}" if note else "")
        )
        if event == "auto_suppress":
            self.log_failure(INPUT, "gpu_aa_input_drop_cascade",
                             {"iter": current_iter, "drops": drops,
                              "suppress_count": suppress_count},
                             severity=WARN)
        elif event == "final_latch":
            self.log_failure(INPUT, "gpu_aa_latch_held",
                             {"iter": current_iter,
                              "suppress_count": suppress_count},
                             severity=ERROR)

    # ── Input GPU yield gate (v1.7.1) ─────────────────────────────────────── #

    def log_input_yield(self, phase: str, key: str, wait_ms: float) -> None:
        """Log how long an input call had to wait on the GPU inflight lock.
        Lets us see whether the yield gate is actually doing work and how
        much it costs in real input latency."""
        self._ev["input_yield_calls"] += 1
        self._ev["input_yield_wait_ms"] += wait_ms
        if wait_ms > self._ev["input_yield_max_ms"]:
            self._ev["input_yield_max_ms"] = wait_ms
        if not self._verb_at_least(VERBOSITY_HIGH) and wait_ms < 5.0:
            return
        self._write(
            f"  INPUT_YIELD  {phase:14s}  key={key:12s}  wait={wait_ms:.1f}ms"
        )

    # ── Nav worker (CPU mode dedicated thread) ────────────────────────────── #

    def log_nav_worker(self, event: str, note: str = "") -> None:
        """event: started | submit | complete | timeout | death |
                  restart | inline_fallback"""
        if event == "started":
            self._ev["nav_worker_starts"] += 1
        elif event == "timeout":
            self._ev["nav_worker_timeouts"] += 1
        elif event == "death":
            self._ev["nav_worker_deaths"] += 1
        elif event == "restart":
            self._ev["nav_worker_restarts"] += 1
        elif event == "inline_fallback":
            self._ev["nav_worker_inline_fb"] += 1
        if not self._verb_at_least(VERBOSITY_HIGH) and event in ("submit", "complete"):
            return
        self._write(f"  NAV_WORKER  {event:18s}  {note}")
        if event == "timeout":
            self.log_failure(SYSTEM, "nav_worker_timeout", {},
                             severity=WARN)
        elif event == "death":
            self.log_failure(SYSTEM, "nav_worker_died", {},
                             severity=ERROR)

    # ── Async analysis ───────────────────────────────────────────────────── #

    def log_async(self, event: str, note: str = "") -> None:
        """event: submit | complete | error | hit | flush"""
        if event == "submit":
            self._ev["async_submits"] += 1
        elif event == "complete":
            self._ev["async_completes"] += 1
        elif event == "error":
            self._ev["async_errors"] += 1
        elif event == "hit":
            self._ev["async_hits"] += 1
        elif event == "flush":
            self._ev["backlog_flushes"] += 1
        if not self._verb_at_least(VERBOSITY_HIGH) and event in ("submit", "complete"):
            return
        self._write(f"  ASYNC  {event:10s}  {note}")
        if event == "error":
            self.log_failure(SYSTEM, "async_worker_error",
                             {"note": note[:80]}, severity=WARN)

    # ── OCR pipeline detail ──────────────────────────────────────────────── #

    def log_slot_ocr(self, current_iter: int, relic_idx: int, slot_idx: int,
                     passive: str | None, curse: str | None,
                     duration_s: float = 0.0,
                     raw_token_count: int = 0) -> None:
        self._ev["slot_ocr_calls"] += 1
        if passive:
            self._ev["slot_ocr_passive_hits"] += 1
        if curse:
            self._ev["slot_ocr_curse_hits"] += 1
        if not self._verb_at_least(VERBOSITY_HIGH):
            return
        self._write(
            f"  SLOT_OCR  iter={current_iter}  relic={relic_idx}  "
            f"slot={slot_idx}  passive={passive!r}  curse={curse!r}  "
            f"tokens={raw_token_count}  dur={duration_s:.3f}s"
        )

    def log_curse_miss(self, current_iter: int, cycle: int, slot_idx: int,
                       raw_text: str = "", dump_path: str = "") -> None:
        """Curse pixels visible but no curse matched.  The raw crop has
        been dumped to <batch_run>/curse_misses/ for offline iteration."""
        self._ev["curse_misses"] += 1
        self._write(
            f"  CURSE_MISS  iter={current_iter}  cyc={cycle}  slot={slot_idx}  "
            f"raw={raw_text[:60]!r}  dump={os.path.basename(dump_path) if dump_path else '?'}"
        )
        self.log_failure(OCR, "curse_pixels_no_match",
                         {"iter": current_iter, "cycle": cycle,
                          "slot": slot_idx, "raw": raw_text[:80],
                          "dump": os.path.basename(dump_path) if dump_path else ""},
                         severity=WARN)

    def log_passive_miss(self, current_iter: int, slot_idx: int,
                         raw_text: str) -> None:
        """Token was classified as passive (white text) but dictionary
        match failed.  Tracks dictionary gaps in passives.py and
        OCR-mangled real passives that fall below the fuzzy threshold."""
        self._ev.setdefault("passive_misses", 0)
        self._ev["passive_misses"] += 1
        if not self._verb_at_least(VERBOSITY_HIGH):
            # Still classify as failure for aggregator, just don't
            # write per-call line at NORMAL verbosity.
            self.log_failure(OCR, "passive_no_match",
                             {"iter": current_iter, "slot": slot_idx,
                              "raw": raw_text[:80]},
                             severity=WARN)
            return
        self._write(
            f"  PASSIVE_MISS  iter={current_iter}  slot={slot_idx}  "
            f"raw={raw_text[:80]!r}"
        )
        self.log_failure(OCR, "passive_no_match",
                         {"iter": current_iter, "slot": slot_idx,
                          "raw": raw_text[:80]},
                         severity=WARN)

    def log_name_no_passives(self, current_iter: int, relic_idx: int,
                             relic_name: str) -> None:
        """Name OCR succeeded but all passive slots came back empty.
        This is the v1.7.1 regression signature — keep monitoring it."""
        self._write(
            f"  OCR_REGRESSION_SIGNATURE  iter={current_iter}  "
            f"relic={relic_idx}  name={relic_name!r}  passives=EMPTY"
        )
        self.log_failure(OCR, "name_ok_passives_empty",
                         {"iter": current_iter, "relic": relic_idx,
                          "name": relic_name}, severity=ERROR)

    # ── Door generation / matching ────────────────────────────────────────── #

    def log_door_gen(self, mode: str, door_count: int,
                     types: dict | None = None) -> None:
        self._ev["door_gen_calls"] += 1
        self._ev["door_total_generated"] += door_count
        breakdown = ""
        if types:
            breakdown = "  " + " ".join(f"{k}={v}" for k, v in types.items())
        self._write(f"  DOOR_GEN  mode={mode}  doors={door_count}{breakdown}")

    def log_compat_reject(self, door_id: str, conflicting: list) -> None:
        self._ev["compat_rejects"] += 1
        if not self._verb_at_least(VERBOSITY_HIGH):
            return
        self._write(f"  COMPAT_REJECT  door={door_id}  conflicts={conflicting}")

    def bump_compat_rejects(self, n: int = 1) -> None:
        """Bulk increment for post-hoc counting from the door generator.

        `log_compat_reject` is per-rejection with evidence; during batch
        generation where 100s of rejections are expected, the bot tallies
        them in door_generator and calls this once with the total.
        """
        if n > 0:
            self._ev["compat_rejects"] += n

    def log_duplicate_skip(self, current_iter: int, idx: int, reason: str) -> None:
        self._ev["duplicate_skips"] += 1
        self._write(f"  DUP_SKIP  iter={current_iter}  idx={idx}  reason={reason}")

    # ── Game state ────────────────────────────────────────────────────────── #

    def log_game(self, event: str, attempt: int = 0, note: str = "") -> None:
        """event: launch_start | launch_ok | launch_fail | focus_ok |
                  close | save_restore | steam_reset"""
        if event == "launch_start":
            self._ev["game_launches"] += 1
        elif event == "launch_fail":
            self._ev["game_launch_fails"] += 1
        elif event == "save_restore":
            self._ev["save_restores"] += 1
        self._write(f"  GAME  {event:14s}  attempt={attempt}"
                    + (f"  {note}" if note else ""))
        if event == "launch_fail":
            self.log_failure(SYSTEM, "game_launch_fail",
                             {"attempt": attempt, "note": note[:80]},
                             severity=ERROR)

    def log_perf_calibration(self, old_mult: float, new_mult: float,
                             sample_n: int = 0) -> None:
        self._ev["perf_recalibrations"] += 1
        self._write(
            f"  PERF_CALIBRATION  {old_mult:.3f}× → {new_mult:.3f}×  "
            f"(samples={sample_n})"
        )

    def log_profile(self, event: str, name: str = "", mode: str = "",
                    migrated: bool = False) -> None:
        self._write(
            f"  PROFILE  {event:14s}  name={name!r}  mode={mode}  "
            f"migrated={migrated}"
        )

    # ── session summary ───────────────────────────────────────────────────── #

    def write_summary(self):
        """Append aggregate session stats. Call at end of batch run."""
        session_s = time.time() - self._session_start
        lines = ["", "=" * 72, "=== SESSION SUMMARY ==="]
        lines.append(f"Total session time : {session_s:.1f}s  ({session_s/60:.1f} min)")

        # Iteration timing
        if self._all_iter_times:
            avg = sum(self._all_iter_times) / len(self._all_iter_times)
            mn  = min(self._all_iter_times)
            mx  = max(self._all_iter_times)
            var = sum((t - avg) ** 2 for t in self._all_iter_times) / len(self._all_iter_times)
            lines.append(
                f"Batches            : {len(self._all_iter_times)}"
                f"  avg={avg:.1f}s  min={mn:.1f}s  max={mx:.1f}s  stddev={var**0.5:.1f}s"
            )
        else:
            lines.append("Batches            : 0 completed")

        # Input reliability
        tot  = self._inp["press_total"]
        ok   = self._inp["press_ok"]
        fail = self._inp["press_fail"]
        pct  = (ok / tot * 100) if tot else 0.0
        lines.append(f"Bot key presses    : {tot}  ok={ok}  fail={fail}  reliability={pct:.1f}%")

        # OCR
        o = self._ocr
        avg_t = (o["total_time"] / o["total"]) if o["total"] else 0.0
        dropped = o.get("dropped", 0)
        lines.append(
            f"OCR calls          : {o['total']}"
            f"  true={o['true']}  false={o['false']}  error={o['error']}"
            f"  avg={avg_t:.3f}s"
        )
        lines.append(
            f"OCR token drops    : {dropped}"
            f"  (tokens filtered by conf<0.35 or len<3 — see OCR_DUMP entries)"
        )

        # User interference
        key_events   = [e for e in self._user_events if "KEY"   in e[1]]
        mouse_events = [e for e in self._user_events if "MOUSE" in e[1]]
        lines.append(
            f"User interference  : {len(self._user_events)} total"
            f"  ({len(key_events)} keyboard  {len(mouse_events)} mouse)"
        )
        if self._user_events:
            lines.append("  Interference timestamps:")
            for ts_f, desc in self._user_events:
                lines.append(f"    {datetime.datetime.fromtimestamp(ts_f).strftime('%H:%M:%S.%f')[:-3]}  {desc}")

        # GPU install
        if self._gpu_install_started:
            lines.append(
                f"GPU install        : {'SUCCESS' if self._gpu_install_ok else 'FAILED/INCOMPLETE'}"
            )

        # ── v1.7.x feature aggregates ────────────────────────────────── #
        e = self._ev
        lines.append("")
        lines.append("--- Phase 1 / Settle ---")
        lines.append(
            f"Settle calls       : {e['settle_total']}  "
            f"empty_slot0={e['settle_empty_slot0']}  "
            f"right_skipped={e['settle_right_skipped']}  "
            f"accepted={e['settle_accepted']}  "
            f"fallthrough={e['settle_fallthrough']}"
        )
        lines.append(f"Buy fail-in-place  : {e['buy_fail_in_place']}")

        lines.append("--- Phase 2 / Advance ---")
        lines.append(
            f"Advances           : {e['advance_total']}  "
            f"dup_accepted={e['advance_dup_accepted']}  "
            f"drops={e['advance_drop']}"
        )

        lines.append("--- Phase 3 ---")
        lines.append(
            f"Tooltip retry      : ok={e['p3_tooltip_retry_ok']}  "
            f"fail={e['p3_tooltip_retry_fail']}  "
            f"esc_timeout={e['p3_esc_timeout']}  "
            f"iter_restarts={e['p3_iter_restart']}"
        )

        lines.append("--- Phase -0.5 / Load ---")
        lines.append(
            f"Black-frame extends: {e['black_frame_extends']}  "
            f"ceiling_hit={e['black_frame_ceiling']}"
        )

        lines.append("--- MenuNav ---")
        lines.append(
            f"Recalcs            : {e['menunav_recalcs']}  "
            f"doubling={e['menunav_doubling_hits']}  "
            f"budget_busted={e['menunav_budget_busted']}"
        )

        lines.append("--- GPU AA suppression ---")
        lines.append(
            f"Suppressions       : {e['gpu_aa_suppressions']}  "
            f"re_enables={e['gpu_aa_re_enables']}  "
            f"final_latches={e['gpu_aa_final_latches']}"
        )

        lines.append("--- Input GPU yield gate ---")
        avg_wait = (e['input_yield_wait_ms'] / e['input_yield_calls']
                    if e['input_yield_calls'] else 0.0)
        lines.append(
            f"Yield calls        : {e['input_yield_calls']}  "
            f"avg={avg_wait:.1f}ms  max={e['input_yield_max_ms']:.1f}ms"
        )

        lines.append("--- Nav worker ---")
        lines.append(
            f"Nav worker         : starts={e['nav_worker_starts']}  "
            f"timeouts={e['nav_worker_timeouts']}  "
            f"deaths={e['nav_worker_deaths']}  "
            f"restarts={e['nav_worker_restarts']}  "
            f"inline_fb={e['nav_worker_inline_fb']}"
        )

        lines.append("--- Async / backlog ---")
        lines.append(
            f"Async              : submit={e['async_submits']}  "
            f"complete={e['async_completes']}  "
            f"errors={e['async_errors']}  "
            f"hits={e['async_hits']}  "
            f"flushes={e['backlog_flushes']}"
        )

        lines.append("--- OCR pipeline ---")
        passive_rate = (e['slot_ocr_passive_hits'] / e['slot_ocr_calls'] * 100
                        if e['slot_ocr_calls'] else 0.0)
        lines.append(
            f"Slot OCR           : calls={e['slot_ocr_calls']}  "
            f"passive_hits={e['slot_ocr_passive_hits']} ({passive_rate:.1f}%)  "
            f"curse_hits={e['slot_ocr_curse_hits']}"
        )
        lines.append(f"Curse misses (PNG) : {e['curse_misses']}  (see curse_misses/ folder)")

        lines.append("--- Doors / matching ---")
        lines.append(
            f"Door gen           : calls={e['door_gen_calls']}  "
            f"total_doors={e['door_total_generated']}  "
            f"compat_rejects={e['compat_rejects']}  "
            f"dup_skips={e['duplicate_skips']}"
        )

        lines.append("--- Game state ---")
        lines.append(
            f"Game launches      : {e['game_launches']}  "
            f"fails={e['game_launch_fails']}  "
            f"save_restores={e['save_restores']}  "
            f"perf_recalibrations={e['perf_recalibrations']}"
        )

        # ── Failure classification breakdown ─────────────────────────── #
        snap = self._failures.snapshot()
        lines.append("")
        lines.append("=== FAILURE CLASSIFICATION ===")
        lines.append(f"Total failures     : {snap['total']}")
        if snap['cat_counts']:
            lines.append("By category:")
            for cat in (SYSTEM, INPUT, OCR, STATE, USER):
                n = snap['cat_counts'].get(cat, 0)
                if n:
                    lines.append(f"  {cat:8s}  {n}")
        if snap['severity_counts']:
            lines.append("By severity:")
            for sev in (INFO, WARN, ERROR, FATAL):
                n = snap['severity_counts'].get(sev, 0)
                if n:
                    lines.append(f"  {sev:6s}  {n}")
        if snap['counts']:
            lines.append("Top subcategories:")
            sorted_subs = sorted(snap['counts'].items(),
                                 key=lambda kv: kv[1], reverse=True)
            for key, n in sorted_subs[:15]:
                lines.append(f"  {key:50s}  {n}")
        if snap['recent']:
            lines.append("")
            lines.append("Most recent failures (up to 10):")
            for rec in snap['recent'][-10:]:
                ev_str = "  ".join(f"{k}={v}" for k, v in rec.get('evidence', {}).items())
                lines.append(
                    f"  [{rec['ts_str']}]  {rec['severity']:5s}  "
                    f"{rec['category']}/{rec['subcategory']}  {ev_str}"
                )

        lines.append(f"\nFull log           : {self._path}")
        lines.append("=" * 72)

        self._write_block("\n".join(lines))

    # ── snapshot accessors (Export Diagnostics consumer) ──────────────────── #

    def get_event_counters(self) -> dict:
        """Return a copy of the v1.7.x feature counters dict."""
        return dict(self._ev)

    def get_failure_snapshot(self) -> dict:
        """Return failure classifier snapshot for Export Diagnostics."""
        return self._failures.snapshot()

    def get_path(self) -> str:
        return self._path

    # ── lifecycle ─────────────────────────────────────────────────────────── #

    def close(self):
        """Stop monitor and write summary. Safe to call multiple times."""
        if getattr(self, "_closed", False):
            return
        self._closed = True
        self.stop_interference_monitor()
        self.write_summary()
        # Final persistence: capture the last runtime snapshot alongside
        # the closed counters and failure aggregator.  This is what the
        # Export Diagnostics button reads after an app restart.
        try:
            _rt = self._runtime_snapshot_fn() if self._runtime_snapshot_fn else {}
        except Exception:
            _rt = {}
        try:
            persist_run_state(self._ev, self._failures.snapshot(), _rt)
        except Exception:
            pass

    def set_runtime_snapshot_fn(self, fn) -> None:
        """app.py installs a callable that returns a dict of live app
        state (perf_gap_mult, GPU AA suppression flags, P3 fail counters,
        etc.) so persist_run_state() can capture it alongside counters."""
        self._runtime_snapshot_fn = fn
