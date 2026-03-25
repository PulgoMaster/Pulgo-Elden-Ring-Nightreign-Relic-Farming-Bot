"""
Entry point for the Elden Ring Nightreign Relic Bot.

  python main.py          (development)
  RelicBot.exe            (frozen build)

When running as a frozen EXE, this module bootstraps the working directory
the first time it runs: copies bundled sequences and creates required folders
next to the executable so the bot can read and write files correctly.
"""

import sys
import pathlib
import shutil
import os


def _bootstrap_frozen() -> None:
    """
    First-run setup when launched as a PyInstaller frozen EXE.

    Creates save_backups/, batch_output/, profiles/, and sequences/ folders
    next to the EXE.  Bundled sequence files are copied into sequences/ only
    if they don't already exist there (preserving any recordings the user made).
    """
    exe_dir = pathlib.Path(sys.executable).parent
    meipass  = pathlib.Path(sys._MEIPASS)

    # Working folders the bot writes to
    for folder in ("save_backups", "batch_output", "profiles"):
        (exe_dir / folder).mkdir(exist_ok=True)

    # Copy bundled default sequences — skip files already present so user
    # recordings are never overwritten.
    seq_src = meipass / "sequences"
    seq_dst = exe_dir / "sequences"
    if seq_src.exists():
        seq_dst.mkdir(exist_ok=True)
        for src_file in seq_src.glob("*.json"):
            dst_file = seq_dst / src_file.name
            if not dst_file.exists():
                shutil.copy2(src_file, dst_file)


if getattr(sys, "frozen", False):
    _bootstrap_frozen()

from ui.app import RelicBotApp


def main():
    app = RelicBotApp()
    app.mainloop()


if __name__ == "__main__":
    main()
