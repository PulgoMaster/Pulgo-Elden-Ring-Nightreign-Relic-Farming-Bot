# Changelog

All notable changes to this project are documented here.

---

## [1.8.1] — 2026-04-15 — PROFILE RELIABILITY + ODDS VIEWER FIXES

### Profile data protection

- Fixed a bug where profile data for one mode (Normal or Deep of Night) could silently overwrite the other mode's data under specific error paths. The `_loading_profile` guard flag is now held in a `try/finally` across the entire profile load sequence, so any exception during load cleanly releases the flag instead of leaving it stuck (which would have caused subsequent mode switches to silently skip their save-to-memory step).
- Fixed: "Reset to Defaults" and "Create Blank Profile" no longer contaminate the opposite mode's slot with the pre-reset UI state when the user is currently viewing the other mode.
- Crash-safe profile saves: all profile writes (Save, Save As, Create) now use atomic tmp + fsync + os.replace so a mid-save process kill or power loss can't leave a profile file truncated. The existing file on disk is never touched until the new one is fully written to disk.

### Odds Viewer — Combine mode

- Fixed: toggling "Combine both tabs" now immediately refreshes BOTH tab panels with the unified odds view (Build Exact Relic + My Pool + Pairings, all visible together regardless of which tab is active), instead of showing stale single-tab content until the user edits something.
- Combined total at the bottom of the unified view now accurately reflects the aggregate probability across exact + pool + pairings via complement product.
- When Combine is disabled, each tab correctly reverts to its own single-section view. The active tab's value wins in the shared per-relic probability state.
- Added a helpful prompt when Combine is on but neither tab has criteria configured (instead of a blank panel).

### Passive data

- Raider character passive "Damage taken while using Character Skill" now uses its full in-game text: "Damage taken while using Character Skill improves attack power and stamina". The OCR matcher, probability pool tables, UI dropdowns, and categorization all use the same canonical name. Existing profiles saved with the truncated form auto-migrate on load.

### Reliability / crash-safety (silent improvements)

- App config, calibration data, timing data, and per-iteration backlog metadata all now use atomic writes. Abrupt shutdowns mid-save no longer leave any of these files corrupt.
- Timing-data recorder now uses a split-lock design: the brief data-lock protects dict mutations, and a separate disk-lock serializes file saves. Analyzer threads no longer block each other during the fsync stage of a timing save.

---

## [1.8.0] — 2026-04-10 — FIRST PUBLIC RELEASE

This is the first public release of RelicBot. All features listed in the changelog below have been tested and verified. Versions prior to 1.8.0 were pre-release builds used during development and testing.

See README.md for a full feature overview and INSTALLATION.md for setup instructions.

---

## [1.7.3] [Pre-Release] — 2026-04-10 — SETTLE LOOP FIX + GPU STALL ELIMINATION + END-OF-LIST WRAP CLAMP

### Settle loop fix
- Moved `check_text_visible("insufficient murk")` out of the settle poll loop — was running full-screen `nav_ocr` on every poll, causing indefinite GPU lock contention. Now runs once after the loop exits on the last captured frame.
- Added hard poll cap (`_SETTLE_MAX_POLLS = 10`) to both settle loops (primary and RIGHT-skip recovery). Prevents runaway loops regardless of timing.

### End-of-list wrap clamp
- Root cause of v1.7.2's `right_advance_doubled` events was buy-qty OCR overcounting (reading 10 instead of 9), NOT key doubling. The cursor walked past the last real relic and wrapped to the beginning.
- New fast-path clamp: when `matched_idx == 0` and `confirmed >= 2`, the cycle is clamped to the confirmed count and exits cleanly. Mathematically guaranteed — doubled keys advance forward and can never revisit slot 0.
- Renamed diagnostic counter from `right_advance_doubled` to `end_of_list_wrap` for accuracy.

### GPU stall elimination
- Async GPU workers were competing with `input_gpu_yield` during Phase 1/2 RIGHT-key and F-key presses, causing 1000+ GPU stalls per run (300+ seconds of wasted wait time).
- Fix: at Phase 1 start, workers are paused via OCR throttle and `wait_gpu_idle()` confirms all in-flight GPU work has finished before any inputs are sent. Workers resume after settle confirms, processing the backlog during Phase 3 and Phase 0 when no input contention exists.
- All early-exit paths release throttle unconditionally to prevent leaks.

### Taskbar icon fix
- AUMID changed from version-specific (`PulgoMaster.RelicBot.v1.6.5`) to version-independent (`PulgoMaster.RelicBot`). Prevents new taskbar slot on each version bump.
- `iconbitmap` calls reordered before `withdraw()` — Tk on Windows can silently drop icon calls on withdrawn windows.
- Added `SHChangeNotify(SHCNE_ASSOCCHANGED)` at startup to flush stale shell icon cache.

### Near miss folder naming
- Near miss iteration folders now use plain numeric names (e.g. `001`) instead of `NEAR MISS 001` prefix. The `Near Miss/` aggregation folder and screenshots still provide full visibility.
- Fallback folder scan updated to find both old prefixed and new plain-numbered folders.

### Other
- Removed `curse_misses/` folder writes — curse detection proven reliable (0 misses, 1014 hits in Deep mode testing). Diagnostic counter still tracks any future misses.
- Fixed `async_submits` diagnostic counter (was never incremented).
- Probability documentation rewritten for clarity.

---

## [1.7.2] [Pre-Release] — 2026-04-08 — PHASE 1 BUY-QUANTITY VERIFICATION + RIGHT-KEY DOUBLING ELIMINATED + GPU PRIORITY HARDENING

### Phase 2 RIGHT-key doubling — root cause and fix

Even after the Phase 1 buy-quantity fix shipped (see "PHASE 1 BUY-QUANTITY VERIFICATION" below), a residual ~10% of cycles were still producing in-cycle duplicate relics. The root cause turned out to be a separate failure mode: **the Phase 2 RIGHT key was occasionally registering as a double press**, causing the cursor to skip a slot. The 10-item circular menu then wrapped at the end, and the originally-skipped slot was re-recorded as a duplicate of an already-scanned slot.

Three fixes layered together eliminated this entirely:

**1. Windows high-resolution timer (`main.py`)**
Default Windows multimedia timer resolution is ~15.6 ms, which makes `time.sleep(0.05)` jitter by up to ~15 ms. Under GPU contention from concurrent OCR, sleeps could stretch the effective key hold from 50 ms to 100–150 ms — long enough for the game to sample the cursor key on multiple frames. New `_set_high_res_timer()` calls `winmm.timeBeginPeriod(1)` at startup, paired with `_restore_timer()` (`timeEndPeriod(1)`) on exit. Tightens **all** `time.sleep` calls across the bot from ±15 ms to ±1 ms.

**2. Phase 2 RIGHT hold shortened (`ui/app.py`)**
The Phase 2 RIGHT advance press now uses `hold=0.02` (was `0.05`). At 60 fps that's roughly 1.2 game frames — long enough for the game to register the key-down edge, short enough that the key is released before the next frame can re-sample it. Other tap sites (Phase 0 / 1 / 3) keep `hold=0.05` since they're not in tight GPU-contended loops and have never doubled.

**3. Strict nav-priority gate in `_slot_readtext` (`bot/relic_analyzer.py`)**
The original `_wait_for_nav_yield()` only checked `_nav_wants_gpu` once per call — multiple worker threads could pass the gate before the flag was set, queue up at `_gpu_inflight_lock`, and force `input_gpu_yield()` to wait for the entire chain. Workers now re-check `_nav_wants_gpu.is_set()` **after** acquiring the lock and immediately release if the consumer arrived during the acquire race.

### GPU priority architecture — verified and hardened

The bot already had a one-GPU-worker-with-priority-gate architecture for OCR analysis vs game inputs. This release verifies and tightens it:

- **All worker spawn sites now cap GPU mode at 1 worker.** Async path, async hybrid, backlog GPU, and backlog hybrid were already correct. Phase 4 review pipelined OCR was previously capped at 4 — fixed in this release.
- **Phase 4 review worker shutdown is now leak-proof.** Previously, an early-return from Phase 4 (bot stopped, capture error, or analyze exception) used `_t.join(timeout=1.0)` without draining the task queue first — workers could outlive Phase 4 by several seconds and compete with the next iteration's Phase 2 inputs. New `_stop_workers()` helper drains the queue, sets `_capture_done`, joins with a 5 s timeout, and logs a warning if any worker fails to exit. All four Phase 4 exit paths now route through it.

### GPU stall instrumentation

New diagnostic infrastructure to identify GPU lock contention sources:

- `_owned_gpu_lock(tag)` context manager records the current owner of `_gpu_inflight_lock` (call site tag, thread ident, acquire timestamp). Wraps every site that holds the lock: `_slot_readtext` ("slot_ocr"), `nav_ocr` ("nav_ocr"), `_nav_inline_fallback` ("nav_inline_fallback").
- `input_gpu_yield()` snapshots the prior owner before each acquire and records a stall record if the wait exceeds 100 ms. Records include wait duration, blocker tag, and how long the prior owner had been holding when the wait began. Held-time is clamped to ≥0 to handle the race where the owner changes between snapshot and acquire.
- New **GPU Stall Tracking** section in Export Diagnostics: per-tag table (count, total ms, avg ms, max wait, max held) and a Top-20 worst-stalls timeline. Reset at the start of every batch run.
- This was the diagnostic that pinpointed the queue-contention pattern (`wait_ms >> held_ms`) and led directly to the strict-gate fix.

### Net effect across the fixes
- `p2_wraparound_skip` per cycle: pre-fix = 1.70 → after timer = 0.61 → after timer + hold = 0.00 → after strict gate + 1-worker cap + leak-proof shutdown = 0.00 (steady state).
- `INPUT/right_advance_doubled` events: ~8628 in a pre-fix 72-iter run → 0 expected in steady state.
- `input_yield_max_ms`: ~1171 ms → bounded by a single in-flight readtext rather than a queued chain.

---

## Below: original v1.7.2 release notes (still in effect — Phase 1 buy-qty work)

### The bug this release fixes
A pre-v1.7.2 batch run of 55 iterations revealed that **42% of cycles** were producing in-cycle duplicate relics — the bot was scanning the same relic multiple times within a single Phase 2 sweep. Root cause: the Phase 1 `F → DOWN → F` buy sequence was occasionally registering the DOWN press as 2, 3, or 4 presses under CPU/GPU load. On a circular 1–10 quantity slider, an extra DOWN moves the selection from `10/10` back to `9/10` (or `8/10`, etc.), so the bot ended up buying 9 relics instead of 10. Phase 2 then scanned all 10 expected slots, the cursor wrapped at the end of the smaller-than-expected menu, and the same relics got re-recorded as new ones. Distribution from the test run:

- 9-item menus: 867 cycles (26%)
- 8-item menus: 398 cycles (12%)
- 7-item menus: 88 cycles (2.6%)
- 6 or fewer: 50 cycles (1.5%)

None of this was visible to existing diagnostics — `advance_drop` and `duplicate_skips` only catch consecutive same-as-previous-slot events, not wraparound to an earlier slot.

### Fix: verified buy quantity via OCR
After the DOWN press and before the confirm F press, the bot now OCRs the buy dialog's `X / N` line and verifies that `X` matches the expected purchase count. The cycle's `_batch_size` is replaced with the **actual verified quantity** so Phase 2 cannot wraparound by construction.

- New OCR helpers in `bot/relic_analyzer.py`:
  - `read_buy_quantity(img)` → returns `(X, N, conf)` parsed from the `X/ N` text via numeric+slash allowlist. Three token-shape parsers handle the various ways EasyOCR may segment the text.
  - `read_cycle_murk_cost(img)` → returns the `Required Murk` value parsed from the larger digit field below the X/N line.
  - Both regions are resolution-independent fractional crops, verified against 1080p and 1440p captures: `BUY_QTY_REGION = (0.593, 0.441, 0.658, 0.473)` and `BUY_CYCLE_COST_REGION = (0.594, 0.485, 0.664, 0.517)`.

### Retry chain
When verification fails (X doesn't match expected, OCR can't parse, or murk-cost cross-check disagrees):

1. **Up to 2× Q-back retry** — press Q to close the buy dialog without losing the shop cursor position, then re-attempt `F → DOWN → OCR`. Q is verified via pixel-diff against the pre-press capture (mean abs RGB delta in the dialog area; threshold 8.0 vs measured signal of 17–21 dialog-vs-no-dialog and <2 same-state). If the Q press itself is dropped, up to 3 internal retries before escalating.
2. **One ESC reset retry** — full ESC + Phase 0 replay + buy + verify, in case Q-recovery couldn't restore a clean state.
3. **Abort iteration** — if the ESC retry also fails, log `STATE/buy_qty_unrecoverable ERROR` and end the iteration with a best-effort verified Q-back cleanup.

### Murk-cost fallback
When X/N OCR fails entirely (`None` returned) but the `Required Murk` value reads cleanly, the bot can still derive the quantity as `cost / per_relic_cost`. The per-relic cost is **learned dynamically** from the first clean cycle of each run (`cycle_cost / X`) — no hardcoded constants, self-corrects if costs ever change in a future patch.

### Pixel-diff helper
- New `screen_capture.screen_changed(jpeg_a, jpeg_b, region, threshold)` — generic mean-abs-RGB-delta comparator between two JPEG captures over a fractional region. Used by the Q-back verification path. Constants `_DIALOG_REGION = (0.32, 0.40, 0.68, 0.62)` and `_DIALOG_DIFF_TH = 8.0` exposed for tuning.

### Diagnostic counters and Export Diagnostics
New `Phase 1 buy-qty verify` group renders 7 counters in every Export Diagnostics dump:
- `buy_qty_verified` — happy path (X matched on first try)
- `buy_qty_corrected_q` — recovered via Q retry
- `buy_qty_corrected_esc` — recovered via ESC reset retry
- `buy_qty_unrecoverable` — both paths exhausted, iteration aborted
- `buy_qty_ocr_fail` — OCR returned nothing parseable
- `buy_qty_drift_detected` — X read cleanly but didn't match expected (the input-doubling case)
- `buy_qty_fallback_murk` — recovered via murk-cost fallback when X/N OCR failed

Plus per-cycle `BUY_QTY` lines in the .diag log with full evidence (cycle, expected, got, n_cap, conf, cost, attempt). Failure events route to `OCR/buy_qty_ocr_fail WARN`, `OCR/buy_qty_drift WARN`, `STATE/buy_qty_unrecoverable ERROR`.

### Per-cycle cost
+100–200ms per cycle (extra 30ms in sleeps for dialog render + ~10ms capture + 60–160ms for the two OCR calls). Across a typical overnight run that's about 5–11 minutes added.

---

## [1.7.1] [Pre-Release] — 2026-04-07 — OCR REGION REWORK + CYAN CURSE DETECTION + DEEP DIAGNOSTICS

### OCR Crop Geometry Rework
- **Slot crops now skip the parchment icon and dialog border entirely.** `_SLOT_X_START` raised from 0.27 to 0.348 — eliminates ~95% of non-text pixels feeding into EasyOCR. Smaller crop = faster OCR with no loss of legibility.
- **Slot Y centers re-tuned** to `[0.595, 0.655, 0.715]` (from `[0.600, 0.665, 0.730]`) — measured against actual passive + curse pair positions in the game UI. Each slot now centers exactly on the midpoint of its passive line and curse line.
- **Slot half-height reduced** from 0.032 to 0.028 — adjacent slot crops are now disjoint with a small gap between them. Eliminates the slot 1 → slot 2 text bleed that was contaminating OCR for cursed Deep relics with all three slots populated.
- **Separate name crop region** — `_NAME_X_START = 0.330` (skips relic thumbnail), `_NAME_Y_CENTER = 0.548`, `_NAME_HALF_HEIGHT = 0.014` (tighter fit around the glyph row, no wasted dialog header).
- All geometry verified against both 1080p and 1440p captures — fractions are resolution-independent and the same constants work on both.

### Cyan-Specific Curse Detection
- **Replaced "blue pixel" curse detection with cyan-specific detection.** Curse text in-game is light cyan (high G AND high B with R noticeably lower) — distinct from pure blue UI elements (parchment icons, dialog borders, the relic thumbnail crystal).
- New `_cyan_text_mask()` shared between `_enhance_curse_pixels`, `_is_curse_text`, and `_has_curse_pixels`. Mask: `(G > 140) & (B > 140) & (G - R > 30) & (B - R > 30) & (|G - B| < 40)`.
- Pure-blue UI elements no longer trigger curse pixel detection. White passive text no longer triggers it either.
- `_is_curse_text` (post-OCR token classifier) now correctly routes only actual cyan text into the curse token bucket — no more dormant power text or icon edges getting misclassified as curses.

### Curse Miss Capture (Targeted)
- New per-batch debug capture: when OCR detects cyan curse tokens but `_match_passive` cannot find a match in the curse dictionary, the raw color crop is dumped to `<batch_run>/curse_misses/<idx>_slot<n>_<ts>.png` with a `.txt` sidecar containing the raw OCR tokens.
- Capture gate is post-OCR: only fires when actual cyan tokens were classified, not on every slot with incidental blue chroma.
- Cap of 200 dumps per run as a disk-fill safety net.

### Diagnostic Logger Expansion
- First update to `bot/diagnostic.py` since v1.6.1. **25 new logging methods** covering every feature shipped since: settle events, P2 advance/duplicate, P3 tooltip retry/recovery, P-0.5 black-frame timeouts, MenuNav recalc-on-doubling, GPU AA suppression, input GPU yield gate timing, async backlog, slot OCR pipeline, door generation, game launches, save restores, perf calibration, profile loads.
- **48 aggregate counters** tracked per run, exposed via `get_event_counters()`.
- **Verbosity knob** (`low / normal / high`) gates the spammy per-event lines. NORMAL keeps the diag file readable; HIGH includes per-token detail.

### Failure Classifier
- New `bot/failure_classifier.py` module — every recoverable failure event is now categorized as **SYSTEM** (game/hardware/network), **INPUT** (key delivery), **OCR** (text reading), **STATE** (bot logic), or **USER** (human interference) with severity **INFO / WARN / ERROR / FATAL**.
- `FailureAggregator` keeps thread-safe rolling counts and a bounded list of recent records with full evidence dicts.
- Lets you (and the developer reading the .diag file) immediately answer "did the system fail us, or did the program fail us?" for every recovery event in a run.

### v1.7.1 Regression Signature Watcher
- New post-analyze check: when name OCR succeeds but ALL passive slots come back empty, fires `OCR/name_ok_passives_empty ERROR` immediately on the first relic. Would have caught the v1.7.1 OCR mask regression on cycle 1 instead of overnight.

### Persistent Last-Run Snapshot
- `last_run_diag.json` written next to the executable on every iteration end and on close. Contains counters, failure aggregator snapshot, and runtime state (perf gap mult, GPU AA suppression flags, P3 fail counter, etc.).
- Survives app restart. The "Export Diagnostics" button now resolves data from either the live in-memory logger or the persisted JSON automatically — you can stop a run, close the bot, reopen it days later, and still export the full diagnostic for the previous run.
- Persisted snapshot is wiped only when the next batch run starts.

### Export Diagnostics Overhaul
- Three new sections in the exported report:
  - **v1.7.x Runtime Snapshot** — perf mult, GPU AA state, P3 fail counter, suppression state, etc.
  - **Diagnostic Counters (last run)** — 12 grouped key-value blocks covering every feature.
  - **Failure Classification (last run)** — totals, per-category, per-severity, top 15 subcategories, and the most recent 10 failures with full evidence.
- Plus a **Curse Miss Captures** index that scans the last 3 batch run folders for `curse_misses/*.png` and lists each with its raw OCR text.
- Source attribution on every section ("live (current app session)" vs "persisted (run finished YYYY-MM-DD HH:MM:SS)").

### Reliability (preserved from v1.7.0/1.7.1)
- **Input GPU yield gate** — Phase 1 F-press and Phase 2 RIGHT presses now drain any in-flight EasyOCR call before sending input. Eliminates the cascade where GPU Always Analyze starves the game's input poll.
- **MenuNav recalc-on-unexpected-position** — when an input gets doubled (single tap registers as two), the navigator accepts the new position, recomputes the path, and continues instead of bailing to ESC recovery. Budget: 4 recalcs per navigation.
- **Phase 3 tooltip retry** — single re-grab + re-OCR after 0.25 s before falling through to ESC + Phase 0 recovery, for transient frame issues.
- **Phase 3 consecutive-fails escalation** — two consecutive Phase 3 shop-return failures escalate to iteration restart instead of looping forever.
- **Navigator OCR isolation** — Phase 1 settle OCR runs on a dedicated CPU reader (in CPU mode) or jumps the GPU queue via priority lock (in GPU mode), so navigation OCR never starves on shared resources.
- **Slot-based OCR pipeline** — replaces the legacy line-reconstruction path. Each slot is OCR'd independently which eliminates cross-line token contamination.
- **GPU AA auto-suppression with 2-suppression latch** — three input drops in one iteration auto-suppresses GPU Always Analyze for the rest of that iteration. Re-enables after 10 clean cycles. Latches permanently after the second suppression to avoid oscillation.
- **Phase -0.5 black-frame ceiling** — cumulative 10-minute cap on black-frame timeout extension. Prevents the load wait from spinning forever if the monitor never wakes.

---

## [1.6.5] [Pre-Release] — 2026-04-04 — ENHANCED PROBABILITY ENGINE + UI OVERHAUL

### Probability Engine
- **Enhanced probability model** with exact compat-group elimination across slots — odds now account for how each passive draw removes a category from subsequent slots.
- **Passive exclusion probability** — odds viewer shows P(match AND no excluded passive), not just P(match). "Exclusion impact: ~X%" line shows how much exclusions reduce effective odds.
- **Curse without-replacement** — curses draw without replacement (can't repeat on same relic). Formula changed from independent `((24-N)/24)^k` to exact `C(24-N,k)/C(24,k)`.
- **Both modes supported** — `prob_effective_deep()` (9 variants, TABLE_2000000/2100000) and `prob_effective_normal()` (3 sizes, TABLE_310/210/110).
- All three odds displays (Build Exact Relic tab, Passive Pool tab, Odds Viewer panel) use the enhanced engine.
- Combined odds view when Combine mode is on — shows all groups with per-group subtotals.

### Bug Fixes (from v1.6.4)
- **Curse blocking was completely broken** — `_is_curse_blocked()` read from a key that doesn't exist on per-relic results. Relics with blocked curses were never categorized as EXCLUDED.
- **Missing save files (NR0000.sl2)** on HIT and SMART folders when backlog workers renamed folders before the save copy.
- **Empty batch markers** in live_log for backlog mode — headers now written lazily before first relic result.
- **EXCLUDED matches missing from matches_log.txt** — now logged in both async and sync paths.
- **`_count_relic_tiers` counted EXCLUDED as hits** — iteration summary no longer inflates hit counts.

### Compatibility Groups
- Expanded from 8 to 24 groups (147 to 376 entries). Synced with datamine compatibilityId values.
- Added: weapon-class attack power, stat tiers, HP/FP on weapon attacks, poise, shields, catalysts, skill cooldown, art charge, affinity damage negation.
- Starting Armament Imbue (compat 200) split from Skill/Spell (compat 300).
- Smart Analyze unified to single source of truth (`_variants_compat` from passives.py). Same 311/298 door counts.

### UI Overhaul
- **"Brute Force Analysis" renamed to "Additional CPU Workers"** — clearer, less intimidating.
- **"Low Performance Mode" renamed to "Conservative Timing"** — now only adjusts timing floors. No longer forces workers off or halves OCR cores.
- **"GPU Settings" sub-window** — GPU Acceleration, Hybrid GPU+CPU, GPU Always Analyze, Install button, and status text grouped together.
- **"Optional Matching Features" sub-window** — Smart Analyze and Save Excluded Hits grouped together.
- **Hybrid GPU+CPU without workers toggle** — defaults to 1 GPU + 1 CPU when Additional CPU Workers is off. Workers minimum changed from 2 to 1.
- **Overlay counter toggles** — Near Misses, Smart Hits, Excluded Hits now have toggle checkboxes in Overlay Elements.
- **Overlay always visible** during bot operation — no more hide/show polling based on game focus.
- **Hardware recommendations updated** — now includes Hybrid GPU+CPU, GPU Always Analyze, Smart Analyze. Apply button sets all settings.

---

## [1.6.4] [Pre-Release] — 2026-04-04 — CURSE BLOCKING FIX + COMPAT GROUP OVERHAUL

See v1.6.5 notes above — v1.6.4 was a partial release that included the bug fixes and compat group overhaul. v1.6.5 adds the enhanced probability engine and UI overhaul.

---

## [1.6.0] [Pre-Release] — 2026-03-30 — SESSION 2 FIXES + RELIC CRITERIA POLISH

### 2026-03-30 Session 2 Changes

#### Bot Reliability — Phase 1 Settle Redesign
- `_P1_BATCH_RETRIES` reduced from 2 to 1 — one retry is sufficient; extra retries added latency without benefit.
- Pre-poll sleep before the settle loop removed — the loop itself provides the delay via its 3.0 s poll interval.
- Settle poll interval changed from variable to a flat 3.0 s per attempt (up to 30 s total).

#### Bot Reliability — GPU Worker Cap
- When GPU Acceleration is ON, parallel worker count is capped at 4 (EasyOCR serialises on GPU above this, causing severe throughput loss).
- When GPU is OFF (CPU mode), cap remains at 8.
- Recommendations panel and spinbox tooltip updated to document the GPU/CPU distinction.
- `_on_gpu_toggle` now clamps the current worker count to the new cap on toggle.

#### Bot Reliability — Murk Validation After ESC Recovery
- After a failed Phase 1 settle triggers ESC + Phase 0 recovery, the bot re-reads the murk total and validates it is a clean multiple of the relic cost (600 or 1800).
- If murk is not a multiple, the iteration is reset immediately — guards against cases where the ESC recovery landed on the wrong screen and the murk read is garbage.
- Guarded by `_mval > 0` to skip the check if OCR fails to read murk at all.

#### Bot Reliability — Async Iteration Abort Cleanup
- New `_async_iter_abort_cleanup(iteration, p2_submitted)` method: corrects `_istate["total"]` to `_p2_submitted` on any early exit from the buy loop, ensuring workers can still trigger `_finalize_async_iter_state`.
- Called at three early-return points: top-of-loop bot stop, Phase 1 all-retries-exhausted abort, Phase 3 bot stop.
- **Fixes HIT folder rename bug** from the 200-iter test run (iters 114, 177): `_finalize_async_iter_state` was never called on early exit, so neither `info.txt` nor the folder rename fired.

#### Bot Reliability — Excluded Hits Folder Condition Fix
- `_excl_match_results` filter was using `not self._is_curse_blocked(...)` — this captured passives-excluded relics but NOT curse-blocked ones.
- Fixed to `self._is_curse_blocked(...) or self._is_passive_excluded(...)` in both sync and async finalization paths.

#### UI — Smart Throttle Available in All Modes
- Smart Throttle checkbox is no longer gated to Async mode — it is now visible and functional in Brute Force and all other modes.
- Recommendations panel and `_apply_recommended_settings` also updated to apply Smart Throttle regardless of async state.

#### UI — Curse Filter Visibility
- Curse Filter section is now hidden when relic type is set to Normal (curses only appear on Deep of Night relics).
- Automatically shown/hidden on mode switch via `_on_relic_type_change`.
- Called on profile load and app startup so initial state is always correct.
- Default relic type changed from "night" to "normal".

#### Relic Criteria — Compat-Group Variant Exclusion (Exact Relic tab)
- `_update_exclusions` in `relic_builder.py` extended with a second exclusion path for passives not in any exclusive compat group.
- Previously: non-grouped passives were silently skipped — selecting "Stamina Recovery upon Landing Attacks" had no effect on other slots.
- Now: uses `_passive_variants(val)` to exclude all tier variants sharing the same base name (e.g. base ↔ +1 ↔ +2), preventing duplicate-family passives on the same relic.
- Per-mode filtering is handled by the existing `set_mode_passives()` pool filter — no separate per-mode compat logic needed.

#### Relic Criteria — Scenic Flatstone Icons
- Scenic Flatstone (Normal) and Deep Scenic Flatstone (Deep of Night) PNG icons added to `ui/relic_icons/` (128×128 circular crop, centered on the stone).
- `relic_images.get_flatstone(don)` added — loads and caches the mode-appropriate icon at 64 px.
- Icon displayed in `RelicBuilderFrame` above the notebook tab bar — visible across all three tabs (Build Exact Relic, Passive Pool, Build Advisor).
- Swaps automatically when relic type is toggled between Normal and Deep of Night.
- Replaced the procedural blank gem that was previously only shown in the Build Exact Relic header.

#### UI — Odds Text Now Selectable
- "Odds (per relic)" display in both the Build Exact Relic and Passive Pool tabs replaced `ttk.Label` with `tk.Text(state="disabled")`.
- Text is now selectable and copyable (click to focus, click-drag or Ctrl+A / Ctrl+C) while remaining non-editable.

#### UI — Mousewheel on Curse Filter and Excluded Passives Listboxes
- `_curse_src_lb`, `_blocked_curses_lb`, `_excl_src_lb`, and `_excluded_lb` now bind `<MouseWheel>` and return `"break"` so scrolling over them scrolls the listbox instead of the main window.

---

### 2026-03-30 Changes

#### Backlog Mode — Mid-Cycle Analysis Bug Fixed
- **Root cause**: `capture_only=True` was never checked inside the Phase 2 slot loop. Phase 2 ran full inline analysis even in backlog mode, returned dicts instead of image tuples, and the batch loop silently discarded them — no screenshots were ever saved to the backlog folder.
- **Fix**: Phase 2 now detects `capture_only and not _p2_async` and short-circuits per slot: appends `(step_i, img, "")` to `_bl_captures` and continues without running OCR. Returns `_bl_captures` at the end of `_run_iteration_phases` instead of relic dicts.
- **Note**: Brute-force mode (no backlog, no async) is unaffected — the new path only activates when `capture_only=True`.

#### Backlog Mode — Re-processing Bug Fixed
- **Root cause**: `_process_backlog_run` scanned all `iter*/backlog/` directories every time it was called. In Intermittent Backlog mode, every drain re-processed all previously processed folders.
- **Fix**: After successfully processing a backlog folder, `backlog_meta.json` is renamed to `backlog_meta_done.json`. On subsequent drains, folders containing `backlog_meta_done.json` are skipped immediately.

#### Exclude Analysis While Operations Are Happening — Full Hard Gate
- Redesigned from a throttle tweak into a true hard gate. When enabled (requires Async mode), worker threads are completely stopped for the entire period from the start of Phase -0.5 (game close triggered) through to Phase -0.5 concluding its inputs. Workers are free to run from `_close_game()` firing through to the end of Phase -0.5 game-load inputs.
- `_excl_ops_mode` flag managed entirely at the batch loop level — Phase 0/1/2/3 throttle releases are suppressed when the mode is active.
- Checkbox label renamed from "Exclude Buy Phase" to "⏸ Exclude Analysis While Operations Are Happening" for clarity.

#### Overlay — Mode Tag
- Overlay header now shows the active run configuration as a compact tag (e.g. `Async · Excl.Ops · SmartAnalyze`, `Backlog · Intermittent/5`, `Brute Force`). Updates at the start of each run.

#### Diagnostics — Terminology & Settings Update (`bot/diagnostic.py`)
- Phase labels corrected: `Phase 2 (relic nav)` → `Phase 2 (scan)`, `Phase 4 (sell)` → `Phase 3 (reset)`.
- Log headers: `=== ITERATION {n} START/END` → `=== BATCH {n} START/END`; `OCR_DUMP iter=` → `OCR_DUMP batch=`.
- Session summary line: `Iterations :` → `Batches    :`.
- `log_settings()` now logs 6 additional settings: Smart Throttle, Excl. Analysis (Ops), Smart Analyze, Backlog Mode, Intermittent Backlog, Low Perf Mode.

#### Export Diagnostics — Expanded Settings
- Export now includes 14 settings (was 4): added Smart Analyze, Smart Throttle, Excl. Analysis (Ops), Backlog Mode, Intermittent Backlog, Perf gap multiplier, and Phase 0–3 configured-flag presence.

#### Update.ps1 — GPU Preservation Fix
- GPU torch detection now checks for **both** `cudart64_12.dll` and `torch_cuda.dll` (previously only checked one). Either DLL present triggers GPU-preserve mode.
- `gpu_upgrade_ready` and `gpu_upgrade.log` files are now protected from deletion during update.
- Post-install verification: checks for RelicBot.exe, both GPU DLLs (if GPU was detected), and profiles folder. Prints a red warning block if CUDA DLLs are missing after update.
- Verbose output at every step — mode used, file counts, protected items.

---

### New Phase Architecture — Buy-Phase Scanning

Completely replaces the old Phase 2/3/4 relic review loop with a faster, more reliable scanning approach.

**Old flow**: Buy batch → navigate sell screen → RIGHT × N through relics → scan each → reset cursor
**New flow**: Buy batch → scan post-buy preview screen → RIGHT × N through preview → single F back to shop

- **Phase 0** (navigate to shop) runs once per run; **Phase 1** (buy + preview) → **Phase 2** (scan relics) → **Phase 3** (reset to shop) repeat per batch. Phase 4 is eliminated entirely.
- **Phase 1** always plays the safe alt sequence (F → DOWN → F) with a settle poll of up to 25 attempts (10 s max). Removed fast/safe path distinction for reliability.
- **Phase 2 RIGHT press** replaced `player.play(phase_events[2])` (had 0.914 s baked-in recording gap) with `player.tap("Key.right", hold=0.05)` + a 0.15–0.25 s settle — approximately **6× faster** per relic.
- **Phase 3 F press** replaced `player.play(phase_events[3])` (1.0 s gap) with `player.tap("f", hold=0.05)` — saves ~1 s per batch.
- **Settle check** after Phase 1: polls `analyze()` on preview crop until a relic with passives is confirmed; reuses the confirming capture as slot 0 (no duplicate screenshot). Rejects Scenic/Deep Scenic Flatstone false positives by requiring at least one PASSIVE token or non-empty `passives` list.
- **No-passive guard**: if slot 0 has no passives, calls `verify_shop_item`; retries Phase 1 in-place (up to `_MAX_P2_SETTLE_SKIPS = 4`) then falls through to ESC + Phase 0 recovery.
- **Per-cycle game focus**: window focus fires before each F burst (previously only once at run start) — eliminates missed inputs from focus loss between cycles.
- **ESC recovery**: all failure paths run `_esc_to_game_screen` before returning so Phase 0 always starts from a clean game world.
- **Preview OCR crop**: fraction-based region (`left=0.28`, `top=0.42` of frame) derived from 2560×1440; adapts to any 16:9 resolution. Captures relic name, passives, and curse slots while excluding the shop panel.
- **`analyze()` new params**: `crop_left`, `crop_top` for region cropping; `relic_type="night"` prepends "Deep " to relic name (OCR drops it due to low confidence on that token).
- **OCR downscale**: crop capped at 1000 px wide before EasyOCR; ~2–3× faster on CPU-only machines.
- **`check_text_visible()` downscale** + 50 px minimum height guard — fixes silent failure on high-resolution screens where small `top_fraction` values produced images too short for OCR.
- **Terminology rename**: "Batch" (one outer loop) → "Iteration"; inner buy/scan/reset cycles → "Cycle N". Updated in status bar, log lines, overlay stats, overlay stop dialog, INI section headers.

**Sequence files** (in `sequences/`):
- `phase1_buy_alt.json` — F → DOWN → F (safe buy sequence)
- `phase2_relic_rites_nav.json` — single RIGHT press
- `phase3_navigate_to_sell.json` — single F press
- `phase4_review_step.json` — empty (`[]`), Phase 4 never runs

---

### Relic Criteria Tab — Passive Filtering & Odds Fixes

#### Mode-based passive filtering
- **Deep of Night mode** now shows only passives available in the deep pool (TABLE_2000000 / TABLE_2100000). **Normal mode** shows only passives from the normal pool (TABLE_100 / TABLE_200 / TABLE_300). Passives that can never appear in the selected mode are hidden from all listboxes — Exact Relic slots, Pool tab, and Pairing dialog.
- New `DEEP_POOL_PASSIVES` and `NORMAL_POOL_PASSIVES` frozensets in `probability_engine.py`, derived at module load from actual pool weight tables (326 deep, 290 normal passives).
- Mode propagates automatically: the relic type selected in the "Choose Relic Type" tab filters all subsequent Relic Criteria tabs — no redundant mode prompt.

#### Curse passives removed from selectable lists
- Curse/demerit categories (`Demerits (Attributes)`, `Demerits (Damage Negation)`, `Demerits (Action)`) are no longer shown in the category dropdown or passive listboxes anywhere in the Relic Criteria tab. Curses cannot be added as passive targets.

#### "Impossible Combo" false positive fix
- `prob_combo_on_relic` was returning `0.0` for passives not in the deep pool, causing the odds display to show "Impossible Combo" for valid deep relics whose specific passive simply isn't in the deep pool. Fixed: returns `None` ("unknown/not applicable") instead of `0.0` for pool-miss cases; compat violations still return `0.0` (truly impossible).

#### Pair odds now account for all accepted variants
- Pool tab pairing odds were using only the first variant (`pair["left"][0]`, `pair["right"][0]`). When a passive has multiple accepted variants (e.g. "Physical Attack Up +3" OR "Physical Attack Up +4"), only one variant's probability was reflected. Fixed: sums `prob_combo_on_relic(l, r)` over all compat-valid (left × right) combinations — exact because variants in the same compat group are mutually exclusive.

#### Single-entry odds now account for all accepted variants
- Same fix for single pool entries: uses `prob_any_combo_on_relic([[p] for p in accepted], ...)` to compute P(any accepted variant appears), instead of only using `accepted[0]`.

#### Full passive names in odds panels
- Passive names in odds readouts are no longer truncated (`[:40]`, `[:42]`, `[:22]` cuts removed). `wraplength` on both exact and pool odds labels increased to 860 px so long names wrap instead of being cut off.

#### Mousewheel scrolling in passive listboxes
- Scrolling with the mouse wheel while hovering over passive listboxes (All Passives picker, My Pool, Pairings, Target list) now scrolls the listbox itself instead of the main window. Binds `<MouseWheel>` on each `tk.Listbox` and returns `"break"` to stop event propagation.

---

### Overlay Settings Reorganisation

- **Toggle Hotkey** and **Matches Hotkey** moved from Batch Mode Settings row 3 into the **Overlay Elements** LabelFrame. These settings are logically tied to the overlay, so they now live alongside the other overlay element toggles.
- Both hotkey controls are **disabled** when the Overlay is toggled off — matching the behaviour of other overlay sub-settings. Neither hotkey does anything at runtime when the overlay is disabled.
- Overlay Elements LabelFrame widened (`columnspan 7 → 8`) to accommodate both new rows neatly.

---

### HIT Info Files — Rarity Display

- Hit info files and README files now include a rarity line in the HITS FOUND block: `Rarity: ~1 in X relics (Y.YY%)`.
- Computed from the probability engine's per-relic combined passive probability.

---

### Profile — Auto-load Last Used

- On startup, RelicBot automatically loads the last profile that was saved or loaded. No prompt — runs silently and sets the profile combobox to show the loaded name.
- Implementation: `.last_profile` file in the profiles folder stores the profile name as plain text. Written whenever a profile is saved (`_write_profile`) or loaded (`_load_profile`). Read at startup in `_auto_load_last_profile()`.

---

### GPU Acceleration Improvements

- **4-phase install UI**: Phase 1 (pip dry-run to resolve wheel URL, 30–90 s) → Phase 2 (urllib live download with MB/s + ETA) → Phase 3 (pip local install) → Phase 4 (strip non-essential folders). Progress shown live in the install dialog.
- **Download resume + auto-retry**: Phase 2 retries up to 3× on connection errors. Sends `Range: bytes=X-` to resume a partial download. Between retries: "Connection interrupted — Resuming automatically in 3 s…". After 3 failures: "Unstable Connection — reconnect and try again."
- **Connection error classification**: `ssl.SSLError`, `urllib.error.URLError`, `ConnectionResetError` and similar show a friendly message instead of a raw traceback.
- **Staging approach**: GPU torch installs to `gpu_torch_staging/`; a `gpu_upgrade_ready` flag is written; `_apply_gpu_upgrade()` in `main.py` swaps the staged folder into `_internal/` at next startup before any torch DLLs load. Eliminates the `PermissionError` on `c10.dll` that occurred when trying to overwrite a loaded DLL.
- **`_apply_gpu_upgrade()` retry + log**: 3-attempt `shutil.rmtree` with 1.5 s waits between tries (Windows Defender may briefly lock DLLs). Writes `gpu_upgrade.log` next to the EXE on every startup.
- **No DLL stripping**: `_STRIP_DLLS` removed entirely. Phase 4 now only removes `torch/test/` and `torch/distributed/` (Python folder trees with no DLL dependencies). Never strip files from `torch/lib/` — Windows resolves the full static import chain at load time and any missing DLL causes WinError 126.
- **CUDA torch installed detection**: `_cuda_torch_installed()` checks for `cudart64_12.dll` in `_internal/torch/lib/`. New label state: "GPU torch installed — CUDA init failed: [error]". New button state: "Reinstall GPU Acceleration" when torch is present but CUDA still failing.
- **`os.add_dll_directory` fix** (`main.py`): adds `_internal/torch/lib/` to Windows DLL search path before importing `ui.app`. Fixes CUDA unavailable even when all files are present — PyInstaller's bootloader only registers `_internal/`, not nested subdirectories.
- **CUDA binary filter in build spec**: both `relic_bot.spec` files strip CUDA/GPU DLLs at build time so the distributed ZIP is CPU-only (~256 MB) regardless of what is installed on the build machine.
- **`pip._vendor.distlib` hidden import fix**: both spec files now include `collect_submodules('pip._vendor.distlib')` to fix "Unable to locate finder" crash during GPU install on fresh machines.

---

### Bot Reliability

- **Signboard accidental-purchase fix**: Phase 2 adds `_p2_success` flag; if the relic screen is never confirmed after 3 attempts, aborts before Phase 3. Phase 3 now gates on `check_text_visible("relic rites")` before sending any inputs; if Signboard text is detected instead, exits with ESC only (no F2/confirm keys pressed). Confirmed safe across 200 test iterations.
- **CPU core management**: bot thread runs with `ABOVE_NORMAL` priority. Input events pinned to CPU core 0 via `SetThreadAffinityMask`. OCR worker threads pinned to all cores except core 0. Low-Power Mode halves the OCR worker core count. `configure_torch_threads` also sets `torch.set_num_interop_threads(1)`.
- **ctypes SendInput input reliability**: 55,584/55,584 inputs confirmed successful (100%) across a 200-iteration test run. 

---

### Analysis & Run Features

- **Backlog Analysis**: new checkbox in Batch Mode Settings. When enabled, the bot captures screenshots during the run but defers all OCR to after the batch completes. `_process_backlog_run` spawns a worker pool over the saved screenshots and runs the full pipeline (hits, Smart Analyze, All Hits, near misses). Useful for fast machines where maximising game-loop speed matters more than real-time feedback.
- **System Test + Calibration**: "🔬 System Test" button runs an OCR benchmark (7 passes on a blank image; first pass discarded as JIT warm-up). Results saved to `relicbot_calibration.json` next to the EXE. On startup and at the start of each run, calibration is loaded and used to pre-seed `_first_load_elapsed` and `_perf_gap_mult` so adaptive timing starts calibrated from iteration 1. Auto-saves when baseline is first measured or when the performance multiplier shifts ≥0.05.
- **Excluded Hits folder**: relics that match passive criteria but are blocked by the curse filter are saved to `Excluded Hits/` with screenshots and a summary file.
- **Smart Analyze Hits folder**: `Smart Analyze Hits/` at the batch level consolidates all smart-analyze finds across iterations for easy review.

---

### Data Fixes

- **`pool_weights.py` hyphen fix**: 32 lines corrected — character stat passives (e.g. `[Duchess] Improved Vigor and Strength, Reduced Mind`) had hyphens in their key names instead of commas, causing zero weight → "Impossible" in Relic Builder. All 16 character stat passives across 8 characters now resolve correctly.

---

### UI / UX

- **Real relic icons**: colour-select row now shows actual in-game relic images instead of procedurally drawn diamonds. 8 PNGs (Normal + Deep of Night variants of Red/Blue/Green/Yellow) processed to 128 × 128 circular crops with brightness-weighted centring and sharpening. Bundled in `ui/relic_icons/` in both spec files.
- **Export Diagnostics button**: static button in the Profile row (right of "Restore Defaults"). Exports system info, GPU/CUDA status, key file sizes, `gpu_upgrade.log`, current settings, and the most recent `.diag` file to a timestamped `.txt` next to the EXE. Opens the folder automatically.
- **Mousewheel fix**: main window scroll handler ignores events from dialogs and the overlay window. Overlay Text widgets bind their own `<MouseWheel>` returning `"break"`. Previously, scrolling inside any child window scrolled the main window instead.
- **UI expansion on resize**: inner canvas frame, profile combobox, and save entry fields now stretch horizontally with the window.
- **`.diag` encoding fix**: `read_text(encoding="utf-8", errors="replace")` used everywhere `.diag` and `gpu_upgrade.log` files are read. Fixes `UnicodeDecodeError` on Windows codepage 1252 machines where `.diag` files contain non-UTF-8 bytes.

---

## [1.5.1] [Pre-Release] – 2026-03-27

### Added
- **Matches View hotkey (F8)** — press F8 (configurable) to toggle the overlay between the normal log view and the full-width Matched Relics panel without touching the mouse. "Matches Hotkey" button added to Batch Mode Settings row 3 alongside the existing overlay toggle hotkey. Saved in profile as `matches_hotkey_str` / `matches_hotkey_display`.
- **GPU Acceleration (opt-in)** (`bot/relic_analyzer.py`, `ui/app.py`) — EasyOCR inference can now run on an NVIDIA CUDA GPU instead of CPU. Reduces per-relic analysis time from ~3 s to ~0.3 s (~10× speedup). Toggle added to Batch Mode Settings row 7 with tooltip and inline CUDA detection status label. Saved in profile as `gpu_accel`.
  - `relic_analyzer.set_gpu_mode(enabled)` — sets module-level `_gpu_mode_enabled` flag. Each worker thread auto-reloads its Reader on the next analysis call if the flag changed, so toggling mid-run takes effect without restart.
  - `_get_reader()` now tracks `_thread_local.reader_gpu` and reloads if it differs from `_gpu_mode_enabled`.
  - `_check_cuda_available()` static method added to `RelicBotApp`; called at startup; stored as `self._hw_cuda_available`.
  - Hardware panel shows CUDA status ("CUDA available" / "no CUDA") next to GPU name.
  - Hardware Recommendations panel gains a 5th entry: GPU Acceleration recommendation.
- **Phase 4 gap reduced with GPU** — when GPU Acceleration is ON and LPM is OFF, Phase 4 advance gap drops from 0.10 s to 0.07 s per relic, allowing faster relic browsing. GPU offloads analysis compute, freeing CPU for input handling.
- **Odds Viewer updated for GPU** — timing model accounts for GPU: `sec_analyze = 0.3` when GPU ON (vs 3.0 CPU). `sec_nav_relic = 0.07` when GPU ON. "GPU Accel (~0.3 s/relic)" shown in mode_parts. Static description label updated.
- **Smart Analyze fully integrated** — toggle UI already existed; modules (`smart_rules.py`, `game_knowledge.py`) were already complete. Integration now wired in both analysis paths:
  - Async path (`_analyze_relic_task`): fires on non-matching relics, saves screenshot + log to `smart_hits/`, updates overlay counter.
  - Sync path (`_run_iteration_phases`): same logic added — was missing before this release.
  - Profile save/load: `"smart_analyze"` key.

### Fixed
- **`_get_hw_recommendations` return arity** — expanded from 4-tuple to 5-tuple; caller updated.
- **Smart Analyze sync path missing** — `evaluate_relic()` was not called in the sync pipelined Phase 4 collection loop. Now matches async path behaviour.
- **Smart Analyze setting not persisted** — `smart_analyze` key missing from profile save/load.

---

## [1.5.0] [Pre-Release] – 2026-03-27 — SUBSTANTIAL UPDATE

### Added
- **Matches log panel** — "View Matches" button in the overlay toggles the two log panels into a single full-width scrollable view showing every matched relic with batch #, relic #, tier (2/3 or 3/3), passives, and curses. Clicking "Back to Logs" returns to the normal split log view. All matches are also written to `matches_log.txt` in the batch run folder for persistent review.
- **Analyzed counter** — new overlay stat (next to Stored) showing total relics analyzed in the current batch across all iterations.
- **Probability Engine** (`bot/probability_engine.py`) — complete rewrite using actual datamined pool weights. Replaces rough category-based estimates with exact per-passive probability calculations derived from `AttachEffectTableParam` data.
  - Normal relics: conditional probability chain across tier-locked slots (TABLE_100/200/300), full category exclusion, C_special handling
  - Deep relics: 9-variant model (size × curse_count), variant-weighted probability across all T2M/T2B slot configurations
  - Multi-target combos: inclusion-exclusion for arbitrary slot counts; compat group enforcement
  - Curse filter integration: variant-weighted pass rate applied to any passive probability when curses are blocked
  - `prob_passive_on_relic`, `prob_combo_on_relic`, `prob_at_least_k_of_pool`, `prob_success_in_n`, `prob_curse_pass`, `format_duration`, `color_probability`
- **Odds Viewer** (Batch Mode Settings) — live probability display showing: odds of finding a relic that meets criteria in N relics, expected iterations, ideal time per iteration, expected total time for L loops. Updates instantly when any relevant setting changes. Slider with arrow-key support to sweep relic count.
- **Odds display in Relic Builder** — per-passive probability shown on each row as `X.XX%  (~1 in N per relic)`. Impossible passives (not in pool) and impossible combinations (compat conflict) shown explicitly. Combined pool odds shown for multi-passive targets.
- **Curse Probability System** — curse count on a Deep relic is structurally determined by variant selection, not a separate roll. Each T2M (exclusive) passive slot is permanently paired with one curse slot. A relic with zero curses can only roll from TABLE_2100000 (broad pool) — no exclusive passives are reachable. Full variant-weighted math implemented.
- **Curse filter odds label** — live label below the Blocked Curses panel showing "~X% of Deep relics pass curse filter" with a warning color if fewer than 3 curses remain unblocked.
- **Hardware detection** — auto-detects RAM, CPU core count, and GPU name on startup; shown in Batch Mode Settings hardware recommendations block.
- **Batch Mode restructure** — Hours mode removed (only Loops, capped at 1000). Output Folder moved to Save File section. Hardware recommendations block added. Batch limit has ▲▼ buttons with digit-only validation.
- **Color deselect safety** — deselecting the last active color now restores the previous multi-color selection instead of going to zero (which would block all relics). Auto-dismissing warning label.

### Fixed
- **Stored counter** — was incorrectly displaying total relics analyzed; now correctly shows the number of relics currently pending in the async priority queue backlog.
- **Deep relic probability engine** — previous engine incorrectly included TABLE_2200000 as an active pool. Confirmed from EquipParamAntique: no bazaar relic uses this table. Engine rewritten around confirmed 9-variant model.
- **Odds display impossible-combo detection** — pair probability was returning "odds unknown" when both passives are in the same compat group. Now correctly returns "Impossible Combo" with an explanation.
- **`batch_output_var` initialization order** — variable was initialized inside the batch frame builder (too late), causing errors if other components referenced it during UI construction. Moved to top of `_build_ui`.

---

## [1.4.7] [Pre-Release] – 2026-03-26

### Added
- **Curse detection** — relics with curse passives are now correctly identified during OCR analysis. Previously `analyze()` only matched against `ALL_PASSIVES_SORTED` (which excludes curses), so `matched_relic_curses` was always empty and `_is_curse_blocked()` never fired. All 4 confirmed false positives from the test run (HIT 014, HIT 024, HIT 030, HIT 039) were curse-carrying relics that should have been excluded. Fixed by adding a second-pass match against `ALL_CURSES` when the first-pass passive match returns None.
- **Build Advisor tab** (Relic Builder → Tab 2) — enter a build description (free text or weapon/spell/skill dropdown) to get ranked passive recommendations. Imports selected passives directly into the Exact Relic tab. Max exact target slots raised 10 → 20.
- **Real pool weight odds** — passive probability estimates now use per-passive `chanceWeight` values mined from game data (`AttachEffectTableParam`). `normal_prob()` and `deep_prob()` helpers in `database/pool_weights.py`. Build Advisor and overlay odds display both use these values.

---

## [1.4.5] [Pre-Release] – 2026-03-25

### Added
- **Adaptive input-gap scaling** — the bot tracks game load time each iteration as a proxy for overall system health. As load times grow over a long run (system slowing under sustained use), a `_perf_gap_mult` multiplier rises proportionally (capped at 2.5×). Phase 0, Phase 1, and Phase 2 input gaps all scale by this factor automatically. A `[Adaptive]` log line is emitted when the multiplier changes by ≥ 5%. Resets to 1.0 at the start of each new batch.
- **Low Performance Mode** — new checkbutton in Batch Mode Settings. When enabled: Phase 1 gap base raised from 0.35 s to 0.50 s; Phase 4 initial settle raised from 1.0 s to 2.0 s; Brute Force Analysis automatically disabled. Saved with the profile.
- **Game process priority boost** — immediately after Phase -0.5 confirms the game is in-game, the bot calls `SetPriorityClass(HIGH_PRIORITY_CLASS)` on the game process. This reduces input-drop frequency on loaded systems by ensuring the game gets more CPU time relative to background tasks.
- **WH_MOUSE_LL mouse blocker** — a low-level Windows mouse hook (`SetWindowsHookExW`, `WH_MOUSE_LL`) swallows all mouse button events at the OS message-pump level while menu navigation phases are active. Runs on a dedicated daemon thread with its own `GetMessageW` pump; torn down via `PostThreadMessageW(WM_QUIT)` when no longer needed. Supersedes the previous transparent-overlay approach, which had no effect on games receiving raw input.
- **Change Garb pre-flight check** — Phase 3 now checks for the Change Garb screen at startup before entering the 80-second Sell scan loop. If detected: immediately ESCs out, re-runs Phase 0 → Phase 2 to navigate back to Relic Rites. Since relics are already bought at this point the current iteration is saved, not aborted. Reduces a previously ~80 s loss to ~15 s recovery.
- **Manual Key Recording safeguards** — the Manual Key Recording button now shows a warning tooltip (advanced users only). Each phase tab shows an expanded tooltip describing what that phase does and what to record. Phase -0.5 (Load Skip) and ESC Recovery tabs added as read-only reference panels.

### Fixed
- **Phase 1 buy desync under sustained load** — the buy sequence used a fixed 0.20 s F-to-DOWN gap. Under sustained load (late in long batches), the purchase dialog takes longer to open, causing DOWN to land in the shop navigation layer instead. Phase 1 now uses `play()` (preserves the original ~504 ms recorded timing) with an additional adaptive delay that scales with `_perf_gap_mult`. Eliminates cursor position drift and the cascading desync that followed.
- **Phase 4 first relic captured twice** — the RIGHT arrow at step 1 of Phase 4 was being swallowed by a still-animating Sell screen transition, causing relic 1 to be photographed twice and counted as two distinct relics. An initial settle (1.0 s normal / 2.0 s LPM, both scaled by `_perf_gap_mult`) is now applied before the Phase 4 loop starts.
- **Change Garb menu entered instead of Relic Rites (~22% of iterations)** — Phase 2 (ESC → M → DOWN×3 → F) could drop one DOWN press under load, landing on Change Garb (one step above Relic Rites) instead. Change Garb shares the same F2 tab layout as Relic Rites, so the bot's 80-second sell scan would run to timeout before recovering. Fixed by the Change Garb pre-flight check (see above) and adaptive Phase 2 timing.
- **Stop condition false positives** — the "Insufficient murk" stop condition was firing on dialog-close animations. The check now double-confirms: if the first read returns true, waits 0.5 s and re-checks before accepting the stop.
- **GOD ROLL mislabelling for pairing matches** — relics found via the Passive Pool pairing mode were sometimes labelled GOD ROLL when they should be HIT. Pairing matches (passives containing the `↔` separator) are now capped at HIT tier regardless of how many pairing entries are in the matched list.
- **Phase 4 OCR reading static UI element** — the "Select/Unselect All" button is always visible at the bottom of the Sell screen panel. If OCR captured it (layout shift or partial screen state during settle), the result was logged as a relic entry. These results are now detected by name and silently skipped with a warning log line.
- **Phase 2 Journal false-positive causing repeated ESC loops** — unreliable OCR check for "Relic Rites" title text caused repeated ESC-outs from a correctly-reached screen. Check removed; Phase 3's Sell-tab detection handles wrong-screen recovery.
- **Phase -0.5 looping on hung/crashed game** — the watchdog set `_game_hung` but Phase -0.5 never checked it. Phase -0.5 now exits immediately when `_game_hung` is detected.
- **Phase -0.5 load wait too short on slow hardware** — hard timeout raised from 90 s to 150 s.
- **Case 2 retry (stop condition fired early)** — when the stop condition fires before all planned relics are bought and the spend is divisible, the bot now automatically re-enters the shop (Phase 0 → Phase 1) and buys the remaining relics, then re-reads murk to compute the true total. The retry respects the stop condition and all bot-running guards. If the shop cannot be confirmed on re-entry the bot falls back to the pre-retry count.
- **Bot self-terminating mid-Phase 1** — the overlay's cursor-lock (`ClipCursor`) fought the game's own cursor lock at 60 fps, flickering the cursor and accidentally triggering Force Stop → Close Game. Mouse lock removed entirely.
- **Game not launching from bot background thread** — replaced `os.startfile()` with `subprocess.Popen(explorer.exe)` for reliable Steam URL handling from frozen PyInstaller threads.
- **Tasklist console windows appearing** — all `tasklist`/`taskkill` subprocess calls replaced with direct Windows ctypes API (`EnumProcesses` / `TerminateProcess`), eliminating both console-window flicker and a hang on machines where subprocess creation from the EXE is delayed by security software.
- **Bot window white/unresponsive on launch** — `mss.mss()` called on the main thread during startup caused a permanent hang on machines where security software scans `gdi32.dll` on first use. The call is now deferred to a background thread.

### Changed
- **Phase 0 and Phase 2 timing adaptive** — `extra_delay` for both phases now scales with `_perf_gap_mult` (minimum 0.10 s) instead of a fixed 0.10 s.
- **Phase 4 relic review gap** — reduced from 0.25 s to 0.15 s (0.20 s in Low Performance Mode). No adaptive scaling applied here since relics are already loaded in memory.
- **UI cleanup** — removed three settings that were either dead code or unsafe to change: Analysis Delay (hardcoded to 3.0 s), Close Buffer (hardcoded to 4.0 s), and Confirm Key (bot requires default F key throughout; replaced with a notice label).
- **Overlay redesigned** — W/H resize sliders removed; overlay visibility is now toggled via a configurable hotkey (default F7, rebindable via a button in Batch Mode Settings). Stats continue updating while the overlay is hidden. The hotkey toggle does not steal game focus. Individual sections (Stats, Rolls, Overflow Hits, Process Log, Relic Log) are independently toggleable; "Close game?" prompt added to force-stop flow.
- **Overlay Elements settings** — new sub-section in Batch Mode Settings with per-element visibility toggles. All settings are saved with the profile.

---

## [1.4.4] [Pre-Release] – 2026-03-24

### Fixed
- **Screenshots missing from HIT folders** — v1.4.2's RAM optimisation placed `img_bytes = None` in the `finally` block, which ran before the screenshot-save check. Screenshots were silently never written. Bytes are now cleared after the save section so all HIT/MATCH images are correctly written to disk.
- **Journal screen causing Phase 3 infinite loop** — Phase 2 now performs a post-navigation screen check: OCR confirms "Relic Rites" is visible before proceeding. If a look-alike menu (e.g. the Journal, which has an identical tab layout) is detected, the attempt retries rather than entering Phase 3's 80-second loop on the wrong screen.
- **Zombie process preventing game relaunch** — if the game crashes and leaves its process alive with no window (Windows access-violation crash), the launch-wait loop now force-kills the process after 180 s and lets the relaunch path run cleanly.
- **Murk counter scanning the wrong screen region** — `read_murk()` had an ROI that covered the top-right of the screen, completely missing the shop murk counter (which is top-left). The function now uses a normalised `MURK_SHOP_REGION = (0, 0, 0.45, 0.18)` pinned to the top-left corner where the counter always appears. Resolution-independent.

### Changed
- **`read_murk()` returns `(value, region)` tuple** — the pinned crop region is returned alongside the value so the same region can be reused on the post-buy re-read, avoiding any drift.
- **Global murk expected check** — after the first successful murk read the value is stored. Every subsequent iteration verifies murk matches after save restore. A mismatch aborts the batch immediately with a clear message (save restore failure).
- **Too-low murk guard** — if all three murk read attempts return a value below the relic cost, a specific warning is logged ("need at least N murk to buy one relic; recommend 100k+") rather than silently falling back to failsafe mode.
- **Post-Phase 1 murk validation expanded to 4-case logic**:
  1. Exact match → all planned relics bought; proceed.
  2. Fewer bought, spend divisible → stop condition fired early; bot resumes Phase 1 for the remaining batches automatically.
  3. Amount indivisible → unexpected purchase pattern; restore save and skip iteration.
  4. Overspent → murk after below expected floor; restore save and skip iteration.

---

## [1.4.3] [Pre-Release] – 2026-03-24

### Fixed
- **Phase 4 scanning pre-existing relics** — Phase 4's relic count was derived from murk math (`murk ÷ 1800`) rather than the number of relics actually purchased. If the save file contained pre-existing relics, Phase 4 would scan them too, producing false positives. The bot now re-reads the murk counter immediately after Phase 1 completes and calculates `actual_bought = (murk_before − murk_after) / cost`. Phase 4 uses this value instead of the estimate.
- **Phase 1 not spending all available murk** — the buy loop lacked a stop-condition check in the murk-known code path, so it could run fewer effective purchases than expected if the game's "Insufficient murk" dialog appeared mid-run. The stop condition (`"Insufficient murk"`) is now checked after every buy batch in both the murk-known and fallback paths.

### Changed
- **Phase 1 capped at 1950-relic equivalent** — the buy loop now caps at `ceil(1950 / 10) = 195` batches, matching the game's built-in relic inventory limit. No practical user will ever hit this ceiling, but it prevents unbounded loops on edge-case saves.
- **Removed dead profile key `phase1_max_loops`** — this field was saved and loaded by every profile but was never referenced in the buy loop. Removed from save, load, and UI init to avoid confusion.

---

## [1.4.2] [Pre-Release] – 2026-03-24

### Fixed
- **RAM exhaustion prevention** — async OCR workers now check free system RAM before each inference call. If available RAM drops below 400 MB, the worker sleeps and retries until memory recovers. Prevents PyTorch OOM crashes on machines where the game's memory footprint spikes during loading.
- **Screenshot bytes released immediately** — each worker task's screenshot reference is cleared as soon as the worker picks it up, rather than being held until after analysis completes.
- **Forced GC after every OCR call** — `gc.collect()` runs after each inference so Python returns freed objects and tensor memory to the OS promptly instead of accumulating in the heap.
- **CPU oversubscription fixed** — PyTorch defaults to using all CPU cores per inference. With multiple workers this causes severe thread contention. Workers now share cores evenly: `torch.set_num_threads(cpu_cores / workers)` is applied before any worker starts.
- **Overflow workers adaptive to RAM** — dedicated overflow threads are only spawned when free RAM ≥ 1 GB. On constrained machines, leftover tasks from the previous batch are routed directly through main workers (no extra model instances loaded). With 1 worker + low RAM, overflow is dropped to avoid destabilising the host.
- **Sell value misread as relic name** — OCR was picking up the sell price (e.g. "620 /") as the relic's name because it was the first high-confidence token in the panel. Tokens that start with a digit are now skipped during name extraction.

### Changed
- **Overlay process log cleaned up** — per-relic `"[Async iter X] Relic Y:"` header lines removed from the overlay and run_log (detail is already in live_log via `_log_result`). Screenshot saved lines also suppressed from overlay.
- **Per-relic match notifications in overlay** — when a relic is confirmed as a match, the overlay immediately shows `"★★★ Match Found! Iter X · Relic Y — 3/3"` or `"★★ Match Found! … — 2/3"` without flooding the log with passive lists.
- **Worker RAM warnings updated** — estimate corrected to ~200 MB per worker (was 100 MB). Label turns red at 4+ workers with "needs 16 GB+". Brute Force tooltip now includes a recommendation chart (8 GB → off, 12 GB → 2 workers, 16 GB → 2–3, 24 GB → 4–5, 32 GB+ → 6–8).

---

## [1.4.1] [Pre-Release] – 2026-03-24

### Fixed
- **Game launch retry loop** — if the bot closed the game and Steam was slow to re-register the session, the "waiting for game window" loop could spin forever. Replaced with three-state logic: (A) window visible → proceed; (B) process running, no window yet → keep polling up to 20 s per cycle; (C) process not found → 15 s grace period for Steam to spawn, then relaunch. After 3 failed launch attempts the batch cancels cleanly.
- **Adaptive load time not corrupted by failed attempts** — `_last_load_elapsed` (used to scale the Phase 0 shop detection window) is now only updated when Phase -0.5 succeeds. A timed-out Phase -0.5 returning 0.0 previously overwrote the last known-good value, shrinking the shop detection window to its minimum (35 s) for all subsequent iterations on slow hardware.
- **Game window focus before every phase** — `_focus_game_window` is now called before Phase 1, Phase 2, Phase 3, Phase 4, and at the start of every ESC recovery. Prevents inputs being eaten by an unfocused window after long waits or game transitions.

---

## [1.4.0] [Pre-Release] – 2026-03-24

### Fixed
- **Phase 3: smart F2 loop replaces blind fallback** — tab detection now runs in an 80-second loop: capture → check if on Sell → if not, detect active tab → press exact F2 count → repeat. If detection is inconclusive, presses F2 ×1 to shift position and re-detects. The old "worst-case 10 presses" and blind F2 fallback are removed; F2 ×10 wrapped the circular tab list and made navigation worse, not better.
- **Phase 4 hard gate** — Phase 4 (right-arrow relic review) is now blocked unless Phase 3 explicitly confirms the Sell page. If Phase 3's 80-second loop exhausts without confirming Sell, the iteration aborts cleanly. Previously the bot continued into Phase 4 with a warning, causing right-arrow inputs on the wrong screen.
- **Game window focus added before every phase** — `_focus_game_window` is now called before Phase 1, Phase 2, Phase 3, Phase 4, and at the start of every ESC recovery. Prevents inputs being eaten by an unfocused window after long waits or game transitions.

---

## [1.3.9] [Pre-Release] – 2026-03-24

### Fixed
- **Phase 0 OCR: "Deep Scenic Flatstone" now detected correctly** — EasyOCR splits the item name into separate "Deep" and "Scenic Flatstone" tokens. Detection now uses positional bounding-box check: "Deep" token must be on the same title line (≤40px vertical tolerance) and to the left of "Scenic Flatstone". Previously the substring check never matched and every iteration failed Phase 0.
- **OCR confidence threshold lowered to 0.05** in `verify_shop_item` — "deep" and "1.02" (small description text in stylized game font) were being filtered out at the old 0.25 threshold.
- **v1.02 check order corrected** — item name is confirmed first; 1.02 is only checked if the correct item is already found. Previously 1.02 was checked before the name, causing ambiguous failures when on the wrong item.
- **Phase 0 failure now restarts the same iteration** (was skipping to next) — 3 Phase 0 failures on the same iteration trigger a full iteration restart from clean save. Only after 3 iteration-restarts all failing Phase 0 does the batch abort. Previously used a consecutive-iteration counter which reset on any success.

### Added
- **Overlay "Stored" stat** — shows total relics finalized this run (3/3 + 2/3 + duds combined), displayed next to "Bought". Updates live as each relic is analyzed.
- **Per-iteration counter rollback on reset** — cancelling an iteration (Reset Iteration button or Phase 0 restart) now subtracts that iteration's counter contributions from all overlay stats and rolls back the best-batch scoreboard if it pointed to the cancelled iteration. Works correctly in both Sync and Async modes. Contributions are tracked per-iteration under a lock; in-flight async workers check a cancellation set before updating counters.

### Changed
- Dead code removed: `simpledialog` import, `mss.tools` import, unused `pair_required` keys in `_entry_label` call sites (pairing feature itself is untouched).

---

## [1.4.0] [Pre-Release] – 2026-03-22

### Changed
- **Merged "Relic Type" and "Relic Color Filter" into one panel** — new "Choose Relic Type" section sits directly below Save File & Game Configuration
- Selecting Deep of Night or Normal now automatically updates gem images in the color filter; the redundant "Relic Mode" toggle has been removed
- Relic Type selector moved out of Sequence Phases into its own top-level UI section
- `gem_mode` profile key removed — gem images are now always derived from `relic_type`
- Phase 0 sequence auto-switch on relic type change still fully functional

---

## [1.3.0] [Pre-Release] – 2026-03-22

### Added
- **Translucent batch-mode HUD overlay** — always-on-top, bottom-left of screen
  - Live stats: Murk, Relics to buy, Bought progress, Relic #, Analysing
  - Hit counters: 3/3 God Rolls (green), 2/3 Hits (blue), Duds (grey)
  - Batch progress header (loops or hours)
  - Pause / Resume button with 3-2-1 countdown, synced with the F8 hotkey
  - Scrollable live log feed
  - Clicking the HUD never steals keyboard focus from the game
  - Auto-shows when the Nightreign game window is detected; auto-hides when it isn't
  - Toggle checkbox in Batch Mode Settings

### Removed
- **Live Mode** removed entirely — the bot now runs exclusively in Batch / Timed mode
  - Mode selection radio buttons removed from UI
  - Live Mode settings frame, live delay field, and keep/continue dialog removed

### Fixed
- Overlay is now guaranteed to be destroyed on all abort paths (fatal errors, save-not-found, etc.)

---

## [1.2.0] [Pre-Release] – 2026-03-22

### Added
- **Resolution-aware relic panel crop** — crops to the bottom-right quadrant where the relic info panel sits (`left = 45%`, `top = 65%` of screen dimensions)
- Works at any resolution in Borderless or Fullscreen mode without adjustment
- Screen resolution logged on startup along with the computed crop region

### Changed
- Removed width cap from screen capture — screenshots now at native resolution for best OCR accuracy
- **Sequence files renamed** to clearly reflect their phase:
  - `phase0_setup_don.json`, `phase0_setup_normal.json`, `phase1_buy_loop.json`
  - `phase2_relic_rites_nav.json`, `phase3_navigate_to_sell.json`, `phase4_review_step.json`
- Phase 1 sequence timing updated with more generous gaps for reliable shop navigation
- Sequence Phases section moved lower in the UI (below Relic Criteria, Color Filter, Curse Filter)
- Default Backup and Batch Output folders pre-filled with repo-included directories on first launch

### Fixed
- Phase 0 auto-switches sequence file when relic type changes
- OCR checks now use full resolution — resolves Phase 3 sell-page detection failures

---

## [1.1.0] [Pre-Release] – 2026-03-21

### Changed
- Switched OCR engine to **EasyOCR** (fully on-device, no API key required, no ongoing costs)
- First launch downloads the English OCR model (~100 MB); all subsequent runs are offline
- Analysis speed improved via pipelined capture + analysis: screenshots submitted for OCR immediately after capture so analysis overlaps with navigation to the next relic
- Curse filter now correctly identifies blue-coloured text as curses only

### Fixed
- 2/3 and 3/3 hit classification ordering corrected

---

## [1.0.0] [Pre-Release] – 2026-03-20

### Added
- Initial release
- Batch Mode and Live Mode bot loops
- EasyOCR-based relic passive recognition
- Input recording and replay with game-focus guard
- Save file backup and restore
- Relic criteria builder: Free Text, Build Exact Relic (up to 10 targets), Passive Pool
- Passive compatibility checking (blocks impossible passive combinations)
- Relic Color Filter (Red / Blue / Green / Yellow)
- Curse Filter (reject relics with specific curses)
- Batch output: per-iteration save copies, screenshots for hits, README.txt, PRIORITY.txt, live_log.txt
- Profile save / load system
- Configurable hotkeys (F8 pause, F9 record toggle)
- Scrollable UI with always-reachable controls
