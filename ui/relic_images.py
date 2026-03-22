"""
Procedurally-generated relic gem images for the UI.

No external image files are required — all gems are drawn with PIL.
Supports Normal and Deep of Night (DON) colour variants for each relic colour.
"""

from PIL import Image, ImageDraw
from PIL import ImageTk   # bundled with Pillow

# ── Palette ─────────────────────────────────────────────────────────────── #
# Each entry: (base, shadow, highlight)  — Normal, then Deep-of-Night
_PALETTES: dict[str, dict] = {
    "Red": {
        "normal": ("#dd2200", "#771000", "#ff9977"),
        "don":    ("#6e1108", "#38070a", "#bb5544"),
    },
    "Blue": {
        "normal": ("#1144cc", "#091a77", "#88aaff"),
        "don":    ("#0b1a5e", "#060e33", "#4466aa"),
    },
    "Green": {
        "normal": ("#117733", "#093d1a", "#66cc88"),
        "don":    ("#0a3b1c", "#051e0e", "#336655"),
    },
    "Yellow": {
        "normal": ("#cc8800", "#784400", "#ffdd55"),
        "don":    ("#5c3b00", "#2e1c00", "#998833"),
    },
    "Blank": {
        "normal": ("#aaaaaa", "#555555", "#dddddd"),
        "don":    ("#666666", "#333333", "#999999"),
    },
}

_GEM_SIZE = 52     # px — size of each generated gem image
_cache: dict[str, ImageTk.PhotoImage] = {}   # keeps references alive


# ── Helpers ─────────────────────────────────────────────────────────────── #

def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _lerp(a: tuple, b: tuple, t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


# ── Core gem drawing ─────────────────────────────────────────────────────── #

def _make_gem(base_hex: str, shadow_hex: str, hi_hex: str,
              size: int = _GEM_SIZE) -> Image.Image:
    """
    Draw a classic four-point diamond gem with three facets and a specular dot.
    Returns an RGBA Image.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)

    cx  = size // 2
    pad = 4

    # Gem outline: top · right · bottom · left (y-centre slightly above midpoint)
    cy_gem = size * 5 // 11
    top    = (cx, pad)
    right  = (size - pad, cy_gem)
    bottom = (cx, size - pad)
    left   = (pad, cy_gem)
    gem    = [top, right, bottom, left]

    b = _hex_rgb(base_hex)
    s = _hex_rgb(shadow_hex)
    h = _hex_rgb(hi_hex)

    # ── Fill ─────────────────────────────────────────────────────────── #
    d.polygon(gem, fill=(*b, 255))

    # Lower dark half (shadow)
    lower = [left, right, bottom]
    d.polygon(lower, fill=(*s, 170))

    # Upper-right mid facet (slightly warm)
    mid_r = [top, right, (cx + size // 8, cy_gem - size // 8)]
    d.polygon(mid_r, fill=(*_lerp(b, s, 0.2), 100))

    # Upper-left highlight facet
    mid_l = [top, left, (cx - size // 8, cy_gem - size // 8)]
    d.polygon(mid_l, fill=(*h, 120))

    # ── Outline ──────────────────────────────────────────────────────── #
    d.polygon(gem, outline=(*s, 230))

    # ── Specular highlight ───────────────────────────────────────────── #
    sx, sy = cx - 3, pad + 4
    d.ellipse([sx - 3, sy - 2, sx + 3, sy + 4], fill=(*h, 210))

    return img


def _make_blank_gem(size: int = _GEM_SIZE + 8) -> Image.Image:
    """
    A larger blank/white relic gem for the Build Exact Relic header.
    Rendered with silver tones and an inner inscription ring.
    """
    pal = _PALETTES["Blank"]["normal"]
    img = _make_gem(*pal, size=size)
    # Add a faint inner ring to suggest 'empty slot'
    d  = ImageDraw.Draw(img)
    cx = size // 2
    pad = size // 5
    d.ellipse([cx - pad, cx - pad, cx + pad, cx + pad],
              outline=(200, 200, 200, 80), width=1)
    return img


# ── Public API ───────────────────────────────────────────────────────────── #

def get_gem(color: str, don: bool = False) -> ImageTk.PhotoImage:
    """
    Return a cached PhotoImage for the given relic colour.

    Args:
        color:  One of "Red", "Blue", "Green", "Yellow", "Blank".
        don:    If True, return the Deep of Night variant (darker palette).
    """
    key = f"{color}_{'don' if don else 'normal'}"
    if key not in _cache:
        pal = _PALETTES.get(color, _PALETTES["Blank"])
        variant = "don" if don else "normal"
        img = _make_gem(*pal[variant])
        _cache[key] = ImageTk.PhotoImage(img)
    return _cache[key]


def get_blank_gem() -> ImageTk.PhotoImage:
    """Return the large blank/silver gem used in the Build Exact Relic tab."""
    key = "_blank_large"
    if key not in _cache:
        _cache[key] = ImageTk.PhotoImage(_make_blank_gem())
    return _cache[key]


def clear_cache() -> None:
    """Discard all cached images (call if root window is destroyed)."""
    _cache.clear()
