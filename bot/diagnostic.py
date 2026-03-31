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

        lines.append(f"\nFull log           : {self._path}")
        lines.append("=" * 72)

        self._write_block("\n".join(lines))

    # ── lifecycle ─────────────────────────────────────────────────────────── #

    def close(self):
        """Stop monitor and write summary. Safe to call multiple times."""
        self.stop_interference_monitor()
        self.write_summary()
