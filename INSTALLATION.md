# Installation & First-Time Configuration

This page walks you through everything you need to do before running the bot for the first time —
finding your files, understanding the critical safety rules, and tuning the bot for your machine.

---

## ⚠️ Read This First

### Back up your save before every session

The bot manages its own internal save backup, but you should always keep a **personal copy of your
save in a location the bot cannot touch** — your Desktop, a USB drive, a separate folder entirely.
If the bot's backup is ever corrupted or overwritten incorrectly, your personal copy is the only
thing that can recover your character.

**Make this a habit: every time you intend to run the bot, make a fresh manual backup first.**

### Never run the bot on an outdated save

The bot restores the save you give it before every iteration. That save must be taken **after your
most recent play session** — specifically, it should be a save captured at Roundtable Hold after
you have finished playing for the day.

If you hand the bot a save from before a run you played, the game detects the inconsistency and
may flag the save as tampered with. Always update the save path in the bot after each play session.

### Online play

The bot runs entirely on your local machine. It uses only keyboard and mouse inputs — it does not
inject into the game process, modify game memory, or communicate with any external server. Based on
how it operates, **it should not be detected or flagged by Nightreign's anti-cheat, even if you are
online.**

However, using the bot online is **at your own discretion.** If you want to be completely safe, launch
Steam in Offline Mode before starting the game. This has no effect on the bot's functionality.

---

## Finding Your Files

### Save File

Your Nightreign save file is stored in a hidden Windows folder. Here is the easiest way to find it:

1. Press **Windows + R** to open the Run dialog
2. Type `%AppData%` and press **Enter** — this opens your Roaming AppData folder directly
3. Navigate to: `Roaming\Nightreign\<YourSteamID>\`
4. Your save file is `NR0000.sl2`

The full path looks like this:
```
C:\Users\YourName\AppData\Roaming\Nightreign\76561198XXXXXXXXX\NR0000.sl2
```

Copy the full path to this file and paste it into the **Save file** field in the bot.

> **Tip:** You can paste a path directly into the Windows Explorer address bar to navigate there
> even if the folder is hidden.

---

### Game Executable

The game executable (`nightreign.exe`) lives inside your Steam installation. To find it:

1. Open **Steam**
2. Right-click **Elden Ring Nightreign** in your library
3. Hover over **Manage** and click **Browse local files**
4. Steam opens the game's install folder — click into the **Game** subfolder if present
5. The executable is `nightreign.exe` — click the address bar at the top and copy the full path

The path typically looks like:
```
C:\Program Files (x86)\Steam\steamapps\common\Elden Ring Nightreign\Game\nightreign.exe
```

Paste this into the **Game executable** field in the bot.

---

## Key Settings to Configure

These are the settings that actually affect whether the bot works. Get these right before running
anything else.

| Setting | What it does | How to set it |
|---------|--------------|---------------|
| **Save file** | The save the bot restores before every iteration | Full path to `NR0000.sl2` (see above) |
| **Backup folder** | Where the bot keeps its own copies of your save | Point to `save_backups/` inside the bot folder |
| **Game executable** | How the bot launches the game | Full path to `nightreign.exe` (see above) |
| **Relic type** | Normal (600 murk) or Deep of Night (1800 murk) | Set before loading sequences |

---

## Tuning the Bot for Your Machine

The bot uses an adaptive load-wait system — it watches for the in-game Equipment menu to appear after each launch, so it does not need a manually calibrated load timer. It will wait up to 150 seconds for the game to become ready before aborting.

### Input Timing in Sequences

The pre-recorded sequences include small delays between inputs to account for menu transitions. If
the bot's inputs arrive faster than your menus can render:
- Re-record the sequence (see SETUP.md) and pause briefly between each input
- Menus typically need 0.2–0.5 seconds to respond — if a sequence skips a step, this is why
- Enable **Low Performance Mode** in Batch Mode Settings if the bot consistently misfires inputs on your machine

---

## What You Need Before Starting

Checklist before running the bot for the first time:

- [ ] Save file path entered and pointing to your current `NR0000.sl2`
- [ ] Personal backup of that save file made in a separate location
- [ ] Game executable path entered correctly
- [ ] Relic type selected (defaults to Normal — change if farming Deep of Night)
- [ ] At least one relic criterion set in the Relic Criteria tab
- [ ] Game is running in **Borderless Windowed** — fullscreen and windowed modes shift the capture
      area and will cause OCR to read the wrong screen region
- [ ] Starting position: standing at Roundtable Hold with the Relic Rites merchant visible

---

## Tips for Best Results

- **Farm Murk before running the bot.** The bot buys as many relics as your current Murk balance
  allows each iteration. More Murk per session means more relics reviewed and fewer total iterations
  to find what you are looking for. Going in with a large Murk stockpile makes a significant difference.

- **The bot automatically boosts the game's process priority** to HIGH after each load. This reduces
  input-drop frequency on busy systems and improves consistency across long runs — no configuration needed.

- **Start from Roundtable Hold.** The included sequences navigate from a specific position at
  Roundtable Hold. Make sure you are standing there, facing the Relic Rites merchant area, before
  starting the bot.

- **Use Async Mode for faster farming.** Enabling Async Analysis lets the bot keep farming while OCR
  runs in the background on the previous cycle. This significantly reduces idle time between
  iterations, especially on slower CPU-only machines.

- **Enable GPU Acceleration if you have an NVIDIA card.** In Batch Mode Settings, click "Install GPU
  Acceleration" to download CUDA-enabled torch. Once installed, GPU mode reduces per-relic OCR from
  ~3 s to ~0.3 s. When GPU is on, keep parallel workers at 4 or fewer — EasyOCR serialises on GPU
  above that and gains nothing from extra workers.

- **If sequences fail, re-record them.** The pre-recorded sequences work regardless of DLC ownership or shop unlock state. If a sequence misfires on your machine due to timing differences, re-record it using the built-in recording tool.

---

For the full technical setup reference, see [SETUP.md](SETUP.md).
