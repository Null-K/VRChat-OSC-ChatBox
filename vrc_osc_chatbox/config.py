from __future__ import annotations

import json
from typing import Any, Dict

from vrc_osc_chatbox.constants import CONFIG_VERSION, DEFAULT_TEMPLATE
from vrc_osc_chatbox.paths import config_path as _config_path


def default_config_dict() -> Dict[str, Any]:
    return {
        "version": CONFIG_VERSION,
        "template": DEFAULT_TEMPLATE,
        "host": "127.0.0.1",
        "port": 9000,
        "sound": False,
        "interval": 3.0,
    }


def load_config_dict() -> Dict[str, Any]:
    base = default_config_dict()
    p = _config_path()
    if not p.is_file():
        return base
    try:
        with open(p, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError, TypeError):
        return base
    if not isinstance(raw, dict):
        return base
    out = {**base, **raw}
    if not isinstance(out.get("template"), str):
        out["template"] = base["template"]
    try:
        out["port"] = int(out["port"])
        if not 1 <= out["port"] <= 65535:
            out["port"] = base["port"]
    except (TypeError, ValueError):
        out["port"] = base["port"]
    out["sound"] = bool(out.get("sound", base["sound"]))
    try:
        out["interval"] = float(out["interval"])
        if out["interval"] < 0.2:
            out["interval"] = base["interval"]
    except (TypeError, ValueError):
        out["interval"] = base["interval"]
    host = out.get("host", base["host"])
    out["host"] = host if isinstance(host, str) else base["host"]
    return out


def save_config_dict(data: Dict[str, Any]) -> None:
    path = _config_path()
    to_write = {**data, "version": CONFIG_VERSION}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_write, f, ensure_ascii=False, indent=2)
