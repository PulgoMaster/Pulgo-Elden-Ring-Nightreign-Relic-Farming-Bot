# Elden Ring Nightreign – Relic Bot

Automates relic farming in **Elden Ring Nightreign** using on-device OCR to analyze relics and match them against your criteria.

Each iteration the bot:
1. Restores a clean save file and relaunches the game
2. Navigates to the Relic Rites merchant (Phase 0 — runs once per iteration)
3. Buys a relic and scans the post-buy preview screen (Phase 1 — repeated per cycle)
4. Navigates right through each relic in the Relic Rites panel and captures/analyzes each one (Phase 2)
5. Resets back to the buy screen with a single F press (Phase 3), then repeats from Phase 1
6. Saves every iteration — folders renamed to HIT or GOD ROLL when a relic matches your criteria

Works fully offline. No internet connection required after the first launch.

---

## ⚠️ Important Warnings

- **Back up your save file manually — separately from the bot's own backup.**
  The bot keeps its own working backup, but you should also keep a personal copy you control before you start.
  Your save is located at:
  `C:\Users\<YourName>\AppData\Roaming\Nightreign\<SteamID>\NR0000.sl2`

- **16:9 aspect ratio required.**
  The bot crops specific screen regions using fixed fractions tuned for 16:9 displays.
  Any resolution works (1080p, 1440p, 4K) as long as the aspect ratio is 16:9.
  Ultrawide (21:9), 4:3, and other non-standard aspect ratios are **not supported** —
  OCR crops will land on the wrong areas and the bot will not function correctly.

- **Always give the bot your most current save.**
  The bot restores that save before every iteration — it must be from before any run you have played.
  If you play a run after setting up the bot, make a fresh save at Roundtable Hold and update the path in the bot.
  Running from an outdated save risks being flagged by Nightreign's anti-cheat system.

See [SETUP.md](SETUP.md) for the full safety guide.

---

## Requirements

- **Windows 10 or 11**
- **Python 3.10 or later**
- **Elden Ring Nightreign** installed via Steam
- **~500 MB free disk space** for the one-time OCR model download
- No specific character required — works with any Nightreign character

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/PulgoMaster/Pulgo-Elden-Ring-Nightreign-Relic-Farming-Bot.git
cd Pulgo-Elden-Ring-Nightreign-Relic-Farming-Bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the bot
python main.py
```

On first launch the bot downloads its OCR model (~100 MB) — one-time only, then works fully offline.

For full setup instructions see **[SETUP.md](SETUP.md)**.
For first-time installation and file location help see **[INSTALLATION.md](INSTALLATION.md)**.
To report a bug see **[BUG_REPORT.md](BUG_REPORT.md)**.

---

## Input Sequences & Compatibility

The included input sequences work regardless of DLC ownership, character, or shop unlock state. The new phase architecture navigates directly to the Relic Rites merchant and does not depend on your Roundtable Hold layout.

If a sequence ever fails on your machine (e.g. due to unusual timing), use the built-in recording tool to re-record it for your setup. See [SETUP.md](SETUP.md) for step-by-step recording instructions.

---

## Tips for Best Results

- **Start with as much Murk as possible.** The bot calculates how many relics it can afford each iteration based on your current Murk balance. More Murk = more relics reviewed per run = fewer total iterations needed to find a match. Farming a large Murk stockpile before starting the bot will significantly speed up your search.
- **The bot automatically boosts the game's process priority** to HIGH after each load. This reduces input-drop frequency on busy systems and helps keep phase timing consistent over long runs.
- Run the game in **Borderless Windowed** mode. Fullscreen and standard windowed both shift the capture area and will cause OCR to read the wrong screen regions.

---

## Relic Criteria

| Tab | Description |
|-----|-------------|
| **Build Exact Relic** | Specify up to 20 target passive combinations. Each target has up to 3 slots and a match threshold (e.g. ≥ 2 of 3 must be present). The bot stops when ANY target is satisfied. Incompatible passives are blocked automatically — selecting a passive from an exclusive compat group hides conflicting passives in the remaining slots. |
| **Passive Pool** | Pick any number of passives; match when a relic has at least N of them simultaneously. Add **Pairings** to require two specific passives to appear together (counts as one match toward the threshold). |
| **Combine** | Tick the checkbox at the bottom to match against either tab simultaneously. |

The Relic Criteria section shows the **Scenic Flatstone** (Normal) or **Deep Scenic Flatstone** (Deep of Night) icon at the top, which updates automatically when you switch relic types. Passive lists are filtered to show only passives available in the currently selected mode.

---

## Hotkeys

| Key | Action |
|-----|--------|
| **F7** | Show / hide the overlay HUD (configurable in Batch Mode Settings) |
| **F8** | Toggle overlay between the normal log view and the full Matched Relics panel (configurable) |
| **F9** | Stop the bot after the current iteration completes (configurable) |

Both overlay hotkeys work even while the Nightreign window has focus. Inputs are automatically blocked if the Nightreign window loses focus — alt-tabbing is safe.

---

## Batch Mode Output

```
batch_output/
└── batch_run_2025-01-15_143022/
    ├── run_log.txt              Full log of everything the bot printed, appended in real time
    ├── live_log.txt             Per-relic analysis summary, appended in real time
    ├── matches_log.txt          All matched relics in one place
    ├── README.txt               Full breakdown of every iteration (hits marked with *)
    ├── 001/
    │   ├── NR0000.sl2
    │   └── info.txt
    ├── HIT 004/                 Relic met your match threshold
    │   ├── NR0000.sl2
    │   ├── info.txt
    │   └── relic_02_MATCH.jpg
    ├── GOD ROLL 007/            All passives matched
    │   ├── NR0000.sl2
    │   ├── info.txt
    │   └── relic_05_MATCH.jpg
    ├── Excluded Hits/           Relics that matched criteria but were blocked by the curse filter
    │   ├── Excluded Hits Info.txt
    │   └── relic_12_MATCH.jpg
    └── Smart Analyze Hits/      Relics flagged by Smart Analyze across all iterations
```

To use a result: copy the `NR0000.sl2` from that folder into your game save location.
