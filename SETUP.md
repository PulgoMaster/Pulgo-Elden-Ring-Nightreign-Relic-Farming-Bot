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

## Repository Folder Structure

```
elden-ring-relic-bot/
├── sequences/          Input sequence files for each phase (load these in the bot)
├── save_backups/       Point the bot's "Backup folder" here — saves are stored here
├── batch_output/       Point the bot's "Output folder" here — batch results go here
├── profiles/           Your saved bot profiles (local only, never committed)
├── bot/                Bot logic (screen capture, OCR analysis, input control)
├── ui/                 User interface
├── assets/             App icon and images
├── main.py             Entry point
├── SETUP.md            This file
└── requirements.txt    Python dependencies
```

---

## Requirements

- Python 3.10 or later
- Elden Ring Nightreign installed via Steam (App ID: `2622380`)
- Windows 10 or 11
- ~500 MB free disk space (for the EasyOCR model download on first run)
- **16:9 display** — the bot crops specific screen regions by fixed fractions tuned for 16:9.
  Any resolution is fine (1080p, 1440p, 4K, etc.) as long as the aspect ratio is 16:9.
  Ultrawide (21:9), 4:3, and other non-standard ratios are **not supported** and will cause
  OCR to read the wrong parts of the screen.

### Install dependencies

```bash
pip install -r requirements.txt
```

> **First run note:** On first launch the bot downloads its OCR model (~100 MB) automatically.
> This is a one-time download — after that the bot works fully offline with no ongoing costs.

---

## First-Time Setup

### 1. Launch the bot

```bash
python main.py
```

### 2. Configure Save File & Game

| Field | What to enter |
|-------|---------------|
| **Save file** | Path to your `NR0000.sl2` (e.g. `C:\Users\<YourName>\AppData\Roaming\Nightreign\<SteamID>\NR0000.sl2`) |
| **Backup folder** | Point to the `save_backups/` folder inside this repo, or any folder you choose |
| **Game executable** | Path to `nightreign.exe` inside your Steam install |
| **Steam App ID** | Pre-filled: `2622380` |
| **Game load wait** | Seconds to wait for the game to load after launch (default 45 — lower if your PC loads faster) |
| **Confirm key** | Pre-filled: `F` (the interact/confirm key in-game) |
| **Manage game automatically** | Enable this — the bot will close, restore your save, and relaunch the game each iteration |

### 3. Select Relic Type

Under **Sequence Phases**, select the relic type **before** loading sequences:
- **Deep of Night** — 1800 murk each (uses `phase0_navigate_to_relic_buy_screen.json`)
- **Normal** — 600 murk each (uses `phase0_normal.json`)

Switching relic type automatically swaps the Phase 0 sequence.

### 4. Load the Standard Input Sequences

The `sequences/` folder contains pre-recorded input sequences for each phase.
They are loaded automatically on startup, but you can reload them manually using the **Load** button inside each Phase tab:

| Phase tab | Auto-loaded file |
|-----------|-----------------|
| **Phase 0 — Setup** | `phase0_navigate_to_relic_buy_screen.json` (Deep of Night) or `phase0_normal.json` |
| **Phase 1 — Buy Loop** | `phase1_buy_one_batch_of_10_relics.json` |
| **Phase 2 — Relic Rites Nav** | `phase3_review_setup.json` |
| **Phase 3 — Navigate to Sell** | `phase2_navigate_to_sell.json` |
| **Phase 4 — Review Step** | `phase4_review_step.json` |

> These sequences assume you start from **Roundtable Hold** with the Relic Rites merchant visible.

### 5. Set Relic Criteria

Use the **Relic Criteria** tabs to define what you are looking for:

- **Build Exact Relic** — specify up to 10 target passive combinations; each target has up to 3 passive slots and a match threshold (e.g. ≥ 2 of 3 must be present). The bot stops when ANY target is satisfied. Incompatible passive combinations are detected and blocked automatically.
- **Passive Pool** — pick any number of passives; the bot matches when a relic has at least N of them simultaneously. Add **Pairings** to require two specific passives to appear together (counts as one match).
- **Combine** — tick the checkbox at the bottom to match against either tab simultaneously.

### 6. Set Relic Color Filter

Select which relic colours you are hunting for (Red / Blue / Green / Yellow).
Switch between **Normal** and **Deep of Night** gem images using the radio buttons to match the mode you're farming.

### 7. Set Curse Filter (optional)

Add any curses you want to block. Relics carrying a blocked curse will be rejected even if their passives match.

### 8. Configure Batch Mode

The bot runs in **Batch Mode** — it runs for a set number of loops or hours and saves every iteration for manual review.

Point the **Output folder** to `batch_output/` inside this repo (or any folder).
After the run, open `README.txt` in the output folder — hits are marked with `*`.

### 9. Save a Profile

Click **Save As…** in the Profile section to save all your settings (save paths, sequences, criteria, filters) to a local JSON file. Profiles are stored only on your machine and are never committed to GitHub.

---

## Hotkeys (work even while the game is focused)

| Key | Action |
|-----|--------|
| **F9** | Toggle input recording on/off |
| **F8** | Pause / resume the bot |

Both hotkeys are configurable in the bot UI. The bot will automatically stop
sending inputs if the Nightreign window loses focus, so alt-tabbing is safe.

---

## Recording Your Own Sequences

If the standard sequences don't work for your setup:

1. Click the **Phase** tab you want to re-record (Setup, Buy Loop, etc.)
2. Click **⏺ Record** — you have 3 seconds to switch to the game window
3. Perform the inputs for that phase **exactly once**
4. Press **F9** to stop recording
5. Click **▶ Test** to verify playback
6. Click **Save** to save the sequence as a JSON file

---

## Output Files (Batch Mode)

Each batch run creates a timestamped folder inside your output directory:

```
batch_output/
└── batch_run_2025-01-15_143022/
    ├── README.txt          Full breakdown of every iteration (hits marked with *)
    ├── PRIORITY.txt        Quick list of saves worth opening
    ├── 001/
    │   ├── NR0000.sl2      Save file for this iteration
    │   └── info.txt        Relics found this iteration
    ├── HIT 004/            Renamed when a relic meets your threshold
    │   ├── NR0000.sl2
    │   ├── info.txt
    │   └── relic_02_MATCH.jpg
    └── GOD ROLL 007/       Renamed when all passives match
```

To use a result: copy the `NR0000.sl2` from that folder to your game save location.
