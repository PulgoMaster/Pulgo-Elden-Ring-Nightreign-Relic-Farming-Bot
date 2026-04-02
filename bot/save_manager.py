"""
Manages Elden Ring Nightreign save files.
Backs up the save before the bot starts, and restores it after each failed attempt
so the game resets to the relic-generation screen.
"""

import shutil
import os
import time


def make_backup_dir(backup_folder: str, run_stamp: str) -> str:
    """Create and return a timestamped ACTIVE backup directory for this run.

    The directory is named with a ACTIVE_ prefix so it can be identified
    and renamed to its final name (with actual iteration count) at run end.
    Returns the full path to the created directory.
    """
    dir_name = f"Nightreign_Backup_ACTIVE_{run_stamp}"
    backup_dir = os.path.join(backup_folder, dir_name)
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def finalize_backup_dir(backup_dir: str, actual_iters: int) -> str:
    """Rename the ACTIVE backup dir to its final name with iteration count and date.

    Returns the final directory path (renamed), or the original if rename fails.
    """
    if not os.path.isdir(backup_dir):
        return backup_dir
    date_str = time.strftime("%Y_%m_%d")
    base = os.path.dirname(backup_dir)
    final_name = f"Nightreign_Backup_{actual_iters}Iters_{date_str}"
    final_dir = os.path.join(base, final_name)
    # Avoid collision if another run on the same day already exists
    suffix = 0
    candidate = final_dir
    while os.path.exists(candidate):
        suffix += 1
        candidate = f"{final_dir}_{suffix}"
    try:
        os.rename(backup_dir, candidate)
        return candidate
    except Exception:
        return backup_dir


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
    # Atomic restore: copy to temp, then os.replace (atomic on NTFS).
    # Prevents corrupted save if process is killed mid-copy.
    tmp = save_path + ".tmp"
    shutil.copy2(backup_path, tmp)
    os.replace(tmp, save_path)


def delete_backup(backup_path: str) -> None:
    """Remove the backup file (e.g. after a successful find)."""
    if os.path.isfile(backup_path):
        os.remove(backup_path)
