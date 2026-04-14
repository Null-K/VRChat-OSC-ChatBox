from __future__ import annotations

import platform
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List

import psutil

from vrc_osc_chatbox.formatting import fmt_bytes, fmt_duration


def subprocess_win_kwargs() -> dict:
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def nvidia_query() -> dict | None:
    try:
        r = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None
        parts = [p.strip() for p in r.stdout.strip().split(",")]
        if len(parts) < 4:
            return None
        return {
            "name": parts[0],
            "mem_used": parts[1],
            "mem_total": parts[2],
            "util": parts[3],
        }
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


_cpu_rapl_prev: tuple[float, int] | None = None


# 拓展示例开始
def cpu_package_power_w() -> str:
    global _cpu_rapl_prev
    if platform.system() != "Linux":
        return "-"
    ej_path = Path("/sys/class/powercap/intel-rapl:0/energy_uj")
    if not ej_path.is_file():
        return "-"
    now = time.time()
    try:
        ej = int(ej_path.read_text().strip())
    except (ValueError, OSError):
        return "-"
    prev = _cpu_rapl_prev
    _cpu_rapl_prev = (now, ej)
    if prev is None:
        return "-"
    t0, e0 = prev
    dt = now - t0
    if dt <= 0:
        return "-"
    de = ej - e0
    if de < 0:
        de += 0xFFFFFFFF
    watts = (de / 1_000_000.0) / dt
    if not (0 <= watts <= 512):
        return "-"
    return f"{watts:.1f}W"


def nvidia_power_draw_w() -> str:
    try:
        r = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=power.draw",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        if r.returncode != 0 or not (r.stdout or "").strip():
            return "-"
        line = (r.stdout or "").strip().splitlines()[0].strip()
        if not line or line.upper() in ("[N/A]", "N/A"):
            return "-"
        return f"{float(line):.1f}W"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError, ValueError):
        return "-"
# 拓展示例结束


def wmi_gpu_name() -> str | None:
    try:
        import wmi

        c = wmi.WMI()
        for a in c.Win32_VideoController():
            if a.Name:
                return str(a.Name)
    except Exception:
        pass
    return None


def disk_root() -> str:
    if platform.system() == "Windows":
        return "C:\\"
    return "/"


def wmic_cpu_name() -> str | None:
    try:
        r = subprocess.run(
            ["wmic", "cpu", "get", "name"],
            capture_output=True,
            text=True,
            timeout=8,
            **subprocess_win_kwargs(),
        )
        if r.returncode != 0:
            return None
        for line in r.stdout.splitlines():
            s = line.strip()
            if s and s.lower() != "name":
                return s
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def is_cpuid_identifier_junk(s: str) -> bool:
    sl = s.lower()
    return "family" in sl and "model" in sl and "stepping" in sl


def windows_cpu_marketing_name() -> str | None:
    try:
        r = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "(Get-CimInstance -ClassName Win32_Processor).Name",
            ],
            capture_output=True,
            text=True,
            timeout=12,
            **subprocess_win_kwargs(),
        )
        if r.returncode == 0:
            line = (r.stdout or "").strip().split("\n")[0].strip()
            if line and not is_cpuid_identifier_junk(line):
                return line
    except (OSError, subprocess.TimeoutExpired):
        pass
    n = wmic_cpu_name()
    if n and not is_cpuid_identifier_junk(n):
        return n
    return None


def linux_cpu_model_from_proc() -> str | None:
    try:
        with open("/proc/cpuinfo", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.lower().startswith("model name") or line.lower().startswith("hardware"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return None


def zhdate_month_day_only() -> str:
    from zhdate import ZhDate

    z = ZhDate.from_datetime(datetime.now())
    ZHNUMS = "零一二三四五六七八九十"
    if z.leap_month:
        zh_month = "闰"
    else:
        zh_month = ""
    if z.lunar_month == 1:
        zh_month += "正"
    elif z.lunar_month == 12:
        zh_month += "腊"
    elif z.lunar_month <= 10:
        zh_month += ZHNUMS[z.lunar_month]
    else:
        zh_month += f"十{ZHNUMS[z.lunar_month - 10]}"
    zh_month += "月"
    if z.lunar_day <= 10:
        zh_day = f"初{ZHNUMS[z.lunar_day]}"
    elif z.lunar_day < 20:
        zh_day = f"十{ZHNUMS[z.lunar_day - 10]}"
    elif z.lunar_day == 20:
        zh_day = "二十"
    elif z.lunar_day <= 29:
        zh_day = "廿" + ZHNUMS[z.lunar_day - 20]
    else:
        zh_day = "三十"
    return zh_month + zh_day


def wmic_computer_model() -> str | None:
    try:
        r = subprocess.run(
            ["wmic", "computersystem", "get", "Manufacturer,Model"],
            capture_output=True,
            text=True,
            timeout=8,
            **subprocess_win_kwargs(),
        )
        if r.returncode != 0:
            return None
        lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        if len(lines) < 2:
            return None
        data = lines[-1]
        parts = [p for p in re.split(r"\s{2,}", data.strip()) if p]
        return " ".join(parts) if parts else None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def wmic_baseboard() -> str | None:
    try:
        r = subprocess.run(
            ["wmic", "baseboard", "get", "Manufacturer,Product"],
            capture_output=True,
            text=True,
            timeout=8,
            **subprocess_win_kwargs(),
        )
        if r.returncode != 0:
            return None
        lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        if len(lines) < 2:
            return None
        data = lines[-1]
        parts = [p for p in re.split(r"\s{2,}", data.strip()) if p]
        return " ".join(parts) if parts else None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def screen_resolution() -> str:
    if platform.system() == "Windows":
        try:
            import ctypes

            u = ctypes.windll.user32
            return f"{int(u.GetSystemMetrics(0))}x{int(u.GetSystemMetrics(1))}"
        except Exception:
            pass
    return "-"


def temperature_best_effort() -> str:
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for _label, entries in temps.items():
                for e in entries:
                    if e.current is not None:
                        return f"{e.current:.0f}°C"
    except (AttributeError, OSError, RuntimeError):
        pass
    if platform.system() == "Windows":
        try:
            r = subprocess.run(
                [
                    "wmic",
                    "/namespace:\\\\root\\wmi",
                    "path",
                    "MSAcpi_ThermalZoneTemperature",
                    "get",
                    "CurrentTemperature",
                ],
                capture_output=True,
                text=True,
                timeout=6,
                **subprocess_win_kwargs(),
            )
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    s = line.strip()
                    if s.isdigit():
                        kelvin_tenth = int(s)
                        c = kelvin_tenth / 10.0 - 273.15
                        return f"{c:.0f}°C"
        except (OSError, subprocess.TimeoutExpired, ValueError):
            pass
    return "-"


def drives_free_all() -> str:
    parts: List[str] = []
    for p in psutil.disk_partitions(all=False):
        if not p.fstype:
            continue
        if "cdrom" in (p.opts or "").lower():
            continue
        try:
            u = psutil.disk_usage(p.mountpoint)
        except OSError:
            continue
        mp = p.mountpoint.rstrip("\\/")
        if platform.system() == "Windows" and len(mp) >= 2 and mp[1] == ":":
            letter = mp[0].upper()
            parts.append(f"{letter}:{fmt_bytes(float(u.free))}")
        else:
            label = mp or p.device
            parts.append(f"{label}:{fmt_bytes(float(u.free))}")
    return " ".join(parts) if parts else "-"


def unix_ts() -> str:
    return str(int(time.time()))


def tz_name_str() -> str:
    try:
        now = datetime.now().astimezone()
        n = now.tzname()
        return n if n else "本地"
    except Exception:
        return "-"


def tz_utc_offset_str() -> str:
    try:
        z = datetime.now().astimezone().strftime("%z")
        if len(z) >= 5:
            return f"{z[:3]}:{z[3:]}"
        return z or "+00:00"
    except Exception:
        return "-"


def lunar_str() -> str:
    try:
        import cnlunar

        L = cnlunar.Lunar(datetime.now(), godType="8char")
        m = (getattr(L, "lunarMonthCn", None) or "").strip()
        m = re.sub(r"[小大]$", "", m)
        d = (getattr(L, "lunarDayCn", None) or "").strip()
        if m and d:
            return f"{m}{d}"
    except Exception:
        pass
    try:
        return zhdate_month_day_only()
    except Exception:
        return "-"


def jieqi_str() -> str:
    try:
        import cnlunar

        L = cnlunar.Lunar(datetime.now(), godType="8char")
        t = L.get_todaySolarTerms()
        ts = str(t).strip() if t is not None else ""
        if len(ts) >= 2:
            return ts
        n = L.nextSolarTerm
        if n:
            return f"下个: {n}"
        return "-"
    except Exception:
        return "-"
