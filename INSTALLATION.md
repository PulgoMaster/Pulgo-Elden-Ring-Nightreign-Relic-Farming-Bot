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
| **Game load wait** | How long the bot waits after launch before sending inputs | See tuning section below |
| **Close buffer (s)** | How long to wait after game closes before relaunching | See tuning section below |
| **Manage game automatically** | Tells the bot to close, restore, and relaunch the game each run | Must be enabled |
| **Relic type** | Normal (600 murk) or Deep of Night (1800 murk) | Set before loading sequences |

---

## Tuning the Bot for Your Machine

**This is the most important step for reliability.** The default timing values are conservative, but
every machine loads the game at a different speed. If you do not calibrate these settings, the bot
will start sending inputs before the game is ready and Phase 0 will fail.

### Game Load Wait

This controls how many seconds the bot waits after launching the game before it begins Phase 0.

**How to calibrate:**
1. Launch the game manually and start a timer the moment the process opens
2. Stop the timer when you have full control at Roundtable Hold
3. Add 5–10 seconds of buffer on top — the bot needs some margin
4. Enter that value in the **Game load wait** field

Machines with fast NVMe SSDs typically load in 20–30 seconds. Slower HDDs may need 60–70 seconds or
more. **If the bot consistently ends up on the wrong screen or misfires inputs, increase this value
first before investigating anything else.**

### Close Buffer

After force-closing the game, the bot waits this many seconds before relaunching. If your machine
leaves lingering background processes after the game closes, set this to 6–8 seconds. The default is 4.

### Input Timing in Sequences

The pre-recorded sequences include small delays between inputs to account for menu transitions. If
the bot's inputs arrive faster than your menus can render:
- Re-record the sequence (see SETUP.md) and pause briefly between each input
- Menus typically need 0.2–0.5 seconds to respond — if a sequence skips a step, this is why

---

## What You Need Before Starting

Checklist before running the bot for the first time:

- [ ] Save file path entered and pointing to your current `NR0000.sl2`
- [ ] Personal backup of that save file made in a separate location
- [ ] Game executable path entered correctly
- [ ] **Manage game automatically** is enabled
- [ ] Game load wait calibrated to your machine
- [ ] Relic type selected (Normal or Deep of Night) to match what you are farming
- [ ] At least one relic criterion set (the bot needs to know what it is looking for)
- [ ] Game is running in **Borderless Windowed or Fullscreen** — windowed mode shifts the capture
      area and will cause OCR to read the wrong screen region

---

## Tips for Best Results

- **Farm Murk before running the bot.** The bot buys as many relics as your current Murk balance
  allows each iteration. More Murk per session means more relics reviewed and fewer total iterations
  to find what you are looking for. Going in with a large Murk stockpile makes a significant difference.

- **Start from Roundtable Hold.** The included sequences navigate from a specific position at
  Roundtable Hold. Make sure you are standing there, facing the Relic Rites merchant area, before
  starting the bot.

- **Use Async Mode for faster farming.** In Batch Mode, enabling Async Analysis lets the bot keep
  farming while OCR runs in the background on the previous batch. This significantly reduces idle time
  between iterations on slower machines.

- **If sequences fail, re-record them.** The pre-recorded sequences are designed for a standard
  Nightreign setup with all shops unlocked. If your layout differs (DLC not owned, different unlock
  state), re-record Phase 0 and Phase 2 for your specific setup. Everything else is universal.

---

For the full technical setup reference, see [SETUP.md](SETUP.md).
