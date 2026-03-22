"""
Manages Elden Ring Nightreign save files.
Backs up the save before the bot starts, and restores it after each failed attempt
so the game resets to the relic-generation screen.
"""

import shutil
import os


def backup(save_path: str, backup_path: str) -> None:
    """
    Copy the current save file to the backup location.
    Call this once before starting the bot loop.
    """
    if not os.path.isfile(save_path):
        raise FileNotFoundError(f"Save file not found: {save_path}")
    os.makedirs(os.path.dirname(backup_path) or ".", exist_ok=True)
    shutil.copy2(save_path, backup_path)


def restore(save_path: str, backup_path: str) -> None:
    """
    Overwrite the current save file with the backup.
    Call this after each failed relic attempt to reset game state.
    """
    if not os.path.isfile(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    shutil.copy2(backup_path, save_path)


def delete_backup(backup_path: str) -> None:
    """Remove the backup file (e.g. after a successful find)."""
    if os.path.isfile(backup_path):
        os.remove(backup_path)
