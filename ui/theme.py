"""
Visual theme for the Relic Bot UI.

Uses the 'clam' ttk theme as a base (gives full background/foreground
control on Windows) and overlays a dark palette with a gold accent.
"""

from tkinter import ttk

# ── Palette ─────────────────────────────────────────────────────────────── #
BG           = "#252525"   # Root window / canvas background
SURFACE      = "#2e2e2e"   # LabelFrame / Frame surface
SURFACE2     = "#383838"   # Nested / raised surfaces (tabs, dropdowns)
INPUT_BG     = "#1c1c1c"   # Entry / Text / Listbox fill
ACCENT       = "#c89840"   # Gold — section labels, active tabs, selections
TEXT         = "#e0e0e0"   # Primary text
TEXT_MUTED   = "#888888"   # Hints, secondary labels
SEL_BG       = "#c89840"   # Selection background (listboxes, text)
SEL_FG       = "#1c1c1c"   # Selection foreground
BORDER       = "#484848"   # Widget borders / frame outlines
START_BG     = "#28632a"   # ▶ START button
START_HOVER  = "#349136"
STOP_BG      = "#7a2020"   # ■ STOP button
STOP_HOVER   = "#9e2a2a"


def apply(root):
    """
    Apply the dark theme to *root* and return the configured ttk.Style.
    Call this once in RelicBotApp.__init__ before _build_ui().
    """
    root.configure(bg=BG)

    s = ttk.Style(root)
    s.theme_use("clam")

    # ── Base ─────────────────────────────────────────────────────────── #
    s.configure("TFrame",       background=SURFACE)
    s.configure("TLabel",       background=SURFACE, foreground=TEXT)
    s.configure("TCheckbutton", background=SURFACE, foreground=TEXT,
                selectcolor=INPUT_BG)
    s.configure("TRadiobutton", background=SURFACE, foreground=TEXT,
                selectcolor=INPUT_BG)
    s.map("TCheckbutton", background=[("active", SURFACE)])
    s.map("TRadiobutton",  background=[("active", SURFACE)])

    # ── Section containers (LabelFrame) ──────────────────────────────── #
    s.configure("TLabelframe",
                background=SURFACE,
                bordercolor=BORDER,
                relief="groove",
                padding=4)
    s.configure("TLabelframe.Label",
                background=SURFACE,
                foreground=ACCENT,
                font=("Segoe UI", 9, "bold"))

    # ── Text input fields ─────────────────────────────────────────────── #
    _entry_map = dict(
        fieldbackground=INPUT_BG,
        foreground=TEXT,
        insertcolor=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
    )
    s.configure("TEntry", **_entry_map)
    s.map("TEntry",
          fieldbackground=[("disabled", SURFACE2)],
          foreground=[("disabled", TEXT_MUTED)])

    s.configure("TSpinbox", **_entry_map, arrowcolor=TEXT)
    s.map("TSpinbox",
          fieldbackground=[("disabled", SURFACE2)],
          foreground=[("disabled", TEXT_MUTED)])

    s.configure("TCombobox", **_entry_map,
                background=SURFACE2,
                selectbackground=SEL_BG,
                selectforeground=SEL_FG,
                arrowcolor=TEXT)
    s.map("TCombobox",
          fieldbackground=[("readonly", INPUT_BG), ("disabled", SURFACE2)],
          foreground=[("readonly", TEXT), ("disabled", TEXT_MUTED)],
          selectbackground=[("readonly", SEL_BG)])

    # ── Buttons ───────────────────────────────────────────────────────── #
    s.configure("TButton",
                background=SURFACE2,
                foreground=TEXT,
                bordercolor=BORDER,
                lightcolor=BORDER,
                darkcolor=BORDER,
                relief="flat",
                padding=(6, 3))
    s.map("TButton",
          background=[("active", "#505050"), ("disabled", SURFACE)],
          foreground=[("disabled", TEXT_MUTED)])

    s.configure("Start.TButton",
                background=START_BG,
                foreground="#ffffff",
                font=("Segoe UI", 10, "bold"),
                padding=(10, 5))
    s.map("Start.TButton",
          background=[("active", START_HOVER), ("disabled", SURFACE2)],
          foreground=[("disabled", TEXT_MUTED)])

    s.configure("Stop.TButton",
                background=STOP_BG,
                foreground="#ffffff",
                font=("Segoe UI", 10, "bold"),
                padding=(10, 5))
    s.map("Stop.TButton",
          background=[("active", STOP_HOVER), ("disabled", SURFACE2)],
          foreground=[("disabled", TEXT_MUTED)])

    # ── Scrollbar ─────────────────────────────────────────────────────── #
    s.configure("TScrollbar",
                background=SURFACE2,
                troughcolor=INPUT_BG,
                bordercolor=BORDER,
                arrowcolor=TEXT_MUTED,
                relief="flat")
    s.map("TScrollbar",
          background=[("active", ACCENT)])

    # ── Notebook ──────────────────────────────────────────────────────── #
    s.configure("TNotebook",
                background=SURFACE,
                bordercolor=BORDER,
                tabmargins=[2, 5, 0, 0])
    s.configure("TNotebook.Tab",
                background=SURFACE2,
                foreground=TEXT_MUTED,
                padding=[12, 4],
                bordercolor=BORDER)
    s.map("TNotebook.Tab",
          background=[("selected", SURFACE), ("active", "#454545")],
          foreground=[("selected", ACCENT)])

    # ── Separator ─────────────────────────────────────────────────────── #
    s.configure("TSeparator", background=BORDER)

    return s


# ── Helpers for native tk widgets ────────────────────────────────────────── #

def style_text(widget, **extra):
    """Apply dark theme to a tk.Text widget."""
    widget.configure(
        bg=INPUT_BG, fg=TEXT,
        insertbackground=TEXT,
        selectbackground=SEL_BG, selectforeground=SEL_FG,
        relief="flat",
        highlightbackground=BORDER, highlightcolor=ACCENT,
        highlightthickness=1,
        **extra,
    )


def style_listbox(widget, **extra):
    """Apply dark theme to a tk.Listbox widget."""
    widget.configure(
        bg=INPUT_BG, fg=TEXT,
        selectbackground=SEL_BG, selectforeground=SEL_FG,
        activestyle="none",
        relief="flat",
        highlightbackground=BORDER, highlightcolor=ACCENT,
        highlightthickness=1,
        **extra,
    )
