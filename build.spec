# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(sys.argv[0]).resolve().parent
sys.path.insert(0, str(ROOT))

from version import __version__

block_cipher = None

a = Analysis(
    ['wallpaper.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / 'i18n'), 'i18n')],
    hiddenimports=[
        'pystray._win32', 'PIL', 'PIL._tkinter_finder',
        'infi.systray', 'infi.systray.win32_adapter',
        'config', 'core', 'tray', 'i18n', 'i18n.loader',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f"DailyCommonsWallpaper-{__version__}",
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
    metadata=None,
)
