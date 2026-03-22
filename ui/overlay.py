"""
BotOverlay — translucent always-on-top HUD for Batch Mode.

Displays live stats and a log feed without stealing focus from the game.
Only visible while the Nightreign game window is detected on screen.
Clicking the overlay (e.g. the Pause button) does NOT focus it, so
the game window keeps keyboard focus throughout.
"""

import tkinter as tk
import ctypes
import ctypes.wintypes
import threading

# ── Windows API: prevent the overlay from ever stealing focus ─────── #

_GWL_EXSTYLE      = -20
_WS_EX_NOACTIVATE = 0x08000000   # clicks don't activate (steal focus from) this window
_WS_EX_TOOLWINDOW = 0x00000080   # hide from taskbar / alt-tab list


def _apply_noactivate(win: tk.Toplevel) -> None:
    """Set WS_EX_NOACTIVATE on the overlay so clicks never steal game focus."""
    try:
        hwnd = int(win.wm_frame(), 16)
        s = ctypes.windll.user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd, _GWL_EXSTYLE, s | _WS_EX_NOACTIVATE | _WS_EX_TOOLWINDOW)
    except Exception:
        pass


# ── Game window detection ─────────────────────────────────────────── #

def game_running(fragment: str = "nightreign") -> bool:
    """Return True if any visible window title contains *fragment* (case-insensitive)."""
    found = [False]
    frag  = fragment.lower()

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def _cb(hwnd, _):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            n = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            b = ctypes.create_unicode_buffer(n + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, b, n + 1)
            if frag in b.value.lower():
                found[0] = True
                return False   # stop enumeration early
        return True

    ctypes.windll.user32.EnumWindows(_cb, 0)
    return found[0]


# ── Colour palette ────────────────────────────────────────────────── #
# Chosen to stand out against Nightreign's dark, desaturated backgrounds.

_BG      = "#0d0f1e"   # very dark blue — distinct from the game's near-blacks
_SURFACE = "#14172a"   # slightly lighter panel background
_SEP     = "#252840"   # separator line
_FG      = "#e8e8f8"   # primary text (slightly blue-tinted white)
_DIM     = "#6870a0"   # labels / secondary text
_GOLD    = "#ffd700"   # murk / key values — warm yellow pops on dark BG
_CYAN    = "#00e5ff"   # progress numbers — bright cyan
_GREEN   = "#00ff88"   # 3/3 god-roll counter
_BLUE    = "#00aaff"   # 2/3 hit counter
_GREY    = "#707080"   # dud counter (de-emphasised)
_PAUSE_C = "#cc3300"   # pause button — orange-red
_RESUME_C= "#008833"   # resume button — green
_WARN_C  = "#ff8800"   # countdown warning — amber

_WIDTH  = 430
_HEIGHT = 420


# ── Main class ────────────────────────────────────────────────────── #

class BotOverlay:
    """
    Translucent batch-mode HUD.

    Usage (from the main app)::

        overlay = BotOverlay(root)
        overlay.build(screen_w, screen_h)
        overlay.set_pause_callback(app._toggle_pause)
        overlay.start_game_watch()          # auto-show when game launches

        # Inside the bot loop (call via root.after(0, ...)):
        overlay.update(murk=18000, to_buy=10, bought="7/10", ...)
        overlay.append_log("[12:34:56] Analysing relic 3…")

        # When bot stops:
        overlay.destroy()
    """

    def __init__(self, root: tk.Tk):
        self._root      = root
        self._win: tk.Toplevel | None = None
        self._pause_cb  = None
        self._watching  = False
        self._sv: dict[str, tk.StringVar] = {}
        self._pause_btn: tk.Label | None  = None
        self._log_box:  tk.Text  | None   = None

    # ── Lifecycle ──────────────────────────────────────────────────── #

    def build(self, screen_w: int, screen_h: int) -> None:
        """Create the overlay window, positioned bottom-left of the screen."""
        if self._win:
            return

        win = tk.Toplevel(self._root)
        win.overrideredirect(True)           # no title bar / frame
        win.wm_attributes("-topmost", True)  # always above game window
        win.wm_attributes("-alpha", 0.88)    # slight transparency
        win.configure(bg=_BG)

        x = 16
        y = screen_h - _HEIGHT - 48
        win.geometry(f"{_WIDTH}x{_HEIGHT}+{x}+{y}")

        self._win = win
        self._build_ui()
        win.withdraw()          # hidden until game is detected
        win.update_idletasks()
        _apply_noactivate(win)  # must happen after window is realised

    def _build_ui(self) -> None:
        w = self._win

        def sv(key: str, default: str = "—") -> tk.StringVar:
            v = tk.StringVar(value=default)
            self._sv[key] = v
            return v

        # ── Header row: title + batch progress ─────────────────────── #
        hdr = tk.Frame(w, bg=_BG)
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(hdr, text="⚙ RELIC BOT", bg=_BG, fg=_GOLD,
                 font=("Consolas", 10, "bold")).pack(side="left")
        tk.Label(hdr, textvariable=sv("batch", "—"),
                 bg=_BG, fg=_DIM, font=("Consolas", 9)).pack(side="right")

        _hline(w)

        # ── Stats row 1: Murk | Relics to buy | Bought ─────────────── #
        r1 = tk.Frame(w, bg=_BG)
        r1.pack(fill="x", padx=10, pady=2)
        _stat(r1, "Murk",    sv("murk"),   _GOLD)
        _stat(r1, "Relics",  sv("to_buy"), _CYAN)
        _stat(r1, "Bought",  sv("bought"), _CYAN)

        # ── Stats row 2: Current relic # | Analysing ───────────────── #
        r2 = tk.Frame(w, bg=_BG)
        r2.pack(fill="x", padx=10, pady=2)
        _stat(r2, "Relic #",   sv("relic_num"),  _FG)
        _stat(r2, "Analysing", sv("analysing"),  _FG)

        _hline(w)

        # ── Hit counters — three large numbers ─────────────────────── #
        hf = tk.Frame(w, bg=_BG)
        hf.pack(fill="x", padx=10, pady=4)
        hf.columnconfigure(0, weight=1)
        hf.columnconfigure(1, weight=1)
        hf.columnconfigure(2, weight=1)

        for col, (label, key, color) in enumerate([
            ("3 / 3",  "hits_33", _GREEN),
            ("2 / 3",  "hits_23", _BLUE),
            ("Duds",   "duds",    _GREY),
        ]):
            cell = tk.Frame(hf, bg=_BG)
            cell.grid(row=0, column=col)
            tk.Label(cell, text=label, bg=_BG, fg=_DIM,
                     font=("Consolas", 8)).pack()
            tk.Label(cell, textvariable=sv(key, "0"), bg=_BG, fg=color,
                     font=("Consolas", 26, "bold")).pack()

        _hline(w)

        # ── Pause / Resume button ───────────────────────────────────── #
        bf = tk.Frame(w, bg=_BG)
        bf.pack(pady=(3, 5))
        self._pause_btn = tk.Label(
            bf, text="⏸  PAUSE",
            bg=_PAUSE_C, fg="white",
            font=("Consolas", 10, "bold"),
            padx=24, pady=5, cursor="hand2", relief="flat",
        )
        self._pause_btn.pack()
        self._pause_btn.bind(
            "<Button-1>",
            lambda _: self._pause_cb() if self._pause_cb else None,
        )

        _hline(w)

        # ── Log box ─────────────────────────────────────────────────── #
        lf = tk.Frame(w, bg=_BG)
        lf.pack(fill="both", expand=True, padx=6, pady=(2, 6))
        self._log_box = tk.Text(
            lf, bg="#080b18", fg=_FG,
            font=("Consolas", 7), wrap="word",
            state="disabled", relief="flat", borderwidth=0,
        )
        sb = tk.Scrollbar(lf, orient="vertical",
                          command=self._log_box.yview,
                          bg=_BG, troughcolor=_SURFACE)
        self._log_box.configure(yscrollcommand=sb.set)
        self._log_box.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def show(self) -> None:
        if self._win:
            self._win.deiconify()

    def hide(self) -> None:
        if self._win:
            self._win.withdraw()

    def destroy(self) -> None:
        """Tear down the overlay and stop the game-watch thread."""
        self._watching = False
        if self._win:
            self._win.destroy()
            self._win = None

    # ── Game window watching ───────────────────────────────────────── #

    def start_game_watch(self, fragment: str = "nightreign") -> None:
        """
        Poll every 2 s for the game window.
        Shows the overlay when the game is running; hides it otherwise.
        """
        if self._watching:
            return
        self._watching = True

        def _poll():
            while self._watching and self._win:
                if game_running(fragment):
                    self._root.after(0, self.show)
                else:
                    self._root.after(0, self.hide)
                threading.Event().wait(2.0)

        threading.Thread(target=_poll, daemon=True).start()

    # ── Data updates ───────────────────────────────────────────────── #

    def update(self, **kwargs) -> None:
        """
        Update any stat display.  Call from the bot thread via ``root.after(0, ...)``.

        Accepted keys
        -------------
        murk        int/str   Starting murk amount
        to_buy      str       Relics available  (e.g. "10")
        bought      str       Buy progress      (e.g. "7 / 10")
        relic_num   str       Current relic #   (e.g. "3 / 10")
        analysing   str       Relic being OCR'd (e.g. "3")
        hits_33     int/str   God-roll count
        hits_23     int/str   2/3-hit count
        duds        int/str   Dud count
        batch       str       Batch progress    (e.g. "3 / 20" or "1.5h / 4h")
        """
        if not self._win:
            return
        for key, val in kwargs.items():
            if key in self._sv:
                try:
                    self._sv[key].set(str(val))
                except Exception:
                    pass

    def append_log(self, line: str) -> None:
        """Append one log line.  Must be called from the **main** thread."""
        if not self._win or not self._log_box:
            return
        self._log_box.configure(state="normal")
        self._log_box.insert("end", line.rstrip() + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def set_paused(self, paused: bool, countdown: int = 0) -> None:
        """Update the pause/resume button label and colour."""
        if not self._pause_btn:
            return
        if paused:
            if countdown > 0:
                self._pause_btn.configure(
                    text=f"▶  RESUMING {countdown}…", bg=_WARN_C)
            else:
                self._pause_btn.configure(text="▶  RESUME", bg=_RESUME_C)
        else:
            self._pause_btn.configure(text="⏸  PAUSE", bg=_PAUSE_C)

    def set_pause_callback(self, cb) -> None:
        self._pause_cb = cb


# ── Widget helpers ────────────────────────────────────────────────── #

def _hline(parent: tk.Widget) -> None:
    tk.Frame(parent, bg=_SEP, height=1).pack(fill="x", padx=8, pady=2)


def _stat(parent: tk.Frame, label: str,
          var: tk.StringVar, color: str) -> None:
    """Compact label + value cell, packed left-to-right."""
    cell = tk.Frame(parent, bg=_BG)
    cell.pack(side="left", padx=6)
    tk.Label(cell, text=label, bg=_BG, fg=_DIM,
             font=("Consolas", 7)).pack(anchor="w")
    tk.Label(cell, textvariable=var, bg=_BG, fg=color,
             font=("Consolas", 10, "bold")).pack(anchor="w")
