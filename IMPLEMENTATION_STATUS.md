# Relic Bot — Implementation Status
Last updated: 2026-03-30 | Current version: v1.6.0

---

## COMPLETED — v1.6.0 (2026-03-30, Session 2)

### Bot Reliability
- **Phase 1 settle redesign**: `_P1_BATCH_RETRIES = 1`, no pre-poll sleep, 3.0 s flat poll interval
- **GPU worker cap**: max 4 workers with GPU ON, max 8 with CPU-only; `_on_gpu_toggle` clamps on switch
- **Murk validation after ESC recovery**: validates murk is a clean multiple of relic cost; resets iteration if not; `_mval > 0` OCR-failure guard
- **`_async_iter_abort_cleanup`**: corrects `_istate["total"]` on any early buy-loop exit so workers can finalize; fixes HIT folder rename + info.txt write failures from 200-iter test run
- **Excluded Hits folder condition fix**: was capturing passive-excluded but not curse-blocked relics; fixed to `is_curse_blocked OR is_passive_excluded`

### UI / UX
- **Smart Throttle in all modes**: no longer gated to Async — visible and functional everywhere
- **Curse Filter hidden in Normal mode**: shown/hidden by `_on_relic_type_change`; called on startup + profile load; default relic type changed to "normal"
- **Scenic/Deep Scenic Flatstone icons**: two 128×128 circular PNGs in `ui/relic_icons/`; displayed across all Relic Criteria tabs via `RelicBuilderFrame`; swap on mode change
- **Odds text selectable**: "Odds (per relic)" replaced `ttk.Label` with `tk.Text(state="disabled")` in both Exact Relic and Passive Pool tabs — text can be selected and copied
- **Mousewheel on Curse Filter + Excluded Passives listboxes**: all four listboxes now scroll locally on hover

### Relic Criteria
- **Compat-group variant exclusion**: `_update_exclusions` now excludes tier variants of non-grouped passives via `_passive_variants()`; previously non-grouped passives had no exclusion effect on other slots

---

## COMPLETED — v1.6.0 (2026-03-30, Session 1)

### Critical Bug Fixes
- **Bot stall after Phase 0**: `_exclude_buy_phase` used before definition → `UnboundLocalError` killed bot thread silently in all modes; pre-initialized before retry loop
- **`verify_shop_item` OCR hang**: was running EasyOCR on unscaled 869×936 px ROI (60–120 s); added 600 px max-dimension downscale; both call sites temporarily archived (`if False:`) pending proper testing
- **Async grace period**: dynamic `grace = max(90, queue_size × 20)` scaling; fixes timeout on CPU-only laptop processing 112 relics

### Backlog Mode
- **Mid-cycle analysis bug fixed**: `capture_only` flag now respected in Phase 2 slot loop; returns image tuples not OCR dicts
- **Re-processing bug fixed**: `backlog_meta_done.json` rename prevents re-scanning already-processed folders
- **info.txt OCR crop fixed**: backlog tasks now pass `crop_left`/`crop_top` preview fractions instead of falling back to sell-screen crop

---

## COMPLETED — v1.5.1

### Smart Analyze — fully integrated
- Toggle UI: Batch Mode Settings row 5, col 2
- Modules: `bot/smart_rules.py` (8 rules), `bot/game_knowledge.py` (2,400+ lines)
- Async path (`_analyze_relic_task`): calls `evaluate_relic()` on non-matching relics
- Sync path (`_run_iteration_phases`): same logic, fires in Phase 2 scan loop (Phase 4 eliminated in v1.6.0)
- On hit: saves screenshot to `smart_hits/` subfolder, appends to `smart_hits.log`, logs to overlay, increments live `_ov_smart_hits` counter
- Profile save/load: `"smart_analyze"` key

### GPU Acceleration — `bot/relic_analyzer.py` + `ui/app.py`
- Opt-in checkbox in Batch Mode Settings row 7 with CUDA detection label
- `set_gpu_mode(enabled)` sets module-level flag; `_get_reader()` reloads per-thread Reader if flag changed
- `_check_cuda_available()` detects CUDA at startup; shown in hardware panel + recommendations
- Phase 4 gap: 0.07 s when GPU ON (vs 0.10 s), LPM still overrides to 0.20 s
- Timing model: `sec_analyze = 0.3` GPU / `3.0` CPU; `sec_nav = 0.07` GPU / `0.10` CPU
- Profile save/load: `"gpu_accel"` key

---

## COMPLETED — v1.5.0

### Probability Engine — `bot/probability_engine.py` (complete rewrite)
- All passive probabilities now use exact datamined pool weights from `database/pool_weights.py`
- Normal relics: full conditional probability chain with category exclusion, tier-locked slots
- Deep relics: 9-variant model (size × curse_count), variant-weighted across T2M/T2B configs
- Confirmed datamine finding: TABLE_2200000 is NOT present in any bazaar relic (EquipParamAntique verified)
- Multi-target combos: inclusion-exclusion across arbitrary slot configurations
- Curse probability functions: `prob_curse_pass`, `prob_curse_pass_on_size`
- Return value convention: `0.0` = impossible, `None` = no data, `float > 0` = real probability

### Odds Viewer — `ui/app.py`
- Live probability display in Batch Mode Settings panel
- Shows: odds in N relics, expected iterations, ideal time per iter, expected total time for L loops
- Curse filter factor applied: blocked curses multiply down effective `p_per_relic`
- Setting-aware timing: adjusts for Low Perf Mode, parallel workers, async vs sync
- Arrow key support on slider; live update on all relevant setting changes
- Mode note shows "N curse(s) blocked" when curse filter is active

### Odds Display in Relic Builder — `ui/relic_builder.py`
- Per-passive: `X.XX%  (~1 in N per relic)` with color filter factor
- Impossible passives: explicit "Impossible — not available on {pool} Relics" message
- Impossible combos: "Impossible Combo, can't be rolled on {pool} Relics"
- Combined: "Odds of finding a relic that fulfills at least N of the expected criteria"
- Pair odds: direct `prob_combo_on_relic` call (fixes "odds unknown" bug for pairs)

### Curse Probability System
- Confirmed: curse count is determined by EQA variant selection, NOT a separate roll
- Each T2M (exclusive) passive slot is permanently paired with one curse slot
- A relic with zero curses can ONLY draw from TABLE_2100000 — no exclusive passives reachable
- Any exclusive passive (PA+3, PA+4, Max HP, Affinity+2, etc.) guarantees ≥1 curse
- `_update_curse_odds()`: shows pass-rate label below Blocked Curses panel
- Maximum blocked curses enforced at 21 (3 must remain unblocked)
- Curse label + Odds Viewer both refresh on relic type change

### Matches Log Panel
- Overlay "View Matches" button shows scrollable log of every matched relic
- Matches written to `matches_log.txt` in batch run folder

### Other Fixes
- Analyzed counter correctly tracks relics analyzed (not Stored count)
- Stored counter fixed to show pending async queue backlog
- `batch_output_var` initialization order fixed
- Color deselect safety: restoring previous multi-color set instead of going blank
- Hardware detection: RAM, CPU cores, GPU name shown in Batch Mode Settings
- Batch Mode restructured: Hours mode removed, Loops only (1–1000)

---

## STILL TO DO — Future Features

### Pending (next up)
- **Smart Analyze rule expansion** — same-class passive doubles, high-tier singles (Physical +4, Max HP, etc.), stat pairs for hybrid scaling (Strength+3 + Faith+3, etc.)
- **Relic Advisor improvements** — scope TBD
- **DiagnosticLogger toggle + debug menu** — pending decision: may keep in a separate debug branch or leave as-is in main build

### Medium Priority
- Sound alert on GOD ROLL match
- Discord / email notification on match
- Per-character overlay stats
- Color scheme / legibility improvements (green text flagged as hard to read)
- **Compat-group filtering — Pair & Exact Relic cross-mode impossible** — detect when a pair spans deep-only and normal-only passives and show "Impossible — passives from different modes" (may already be fixed — needs a failing example to confirm)

### Low Priority / Future
- Hotkeys tab: configurable start/stop/reset hotkeys (currently hardcoded)
- Non-16:9 aspect ratio support (currently blocked + warned)
- Faster OCR (Tesseract or tighter pre-crop to reduce EasyOCR input size)
- **Collector Signboard farming mode** — dedicated bot mode for farming Collector Signboard relics. Requires its own navigation sequence and potentially different phase logic since the source and purchase flow differ from the standard Relic Rites bazaar. Signboard has different pool tables (see math doc Section 11B note — Signboard mechanics still partially unverified).
- **1.02 relic farming mode + odds comparison** — support farming version 1.02 relics across all modes (Normal, Deep, Signboard). The Odds Viewer / Relic Builder should compare expected odds across all available sources and recommend which farming mode gives the best probability for the requested combo.

---

## Database Files — What Exists

| File | Status | Source CSV | Notes |
|------|--------|------------|-------|
| `database/weapons.py` | Complete | EquipParamWeapon.csv + EquipParamCustomWeapon.csv | 70 weapons, hero/category/scaling data |
| `database/spells.py` | Complete | Magic.csv | 56 sorceries + 65 incantations, school mapping |
| `database/passive_groups.py` | Complete | AttachEffectParam.csv | GROUP_100 and GROUP_800 definitions |
| `database/normal_relic_categories.py` | Complete | AttachEffectParam.csv + community data | 19-category normal relic system |
| `database/deep_relic_data.py` | Complete | AttachEffectTableParam.csv + community data | 6-category deep relic system, pool lists |
| `database/pool_weights.py` | Complete | AttachEffectTableParam.csv | Per-passive chanceWeight for 8 active pool tables (100/110/200/210/300/310/2M/2.1M). TABLE_2200000 confirmed not used in any bazaar relic. |
| `database/character_stats.py` | Complete | HeroStatusParam.csv + CharaInitParam.csv | All 10 heroes, stats at Lv1/2/12/15, passive upgrade deltas, body scale |
| `database/weapon_tiers.py` | Complete | ReinforceParamWeapon.csv | White/Blue/Purple/Orange rarity multipliers, Uncommon/Rare/Legendary tracks, skill upgrade tracks |
| `database/weapon_skills.py` | Complete | SwordArtsParam.csv + SwordArtsTableParam.csv | 155 named skills with FP costs, categories, pool table base IDs |
| `database/consumables.py` | Complete | AtkParam_Pc.csv + Bullet.csv | All consumables at L1/L2/L3, Scholar damage rankings |
| `database/weapon_scaling.py` | Low priority | PDF source | AP scaling data, not critical |
| `bot/game_knowledge.py` | Complete | Manual + param data | 113 weapons, 414 passives, 10 characters |
| `bot/smart_rules.py` | Complete | Manual | 8 auditable named rules for Smart Analyze |

`database/` files are not integrated into the bot except `pool_weights.py` (used by probability engine) and `deep_relic_data.py` / `normal_relic_categories.py` (used by passives.py compat system).

---

## Known Accuracy Gaps

- `disableParam_NT` flag in EquipParamWeapon is a Smithbox editor flag, NOT a gameplay
  flag. Antspur Rapier has it set but IS in the game. Some weapon analysis may be off.
- Antspur Rapier is not in EquipParamCustomWeapon (the loot pool param) despite being in
  game — there is at least one other weapon sourcing mechanism not yet identified.
- Sorcery school IDs 1 (Moon), 6, 8 (Magma), 10 (Death), 13 (Cold), 14, 15, 28 (Crucible)
  have no corresponding GROUP_800 passive — spells in these schools benefit only from
  Improved Sorceries (broad booster) and elemental attack-up passives.
- C_special (the passive category that does not trigger exclusion when drawn) — exact
  identity still unknown from datamine.
