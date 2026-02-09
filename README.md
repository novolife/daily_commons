# Daily Commons Wallpaper

[![Build](https://github.com/novolife/daily_commons/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/novolife/daily_commons/actions)
[![Version](https://img.shields.io/badge/version-1.0.4-blue.svg)](https://github.com/novolife/daily_commons/releases)
[![Download](https://img.shields.io/badge/download-latest-green.svg)](https://github.com/novolife/daily_commons/releases/latest)

**Other languages:** [简体中文 (README_zh.md)](README_zh.md)

---

Bing-style daily wallpaper from [Wikimedia Commons featured widescreen desktop backgrounds](https://commons.wikimedia.org/wiki/Category:Commons_featured_widescreen_desktop_backgrounds).

## Features

- **Standalone EXE** - Single-file build, no Python required
- **System tray** - Runs in background, minimal footprint
- **Auto-start** - Toggle startup with Windows from tray menu
- **Daily auto-refresh** - Detects date change, fetches new image (date-based seed)
- **Resolution filter** - Only images ≥1920×1080
- **i18n** - Follows system language (English, 简体中文)
- 800+ curated widescreen wallpapers

## Quick Start

### Option 1: EXE (Recommended)

**[Download latest release](https://github.com/novolife/daily_commons/releases/latest)** · or build locally:

1. Run `build.bat` to generate `dist\DailyCommonsWallpaper.exe`
2. Double-click to start; app minimizes to system tray
3. Right-click tray icon:
   - **Change Wallpaper Now** - Manual refresh
   - **Start with Windows** - Toggle autostart
   - **Quit** - Exit

**Windows 11: tray icon not showing?** The app now uses pystray for better compatibility. If still hidden: ① Click `^` on the taskbar to view overflow icons; ② Settings → Personalization → Taskbar → Other system tray icons, enable this app.

```bash
pip install infi.systray pystray Pillow
python wallpaper.py          # Tray mode
python wallpaper.py --once   # Run once
python wallpaper.py --once -r  # Random image, then exit
```

## Daily Logic

- Checks date every 60 seconds
- On date change, fetches and sets new wallpaper
- Same day = same image (deterministic seed); new day = new image

## Build

```bash
pip install infi.systray pystray Pillow pyinstaller
# If typing conflict: pip uninstall typing
pyinstaller --clean build.spec
```

Output: `dist\DailyCommonsWallpaper.exe` (no console window)

## Project Structure

| File | Description |
|------|-------------|
| `wallpaper.py` | Main entry |
| `core.py` | Fetch, download, update logic |
| `tray.py` | System tray (infi.systray / pystray) |
| `config.py` | Constants |
| `i18n/` | Language files (en.json, zh_CN.json) |
| `build.spec` | PyInstaller config |
| `%USERPROFILE%\.daily_commons_wallpaper\` | Cache directory |

## CLI Options

| Option | Description |
|--------|-------------|
| `--tray` | Tray mode (default) |
| `--once` | Run once and exit |
| `-r, --random` | Random selection (with --once) |
| `-n, --count` | Image count, default 500 |

## Image Source

Images from [Wikimedia Commons](https://commons.wikimedia.org/), under their original licenses (mostly CC).

## License

MIT License - see [LICENSE](LICENSE).
