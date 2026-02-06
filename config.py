"""Configuration and constants."""

import sys
from pathlib import Path

# Wallpaper
MIN_WIDTH = 1920
MIN_HEIGHT = 1080
CATEGORY = "Commons featured widescreen desktop backgrounds"
API_URL = "https://commons.wikimedia.org/w/api.php"
_DATE_HASH_PRIME = 2654435761

# Paths
WALLPAPER_DIR = Path.home() / ".daily_commons_wallpaper"
CACHE_FILE = WALLPAPER_DIR / "cache.json"
CONFIG_FILE = WALLPAPER_DIR / "config.json"
ICON_FILE = WALLPAPER_DIR / "tray_icon.ico"

# App
CHECK_INTERVAL = 60
APP_NAME = "DailyCommonsWallpaper"


def get_exe_path() -> str:
    """Get current executable path (PyInstaller compatible)."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return str(Path(__file__).resolve())
