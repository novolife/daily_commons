#!/usr/bin/env python3
"""
Daily Commons Wallpaper - 仿 Bing 壁纸
后台运行、系统托盘、开机自启、跨日自动更换
"""

import json
import random
import re
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# 配置
CATEGORY = "Commons featured widescreen desktop backgrounds"
API_URL = "https://commons.wikimedia.org/w/api.php"
WALLPAPER_DIR = Path.home() / ".daily_commons_wallpaper"
CACHE_FILE = WALLPAPER_DIR / "cache.json"
CONFIG_FILE = WALLPAPER_DIR / "config.json"
ICON_FILE = WALLPAPER_DIR / "tray_icon.ico"
CHECK_INTERVAL = 60  # 跨日检测间隔（秒）
APP_NAME = "DailyCommonsWallpaper"


def ensure_dir():
    """确保壁纸目录存在"""
    WALLPAPER_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """加载配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"autostart": False}


def save_config(config: dict):
    """保存配置"""
    ensure_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_exe_path() -> str:
    """获取当前程序路径（支持 PyInstaller 打包后）"""
    if getattr(sys, "frozen", False):
        return sys.executable
    return str(Path(__file__).resolve())


def is_autostart_enabled() -> bool:
    """检查是否已设置开机自启"""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def set_autostart(enabled: bool) -> bool:
    """设置/取消开机自启"""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        path = get_exe_path()
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        try:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{path}"')
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            config = load_config()
            config["autostart"] = enabled
            save_config(config)
            return True
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def _strip_html(text: str) -> str:
    """去除 HTML 标签"""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def fetch_images_from_commons(limit: int = 200) -> list[dict]:
    """从 Wikimedia Commons API 获取分类中的图片列表（含元数据）"""
    params = {
        "action": "query",
        "generator": "categorymembers",
        "gcmtype": "file",
        "gcmtitle": f"Category:{CATEGORY}",
        "gcmlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiextmetadatafilter": "ObjectName|ImageDescription|Artist|LicenseShortName|Credit",
        "format": "json",
    }
    url = f"{API_URL}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "DailyCommonsWallpaper/1.0"})

    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except (URLError, HTTPError):
        return []

    images = []
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "imageinfo" in page and page["imageinfo"]:
            info = page["imageinfo"][0]
            extmeta = info.get("extmetadata", {})
            images.append({
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
    """获取单张图片的元数据（用于缓存中仅有 title 时补充）"""
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


def download_image(url: str, filepath: Path) -> bool:
    """下载图片到本地"""
    try:
        req = Request(url, headers={"User-Agent": "DailyCommonsWallpaper/1.0"})
        with urlopen(req, timeout=60) as resp:
            data = resp.read()
        filepath.write_bytes(data)
        return True
    except (URLError, HTTPError, OSError):
        return False


def set_windows_wallpaper(filepath: Path) -> bool:
    """设置 Windows 桌面壁纸"""
    try:
        import ctypes
        SPI_SETDESKWALLPAPER = 0x0014
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, str(filepath.resolve()), 3
        )
        return True
    except Exception:
        return False


def set_wallpaper(filepath: Path) -> bool:
    """根据系统设置壁纸"""
    if sys.platform == "win32":
        return set_windows_wallpaper(filepath)
    return False


def get_today_seed() -> int:
    """基于日期的种子，跨日时选择新图片"""
    return int(datetime.now().strftime("%Y%m%d"))


def select_image(images: list[dict], seed: int = None) -> dict:
    """根据种子选择图片（同一天相同种子得到相同图片）"""
    if not images:
        return None
    seed = seed or get_today_seed()
    rng = random.Random(seed)
    return rng.choice(images)


def get_file_extension(url: str) -> str:
    """从 URL 获取文件扩展名"""
    path = url.split("?")[0]
    if "." in path:
        return "." + path.rsplit(".", 1)[-1].lower()
    return ".jpg"


def _is_cache_from_today() -> tuple[bool, dict]:
    """检查缓存是否是当天的，返回 (是否有效, 缓存数据)"""
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


def update_wallpaper() -> bool:
    """获取并设置当日壁纸。跨日时自动选新图。开机自启时也会检查跨日并更新。"""
    ensure_dir()
    seed = get_today_seed()

    # 检查缓存是否是当天的（含跨日判断：缓存日期 != 今天 则需更新）
    is_today, cache = _is_cache_from_today()
    if is_today:
        set_wallpaper(Path(cache["path"]))
        return True

    images = fetch_images_from_commons(limit=200)
    if not images:
        if cache and Path(cache.get("path", "")).exists():
            set_wallpaper(Path(cache["path"]))
            return True
        return False

    selected = select_image(images, seed)
    if not selected:
        return False

    ext = get_file_extension(selected["url"])
    filename = f"wallpaper_{seed}{ext}"
    filepath = WALLPAPER_DIR / filename

    if not download_image(selected["url"], filepath):
        return False

    if set_wallpaper(filepath):
        metadata = selected.get("metadata", {})
        cache_data = {
            "path": str(filepath),
            "title": selected["title"],
            "url": selected["url"],
            "descriptionurl": selected.get("descriptionurl", ""),
            "date": datetime.now().isoformat(),
            "seed": seed,
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
        return True
    return False


def get_current_wallpaper_info() -> dict:
    """获取当前壁纸信息（从缓存，必要时补充元数据）"""
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
    return {
        "title": meta.get("title") or cache.get("title", ""),
        "description": meta.get("description", ""),
        "artist": meta.get("artist", ""),
        "license": meta.get("license", ""),
        "credit": meta.get("credit", ""),
        "url": cache.get("descriptionurl", ""),
    }


def create_tray_icon_file() -> Path:
    """创建托盘图标 ICO 文件（Windows 需要标准 ICO）"""
    ensure_dir()
    if ICON_FILE.exists():
        return ICON_FILE
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (48, 48), (70, 130, 180, 255))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([2, 2, 46, 46], radius=6, fill=(100, 149, 237))
        draw.polygon([(24, 12), (44, 44), (4, 44)], fill=(255, 255, 255))
        img.save(ICON_FILE, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    except Exception:
        try:
            img = Image.new("RGB", (32, 32), (70, 130, 180))
            img.save(ICON_FILE, format="ICO")
        except Exception:
            pass
    return ICON_FILE


def run_tray_app():
    """运行系统托盘应用（使用 infi.systray，Windows 原生支持更好）"""
    ensure_dir()
    icon_path = str(create_tray_icon_file())
    if not Path(icon_path).exists():
        icon_path = None  # infi.systray 会使用系统默认图标

    last_date = datetime.now().date()
    systray_ref = [None]

    def on_change_wallpaper(systray):
        nonlocal last_date
        if update_wallpaper():
            last_date = datetime.now().date()
            _notify("壁纸已更新", "Daily Commons Wallpaper")
            _update_hover_text(systray_ref)

    def on_autostart_toggle(systray):
        enabled = not is_autostart_enabled()
        if set_autostart(enabled):
            _notify("开机自启已" + ("开启" if enabled else "关闭"), APP_NAME)

    def on_show_wallpaper_info(systray):
        info = get_current_wallpaper_info()
        if not info:
            _notify("暂无壁纸信息", APP_NAME)
            return
        title = (info.get("title") or "未知")[:50]
        desc = (info.get("description") or "")[:80]
        artist = (info.get("artist") or "").strip() or "未知"
        license_ = info.get("license") or "未知"
        msg = f"标题: {title}\n描述: {desc}\n作者: {artist}\n许可: {license_}"
        _show_message_box("当前壁纸信息", msg)

    def on_open_commons(systray):
        info = get_current_wallpaper_info()
        url = info.get("url", "https://commons.wikimedia.org/")
        if url:
            webbrowser.open(url)

    def _update_hover_text(systray_ref):
        s = systray_ref[0]
        if not s:
            return
        info = get_current_wallpaper_info()
        title = (info.get("title") or "Daily Commons 壁纸")[:60]
        if hasattr(s, "update") and callable(getattr(s, "update")):
            s.update(hover_text=title)
        elif hasattr(s, "title"):
            s.title = title

    def background_check():
        nonlocal last_date
        while True:
            time.sleep(CHECK_INTERVAL)
            now = datetime.now().date()
            if now != last_date:
                last_date = now
                if update_wallpaper():
                    _notify("新的一天，壁纸已更新", "Daily Commons Wallpaper")
                    _update_hover_text(systray_ref)

    def on_quit(systray):
        pass

    hover_text = "Daily Commons 壁纸"
    info = get_current_wallpaper_info()
    if info.get("title"):
        hover_text = (info["title"])[:64]

    menu_options = (
        ("立即更换壁纸", None, on_change_wallpaper),
        ("开机自启", None, on_autostart_toggle),
        ("当前壁纸信息", None, on_show_wallpaper_info),
        ("在 Commons 查看", None, on_open_commons),
    )

    try:
        from infi.systray import SysTrayIcon
        systray = SysTrayIcon(
            icon_path or "",
            hover_text,
            menu_options,
            on_quit=on_quit,
            default_menu_index=0,
        )
        systray_ref[0] = systray
        # 启动时检查跨日并更新壁纸（含开机自启场景）
        update_wallpaper()
        _update_hover_text(systray_ref)
        t = threading.Thread(target=background_check, daemon=True)
        t.start()
        systray.start()
    except ImportError:
        # 回退到 pystray
        _run_tray_pystray(icon_path, hover_text, last_date, background_check, _update_hover_text)


def _notify(title: str, message: str):
    """系统通知（infi.systray 无内置 notify，仅更新悬浮提示）"""
    pass


def _show_message_box(title: str, message: str):
    """显示消息框"""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
        except Exception:
            pass


def _run_tray_pystray(icon_path: str, hover_text: str, last_date, background_check, _update_hover_text):
    """pystray 回退实现"""
    import pystray
    from PIL import Image

    icon = None
    systray_ref = [None]

    def on_change_wallpaper(_, __):
        nonlocal last_date
        if update_wallpaper():
            last_date = datetime.now().date()
            if icon:
                icon.notify("壁纸已更新", "Daily Commons Wallpaper")
            _update_hover_text(systray_ref)

    autostart_state = [is_autostart_enabled()]

    def on_autostart_toggle(_, item):
        enabled = not autostart_state[0]
        if set_autostart(enabled):
            autostart_state[0] = enabled
            if icon:
                icon.notify("开机自启已" + ("开启" if enabled else "关闭"), APP_NAME)

    def on_show_info(_, __):
        info = get_current_wallpaper_info()
        if info:
            title = (info.get("title") or "未知")[:50]
            artist = (info.get("artist") or "").strip() or "未知"
            license_ = info.get("license") or "未知"
            msg = f"标题: {title}\n作者: {artist}\n许可: {license_}"
            _show_message_box("当前壁纸信息", msg)

    def on_open_commons(_, __):
        info = get_current_wallpaper_info()
        url = info.get("url", "https://commons.wikimedia.org/")
        if url:
            webbrowser.open(url)

    def setup(icon_obj):
        nonlocal icon
        icon = icon_obj
        systray_ref[0] = icon
        update_wallpaper()
        _update_hover_text(systray_ref)
        t = threading.Thread(target=background_check, daemon=True)
        t.start()

    menu = pystray.Menu(
        pystray.MenuItem("立即更换壁纸", on_change_wallpaper, default=True),
        pystray.MenuItem("开机自启", on_autostart_toggle, checked=lambda _: autostart_state[0]),
        pystray.MenuItem("当前壁纸信息", on_show_info),
        pystray.MenuItem("在 Commons 查看", on_open_commons),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", lambda _, __: icon.stop()),
    )
    img = Image.open(icon_path) if icon_path and Path(icon_path).exists() else _create_pil_icon()
    tray_icon = pystray.Icon(APP_NAME, icon=img, title=hover_text, menu=menu)
    tray_icon.run(setup=setup)


def _create_pil_icon():
    """创建 PIL 图标（pystray 回退用）"""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (70, 130, 180, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([8, 8, 56, 56], radius=8, fill=(100, 149, 237))
    draw.polygon([(32, 20), (50, 50), (14, 50)], fill=(255, 255, 255))
    return img.resize((32, 32), Image.Resampling.LANCZOS)


def main():
    """入口"""
    import argparse
    parser = argparse.ArgumentParser(description="Daily Commons Wallpaper")
    parser.add_argument("--tray", action="store_true", help="后台托盘模式（默认）")
    parser.add_argument("--once", action="store_true", help="仅运行一次后退出")
    parser.add_argument("-r", "--random", action="store_true", help="随机选择（单次模式）")
    parser.add_argument("-n", "--count", type=int, default=200, help="获取图片数量")
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
