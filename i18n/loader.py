"""i18n loader - load strings by system language."""

import json
import locale
import os
import sys
from pathlib import Path

_STRINGS = {}
_LANG = "en"
_EN_STRINGS = {}
_EN_LOADED = False


def _get_i18n_dir() -> Path:
    """Get i18n directory path (supports PyInstaller)."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "i18n"
        if not base.exists():
            base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent
    return base


# Windows LANGID -> our locale code
_WIN_LANGID_MAP = {
    0x0404: "zh_TW",   # zh-TW Traditional
    0x0804: "zh_CN",   # zh-CN Simplified
    0x0c04: "zh_TW",   # zh-HK Hong Kong
    0x1004: "zh_CN",   # zh-SG Singapore
    0x0411: "ja",      # ja-JP Japanese
    0x0409: "en",      # en-US
    0x040c: "fr",      # fr-FR French
    0x0407: "de",      # de-DE German
    0x0419: "ru",      # ru-RU Russian
    0x0c0a: "es",      # es-ES Spanish (Spain)
    0x0410: "it",      # it-IT Italian
    0x042a: "vi",      # vi-VN Vietnamese
    0x0412: "ko",      # ko-KR Korean
    0x043e: "ms",      # ms-MY Malay
    0x0408: "el",      # el-GR Greek
    0x0401: "ar",      # ar-SA Arabic
}


def _detect_language() -> str:
    """Detect system language code."""
    # 1. Windows: GetUserDefaultUILanguage (most reliable for UI language on Windows)
    if sys.platform == "win32":
        try:
            import ctypes
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if lcid in _WIN_LANGID_MAP:
                return _WIN_LANGID_MAP[lcid]
            prim = lcid & 0x3FF
            if prim == 0x04:  # Chinese
                return "zh_CN" if lcid == 0x0804 else "zh_TW"
            if prim == 0x0a:  # Spanish
                return "es"
            if prim == 0x11:  # Japanese
                return "ja"
        except Exception:
            pass
    # 2. LANG env (e.g. zh_CN, ja_JP)
    lang_env = os.environ.get("LANG", "").split(".")[0]
    if lang_env:
        code = lang_env.replace("-", "_")
        if code.startswith("zh"):
            return "zh_CN" if "CN" in code.upper() or "Hans" in code else "zh_TW"
        if code.startswith("ja"):
            return "ja"
        if len(code) >= 2:
            return code
    # 3. locale.getlocale() / getdefaultlocale()
    for getter in (locale.getlocale, locale.getdefaultlocale):
        try:
            lang, _ = getter()
            if lang:
                if lang.startswith("zh"):
                    return "zh_CN" if "CN" in lang.upper() or "Hans" in lang else "zh_TW"
                if lang.startswith("ja"):
                    return "ja"
                return lang.split("_")[0].lower()
        except Exception:
            pass
    return "en"


def load(lang: str = None) -> dict:
    """Load strings for language. Returns dict of key->value."""
    global _STRINGS, _LANG
    _LANG = lang or _detect_language()
    i18n_dir = _get_i18n_dir()
    for candidate in [_LANG, _LANG.split("_")[0], "en"]:
        path = i18n_dir / f"{candidate}.json"
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    _STRINGS = json.load(f)
                return _STRINGS
            except Exception:
                pass
    _STRINGS = {}
    return _STRINGS


def t(key: str) -> str:
    """Get translated string by key.

    优先顺序：
    1. 当前语言的字符串（_STRINGS）
    2. 英文字符串（en.json）
    3. key 本身
    """
    global _EN_STRINGS, _EN_LOADED
    if not _STRINGS:
        load()
    if key in _STRINGS:
        return _STRINGS[key]

    # 尝试加载英文作为通用回退
    if not _EN_LOADED:
        i18n_dir = _get_i18n_dir()
        path = i18n_dir / "en.json"
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    _EN_STRINGS = json.load(f)
            except Exception:
                _EN_STRINGS = {}
        _EN_LOADED = True
    if key in _EN_STRINGS:
        return _EN_STRINGS[key]

    return key
