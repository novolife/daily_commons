"""System tray application - infi.systray and pystray."""

import queue
import sys
import threading
import time
from pathlib import Path

from config import APP_NAME, CHECK_INTERVAL, ICON_FILE, WALLPAPER_DIR
from core import (
    ensure_dir,
    get_current_wallpaper_info,
    open_url,
    update_wallpaper,
)


def _load_i18n():
    from i18n.loader import t
    return t


def is_autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        from config import get_exe_path
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
    if sys.platform != "win32":
        return False
    try:
        import winreg
        from config import get_exe_path
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
            from core import load_config, save_config
            config = load_config()
            config["autostart"] = enabled
            save_config(config)
            return True
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def create_tray_icon_file() -> Path:
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


def _show_message_box(title: str, message: str):
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
        except Exception:
            pass


def _run_progress_dialog(on_complete):
    """Run progress dialog in current thread (no new threads)."""
    t = _load_i18n()
    status_keys = ["fetching", "selecting", "downloading", "setting", "done", "error"]
    status_text = {k: t(f"progress_{k}") for k in status_keys}

    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title(t("dialog_title"))
    root.resizable(False, False)
    root.geometry("320x140")
    root.attributes("-topmost", True)

    label = tk.Label(root, text=status_text["fetching"])
    label.pack(pady=(20, 8), padx=20, anchor="w")

    progress = ttk.Progressbar(root, length=280, mode="determinate")
    progress.pack(pady=8, padx=20, fill="x")
    progress["value"] = 0

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=(16, 12))
    ok_btn = tk.Button(btn_frame, text=t("btn_ok"), width=8, command=lambda: root.destroy(), state="disabled")
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


def run_tray_app():
    t = _load_i18n()
    ensure_dir()
    icon_path = str(create_tray_icon_file())
    if not Path(icon_path).exists():
        icon_path = None

    from datetime import datetime
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
        while True:
            try:
                on_complete = dialog_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            _set_hover(t("menu_downloading"))
            _run_progress_dialog(on_complete)

    def on_change_wallpaper(systray):
        def on_complete(ok):
            nonlocal last_date
            _set_hover(t("app_title"))
            if ok:
                last_date = datetime.now().date()
                _update_hover_text(systray_ref)
        dialog_queue.put(on_complete)

    def on_autostart_toggle(systray):
        enabled = not is_autostart_enabled()
        if set_autostart(enabled):
            pass  # _notify removed

    def on_show_wallpaper_info(systray):
        info = get_current_wallpaper_info()
        if not info:
            _show_message_box(t("info_wallpaper_info"), t("info_no_wallpaper"))
            return
        title = (info.get("title") or t("info_unknown"))[:50]
        desc = (info.get("description") or "")[:80]
        artist = (info.get("artist") or "").strip() or t("info_unknown")
        license_ = info.get("license") or t("info_unknown")
        msg = f"{t('info_title')}: {title}\n{t('info_description')}: {desc}\n{t('info_artist')}: {artist}\n{t('info_license')}: {license_}"
        _show_message_box(t("info_wallpaper_info"), msg)

    def on_open_commons(systray):
        info = get_current_wallpaper_info()
        url = info.get("url", "")
        open_url(url or "https://commons.wikimedia.org/wiki/Category:Commons_featured_widescreen_desktop_backgrounds")

    def _update_hover_text(systray_ref):
        s = systray_ref[0]
        if not s:
            return
        info = get_current_wallpaper_info()
        title = (info.get("title") or t("app_title"))[:60]
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
                    pass
                _update_hover_text(systray_ref)

    def on_quit(systray):
        pass

    hover_text = t("app_title")
    info = get_current_wallpaper_info()
    if info.get("title"):
        hover_text = (info["title"])[:64]

    menu_options = (
        (t("menu_change_wallpaper"), None, on_change_wallpaper),
        (t("menu_autostart"), None, on_autostart_toggle),
        (t("menu_wallpaper_info"), None, on_show_wallpaper_info),
        (t("menu_view_commons"), None, on_open_commons),
    )

    # Prefer pystray on Windows 11 - uses in-memory icon, better compatibility
    # infi.systray has known issues: icon path with Unicode, Shell_NotifyIcon on Win11
    use_pystray = sys.platform == "win32"

    if use_pystray:
        try:
            _run_tray_pystray(icon_path, hover_text, last_date, background_check, _update_hover_text)
            return
        except Exception:
            pass

    try:
        from infi.systray import SysTrayIcon
        from infi.systray.win32_adapter import (
            CreatePopupMenu, POINT, GetCursorPos, SetForegroundWindow,
            TrackPopupMenu, PostMessage, TPM_LEFTALIGN, WM_NULL,
        )
        import ctypes

        MF_BYCOMMAND = 0
        MF_CHECKED = 0x0008
        MF_UNCHECKED = 0x0000

        class SysTrayIconWithAutostartCheckbox(SysTrayIcon):
            """Subclass that shows checkbox state for autostart menu item."""
            def _show_menu(self):
                if self._menu is None:
                    self._menu = CreatePopupMenu()
                    self._create_menu(self._menu, self._menu_options)
                for aid, action in self._menu_actions_by_id.items():
                    if action is on_autostart_toggle:
                        flag = MF_CHECKED if is_autostart_enabled() else MF_UNCHECKED
                        ctypes.windll.user32.CheckMenuItem(
                            self._menu, aid, MF_BYCOMMAND | flag
                        )
                        break
                pos = POINT()
                GetCursorPos(ctypes.byref(pos))
                SetForegroundWindow(self._hwnd)
                TrackPopupMenu(
                    self._menu, TPM_LEFTALIGN, pos.x, pos.y, 0, self._hwnd, None
                )
                PostMessage(self._hwnd, WM_NULL, 0, 0)

        systray = SysTrayIconWithAutostartCheckbox(
            icon_path or "",
            hover_text,
            menu_options,
            on_quit=on_quit,
            default_menu_index=0,
        )
        systray_ref[0] = systray
        dt = threading.Thread(target=_dialog_worker, daemon=True)
        dt.start()
        update_wallpaper()
        _update_hover_text(systray_ref)
        t2 = threading.Thread(target=background_check, daemon=True)
        t2.start()
        systray.start()
    except ImportError:
        _run_tray_pystray(icon_path, hover_text, last_date, background_check, _update_hover_text)


def _run_tray_pystray(icon_path: str, hover_text: str, last_date, background_check, _update_hover_text):
    t = _load_i18n()
    import pystray
    from PIL import Image

    icon = None
    systray_ref = [None]
    dialog_queue = queue.Queue()
    downloading_state = [False]

    def _dialog_worker():
        while True:
            try:
                dialog_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            downloading_state[0] = True
            if icon:
                icon.title = t("menu_downloading")

            def _on_complete(ok):
                downloading_state[0] = False
                if ok:
                    if icon:
                        icon.title = t("app_title")
                        icon.notify(t("progress_done"), t("app_name"))
                    _update_hover_text(systray_ref)
                else:
                    if icon:
                        icon.title = t("app_title")

            _run_progress_dialog(_on_complete)

    def on_change_wallpaper(_, __):
        dialog_queue.put(None)

    autostart_state = [is_autostart_enabled()]

    def on_autostart_toggle(_, item):
        enabled = not autostart_state[0]
        if set_autostart(enabled):
            autostart_state[0] = enabled
            if icon:
                icon.notify(t("notify_autostart_on") if enabled else t("notify_autostart_off"), APP_NAME)
                icon.update_menu()

    def on_show_info(_, __):
        info = get_current_wallpaper_info()
        if info:
            title = (info.get("title") or t("info_unknown"))[:50]
            artist = (info.get("artist") or "").strip() or t("info_unknown")
            license_ = info.get("license") or t("info_unknown")
            msg = f"{t('info_title')}: {title}\n{t('info_artist')}: {artist}\n{t('info_license')}: {license_}"
            _show_message_box(t("info_wallpaper_info"), msg)

    def on_open_commons(_, __):
        info = get_current_wallpaper_info()
        url = info.get("url", "")
        open_url(url or "https://commons.wikimedia.org/wiki/Category:Commons_featured_widescreen_desktop_backgrounds")

    def setup(icon_obj):
        nonlocal icon
        icon = icon_obj
        systray_ref[0] = icon
        threading.Thread(target=_dialog_worker, daemon=True).start()
        update_wallpaper()
        _update_hover_text(systray_ref)
        threading.Thread(target=background_check, daemon=True).start()

    def menu_text(_):
        return t("menu_downloading") if downloading_state[0] else t("menu_change_wallpaper")

    menu = pystray.Menu(
        pystray.MenuItem(menu_text, on_change_wallpaper, default=True),
        pystray.MenuItem(t("menu_autostart"), on_autostart_toggle, checked=lambda _: autostart_state[0]),
        pystray.MenuItem(t("menu_wallpaper_info"), on_show_info),
        pystray.MenuItem(t("menu_view_commons"), on_open_commons),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(t("menu_quit"), lambda _, __: icon.stop()),
    )
    img = Image.open(icon_path) if icon_path and Path(icon_path).exists() else _create_pil_icon()
    tray_icon = pystray.Icon(APP_NAME, icon=img, title=hover_text, menu=menu)
    tray_icon.run(setup=setup)


def _create_pil_icon():
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (70, 130, 180, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([8, 8, 56, 56], radius=8, fill=(100, 149, 237))
    draw.polygon([(32, 20), (50, 50), (14, 50)], fill=(255, 255, 255))
    return img.resize((32, 32), Image.Resampling.LANCZOS)
