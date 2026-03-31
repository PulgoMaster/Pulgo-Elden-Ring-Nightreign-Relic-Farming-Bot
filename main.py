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

# ── GPU install handler ────────────────────────────────────────────────────── #
# The "Install GPU Acceleration" button re-launches this EXE with --run-pip
# so it can invoke the bundled pip to install CUDA torch into _internal/.
# Must be checked before anything else (including bootstrap and GUI import).
if '--run-pip' in sys.argv:
    _idx = sys.argv.index('--run-pip')
    _pip_args = sys.argv[_idx + 1:]
    try:
        # Pre-populate distlib's _finder_cache for frozen PyInstaller env.
        # finder() checks _finder_cache first (keyed by package name string).
        # Without this, it falls through to pkgutil.find_loader which returns
        # None for PYZ-bundled modules, causing "Unable to locate finder".
        # ResourceFinder(module) uses module.__file__ to derive the base path,
        # which in onedir mode points to _MEIPASS/pip/_vendor/distlib/ where
        # the data files (t32.exe, t64.exe, etc.) are extracted on disk.
        if getattr(sys, 'frozen', False):
            try:
                import pip._vendor.distlib as _dl
                import pip._vendor.distlib.resources as _dlr
                _dlr._finder_cache['pip._vendor.distlib'] = _dlr.ResourceFinder(_dl)
            except Exception:
                pass
        from pip._internal.cli.main import main as _pip_main
        sys.exit(_pip_main(_pip_args))
    except Exception as _e:
        print(f'pip error: {_e}', file=sys.stderr)
        sys.exit(1)
# ────────────────────────────────────────────────────────────────────────────── #


def _apply_gpu_upgrade() -> None:
    """
    If the user ran Install GPU Acceleration, the CUDA torch is staged next to
    the EXE in gpu_torch_staging/.  Swap it into _internal/ here, BEFORE any
    imports that would load the CPU torch DLLs (which Windows locks on load).
    Flag file gpu_upgrade_ready signals that a staged upgrade is waiting.
    Results are written to gpu_upgrade.log next to the EXE for diagnosis.
    """
    import time as _time
    exe_dir  = pathlib.Path(sys.executable).parent
    flag     = exe_dir / "gpu_upgrade_ready"
    staging  = exe_dir / "gpu_torch_staging"
    internal = exe_dir / "_internal"
    log_path = exe_dir / "gpu_upgrade.log"
    log      = ["_apply_gpu_upgrade: started"]

    if not flag.exists():
        return

    try:
        new_torch = staging / "torch"
        old_torch = internal / "torch"
        log.append(f"new_torch exists: {new_torch.exists()}")
        log.append(f"old_torch exists: {old_torch.exists()}")

        if new_torch.exists():
            if old_torch.exists():
                # Retry rmtree — Windows Defender may briefly lock DLLs at startup
                for _attempt in range(3):
                    try:
                        shutil.rmtree(str(old_torch))
                        log.append(f"rmtree old_torch: success (attempt {_attempt + 1})")
                        break
                    except Exception as _re:
                        log.append(f"rmtree old_torch: attempt {_attempt + 1} failed: {_re}")
                        if _attempt < 2:
                            _time.sleep(1.5)
                        else:
                            raise
            shutil.move(str(new_torch), str(old_torch))
            log.append("shutil.move: success")
            cudart = old_torch / "lib" / "cudart64_12.dll"
            log.append(f"cudart64_12.dll present after move: {cudart.exists()}")
        else:
            log.append("WARNING: new_torch not found in staging — nothing to move")

        flag.unlink(missing_ok=True)
        log.append("flag removed")
        if staging.exists():
            shutil.rmtree(str(staging), ignore_errors=True)
            log.append("staging dir cleaned up")
        log.append("completed successfully")
    except Exception as _e:
        log.append(f"FAILED: {_e}")
        print(f"GPU upgrade apply failed: {_e}", file=sys.stderr)
    finally:
        try:
            log_path.write_text("\n".join(log) + "\n")
        except Exception:
            pass


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
    _apply_gpu_upgrade()   # swap staged CUDA torch BEFORE torch DLLs are loaded
    _bootstrap_frozen()
    # If CUDA torch is installed, add _internal/torch/lib/ to the Windows DLL search
    # path NOW — before ui.app imports torch.  PyInstaller's bootloader only adds
    # _internal/ (sys._MEIPASS) via AddDllDirectory; the nested torch/lib/ where
    # cudart64_12.dll and torch_cuda.dll live is NOT registered, so torch._C fails
    # to load torch_cuda.dll at import time even though the files are present.
    _torch_lib = pathlib.Path(sys.executable).parent / "_internal" / "torch" / "lib"
    if _torch_lib.exists():
        try:
            os.add_dll_directory(str(_torch_lib))
        except Exception as _dle:
            pass   # non-fatal; CUDA just won't work if this fails

    # PyTorch CUDA initialization calls inspect.getsource() on internal functions
    # during lazy init.  In a frozen PyInstaller EXE the .py source files are not
    # on disk (they live in the PYZ archive), so inspect raises
    # OSError: "could not get source code".  Patch getsource to return '' instead
    # of raising — torch falls through gracefully and CUDA still initialises.
    try:
        import inspect as _inspect
        _real_getsource = _inspect.getsource
        def _frozen_getsource(obj, **kwargs):
            try:
                return _real_getsource(obj, **kwargs)
            except OSError:
                return ""
        _inspect.getsource = _frozen_getsource
    except Exception:
        pass

from ui.app import RelicBotApp


def main():
    app = RelicBotApp()
    app.mainloop()


if __name__ == "__main__":
    main()
