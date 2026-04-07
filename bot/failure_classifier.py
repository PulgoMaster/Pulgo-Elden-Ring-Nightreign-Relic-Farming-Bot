"""
Failure classifier — turn raw failure events into structured records that
the diagnostic logger can aggregate and the Export Diagnostics panel can
summarize.

The goal is to answer the question "did the system fail us, or did the
program fail us?" for every failure the bot recovers from.

Categories
----------
SYSTEM   game state, hardware, OS, network — things outside our control.
         Examples: black-frame timeout, GPU OOM, screen capture empty,
         game process death, Steam launch fail, FPS drop confirmed.

INPUT    key delivery — SendInput returned ok but the game didn't react,
         or SendInput failed outright.
         Examples: SendInput WinError, RIGHT advance failed after 3 retries,
         Phase 1 F-buy-fail-in-place, post-yield input drop.

OCR      text reading — EasyOCR ran but the result was unusable.
         Examples: empty result on populated slot, low confidence,
         curse pixels visible but no curse matched, name found but all
         passives empty (the v1.7.1 regression signature).

STATE    bot internal logic — our model of the game state was wrong.
         Examples: unexpected menu row (input doubling), stale cursor,
         settle empty after RIGHT-skip retry, P3 consecutive fails.

USER     human interference — already detected by the OS-level hook in
         DiagnosticLogger.  Reclassified here so it shows up in the
         same aggregate view.

Severity
--------
INFO     event was handled cleanly, just being recorded for context.
WARN     event triggered a recovery path; iteration continued.
ERROR    event ended an iteration or required ESC + Phase 0 recovery.
FATAL    event required restarting the game or stopped the run.
"""

import datetime
import threading
import time


# Public category constants — keep these stable, they show up in
# aggregated counts and the user-facing Export Diagnostics report.
SYSTEM = "SYSTEM"
INPUT  = "INPUT"
OCR    = "OCR"
STATE  = "STATE"
USER   = "USER"

INFO  = "INFO"
WARN  = "WARN"
ERROR = "ERROR"
FATAL = "FATAL"

_VALID_CATEGORIES = {SYSTEM, INPUT, OCR, STATE, USER}
_VALID_SEVERITIES = {INFO, WARN, ERROR, FATAL}


def classify(category: str, subcategory: str, evidence: dict | None = None,
             severity: str = WARN) -> dict:
    """Build a structured failure record.

    Args:
        category:    One of SYSTEM/INPUT/OCR/STATE/USER.
        subcategory: Free-form short tag (e.g. "black_frame_timeout",
                     "right_advance_drop", "curse_pixels_no_match").
                     Used for aggregation — keep it consistent.
        evidence:    Free-form dict with whatever context the call site
                     has (cycle, slot, retries, raw_text, conf, durations).
                     Will be serialized into the .diag entry verbatim.
        severity:    INFO/WARN/ERROR/FATAL.

    Returns:
        Dict with keys: ts, category, subcategory, severity, evidence.
    """
    if category not in _VALID_CATEGORIES:
        category = STATE   # mis-tagged calls land in STATE so we notice
    if severity not in _VALID_SEVERITIES:
        severity = WARN
    return {
        "ts":          time.time(),
        "ts_str":      datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "category":    category,
        "subcategory": str(subcategory)[:64],
        "severity":    severity,
        "evidence":    dict(evidence) if evidence else {},
    }


# ─────────────────────────────────────────────────────────────────────────── #
# Aggregator — kept here so DiagnosticLogger can hold one and Export
# Diagnostics can read counts directly without round-tripping through the
# .diag text file.

class FailureAggregator:
    """Thread-safe rolling collection of classified failures.

    Tracks per-category and per-(category, subcategory) counts so the
    summary can show "INPUT/right_advance_drop: 23" without re-parsing
    the .diag file.

    Also keeps the most recent N records in full for the Export Diagnostics
    "top events" section, so the user can paste them to me and I can see
    the actual evidence dicts.
    """

    def __init__(self, recent_cap: int = 50):
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}              # "CAT/sub" → n
        self._cat_counts: dict[str, int] = {}          # "CAT" → n
        self._severity_counts: dict[str, int] = {}     # "SEV" → n
        self._recent: list[dict] = []
        self._recent_cap = recent_cap

    def add(self, record: dict) -> None:
        with self._lock:
            cat = record.get("category", STATE)
            sub = record.get("subcategory", "?")
            sev = record.get("severity", WARN)
            self._cat_counts[cat] = self._cat_counts.get(cat, 0) + 1
            key = f"{cat}/{sub}"
            self._counts[key] = self._counts.get(key, 0) + 1
            self._severity_counts[sev] = self._severity_counts.get(sev, 0) + 1
            self._recent.append(record)
            if len(self._recent) > self._recent_cap:
                self._recent.pop(0)

    def snapshot(self) -> dict:
        """Return a deep-ish copy for Export Diagnostics."""
        with self._lock:
            return {
                "counts":          dict(self._counts),
                "cat_counts":      dict(self._cat_counts),
                "severity_counts": dict(self._severity_counts),
                "recent":          list(self._recent),
                "total":           sum(self._cat_counts.values()),
            }

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()
            self._cat_counts.clear()
            self._severity_counts.clear()
            self._recent.clear()
