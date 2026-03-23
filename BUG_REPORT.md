# Reporting a Bug

If something is not working as expected, open an issue on the
[Issues page](https://github.com/PulgoMaster/Pulgo-Elden-Ring-Nightreign-Relic-Farming-Bot/issues).

To help reproduce and fix the problem quickly, **include the following in your report:**

---

## What to Include

### 1. Bot version
Check the window title or the release you downloaded. Example: `v1.3.0`

### 2. What happened
Describe what the bot did wrong. Be specific:
- Which phase did it fail on? (Phase 0 Setup / Phase 1 Buy / Phase 2 Nav / Phase 3 Tab / Phase 4 Review)
- Did the bot log any error messages? Copy the relevant lines from the log panel.
- Did the bot stop, loop, or do something unexpected?

### 3. What you expected to happen
Describe what the bot should have done instead.

### 4. How to reproduce it
List the steps that cause the issue to happen. If it happens consistently, say so. If it only happens sometimes (e.g. after several iterations), note that too.

### 5. Your setup
- **Relic type:** Normal or Deep of Night
- **Bot mode:** Live or Batch
- **Async Analysis:** enabled or disabled
- **Number of workers** (if Brute Force Analysis is on)
- **Game load wait (s):** what value you have set
- **Close buffer (s):** what value you have set
- **PC specs (optional but helpful):** CPU, RAM, SSD or HDD — relevant if timing-related

### 6. Screenshot or log (if possible)
- A screenshot of the bot UI showing the error or the unexpected state
- The log output from the run — you can copy it directly from the log panel

---

## Tips Before Reporting

- **Timing issues:** If the bot starts on the wrong screen or inputs seem to fire too early, try increasing **Game load wait** by 5–10 seconds before reporting. Most timing problems are machine-specific and can be fixed this way.
- **Sequence issues:** If the bot navigates incorrectly, check that your Phase 0 and Phase 2 sequences match your in-game shop layout. If shops are in different positions (DLC not owned, different unlock state), re-recording those phases may fix the issue without needing a bug report.
- **OCR failures:** If relics are not being read correctly, make sure the game is running in **Borderless Windowed or Fullscreen** — windowed mode shifts the capture area.

---

*Thank you for taking the time to report issues. Detailed reports make fixes much faster.*
