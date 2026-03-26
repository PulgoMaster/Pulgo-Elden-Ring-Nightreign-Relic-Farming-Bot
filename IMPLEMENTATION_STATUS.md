# Relic Bot — Implementation Status
Last updated: 2026-03-25 | Current version: v1.4.6

---

## DONE THIS SESSION (v1.4.6)

### 1. School-Specific Compat Fix — `bot/passives.py`
- All 14 school-specific passives (Improved Glintblade Sorcery, Improved Giants' Flame
  Incantations, etc.) now form their own exclusive compat group (Group 7)
- In the Relic Builder: two school boosters in the same target are correctly blocked
- Fire Attack Up + Improved Giants' Flame correctly ALLOWED (they are different compat
  categories in the actual game param data)
- Previously: any two school boosters could be combined without warning — FIXED

### 2. Odds Display — `ui/relic_builder.py`
- "Odds (estimated)" panel added to both Exact Relic tab and Passive Pool tab
- Per-passive: shows ~1 in N relics for each selected passive
- Combined: multiplied probability for the full combination
- Threshold-aware: if threshold = 2 of 3 slots, shows both "all 3" and "≥2 of 3" estimates
- Expected iterations: ~N relics to find the combo
- Time estimate: expected × ~45 sec/relic, shown as minutes / hours / days
- Disclaimer on all displays: "Estimates only — actual odds depend on game pool weights"
- Probability model used (rough, category-based):
    School boosters (14 passives, Cat 4):    ~1 in 100 per relic
    Stat passives (per stat, 3 tiers):       ~1 in 67 per relic
    Elemental Attack Up (normal tiers):      ~1 in 250 per relic
    Weapon-class Attack Up (Cat 1, large):   ~1 in 333 per relic
    Deep-only passives (+3/+4, Affinity...): ~1 in 333 per relic
    Dormant Powers:                          ~1 in 500 per relic
    Character-specific passives:             ~1 in 200 per relic
    Everything else:                         ~1 in 200 per relic
- NOTE: These numbers will be refined once AttachEffectTableParam.csv pool weights
  are mined. For now they are usable for relative comparison only.

### 3. Exclusion List — `ui/app.py`
(Implemented previous session, committed and released this session)
- "Excluded Passives" section in Batch Mode Settings
- A relic that MATCHES your criteria but ALSO has an excluded passive = REJECTED
- Exception: if the excluded passive is also in your Pool, Pairings, or Build targets,
  the explicit request wins and the exclusion is ignored for that passive
- "Add All Dormant Powers" button for quick setup
- Saves/loads with profile

### 4. Spell School Database — `database/spells.py` (new file)
- Mined from Magic.csv (56 sorceries + 65 incantations)
- School ID → GROUP_800 passive mapping confirmed from param data
- `get_school_passive("O, Flame!")` → "Improved Giants' Flame Incantations"
- `get_spells_for_passive("Improved Dragon Cult Incantations")` → [Lightning Spear, ...]
- Unmapped schools (no relic passive): Magma, Death/Ghostflame, Cold, Crucible, Moon
- NOTE: database/ is kept separate from bot/ until robust enough to integrate

---

## STILL TO DO — Bot Features

### High Priority

#### Smart Analyze Integration (→ v1.4.7)
The data layer is complete (bot/game_knowledge.py + bot/smart_rules.py).
What still needs to happen:
- Toggle in Batch Mode Settings: "Smart Analyze — flag notable relics not matched by criteria"
- In sync + async analysis paths: call `evaluate_relic(passives)` on relics that do NOT
  match the main criteria and are NOT excluded
- If rules fire: copy screenshot + append findings to
  `Recommended Unassigned Hits/smart_summary.txt` in run_dir
- New overlay counter: "Unassigned: N" separate from HIT/GOD ROLL counter
- Profile save/load for the toggle state (`"smart_analyze": bool`)

#### Accurate Pool Odds (refinement of the odds display)
- Mine `AttachEffectTableParam.csv` for actual pool weights per passive
- Replace `estimate_passive_prob()` rough estimates with data-driven values
- Will make the odds display in the Relic Builder genuinely accurate rather than approximate

### Medium Priority

#### More Database Mining
- `SwordArtsParam.csv` / `SwordArtsTableParam.csv` — weapon skill (AoW) data
- `ReinforceParamWeapon.csv` — weapon damage at each reinforcement level (+0 to +10)
- Consumable damage params — thrown pots, knives, etc.
- `CharaInitParam.csv` / `HeroStatusParam.csv` — character base stats per level

#### Bot Features
- Sound alert on GOD ROLL match
- Discord / email notification on match
- Per-character overlay stats

### Low Priority / Future

- Hotkeys tab: configurable start/stop/reset hotkeys (currently hardcoded)
- Phase 3 debug mode: log tab brightness values, standalone tab detection test
- Dead code cleanup: `_passive_variants()` in relic_builder.py:24-28 (unused),
  unused `pair_required` keys (~859/907/910/911)
- Non-16:9 aspect ratio support (currently blocked + warned)
- Faster OCR (Tesseract or tighter pre-crop to reduce EasyOCR input size)
- OCR-based Phase 0/2 menu position verification (reliability uncertain, needs testing)

---

## Database Files — What Exists

| File | Status | Source CSV | Notes |
|------|--------|------------|-------|
| `database/weapons.py` | Complete | EquipParamWeapon.csv + EquipParamCustomWeapon.csv | 70 weapons, hero/category/scaling data |
| `database/spells.py` | Complete | Magic.csv | 56 sorceries + 65 incantations, school mapping |
| `database/passive_groups.py` | Complete | AttachEffectParam.csv | GROUP_100 and GROUP_800 definitions |
| `database/normal_relic_categories.py` | Complete | AttachEffectParam.csv + community data | 19-category normal relic system |
| `database/deep_relic_data.py` | Complete | AttachEffectTableParam.csv + community data | 6-category deep relic system, pool lists |
| `database/pool_weights.py` | Complete | AttachEffectTableParam.csv | 2606 lines — per-passive chanceWeight for all 9 key pool tables (100/110/200/210/300/310/2M/2.1M/2.2M) |
| `database/character_stats.py` | Complete | HeroStatusParam.csv + CharaInitParam.csv | All 10 heroes, stats at Lv1/2/12/15, passive upgrade deltas, body scale |
| `database/weapon_tiers.py` | Complete | ReinforceParamWeapon.csv | White/Blue/Purple/Orange rarity multipliers, Uncommon/Rare/Legendary tracks, skill upgrade tracks |
| `database/weapon_skills.py` | Complete | SwordArtsParam.csv + SwordArtsTableParam.csv | 155 named skills with FP costs, categories, pool table base IDs |
| `database/consumables.py` | Complete | AtkParam_Pc.csv + Bullet.csv | All consumables at L1/L2/L3, Scholar damage rankings |
| `database/weapon_scaling.py` | Low priority | PDF source | AP scaling data, not critical |
| `bot/game_knowledge.py` | Complete | Manual + param data | 113 weapons, 414 passives, 10 characters |
| `bot/smart_rules.py` | Complete | Manual | 8 auditable named rules for Smart Analyze |

None of the `database/` files are integrated into the bot yet — they're built and ready,
waiting for Smart Analyze integration and other feature work.

---

## Known Accuracy Gaps

- `disableParam_NT` flag in EquipParamWeapon is a Smithbox editor flag, NOT a gameplay
  flag. Antspur Rapier has it set but IS in the game. Some weapon analysis may be off.
- Antspur Rapier is not in EquipParamCustomWeapon (the loot pool param) despite being in
  game — there is at least one other weapon sourcing mechanism not yet identified.
- Odds estimates in the Relic Builder are rough until AttachEffectTableParam weights are mined.
- Sorcery school IDs 1 (Moon), 6, 8 (Magma), 10 (Death), 13 (Cold), 14, 15, 28 (Crucible)
  have no corresponding GROUP_800 passive — spells in these schools benefit only from
  Improved Sorceries (broad booster) and elemental attack-up passives.
