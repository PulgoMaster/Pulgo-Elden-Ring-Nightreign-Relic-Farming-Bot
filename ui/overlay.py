"""
BotOverlay — translucent always-on-top HUD for Batch Mode.

Displays live stats and a log feed without stealing focus from the game.
Only visible while the Nightreign game window is detected on screen.
Clicking the overlay (e.g. the Pause button) does NOT focus it, so
the game window keeps keyboard focus throughout.

Drag the header bar to move the overlay.
Use the W / H sliders at the bottom to resize it.
"""

import tkinter as tk
from tkinter import messagebox as tk_messagebox
import ctypes
import threading

# ── Windows API: prevent the overlay from ever stealing focus ─────── #

_GWL_EXSTYLE            = -20
_WS_EX_NOACTIVATE       = 0x08000000   # clicks don't activate (steal focus from) this window
_WS_EX_TOOLWINDOW       = 0x00000080   # hide from taskbar / alt-tab list
_WDA_EXCLUDEFROMCAPTURE = 0x00000011   # invisible to screen capture (Win10 2004+)


def _apply_noactivate(win: tk.Toplevel) -> None:
    """Set WS_EX_NOACTIVATE on the overlay so clicks never steal game focus."""
    try:
        hwnd = int(win.wm_frame(), 16)
        s = ctypes.windll.user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd, _GWL_EXSTYLE, s | _WS_EX_NOACTIVATE | _WS_EX_TOOLWINDOW)
    except Exception:
        pass


def _apply_capture_exclusion(win: tk.Toplevel) -> None:
    """Exclude the overlay from screen capture (mss, BitBlt, etc.).

    Uses SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE) — available on
    Windows 10 version 2004 (build 19041) and later.  Silently ignored on
    older versions so the bot still runs; the overlay just becomes visible
    in screenshots on those systems.
    """
    try:
        hwnd = int(win.wm_frame(), 16)
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, _WDA_EXCLUDEFROMCAPTURE)
    except Exception:
        pass


# ── Game window detection ─────────────────────────────────────────── #

def game_running(fragment: str = "nightreign") -> bool:
    """Return True if the foreground (focused) window title contains *fragment* (case-insensitive).

    The overlay is only shown when the game window is actively focused.
    Alt-tabbing away hides the overlay immediately.
    """
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return False
        n = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        b = ctypes.create_unicode_buffer(n + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, b, n + 1)
        return fragment.lower() in b.value.lower()
    except Exception:
        return False


# ── Colour palette ────────────────────────────────────────────────── #

_BG      = "#0d0f1e"
_SURFACE = "#14172a"
_SEP     = "#252840"
_FG      = "#e8e8f8"
_DIM     = "#6870a0"
_GOLD    = "#ffd700"
_CYAN    = "#00e5ff"
_GREEN   = "#00ff88"
_BLUE    = "#00aaff"
_GREY    = "#707080"
_RESET_C = "#1a3a5c"   # reset iteration button colour
_WARN_C  = "#ff8800"

_MIN_W = 480
_MIN_H = 480
_DEF_W = 720
_DEF_H = 800
_MAX_W = 1400
_MAX_H = 1400


# ── Tooltip helper ────────────────────────────────────────────────── #

class _Tooltip:
    """Lightweight hover tooltip for overlay widgets."""
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self._widget = widget
        self._text   = text
        self._tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        if self._tip:
            return
        x = self._widget.winfo_rootx() + self._widget.winfo_width() + 6
        y = self._widget.winfo_rooty()
        tip = tk.Toplevel(self._widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        tip.wm_attributes("-topmost", True)
        tk.Label(
            tip, text=self._text, justify="left",
            bg="#1e2235", fg="#ccddff",
            font=("Consolas", 8),
            padx=8, pady=6, relief="flat",
            wraplength=280,
        ).pack()
        self._tip = tip

    def _hide(self, _event=None) -> None:
        if self._tip:
            self._tip.destroy()
            self._tip = None


# ── Section wrapper helper ─────────────────────────────────────────── #

def _section_frame(parent: tk.Widget, with_sep: bool = True) -> tk.Frame:
    """Create a tk.Frame to wrap a toggleable section, optionally with a leading separator."""
    outer = tk.Frame(parent, bg=_BG)
    if with_sep:
        tk.Frame(outer, bg=_SEP, height=1).pack(fill="x", padx=8, pady=2)
    return outer


# ── Main class ────────────────────────────────────────────────────── #

class BotOverlay:
    """
    Translucent batch-mode HUD.  Drag the header to move.
    Use the W/H sliders to resize.  Individual sections can be toggled
    via apply_settings().
    """

    def __init__(self, root: tk.Tk):
        self._root           = root
        self._win: tk.Toplevel | None = None
        self._reset_iter_cb  = None
        self._stop_cb        = None        # graceful: stop after current batch
        self._force_stop_cb  = None        # immediate: stop right now
        self._close_game_cb  = None        # optional: close game after force stop
        self._watching       = False
        self._sv: dict[str, tk.StringVar] = {}
        self._reset_iter_btn: tk.Label | None  = None
        self._abort_btn:      tk.Label | None  = None
        self._view_matches_btn: tk.Label | None = None
        self._log_box:        tk.Text  | None  = None   # process log
        self._relic_log_box:  tk.Text  | None  = None   # relic analysis log
        self._matches_log_box: tk.Text | None  = None   # matches-only log
        self._matches_panel:  tk.Frame | None  = None
        self._overflow_hits_frame: tk.Frame | None = None
        self._stop_pending   = False
        self._matches_view   = False

        # Drag-to-move state
        self._drag_x = 0
        self._drag_y = 0

        # User-initiated hide (hotkey toggle) — while True, game_watch auto-show is suppressed
        self._user_hidden = False

        # Section visibility
        self._section_visible: dict[str, bool] = {
            "stats":       True,
            "rolls":       True,
            "overflow":    True,
            "near_miss":   True,
            "smart":       True,
            "excl":        True,
            "process_log": True,
            "relic_log":   True,
        }

        # Ordered sections list: (key, frame, pack_kwargs)
        # Populated during _build_ui(); used by _repack_sections()
        self._managed_sections: list = []

        # Log panel refs for spanning logic
        self._log_outer:    tk.Frame | None = None
        self._process_panel: tk.Frame | None = None
        self._relic_panel:   tk.Frame | None = None
        self._log_sep:       tk.Frame | None = None   # vertical divider between panels

    # ── Lifecycle ──────────────────────────────────────────────────── #

    def build(self, screen_w: int, screen_h: int,
              async_mode: bool = False,
              backlog_mode: bool = False,
              settings: dict | None = None) -> None:
        """Create the overlay window, positioned bottom-left of the screen."""
        if self._win:
            return

        self._async_mode   = async_mode
        self._backlog_mode = backlog_mode

        if settings:
            for key in self._section_visible:
                # profile keys use the same names
                self._section_visible[key] = settings.get(f"show_{key}", True)

        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.wm_attributes("-topmost", True)
        win.wm_attributes("-alpha", 0.88)
        win.configure(bg=_BG)

        x = 16
        y = screen_h - _DEF_H - 48
        win.geometry(f"{_DEF_W}x{_DEF_H}+{x}+{y}")
        win.minsize(_MIN_W, _MIN_H)

        self._win = win
        self._build_ui()
        win.update_idletasks()
        _apply_noactivate(win)
        _apply_capture_exclusion(win)

    def _build_ui(self) -> None:
        w = self._win
        self._managed_sections = []

        def sv(key: str, default: str = "—") -> tk.StringVar:
            v = tk.StringVar(value=default)
            self._sv[key] = v
            return v

        def _reg(key: str, frame: tk.Frame, **kwargs) -> tk.Frame:
            """Register a managed section frame."""
            self._managed_sections.append((key, frame, kwargs))
            return frame

        # ── Header — drag to move ───────────────────────────────────── #
        hdr = tk.Frame(w, bg=_BG, cursor="fleur")
        _reg("always", hdr, fill="x", padx=10, pady=(8, 2))

        tk.Label(hdr, text="⚙ RELIC BOT", bg=_BG, fg=_GOLD,
                 font=("Consolas", 10, "bold"), cursor="fleur").pack(side="left")
        tk.Label(hdr, textvariable=sv("batch", "—"),
                 bg=_BG, fg=_DIM, font=("Consolas", 9), cursor="fleur").pack(side="right")
        tk.Label(hdr, textvariable=sv("mode_tag", ""),
                 bg=_BG, fg="#5588aa", font=("Consolas", 8), cursor="fleur").pack(side="right", padx=(0, 8))

        for widget in (hdr,) + tuple(hdr.winfo_children()):
            widget.bind("<ButtonPress-1>", self._on_drag_start)
            widget.bind("<B1-Motion>",     self._on_drag_move)

        # ── Stats section ───────────────────────────────────────────── #
        stats_sec = _section_frame(w, with_sep=True)
        _reg("stats", stats_sec, fill="x")

        r1 = tk.Frame(stats_sec, bg=_BG)
        r1.pack(fill="x", padx=10, pady=2)
        _stat(r1, "Murk",       sv("murk"),                _GOLD)
        _stat(r1, "Est. After", sv("est_murk_after", "—"), _GOLD)
        _stat(r1, "Relics",     sv("to_buy"),              _CYAN)
        _stat(r1, "Bought",     sv("bought"),              _CYAN)
        _stat(r1, "Stored",     sv("stored",   "0"),         _FG)
        _stat(r1, "Analyzed",   sv("analyzed", "0"),         _FG)

        r2 = tk.Frame(stats_sec, bg=_BG)
        r2.pack(fill="x", padx=10, pady=2)
        _stat(r2, "Relic #",   sv("relic_num"),  _FG)
        _stat(r2, "Analysing", sv("analysing"),  _FG)

        # ── Rolls section (hit counters + best batches) ─────────────── #
        rolls_sec = _section_frame(w, with_sep=True)
        _reg("rolls", rolls_sec, fill="x")

        hf = tk.Frame(rolls_sec, bg=_BG)
        hf.pack(fill="x", padx=10, pady=(4, 6))
        hf.columnconfigure(0, weight=1)
        hf.columnconfigure(1, weight=1)
        hf.columnconfigure(2, weight=1)

        for col, (label, key_run, key_all, color) in enumerate([
            ("God Roll", "hits_33", "at_33",   _GREEN),
            ("Good",     "hits_23", "at_23",   _BLUE),
            ("Duds",     "duds",    "at_duds", _GREY),
        ]):
            cell = tk.Frame(hf, bg=_BG)
            cell.grid(row=0, column=col, sticky="n", pady=2)
            tk.Label(cell, text=label, bg=_BG, fg=_DIM,
                     font=("Consolas", 8)).pack()
            if not self._async_mode and not self._backlog_mode:
                tk.Label(cell, text="this run", bg=_BG, fg=_DIM,
                         font=("Consolas", 7)).pack()
                tk.Label(cell, textvariable=sv(key_run, "0"), bg=_BG, fg=color,
                         font=("Consolas", 22, "bold")).pack()
                tk.Label(cell, text="all time", bg=_BG, fg=_DIM,
                         font=("Consolas", 7)).pack(pady=(4, 0))
                tk.Label(cell, textvariable=sv(key_all, "0"), bg=_BG, fg=color,
                         font=("Consolas", 14, "bold")).pack()
            else:
                tk.Label(cell, textvariable=sv(key_all, "0"), bg=_BG, fg=color,
                         font=("Consolas", 22, "bold")).pack()

        # Best Batches scoreboard (inside rolls section)
        tk.Frame(rolls_sec, bg=_SEP, height=1).pack(fill="x", padx=8, pady=2)

        bb_hdr = tk.Frame(rolls_sec, bg=_BG)
        bb_hdr.pack(fill="x", padx=10, pady=(4, 2))
        tk.Label(bb_hdr, text="BEST BATCHES", bg=_BG, fg=_DIM,
                 font=("Consolas", 8, "bold")).pack(anchor="w")

        bb = tk.Frame(rolls_sec, bg=_BG)
        bb.pack(fill="x", padx=14, pady=(0, 4))

        row_33 = tk.Frame(bb, bg=_BG)
        row_33.pack(fill="x", pady=1)
        tk.Label(row_33, text="Most 3/3 :", bg=_BG, fg=_GREEN,
                 font=("Consolas", 8, "bold"), width=11, anchor="w").pack(side="left")
        tk.Label(row_33, textvariable=sv("best_33", "N/A"), bg=_BG, fg=_FG,
                 font=("Consolas", 8)).pack(side="left")

        row_top = tk.Frame(bb, bg=_BG)
        row_top.pack(fill="x", pady=1)
        tk.Label(row_top, text="Most Hits:", bg=_BG, fg=_CYAN,
                 font=("Consolas", 8, "bold"), width=11, anchor="w").pack(side="left")
        tk.Label(row_top, textvariable=sv("best_hits", "N/A"), bg=_BG, fg=_FG,
                 font=("Consolas", 8)).pack(side="left")

        self._row_nearmiss = tk.Frame(bb, bg=_BG)
        self._row_nearmiss.pack(fill="x", pady=1)
        tk.Label(self._row_nearmiss, text="Near Miss:", bg=_BG, fg="#cccc00",
                 font=("Consolas", 8, "bold"), width=11, anchor="w").pack(side="left")
        tk.Label(self._row_nearmiss, textvariable=sv("near_miss_hits", "0"), bg=_BG, fg=_FG,
                 font=("Consolas", 8)).pack(side="left")

        self._row_smart = tk.Frame(bb, bg=_BG)
        self._row_smart.pack(fill="x", pady=1)
        tk.Label(self._row_smart, text="Smart Hits:", bg=_BG, fg="#9966ff",
                 font=("Consolas", 8, "bold"), width=11, anchor="w").pack(side="left")
        tk.Label(self._row_smart, textvariable=sv("smart_hits", "0"), bg=_BG, fg=_FG,
                 font=("Consolas", 8)).pack(side="left")

        self._row_excl = tk.Frame(bb, bg=_BG)
        self._row_excl.pack(fill="x", pady=1)
        tk.Label(self._row_excl, text="Excl. Hits:", bg=_BG, fg="#cc6600",
                 font=("Consolas", 8, "bold"), width=11, anchor="w").pack(side="left")
        tk.Label(self._row_excl, textvariable=sv("excl_hits", "0"), bg=_BG, fg=_FG,
                 font=("Consolas", 8)).pack(side="left")

        # ── Overflow hits section ────────────────────────────────────── #
        # Invisible when count = 0; lights up when old-batch overflow workers
        # find a 2/3 or 3/3.  Always packed so layout never shifts.
        ov_sec = _section_frame(w, with_sep=True)
        _reg("overflow", ov_sec, fill="x")

        self._overflow_hits_frame = tk.Frame(ov_sec, bg=_BG)
        self._overflow_hits_frame.pack(fill="x", padx=10, pady=0)
        self._sv["overflow_hits_label"] = tk.StringVar(value="")
        self._sv["overflow_hits"]       = tk.StringVar(value="")
        tk.Label(
            self._overflow_hits_frame,
            textvariable=self._sv["overflow_hits_label"],
            bg=_BG, fg="#ff8800",
            font=("Consolas", 8, "bold"),
        ).pack(side="left")
        tk.Label(
            self._overflow_hits_frame,
            textvariable=self._sv["overflow_hits"],
            bg=_BG, fg="#ffcc66",
            font=("Consolas", 14, "bold"),
        ).pack(side="right", padx=(8, 0))

        # ── Buttons section ──────────────────────────────────────────── #
        btns_sec = _section_frame(w, with_sep=True)
        _reg("always", btns_sec, fill="x")

        bf = tk.Frame(btns_sec, bg=_BG)
        bf.pack(pady=(3, 5))

        self._reset_iter_btn = tk.Label(
            bf, text="⟳  RESET ITER",
            bg=_RESET_C, fg="#88bbff",
            font=("Consolas", 10, "bold"),
            padx=16, pady=5, cursor="hand2", relief="flat",
        )
        self._reset_iter_btn.pack(side="left", padx=(0, 6))
        self._reset_iter_btn.bind(
            "<Button-1>",
            lambda _: self._reset_iter_cb() if self._reset_iter_cb else None,
        )
        _Tooltip(self._reset_iter_btn,
                 "Reset Batch\n\n"
                 "Closes the game, deletes this batch's output folder,\n"
                 "restores your save to a clean state, and re-runs the\n"
                 "current batch as if it never happened.\n\n"
                 "Use this if you notice the bot is lost or stuck mid-run.")

        self._abort_btn = tk.Label(
            bf, text="⏻  STOP AFTER BATCH",
            bg="#1a1a2e", fg="#cc3300",
            font=("Consolas", 10, "bold"),
            padx=16, pady=5, cursor="hand2", relief="flat",
        )
        self._abort_btn.pack(side="left")
        self._abort_btn.bind("<Button-1>", self._on_abort_click)

        self._view_matches_btn = tk.Label(
            bf, text="★ View Matches",
            bg="#0d2a0d", fg="#00ff88",
            font=("Consolas", 10, "bold"),
            padx=14, pady=5, cursor="hand2", relief="flat",
        )
        self._view_matches_btn.pack(side="left", padx=(6, 0))
        self._view_matches_btn.bind("<Button-1>", lambda _: self._toggle_matches_view())

        # ── Log panels — Process (left) | Relics (right) ────────────── #
        logs_sec = _section_frame(w, with_sep=True)
        _reg("always", logs_sec, fill="both", expand=True, padx=0, pady=0)

        self._log_outer = tk.Frame(logs_sec, bg=_BG)
        self._log_outer.pack(fill="both", expand=True, padx=6, pady=(2, 0))
        self._log_outer.columnconfigure(0, weight=1, uniform="logcol")
        self._log_outer.columnconfigure(1, weight=1, uniform="logcol")
        self._log_outer.rowconfigure(0, weight=1)

        # Process panel
        self._process_panel = tk.Frame(self._log_outer, bg=_BG)
        self._process_panel.columnconfigure(0, weight=1)
        self._process_panel.rowconfigure(1, weight=1)
        tk.Label(self._process_panel, text="PROCESS", bg=_BG, fg=_DIM,
                 font=("Consolas", 7, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        self._log_box = tk.Text(
            self._process_panel, bg="#080b18", fg=_FG,
            font=("Consolas", 7), wrap="word",
            state="disabled", relief="flat", borderwidth=0,
        )
        psb = tk.Scrollbar(self._process_panel, orient="vertical",
                           command=self._log_box.yview,
                           bg=_BG, troughcolor=_SURFACE)
        self._log_box.configure(yscrollcommand=psb.set)
        self._log_box.grid(row=1, column=0, sticky="nsew")
        psb.grid(row=1, column=1, sticky="ns")

        # Vertical separator (between panels)
        self._log_sep = tk.Frame(self._log_outer, bg=_SEP, width=1)

        # Relic panel
        self._relic_panel = tk.Frame(self._log_outer, bg=_BG)
        self._relic_panel.columnconfigure(0, weight=1)
        self._relic_panel.rowconfigure(1, weight=1)
        tk.Label(self._relic_panel, text="RELICS", bg=_BG, fg=_DIM,
                 font=("Consolas", 7, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        self._relic_log_box = tk.Text(
            self._relic_panel, bg="#080b18", fg=_FG,
            font=("Consolas", 7), wrap="word",
            state="disabled", relief="flat", borderwidth=0,
        )
        rsb = tk.Scrollbar(self._relic_panel, orient="vertical",
                           command=self._relic_log_box.yview,
                           bg=_BG, troughcolor=_SURFACE)
        self._relic_log_box.configure(yscrollcommand=rsb.set)
        self._relic_log_box.grid(row=1, column=0, sticky="nsew")
        rsb.grid(row=1, column=1, sticky="ns")

        # Matches panel — full-width, replaces both log panels in matches view
        self._matches_panel = tk.Frame(self._log_outer, bg=_BG)
        self._matches_panel.columnconfigure(0, weight=1)
        self._matches_panel.rowconfigure(1, weight=1)
        tk.Label(self._matches_panel, text="MATCHED RELICS", bg=_BG, fg=_GREEN,
                 font=("Consolas", 7, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        self._matches_log_box = tk.Text(
            self._matches_panel, bg="#080b18", fg=_FG,
            font=("Consolas", 7), wrap="word",
            state="disabled", relief="flat", borderwidth=0,
        )
        msb = tk.Scrollbar(self._matches_panel, orient="vertical",
                           command=self._matches_log_box.yview,
                           bg=_BG, troughcolor=_SURFACE)
        self._matches_log_box.configure(yscrollcommand=msb.set)
        self._matches_log_box.grid(row=1, column=0, sticky="nsew")
        msb.grid(row=1, column=1, sticky="ns")

        # Mousewheel scrolling for each log panel — bind explicitly so the main
        # window's bind_all handler doesn't steal the event.  Returning "break"
        # stops propagation after the local scroll is applied.
        def _scroll(box):
            def _handler(event):
                box.yview_scroll(int(-1 * (event.delta / 120)) * 3, "units")
                return "break"
            box.bind("<MouseWheel>", _handler)
        _scroll(self._log_box)
        _scroll(self._relic_log_box)
        _scroll(self._matches_log_box)

        # Initial pack of all sections + log layout
        self._repack_sections()

    # ── Section visibility ─────────────────────────────────────────── #

    def _repack_sections(self) -> None:
        """Unpack all managed sections then re-pack visible ones in order."""
        if not self._win:
            return
        for _key, frame, _kwargs in self._managed_sections:
            frame.pack_forget()
        for key, frame, kwargs in self._managed_sections:
            if key == "always" or self._section_visible.get(key, True):
                frame.pack(**kwargs)

        # Toggle inline counter rows within the rolls section
        for attr, key in [("_row_nearmiss", "near_miss"),
                          ("_row_smart",    "smart"),
                          ("_row_excl",     "excl")]:
            row = getattr(self, attr, None)
            if row:
                if self._section_visible.get(key, True):
                    row.pack(fill="x", pady=1)
                else:
                    row.pack_forget()

        self._update_log_layout()

    def _update_log_layout(self) -> None:
        """Adjust log panel grid spanning based on which logs are visible."""
        if not self._log_outer:
            return

        # Forget all panels first
        self._process_panel.grid_forget()
        self._relic_panel.grid_forget()
        self._log_sep.grid_forget()
        if self._matches_panel:
            self._matches_panel.grid_forget()

        if self._matches_view:
            # Matches view: full-width matches panel only
            if self._matches_panel:
                self._matches_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
            return

        show_proc  = self._section_visible.get("process_log", True)
        show_relic = self._section_visible.get("relic_log",   True)

        if show_proc and show_relic:
            self._process_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 1))
            self._log_sep.grid(row=0, column=0, sticky="nse", pady=4)
            self._relic_panel.grid(row=0, column=1, sticky="nsew", padx=(1, 0))
        elif show_proc:
            self._process_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
        elif show_relic:
            self._relic_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")

    def _toggle_matches_view(self) -> None:
        """Switch between normal log view and the full-width matched-relics view."""
        if not self._win:
            return
        self._matches_view = not self._matches_view
        if self._view_matches_btn:
            if self._matches_view:
                self._view_matches_btn.configure(text="◀ Back to Logs",
                                                 bg="#2a1a00", fg=_GOLD)
            else:
                self._view_matches_btn.configure(text="★ View Matches",
                                                 bg="#0d2a0d", fg=_GREEN)
        self._update_log_layout()

    def apply_settings(self, settings: dict) -> None:
        """Live-apply overlay element settings from a dict.

        Keys: show_stats, show_rolls, show_overflow,
              show_process_log, show_relic_log
        """
        changed = False
        for key in self._section_visible:
            new_val = settings.get(f"show_{key}", self._section_visible[key])
            if new_val != self._section_visible[key]:
                self._section_visible[key] = new_val
                changed = True

        if changed and self._win:
            self._root.after(0, self._repack_sections)

    # ── Drag-to-move ───────────────────────────────────────────────── #

    def _on_drag_start(self, event) -> None:
        self._drag_x = event.x_root - self._win.winfo_x()
        self._drag_y = event.y_root - self._win.winfo_y()

    def _on_drag_move(self, event) -> None:
        if not self._win:
            return
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self._win.geometry(f"+{x}+{y}")

    # ── Show / hide / destroy ──────────────────────────────────────── #

    def suppress_show(self, suppressed: bool) -> None:
        """While suppressed, show() is a no-op (used when a dialog must be on top)."""
        self._suppressed = suppressed

    def show(self) -> None:
        """Show overlay (respects user toggle)."""
        if self._win and not self._user_hidden:
            self._win.deiconify()

    def hide(self) -> None:
        """Hide overlay (used by user toggle)."""
        if self._win:
            self._win.withdraw()

    def toggle_user_visibility(self) -> None:
        """Hotkey-triggered toggle. Flips user_hidden and immediately shows/hides.
        Stats continue updating in the background regardless of visibility."""
        if not self._win:
            return
        self._user_hidden = not self._user_hidden
        if self._user_hidden:
            self._win.withdraw()
        else:
            self._win.deiconify()

    def destroy(self) -> None:
        self._watching = False
        if self._win:
            self._win.destroy()
            self._win = None

    # ── Game window watching ───────────────────────────────────────── #

    def start_game_watch(self, fragment: str = "nightreign") -> None:
        """Keep overlay visible for the entire bot session.

        The overlay stays shown regardless of whether the game window is
        focused or even running.  Users control visibility via the hotkey
        toggle or the Overlay Elements settings.
        """
        if self._watching:
            return
        self._watching = True
        # Show immediately — no polling needed.  The overlay stays visible
        # until the bot run ends and destroy() is called.
        if self._win and not self._user_hidden:
            self._root.after(0, self._win.deiconify)

    # Row visibility for near_miss/smart/excl now handled by _repack_sections()
    # via _section_visible dict and overlay element settings.

    # ── Data updates ───────────────────────────────────────────────── #

    def update(self, **kwargs) -> None:
        if not self._win:
            return
        for key, val in kwargs.items():
            if key in self._sv:
                try:
                    self._sv[key].set(str(val))
                except Exception:
                    pass

    def append_log(self, line: str) -> None:
        """Append one process log line (left panel). Must be called from the main thread."""
        if not self._win or not self._log_box:
            return
        self._log_box.configure(state="normal")
        self._log_box.insert("end", line.rstrip() + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def append_relic_log(self, line: str) -> None:
        """Append one relic analysis line (right panel). Must be called from the main thread."""
        if not self._win or not self._relic_log_box:
            return
        self._relic_log_box.configure(state="normal")
        self._relic_log_box.insert("end", line.rstrip() + "\n")
        self._relic_log_box.see("end")
        self._relic_log_box.configure(state="disabled")

    def append_matches_log(self, text: str) -> None:
        """Append a formatted match entry to the matches log panel. Main thread only."""
        if not self._win or not self._matches_log_box:
            return
        self._matches_log_box.configure(state="normal")
        self._matches_log_box.insert("end", text)
        self._matches_log_box.see("end")
        self._matches_log_box.configure(state="disabled")

    def set_overflow_hits(self, count: int) -> None:
        """Show/update the previous-batch overflow hit counter. Must be called from main thread."""
        if not self._win:
            return
        if count > 0:
            self._sv["overflow_hits_label"].set("⚠ PREV BATCH OVERFLOW HITS")
            self._sv["overflow_hits"].set(str(count))
            if self._overflow_hits_frame:
                self._overflow_hits_frame.configure(bg="#1a0d00")
                for child in self._overflow_hits_frame.winfo_children():
                    child.configure(bg="#1a0d00")
        else:
            self._sv["overflow_hits_label"].set("")
            self._sv["overflow_hits"].set("")
            if self._overflow_hits_frame:
                self._overflow_hits_frame.configure(bg=_BG)
                for child in self._overflow_hits_frame.winfo_children():
                    child.configure(bg=_BG)

    # ── Callback wiring ─────────────────────────────────────────────── #

    def set_reset_iter_callback(self, cb) -> None:
        self._reset_iter_cb = cb

    def set_stop_callback(self, cb) -> None:
        """Graceful stop: bot finishes the current batch then exits."""
        self._stop_cb = cb

    def set_force_stop_callback(self, cb) -> None:
        """Immediate stop: interrupts the bot right now (second click)."""
        self._force_stop_cb = cb

    def set_close_game_callback(self, cb) -> None:
        """Optional: called after a force stop if the user asks to close the game."""
        self._close_game_cb = cb

    def set_stop_pending(self, pending: bool) -> None:
        """Sync the abort button state (e.g. when stop was triggered externally)."""
        self._stop_pending = pending
        if not self._abort_btn:
            return
        if pending:
            self._abort_btn.configure(
                text="⌛ AFTER BATCH…", bg=_WARN_C, fg="white")
        else:
            self._abort_btn.configure(
                text="⏻  STOP AFTER BATCH", bg="#1a1a2e", fg="#cc3300")

    def _on_abort_click(self, _event=None) -> None:
        if not self._stop_pending:
            # First click — request graceful stop after current batch
            self._stop_pending = True
            if self._abort_btn:
                self._abort_btn.configure(
                    text="⌛ AFTER BATCH…", bg=_WARN_C, fg="white")
            if self._stop_cb:
                self._stop_cb()
        else:
            # Second click — offer immediate force stop
            confirmed = tk_messagebox.askyesno(
                "Force Stop Now?",
                "The bot is already scheduled to stop after this batch.\n\n"
                "Force stop RIGHT NOW instead?\n"
                "The current batch will be incomplete.",
                icon="warning",
                parent=self._win,
            )
            if confirmed:
                close_game = (
                    self._close_game_cb is not None
                    and tk_messagebox.askyesno(
                        "Close Game?",
                        "Close the game instance as well?",
                        parent=self._win,
                    )
                )
                if self._force_stop_cb:
                    self._force_stop_cb()
                # Run _close_game in a thread — it polls until the process exits
                # and must not block the main tkinter thread.
                if close_game:
                    import threading as _threading
                    _threading.Thread(
                        target=self._close_game_cb, daemon=True,
                        name="manual-close-game").start()


# ── Widget helpers ────────────────────────────────────────────────── #

def _stat(parent: tk.Frame, label: str,
          var: tk.StringVar, color: str) -> None:
    cell = tk.Frame(parent, bg=_BG)
    cell.pack(side="left", padx=6)
    tk.Label(cell, text=label, bg=_BG, fg=_DIM,
             font=("Consolas", 7)).pack(anchor="w")
    tk.Label(cell, textvariable=var, bg=_BG, fg=color,
             font=("Consolas", 10, "bold")).pack(anchor="w")
