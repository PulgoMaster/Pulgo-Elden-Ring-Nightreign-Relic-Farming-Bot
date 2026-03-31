"""
Relic gem images for the UI.

Normal and Deep of Night variants are loaded from pre-rendered PNG files
in ui/relic_icons/.  The blank gem (used in the Build Exact Relic tab) is
still drawn procedurally since there is no in-game equivalent.
"""

import os
import sys

from PIL import Image, ImageDraw
from PIL import ImageTk   # bundled with Pillow


_GEM_SIZE       = 64     # px — display size for colour-select gems
_BLANK_GEM_SIZE = 60     # px — blank/silver gem in the relic builder
_FLATSTONE_SIZE = 64     # px — Scenic / Deep Scenic Flatstone in Relic Criteria header

_cache: dict[str, ImageTk.PhotoImage] = {}   # keeps references alive


# ── Path resolution ──────────────────────────────────────────────────────── #

def _icons_dir() -> str:
    """Return the folder containing relic icon PNGs (frozen or dev)."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "ui", "relic_icons")
    return os.path.join(os.path.dirname(__file__), "relic_icons")


# ── File-based gem loading ───────────────────────────────────────────────── #

_COLOR_NAME: dict[str, str] = {
    "Red":    "red",
    "Blue":   "blue",
    "Green":  "green",
    "Yellow": "yellow",
}


def _load_gem(color: str, don: bool) -> Image.Image:
    """Load, resize, and return the PNG for the given colour/variant."""
    prefix  = "deep" if don else "normal"
    name    = _COLOR_NAME.get(color, color.lower())
    path    = os.path.join(_icons_dir(), f"{prefix}_{name}.png")
    img     = Image.open(path).convert("RGBA")
    return img.resize((_GEM_SIZE, _GEM_SIZE), Image.LANCZOS)


# ── Blank gem (procedural) ───────────────────────────────────────────────── #

def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _lerp(a: tuple, b: tuple, t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def _make_blank_gem(size: int = _BLANK_GEM_SIZE) -> Image.Image:
    """Silver blank-slot gem for the Build Exact Relic header."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    cx  = size // 2
    pad = 4

    cy_gem = size * 5 // 11
    top    = (cx, pad)
    right  = (size - pad, cy_gem)
    bottom = (cx, size - pad)
    left   = (pad, cy_gem)
    gem    = [top, right, bottom, left]

    b = _hex_rgb("#aaaaaa")
    s = _hex_rgb("#555555")
    h = _hex_rgb("#dddddd")

    d.polygon(gem, fill=(*b, 255))
    d.polygon([left, right, bottom], fill=(*s, 170))
    d.polygon([top, right, (cx + size // 8, cy_gem - size // 8)],
              fill=(*_lerp(b, s, 0.2), 100))
    d.polygon([top, left, (cx - size // 8, cy_gem - size // 8)],
              fill=(*h, 120))
    d.polygon(gem, outline=(*s, 230))

    sx, sy = cx - 3, pad + 4
    d.ellipse([sx - 3, sy - 2, sx + 3, sy + 4], fill=(*h, 210))

    d.ellipse([cx - size // 5, cx - size // 5,
               cx + size // 5, cx + size // 5],
              outline=(200, 200, 200, 80), width=1)
    return img


# ── Public API ───────────────────────────────────────────────────────────── #

def get_gem(color: str, don: bool = False) -> ImageTk.PhotoImage:
    """
    Return a cached PhotoImage for the given relic colour.

    Args:
        color:  One of "Red", "Blue", "Green", "Yellow".
        don:    If True, return the Deep of Night variant.
    """
    key = f"{color}_{'don' if don else 'normal'}"
    if key not in _cache:
        _cache[key] = ImageTk.PhotoImage(_load_gem(color, don))
    return _cache[key]


def get_blank_gem() -> ImageTk.PhotoImage:
    """Return the large blank/silver gem used in the Build Exact Relic tab."""
    key = "_blank"
    if key not in _cache:
        _cache[key] = ImageTk.PhotoImage(_make_blank_gem())
    return _cache[key]


def get_flatstone(don: bool = False) -> ImageTk.PhotoImage:
    """
    Return the Scenic Flatstone (Normal) or Deep Scenic Flatstone (Deep of Night)
    icon for the Relic Criteria tab header.
    """
    key = f"flatstone_{'deep' if don else 'normal'}"
    if key not in _cache:
        name = "flatstone_deep" if don else "flatstone_normal"
        path = os.path.join(_icons_dir(), f"{name}.png")
        img  = Image.open(path).convert("RGBA")
        img  = img.resize((_FLATSTONE_SIZE, _FLATSTONE_SIZE), Image.LANCZOS)
        _cache[key] = ImageTk.PhotoImage(img)
    return _cache[key]


def clear_cache() -> None:
    """Discard all cached images (call if root window is destroyed)."""
    _cache.clear()
