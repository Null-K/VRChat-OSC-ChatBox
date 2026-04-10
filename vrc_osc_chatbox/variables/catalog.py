from __future__ import annotations

import platform
import socket
import time
from datetime import datetime
from getpass import getuser
from typing import Callable, Dict, List, Tuple

import psutil

from vrc_osc_chatbox.formatting import fmt_bytes, fmt_duration
from vrc_osc_chatbox.system_info import (
    disk_root,
    drives_free_all,
    jieqi_str,
    lunar_str,
    screen_resolution,
    temperature_best_effort,
    tz_name_str,
    tz_utc_offset_str,
    unix_ts,
    wmi_gpu_name,
    wmic_baseboard,
    wmic_computer_model,
)
from vrc_osc_chatbox.variables.context import VarContext
from vrc_osc_chatbox.variables.registry import (
    EXTRA_PLACEHOLDER_CATEGORIES,
    CategoryDef,
    VarCategoryRow,
)


def _default_categories(ctx: VarContext) -> List[CategoryDef]:
    root = disk_root()

    def mem_ram() -> str:
        v = psutil.virtual_memory()
        return f"{v.percent:.0f}% ({fmt_bytes(float(v.used))} / {fmt_bytes(float(v.total))})"

    def mem_ram_used() -> str:
        return fmt_bytes(float(psutil.virtual_memory().used))

    def mem_ram_total() -> str:
        return fmt_bytes(float(psutil.virtual_memory().total))

    def mem_ram_free() -> str:
        return fmt_bytes(float(psutil.virtual_memory().available))

    def mem_ram_percent() -> str:
        return f"{psutil.virtual_memory().percent:.1f}%"

    def mem_swap_total() -> str:
        s = psutil.swap_memory()
        return fmt_bytes(float(s.total)) if s.total else "无"

    def mem_swap_used() -> str:
        s = psutil.swap_memory()
        return fmt_bytes(float(s.used))

    def mem_swap_percent() -> str:
        s = psutil.swap_memory()
        return f"{s.percent:.1f}%" if s.total else "-"

    def cpu_pct() -> str:
        return f"{psutil.cpu_percent(interval=None):.0f}%"

    def cpu_freq() -> str:
        f = psutil.cpu_freq()
        if f and f.current:
            return f"{f.current:.0f}MHz"
        return "-"

    def cpu_logical() -> str:
        return str(psutil.cpu_count(logical=True) or 0)

    def cpu_physical() -> str:
        return str(psutil.cpu_count(logical=False) or 0)

    def gpu_line() -> str:
        n = ctx.nvidia()
        if n:
            return f"{n['name']} | VRAM {n['mem_used']}/{n['mem_total']} MiB | {n['util']}%"
        w = wmi_gpu_name()
        if w:
            return w
        return "未检测到"

    def gpu_name() -> str:
        n = ctx.nvidia()
        if n:
            return n["name"]
        w = wmi_gpu_name()
        return w or "Unknown"

    def gpu_mem_used() -> str:
        n = ctx.nvidia()
        return f"{n['mem_used']} MiB" if n else "-"

    def gpu_mem_total() -> str:
        n = ctx.nvidia()
        return f"{n['mem_total']} MiB" if n else "-"

    def gpu_util() -> str:
        n = ctx.nvidia()
        return f"{n['util']}%" if n else "-"

    def disk_sys() -> str:
        try:
            d = psutil.disk_usage(root)
        except Exception:
            d = psutil.disk_usage(".")
        return f"{d.percent:.0f}% ({fmt_bytes(float(d.used))}/{fmt_bytes(float(d.total))})"

    def disk_free() -> str:
        try:
            d = psutil.disk_usage(root)
        except Exception:
            d = psutil.disk_usage(".")
        return fmt_bytes(float(d.free))

    def disk_c() -> str:
        if platform.system() != "Windows":
            return disk_sys()
        try:
            d = psutil.disk_usage("C:\\")
            return f"C: {d.percent:.0f}% 已用"
        except Exception:
            return "-"

    def disk_c_free() -> str:
        if platform.system() != "Windows":
            return disk_free()
        try:
            d = psutil.disk_usage("C:\\")
            return fmt_bytes(float(d.free))
        except Exception:
            return "-"

    def net_sent() -> str:
        return fmt_bytes(float(psutil.net_io_counters().bytes_sent))

    def net_recv() -> str:
        return fmt_bytes(float(psutil.net_io_counters().bytes_recv))

    def net_up() -> str:
        u, _ = ctx.net_rate()
        return u

    def net_down() -> str:
        _, d = ctx.net_rate()
        return d

    def time_s() -> str:
        return datetime.now().strftime("%H:%M:%S")

    def date_s() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def datetime_s() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    weekdays = "一二三四五六日"

    def weekday_cn() -> str:
        return "星期" + weekdays[datetime.now().weekday()]

    def week_of_year() -> str:
        return f"{datetime.now().isocalendar()[1]:02d}"

    def hostname() -> str:
        return socket.gethostname()

    def username() -> str:
        try:
            return getuser()
        except Exception:
            return "-"

    def os_short() -> str:
        return f"{platform.system()} {platform.release()}"

    def os_ver() -> str:
        return platform.version()[:48] + ("…" if len(platform.version()) > 48 else "")

    def boot_s() -> str:
        return datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M")

    def uptime_s() -> str:
        return fmt_duration(time.time() - psutil.boot_time())

    def proc_count() -> str:
        return str(len(psutil.pids()))

    def battery_s() -> str:
        b = psutil.sensors_battery()
        if not b:
            return "无电池/未知"
        pct = int(b.percent)
        plug = "充电" if b.power_plugged else "电池"
        return f"{pct}% {plug}"

    def drives_all() -> str:
        return drives_free_all()

    def unix_ts_fn() -> str:
        return unix_ts()

    def tz_name() -> str:
        return tz_name_str()

    def utc_off() -> str:
        return tz_utc_offset_str()

    def lunar_d() -> str:
        return lunar_str()

    def jieqi_d() -> str:
        return jieqi_str()

    def cpu_model_s() -> str:
        n = ctx.cpu_model_cached()
        if n == "-":
            return "-"
        return n if len(n) <= 72 else n[:71] + "…"

    def machine_s() -> str:
        if platform.system() == "Windows":
            m = wmic_computer_model()
            if m:
                return m if len(m) <= 80 else m[:79] + "…"
        return "-"

    def board_s() -> str:
        if platform.system() == "Windows":
            m = wmic_baseboard()
            if m:
                return m if len(m) <= 80 else m[:79] + "…"
        return "-"

    def screen_s() -> str:
        return screen_resolution()

    def temp_s() -> str:
        return temperature_best_effort()

    cats: List[CategoryDef] = [
        (
            "内存",
            [
                ("ram", "占用与总量摘要", lambda _: mem_ram),
                ("ram_percent", "内存占用百分比", lambda _: mem_ram_percent),
                ("ram_used", "已用内存", lambda _: mem_ram_used),
                ("ram_total", "内存总量", lambda _: mem_ram_total),
                ("ram_free", "可用内存", lambda _: mem_ram_free),
                ("swap_total", "交换分区大小", lambda _: mem_swap_total),
                ("swap_used", "交换已用", lambda _: mem_swap_used),
                ("swap_percent", "交换占用百分比", lambda _: mem_swap_percent),
            ],
        ),
        (
            "处理器",
            [
                ("cpu", "CPU 利用率", lambda _: cpu_pct),
                ("cpu_model", "CPU 型号", lambda _: cpu_model_s),
                ("cpu_freq", "当前频率", lambda _: cpu_freq),
                ("cpu_logical", "逻辑核心数", lambda _: cpu_logical),
                ("cpu_physical", "物理核心数", lambda _: cpu_physical),
            ],
        ),
        (
            "显卡",
            [
                ("gpu", "显存与利用率摘要", lambda _: gpu_line),
                ("gpu_name", "GPU 名称", lambda _: gpu_name),
                ("gpu_mem_used", "已用显存", lambda _: gpu_mem_used),
                ("gpu_mem_total", "显存总量", lambda _: gpu_mem_total),
                ("gpu_util", "GPU 利用率", lambda _: gpu_util),
            ],
        ),
        (
            "磁盘",
            [
                ("disk", f"系统盘 {root.rstrip(chr(92)) or '/'} 占用摘要", lambda _: disk_sys),
                ("disk_free", "系统盘剩余空间", lambda _: disk_free),
                ("disk_c", "C 盘已用百分比", lambda _: disk_c),
                ("disk_c_free", "C 盘剩余空间", lambda _: disk_c_free),
                ("drives", "各盘符剩余空间", lambda _: drives_all),
            ],
        ),
        (
            "网络",
            [
                ("net_sent", "累计发送", lambda _: net_sent),
                ("net_recv", "累计接收", lambda _: net_recv),
                ("net_up", "当前上行速率", lambda _: net_up),
                ("net_down", "当前下行速率", lambda _: net_down),
            ],
        ),
        (
            "时间",
            [
                ("time", "时间 HH:MM:SS", lambda _: time_s),
                ("date", "日期 YYYY-MM-DD", lambda _: date_s),
                ("datetime", "日期时间", lambda _: datetime_s),
                ("unix", "Unix 秒级时间戳", lambda _: unix_ts_fn),
                ("tz", "时区名称", lambda _: tz_name),
                ("utc_offset", "UTC 偏移", lambda _: utc_off),
                ("lunar", "农历月日", lambda _: lunar_d),
                ("jieqi", "当前或下一个节气", lambda _: jieqi_d),
                ("weekday", "中文星期", lambda _: weekday_cn),
                ("week", "年内第几周", lambda _: week_of_year),
            ],
        ),
        (
            "系统",
            [
                ("hostname", "计算机名", lambda _: hostname),
                ("user", "当前用户名", lambda _: username),
                ("os", "系统名", lambda _: os_short),
                ("os_ver", "内核/版本字符串", lambda _: os_ver),
                ("boot", "开机时间", lambda _: boot_s),
                ("uptime", "运行时长", lambda _: uptime_s),
                ("processes", "进程数量", lambda _: proc_count),
                ("battery", "笔记本电池", lambda _: battery_s),
                ("machine", "品牌/机型", lambda _: machine_s),
                ("motherboard", "主板厂商与型号", lambda _: board_s),
                ("screen", "主显示器分辨率", lambda _: screen_s),
                ("temp", "温度", lambda _: temp_s),
            ],
        ),
    ]
    return cats


def build_placeholder_categories(ctx: VarContext) -> List[CategoryDef]:
    return _default_categories(ctx) + list(EXTRA_PLACEHOLDER_CATEGORIES)


def build_var_fns(ctx: VarContext) -> Dict[str, Callable[[], str]]:
    fns: Dict[str, Callable[[], str]] = {}
    for _, rows in build_placeholder_categories(ctx):
        for key, _, fac in rows:
            fns[key] = fac(ctx)
    return fns
