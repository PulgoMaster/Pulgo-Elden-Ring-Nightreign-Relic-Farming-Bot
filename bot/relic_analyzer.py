"""
Analyzes relic screenshots using local OCR (EasyOCR).
Runs entirely on-device — no internet connection or account required.

First run: EasyOCR downloads its English model (~100 MB) automatically.
After that the bot works fully offline with no ongoing costs.
"""

import io
import re
import difflib

import numpy as np
from PIL import Image


# ── EasyOCR reader singleton ──────────────────────────────────────────── #

_reader = None


def _get_reader():
    """Lazy-load the EasyOCR reader (downloads model on first call)."""
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _reader


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
        elif relic_name is None and conf > 0.55 and color != "curse":
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


def read_murk(image_bytes: bytes) -> int:
    """
    Read the murk (currency) amount from the screen using OCR.
    Returns 0 if the amount cannot be reliably determined.
    """
    reader = _get_reader()
    img = _to_array(image_bytes, max_width=0)   # full resolution — murk digits are small

    # Try top-right quarter first — that's where the HUD currency typically sits.
    h, w = img.shape[:2]
    roi = img[0: h // 3, w // 2:]
    results = reader.readtext(roi)

    candidates = []
    for _, text, conf in results:
        for n in re.findall(r"\d+", text.replace(",", "").replace(".", "")):
            val = int(n)
            if val > 0:
                candidates.append((conf, val))

    if not candidates:
        # Fall back to the full image and require a plausible murk range.
        results = reader.readtext(img)
        for _, text, conf in results:
            for n in re.findall(r"\d+", text.replace(",", "").replace(".", "")):
                val = int(n)
                if 100 <= val <= 999_999:
                    candidates.append((conf, val))

    if not candidates:
        return 0

    # Return the value associated with the highest OCR confidence.
    candidates.sort(reverse=True)
    return candidates[0][1]


def check_condition(image_bytes: bytes, condition_text: str) -> bool:
    """
    Check whether the given text is visible anywhere on screen using OCR.
    Returns True if found, False otherwise.
    """
    reader = _get_reader()
    img = _to_array(image_bytes, max_width=0)   # full resolution — called rarely, must be reliable
    results = reader.readtext(img)

    all_text = " ".join(t for _, t, c in results if c > 0.3).lower()
    condition_lower = condition_text.lower()

    if condition_lower in all_text:
        return True

    # Fuzzy fallback: accept if most words of the condition are present.
    words = condition_lower.split()
    matched = sum(1 for w in words if w in all_text)
    return matched >= max(1, len(words) * 0.6)
