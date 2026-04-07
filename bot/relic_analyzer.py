"""
Analyzes relic screenshots using local OCR (EasyOCR).
Runs entirely on-device — no internet connection or account required.

First run: EasyOCR downloads its English model (~100 MB) automatically.
After that the bot works fully offline with no ongoing costs.
"""

import io
import re
import time
import queue
import difflib
import threading
import concurrent.futures

import numpy as np
from PIL import Image


# ── Navigator OCR isolation ──────────────────────────────────────────── #
# nav_ocr() is the single entry point for main-thread navigation OCR.
# GPU mode: priority gate — analysis workers acquire _gpu_inflight_lock
#   around their reader.readtext() calls and yield while _nav_wants_gpu
#   is set, so nav jumps the queue without pre-emption.
# CPU mode: dedicated nav thread with its own EasyOCR Reader, higher
#   OS priority, and an affinity mask disjoint from the analysis mask.

_nav_wants_gpu       = threading.Event()
_gpu_inflight_lock   = threading.Lock()
_pause_inputs_for_nav = None   # callable(bool); set by app.py at startup

_nav_thread: "threading.Thread | None" = None
_nav_queue: "queue.Queue | None"        = None
_nav_thread_started = False
_nav_started_lock   = threading.Lock()


def register_input_pause_hook(fn) -> None:
    """app.py calls this at startup to register an input-pause callback.

    The callback takes one bool argument: True to pause inputs (before nav
    OCR runs on the main-thread GPU reader), False to resume.
    """
    global _pause_inputs_for_nav
    _pause_inputs_for_nav = fn


def _wait_for_nav_yield() -> None:
    """Analysis workers call this in a tight spin before each readtext
    to yield GPU cycles to pending nav OCR calls."""
    while _nav_wants_gpu.is_set():
        time.sleep(0.005)


def _nav_worker_loop() -> None:
    import easyocr
    try:
        import ctypes
        THREAD_PRIORITY_ABOVE_NORMAL = 1
        h = ctypes.windll.kernel32.GetCurrentThread()
        ctypes.windll.kernel32.SetThreadPriority(h, THREAD_PRIORITY_ABOVE_NORMAL)
    except Exception:
        pass
    try:
        import os as _os
        cpu_n = _os.cpu_count() or 4
        if _ocr_affinity_mask:
            _full = (1 << cpu_n) - 1
            _nav_mask = _full & ~_ocr_affinity_mask
            if not _nav_mask:
                _nav_mask = 0b11 & _full
        else:
            _nav_mask = 0b11 & ((1 << cpu_n) - 1)
        if _nav_mask:
            _apply_thread_affinity(_nav_mask)
    except Exception:
        pass
    try:
        _nav_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    except Exception:
        _nav_reader = None
    while True:
        try:
            item = _nav_queue.get()
        except Exception:
            break
        if item is None:
            break
        crop, kwargs, fut = item
        try:
            if _nav_reader is None:
                raise RuntimeError("nav reader not initialized")
            res = _nav_reader.readtext(crop, **kwargs)
            fut.set_result(res)
        except Exception as e:
            try:
                fut.set_exception(e)
            except Exception:
                pass


def start_nav_worker() -> None:
    """Start the dedicated CPU nav thread if not yet running.  Safe to call
    multiple times — if the existing thread is alive, this is a no-op; if
    it died (or was never started), a fresh thread is spawned and the
    queue is recreated.  No-op in GPU mode — the priority-gate path
    handles nav routing without a dedicated thread."""
    global _nav_thread, _nav_queue, _nav_thread_started
    with _nav_started_lock:
        if _nav_thread is not None and _nav_thread.is_alive():
            _nav_thread_started = True
            return
        # Either never started, or the previous thread died — (re)spawn.
        _nav_queue = queue.Queue()
        _nav_thread = threading.Thread(
            target=_nav_worker_loop, daemon=True, name="relic-nav-ocr")
        _nav_thread.start()
        _nav_thread_started = True


def _nav_inline_fallback(crop_bgr, kw):
    """Last-resort path: run nav OCR inline on the main-thread reader using
    the same priority-gate pattern as GPU mode.  Used when the CPU nav
    worker thread has died and cannot be revived."""
    _nav_wants_gpu.set()
    if _pause_inputs_for_nav is not None:
        try:
            _pause_inputs_for_nav(True)
        except Exception:
            pass
    try:
        with _gpu_inflight_lock:
            reader = _get_reader()
            return reader.readtext(crop_bgr, **kw)
    finally:
        _nav_wants_gpu.clear()
        if _pause_inputs_for_nav is not None:
            try:
                _pause_inputs_for_nav(False)
            except Exception:
                pass


def nav_ocr(crop_bgr, *, name_only=False, **kw):
    """OCR call for the main thread / navigation.  Routes through the
    priority gate (GPU) or the dedicated nav thread (CPU) so navigation
    never contends with analysis workers.

    name_only — reserved for future lightweight name-band OCR path.
    """
    global _nav_thread_started
    if _gpu_mode_enabled:
        _nav_wants_gpu.set()
        if _pause_inputs_for_nav is not None:
            try:
                _pause_inputs_for_nav(True)
            except Exception:
                pass
        try:
            with _gpu_inflight_lock:
                reader = _get_reader()
                return reader.readtext(crop_bgr, **kw)
        finally:
            _nav_wants_gpu.clear()
            if _pause_inputs_for_nav is not None:
                try:
                    _pause_inputs_for_nav(False)
                except Exception:
                    pass
    else:
        if not _nav_thread_started:
            start_nav_worker()
        fut: concurrent.futures.Future = concurrent.futures.Future()
        _nav_queue.put((crop_bgr, kw, fut))
        try:
            return fut.result(timeout=30.0)
        except concurrent.futures.TimeoutError:
            pass
        # Timeout — diagnose and recover.
        _alive = _nav_thread is not None and _nav_thread.is_alive()
        if not _alive:
            print("[NavWorker] Worker thread died — restarting", flush=True)
            with _nav_started_lock:
                _nav_thread_started = False
            start_nav_worker()
        # Retry once on the (possibly new) queue.
        try:
            fut2: concurrent.futures.Future = concurrent.futures.Future()
            _nav_queue.put((crop_bgr, kw, fut2))
            return fut2.result(timeout=30.0)
        except Exception:
            pass
        print("[NavWorker] CPU nav unavailable — falling back to inline OCR"
              " on main thread", flush=True)
        return _nav_inline_fallback(crop_bgr, kw)


import contextlib

@contextlib.contextmanager
def input_gpu_yield():
    """Pause GPU analysis workers around a critical game input.

    Mirrors the nav_ocr GPU priority gate, but yields to the caller instead
    of running OCR.  Sets _nav_wants_gpu so analysis workers stop spawning
    new readtext calls, then acquires _gpu_inflight_lock so any in-flight
    readtext drains before the caller's input is sent.  This eliminates the
    "input drop" race where the game misses a key press while the GPU is
    saturated by an analysis readtext.

    No-op in CPU mode — CPU OCR workers don't cause input drops the same
    way the GPU contention does.
    """
    if not _gpu_mode_enabled:
        yield
        return
    _nav_wants_gpu.set()
    try:
        with _gpu_inflight_lock:
            yield
    finally:
        _nav_wants_gpu.clear()


# ── EasyOCR reader — one instance per thread ─────────────────────────── #
#
# EasyOCR is not thread-safe when sharing a single Reader instance.
# Using threading.local() gives each thread its own Reader so that
# multiple worker threads can run OCR in parallel without interfering.
# The model is loaded lazily on the first call from each thread (~2-3 s
# one-time cost; subsequent calls on the same thread are instant).

_thread_local        = threading.local()
_thread_device_local = threading.local()   # per-thread GPU override (True/False/None)
_thread_nav_mode     = threading.local()   # analyze() routes via nav_ocr when set
_torch_threads       = 1      # set via configure_torch_threads() before workers start
_gpu_mode_enabled    = False  # set via set_gpu_mode() from the UI
_ocr_affinity_mask   = 0      # set via configure_ocr_affinity(); 0 = no restriction


def _apply_thread_affinity(mask: int) -> None:
    """Pin the calling thread to the given CPU core bitmask (Windows only).

    Called from within OCR worker threads so they are restricted to OCR-only
    cores, leaving the input core free for the bot thread.  Silent no-op on
    non-Windows or if the mask is 0.
    """
    if not mask:
        return
    try:
        import ctypes
        handle = ctypes.windll.kernel32.GetCurrentThread()
        ctypes.windll.kernel32.SetThreadAffinityMask(handle, mask)
    except Exception:
        pass


def configure_ocr_affinity(mask: int) -> None:
    """Set the CPU core affinity mask applied to every OCR worker thread.

    Pass a bitmask of cores that OCR workers are allowed to run on.
    0 disables the restriction (default).  Called from app.py before
    async workers start so the mask is in place when _get_reader() fires.
    """
    global _ocr_affinity_mask
    _ocr_affinity_mask = mask


def configure_torch_threads(n: int) -> None:
    """Set PyTorch's per-inference CPU thread count for all subsequent calls.

    With multiple workers each defaulting to all available cores, threads
    fight each other (oversubscription).  Setting this to cpu_cores/workers
    distributes cores evenly so workers run in parallel without contention.
    Also sets num_interop_threads to 1 to reduce parallel-op scheduling
    overhead (the main source of CPU spike outside of matrix math).
    Call once from the main thread before spawning async workers.
    """
    global _torch_threads
    _torch_threads = max(1, n)
    try:
        import torch
        torch.set_num_threads(_torch_threads)
        torch.set_num_interop_threads(1)
    except Exception:
        pass


def set_thread_device(gpu) -> None:
    """Force the calling thread to use GPU (True) or CPU (False).

    Pass None to clear the override and fall back to the global gpu_mode flag.
    Call this at thread startup — before the first analyze() call — so the
    correct Reader is created from the start.
    """
    _thread_device_local.use_gpu = gpu


def set_gpu_mode(enabled: bool) -> None:
    """Enable or disable GPU (CUDA) inference for all subsequent OCR calls.

    Each worker thread checks this flag before each call and reloads its Reader
    if the setting has changed, so toggling mid-run takes effect on the next
    analysis request without requiring a restart.
    """
    global _gpu_mode_enabled
    _gpu_mode_enabled = bool(enabled)


def _get_reader():
    """Return the EasyOCR reader for the calling thread, loading it if needed.

    Reloads automatically if the GPU mode has changed since the reader was
    created — each thread tracks the gpu setting its reader was built with.
    Applies the OCR affinity mask on first load so the calling thread (an
    async worker) is pinned to OCR-only cores, keeping the input core free.

    Per-thread device override (set via set_thread_device()) takes priority
    over the global _gpu_mode_enabled flag — used by hybrid GPU+CPU backlog
    workers so each thread runs on its designated device.
    """
    _override = getattr(_thread_device_local, "use_gpu", None)
    _use_gpu  = _override if _override is not None else _gpu_mode_enabled
    if not hasattr(_thread_local, "reader") or getattr(_thread_local, "reader_gpu", None) != _use_gpu:
        _apply_thread_affinity(_ocr_affinity_mask)
        try:
            import torch
            torch.set_num_threads(_torch_threads)
            torch.set_num_interop_threads(1)
        except Exception:
            pass
        import easyocr
        _thread_local.reader     = easyocr.Reader(["en"], gpu=_use_gpu, verbose=False)
        _thread_local.reader_gpu = _use_gpu
    return _thread_local.reader


# ── Relic panel crop ─────────────────────────────────────────────────── #
#
# The relic info panel (name + passives) always occupies the bottom-right of
# the Relic Rites sell screen.  Using fractions of the image dimensions keeps
# the crop correct at any screen resolution (1080p, 1440p, 4K, etc.) as long
# as the game runs in borderless or fullscreen mode.
#
# Geometry (derived from the sell-screen layout):
#   left edge  ≈ 45 % from left  — just before the vertical centre line
#   top  edge  ≈ 65 % from top   — upper boundary of the panel row
#
# Adjust these two constants if your UI layout differs (e.g. an ultrawide aspect
# ratio with pillarboxing may need a different left fraction).

_CROP_LEFT_FRAC = 0.45   # fraction of image width  to skip from the left
_CROP_TOP_FRAC  = 0.65   # fraction of image height to skip from the top

# Geometry for the post-buy preview screen (bazaar inspect view):
#   The info sub-box (relic icon + name + passives) is centred in the modal.
#   At 2560×1440 the relic name starts at ~y=46%, text at ~x=46%.
#   Cropping from left=0.28 / top=0.38 captures the full info panel while
#   excluding the shop items column on the far left.
#
#   Top was lowered from 0.42 → 0.38 to give a larger margin above the relic
#   name.  Delicate relics (1 passive) have their only passive line just below
#   the name; at 0.42 it could land right at the crop boundary and be missed.
#   0.38 keeps the passive well within the captured area at all tested
#   resolutions without meaningfully increasing OCR area.

_PREVIEW_CROP_LEFT_FRAC = 0.28   # fraction of width  to skip (preview screen)
_PREVIEW_CROP_TOP_FRAC  = 0.38   # fraction of height to skip (preview screen)

# Maximum width (px) fed to the OCR engine after cropping.
# OCR time scales with pixel count — capping at 1000 px gives ~2-3× speed
# improvement on 1440p/4K screens with no meaningful accuracy loss (relic
# name and passive text remains well above the minimum legible size).
_MAX_OCR_WIDTH = 1000

# ── Slot-based OCR geometry ──────────────────────────────────────────── #
# Fixed Y positions (fraction of full screen height, 16:9 any resolution).
# Each relic has 3 passive slots. Each slot has a passive line and an
# optional curse line below it.  Positions measured from 2560x1440 and
# confirmed across Grand/Polished/Delicate, Normal and Deep.
#
# The X range covers the text area of the relic detail panel.
_SLOT_X_START = 0.348    # fraction of screen width — passive/curse text (past icons)
_SLOT_X_END   = 0.73     # fraction of screen width (right edge of text)
# Name crop needs a WIDER x range than slot crops because the relic name
# starts to the LEFT of where passive icons sit (verified at px 680 / 0.266
# on a 2560x1440 screenshot — the "D" of "Deep Grand Tranquil Scene").
# Using _SLOT_X_START for the name crop would cut off "Deep Grand".
_NAME_X_START = 0.330    # fraction of screen width (post-icon, pre-text gap)
_NAME_X_END   = 0.73     # fraction of screen width (right edge of relic name)

# Each slot: (passive_y_center, curse_y_center) as fraction of screen height.
# The passive line is ~0.8% tall, curse line is ~0.8% tall.
# We crop +/- 1.5% around each center to capture the full text line.
# Each slot center covers the full passive (1-2 lines) + optional curse.
# Slot height of +/- 3.2% captures both without overlapping adjacent slots.
_SLOT_CENTERS = [0.595, 0.655, 0.715]   # Y center of each passive+curse pair
_SLOT_HALF_HEIGHT = 0.028               # +/- 2.8% — disjoint crops, no neighbor bleed

# Relic name position (for extracting the name before passives)
_NAME_Y_CENTER = 0.548     # measured peak of name text density
_NAME_HALF_HEIGHT = 0.014  # +/- 1.4% — tight fit around the glyph row


def _to_array(image_bytes: bytes, max_width: int = 0) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if max_width and img.width > max_width:
        scale = max_width / img.width
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.LANCZOS,
        )
    return np.array(img)


# ── Passive fuzzy matching ────────────────────────────────────────────── #

# Template passives: long passives where only a short keyword in the middle
# differs.  Generic fuzzy matching fails on these because the shared
# prefix+suffix dominates the similarity ratio.  We extract the keyword
# and match that independently.
#
# Two families:
#   1. Spell-change: "Changes compatible armament's [type] to X at start..."
#   2. Weapon-class: "Improved Attack Power with 3+ X Equipped"

_SPELL_CHANGE_RE = re.compile(
    r"[Cc]hang\w*\s+compatible\s+armament.?\s*s?\s+"
    r"(skill|incantation|sorcery)\s+to\s+(.+?)\s+at\s+start",
    re.IGNORECASE,
)
_WEAPON_CLASS_RE = re.compile(
    r"[Ii]mproved\s+[Aa]ttack\s+[Pp]ower\s+with\s+3\+?\s+(.+?)\s+[Ee]quipped",
    re.IGNORECASE,
)

# Lookups populated on first use
_SPELL_CHANGE_PASSIVES: dict[str, dict[str, str]] = {}
_SPELL_NAMES_BY_TYPE: dict[str, list[str]] = {}
_WEAPON_CLASS_PASSIVES: dict[str, str] = {}  # {weapon_lower: full_passive}
_WEAPON_CLASS_NAMES: list[str] = []
_TEMPLATE_LOOKUP_INIT = False

def _ensure_template_lookup():
    """Populate template passive lookup tables on first use."""
    global _TEMPLATE_LOOKUP_INIT
    if _TEMPLATE_LOOKUP_INIT:
        return
    _TEMPLATE_LOOKUP_INIT = True
    from bot.passives import ALL_PASSIVES_SORTED
    _spell_re = re.compile(
        r"Changes compatible armament's (skill|incantation|sorcery) "
        r"to (.+) at start of expedition")
    _weapon_re = re.compile(
        r"Improved Attack Power with 3\+ (.+) Equipped")
    for p in ALL_PASSIVES_SORTED:
        m = _spell_re.match(p)
        if m:
            stype = m.group(1)
            sname = m.group(2)
            _SPELL_CHANGE_PASSIVES.setdefault(stype, {})[sname.lower()] = p
            _SPELL_NAMES_BY_TYPE.setdefault(stype, []).append(sname)
            continue
        m = _weapon_re.match(p)
        if m:
            wname = m.group(1)
            _WEAPON_CLASS_PASSIVES[wname.lower()] = p
            _WEAPON_CLASS_NAMES.append(wname)


def _match_template_passive(text: str) -> str | None:
    """Try to match a template passive by extracting the keyword.

    Handles spell-change passives ("Changes ... to X at start ...") and
    weapon-class passives ("Improved Attack Power with 3+ X Equipped").

    Returns the full passive string if matched, None otherwise.
    """
    # Try spell-change first
    m = _SPELL_CHANGE_RE.search(text)
    if m:
        _ensure_template_lookup()
        spell_type = m.group(1).lower()
        ocr_name = m.group(2).strip()
        if len(ocr_name) < 2:
            return None
        lookup = _SPELL_CHANGE_PASSIVES.get(spell_type)
        names = _SPELL_NAMES_BY_TYPE.get(spell_type)
        if not lookup or not names:
            return None
        if ocr_name.lower() in lookup:
            return lookup[ocr_name.lower()]
        hits = difflib.get_close_matches(ocr_name, names, n=1, cutoff=0.6)
        if hits:
            return lookup.get(hits[0].lower())
        return None

    # Try weapon-class
    m = _WEAPON_CLASS_RE.search(text)
    if m:
        _ensure_template_lookup()
        ocr_name = m.group(1).strip()
        if len(ocr_name) < 2:
            return None
        if ocr_name.lower() in _WEAPON_CLASS_PASSIVES:
            return _WEAPON_CLASS_PASSIVES[ocr_name.lower()]
        hits = difflib.get_close_matches(
            ocr_name, _WEAPON_CLASS_NAMES, n=1, cutoff=0.6)
        if hits:
            return _WEAPON_CLASS_PASSIVES.get(hits[0].lower())
        return None

    return None


def _match_passive(text: str, known: list, cutoff: float = 0.82) -> str | None:
    """
    Return the closest known passive name, or None if below cutoff.

    For spell-change passives ("Changes compatible armament's ... to X ..."),
    extracts the spell name and matches it independently for higher accuracy.

    Strict +N suffix rule: if either the OCR text or the matched passive has a
    +N suffix, both must carry the exact same suffix.  This means:
      • "Foo"      will NOT match "Foo +1"   (missing suffix)
      • "Foo +1"   will NOT match "Foo +2"   (wrong number)
      • "Foo +2"   will NOT match "Foo"      (extra suffix)
    OCR must read the correct +N for it to count.
    """
    text = text.strip()
    if len(text) < 5:
        return None
    # Try template matching first (spell-change + weapon-class passives)
    spell_match = _match_template_passive(text)
    if spell_match and spell_match in known:
        return spell_match
    # Generic fuzzy match
    hits = difflib.get_close_matches(text, known, n=1, cutoff=cutoff)
    if not hits:
        return None
    matched = hits[0]
    # OCR sometimes reads "+1" as "+ 1" (space before digit) — normalize
    ocr_suffix   = re.search(r' \+\s*\d+$', text)
    match_suffix = re.search(r' \+\d+$', matched)
    ocr_s   = re.sub(r'\s', '', ocr_suffix.group())   if ocr_suffix   else ""
    match_s = re.sub(r'\s', '', match_suffix.group()) if match_suffix else ""
    if ocr_s != match_s:
        return None
    return matched


# ── Criteria checking ─────────────────────────────────────────────────── #

def _check_criteria(found: list, criteria: dict) -> tuple:
    """
    Check found passives against a structured criteria dict.
    Returns (match: bool, matched_passives: list, near_misses: list).

    The relic's passives (the "key") are tested against EVERY door.
    If multiple doors open, the one with the most matched passives wins.
    A 2-passive pool hit is never shadowed by a 1-passive target that
    happened to be listed first.
    """
    found_set = set(found)
    mode = criteria.get("mode", "exact")

    if mode == "exact":
        near_misses = []
        best_hits = []   # passives from the best-matching target
        for target in criteria.get("targets", []):
            required = [p for p in target.get("passives", []) if p]
            threshold = target.get("threshold", 2)
            if not required:
                continue
            hits = [p for p in required if p in found_set]
            if len(hits) >= threshold:
                # This door opened — keep it if it's better than what we have
                if len(hits) > len(best_hits):
                    best_hits = hits
            elif hits:
                near_misses.append({
                    "relic_name": "current relic",
                    "matching_passive_count": len(hits),
                    "matching_passives": hits,
                })
        if best_hits:
            return True, best_hits, []
        return False, [], near_misses

    if mode == "pool":
        entries = criteria.get("entries", [])
        # Backward compat: old format uses "passives" list
        if not entries and criteria.get("passives"):
            entries = [{"accepted": [p]} for p in criteria["passives"]]

        threshold = criteria.get("threshold", 2)
        matched, near_miss_passives = [], []

        # Individual pool entries — each counts if its passive is present
        for entry in entries:
            accepted = entry.get("accepted", [])
            hit = next((p for p in accepted if p in found_set), None)
            if hit:
                matched.append(hit)

        # Pairings — at least 2 of 3 slots (A, B, pool C) must be populated.
        # A present relic must satisfy ALL populated slots for the pairing to match.
        # Pool C requires at least one pool passive present on the relic.
        for pairing in criteria.get("pairings", []):
            left  = pairing.get("left",  [])
            right = pairing.get("right", [])
            pool  = pairing.get("pool",  [])
            has_a, has_b, has_c = bool(left), bool(right), bool(pool)
            left_hit  = next((p for p in left  if p in found_set), None) if has_a else None
            right_hit = next((p for p in right if p in found_set), None) if has_b else None
            pool_hit  = next((p for p in pool  if p in found_set), None) if has_c else None

            # Check if all populated slots are satisfied
            a_ok = (not has_a) or (left_hit  is not None)
            b_ok = (not has_b) or (right_hit is not None)
            c_ok = (not has_c) or (pool_hit  is not None)

            if a_ok and b_ok and c_ok:
                # Full match — build label from what's present
                parts = []
                if left_hit:
                    parts.append(left_hit)
                if right_hit:
                    parts.append(right_hit)
                if pool_hit:
                    parts.append(pool_hit)
                matched.append(" \u2194 ".join(parts))
            else:
                # Near miss — at least one populated slot hit but not all
                partial = []
                if left_hit:
                    partial.append(left_hit)
                if right_hit:
                    partial.append(right_hit)
                if pool_hit:
                    partial.append(pool_hit)
                if partial:
                    near_miss_passives.append(" \u2194 ".join(partial))

        if len(matched) >= threshold:
            return True, matched, []
        if matched or near_miss_passives:
            return False, [], [{
                "relic_name": "current relic",
                "matching_passive_count": len(matched),
                "matching_passives": matched,
            }]
        return False, [], []

    if mode == "combine":
        # Test ALL doors — exact targets AND pool — then keep the best.
        exact_m, exact_mp, exact_nm = _check_criteria(
            found, {**criteria.get("exact", {}), "mode": "exact"})
        pool_m, pool_mp, pool_nm = _check_criteria(
            found, {**criteria.get("pool", {}), "mode": "pool"})

        # Pick whichever door gave the most matched passives
        if exact_m and pool_m:
            if len(pool_mp) > len(exact_mp):
                return pool_m, pool_mp, pool_nm
            return exact_m, exact_mp, exact_nm
        if exact_m:
            return exact_m, exact_mp, exact_nm
        if pool_m:
            return pool_m, pool_mp, pool_nm
        # Neither matched — merge near misses from both
        return False, [], exact_nm + pool_nm

    return False, [], []


# ── Tab detection (Phase 3 smart navigation) ─────────────────────────── #

# ── Relic color detection ─────────────────────────────────────────────── #

# Keyword → color: every relic name contains exactly one of these words.
_COLOR_KEYWORDS = {
    "burning":  "Red",
    "drizzly":  "Blue",
    "tranquil": "Green",
    "luminous": "Yellow",
}


def _detect_relic_color(relic_name: str) -> str | None:
    """
    Detect relic color from its name.
    All relics contain a keyword that maps directly to a color:
      Burning → Red,  Drizzly → Blue,  Tranquil → Green,  Luminous → Yellow.
    Returns the color string, or None if no keyword is found.
    """
    name_lower = relic_name.lower()
    for keyword, color in _COLOR_KEYWORDS.items():
        if keyword in name_lower:
            return color
    return None


# ── Slot-based OCR pipeline ──────────────────────────────────────────── #

def _slot_readtext(reader, crop: np.ndarray):
    """Run reader.readtext() honoring the nav-isolation routing.

    Uses nav_ocr() when the calling thread set _thread_nav_mode.on (i.e.
    came in via analyze_for_nav), otherwise yields to pending nav OCR
    and acquires the GPU inflight lock just like the legacy analyze path.
    """
    if getattr(_thread_nav_mode, "on", False):
        return nav_ocr(crop)
    _wait_for_nav_yield()
    with _gpu_inflight_lock:
        return reader.readtext(crop)


def _crop_band(img: np.ndarray, y_center: float, half_height: float,
               x_start: float = _SLOT_X_START,
               x_end: float = _SLOT_X_END) -> np.ndarray:
    """Crop a horizontal band from a full-screen image using fractions."""
    h, w = img.shape[:2]
    x1 = int(w * x_start)
    x2 = int(w * x_end)
    y1 = max(0, int(h * (y_center - half_height)))
    y2 = min(h, int(h * (y_center + half_height)))
    return img[y1:y2, x1:x2]


def _cyan_text_mask(crop: np.ndarray) -> np.ndarray:
    """Boolean mask of pixels that match the curse-text cyan signature.

    Curse text in-game is light cyan: high G AND high B (so G ≈ B), with
    R noticeably lower.  Pure-blue UI elements (parchment icons, dialog
    border, relic crystal) have B much higher than G and fail the |G−B|
    test.  White passive text has R ≈ G ≈ B and fails the (G−R) test.
    Dark navy background fails the brightness test.

    This mask is the basis for both _has_curse_pixels (the curse-miss
    sniff helper) and _is_curse_text (the post-OCR token classifier).
    """
    r = crop[:, :, 0].astype(np.int16)
    g = crop[:, :, 1].astype(np.int16)
    b = crop[:, :, 2].astype(np.int16)
    return ((g > 140) & (b > 140) &        # bright (text-readable)
            (g - r > 30) & (b - r > 30) &  # not white
            (np.abs(g - b) < 40))           # cyan, not pure blue


def _enhance_curse_pixels(crop: np.ndarray) -> np.ndarray:
    """Convert cyan curse-text pixels to white for better OCR.

    Used as the EasyOCR input image so cyan curse text reads as cleanly
    as white passive text.  Token color classification (passive vs curse)
    still happens AFTER OCR by sampling the ORIGINAL crop at each
    token's Y.  Uses the same cyan signature as _cyan_text_mask so we
    only convert actual curse text, not pure-blue UI elements.
    """
    mask = _cyan_text_mask(crop)
    if mask.any():
        out = crop.copy()
        out[mask] = [255, 255, 255]
        return out
    return crop


def _is_curse_text(crop: np.ndarray) -> bool:
    """Check if a Y-strip contains curse-text cyan pixels (vs passive
    white text or no text at all).  Uses the cyan-specific mask so pure
    blue UI elements don't false-positive."""
    return int(_cyan_text_mask(crop).sum()) >= 8


def _has_curse_pixels(crop: np.ndarray, min_pixels: int = 25) -> bool:
    """Sniff helper for curse-miss capture: does the slot crop contain
    enough cyan-text pixels to plausibly contain an actual curse line?
    Cyan-specific so dormant power text, parchment icons, and dialog
    borders don't trigger.  Bumped from 15 to 25 px because the cyan
    mask is more selective (less risk of one-off pixel noise)."""
    return int(_cyan_text_mask(crop).sum()) >= min_pixels


# Passive-miss hook — fires when a token classified as passive (white text)
# couldn't be matched against the dictionary.  Lets app.py log dictionary
# gaps as OCR/passive_no_match failure events without coupling the
# OCR module to the diagnostic logger.
_passive_miss_hook = None   # callable(slot_idx, raw_text) -> None


def set_passive_miss_hook(fn) -> None:
    global _passive_miss_hook
    _passive_miss_hook = fn


# ── Curse miss debug capture ──────────────────────────────────────────── #
# When a slot has detectable blue pixels but no curse matched, we dump the
# RAW (un-enhanced) color crop as a PNG plus a sidecar with the raw OCR
# tokens.  Lets us iterate against actual failing screenshots from the
# laptop instead of guessing thresholds.

_curse_miss_dir: "str | None" = None
_curse_miss_lock = threading.Lock()
_curse_miss_count = 0
_curse_miss_max_per_run = 200   # safety cap so disk doesn't fill up
_curse_miss_hook = None         # callable(slot_idx, raw_text, dump_path) → None


def set_curse_miss_hook(fn) -> None:
    """app.py installs a callback so curse misses also flow into the
    DiagnosticLogger.  fn(slot_idx, raw_text, dump_path)."""
    global _curse_miss_hook
    _curse_miss_hook = fn


def set_curse_miss_dir(path: "str | None") -> None:
    """app.py calls this when a batch run starts.  Pass None to disable."""
    global _curse_miss_dir, _curse_miss_count
    with _curse_miss_lock:
        _curse_miss_dir = path
        _curse_miss_count = 0
        if path:
            try:
                import os as _os
                _os.makedirs(path, exist_ok=True)
            except Exception:
                pass


def _dump_curse_miss(crop: np.ndarray, slot_idx: int, raw_text: str,
                     tokens: list) -> "str | None":
    """Save raw crop + sidecar.  Returns the saved PNG path or None."""
    global _curse_miss_count
    with _curse_miss_lock:
        if not _curse_miss_dir:
            return None
        if _curse_miss_count >= _curse_miss_max_per_run:
            return None
        _curse_miss_count += 1
        idx = _curse_miss_count
    try:
        import os as _os
        import datetime as _dt
        ts = _dt.datetime.now().strftime("%H%M%S_%f")[:-3]
        base = f"{idx:03d}_slot{slot_idx}_{ts}"
        png_path = _os.path.join(_curse_miss_dir, base + ".png")
        txt_path = _os.path.join(_curse_miss_dir, base + ".txt")
        Image.fromarray(crop).save(png_path)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Slot index: {slot_idx}\n")
            f.write(f"Raw concatenated text: {raw_text!r}\n\n")
            f.write("Tokens:\n")
            for t in tokens:
                f.write(f"  conf={t.get('conf', 0):.2f}  "
                        f"y={int(t.get('y', -1)):4d}  "
                        f"text={t.get('text', '')!r}\n")
        return png_path
    except Exception:
        return None


def _ocr_slot(reader, crop: np.ndarray,
              all_passives: list, all_curses: list,
              slot_idx: int = -1) -> tuple:
    """OCR a single slot crop and return (passive, curse, dbg_tokens).

    Single readtext on _enhance_curse_pixels(crop), then post-token color
    classification by sampling the ORIGINAL crop at each token's Y.
    Reverted from the v1.7.1 two-pass mask approach because its absolute
    brightness thresholds killed passive OCR on the laptop.

    Returns:
        (passive_name or None, curse_name or None, list_of_dbg_token_dicts)
    """
    h, _w = crop.shape[:2]
    dbg = []

    enhanced = _enhance_curse_pixels(crop)
    results = _slot_readtext(reader, enhanced)
    if not results:
        return None, None, dbg

    tokens = []
    for bbox, text, conf in results:
        text = text.strip()
        if not bbox or len(text) < 2:
            continue
        y_center = (min(pt[1] for pt in bbox) + max(pt[1] for pt in bbox)) / 2
        x_center = (min(pt[0] for pt in bbox) + max(pt[0] for pt in bbox)) / 2
        tokens.append({"text": text, "conf": conf,
                        "y": y_center, "x": x_center})
    if not tokens:
        return None, None, dbg

    # Classify each token as passive vs curse by sampling the ORIGINAL
    # (un-enhanced) crop's bright pixel color at the token's Y strip.
    passive_tokens = []
    curse_tokens   = []
    for tok in tokens:
        y = int(tok["y"])
        y1 = max(0, y - 3)
        y2 = min(h, y + 3)
        if _is_curse_text(crop[y1:y2, :]):
            curse_tokens.append(tok)
        else:
            passive_tokens.append(tok)

    def _order(toks, row_gap=15):
        if not toks:
            return []
        ts = sorted(toks, key=lambda t: t["y"])
        rows = [[ts[0]]]
        for t in ts[1:]:
            if abs(t["y"] - rows[-1][-1]["y"]) <= row_gap:
                rows[-1].append(t)
            else:
                rows.append([t])
        out = []
        for row in rows:
            out.extend(sorted(row, key=lambda t: t["x"]))
        return out

    passive_name = None
    if passive_tokens:
        passive_text = " ".join(t["text"] for t in _order(passive_tokens))
        passive_name = _match_passive(passive_text, all_passives, cutoff=0.75)
        for t in passive_tokens:
            dbg.append({
                "text": t["text"], "conf": t["conf"], "y": int(t["y"]),
                "status": "PASSIVE" if passive_name else "MISS",
                "reason": "slot_ocr",
                "matched": passive_name,
            })
        # Passive miss capture: white text was OCR'd but the dictionary
        # couldn't find a match.  Fires for unknown passives, mangled
        # OCR, and any dictionary gaps in passives.py.
        if passive_name is None and _passive_miss_hook:
            try:
                _passive_miss_hook(slot_idx, passive_text)
            except Exception:
                pass

    curse_name = None
    if curse_tokens:
        curse_text = " ".join(t["text"] for t in _order(curse_tokens))
        curse_name = _match_passive(curse_text, all_curses, cutoff=0.75)
        for t in curse_tokens:
            dbg.append({
                "text": t["text"], "conf": t["conf"], "y": int(t["y"]),
                "status": "CURSE" if curse_name else "MISS",
                "reason": "slot_ocr",
                "matched": curse_name,
            })

    # Curse miss capture (TIGHTENED): only fire when OCR actually
    # classified tokens as curse-colored (cyan via _is_curse_text on
    # their y-strip) AND the dictionary couldn't match them.  No more
    # dumping for every slot with incidental blue pixels.
    if curse_tokens and curse_name is None:
        raw_text = " ".join(t["text"] for t in curse_tokens)
        _dump_path = _dump_curse_miss(crop, slot_idx, raw_text, curse_tokens)
        if _curse_miss_hook:
            try:
                _curse_miss_hook(slot_idx, raw_text, _dump_path or "")
            except Exception:
                pass

    return passive_name, curse_name, dbg


def _ocr_by_slots(img_full: np.ndarray, reader,
                   all_passives: list, all_curses: list,
                   relic_type: str = "") -> tuple:
    """Run slot-based OCR on a full screenshot.

    Crops each slot independently and OCRs them separately.
    No line reconstruction needed — each crop contains exactly one
    passive and optionally one curse.

    Args:
        img_full: Full screenshot as numpy array (RGB).
        reader: EasyOCR reader instance.
        all_passives: Sorted list of all known passive names.
        all_curses: List of all known curse names.
        relic_type: "night" to prepend "Deep " to the relic name.

    Returns:
        (relic_name, passives_list, curses_list, dbg_tokens_list)
    """
    # OCR the relic name
    name_crop = _crop_band(img_full, _NAME_Y_CENTER, _NAME_HALF_HEIGHT,
                            x_start=_NAME_X_START, x_end=_NAME_X_END)
    name_results = _slot_readtext(reader, name_crop)
    # Sort name tokens left-to-right by X position for correct word order
    _name_tokens = [(min(pt[0] for pt in bbox), t.strip())
                    for bbox, t, c in name_results if c > 0.3 and t.strip()]
    _name_tokens.sort(key=lambda x: x[0])
    relic_name = " ".join(t for _, t in _name_tokens).strip() or None

    # Prepend "Deep " for night mode relics (if not already in the OCR'd name)
    if relic_name and relic_type == "night" and "deep" not in relic_name.lower():
        relic_name = "Deep " + relic_name

    passives = []
    curses = []
    all_dbg = []

    # Name debug tokens
    for _, text, conf in name_results:
        all_dbg.append({
            "text": text.strip(), "conf": conf, "y": 0,
            "status": "NAME" if conf > 0.3 else "DROPPED",
            "reason": "name_slot",
            "matched": relic_name,
        })

    # OCR each passive slot
    for slot_idx, slot_center in enumerate(_SLOT_CENTERS):
        slot_crop = _crop_band(img_full, slot_center, _SLOT_HALF_HEIGHT)
        passive, curse, slot_dbg = _ocr_slot(
            reader, slot_crop, all_passives, all_curses, slot_idx=slot_idx)

        if passive and passive not in passives:
            passives.append(passive)
        if curse and curse not in curses:
            curses.append(curse)
        all_dbg.extend(slot_dbg)

    return relic_name, passives, curses, all_dbg


# ── Public API ────────────────────────────────────────────────────────── #

def analyze(
    image_bytes: bytes,
    criteria: dict,
    relic_type: str  = "",
    doors: "list[tuple] | None" = None,
) -> dict:
    """
    Analyze a relic screenshot and check if it matches the criteria.

    Args:
        image_bytes:  JPEG screenshot as bytes.
        criteria:     Structured dict from relic_builder.get_criteria_dict().
        doors:        Pre-computed door list from door_generator.generate_doors().
                      If provided, uses fast door matching instead of runtime
                      criteria evaluation.

    Returns:
        dict with keys: relics_found, match, matched_relic, matched_passives,
                        matched_relic_curses, near_misses, reason,
                        _ocr_tokens (raw OCR debug data — list of token dicts).
    """
    from bot.passives import ALL_PASSIVES_SORTED, ALL_CURSES

    reader = _get_reader()
    img = _to_array(image_bytes, max_width=0)   # full resolution — we crop first, then scale

    # ── Slot-based OCR ────────────────────────────────────────────────── #
    relic_name, passives, curses, _dbg_tokens = _ocr_by_slots(
        img, reader, ALL_PASSIVES_SORTED, ALL_CURSES, relic_type)

    # Color detection
    allowed_colors = criteria.get("allowed_colors", [])
    if allowed_colors and len(allowed_colors) < 4:
        relic_color = _detect_relic_color(relic_name or "")
        if relic_color and relic_color not in allowed_colors:
            return {
                "relics_found": [{"name": relic_name, "passives": passives, "curses": curses}],
                "match": False,
                "matched_relic": None,
                "matched_passives": [],
                "matched_relic_curses": [],
                "near_misses": [],
                "reason": f"Relic color '{relic_color}' not in allowed colors",
                "_ocr_tokens": _dbg_tokens,
            }

    # Criteria matching
    if doors is not None:
        from bot.door_generator import check_doors
        match, matched_passives, near_misses = check_doors(passives, doors)
    else:
        match, matched_passives, near_misses = _check_criteria(passives, criteria)
    for _nm in near_misses:
        if _nm.get("relic_name") == "current relic" and relic_name:
            _nm["relic_name"] = relic_name

    return {
        "relics_found": [{"name": relic_name, "passives": passives, "curses": curses}],
        "match": match,
        "matched_relic": relic_name if match else None,
        "matched_passives": matched_passives,
        "matched_relic_curses": curses if match else [],
        "near_misses": near_misses,
        "reason": (
            f"Found {len(matched_passives)} matching passive(s)"
            if match else
            f"No match — {len(passives)} passive(s) detected"
        ),
        "_ocr_tokens": _dbg_tokens,
    }


def analyze_for_nav(
    image_bytes: bytes,
    criteria: dict,
    relic_type: str  = "",
    doors: "list[tuple] | None" = None,
) -> dict:
    """analyze() variant routed through nav_ocr for main-thread callers.

    Sets a thread-local flag so the readtext calls inside analyze()
    dispatch via the navigator path (GPU priority gate or dedicated CPU
    nav thread) instead of the normal analysis path.
    """
    _thread_nav_mode.on = True
    try:
        return analyze(
            image_bytes, criteria,
            relic_type=relic_type, doors=doors,
        )
    finally:
        _thread_nav_mode.on = False


def _preprocess_for_ocr(img: np.ndarray) -> np.ndarray:
    """Boost contrast and convert to grayscale to help OCR read HUD numbers."""
    from PIL import Image as _Image, ImageEnhance as _Enhance, ImageFilter as _Filter
    pil = _Image.fromarray(img)
    pil = pil.convert("L")                         # grayscale
    pil = _Enhance.Contrast(pil).enhance(2.5)      # punch contrast
    pil = pil.filter(_Filter.SHARPEN)              # sharpen edges
    return np.array(pil.convert("RGB"))


# Normalised crop region for the shop murk counter.
# The counter lives in the top-left of the shop UI — roughly the top 18 % of
# screen height and left 45 % of screen width.  Using fractions makes this
# resolution-independent (works identically at 1080p, 1440p, etc.).
# All other screens (in-game HUD, Relic Rites sell page, Collector Signboard)
# place the murk counter in completely different regions, so restricting the
# scan to this zone also acts as an implicit shop-screen filter.
MURK_SHOP_REGION = (0.0, 0.0, 0.45, 0.18)


def read_murk(image_bytes: bytes,
              region: tuple | None = None) -> tuple[int, tuple]:
    """
    Read the murk (currency) amount from the shop screen.

    region : (x1, y1, x2, y2) as fractions of the full image dimensions.
             Defaults to MURK_SHOP_REGION if None.

    Returns (murk_value, region_used).
    murk_value is 0 when the counter cannot be read confidently.
    region_used is always the normalised crop that was actually scanned —
    callers can save it and pass it back on subsequent calls to guarantee the
    same pixels are examined every time.
    """
    if region is None:
        region = MURK_SHOP_REGION

    img = _to_array(image_bytes, max_width=0)   # full resolution — murk digits are small

    h, w = img.shape[:2]
    x1 = int(w * region[0])
    y1 = int(h * region[1])
    x2 = int(w * region[2])
    y2 = int(h * region[3])
    roi_raw  = img[y1:y2, x1:x2]
    roi_proc = _preprocess_for_ocr(roi_raw)

    candidates = []

    def _extract(results):
        for _, text, conf in results:
            if conf < 0.45:
                continue
            clean = text.replace(",", "").replace(".", "").replace(" ", "")
            for n in re.findall(r"\d+", clean):
                val = int(n)
                if 1 <= val <= 9_999_999:
                    candidates.append((conf, val))

    _extract(nav_ocr(roi_raw))
    if not candidates:
        _extract(nav_ocr(roi_proc))

    if not candidates:
        return 0, region

    # Largest value wins; ties broken by confidence.
    candidates.sort(key=lambda x: (x[1], x[0]), reverse=True)
    return candidates[0][1], region


def check_text_visible(image_bytes: bytes, text: str, top_fraction: float = 0.50) -> bool:
    """
    Check if text appears anywhere in the top portion of the screen.
    Scans the full width so tab-bar labels at any horizontal position are found.
    Used for Equipment menu detection during ESC recovery.

    Pass a top_fraction appropriate to where the text sits on screen
    (e.g. 0.15 for "small jar bazaar" near the top, 0.15 for equipment tabs).
    Downscaling to _MAX_OCR_WIDTH gives ~2-3× speedup; the region must be at
    least 50 px tall after downscaling to keep text legible.
    """
    img = _to_array(image_bytes, max_width=0)
    h, w = img.shape[:2]
    scan_region = img[:max(1, int(h * top_fraction)), :]
    _rh, _rw = scan_region.shape[:2]
    if _rw > _MAX_OCR_WIDTH:
        _scale = _MAX_OCR_WIDTH / _rw
        _new_h = max(1, int(_rh * _scale))
        if _new_h >= 50:   # skip downscale if result would be too short for OCR
            scan_region = np.array(
                Image.fromarray(scan_region).resize(
                    (_MAX_OCR_WIDTH, _new_h), Image.LANCZOS,
                )
            )
    results = nav_ocr(scan_region)
    all_text = " ".join(t for _, t, c in results if c > 0.3).lower()
    return text.lower() in all_text


def verify_shop_item(image_bytes: bytes, relic_type: str) -> tuple:
    """
    Confirm the highlighted shop item is the correct relic before Phase 1 runs.

    The tooltip panel sits in the horizontal middle third of the shop screen
    (approximately 33 %–67 % of width, top 65 % of height).  OCR-ing only
    that region avoids interference from the item grid on the left and the
    character model on the right.

    Checks:
      1. Correct item name is present in the tooltip.
           night  → "Deep Scenic Flatstone"
           normal → "Scenic Flatstone" (not the Deep variant)
      2. Old-version marker is absent ("1.02" from the N.B. note that reads
         "Yields items from up to ver. 1.02 of the game.").

    Returns:
        (True,  "OK")         correct relic, no old-version marker.
        (False, reason_str)   wrong item, old-version relic, or inconclusive.
    """
    img = _to_array(image_bytes, max_width=0)
    h, w = img.shape[:2]

    # Middle horizontal third, top 65 % — isolates the tooltip panel.
    roi = img[:int(h * 0.65), int(w * 0.33):int(w * 0.67)]

    # Downscale ROI before OCR — this region is portrait-oriented (~870×936 px
    # at 1440p) and EasyOCR's CRAFT pass scales with pixel count.  Cap the
    # longest dimension to 600 px to keep OCR fast without losing legibility
    # on large title / description text.
    _MAX_VERIFY_DIM = 600
    _rh, _rw = roi.shape[:2]
    _long = max(_rh, _rw)
    if _long > _MAX_VERIFY_DIM:
        _sc = _MAX_VERIFY_DIM / _long
        roi = np.array(
            Image.fromarray(roi).resize(
                (max(1, int(_rw * _sc)), max(1, int(_rh * _sc))), Image.LANCZOS
            )
        )

    results = nav_ocr(roi)
    # Low-confidence threshold — short words and small description text can
    # score below 0.25 in stylised game fonts; 0.05 keeps sensitivity high.
    all_text_lo = " ".join(t for _, t, c in results if c > 0.05).lower()

    def _lx(bbox): return min(pt[0] for pt in bbox)
    def _ty(bbox): return min(pt[1] for pt in bbox)

    # ── Item name check then old-version check ─────────────────────────── #
    # EasyOCR splits "Deep Scenic Flatstone" into separate tokens: a "Deep"
    # token and a "Scenic Flatstone" token.  We confirm the deep variant by
    # checking that a "deep"-containing token sits to the LEFT of (or at the
    # same x as) the "Scenic Flatstone" token at the same y-level (≤40 px
    # apart) — i.e. they are on the same title line.  The description also
    # contains "Deep" for the deep variant but ~160 px lower, so the y-
    # tolerance filter excludes it and prevents false positives in normal mode.

    # Find the first "Scenic Flatstone" title token.
    _scenic_bbox = None
    for _bbox, _txt, _c in results:
        if "scenic flatstone" in _txt.lower() and _c > 0.05:
            _scenic_bbox = _bbox
            break

    _has_scenic = _scenic_bbox is not None

    # Confirm "Deep" is present immediately to the left on the title line.
    _has_deep_scenic = False
    if _has_scenic:
        _s_lx, _s_ty = _lx(_scenic_bbox), _ty(_scenic_bbox)
        for _bbox, _txt, _c in results:
            if "deep" in _txt.lower() and _c > 0.05:
                _d_lx, _d_ty = _lx(_bbox), _ty(_bbox)
                if _d_lx <= _s_lx and abs(_d_ty - _s_ty) <= 40:
                    _has_deep_scenic = True
                    break

    _has_old_version = "1.02" in all_text_lo

    if relic_type == "night":
        if _has_deep_scenic:
            if _has_old_version:
                return False, "Old-version Deep Scenic Flatstone ('1.02' in description)"
            return True, "OK"
        if _has_scenic:
            return False, "Normal relic (Scenic Flatstone) highlighted but night mode is active"
        return False, "'Deep Scenic Flatstone' not found in tooltip — inconclusive OCR"
    else:
        # Normal mode: Scenic Flatstone (not Deep variant)
        if _has_deep_scenic:
            return False, "Night relic (Deep Scenic Flatstone) highlighted but normal mode is active"
        if _has_scenic:
            if _has_old_version:
                return False, "Old-version Scenic Flatstone ('1.02' in description)"
            return True, "OK"
        return False, "'Scenic Flatstone' not found in tooltip — inconclusive OCR"


