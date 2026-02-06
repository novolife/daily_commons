"""i18n loader - load strings by system language."""

import json
import locale
import os
import sys
from pathlib import Path

_STRINGS = {}
_LANG = "en"


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


def t(key: str, default: str = "") -> str:
    """Get translated string by key."""
    if not _STRINGS:
        load()
    return _STRINGS.get(key, default or key)
