"""Generate SHA256 hashes of every source file in the repo.

Writes `source-hashes.txt` in the repo root with lines of the form:
    <sha256>  <relative/path>

Intended for release verification: a reviewer can run this script on
their clone at the same tag and compare the resulting file against the
one committed to the repo.  If they match, the source is unmodified.

Coverage:
    - All *.py files tracked in the repo
    - relic_bot.spec, requirements.txt, BUILD.md, CHANGELOG.md,
      README.md, INSTALLATION.md, GUIDE.txt, Update.ps1, Update.bat
    - All .json sequences under sequences/

Excluded:
    - Build artifacts (dist/, build/, __pycache__/)
    - Generated files (source-hashes.txt itself)
    - Runtime state (profiles/, *.json config files, batch_output/)
    - Binary assets (*.png, *.ico, *.pth) — these should be verified
      against the GitHub release artifact hash directly.
"""

import hashlib
import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

_EXCLUDE_DIRS = {
    "dist", "build", "__pycache__", ".git", ".pytest_cache",
    "batch_output", "save_backups", "profiles", "easyocr_models",
    "_internal",
}
_EXCLUDE_FILES = {
    "source-hashes.txt",
    "relicbot_config.json", "relicbot_calibration.json",
    "relicbot_timing.json", ".last_profile",
    "gpu_upgrade_ready", "gpu_upgrade.log",
}
_INCLUDE_EXT = {
    ".py", ".spec", ".txt", ".md", ".json", ".ps1", ".bat",
}


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_source_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS]
        for fn in filenames:
            if fn in _EXCLUDE_FILES:
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext not in _INCLUDE_EXT:
                continue
            # Skip JSON config files at the repo root
            if ext == ".json" and os.path.dirname(os.path.relpath(
                    os.path.join(dirpath, fn), root)) == "":
                continue
            yield os.path.join(dirpath, fn)


def main() -> int:
    entries = []
    for path in _iter_source_files(REPO_ROOT):
        rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
        digest = _hash_file(path)
        entries.append((rel, digest))
    entries.sort(key=lambda x: x[0])

    out_path = os.path.join(REPO_ROOT, "source-hashes.txt")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# SHA256 hashes of RelicBot source files.\n")
        f.write("# Regenerate with: python gen_source_hashes.py\n")
        f.write(f"# Total files: {len(entries)}\n\n")
        for rel, digest in entries:
            f.write(f"{digest}  {rel}\n")

    print(f"Wrote {out_path} — {len(entries)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
