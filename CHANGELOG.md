# Changelog

All notable changes to this project are documented here.

---

## [1.4.3] – 2026-03-24

### Fixed
- **Phase 4 scanning pre-existing relics** — Phase 4's relic count was derived from murk math (`murk ÷ 1800`) rather than the number of relics actually purchased. If the save file contained pre-existing relics, Phase 4 would scan them too, producing false positives. The bot now re-reads the murk counter immediately after Phase 1 completes and calculates `actual_bought = (murk_before − murk_after) / cost`. Phase 4 uses this value instead of the estimate.
- **Phase 1 not spending all available murk** — the buy loop lacked a stop-condition check in the murk-known code path, so it could run fewer effective purchases than expected if the game's "Insufficient murk" dialog appeared mid-run. The stop condition (`"Insufficient murk"`) is now checked after every buy batch in both the murk-known and fallback paths.

### Changed
- **Phase 1 capped at 1950-relic equivalent** — the buy loop now caps at `ceil(1950 / 10) = 195` batches, matching the game's built-in relic inventory limit. No practical user will ever hit this ceiling, but it prevents unbounded loops on edge-case saves.
- **Removed dead profile key `phase1_max_loops`** — this field was saved and loaded by every profile but was never referenced in the buy loop. Removed from save, load, and UI init to avoid confusion.

---

## [1.4.2] – 2026-03-24

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

## [1.4.1] – 2026-03-24

### Fixed
- **Game launch retry loop** — if the bot closed the game and Steam was slow to re-register the session, the "waiting for game window" loop could spin forever. Replaced with three-state logic: (A) window visible → proceed; (B) process running, no window yet → keep polling up to 20 s per cycle; (C) process not found → 15 s grace period for Steam to spawn, then relaunch. After 3 failed launch attempts the batch cancels cleanly.
- **Adaptive load time not corrupted by failed attempts** — `_last_load_elapsed` (used to scale the Phase 0 shop detection window) is now only updated when Phase -0.5 succeeds. A timed-out Phase -0.5 returning 0.0 previously overwrote the last known-good value, shrinking the shop detection window to its minimum (35 s) for all subsequent iterations on slow hardware.
- **Game window focus before every phase** — `_focus_game_window` is now called before Phase 1, Phase 2, Phase 3, Phase 4, and at the start of every ESC recovery. Prevents inputs being eaten by an unfocused window after long waits or game transitions.

---

## [1.4.0] – 2026-03-24

### Fixed
- **Phase 3: smart F2 loop replaces blind fallback** — tab detection now runs in an 80-second loop: capture → check if on Sell → if not, detect active tab → press exact F2 count → repeat. If detection is inconclusive, presses F2 ×1 to shift position and re-detects. The old "worst-case 10 presses" and blind F2 fallback are removed; F2 ×10 wrapped the circular tab list and made navigation worse, not better.
- **Phase 4 hard gate** — Phase 4 (right-arrow relic review) is now blocked unless Phase 3 explicitly confirms the Sell page. If Phase 3's 80-second loop exhausts without confirming Sell, the iteration aborts cleanly. Previously the bot continued into Phase 4 with a warning, causing right-arrow inputs on the wrong screen.
- **Game window focus added before every phase** — `_focus_game_window` is now called before Phase 1, Phase 2, Phase 3, Phase 4, and at the start of every ESC recovery. Prevents inputs being eaten by an unfocused window after long waits or game transitions.

---

## [1.3.9] – 2026-03-24

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

## [1.4.0] – 2026-03-22

### Changed
- **Merged "Relic Type" and "Relic Color Filter" into one panel** — new "Choose Relic Type" section sits directly below Save File & Game Configuration
- Selecting Deep of Night or Normal now automatically updates gem images in the color filter; the redundant "Relic Mode" toggle has been removed
- Relic Type selector moved out of Sequence Phases into its own top-level UI section
- `gem_mode` profile key removed — gem images are now always derived from `relic_type`
- Phase 0 sequence auto-switch on relic type change still fully functional

---

## [1.3.0] – 2026-03-22

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

## [1.2.0] – 2026-03-22

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

## [1.1.0] – 2026-03-21

### Changed
- Switched OCR engine to **EasyOCR** (fully on-device, no API key required, no ongoing costs)
- First launch downloads the English OCR model (~100 MB); all subsequent runs are offline
- Analysis speed improved via pipelined capture + analysis: screenshots submitted for OCR immediately after capture so analysis overlaps with navigation to the next relic
- Curse filter now correctly identifies blue-coloured text as curses only

### Fixed
- 2/3 and 3/3 hit classification ordering corrected

---

## [1.0.0] – 2026-03-20

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
