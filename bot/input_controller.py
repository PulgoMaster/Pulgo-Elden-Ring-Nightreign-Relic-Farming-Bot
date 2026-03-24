"""
Records and replays keyboard/mouse input sequences for game automation.
Uses pynput to record events and replay them with original timing.
"""

import ctypes
import time
import json
from pynput import keyboard, mouse
from pynput.keyboard import Controller as KeyController, Key
from pynput.mouse import Controller as MouseController, Button


def _game_is_foreground(exe_name: str) -> bool:
    """Return True if the foreground window belongs to the given exe (case-insensitive)."""
    if not exe_name:
        return True  # no exe configured — don't block
    try:
        import os
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = user32.GetForegroundWindow()
        pid = ctypes.c_ulong(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
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
        self._ms_listener = None
        # Optional callable: if set, events are only recorded when it returns True.
        # Called on the listener thread for every incoming event.
        self.filter_fn = None
        # Keys in this set are silently ignored (not recorded).  Add the
        # toggle-hotkey string here so it never appears in a recorded sequence.
        self.suppress_keys: set = set()

    def start(self):
        self.events = []
        self.recording = True
        self._start_time = time.time()

        self._kb_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._ms_listener = mouse.Listener(
            on_click=self._on_click,
            on_move=self._on_move,
        )
        self._kb_listener.start()
        self._ms_listener.start()

    def stop(self):
        self.recording = False
        if self._kb_listener:
            self._kb_listener.stop()
            self._kb_listener = None
        if self._ms_listener:
            self._ms_listener.stop()
            self._ms_listener = None

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

    def _on_click(self, x, y, button, pressed):
        if not self._allowed():
            return
        event_type = "mouse_press" if pressed else "mouse_release"
        self.events.append({
            "type": event_type,
            "x": x,
            "y": y,
            "button": "left" if button == Button.left else "right",
            "time": self._timestamp(),
        })

    def _on_move(self, x, y):
        if not self._allowed():
            return
        # Only record moves every ~50ms to avoid flooding
        if self.events and self.events[-1]["type"] == "mouse_move":
            last = self.events[-1]
            if self._timestamp() - last["time"] < 0.05:
                return
        self.events.append({"type": "mouse_move", "x": x, "y": y, "time": self._timestamp()})

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.events, f, indent=2)

    def load(self, path: str):
        with open(path, "r") as f:
            self.events = json.load(f)


class InputPlayer:
    """Replays a recorded sequence of events."""

    def __init__(self):
        self._kb = KeyController()
        self._ms = MouseController()
        self._stop_flag = False
        # Set this to the game exe filename (e.g. "nightreign.exe") to enable
        # focus-guard: inputs are skipped if the game is not the foreground window.
        self.game_exe: str = ""

    def stop(self):
        self._stop_flag = True

    def _game_focused(self) -> bool:
        """Return True if the game window is currently in the foreground."""
        return _game_is_foreground(self.game_exe)

    def tap(self, key: str, hold: float = 0.05):
        """Press and release a single key. Used for menu navigation spam."""
        if not self._game_focused():
            return
        try:
            k = self._parse_key(key)
            self._kb.press(k)
            time.sleep(hold)
            self._kb.release(k)
        except Exception:
            pass

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
                    self._kb.press(self._parse_key(event["key"]))
                    time.sleep(hold)
                except Exception:
                    pass
            elif etype == "key_release":
                try:
                    self._kb.release(self._parse_key(event["key"]))
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
                    self._kb.press(self._parse_key(event["key"]))
                    fired += 1
                    fired_keys.append(event["key"])
                except Exception:
                    pass

            elif etype == "key_release":
                try:
                    self._kb.release(self._parse_key(event["key"]))
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

        return fired, fired_keys

    def play_split(self, events: list, split_after_n_keys: int, mid_pause: float,
                   bypass_focus: bool = False, extra_delay: float = 0.0) -> tuple:
        """
        Replay events with a mid-sequence pause after the first split_after_n_keys
        key_release events have been processed, then continue with the remainder.

        Use this for sequences that cross a UI transition — the pause lets the game
        finish loading before the second section of inputs fires.

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
                time.sleep(mid_pause)
                prev_time = event["time"]   # reset so section-2 timing is relative

            delay = event["time"] - prev_time
            if delay > 0:
                time.sleep(delay)
            prev_time = event["time"]

            etype = event["type"]
            if etype == "key_press":
                try:
                    self._kb.press(self._parse_key(event["key"]))
                    fired += 1
                    fired_keys.append(event["key"])
                except Exception:
                    pass
            elif etype == "key_release":
                try:
                    self._kb.release(self._parse_key(event["key"]))
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

        return fired, fired_keys

    def _parse_key(self, key_str: str):
        """Convert stored key string back to a pynput Key or character."""
        if key_str.startswith("Key."):
            attr = key_str[4:]
            return getattr(Key, attr, key_str)
        return key_str
