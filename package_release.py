"""Package the built dist/RelicBot into the two release ZIPs.

One build, two packages.  The only difference between them is the
one-line `update_channel.txt` sidecar that sits next to the EXE:

    RelicBot_vX.Y.Z.zip        channel 'github'  -> GitHub release
    RelicBot_Nexus_vX.Y.Z.zip  channel 'nexus'   -> NexusMods upload

The GitHub package's Update button fetches the newest release from GitHub
and installs it.  The NexusMods package's Update button only installs a ZIP
the user downloaded themselves and never contacts GitHub, which is what
NexusMods requires: their rules say the in-app updater must install a
user-provided file rather than pull one from another site.

Run after PyInstaller:

    py -3.14 -m PyInstaller relic_bot.spec --noconfirm
    py -3.14 package_release.py
"""

import hashlib
import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
DIST = ROOT / "dist" / "RelicBot"

# (channel value, ZIP name template)
PACKAGES = [
    ("github", "RelicBot_v{ver}.zip"),
    ("nexus",  "RelicBot_Nexus_v{ver}.zip"),
]

# Files that must exist in the build before it is worth packaging at all.
REQUIRED = [
    "RelicBot.exe",
    "GUIDE.txt",
    "build_flavor.txt",
    "_internal",
    "_internal/numpy/_core/_multiarray_umath.cp314-win_amd64.pyd",
]


def app_version() -> str:
    src = (ROOT / "ui" / "app.py").read_text(encoding="utf-8")
    m = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', src, re.M)
    if not m:
        sys.exit("could not read APP_VERSION from ui/app.py")
    return m.group(1)


def verify_build() -> None:
    if not DIST.is_dir():
        sys.exit(f"no build found at {DIST} — run PyInstaller first")
    missing = [r for r in REQUIRED if not (DIST / r).exists()]
    if missing:
        sys.exit("build is incomplete, refusing to package:\n  "
                 + "\n  ".join(missing))
    # Runtime folders are created on first launch; if a smoke test made them
    # they must not be shipped, or the release carries local state.
    strays = [d for d in ("profiles", "save_backups", "batch_output", "sequences")
              if (DIST / d).exists()]
    if strays:
        sys.exit("build contains runtime folders from a local run: "
                 + ", ".join(strays) + "\n  delete them before packaging")


def build_zip(channel: str, zip_path: pathlib.Path) -> None:
    """Zip dist/RelicBot as a top-level RelicBot/ folder, injecting the channel."""
    files = sorted(p for p in DIST.rglob("*") if p.is_file()
                   and p.name != "update_channel.txt")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, f"RelicBot/{p.relative_to(DIST).as_posix()}")
        # Written directly into the archive so dist/ is never left dirty and
        # the two packages can never pick up each other's channel.
        zf.writestr("RelicBot/update_channel.txt", channel + "\n")
    return len(files) + 1


def main() -> int:
    verify_build()
    ver = app_version()

    for old in list(ROOT.glob("RelicBot_v*.zip")) + list(ROOT.glob("RelicBot_Nexus_v*.zip")):
        print(f"removing old package: {old.name}")
        old.unlink()

    print(f"\npackaging v{ver} from {DIST}")
    for channel, template in PACKAGES:
        zip_path = ROOT / template.format(ver=ver)
        n = build_zip(channel, zip_path)
        size_mb = zip_path.stat().st_size / 1048576
        sha = hashlib.sha256(zip_path.read_bytes()).hexdigest().upper()
        print(f"\n  {zip_path.name}")
        print(f"    channel : {channel}")
        print(f"    entries : {n}")
        print(f"    size    : {size_mb:,.1f} MB")
        print(f"    SHA256  : {sha}")

    # Confirm each package really carries the channel it is supposed to.
    print("\nverifying:")
    ok = True
    for channel, template in PACKAGES:
        zp = ROOT / template.format(ver=ver)
        with zipfile.ZipFile(zp) as zf:
            got = zf.read("RelicBot/update_channel.txt").decode().strip()
            flavor = zf.read("RelicBot/build_flavor.txt").decode().strip()
        good = got == channel
        ok &= good
        print(f"  {'OK  ' if good else 'FAIL'} {zp.name}: "
              f"channel={got} flavor={flavor}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
