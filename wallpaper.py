#!/usr/bin/env python3
"""
Daily Commons Wallpaper - 仿 Bing 壁纸
后台运行、系统托盘、开机自启、跨日自动更换
"""

import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from datetime import datetime

# 壁纸最小分辨率
MIN_WIDTH = 1920
MIN_HEIGHT = 1080
from pathlib import Path
from urllib.parse import quote, urlencode
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
    """从 Wikimedia Commons API 获取分类中的图片列表（含元数据），过滤分辨率 < 1920x1080"""
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


def download_image(url: str, filepath: Path, progress_callback=None) -> bool:
    """下载图片到本地，progress_callback(step, percent) 可选"""
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


def get_date_id() -> int:
    """基于日期的标识符，确保不同日期对应不同壁纸"""
    return int(datetime.now().strftime("%Y%m%d"))


# 大质数用于哈希分布，避免相邻日期选到相同或相邻图片
_DATE_HASH_PRIME = 2654435761


def select_image(images: list[dict], seed: int = None) -> dict:
    """根据种子确定性选择图片，不同种子得到不同图片"""
    if not images:
        return None
    seed = seed if seed is not None else get_date_id()
    # 按 pageid 排序确保 API 返回顺序一致
    sorted_images = sorted(images, key=lambda x: x.get("pageid", 0) or 0)
    # 种子 -> 确定性索引
    index = ((seed * _DATE_HASH_PRIME) & 0xFFFFFFFF) % len(sorted_images)
    return sorted_images[index]


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


def update_wallpaper(force_refresh: bool = False, progress_callback=None) -> bool:
    """获取并设置当日壁纸。progress_callback(step, percent) 可选，step: fetching|selecting|downloading|setting|done|error"""
    def _report(step: str, percent: int = None):
        if progress_callback:
            progress_callback(step, percent)

    ensure_dir()
    date_id = get_date_id()

    # 检查缓存是否是当天的（手动刷新时跳过，强制拉取新图）
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
    # 手动刷新时用时间戳作为额外因子，确保每次选到不同图片
    select_id = date_id if not force_refresh else (date_id * 1000 + int(time.time()) % 1000)
    selected = select_image(images, select_id)
    if not selected:
        _report("error", 0)
        return False

    ext = get_file_extension(selected["url"])
    filename = f"wallpaper_{select_id}{ext}"
    filepath = WALLPAPER_DIR / filename

    def dl_progress(_, pct):
        _report("downloading", 15 + int(pct * 70 / 100))  # 15-85%
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
    # descriptionurl 可能存在于 cache 或 meta 中
    commons_url = cache.get("descriptionurl") or (meta.get("descriptionurl") if isinstance(meta, dict) else "")
    if not commons_url and cache.get("title"):
        # 从 title 拼 Commons 链接
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
    dialog_queue = queue.Queue()

    def _set_hover(text: str):
        s = systray_ref[0]
        if s and hasattr(s, "update") and callable(getattr(s, "update")):
            try:
                s.update(hover_text=text[:64])
            except Exception:
                pass

    def _dialog_worker():
        """预启动的对话框工作线程，避免在回调中创建新线程"""
        while True:
            try:
                on_complete = dialog_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            _set_hover("下载中...")
            _run_progress_dialog(on_complete)

    def on_change_wallpaper(systray):
        def on_complete(ok):
            nonlocal last_date
            _set_hover("Daily Commons 壁纸")
            if ok:
                last_date = datetime.now().date()
                _update_hover_text(systray_ref)
        dialog_queue.put(on_complete)

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
        url = info.get("url", "")
        _open_url(url or "https://commons.wikimedia.org/wiki/Category:Commons_featured_widescreen_desktop_backgrounds")

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
        # 预启动对话框工作线程（避免在回调中创建线程导致 RuntimeError）
        dt = threading.Thread(target=_dialog_worker, daemon=True)
        dt.start()
        # 启动时检查跨日并更新壁纸（含开机自启场景）
        update_wallpaper()
        _update_hover_text(systray_ref)
        t = threading.Thread(target=background_check, daemon=True)
        t.start()
        systray.start()
    except ImportError:
        # 回退到 pystray
        _run_tray_pystray(icon_path, hover_text, last_date, background_check, _update_hover_text)


def _open_url(url: str) -> bool:
    """在默认浏览器中打开 URL（兼容后台/服务环境）"""
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


def _notify(title: str, message: str):
    """系统通知（尽量不使用气泡）"""
    pass


def _show_message_box(title: str, message: str):
    """显示消息框"""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
        except Exception:
            pass


def _run_progress_dialog(on_complete) -> None:
    """在当前线程运行带进度条的信息框，同步执行下载（不创建新线程）。"""
    status_text = {
        "fetching": "正在获取图片列表...",
        "selecting": "正在选择图片...",
        "downloading": "正在下载壁纸...",
        "setting": "正在设置壁纸...",
        "done": "壁纸已设置成功",
        "error": "更新失败，请检查网络连接",
    }

    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("更换壁纸")
    root.resizable(False, False)
    root.geometry("320x140")
    root.attributes("-topmost", True)

    label = tk.Label(root, text="正在获取图片列表...", font=("Microsoft YaHei", 10))
    label.pack(pady=(20, 8), padx=20, anchor="w")

    progress = ttk.Progressbar(root, length=280, mode="determinate")
    progress.pack(pady=8, padx=20, fill="x")
    progress["value"] = 0

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=(16, 12))
    ok_btn = tk.Button(btn_frame, text="确定", width=8, command=lambda: root.destroy(), state="disabled")
    ok_btn.pack()

    def progress_cb(step: str, pct: int):
        label.config(text=status_text.get(step, step))
        if pct is not None:
            progress["value"] = pct
        root.update()

    root.update()
    try:
        ok = update_wallpaper(force_refresh=True, progress_callback=progress_cb)
    except Exception:
        ok = False
        progress_cb("error", 0)

    progress["value"] = 100 if ok else 0
    label.config(text=status_text["done"] if ok else status_text["error"])
    ok_btn.config(state="normal")
    on_complete(ok)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


def _run_tray_pystray(icon_path: str, hover_text: str, last_date, background_check, _update_hover_text):
    """pystray 回退实现"""
    import pystray
    from PIL import Image

    icon = None
    systray_ref = [None]
    dialog_queue = queue.Queue()
    downloading_state = [False]

    def _dialog_worker():
        while True:
            try:
                on_complete = dialog_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            downloading_state[0] = True
            if icon:
                icon.title = "下载中..."

            def _on_complete(ok):
                downloading_state[0] = False
                if ok:
                    if icon:
                        icon.title = "Daily Commons 壁纸"
                        icon.notify("壁纸已更新", "Daily Commons Wallpaper")
                    _update_hover_text(systray_ref)
                else:
                    if icon:
                        icon.title = "Daily Commons 壁纸"

            _run_progress_dialog(_on_complete)

    def on_change_wallpaper(_, __):
        dialog_queue.put(None)

    def on_change_wallpaper(_, __):
        refresh_queue.put(None)

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
        url = info.get("url", "")
        _open_url(url or "https://commons.wikimedia.org/wiki/Category:Commons_featured_widescreen_desktop_backgrounds")

    def setup(icon_obj):
        nonlocal icon
        icon = icon_obj
        systray_ref[0] = icon
        threading.Thread(target=_dialog_worker, daemon=True).start()
        update_wallpaper()
        _update_hover_text(systray_ref)
        t = threading.Thread(target=background_check, daemon=True)
        t.start()

    menu = pystray.Menu(
        pystray.MenuItem(lambda _: "下载中..." if downloading_state[0] else "立即更换壁纸", on_change_wallpaper, default=True),
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
