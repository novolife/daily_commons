# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置

block_cipher = None

a = Analysis(
    ['wallpaper.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pystray._win32', 'PIL', 'PIL._tkinter_finder', 'infi.systray', 'infi.systray.win32_adapter'],
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
    name='DailyCommonsWallpaper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    metadata=None,
)
