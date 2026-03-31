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
- Which phase did it fail on? (Phase 0 Setup / Phase 1 Buy+Preview / Phase 2 Scan / Phase 3 Reset)
- Did the bot log any error messages? Copy the relevant lines from the log panel.
- Did the bot stop, loop, or do something unexpected?

### 3. What you expected to happen
Describe what the bot should have done instead.

### 4. How to reproduce it
List the steps that cause the issue to happen. If it happens consistently, say so. If it only happens sometimes (e.g. after several iterations), note that too.

### 5. Your setup
- **Relic type:** Normal or Deep of Night
- **Async Analysis:** enabled or disabled
- **Backlog Mode:** enabled or disabled
- **GPU Acceleration:** enabled or disabled
- **Smart Throttle:** enabled or disabled
- **Number of workers** (if Brute Force or Async Analysis is on)
- **Low Performance Mode:** enabled or disabled
- **PC specs (optional but helpful):** CPU, RAM, GPU, SSD or HDD — relevant if timing-related

### 6. Screenshot or log (if possible)
- A screenshot of the bot UI showing the error or the unexpected state
- The log output from the run — you can copy it directly from the log panel

---

## Tips Before Reporting

- **Timing issues:** If the bot consistently ends up on the wrong screen or misfires inputs, try enabling **Low Performance Mode** in Batch Mode Settings before reporting. This widens input gaps across all phases and resolves most timing-related failures.
- **Sequence issues:** If the bot navigates incorrectly, try re-recording the affected phase using the built-in recording tool. The sequences are not dependent on DLC ownership or shop unlock state, so timing is the most likely culprit — enable Low Performance Mode first before re-recording.
- **OCR failures:** If relics are not being read correctly, make sure the game is running in **Borderless Windowed** mode — fullscreen and standard windowed both shift the capture area.

---

*Thank you for taking the time to report issues. Detailed reports make fixes much faster.*
