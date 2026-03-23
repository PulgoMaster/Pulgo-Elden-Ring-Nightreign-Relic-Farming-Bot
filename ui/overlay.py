"""
BotOverlay — translucent always-on-top HUD for Batch Mode.

Displays live stats and a log feed without stealing focus from the game.
Only visible while the Nightreign game window is detected on screen.
Clicking the overlay (e.g. the Pause button) does NOT focus it, so
the game window keeps keyboard focus throughout.

Drag the header bar to move the overlay.
Drag the ⤡ grip in the bottom-right corner to resize it.
"""

import tkinter as tk
from tkinter import messagebox as tk_messagebox
import ctypes
import ctypes.wintypes
import threading

# ── Windows API: prevent the overlay from ever stealing focus ─────── #

_GWL_EXSTYLE          = -20
_WS_EX_NOACTIVATE     = 0x08000000   # clicks don't activate (steal focus from) this window
_WS_EX_TOOLWINDOW     = 0x00000080   # hide from taskbar / alt-tab list
_WDA_EXCLUDEFROMCAPTURE = 0x00000011  # invisible to screen capture (Win10 2004+)


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
_PAUSE_C = "#cc3300"
_RESUME_C= "#008833"
_WARN_C  = "#ff8800"
_GRIP_C  = "#3a3d5c"   # resize grip colour

_MIN_W = 340
_MIN_H = 380
_DEF_W = 500
_DEF_H = 620


# ── Main class ────────────────────────────────────────────────────── #

class BotOverlay:
    """
    Translucent batch-mode HUD.  Drag the header to move; drag ⤡ to resize.
    """

    def __init__(self, root: tk.Tk):
        self._root      = root
        self._win: tk.Toplevel | None = None
        self._pause_cb  = None
        self._stop_cb   = None
        self._watching  = False
        self._sv: dict[str, tk.StringVar] = {}
        self._pause_btn: tk.Label | None  = None
        self._log_box:  tk.Text  | None   = None

        # Drag-to-move state
        self._drag_x = 0
        self._drag_y = 0

        # Drag-to-resize state
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_w = _DEF_W
        self._resize_start_h = _DEF_H

    # ── Lifecycle ──────────────────────────────────────────────────── #

    def build(self, screen_w: int, screen_h: int) -> None:
        """Create the overlay window, positioned bottom-left of the screen."""
        if self._win:
            return

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
        win.withdraw()
        win.update_idletasks()
        _apply_noactivate(win)
        _apply_capture_exclusion(win)

    def _build_ui(self) -> None:
        w = self._win

        def sv(key: str, default: str = "—") -> tk.StringVar:
            v = tk.StringVar(value=default)
            self._sv[key] = v
            return v

        # ── Header — drag to move ───────────────────────────────────── #
        hdr = tk.Frame(w, bg=_BG, cursor="fleur")
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(hdr, text="⚙ RELIC BOT", bg=_BG, fg=_GOLD,
                 font=("Consolas", 10, "bold"), cursor="fleur").pack(side="left")
        tk.Label(hdr, textvariable=sv("batch", "—"),
                 bg=_BG, fg=_DIM, font=("Consolas", 9), cursor="fleur").pack(side="right")

        for widget in (hdr,) + tuple(hdr.winfo_children()):
            widget.bind("<ButtonPress-1>",   self._on_drag_start)
            widget.bind("<B1-Motion>",       self._on_drag_move)

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

        # ── Hit counters ─────────────────────────────────────────────── #
        hf = tk.Frame(w, bg=_BG)
        hf.pack(fill="x", padx=10, pady=(4, 6))
        hf.columnconfigure(0, weight=1)
        hf.columnconfigure(1, weight=1)
        hf.columnconfigure(2, weight=1)

        for col, (label, key_run, key_all, color) in enumerate([
            ("3 / 3",  "hits_33", "at_33",   _GREEN),
            ("2 / 3",  "hits_23", "at_23",   _BLUE),
            ("Duds",   "duds",    "at_duds", _GREY),
        ]):
            cell = tk.Frame(hf, bg=_BG)
            cell.grid(row=0, column=col, sticky="n", pady=2)
            tk.Label(cell, text=label, bg=_BG, fg=_DIM,
                     font=("Consolas", 8)).pack()
            tk.Label(cell, text="this run", bg=_BG, fg=_DIM,
                     font=("Consolas", 7)).pack()
            tk.Label(cell, textvariable=sv(key_run, "0"), bg=_BG, fg=color,
                     font=("Consolas", 22, "bold")).pack()
            tk.Label(cell, text="all time", bg=_BG, fg=_DIM,
                     font=("Consolas", 7)).pack(pady=(4, 0))
            tk.Label(cell, textvariable=sv(key_all, "0"), bg=_BG, fg=color,
                     font=("Consolas", 14, "bold")).pack()

        _hline(w)

        # ── Best Batches scoreboard ───────────────────────────────────── #
        bb_hdr = tk.Frame(w, bg=_BG)
        bb_hdr.pack(fill="x", padx=10, pady=(4, 2))
        tk.Label(bb_hdr, text="BEST BATCHES", bg=_BG, fg=_DIM,
                 font=("Consolas", 8, "bold")).pack(anchor="w")

        bb = tk.Frame(w, bg=_BG)
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

        _hline(w)

        # ── Pause / Resume + Abort buttons ──────────────────────────── #
        bf = tk.Frame(w, bg=_BG)
        bf.pack(pady=(3, 5))

        self._pause_btn = tk.Label(
            bf, text="⏸  PAUSE",
            bg=_PAUSE_C, fg="white",
            font=("Consolas", 10, "bold"),
            padx=20, pady=5, cursor="hand2", relief="flat",
        )
        self._pause_btn.pack(side="left", padx=(0, 6))
        self._pause_btn.bind(
            "<Button-1>",
            lambda _: self._pause_cb() if self._pause_cb else None,
        )

        abort_btn = tk.Label(
            bf, text="⏻  STOP",
            bg="#1a1a2e", fg="#cc3300",
            font=("Consolas", 10, "bold"),
            padx=16, pady=5, cursor="hand2", relief="flat",
        )
        abort_btn.pack(side="left")
        abort_btn.bind("<Button-1>", self._on_abort_click)

        _hline(w)

        # ── Log box ──────────────────────────────────────────────────── #
        lf = tk.Frame(w, bg=_BG)
        lf.pack(fill="both", expand=True, padx=6, pady=(2, 0))
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

        # ── Resize grip — bottom-right corner ───────────────────────── #
        grip = tk.Label(w, text="⤡", bg=_GRIP_C, fg=_DIM,
                        font=("Consolas", 10), cursor="se-resize",
                        padx=2, pady=1)
        grip.pack(side="right", anchor="se", padx=2, pady=2)
        grip.bind("<ButtonPress-1>",  self._on_resize_start)
        grip.bind("<B1-Motion>",      self._on_resize_move)

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

    # ── Drag-to-resize ─────────────────────────────────────────────── #

    def _on_resize_start(self, event) -> None:
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_start_w = self._win.winfo_width()
        self._resize_start_h = self._win.winfo_height()

    def _on_resize_move(self, event) -> None:
        if not self._win:
            return
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        new_w = max(_MIN_W, self._resize_start_w + dx)
        new_h = max(_MIN_H, self._resize_start_h + dy)
        x = self._win.winfo_x()
        y = self._win.winfo_y()
        self._win.geometry(f"{new_w}x{new_h}+{x}+{y}")

    # ── Show / hide / destroy ──────────────────────────────────────── #

    def show(self) -> None:
        if self._win:
            self._win.deiconify()

    def hide(self) -> None:
        if self._win:
            self._win.withdraw()

    def destroy(self) -> None:
        self._watching = False
        if self._win:
            self._win.destroy()
            self._win = None

    # ── Game window watching ───────────────────────────────────────── #

    def start_game_watch(self, fragment: str = "nightreign") -> None:
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
        if not self._win:
            return
        for key, val in kwargs.items():
            if key in self._sv:
                try:
                    self._sv[key].set(str(val))
                except Exception:
                    pass

    def append_log(self, line: str) -> None:
        """Append one log line. Must be called from the main thread."""
        if not self._win or not self._log_box:
            return
        self._log_box.configure(state="normal")
        self._log_box.insert("end", line.rstrip() + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def set_paused(self, paused: bool, countdown: int = 0) -> None:
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

    def set_stop_callback(self, cb) -> None:
        self._stop_cb = cb

    def _on_abort_click(self, _event=None) -> None:
        """Show a confirmation dialog before stopping the bot."""
        if not self._stop_cb:
            return
        # Ask on the main thread — messagebox is always thread-safe here
        # since this is already a tkinter event callback on the main thread.
        confirmed = tk_messagebox.askyesno(
            "Stop Bot",
            "Are you sure you want to stop the bot?\n\n"
            "The current iteration will be cancelled.",
            icon="warning",
            parent=self._win,
        )
        if confirmed:
            self._stop_cb()


# ── Widget helpers ────────────────────────────────────────────────── #

def _hline(parent: tk.Widget) -> None:
    tk.Frame(parent, bg=_SEP, height=1).pack(fill="x", padx=8, pady=2)


def _stat(parent: tk.Frame, label: str,
          var: tk.StringVar, color: str) -> None:
    cell = tk.Frame(parent, bg=_BG)
    cell.pack(side="left", padx=6)
    tk.Label(cell, text=label, bg=_BG, fg=_DIM,
             font=("Consolas", 7)).pack(anchor="w")
    tk.Label(cell, textvariable=var, bg=_BG, fg=color,
             font=("Consolas", 10, "bold")).pack(anchor="w")
