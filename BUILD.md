# Building RelicBot from source

These are the exact steps used to produce the released `RelicBot.exe`.
They are intended for reviewers and anyone who wants to verify the
source in this repository matches the binary published on GitHub
releases / Nexus Mods.

> **Reproducibility note.** PyInstaller does not currently produce
> bit-for-bit deterministic binaries — Python bytecode embeds
> compilation timestamps, and file packaging order can vary between
> runs. Two clean builds of the same source will have different SHA256
> hashes but identical behaviour, identical size within a few KB, and
> identical module contents.
>
> For source-level tamper verification, see
> [`source-hashes.txt`](source-hashes.txt) — a SHA256 hash of every
> source file in the repository at the time of release. Regenerate it
> with `python gen_source_hashes.py` from a fresh clone at the same tag
> and diff against the committed copy to confirm nothing has been
> modified.

---

## Build environment

| | Version |
|---|---|
| OS | Windows 10 or 11 (64-bit) |
| Python | **3.14.3** (from python.org; `python --version`) |
| pip | 25.x (ships with Python 3.14) |
| PyInstaller | **6.19.0** |
| PyTorch | **2.11.0+cpu** (CPU-only wheel) |

CUDA is **not required**. The spec file auto-detects a CUDA PyTorch
install on the build machine and silently swaps in the matching
CPU-only DLLs at build time, so the shipped EXE never contains CUDA
runtime files.

---

## Step-by-step

These commands assume a fresh clone, a fresh Python 3.14.3 install,
and an empty `%TEMP%\relicbot_spec_cache` directory.

```bat
:: 1. Clone and enter the repo
git clone https://github.com/PulgoMaster/Pulgo-Elden-Ring-Nightreign-Relic-Farming-Bot.git
cd Pulgo-Elden-Ring-Nightreign-Relic-Farming-Bot

:: 2. (Optional but recommended) create an isolated virtual environment
python -m venv .venv
.venv\Scripts\activate

:: 3. Install pinned dependencies — note the CPU-only PyTorch index
pip install -r requirements.txt ^
    --index-url https://pypi.org/simple ^
    --extra-index-url https://download.pytorch.org/whl/cpu

:: 4. (Optional) verify source integrity
python gen_source_hashes.py
fc source-hashes.txt source-hashes.txt   :: should be identical

:: 5. Build the EXE
python -m PyInstaller relic_bot.spec --noconfirm

:: 6. Output layout
::    dist\RelicBot\RelicBot.exe     — single ~300 MB self-contained EXE
::    dist\RelicBot\GUIDE.txt        — user guide (plain text)
::    dist\RelicBot\Update.ps1       — in-place updater (PowerShell)
::    dist\RelicBot\Update.bat       — updater launcher
```

Total build time on a typical laptop: 3–5 minutes (dominated by
PyTorch DLL collection and bundled-model compression).

---

## What the spec file does

[`relic_bot.spec`](relic_bot.spec) runs several non-trivial steps:

1. **Pre-downloads the EasyOCR models** (`craft_mlt_25k.pth`,
   `english_g2.pth`) from the upstream EasyOCR GitHub release, caches
   them in `%TEMP%\relicbot_spec_cache\easyocr_models\`, and bundles
   them inside the EXE under `easyocr_models/`. Cached across builds.
2. **Collects** `easyocr`, `torch`, `mss`, `pip`, and `skimage` via
   PyInstaller's `collect_all` hook.
3. **Detects CUDA torch** on the build machine and, if present,
   downloads the matching CPU wheel to a second cache directory and
   swaps all `torch/lib/*.dll` binary paths to the CPU versions. This
   lets developers keep CUDA PyTorch installed for other work without
   contaminating the build.
4. **Strips** CUDA-only DLLs, `.lib` files, and development folders
   (`torch/test/`, `torch/distributed/`, `torch/_inductor/`) from the
   final binary.
5. **Excludes** user-specific runtime files (profiles, config, timing
   data, save backups) from the bundled data.
6. **Builds a single-file EXE** via PyInstaller's onefile mode. The
   EXE contains the Python interpreter, all dependencies, the
   bundled OCR models, and the application code in one compressed
   archive. On first launch, the payload self-extracts to
   `%TEMP%\_MEI<random>\` and executes from there.
7. **Moves the built EXE** into `dist\RelicBot\` and places
   `GUIDE.txt`, `Update.ps1`, and `Update.bat` alongside it.

---

## Packaging for distribution

```powershell
Compress-Archive -Path 'dist\RelicBot' -DestinationPath 'RelicBot_vX.Y.Z.zip'
```

The resulting ZIP contains four files: `RelicBot.exe`, `GUIDE.txt`,
`Update.ps1`, and `Update.bat`. The EXE is self-contained — no
`_internal/` folder, no loose DLLs, no on-first-run downloads. The bot
works offline from launch.

---

## Bundled OCR models — provenance and license

The CRAFT text detection model and the English text recognition model
shipped inside the EXE come from the upstream [EasyOCR GitHub release
page](https://github.com/JaidedAI/EasyOCR/releases). Both are published
by JaidedAI under the Apache License 2.0, which permits redistribution.

| File | Size | Purpose | Source |
|---|---|---|---|
| `craft_mlt_25k.pth` | ~80 MB | Text detection | [pre-v1.1.6 release](https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/craft_mlt_25k.zip) |
| `english_g2.pth` | ~15 MB | English recognition | [v1.3 release](https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip) |

These can be manually downloaded from the URLs above if you wish to
populate a local `easyocr_models/` directory for source runs. The spec
script does this automatically on first build.
