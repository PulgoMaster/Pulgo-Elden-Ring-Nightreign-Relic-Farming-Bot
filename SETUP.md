# Elden Ring Nightreign – Relic Bot Setup Guide

A bot that automates relic farming in Elden Ring Nightreign using local OCR to analyze
and match relics against your criteria. No internet connection or account required.

---

## ⚠️ Critical Warnings – Read Before Anything Else

### Save File Safety

- **Always back up your save file manually before using the bot.**
  The bot makes its own backup, but having a second copy you control is essential.
  Your save is located at:
  `C:\Users\<YourName>\AppData\Roaming\Nightreign\<SteamID>\NR0000.sl2`

- **Always give the bot your most current save.**
  The bot uses the save you provide as the template it restores before every
  iteration. That save must be from **before any run you have played**.
  If you play a run after making your save, that save is now "used" — hand it
  to the bot anyway and you risk being flagged by the Nightreign anti-cheat
  system. The fix is simple: whenever you play a run, make a fresh save
  afterwards at Roundtable Hold and update the path in the bot before running
  it again.

---

## Folder Structure

After extracting the release ZIP, your folder looks like this:

```
RelicBot/
├── RelicBot.exe        Launch this to start the bot
├── sequences/          Input sequence files for each phase
├── save_backups/       Bot stores save backups here
├── batch_output/       Batch run results go here
├── profiles/           Your saved bot profiles
├── GUIDE.txt           User guide
├── SETUP.md            This file
└── _internal/          Bot internals (do not modify)
```

---

## Requirements

- Windows 10 or 11
- Elden Ring Nightreign installed via Steam
- **16:9 display** — any resolution (1080p, 1440p, 4K) as long as the aspect ratio is 16:9.
  Ultrawide (21:9), 4:3, and other non-standard ratios are **not supported**.
- No Python or other software needed — everything is bundled in the EXE

> **First run:** The bot downloads its OCR model (~100 MB) automatically on first launch.
> One-time only — after that the bot works fully offline.

---

## First-Time Setup

### 1. Launch the bot

Run `RelicBot.exe` from the extracted folder.

### 2. Configure Save File & Game

| Field | What to enter |
|-------|---------------|
| **Save file** | Path to your `NR0000.sl2` (e.g. `C:\Users\<YourName>\AppData\Roaming\Nightreign\<SteamID>\NR0000.sl2`) |
| **Backup folder** | Point to the `save_backups/` folder inside the RelicBot folder, or any folder you choose |
| **Game executable** | Path to `nightreign.exe` inside your Steam install |
| **Steam App ID** | Pre-filled: `2622380` |

### 3. Select Relic Type

Under **Choose Relic Type**, select your farming mode:
- **Deep of Night** — 1800 murk each (uses `phase0_setup_don.json`)
- **Normal** — 600 murk each (uses `phase0_setup_normal.json`)

Switching relic type automatically swaps the Phase 0 sequence and updates the Relic Criteria passive pool.

### 4. Input Sequences

The `sequences/` folder contains pre-recorded input sequences for each phase.
They are loaded automatically on startup. The active bot loop is:

| Phase | Purpose | Auto-loaded file |
|-------|---------|-----------------|
| **Phase 0 — Setup** | Navigate from Roundtable Hold to the Relic Rites buy screen (runs once per iteration) | `phase0_setup_don.json` or `phase0_setup_normal.json` |
| **Phase 1 — Buy + Preview** | Buy one relic and hold on the post-buy preview screen | `phase1_buy_alt.json` |
| **Phase 2 — Scan** | Single RIGHT press to navigate to the next relic in the Relic Rites panel | `phase2_relic_rites_nav.json` |
| **Phase 3 — Reset** | Single F press to return to the buy screen | `phase3_navigate_to_sell.json` |

> Phase 4 is no longer used — the old sell/review loop has been replaced by buy-phase scanning.
> These sequences assume you start from **Roundtable Hold** with the Relic Rites merchant visible.

### 5. Set Relic Criteria

Use the **Relic Criteria** tabs to define what you are looking for:

- **Build Exact Relic** — specify up to 20 target passive combinations; each target has up to 3 passive slots and a match threshold (e.g. ≥ 2 of 3 must be present). The bot stops when ANY target is satisfied. Incompatible passive combinations are blocked automatically — the listboxes hide conflicting passives as you make selections.
- **Passive Pool** — pick any number of passives; the bot matches when a relic has at least N of them simultaneously. Add **Pairings** to require two specific passives to appear together (counts as one match).
- **Combine** — tick the checkbox at the bottom to match against either tab simultaneously.

Passive lists are automatically filtered to show only passives available in the selected relic mode (Normal or Deep of Night).

### 6. Set Relic Color Filter

Select which relic colours you are hunting for (Red / Blue / Green / Yellow).
Switch between **Normal** and **Deep of Night** gem images using the radio buttons to match the mode you're farming.

### 7. Set Curse Filter (optional)

Add any curses you want to block. Relics carrying a blocked curse will be rejected even if their passives match.

### 8. Configure Batch Mode

The bot runs in **Batch Mode** — it runs for a set number of loops or hours and saves every iteration for manual review.

Point the **Output folder** to `batch_output/` inside the RelicBot folder (or any folder).
After the run, open `README.txt` in the output folder — hits are marked with `*`.

### 9. Save a Profile

Click **Save As…** in the Profile section to save all your settings (save paths, sequences, criteria, filters) to a local JSON file. Profiles are stored only on your machine and are never committed to GitHub.

---

## Hotkeys (work even while the game is focused)

| Key | Action |
|-----|--------|
| **F7** | Show / hide the overlay HUD (configurable) |
| **F8** | Toggle overlay between log view and full Matched Relics panel (configurable) |
| **F9** | Stop bot after current iteration (configurable) |

The bot will automatically stop sending inputs if the Nightreign window loses focus, so alt-tabbing is safe.

---

## Recording Your Own Sequences

If the standard sequences don't work for your setup:

1. Click the **Phase** tab you want to re-record (Setup, Buy Loop, etc.)
2. Click **⏺ Record** — you have 3 seconds to switch to the game window
3. Perform the inputs for that phase **exactly once**
4. Press the recording hotkey (configurable, shown in the Manual Key Recording panel) to stop recording
5. Click **▶ Test** to verify playback
6. Click **Save** to save the sequence as a JSON file

---

## Output Files (Batch Mode)

Each batch run creates a timestamped folder inside your output directory:

```
batch_output/
└── batch_run_2025-01-15_143022/
    ├── run_log.txt              Full bot log, appended in real time
    ├── live_log.txt             Per-relic summary, appended in real time
    ├── matches_log.txt          All matched relics in one file
    ├── README.txt               Full iteration breakdown (hits marked with *)
    ├── 001/
    │   ├── NR0000.sl2           Save file for this iteration
    │   └── info.txt             Relics found this iteration
    ├── HIT 004/                 Renamed when a relic meets your threshold
    │   ├── NR0000.sl2
    │   ├── info.txt
    │   └── relic_02_MATCH.jpg
    ├── GOD ROLL 007/            Renamed when all passives match
    │   ├── NR0000.sl2
    │   ├── info.txt
    │   └── relic_05_MATCH.jpg
    └── Excluded Hits/           Relics that matched criteria but were curse-filtered
        ├── Excluded Hits Info.txt
        └── relic_12_MATCH.jpg
```

To use a result: copy the `NR0000.sl2` from that folder to your game save location.
