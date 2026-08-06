# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('easyocr')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('torch')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('mss')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pip')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('skimage')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Include assets, relic icons, default sequences, and user-facing docs in the bundle
datas += [
    ('assets/icon.ico', 'assets'),
    ('ui/relic_icons', 'ui/relic_icons'),
    ('sequences', 'sequences'),
    ('GUIDE.txt', '.'),
]

# ── Pre-download EasyOCR models and bundle them ────────────────────────
# The models (CRAFT detector + English recognizer) are fetched from the
# upstream EasyOCR GitHub releases at build time, cached across builds,
# and included in the EXE at `easyocr_models/`.  At runtime the bot passes
# `model_storage_directory=<bundled path>` + `download_enabled=False` so
# EasyOCR never attempts to fetch on first launch — bot runs offline.
import os as _os
import sys as _sys
import tempfile as _tmp
import urllib.request as _ureq
import zipfile as _zip

# URLs match those declared in easyocr/config.py for the installed
# easyocr version (detection=CRAFT, recognition=english_g2).  If a future
# easyocr version changes these URLs, rebuild against the new config.
_MODEL_URLS = {
    'craft_mlt_25k.pth': 'https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/craft_mlt_25k.zip',
    'english_g2.pth':    'https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip',
}
_model_cache_dir = _os.path.join(_tmp.gettempdir(), "relicbot_spec_cache", "easyocr_models")
_os.makedirs(_model_cache_dir, exist_ok=True)

for _pth_name, _url in _MODEL_URLS.items():
    _pth_path = _os.path.join(_model_cache_dir, _pth_name)
    if _os.path.exists(_pth_path):
        print(f"[Spec] Using cached EasyOCR model: {_pth_name}")
        continue
    print(f"[Spec] Downloading EasyOCR model: {_pth_name} from {_url}")
    _zip_path = _pth_path + ".zip"
    try:
        _ureq.urlretrieve(_url, _zip_path)
        with _zip.ZipFile(_zip_path, 'r') as _zf:
            _zf.extractall(_model_cache_dir)
        _os.remove(_zip_path)
        if not _os.path.exists(_pth_path):
            raise RuntimeError(f"Expected {_pth_name} after extract, not found")
        print(f"[Spec] Downloaded and extracted: {_pth_name}")
    except Exception as _e:
        print(f"[Spec] FATAL: Failed to fetch {_pth_name}: {_e}")
        raise

# Add every .pth model as a bundled data file under `easyocr_models/`.
for _pth_name in _MODEL_URLS:
    _p = _os.path.join(_model_cache_dir, _pth_name)
    if _os.path.exists(_p):
        datas.append((_p, 'easyocr_models'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# ── Ensure CPU torch DLLs are bundled, regardless of build env ─────────
# If the build machine has CUDA torch installed, torch.dll / c10.dll are
# CUDA-enabled builds that statically link to c10_cuda.dll etc.  Stripping
# the CUDA DLLs without replacing the base DLLs leaves broken dependency
# chains (WinError 126 on EXE launch).  Fix: download the matching CPU
# torch wheel to a cache dir at build time and swap all torch/lib/*.dll
# paths to the CPU versions.  Cached across builds — one-time download
# per torch version.
try:
    import torch as _t
    _is_cuda_build = _t.version.cuda is not None
except Exception:
    _is_cuda_build = False

_cpu_lib_dir = None
if _is_cuda_build:
    import subprocess as _sp
    _torch_ver = _t.__version__.split('+')[0]
    _py_tag = f"cp{_sys.version_info.major}{_sys.version_info.minor}"
    _cache_dir = _os.path.join(_tmp.gettempdir(), "relicbot_spec_cache")
    _extract_dir = _os.path.join(_cache_dir, f"torch-cpu-{_torch_ver}-{_py_tag}")
    _cpu_lib_dir = _os.path.join(_extract_dir, "torch", "lib")

    def _cached_cpu_version():
        """Actual __version__ of the cached CPU wheel, or None."""
        _vp = _os.path.join(_extract_dir, "torch", "version.py")
        try:
            with open(_vp, "r", encoding="utf-8") as _vf:
                for _line in _vf:
                    if _line.startswith("__version__"):
                        return _line.split("=", 1)[1].strip().strip("'\"")
        except Exception:
            pass
        return None

    # LOAD-BEARING: pin the CPU wheel to the EXACT bundled torch version.
    # Asking pip for plain "torch" returns the NEWEST on the CPU index, which
    # is then cached under a directory named after the BUNDLED version — so the
    # name lies and the build silently pairs torch 2.11.0+cu126's Python half
    # with 2.13.0+cpu's DLLs. torch then fails to import outright:
    #     AttributeError: torch._C.TensorBase has no attribute 'align_as'
    # and EasyOCR's retry surfaces it as
    #     RuntimeError: method '...' already has a docstring
    # i.e. no OCR at all in the shipped EXE. This is the same defect v1.8.8
    # fixed in _install_gpu_acceleration; the sibling build path was missed.
    # The version is ALSO verified after the fact, because a cache poisoned by
    # an earlier unpinned build would otherwise be reused forever.
    _cached = _cached_cpu_version()
    if _cached and _cached.split('+')[0] != _torch_ver:
        print(f"[Spec] Cached CPU torch is {_cached}, expected {_torch_ver} — "
              f"discarding poisoned cache")
        import shutil as _sh
        _sh.rmtree(_extract_dir, ignore_errors=True)

    if not _os.path.exists(_cpu_lib_dir):
        print(f"[Spec] CUDA torch detected ({_t.__version__}) — "
              f"downloading CPU wheel pinned to =={_torch_ver}")
        _os.makedirs(_extract_dir, exist_ok=True)
        try:
            _sp.check_call([
                _sys.executable, "-m", "pip", "install", f"torch=={_torch_ver}",
                "--index-url", "https://download.pytorch.org/whl/cpu",
                "--no-deps", "--target", _extract_dir,
                "--force-reinstall", "--quiet",
            ])
            print(f"[Spec] CPU torch cached at {_extract_dir}")
        except Exception as _e:
            print(f"[Spec] WARNING: CPU torch download failed: {_e}")
            print(f"[Spec] EXE will be broken on CUDA-strip — install CPU torch manually")
            _cpu_lib_dir = None
    else:
        print(f"[Spec] Using cached CPU torch at {_extract_dir}")

    # Hard gate: never ship a build whose CPU DLLs disagree with the Python half.
    if _cpu_lib_dir:
        _got = _cached_cpu_version()
        if not _got or _got.split('+')[0] != _torch_ver:
            raise SystemExit(
                f"[Spec] FATAL: CPU torch version mismatch — bundled Python half "
                f"is {_torch_ver}, CPU wheel is {_got}. Refusing to build a broken "
                f"EXE (torch would fail to import and OCR would be dead)."
            )
        print(f"[Spec] CPU torch version verified: {_got} matches {_torch_ver}")

if _cpu_lib_dir and _os.path.exists(_cpu_lib_dir):
    _cpu_dlls = {
        _fn.lower(): _os.path.join(_cpu_lib_dir, _fn)
        for _fn in _os.listdir(_cpu_lib_dir)
        if _fn.lower().endswith('.dll')
    }
    # Swap torch/lib/*.dll paths to CPU versions; drop CUDA-only DLLs
    _new_binaries = []
    _swap_count = 0
    _drop_count = 0
    for name, path, typ in a.binaries:
        _norm = name.replace('\\', '/')
        if _norm.startswith('torch/lib/') and _norm.lower().endswith('.dll'):
            _bn = _os.path.basename(_norm).lower()
            if _bn in _cpu_dlls:
                _new_binaries.append((name, _cpu_dlls[_bn], typ))
                _swap_count += 1
            else:
                _drop_count += 1   # CUDA-only DLL, drop it
        else:
            _new_binaries.append((name, path, typ))
    a.binaries = _new_binaries
    print(f"[Spec] Swapped {_swap_count} torch DLLs for CPU, dropped {_drop_count} CUDA-only DLLs")

    # ── torchvision must be CPU-matched too ────────────────────────────────
    # Swapping only torch leaves a CUDA-built torchvision whose native ops
    # cannot register against CPU torch, so EasyOCR dies with:
    #     RuntimeError: operator torchvision::nms does not exist
    # torch imports fine at that point, which makes this look like an EasyOCR
    # bug rather than a build-composition one. Pin to the bundled version for
    # the same reason torch is pinned.
    try:
        import torchvision as _tv
        _tv_ver = _tv.__version__.split('+')[0]
    except Exception:
        _tv_ver = None

    if _tv_ver:
        _tv_dir = _os.path.join(_cache_dir, f"torchvision-cpu-{_tv_ver}-{_py_tag}")

        def _cached_tv_version():
            _vp = _os.path.join(_tv_dir, "torchvision", "version.py")
            try:
                with open(_vp, "r", encoding="utf-8") as _vf:
                    for _line in _vf:
                        if _line.startswith("__version__"):
                            return _line.split("=", 1)[1].strip().strip("'\"")
            except Exception:
                return None
            return None

        _tvc = _cached_tv_version()
        if _tvc and _tvc.split('+')[0] != _tv_ver:
            print(f"[Spec] Cached CPU torchvision is {_tvc}, expected {_tv_ver} — discarding")
            import shutil as _sh2
            _sh2.rmtree(_tv_dir, ignore_errors=True)

        if not _os.path.isdir(_os.path.join(_tv_dir, "torchvision")):
            print(f"[Spec] Downloading CPU torchvision pinned to =={_tv_ver}")
            _os.makedirs(_tv_dir, exist_ok=True)
            try:
                _sp.check_call([
                    _sys.executable, "-m", "pip", "install",
                    f"torchvision=={_tv_ver}",
                    "--index-url", "https://download.pytorch.org/whl/cpu",
                    "--no-deps", "--target", _tv_dir,
                    "--force-reinstall", "--quiet",
                ])
            except Exception as _e:
                print(f"[Spec] WARNING: CPU torchvision download failed: {_e}")

        _tv_src = _os.path.join(_tv_dir, "torchvision")
        if _os.path.isdir(_tv_src):
            _got_tv = _cached_tv_version()
            if not _got_tv or _got_tv.split('+')[0] != _tv_ver:
                raise SystemExit(
                    f"[Spec] FATAL: CPU torchvision mismatch — bundled is {_tv_ver}, "
                    f"wheel is {_got_tv}. Refusing to build (EasyOCR would fail with "
                    f"'operator torchvision::nms does not exist').")
            _tv_files = {
                _fn.lower(): _os.path.join(_tv_src, _fn)
                for _fn in _os.listdir(_tv_src)
                if _fn.lower().endswith(('.dll', '.pyd'))
            }
            _tv_swap = _tv_drop = 0
            _nb = []
            for name, path, typ in a.binaries:
                _norm = name.replace('\\', '/')
                if _norm.startswith('torchvision/') and _norm.lower().endswith(('.dll', '.pyd')):
                    _bn = _os.path.basename(_norm).lower()
                    if _bn in _tv_files:
                        _nb.append((name, _tv_files[_bn], typ))
                        _tv_swap += 1
                    else:
                        _tv_drop += 1   # CUDA-only (e.g. nvjpeg64_12.dll)
                else:
                    _nb.append((name, path, typ))
            a.binaries = _nb
            print(f"[Spec] CPU torchvision {_got_tv} verified — swapped {_tv_swap} "
                  f"file(s), dropped {_tv_drop} CUDA-only")

# Safety net: strip any remaining CUDA DLLs and .lib files that slipped
# through (e.g. outside torch/lib/, or if the CPU-swap step was skipped).
_CUDA_PREFIXES = (
    'cublas', 'cuda', 'cudart', 'cudnn', 'cufft', 'curand', 'cusolver',
    'cusparse', 'nccl', 'nvfatbin', 'nvjitlink', 'nvrtc', 'nvperf',
    'caffe2_nvrtc', 'torch_cuda', 'c10_cuda', 'cupti',
)
a.binaries = [
    (name, path, typ) for name, path, typ in a.binaries
    if not any(_os.path.basename(name).lower().startswith(pfx) for pfx in _CUDA_PREFIXES)
    and not name.lower().endswith('.lib')
]

# Strip torch dev/test folders and .lib files from datas
a.datas = [
    (name, path, typ) for name, path, typ in a.datas
    if not any(p in name.replace('\\', '/') for p in ('torch/test/', 'torch/distributed/', 'torch/_inductor/'))
    and not name.lower().endswith('.lib')
]

# Strip user-specific files that shouldn't be in the distribution
_EXCLUDE_DATA = (
    'profiles', 'relicbot_config.json', 'relicbot_calibration.json',
    'relicbot_timing.json', '.last_profile', 'batch_output',
    'save_backups', 'gpu_upgrade_ready', 'gpu_upgrade.log',
    'NR0000.sl2', 'Nightreign_Backup',
)
a.datas = [
    (name, path, typ) for name, path, typ in a.datas
    if not any(_os.path.basename(path) == ex or name.startswith(ex) for ex in _EXCLUDE_DATA)
]

pyz = PYZ(a.pure)

# ── Onedir mode ─────────────────────────────────────────────────────────
# `RelicBot.exe` ships next to an `_internal/` folder holding the
# interpreter, dependencies and bundled EasyOCR models.
#
# This layout is REQUIRED by GPU Acceleration and must not be changed to
# onefile.  `_apply_gpu_upgrade()` in main.py swaps the downloaded CUDA
# torch into `_internal/torch/` at startup, `_cuda_torch_installed()` reads
# that same path, and the in-UI updater backs it up and restores it across
# updates.  A onefile build extracts its payload to a fresh
# `%TEMP%/_MEI<random>/` on every launch and imports torch from there, so a
# torch swapped into `_internal/` is never loaded: the install appears to
# succeed, the UI reports "GPU torch installed", and CUDA init still fails
# with "Torch not compiled with CUDA enabled".
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RelicBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RelicBot',
)

# COLLECT already produced `dist/RelicBot/` containing RelicBot.exe and the
# `_internal/` payload folder.  Copy the user-facing sidecars in next to the
# EXE: GUIDE.txt is the bundled documentation (PyInstaller puts its own copy
# under _internal/, which users never look in), and build_flavor.txt is what
# the in-UI updater reads out of an update ZIP to enforce cross-flavor
# protection (mainline vs CE).
import shutil as _shutil
_dist_dir = _os.path.join('dist', 'RelicBot')
_os.makedirs(_dist_dir, exist_ok=True)
try:
    for _sidecar in ('GUIDE.txt', 'build_flavor.txt'):
        if _os.path.exists(_sidecar):
            _shutil.copy2(_sidecar, _os.path.join(_dist_dir, _sidecar))
            print(f"[Spec] Copied sidecar {_sidecar} to {_dist_dir}")
except Exception as _e:
    print(f"[Spec] Post-build file layout failed: {_e}")
