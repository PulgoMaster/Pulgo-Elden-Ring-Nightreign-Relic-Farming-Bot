# Elden Ring Nightreign – Relic Bot

Automates relic farming in **Elden Ring Nightreign** using on-device OCR to analyze relics and match them against your criteria.

Each iteration the bot:
1. Restores a clean save file and relaunches the game
2. Navigates to the Relic Rites merchant and buys a batch of relics
3. Reviews each relic using local OCR and checks it against your criteria
4. Saves the result — every iteration is kept for manual review; runs marked as HIT or GOD ROLL are renamed so they stand out

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

The included input sequences assume:
- You own the **Nightreign DLC**
- **All shops in Roundtable Hold are unlocked**

**If you do not have the DLC or not all shops are unlocked**, the navigation in **Phase 0 (Setup)** and **Phase 2 (Relic Rites Nav)** will fail because your menu layout differs.
Use the built-in recording tool to re-record those two phases for your setup — all other phases work universally and do not need re-recording.

See [SETUP.md](SETUP.md) for step-by-step recording instructions.

---

## Tips for Best Results

- **Start with as much Murk as possible.** The bot calculates how many relics it can afford each iteration based on your current Murk balance. More Murk = more relics reviewed per run = fewer total iterations needed to find a match. Farming a large Murk stockpile before starting the bot will significantly speed up your search.
- **The bot automatically boosts the game's process priority** to HIGH after each load. This reduces input-drop frequency on busy systems and helps keep phase timing consistent over long runs.
- Run the game in **Borderless Windowed** mode. Fullscreen and standard windowed both shift the capture area and will cause OCR to read the wrong screen regions.

---

## Relic Criteria

| Tab | Description |
|-----|-------------|
| **Build Exact Relic** | Specify up to 10 target passive combinations. Each target has up to 3 slots and a match threshold (e.g. ≥ 2 of 3 must be present). The bot stops when ANY target is satisfied. Incompatible passives are blocked automatically. |
| **Passive Pool** | Pick any number of passives; match when a relic has at least N of them simultaneously. Add **Pairings** to require two specific passives to appear together (counts as one match toward the threshold). |
| **Combine** | Tick the checkbox at the bottom to match against either tab simultaneously. |

---

## Hotkeys

| Key | Action |
|-----|--------|
| **F7** | Show / hide the overlay HUD (configurable in Batch Mode Settings) |

Inputs are automatically blocked if the Nightreign window loses focus — alt-tabbing is safe.

---

## Batch Mode Output

```
batch_output/
└── batch_run_2025-01-15_143022/
    ├── run_log.txt         Full log of everything the bot printed, appended in real time
    ├── live_log.txt        Per-relic analysis summary, appended in real time
    ├── README.txt          Full breakdown of every iteration (hits marked with *)
    ├── PRIORITY.txt        Quick list of saves worth reviewing first
    ├── 001/
    │   ├── NR0000.sl2
    │   └── info.txt
    ├── HIT 004/            Relic met your match threshold
    │   ├── NR0000.sl2
    │   ├── info.txt
    │   └── relic_02_MATCH.jpg
    └── GOD ROLL 007/       All passives matched
        ├── NR0000.sl2
        ├── info.txt
        └── relic_05_MATCH.jpg
```

To use a result: copy the `NR0000.sl2` from that folder into your game save location.
