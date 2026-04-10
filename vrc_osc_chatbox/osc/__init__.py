from __future__ import annotations

from pythonosc.udp_client import SimpleUDPClient


def send_chatbox(client: SimpleUDPClient, text: str, play_sound: bool = True) -> None:
    client.send_message("/chatbox/input", [text, True, play_sound])
