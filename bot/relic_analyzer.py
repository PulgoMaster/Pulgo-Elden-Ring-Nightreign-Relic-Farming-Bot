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

_thread_local   = threading.local()
_torch_threads  = 1   # set via configure_torch_threads() before workers start


def configure_torch_threads(n: int) -> None:
    """Set PyTorch's per-inference CPU thread count for all subsequent calls.

    With multiple workers each defaulting to all available cores, threads
    fight each other (oversubscription).  Setting this to cpu_cores/workers
    distributes cores evenly so workers run in parallel without contention.
    Call once from the main thread before spawning async workers.
    """
    global _torch_threads
    _torch_threads = max(1, n)
    try:
        import torch
        torch.set_num_threads(_torch_threads)
    except Exception:
        pass


def _get_reader():
    """Return the EasyOCR reader for the calling thread, loading it if needed."""
    if not hasattr(_thread_local, "reader"):
        try:
            import torch
            torch.set_num_threads(_torch_threads)
        except Exception:
            pass
        import easyocr
        _thread_local.reader = easyocr.Reader(["en"], gpu=False, verbose=False)
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


def _to_array(image_bytes: bytes, max_width: int = 0) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if max_width and img.width > max_width:
        scale = max_width / img.width
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.LANCZOS,
        )
    return np.array(img)


# ── Color classification ──────────────────────────────────────────────── #

def _classify_color(img: np.ndarray, bbox) -> str:
    """
    Sample pixels inside an EasyOCR bounding box and classify as
    'passive' (white-ish text) or 'curse' (blue-ish text).
    Background pixels (dark) are ignored — only bright pixels are sampled.
    """
    pts = np.array(bbox, dtype=int)
    x0, y0 = pts[:, 0].min(), pts[:, 1].min()
    x1, y1 = pts[:, 0].max(), pts[:, 1].max()

    h, w = img.shape[:2]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)

    region = img[y0:y1, x0:x1].reshape(-1, 3).astype(float)
    if len(region) == 0:
        return "unknown"

    # Only consider non-dark pixels (text, not background)
    bright = region[region.max(axis=1) > 140]
    if len(bright) == 0:
        return "unknown"

    r, g, b = bright.mean(axis=0)

    # White/grey: all channels high and roughly equal
    if r > 160 and g > 160 and b > 160 and abs(r - b) < 60:
        return "passive"

    # Blue/cyan: blue channel clearly dominates
    if b > 140 and b > r + 40:
        return "curse"

    return "unknown"


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

        # Pairings — both sides must be present; counts as 1 match
        for pairing in criteria.get("pairings", []):
            left_hit  = next((p for p in pairing.get("left",  []) if p in found_set), None)
            right_hit = next((p for p in pairing.get("right", []) if p in found_set), None)
            if left_hit and right_hit:
                matched.append(f"{left_hit} \u2194 {right_hit}")
            elif left_hit or right_hit:
                near_miss_passives.append(left_hit or right_hit)

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

_TAB_HIERARCHY = [
    "Wylder", "Guardian", "Ironeye", "Duchess", "Raider",
    "Revenant", "Recluse", "Executor", "Scholar", "Undertaker", "Sell",
]
# How many F2 presses are needed from each tab to reach Sell
_TAB_F2_COUNT = {name: (len(_TAB_HIERARCHY) - 1 - i) for i, name in enumerate(_TAB_HIERARCHY)}
# Wylder→10, Guardian→9, Ironeye→8, Duchess→7, Raider→6,
# Revenant→5, Recluse→4, Executor→3, Scholar→2, Undertaker→1, Sell→0


def detect_current_tab(image_bytes: bytes) -> tuple:
    """
    Detect which Relic Rites tab is currently active.

    Strategy 1 (primary): OCR the upper 50 % of the screen and look for
    character name text.  The active tab renders its name prominently in
    the content area, so a direct text match is more reliable than measuring
    tab-label brightness.

    Strategy 2 (fallback): Among OCR results that fall inside the tab bar
    region (top ~14 %), score each detected name by the average brightness of
    its bounding box.  The selected tab label is noticeably brighter; winner
    must be ≥ 15 units brighter than the runner-up.

    A single readtext() call covers both strategies — results are filtered
    by position for strategy 2 rather than re-scanning.

    Returns:
        (tab_name, f2_presses_needed)  e.g. ("Guardian", 9)
        (None, None)                   if detection is inconclusive — callers
                                       should press F2 × 1 to shift position
                                       and re-detect on the next cycle
    """
    reader = _get_reader()
    img = _to_array(image_bytes, max_width=0)
    h, w = img.shape[:2]
    tab_bar_h = int(h * 0.14)

    # OCR the upper 50 % — covers both the tab bar and the main content header
    scan_h = int(h * 0.50)
    scan_region = img[:scan_h, :]
    results = reader.readtext(scan_region)

    # ── Strategy 1: direct character name text matching ───────────────── #
    # Collect (confidence, y_center, tab_name) for every OCR hit that
    # contains a tab name.  Prefer higher confidence; break ties by proximity
    # to the top of the screen (tab bar area).
    name_candidates: list = []
    for bbox, text, conf in results:
        if conf < 0.30:
            continue
        text_clean = text.strip()
        for tab in _TAB_HIERARCHY:
            if tab.lower() in text_clean.lower():
                pts = np.array(bbox, dtype=int)
                y_center = (int(pts[:, 1].min()) + int(pts[:, 1].max())) / 2
                name_candidates.append((conf, y_center, tab))
                break

    if name_candidates:
        # Sort: highest confidence first; for equal confidence, closest to top
        name_candidates.sort(key=lambda x: (-x[0], x[1]))
        best_conf, _best_y, best_tab = name_candidates[0]
        if best_conf >= 0.45:
            return best_tab, _TAB_F2_COUNT[best_tab]

    # ── Strategy 2: tab-bar brightness scoring ────────────────────────── #
    # Reuse the same readtext() results; only consider bounding boxes that
    # sit inside the tab bar strip (top 14 % of the original image).
    brightness_candidates: list = []
    for bbox, text, conf in results:
        if conf < 0.25:
            continue
        pts = np.array(bbox, dtype=int)
        y0_bbox = int(pts[:, 1].min())
        if y0_bbox > tab_bar_h:
            continue  # outside the tab bar — skip for brightness scoring
        text_clean = text.strip()
        for tab in _TAB_HIERARCHY:
            if tab.lower() in text_clean.lower():
                x0 = max(0, int(pts[:, 0].min()))
                y0 = max(0, y0_bbox)
                x1 = min(w,          int(pts[:, 0].max()))
                y1 = min(tab_bar_h,  int(pts[:, 1].max()))
                region = scan_region[y0:y1, x0:x1]
                if region.size == 0:
                    break
                brightness = float(region.mean())
                brightness_candidates.append((brightness, tab))
                break

    if brightness_candidates:
        brightness_candidates.sort(reverse=True)
        best_brightness, best_tab = brightness_candidates[0]
        if len(brightness_candidates) < 2 or brightness_candidates[0][0] - brightness_candidates[1][0] >= 15:
            return best_tab, _TAB_F2_COUNT[best_tab]

    return None, None  # nothing conclusive — caller presses F2 × 1 and re-detects


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

def analyze(image_bytes: bytes, criteria: dict) -> dict:
    """
    Analyze a relic screenshot and check if it matches the criteria.

    Args:
        image_bytes:  JPEG screenshot as bytes.
        criteria:     Structured dict from relic_builder.get_criteria_dict().

    Returns:
        dict with keys: relics_found, match, matched_relic, matched_passives,
                        matched_relic_curses, near_misses, reason
    """
    from bot.passives import ALL_PASSIVES_SORTED

    reader = _get_reader()
    img = _to_array(image_bytes, max_width=0)   # full resolution — we crop, not downscale

    # Crop to the relic info panel (bottom-right quadrant of the sell screen).
    # Fraction-based so it scales correctly for any resolution.
    h, w = img.shape[:2]
    left = int(w * _CROP_LEFT_FRAC)
    top  = int(h * _CROP_TOP_FRAC)
    img  = img[top:, left:]

    results = reader.readtext(img)

    passives, curses = [], []
    relic_name = None

    for bbox, text, conf in results:
        if conf < 0.35 or len(text.strip()) < 3:
            continue

        color = _classify_color(img, bbox)
        matched = _match_passive(text, ALL_PASSIVES_SORTED)

        if matched:
            if color == "curse":
                if matched not in curses:
                    curses.append(matched)
            else:
                if matched not in passives:
                    passives.append(matched)
        elif relic_name is None and conf > 0.55 and color != "curse" \
                and not text.strip()[0].isdigit():
            relic_name = text.strip()

    relic_name = relic_name or "Unknown Relic"

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
            }

    match, matched_passives, near_misses = _check_criteria(passives, criteria)

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
    """
    reader = _get_reader()
    img = _to_array(image_bytes, max_width=0)
    h = img.shape[0]
    scan_region = img[:int(h * top_fraction), :]
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


def check_condition(image_bytes: bytes, condition_text: str) -> bool:
    """
    Check whether the given text is visible anywhere on screen using OCR.
    Returns True if found, False otherwise.

    Uses a downscaled crop of the top half of the screen — UI labels like
    "Sell" appear there and the smaller image makes each OCR call ~2-3 s
    faster than scanning the full frame.
    """
    reader = _get_reader()
    img = _to_array(image_bytes, max_width=0)       # full resolution — keep OCR reliable
    h, w = img.shape[:2]
    img = img[: int(h * 0.30), : int(w * 0.65)]   # top-left corner — "Sell" label lives here
    results = reader.readtext(img)

    all_text = " ".join(t for _, t, c in results if c > 0.3).lower()
    condition_lower = condition_text.lower()

    if condition_lower in all_text:
        return True

    # Fuzzy fallback: accept if most words of the condition are present.
    words = condition_lower.split()
    matched = sum(1 for w in words if w in all_text)
    return matched >= max(1, len(words) * 0.6)
