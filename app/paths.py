"""Per-user paths used by the app. Works on Windows, macOS and Linux.

Settings are portable: the file next to the program is tried first, then the
per-user configuration folder (which is writable even when the app lives in a
read-only place such as /Applications or an AppImage mount).
"""
import os
import sys
from pathlib import Path

APP_NAME = "SuperHeroBoostConfig"


def program_dir() -> Path:
    """Folder of the executable (frozen) or of the Python sources."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def user_config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_NAME


def settings_paths() -> tuple[Path, Path]:
    """Portable first, per-user second."""
    return program_dir() / f"{APP_NAME}.json", user_config_dir() / "settings.json"


def cache_dir() -> Path:
    return user_config_dir() / "classic"
