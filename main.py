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

        if new_torch.exists() and old_torch.exists():
            # ── LOAD-BEARING: swap ONLY the compiled half ──────────────────
            # PyInstaller's collect_all('torch') puts torch's .py modules in
            # BOTH the PYZ (hiddenimports) and on disk (datas). Replacing the
            # whole on-disk package leaves two DIFFERENT torch builds
            # reachable, torch's docstring registration runs twice, and the
            # import dies with:
            #     RuntimeError: function 'conv1d' already has a docstring
            # That is not a degraded GPU — torch does not import at all, so
            # OCR is dead and the bot can never confirm it is in-game. It
            # bricked every GPU install on v1.8.8-v1.8.11 (found 2026-08-06 on
            # an RTX 3070 laptop). Version-pinning the wheel does NOT help;
            # the two copies collide even at identical versions.
            # Only lib/* and *.pyd may be replaced. The .py half must remain
            # exactly the bundled copy so it always matches the PYZ.
            _copied = []

            new_lib, old_lib = new_torch / "lib", old_torch / "lib"
            if new_lib.is_dir():
                if old_lib.exists():
                    for _attempt in range(3):
                        try:
                            shutil.rmtree(str(old_lib))
                            log.append(f"rmtree torch/lib: success (attempt {_attempt + 1})")
                            break
                        except Exception as _re:
                            log.append(f"rmtree torch/lib: attempt {_attempt + 1} failed: {_re}")
                            if _attempt < 2:
                                _time.sleep(1.5)
                            else:
                                raise
                shutil.copytree(str(new_lib), str(old_lib))
                _copied.append(f"lib/ ({len(list(old_lib.iterdir()))} files)")
            else:
                log.append("WARNING: staged torch has no lib/ — nothing to swap")

            for _pyd in new_torch.glob("*.pyd"):
                shutil.copy2(str(_pyd), str(old_torch / _pyd.name))
                _copied.append(_pyd.name)

            log.append("compiled-half swap: " + ", ".join(_copied))
            log.append(f"python half untouched: "
                       f"{len(list(old_torch.rglob('*.py')))} .py files retained")
            cudart = old_torch / "lib" / "cudart64_12.dll"
            log.append(f"cudart64_12.dll present after swap: {cudart.exists()}")
        elif not new_torch.exists():
            log.append("WARNING: new_torch not found in staging — nothing to swap")
        else:
            log.append("WARNING: _internal/torch missing — cannot swap compiled half")

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

# ── torch self-check ───────────────────────────────────────────────────────── #
# `RelicBot.exe --torch-check` imports torch and reports what actually happened,
# then exits. Exists because GPU acceleration shipped broken in v1.8.8-v1.8.11:
# the only checks anyone could run were "does cudart64_12.dll exist on disk" and
# "does the GPU panel say installed". Both passed while torch could not import at
# all. Anything that swaps torch MUST be validated with this, not with a file
# listing. Runs AFTER --run-pip so the pip path is unaffected, and BEFORE the
# GUI import so a broken torch cannot hide behind a window that still opens.
if '--torch-check' in sys.argv:
    import json as _json
    _r = {"ok": False}
    try:
        import torch as _t
        _r["ok"] = True
        _r["version"] = getattr(_t, "__version__", "?")
        _r["file"] = getattr(_t, "__file__", "?")
        try:
            _r["cuda_available"] = bool(_t.cuda.is_available())
            _r["cuda_build"] = getattr(_t.version, "cuda", None)
            if _r["cuda_available"]:
                _r["device"] = _t.cuda.get_device_name(0)
        except Exception as _ce:
            _r["cuda_available"] = False
            _r["cuda_error"] = f"{type(_ce).__name__}: {_ce}"
    except Exception as _te:
        import traceback as _tb
        _r["error"] = f"{type(_te).__name__}: {_te}"
        _r["traceback"] = _tb.format_exc().splitlines()[-14:]
    # EasyOCR is what the bot actually needs; torch importing is necessary but
    # not sufficient, so probe the real consumer too.
    try:
        import easyocr as _e          # noqa: F401
        _r["easyocr"] = True
    except Exception as _ee:
        _r["easyocr"] = False
        _r["easyocr_error"] = f"{type(_ee).__name__}: {_ee}"
    print("TORCH_CHECK " + _json.dumps(_r, indent=1))
    sys.exit(0 if _r["ok"] and _r.get("easyocr") else 2)
# ────────────────────────────────────────────────────────────────────────────── #

from ui.app import RelicBotApp


def _set_high_res_timer():
    """
    Raise Windows multimedia timer resolution to 1ms for the bot process.

    Default Windows timer resolution is 15.6ms, which makes time.sleep() jittery
    by up to ~15ms. Phase 2 RIGHT presses use a 50ms hold via time.sleep(0.05);
    under GPU contention this can stretch to 100-150ms, long enough for the game
    to register the cursor key on multiple frames and double-advance.

    timeBeginPeriod(1) makes time.sleep accurate to ~1ms across the entire
    process, eliminating the jitter source. Paired with timeEndPeriod(1) on exit.

    Returns True if the resolution was successfully raised, False otherwise.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        return ctypes.windll.winmm.timeBeginPeriod(1) == 0  # TIMERR_NOERROR == 0
    except Exception:
        return False


def _restore_timer():
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.winmm.timeEndPeriod(1)
    except Exception:
        pass


def main():
    _set_high_res_timer()
    try:
        app = RelicBotApp()
        app.mainloop()
    finally:
        _restore_timer()


if __name__ == "__main__":
    main()
