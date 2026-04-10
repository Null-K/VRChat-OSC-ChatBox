from __future__ import annotations

from typing import List


def fmt_bytes(n: float) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0 or u == "TB":
            return f"{n:.1f}{u}"
        n /= 1024.0
    return f"{n:.1f}B"


def fmt_duration(seconds: float) -> str:
    s = int(max(0, seconds))
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts: List[str] = []
    if d:
        parts.append(f"{d}天")
    if h or parts:
        parts.append(f"{h}时")
    parts.append(f"{m}分")
    parts.append(f"{s}秒")
    return "".join(parts)
