#!/usr/bin/env python3
"""
Daily Commons Wallpaper - Bing-style daily wallpaper from Wikimedia Commons.
"""

import random
import sys

from config import WALLPAPER_DIR
from core import (
    ensure_dir,
    fetch_images_from_commons,
    get_file_extension,
    download_image,
    set_wallpaper,
    update_wallpaper,
)
from tray import run_tray_app


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Daily Commons Wallpaper")
    parser.add_argument("--tray", action="store_true", help="Tray mode (default)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("-r", "--random", action="store_true", help="Random selection (with --once)")
    parser.add_argument("-n", "--count", type=int, default=200, help="Image count to fetch")
    args = parser.parse_args()

    if args.once:
        ensure_dir()
        if args.random:
            images = fetch_images_from_commons(limit=args.count)
            if images:
                selected = random.choice(images)
                ext = get_file_extension(selected["url"])
                filepath = WALLPAPER_DIR / f"wallpaper{ext}"
                if download_image(selected["url"], filepath):
                    set_wallpaper(filepath)
        else:
            update_wallpaper()
        return

    if args.tray or (len(sys.argv) == 1 and sys.platform == "win32"):
        run_tray_app()
    else:
        ensure_dir()
        update_wallpaper()


if __name__ == "__main__":
    main()
