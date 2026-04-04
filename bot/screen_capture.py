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
