"""Core wallpaper logic - fetch, download, update."""

import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from config import (
    API_URL,
    CACHE_FILE,
    CATEGORY,
    CONFIG_FILE,
    MIN_HEIGHT,
    MIN_WIDTH,
    WALLPAPER_DIR,
    _DATE_HASH_PRIME,
)


def ensure_dir():
    WALLPAPER_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"autostart": False}


def save_config(config: dict):
    ensure_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _fetch_with_retry(req: Request, max_retries: int = 4, base_delay: float = 3.0):
    """Fetch with retry (for boot when network may not be ready)."""
    for attempt in range(max_retries):
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except (URLError, HTTPError, OSError):
            if attempt < max_retries - 1:
                time.sleep(base_delay * (attempt + 1))
    return None


def fetch_images_from_commons(limit: int = 200) -> list[dict]:
    params = {
        "action": "query",
        "generator": "categorymembers",
        "gcmtype": "file",
        "gcmtitle": f"Category:{CATEGORY}",
        "gcmlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiextmetadatafilter": "ObjectName|ImageDescription|Artist|LicenseShortName|Credit",
        "format": "json",
    }
    url = f"{API_URL}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "DailyCommonsWallpaper/1.0"})
    data = _fetch_with_retry(req)
    if not data:
        return []
    images = []
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "imageinfo" in page and page["imageinfo"]:
            info = page["imageinfo"][0]
            w, h = info.get("width", 0), info.get("height", 0)
            if w < MIN_WIDTH or h < MIN_HEIGHT:
                continue
            extmeta = info.get("extmetadata", {})
            images.append({
                "pageid": page.get("pageid"),
                "title": page.get("title", "").replace("File:", ""),
                "url": info["url"],
                "descriptionurl": info.get("descriptionurl", ""),
                "metadata": {
                    "title": _strip_html(extmeta.get("ObjectName", {}).get("value", "")),
                    "description": _strip_html(extmeta.get("ImageDescription", {}).get("value", "")),
                    "artist": _strip_html(extmeta.get("Artist", {}).get("value", "")),
                    "license": _strip_html(extmeta.get("LicenseShortName", {}).get("value", "")),
                    "credit": _strip_html(extmeta.get("Credit", {}).get("value", "")),
                }
            })
    return images


def fetch_image_metadata(file_title: str) -> dict:
    params = {
        "action": "query",
        "titles": f"File:{file_title}",
        "prop": "imageinfo",
        "iiprop": "extmetadata|url",
        "iiextmetadatafilter": "ObjectName|ImageDescription|Artist|LicenseShortName|Credit",
        "format": "json",
    }
    url = f"{API_URL}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "DailyCommonsWallpaper/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if "imageinfo" in page and page["imageinfo"]:
                info = page["imageinfo"][0]
                extmeta = info.get("extmetadata", {})
                return {
                    "descriptionurl": info.get("descriptionurl", ""),
                    "title": _strip_html(extmeta.get("ObjectName", {}).get("value", "")),
                    "description": _strip_html(extmeta.get("ImageDescription", {}).get("value", "")),
                    "artist": _strip_html(extmeta.get("Artist", {}).get("value", "")),
                    "license": _strip_html(extmeta.get("LicenseShortName", {}).get("value", "")),
                    "credit": _strip_html(extmeta.get("Credit", {}).get("value", "")),
                }
    except Exception:
        pass
    return {}


def download_image(url: str, filepath: Path, progress_callback=None, max_retries: int = 3) -> bool:
    base_delay = 2.0
    for attempt in range(max_retries):
        try:
            req = Request(url, headers={"User-Agent": "DailyCommonsWallpaper/1.0"})
            with urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0) or 0)
                data = []
                read = 0
                chunk = 65536
                while True:
                    b = resp.read(chunk)
                    if not b:
                        break
                    data.append(b)
                    read += len(b)
                    if progress_callback and total > 0:
                        pct = min(100, int(read * 100 / total))
                        progress_callback("downloading", pct)
            filepath.write_bytes(b"".join(data))
            return True
        except (URLError, HTTPError, OSError):
            if attempt < max_retries - 1:
                time.sleep(base_delay * (attempt + 1))
    return False


def set_windows_wallpaper(filepath: Path) -> bool:
    try:
        import ctypes
        ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, str(filepath.resolve()), 3)
        return True
    except Exception:
        return False


def set_wallpaper(filepath: Path) -> bool:
    if sys.platform == "win32":
        return set_windows_wallpaper(filepath)
    return False


def get_date_id() -> int:
    return int(datetime.now().strftime("%Y%m%d"))


def select_image(images: list[dict], seed: int = None) -> dict:
    if not images:
        return None
    seed = seed if seed is not None else get_date_id()
    sorted_images = sorted(images, key=lambda x: x.get("pageid", 0) or 0)
    index = ((seed * _DATE_HASH_PRIME) & 0xFFFFFFFF) % len(sorted_images)
    return sorted_images[index]


def get_file_extension(url: str) -> str:
    path = url.split("?")[0]
    if "." in path:
        return "." + path.rsplit(".", 1)[-1].lower()
    return ".jpg"


def _is_cache_from_today() -> tuple[bool, dict]:
    if not CACHE_FILE.exists():
        return False, {}
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            cache = json.load(f)
        cache_date = cache.get("date", "")[:10]
        today = datetime.now().strftime("%Y-%m-%d")
        if cache_date == today and Path(cache.get("path", "")).exists():
            return True, cache
        return False, cache
    except (json.JSONDecodeError, OSError):
        return False, {}


def update_wallpaper(force_refresh: bool = False, progress_callback=None) -> bool:
    def _report(step: str, percent: int = None):
        if progress_callback:
            progress_callback(step, percent)

    ensure_dir()
    date_id = get_date_id()
    if not force_refresh:
        is_today, cache = _is_cache_from_today()
        if is_today:
            set_wallpaper(Path(cache["path"]))
            return True
    else:
        _, cache = _is_cache_from_today()

    _report("fetching", 0)
    images = fetch_images_from_commons(limit=500)
    if not images:
        if cache and Path(cache.get("path", "")).exists():
            set_wallpaper(Path(cache["path"]))
            return True
        return False

    _report("selecting", 15)
    select_id = date_id if not force_refresh else (date_id * 1000 + int(time.time()) % 1000)
    selected = select_image(images, select_id)
    if not selected:
        _report("error", 0)
        return False

    ext = get_file_extension(selected["url"])
    filename = f"wallpaper_{select_id}{ext}"
    filepath = WALLPAPER_DIR / filename

    def dl_progress(_, pct):
        _report("downloading", 15 + int(pct * 70 / 100))
    if not download_image(selected["url"], filepath, progress_callback=dl_progress):
        _report("error", 0)
        return False

    _report("setting", 90)
    if set_wallpaper(filepath):
        metadata = selected.get("metadata", {})
        cache_data = {
            "path": str(filepath),
            "title": selected["title"],
            "url": selected["url"],
            "descriptionurl": selected.get("descriptionurl", ""),
            "date": datetime.now().isoformat(),
            "date_id": select_id,
            "metadata": {
                "title": metadata.get("title") or selected["title"],
                "description": metadata.get("description", ""),
                "artist": metadata.get("artist", ""),
                "license": metadata.get("license", ""),
                "credit": metadata.get("credit", ""),
            }
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        _report("done", 100)
        return True
    _report("error", 0)
    return False


def get_current_wallpaper_info() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    meta = cache.get("metadata", {})
    if not meta and cache.get("title"):
        meta = fetch_image_metadata(cache["title"])
    commons_url = cache.get("descriptionurl") or (meta.get("descriptionurl") if isinstance(meta, dict) else "")
    if not commons_url and cache.get("title"):
        fn = quote(cache["title"].replace(" ", "_"))
        commons_url = f"https://commons.wikimedia.org/wiki/File:{fn}"
    return {
        "title": (meta or {}).get("title") or cache.get("title", ""),
        "description": (meta or {}).get("description", ""),
        "artist": (meta or {}).get("artist", ""),
        "license": (meta or {}).get("license", ""),
        "credit": (meta or {}).get("credit", ""),
        "url": commons_url or "https://commons.wikimedia.org/",
    }


def open_folder(path: Path) -> bool:
    """Open folder in file manager."""
    try:
        path = path.resolve()
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(path))
        else:
            subprocess.run(["xdg-open", str(path)], check=False, capture_output=True)
        return True
    except Exception:
        return False


def open_url(url: str) -> bool:
    try:
        if sys.platform == "win32":
            os.startfile(url)
        else:
            subprocess.run(["xdg-open", url], check=False, capture_output=True)
        return True
    except Exception:
        try:
            import webbrowser
            webbrowser.open(url)
            return True
        except Exception:
            return False
