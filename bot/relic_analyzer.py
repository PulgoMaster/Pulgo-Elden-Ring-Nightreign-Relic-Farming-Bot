"""
Analyzes relic screenshots using local OCR (EasyOCR).
Runs entirely on-device — no internet connection or account required.

First run: EasyOCR downloads its English model (~100 MB) automatically.
After that the bot works fully offline with no ongoing costs.
"""

import io
import re
import difflib
import threading

import numpy as np
from PIL import Image


# ── EasyOCR reader — one instance per thread ─────────────────────────── #
#
# EasyOCR is not thread-safe when sharing a single Reader instance.
# Using threading.local() gives each thread its own Reader so that
# multiple worker threads can run OCR in parallel without interfering.
# The model is loaded lazily on the first call from each thread (~2-3 s
# one-time cost; subsequent calls on the same thread are instant).

_thread_local        = threading.local()
_thread_device_local = threading.local()   # per-thread GPU override (True/False/None)
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

def _match_passive(text: str, known: list, cutoff: float = 0.82) -> str | None:
    """
    Return the closest known passive name, or None if below cutoff.

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
    hits = difflib.get_close_matches(text, known, n=1, cutoff=cutoff)
    if not hits:
        return None
    matched = hits[0]
    ocr_suffix   = re.search(r' \+\d+$', text)
    match_suffix = re.search(r' \+\d+$', matched)
    ocr_s   = ocr_suffix.group()   if ocr_suffix   else ""
    match_s = match_suffix.group() if match_suffix else ""
    if ocr_s != match_s:
        return None
    return matched


# ── Criteria checking ─────────────────────────────────────────────────── #

def _check_criteria(found: list, criteria: dict) -> tuple:
    """
    Check found passives against a structured criteria dict.
    Returns (match: bool, matched_passives: list, near_misses: list).
    """
    found_set = set(found)
    mode = criteria.get("mode", "exact")

    if mode == "exact":
        near_misses = []
        for target in criteria.get("targets", []):
            required = [p for p in target.get("passives", []) if p]
            threshold = target.get("threshold", 2)
            if not required:
                continue
            hits = [p for p in required if p in found_set]
            if len(hits) >= threshold:
                return True, hits, []
            if hits:
                near_misses.append({
                    "relic_name": "current relic",
                    "matching_passive_count": len(hits),
                    "matching_passives": hits,
                })
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
        m, mp, nm = _check_criteria(found, {**criteria.get("exact", {}), "mode": "exact"})
        if m:
            return m, mp, nm
        return _check_criteria(found, {**criteria.get("pool", {}), "mode": "pool"})

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


# ── Public API ────────────────────────────────────────────────────────── #

def analyze(
    image_bytes: bytes,
    criteria: dict,
    crop_left: float = _CROP_LEFT_FRAC,
    crop_top: float  = _CROP_TOP_FRAC,
    relic_type: str  = "",
) -> dict:
    """
    Analyze a relic screenshot and check if it matches the criteria.

    Args:
        image_bytes:  JPEG screenshot as bytes.
        criteria:     Structured dict from relic_builder.get_criteria_dict().
        crop_left:    Fraction of image width  to skip from the left (default:
                      sell-screen crop).  Pass _PREVIEW_CROP_LEFT_FRAC for the
                      bazaar post-buy preview screen.
        crop_top:     Fraction of image height to skip from the top (default:
                      sell-screen crop).  Pass _PREVIEW_CROP_TOP_FRAC for the
                      bazaar post-buy preview screen.

    Returns:
        dict with keys: relics_found, match, matched_relic, matched_passives,
                        matched_relic_curses, near_misses, reason,
                        _ocr_tokens (raw OCR debug data — list of token dicts).
    """
    from bot.passives import ALL_PASSIVES_SORTED, ALL_CURSES

    reader = _get_reader()
    img = _to_array(image_bytes, max_width=0)   # full resolution — we crop first, then scale

    # Crop to the relic info panel. Fraction-based so it scales correctly for
    # any resolution. Caller supplies the right fractions for the screen type.
    h, w = img.shape[:2]
    left = int(w * crop_left)
    top  = int(h * crop_top)
    img  = img[top:, left:]

    # Downscale the cropped region to _MAX_OCR_WIDTH if wider.
    # OCR time scales roughly with pixel count; capping at 1000 px gives a
    # 2-3× speed improvement on 1440p/4K without affecting accuracy (relic
    # name and passive text remain well above the minimum legible size).
    _ch, _cw = img.shape[:2]
    if _cw > _MAX_OCR_WIDTH:
        _scale = _MAX_OCR_WIDTH / _cw
        img = np.array(
            Image.fromarray(img).resize(
                (_MAX_OCR_WIDTH, max(1, int(_ch * _scale))),
                Image.LANCZOS,
            )
        )

    # ── Curse text enhancement ────────────────────────────────────────── #
    # Curse text renders as light-blue in-game (B significantly dominates R).
    # EasyOCR assigns lower confidence to blue-tinted text vs white text.
    # Pre-processing: convert blue-dominant, non-dark pixels to white so the
    # OCR engine treats curse lines the same as passive lines.
    # White passive/name text is unaffected (R≈G≈B → B-R ≈ 0 ≤ threshold).
    # Dark panel backgrounds are unaffected (B < 110).
    _b_ch = img[:, :, 2].astype(np.int16)
    _r_ch = img[:, :, 0].astype(np.int16)
    _curse_px_mask = (_b_ch - _r_ch > 45) & (_b_ch > 110)
    if _curse_px_mask.any():
        _ocr_img = img.copy()
        _ocr_img[_curse_px_mask] = [255, 255, 255]
    else:
        _ocr_img = img

    results = reader.readtext(_ocr_img)

    passives, curses = [], []
    relic_name = None

    # Always collect raw OCR tokens for diagnostic logging via DiagnosticLogger.
    _dbg_tokens: list[dict] = []
    # Tokens dropped for low confidence — retried against ALL_CURSES after the
    # main pass since curse text can still be readable at conf < 0.35.
    _low_conf_tokens: list[tuple] = []

    for bbox, text, conf in results:
        _text = text.strip()
        # Compute bbox top-left Y (relative to crop, for ordering context)
        _y = int(min(pt[1] for pt in bbox)) if bbox else -1

        if len(_text) < 3:
            _dbg_tokens.append({
                "text": _text, "conf": conf, "y": _y,
                "status": "DROPPED",
                "reason": "too_short",
                "matched": None,
            })
            continue

        if conf < 0.35:
            # Low confidence — keep for curse-rescue pass below.
            _low_conf_tokens.append((_text, conf, _y))
            _dbg_tokens.append({
                "text": _text, "conf": conf, "y": _y,
                "status": "DROPPED",
                "reason": "conf<0.35",
                "matched": None,
            })
            continue

        # Try matching as a known passive first, then as a known curse.
        # Curses render as light-blue text (smaller, below the passive line).
        # Color-based classification is not used — matching against dedicated
        # ALL_CURSES list is the reliable approach since confidence varies.
        matched_passive = _match_passive(_text, ALL_PASSIVES_SORTED)
        if matched_passive:
            if matched_passive not in passives:
                passives.append(matched_passive)
            _dbg_tokens.append({
                "text": _text, "conf": conf, "y": _y,
                "status": "PASSIVE",
                "reason": None,
                "matched": matched_passive,
            })
        else:
            matched_curse = _match_passive(_text, ALL_CURSES)
            if matched_curse:
                if matched_curse not in curses:
                    curses.append(matched_curse)
                _dbg_tokens.append({
                    "text": _text, "conf": conf, "y": _y,
                    "status": "CURSE",
                    "reason": None,
                    "matched": matched_curse,
                })
            elif relic_name is None and conf > 0.55 \
                    and _text and not _text[0].isdigit():
                relic_name = _text
                _dbg_tokens.append({
                    "text": _text, "conf": conf, "y": _y,
                    "status": "RELIC_NAME",
                    "reason": None,
                    "matched": _text,
                })
            else:
                _dbg_tokens.append({
                    "text": _text, "conf": conf, "y": _y,
                    "status": "NO_MATCH",
                    "reason": None,
                    "matched": None,
                })

    # ── Token-merge pass ─────────────────────────────────────────────────── #
    # Long passive names (e.g. "Changes compatible armament's incantation
    # to Lightning Spear at start of expedition") may be split by EasyOCR
    # into 2+ tokens that individually don't match anything.  Merge
    # adjacent unmatched tokens (sorted by Y position) and retry.
    _unmatched = [(d["text"], d["y"]) for d in _dbg_tokens
                  if d["status"] == "NO_MATCH" and len(d["text"]) >= 5]
    _unmatched.sort(key=lambda x: x[1])   # sort by Y so adjacent lines merge
    for i in range(len(_unmatched)):
        for j in range(i + 1, min(i + 3, len(_unmatched))):  # try 2-3 token combos
            merged = _unmatched[i][0] + " " + " ".join(
                _unmatched[k][0] for k in range(i + 1, j + 1))
            merged_match = _match_passive(merged, ALL_PASSIVES_SORTED, cutoff=0.80)
            if merged_match and merged_match not in passives:
                passives.append(merged_match)
                # Mark the merged tokens in diagnostics
                for k in range(i, j + 1):
                    for _dt in _dbg_tokens:
                        if _dt["text"] == _unmatched[k][0] and _dt["status"] == "NO_MATCH":
                            _dt["status"] = "PASSIVE"
                            _dt["reason"] = "token_merge"
                            _dt["matched"] = merged_match
                            break
                break  # stop extending this merge, move to next starting token

    # ── Passive-rescue pass ──────────────────────────────────────────────── #
    # Retry low-confidence tokens against ALL_PASSIVES_SORTED.  Motivated by
    # Delicate relics (1 passive): the single passive line can land at the top
    # of the cropped region with slightly reduced contrast, pushing its OCR
    # confidence below the 0.35 floor even though the text is correct.  A
    # lower fuzzy cutoff (0.78) recovers these while staying well above random-
    # noise.  Tokens already matched as passives or with conf < 0.05 are skipped.
    for _lct, _lcc, _lcy in _low_conf_tokens:
        if _lcc < 0.05 or _lct in passives:
            continue
        _rescue_passive = _match_passive(_lct, ALL_PASSIVES_SORTED, cutoff=0.78)
        if _rescue_passive and _rescue_passive not in passives:
            passives.append(_rescue_passive)
            for _dt in reversed(_dbg_tokens):
                if _dt["text"] == _lct and _dt["status"] == "DROPPED":
                    _dt["status"]  = "PASSIVE"
                    _dt["reason"]  = "low_conf_rescue"
                    _dt["matched"] = _rescue_passive
                    break

    # ── Curse-rescue pass ────────────────────────────────────────────────── #
    # Retry low-confidence tokens against ALL_CURSES only.  The 0.82 fuzzy
    # similarity threshold inside _match_passive is still the real gate;
    # we only bypass the OCR-confidence floor because curse text (light-blue,
    # smaller font) inherently scores lower than white passive/name text.
    # Tokens with conf < 0.10 are still treated as garbage and skipped.
    for _lct, _lcc, _lcy in _low_conf_tokens:
        if _lcc < 0.05 or _lct in curses:
            continue
        # Lower similarity cutoff (0.75 vs default 0.82): low-conf curse tokens
        # are often OCR-mangled enough that 0.82 rejects correct matches.
        # 0.75 recovers those while remaining well above random-noise territory
        # (tested against all 24 known curses — no cross-passive false matches).
        _rescue_curse = _match_passive(_lct, ALL_CURSES, cutoff=0.75)
        if _rescue_curse and _rescue_curse not in curses:
            curses.append(_rescue_curse)
            # Patch the already-appended DROPPED token so diag shows the outcome.
            for _dt in reversed(_dbg_tokens):
                if _dt["text"] == _lct and _dt["status"] == "DROPPED":
                    _dt["status"]  = "CURSE"
                    _dt["reason"]  = "low_conf_rescue"
                    _dt["matched"] = _rescue_curse
                    break

    relic_name = relic_name or "Unknown Relic"

    # Prepend "Deep " when scanning Deep of Night relics (relic_type="night")
    # and the name wasn't already captured with the prefix.
    if (relic_type == "night"
            and relic_name != "Unknown Relic"
            and not relic_name.startswith("Deep ")):
        relic_name = "Deep " + relic_name

    # ── Color detection (best-effort) ───────────────────────────────────── #
    allowed_colors = criteria.get("allowed_colors", [])
    if allowed_colors and len(allowed_colors) < 4:  # if all 4 enabled, skip check
        relic_color = _detect_relic_color(relic_name)
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

    match, matched_passives, near_misses = _check_criteria(passives, criteria)
    # Patch near-miss records with the actual relic name (criteria checker
    # uses a placeholder because it doesn't receive the name).
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

    reader = _get_reader()
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

    _extract(reader.readtext(roi_raw))
    if not candidates:
        _extract(reader.readtext(roi_proc))

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
    reader = _get_reader()
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
    results = reader.readtext(scan_region)
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
    reader = _get_reader()
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

    results = reader.readtext(roi)
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


