"""
Records and replays keyboard/mouse input sequences for game automation.
Uses pynput to RECORD events and ctypes SendInput (hardware scan codes) to REPLAY them.

SendInput with KEYEVENTF_SCANCODE sends hardware-level scan codes, which are
processed by the game's raw input handler and are indistinguishable from a
physical keyboard.  pynput's default virtual-key approach can be ignored by
games that read WM_INPUT / DirectInput directly.
"""

import ctypes
import time
import json
import os
from pynput import keyboard, mouse
from pynput.mouse import Controller as MouseController, Button

# ─── ctypes SendInput structures ──────────────────────────────────────────── #

_user32 = ctypes.windll.user32

INPUT_KEYBOARD        = 1
KEYEVENTF_SCANCODE    = 0x0008
KEYEVENTF_KEYUP       = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         ctypes.c_ushort),
        ("wScan",       ctypes.c_ushort),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_size_t),   # ULONG_PTR — pointer-sized on any platform
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki",   _KEYBDINPUT),
        # MOUSEINPUT is 32 bytes on x64; pad the union to that size so
        # ctypes computes sizeof(INPUT) == 40, matching the Windows ABI.
        ("_pad", ctypes.c_byte * 32),
    ]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("_u",   _INPUT_UNION),
    ]


# Hardware scan codes (Set 1 make codes)
# Extended keys additionally require KEYEVENTF_EXTENDEDKEY.
_SCAN: dict = {
    # ── Letters ──
    'a': 0x1E, 'b': 0x30, 'c': 0x2E, 'd': 0x20, 'e': 0x12,
    'f': 0x21, 'g': 0x22, 'h': 0x23, 'i': 0x17, 'j': 0x24,
    'k': 0x25, 'l': 0x26, 'm': 0x32, 'n': 0x31, 'o': 0x18,
    'p': 0x19, 'q': 0x10, 'r': 0x13, 's': 0x1F, 't': 0x14,
    'u': 0x16, 'v': 0x2F, 'w': 0x11, 'x': 0x2D, 'y': 0x15,
    'z': 0x2C,
    # ── Number row ──
    '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06,
    '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A, '0': 0x0B,
    # ── Punctuation ──
    '-': 0x0C, '=': 0x0D, '[': 0x1A, ']': 0x1B, '\\': 0x2B,
    ';': 0x27, "'": 0x28, '`': 0x29, ',': 0x33, '.': 0x34, '/': 0x35,
    # ── Special ──
    'Key.esc':       0x01,
    'Key.tab':       0x0F,
    'Key.backspace': 0x0E,
    'Key.enter':     0x1C,
    'Key.space':     0x39,
    'Key.caps_lock': 0x3A,
    # ── Shift / Ctrl / Alt ──
    'Key.shift':   0x2A, 'Key.shift_l': 0x2A, 'Key.shift_r': 0x36,
    'Key.ctrl':    0x1D, 'Key.ctrl_l':  0x1D, 'Key.ctrl_r':  0x1D,
    'Key.alt':     0x38, 'Key.alt_l':   0x38, 'Key.alt_r':   0x38,
    # ── Function keys ──
    'Key.f1':  0x3B, 'Key.f2':  0x3C, 'Key.f3':  0x3D, 'Key.f4':  0x3E,
    'Key.f5':  0x3F, 'Key.f6':  0x40, 'Key.f7':  0x41, 'Key.f8':  0x42,
    'Key.f9':  0x43, 'Key.f10': 0x44, 'Key.f11': 0x57, 'Key.f12': 0x58,
    # ── Arrow keys (extended) ──
    'Key.up':    0x48, 'Key.down':  0x50,
    'Key.left':  0x4B, 'Key.right': 0x4D,
    # ── Navigation cluster (extended) ──
    'Key.home':      0x47, 'Key.end':       0x4F,
    'Key.page_up':   0x49, 'Key.page_down': 0x51,
    'Key.insert':    0x52, 'Key.delete':    0x53,
    # ── Misc ──
    'Key.print_screen': 0x37,
    'Key.scroll_lock':  0x46,
    # ── Numpad ──
    'Key.num_lock': 0x45,
    'Key.numpad0':  0x52, 'Key.numpad1': 0x4F, 'Key.numpad2': 0x50,
    'Key.numpad3':  0x51, 'Key.numpad4': 0x4B, 'Key.numpad5': 0x4C,
    'Key.numpad6':  0x4D, 'Key.numpad7': 0x47, 'Key.numpad8': 0x48,
    'Key.numpad9':  0x49,
}

# Keys that need KEYEVENTF_EXTENDEDKEY in addition to KEYEVENTF_SCANCODE
_EXTENDED = frozenset({
    'Key.ctrl_r', 'Key.alt_r',
    'Key.up', 'Key.down', 'Key.left', 'Key.right',
    'Key.home', 'Key.end', 'Key.page_up', 'Key.page_down',
    'Key.insert', 'Key.delete',
    'Key.print_screen',
})


def _sc_for_key(key_str: str):
    """
    Return (scan_code, is_extended) for a key string.
    Falls back to MapVirtualKeyW for characters not in the static table.
    Returns (0, False) if the key cannot be resolved.
    """
    sc = _SCAN.get(key_str)
    if sc is not None:
        return sc, key_str in _EXTENDED

    # Fallback: single character — get VK via VkKeyScanW, then scan code
    if len(key_str) == 1:
        vk = _user32.VkKeyScanW(ord(key_str)) & 0xFF
        if vk:
            sc = _user32.MapVirtualKeyW(vk, 0)  # MAPVK_VK_TO_VSC
            if sc:
                return sc, False

    return 0, False


def _send_key(key_str: str, key_up: bool = False) -> bool:
    """
    Fire a single SendInput keyboard event using a hardware scan code.
    Returns True if Windows accepted the event (SendInput returned 1).
    """
    sc, extended = _sc_for_key(key_str)
    if not sc:
        return False

    flags = KEYEVENTF_SCANCODE
    if key_up:
        flags |= KEYEVENTF_KEYUP
    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY

    inp = _INPUT()
    inp.type          = INPUT_KEYBOARD
    inp._u.ki.wVk     = 0
    inp._u.ki.wScan   = sc
    inp._u.ki.dwFlags = flags
    inp._u.ki.time    = 0
    inp._u.ki.dwExtraInfo = 0

    return _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp)) == 1


# ─────────────────────────────────────────────────────────────────────────── #


def _game_is_foreground(exe_name: str) -> bool:
    """Return True if the foreground window belongs to the given exe (case-insensitive)."""
    if not exe_name:
        return True  # no exe configured — don't block
    try:
        kernel32 = ctypes.windll.kernel32
        hwnd = _user32.GetForegroundWindow()
        pid = ctypes.c_ulong(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h = kernel32.OpenProcess(0x1000, False, pid.value)
        if not h:
            return True
        buf = ctypes.create_unicode_buffer(260)
        sz = ctypes.c_ulong(260)
        ok = kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(sz))
        kernel32.CloseHandle(h)
        if ok:
            return os.path.basename(buf.value).lower() == exe_name.lower()
    except Exception:
        pass
    return True


class InputRecorder:
    """Listens for keyboard and mouse events and stores them with timestamps."""

    def __init__(self):
        self.events = []
        self.recording = False
        self._start_time = None
        self._kb_listener = None
        # Optional callable: if set, events are only recorded when it returns True.
        # Called on the listener thread for every incoming event.
        self.filter_fn = None
        # Keys in this set are silently ignored (not recorded).  Add the
        # toggle-hotkey string here so it never appears in a recorded sequence.
        self.suppress_keys: set = set()
        # Mouse inputs are intentionally not recorded — the bot uses keyboard
        # only.  This prevents accidental mouse events in user-edited sequences.

    def start(self):
        self.events = []
        self.recording = True
        self._start_time = time.time()

        self._kb_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._kb_listener.start()

    def stop(self):
        self.recording = False
        if self._kb_listener:
            self._kb_listener.stop()
            self._kb_listener = None

    def _timestamp(self):
        return round(time.time() - self._start_time, 4)

    def _allowed(self) -> bool:
        """Return True if the current event should be recorded."""
        if not self.recording:
            return False
        if self.filter_fn is not None:
            try:
                return bool(self.filter_fn())
            except Exception:
                return True
        return True

    def _on_key_press(self, key):
        if not self._allowed():
            return
        try:
            k = key.char
        except AttributeError:
            k = str(key)
        if k in self.suppress_keys:
            return
        self.events.append({"type": "key_press", "key": k, "time": self._timestamp()})

    def _on_key_release(self, key):
        if not self._allowed():
            return
        try:
            k = key.char
        except AttributeError:
            k = str(key)
        if k in self.suppress_keys:
            return
        self.events.append({"type": "key_release", "key": k, "time": self._timestamp()})

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.events, f, indent=2)

    def load(self, path: str):
        with open(path, "r") as f:
            self.events = json.load(f)


class InputPlayer:
    """Replays a recorded sequence of events using ctypes SendInput (keyboard)
    and pynput (mouse).  Keyboard events use hardware scan codes so they reach
    the game's raw-input handler regardless of which input API it uses."""

    def __init__(self):
        self._ms = MouseController()
        self._stop_flag = False
        self._held_keys: set[str] = set()   # keys currently pressed (for abort cleanup)
        # Set this to the game exe filename (e.g. "nightreign.exe") to enable
        # focus-guard: inputs are skipped if the game is not the foreground window.
        self.game_exe: str = ""
        # Optional DiagnosticLogger — set by app.py when a batch run starts.
        # When set, every key press/release is logged with scan code + SendInput result.
        self.diag = None
        # Current iteration number for per-iteration bucketing in the diag log.
        self._diag_iter: int = 0

    def stop(self):
        self._stop_flag = True

    def _game_focused(self) -> bool:
        """Return True if the game window is currently in the foreground."""
        return _game_is_foreground(self.game_exe)

    # ── low-level key helpers ──────────────────────────────────────────────── #

    def _press(self, key_str: str):
        ok = _send_key(key_str, key_up=False)
        if ok:
            self._held_keys.add(key_str)
        if self.diag is not None:
            sc, ext = _sc_for_key(key_str)
            self.diag.log_input(self._diag_iter, key_str, "press", sc, ok, ext)

    def _release(self, key_str: str):
        ok = _send_key(key_str, key_up=True)
        self._held_keys.discard(key_str)
        if self.diag is not None:
            sc, ext = _sc_for_key(key_str)
            self.diag.log_input(self._diag_iter, key_str, "release", sc, ok, ext)

    # ── public API ────────────────────────────────────────────────────────── #

    def _release_all_held(self):
        """Release any keys still held — safety cleanup after abort."""
        for key in list(self._held_keys):
            try:
                self._release(key)
            except Exception:
                pass
        self._held_keys.clear()

    def tap(self, key: str, hold: float = 0.05):
        """Press and release a single key. Used for menu navigation spam."""
        if not self._game_focused():
            return
        self._press(key)
        time.sleep(hold)
        self._release(key)

    def play_fast(self, events: list, hold: float = 0.05, gap: float = 0.0,
                  bypass_focus: bool = False):
        """
        Replay events ignoring all original inter-event timing.
        Each key/button is held for `hold` seconds then released.
        `gap` is extra sleep added only after key/mouse release events (between keys).
        Skips all inputs silently if the game window is not in the foreground,
        unless bypass_focus=True (used for diagnostic input tests).
        """
        if not bypass_focus and not self._game_focused():
            return
        self._stop_flag = False
        for event in events:
            if self._stop_flag:
                break
            etype = event["type"]
            if etype == "key_press":
                try:
                    self._press(event["key"])
                    time.sleep(hold)
                except Exception:
                    pass
            elif etype == "key_release":
                try:
                    self._release(event["key"])
                    time.sleep(hold + gap)
                except Exception:
                    pass
            elif etype == "mouse_move":
                self._ms.position = (event["x"], event["y"])
            elif etype == "mouse_press":
                btn = Button.left if event["button"] == "left" else Button.right
                self._ms.press(btn)
            elif etype == "mouse_release":
                btn = Button.left if event["button"] == "left" else Button.right
                self._ms.release(btn)
                time.sleep(hold + gap)
        self._release_all_held()

    def play(self, events: list, speed: float = 1.0, bypass_focus: bool = False,
             extra_delay: float = 0.0) -> tuple:
        """
        Replay events preserving original timing.
        speed > 1 plays faster, speed < 1 plays slower.
        extra_delay adds that many seconds after every key/mouse release on top of
        the original timing — use this to prevent inputs being eaten during
        game-UI transitions.
        Skips all inputs silently if the game window is not in the foreground,
        unless bypass_focus=True (used for Phase 0 which launches the game).
        Returns (fired_count, fired_keys) where fired_keys is the ordered list of
        key strings from key_press events that were actually sent.
        """
        if not bypass_focus and not self._game_focused():
            return 0, []
        self._stop_flag = False
        if not events:
            return 0, []

        prev_time = 0.0
        fired = 0
        fired_keys = []
        for event in events:
            if self._stop_flag:
                break

            delay = (event["time"] - prev_time) / speed
            if delay > 0:
                time.sleep(delay)
            prev_time = event["time"]

            etype = event["type"]

            if etype == "key_press":
                try:
                    self._press(event["key"])
                    fired += 1
                    fired_keys.append(event["key"])
                except Exception:
                    pass

            elif etype == "key_release":
                try:
                    self._release(event["key"])
                    if extra_delay > 0:
                        time.sleep(extra_delay)
                except Exception:
                    pass

            elif etype == "mouse_move":
                self._ms.position = (event["x"], event["y"])

            elif etype == "mouse_press":
                btn = Button.left if event["button"] == "left" else Button.right
                self._ms.press(btn)

            elif etype == "mouse_release":
                btn = Button.left if event["button"] == "left" else Button.right
                self._ms.release(btn)
                if extra_delay > 0:
                    time.sleep(extra_delay)

        self._release_all_held()
        return fired, fired_keys

    def play_split(self, events: list, split_after_n_keys: int, mid_pause: float = 0.0,
                   wait_fn=None, bypass_focus: bool = False,
                   extra_delay: float = 0.0) -> tuple:
        """
        Replay events with a mid-sequence pause after the first split_after_n_keys
        key_release events have been processed, then continue with the remainder.

        Use this for sequences that cross a UI transition — the pause lets the game
        finish loading before the second section of inputs fires.

        mid_pause: fixed seconds to sleep between sections (used when wait_fn is None).
        wait_fn:   optional callable; called instead of sleeping mid_pause. Use this
                   for dynamic waits (e.g. polling OCR until a screen is ready).

        Returns (fired_count, fired_keys) across both sections combined.
        """
        if not bypass_focus and not self._game_focused():
            return 0, []
        self._stop_flag = False
        if not events:
            return 0, []

        # Find the index at which to inject the pause (after Nth key_release)
        _kr_seen = 0
        _split_idx = len(events)   # default: no split (play all normally)
        for _i, _e in enumerate(events):
            if _e["type"] == "key_release":
                _kr_seen += 1
                if _kr_seen == split_after_n_keys:
                    _split_idx = _i + 1
                    break

        fired = 0
        fired_keys = []
        prev_time = 0.0

        for idx, event in enumerate(events):
            if self._stop_flag:
                break

            # Inject the mid-pause between sections
            if idx == _split_idx:
                if wait_fn is not None:
                    wait_fn()
                else:
                    time.sleep(mid_pause)
                prev_time = event["time"]   # reset so section-2 timing is relative

            delay = event["time"] - prev_time
            if delay > 0:
                time.sleep(delay)
            prev_time = event["time"]

            etype = event["type"]
            if etype == "key_press":
                try:
                    self._press(event["key"])
                    fired += 1
                    fired_keys.append(event["key"])
                except Exception:
                    pass
            elif etype == "key_release":
                try:
                    self._release(event["key"])
                    if extra_delay > 0:
                        time.sleep(extra_delay)
                except Exception:
                    pass
            elif etype == "mouse_move":
                self._ms.position = (event["x"], event["y"])
            elif etype == "mouse_press":
                btn = Button.left if event["button"] == "left" else Button.right
                self._ms.press(btn)
            elif etype == "mouse_release":
                btn = Button.left if event["button"] == "left" else Button.right
                self._ms.release(btn)
                if extra_delay > 0:
                    time.sleep(extra_delay)

        self._release_all_held()
        return fired, fired_keys
