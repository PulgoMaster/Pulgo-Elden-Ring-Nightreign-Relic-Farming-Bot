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
    if not _os.path.exists(_cpu_lib_dir):
        print(f"[Spec] CUDA torch detected ({_t.__version__}) — downloading CPU wheel")
        _os.makedirs(_extract_dir, exist_ok=True)
        try:
            _sp.check_call([
                _sys.executable, "-m", "pip", "install", "torch",
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

# ── Onefile mode ────────────────────────────────────────────────────────
# Packs the interpreter, all dependencies, bundled EasyOCR models, and the
# application itself into a single self-contained `RelicBot.exe`.  On first
# run the EXE extracts its payload to a per-session temp directory
# (`%TEMP%/_MEI<random>/`) and executes from there.  No `_internal/` folder
# is shipped — the resulting distribution is a single executable.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RelicBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.ico'],
)

# Place the single EXE alongside the updater scripts + GUIDE in `dist/RelicBot/`.
# Users unzip a small directory containing 4 files total (EXE, GUIDE.txt,
# Update.ps1, Update.bat) instead of the hundreds-of-files onedir layout.
import shutil as _shutil
_dist_dir = _os.path.join('dist', 'RelicBot')
_os.makedirs(_dist_dir, exist_ok=True)
try:
    # PyInstaller in onefile mode writes the EXE to dist/<name>.exe — move it
    # into dist/RelicBot/ so the ZIP layout matches the onedir expectation.
    _exe_src = _os.path.join('dist', 'RelicBot.exe')
    _exe_dst = _os.path.join(_dist_dir, 'RelicBot.exe')
    if _os.path.exists(_exe_src):
        _shutil.move(_exe_src, _exe_dst)
        print(f"[Spec] Moved EXE to {_exe_dst}")
    # Sidecar files that ship alongside the EXE for end users.
    # CE build includes the Cheat Engine table from FrCynda + CE_SETUP.txt
    # workflow doc; mainline build doesn't ship these.
    for _sidecar in ('GUIDE.txt', 'Update.ps1', 'Update.bat',
                      'CE_SETUP.txt', 'Relic_Bot_Uncapped_by_FrCynda.CT'):
        if _os.path.exists(_sidecar):
            _shutil.copy2(_sidecar, _os.path.join(_dist_dir, _sidecar))
except Exception as _e:
    print(f"[Spec] Post-build file layout failed: {_e}")
