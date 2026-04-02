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


def capture(region: Optional[Tuple[int, int, int, int]] = None) -> bytes:
    """
    Capture a screenshot and return JPEG bytes at native resolution.

    Args:
        region: (left, top, width, height) in screen coordinates.
                If None, captures the primary monitor.

    Returns:
        JPEG image as bytes.
    """
    with mss.mss() as sct:
        if region:
            left, top, width, height = region
            monitor = {"left": left, "top": top, "width": width, "height": height}
        else:
            monitor = sct.monitors[1]  # Primary monitor

        screenshot = sct.grab(monitor)

    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    return buf.getvalue()


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
