from __future__ import annotations

import sys
from pathlib import Path

from vrc_osc_chatbox.constants import CONFIG_FILENAME, ICON_FILENAME


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resolve_icon_path() -> Path | None:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            p = Path(meipass) / ICON_FILENAME
            if p.is_file():
                return p
    p = app_dir() / ICON_FILENAME
    if p.is_file():
        return p
    return None


def config_path() -> Path:
    return app_dir() / CONFIG_FILENAME
