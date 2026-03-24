# Changelog

All notable changes to this project are documented here.

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
