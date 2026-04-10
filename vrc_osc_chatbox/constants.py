from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppMetadata:
    app_title: str = "VRChat OSC 聊天框消息工具"
    version: str = "1.0.0"
    author: str = "PuddingKC"
    community_qq: str = "1047423396"
    theme: str = "darkly"
    about_title: str = "关于软件"

    def about_message(self) -> str:
        return (
            "VRChat OSC 聊天框消息工具\n"
            "\n"
            f"版本: v{self.version}\n"
            f"作者: {self.author}\n"
            f"交流群: {self.community_qq}\n"
        )


METADATA = AppMetadata()

CHATBOX_MAX_LEN = 144
CONFIG_FILENAME = "vrc_osc_chatbox_config.json"
CONFIG_VERSION = 1
ICON_FILENAME = "app.ico"

DEFAULT_TEMPLATE = (
    "CPU: {cpu_model}\n"
    "GPU: {gpu_name}\n"
    "VRAM: {gpu_mem_used}/{gpu_mem_total}\n"
    "RAM: {ram_percent} ({ram_used}/{ram_total})\n"
    "⏱{time} UTC{utc_offset}"
)
