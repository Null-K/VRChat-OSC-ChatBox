from __future__ import annotations

import platform
import time
from dataclasses import dataclass

import psutil

from vrc_osc_chatbox.formatting import fmt_bytes
from vrc_osc_chatbox.system_info import (
    linux_cpu_model_from_proc,
    nvidia_query,
    windows_cpu_marketing_name,
)


@dataclass
class VarContext:
    _net_prev: tuple[float, float, float] | None = None
    _net_pair_cache: tuple[str, str] | None = None
    _net_pair_mono: float = 0.0
    _nvidia_cache: tuple[float, dict | None] | None = None
    _cpu_name_cache: tuple[float, str | None] | None = None

    def cpu_model_cached(self) -> str:
        now = time.time()
        ttl = 120.0
        if self._cpu_name_cache and now - self._cpu_name_cache[0] < ttl:
            s = self._cpu_name_cache[1]
            return s if s else "-"
        n: str | None = None
        if platform.system() == "Windows":
            n = windows_cpu_marketing_name()
        elif platform.system() == "Linux":
            n = linux_cpu_model_from_proc()
        self._cpu_name_cache = (now, n)
        return n if n else "-"

    def nvidia(self) -> dict | None:
        now = time.time()
        if self._nvidia_cache and now - self._nvidia_cache[0] < 1.2:
            return self._nvidia_cache[1]
        d = nvidia_query()
        self._nvidia_cache = (now, d)
        return d

    def net_rate(self) -> tuple[str, str]:
        mono = time.monotonic()
        if self._net_pair_cache is not None and (mono - self._net_pair_mono) < 0.08:
            return self._net_pair_cache

        c = psutil.net_io_counters()
        now = time.time()
        if self._net_prev is None:
            self._net_prev = (float(c.bytes_sent), float(c.bytes_recv), now)
            pair = ("0B/s", "0B/s")
        else:
            ps, pr, t0 = self._net_prev
            dt = max(now - t0, 0.001)
            up = (c.bytes_sent - ps) / dt
            down = (c.bytes_recv - pr) / dt
            self._net_prev = (float(c.bytes_sent), float(c.bytes_recv), now)
            pair = (fmt_bytes(up) + "/s", fmt_bytes(down) + "/s")
        self._net_pair_cache = pair
        self._net_pair_mono = mono
        return pair
