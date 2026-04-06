"""
Captures screenshots of the game window or a specified screen region.
Returns JPEG bytes consumed by the local OCR analyser.
"""

import io
from typing import Optional, Tuple
from PIL import Image
import mss

_JPEG_QUALITY = 85


def get_screen_size() -> Tuple[int, int]:
    """Return (width, height) of the primary monitor in pixels."""
    with mss.mss() as sct:
        m = sct.monitors[1]
        return m["width"], m["height"]


def capture(region: Optional[Tuple[int, int, int, int]] = None,
            *, with_compare_crop: bool = False):
    """
    Capture a screenshot and return JPEG bytes at native resolution.

    Args:
        region: (left, top, width, height) in screen coordinates.
                If None, captures the primary monitor.
        with_compare_crop: If True, also return a small numpy crop of the
                description area (name + passives) extracted from raw pixels
                before JPEG encoding.  Used for duplicate relic detection.

    Returns:
        JPEG bytes if with_compare_crop is False.
        (JPEG bytes, crop_array) if with_compare_crop is True.
    """
    with mss.mss() as sct:
        if region:
            left, top, width, height = region
            monitor = {"left": left, "top": top, "width": width, "height": height}
        else:
            monitor = sct.monitors[1]  # Primary monitor

        screenshot = sct.grab(monitor)

    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    crop_arr = None
    if with_compare_crop:
        try:
            import numpy as np
            w, h = img.size
            # Two regions combined for robust duplicate detection:
            # 1) Icon row — cursor position always changes between relics
            # 2) Description — relic name + passives + curses text
            icon_crop = img.crop((int(w * 0.25), int(h * 0.15),
                                  int(w * 0.75), int(h * 0.35)))
            desc_crop = img.crop((int(w * 0.30), int(h * 0.53),
                                  int(w * 0.70), int(h * 0.75)))
            crop_arr = (np.array(icon_crop, dtype=np.int16),
                        np.array(desc_crop, dtype=np.int16))
        except Exception:
            pass

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    jpeg = buf.getvalue()

    if with_compare_crop:
        return jpeg, crop_arr
    return jpeg


# Duplicate detection threshold: percentage of pixels with >30 difference
# in any RGB channel.  Duplicates show <1%, different relics show >5%.
_DUPE_PCT_THRESHOLD = 1.5

def crops_differ(crop_a, crop_b) -> bool:
    """True if two (icon_row, desc) crop tuples represent different relics.

    Checks icon row first (cursor glow) — if that already exceeds threshold,
    skips the description check for speed.  Falls back to description text
    diff for edge cases where cursor didn't visibly move.
    """
    if crop_a is None or crop_b is None:
        return True  # assume different if either failed
    try:
        import numpy as np
        icon_a, desc_a = crop_a
        icon_b, desc_b = crop_b
        # Fast path: icon row cursor glow usually changes
        pct_icon = float(np.mean(np.max(np.abs(icon_a - icon_b), axis=2) > 30)) * 100
        if pct_icon > _DUPE_PCT_THRESHOLD:
            return True
        # Slow path: check description text for edge cases
        pct_desc = float(np.mean(np.max(np.abs(desc_a - desc_b), axis=2) > 30)) * 100
        return pct_desc > _DUPE_PCT_THRESHOLD
    except Exception:
        return True


# ── Menu highlight detection ────────────────────────────────────────── #
# The Roundtable Hold menu overlays a blue-tinted semi-transparent
# rectangle on the currently selected item.  We detect it by measuring
# the blue-minus-red (B-R) difference in a vertical strip past the text
# (x: 18-21% of screen width) at a known Y position.
#
# Highlighted row: B-R ≈ 28-36  (fresh ≈ 36, fading ≈ 28)
# Unhighlighted:   B-R ≈ 11-13
# Threshold of 16 cleanly separates even the most-faded highlight.
#
# Menu items are spaced exactly 5.0% of screen height apart (all 16:9):
#   Expeditions:          24.8%
#   Character Selection:  29.8%
#   Change Garb:          34.8%
#   Relic Rites:          39.8%
#   Visual Codex:         44.8%
#   Journal:              49.8%
#   Small Jar Bazaar:     54.8%

_HIGHLIGHT_BR_THRESHOLD = 16   # B-R value — only used by is_highlighted()
_HIGHLIGHT_X_START      = 0.18 # fraction of screen width (past text + blue border bleed)
_HIGHLIGHT_X_END        = 0.21
_HIGHLIGHT_STRIP_HALF   = 0.015  # +/- 1.5% of height around center

# Y-center fractions for each Roundtable menu item (16:9, any resolution)
MENU_ITEM_Y = {
    "expeditions":          0.248,
    "character_selection":  0.298,
    "change_garb":          0.348,
    "relic_rites":          0.398,
    "visual_codex":         0.448,
    "journal":              0.498,
    "small_jar_bazaar":     0.548,
    "collector_signboard":  0.598,
    "garden":               0.648,
    "shore":                0.698,
    "waiting_room":         0.748,
    "chapel":               0.798,
    "crypt":                0.848,
    "sparring_grounds":     0.898,
}


def _grab_screen(region=None):
    """Grab a screenshot and return (numpy_array_BGRA, width, height)."""
    import numpy as np
    with mss.mss() as sct:
        if region:
            left, top, width, height = region
            monitor = {"left": left, "top": top, "width": width, "height": height}
        else:
            monitor = sct.monitors[1]
        shot = sct.grab(monitor)
    w = shot.width
    h = shot.height
    arr = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(h, w, 4)
    return arr, w, h


def _br_at_y(arr, w, h, target_y_frac: float) -> float:
    """Return the B-R value at a given Y fraction from a pre-captured frame."""
    import numpy as np
    x1 = int(w * _HIGHLIGHT_X_START)
    x2 = int(w * _HIGHLIGHT_X_END)
    strip_h = int(h * _HIGHLIGHT_STRIP_HALF)
    yc = int(h * target_y_frac)
    y1 = max(0, yc - strip_h)
    y2 = min(h, yc + strip_h)

    strip = arr[y1:y2, x1:x2]
    b = float(np.mean(strip[:, :, 0]))   # Blue (BGRA index 0)
    r = float(np.mean(strip[:, :, 2]))   # Red  (BGRA index 2)
    return b - r


def check_highlight(target_y_frac: float,
                    region=None) -> float:
    """Check for a blue menu highlight at the given Y fraction of the screen.

    Returns:
        The B-R (blue minus red) value at the target position.
    """
    arr, w, h = _grab_screen(region)
    return _br_at_y(arr, w, h, target_y_frac)


def find_highlighted_item(region=None,
                          min_gap: float = 5.0):
    """Scan all menu positions and return the highlighted item.

    Uses a single screen capture and checks B-R at every known menu
    position.  The item with the highest B-R wins, provided it leads
    the second-highest by at least `min_gap` points.

    Args:
        region: Optional capture region.
        min_gap: Minimum B-R gap between 1st and 2nd place to consider
                 the result reliable.  Default 5.0 (unhighlighted items
                 are typically 11-13, highlighted 20-35, so gap is always
                 10+ in practice).

    Returns:
        (item_name, br_value, all_values_dict) if a clear winner exists.
        (None, best_br, all_values_dict) if no item is clearly highlighted
        (e.g. menu not open, or ambiguous).
    """
    arr, w, h = _grab_screen(region)
    values = {}
    for name, y_frac in MENU_ITEM_Y.items():
        values[name] = _br_at_y(arr, w, h, y_frac)

    sorted_items = sorted(values.items(), key=lambda x: x[1], reverse=True)
    best_name, best_br = sorted_items[0]
    second_br = sorted_items[1][1] if len(sorted_items) > 1 else 0.0

    if (best_br - second_br) >= min_gap:
        return best_name, best_br, values
    return None, best_br, values


def is_highlighted(target_y_frac: float,
                   region=None,
                   threshold: float = _HIGHLIGHT_BR_THRESHOLD) -> bool:
    """Return True if the blue menu highlight is on the row at target_y_frac."""
    return check_highlight(target_y_frac, region) >= threshold


# ── Shop grid snapshot comparison ───────────────────────────────────── #
# After pressing UP in the shop, the item grid changes dramatically
# (goblets → flatstones).  We detect this by comparing a snapshot of the
# grid region before and after the UP press.
#
# Grid region (fraction of screen): x 1-18%, y 15-55%
# Goblet→Flatstone diff: 10-35% of pixels change by >30 in any channel.
# Same-tab diff (no change): <1%.

_SHOP_GRID_X1 = 0.01
_SHOP_GRID_X2 = 0.18
_SHOP_GRID_Y1 = 0.15
_SHOP_GRID_Y2 = 0.55
_SHOP_GRID_CHANGE_THRESHOLD = 5.0  # % of pixels that must differ


def capture_shop_grid(region=None):
    """Capture a snapshot of the shop item grid area.

    Returns a numpy array (int16) of the grid region, suitable for
    passing to shop_grid_changed().
    """
    import numpy as np
    arr, w, h = _grab_screen(region)
    x1 = int(w * _SHOP_GRID_X1)
    x2 = int(w * _SHOP_GRID_X2)
    y1 = int(h * _SHOP_GRID_Y1)
    y2 = int(h * _SHOP_GRID_Y2)
    return arr[y1:y2, x1:x2, :3].astype(np.int16)


def shop_grid_changed(before, after, threshold: float = _SHOP_GRID_CHANGE_THRESHOLD) -> bool:
    """Return True if the shop grid content changed between two snapshots.

    Args:
        before: numpy array from capture_shop_grid() before the input.
        after:  numpy array from capture_shop_grid() after the input.
        threshold: minimum % of pixels with >30 diff in any channel.

    Returns:
        True if the grid changed (input was accepted).
    """
    import numpy as np
    if before is None or after is None:
        return True  # assume changed if either capture failed
    try:
        diff = np.abs(before - after)
        pct = float(np.mean(np.max(diff, axis=2) > 30)) * 100
        return pct > threshold
    except Exception:
        return True


def is_black_frame(image_bytes: bytes, threshold: int = 15, dark_ratio: float = 0.95) -> bool:
    """Check if a captured frame is mostly black (monitor off / sleep).

    Returns True if more than `dark_ratio` of pixels have all RGB channels
    below `threshold`.  Used to detect monitor-off conditions where screen
    capture returns blank frames.
    """
    try:
        import numpy as np
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
        dark_pixels = np.all(arr < threshold, axis=2)
        return float(dark_pixels.mean()) >= dark_ratio
    except Exception:
        return False
