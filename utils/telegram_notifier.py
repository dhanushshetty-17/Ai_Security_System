"""Telegram alert notifier for surveillance threats.

Sends a photo + caption to a Telegram chat when HIGH/CRITICAL threats are
detected.  Uses a cooldown per camera to prevent spam.
"""

from __future__ import annotations

import json
import time
import threading
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any


class TelegramNotifier:
    """Send threat alerts to a Telegram bot chat."""

    def __init__(
        self,
        bot_token: str = "",
        chat_id: str = "",
        cooldown_sec: float = 30.0,
        min_threat_level: str = "HIGH",
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.cooldown_sec = cooldown_sec
        self.min_threat_level = min_threat_level
        self._last_sent: dict[str, float] = {}  # camera_id -> timestamp
        self._level_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def should_send(self, camera_id: str, threat_level: str) -> bool:
        if not self.enabled:
            return False
        level_val = self._level_order.get(threat_level, 0)
        min_val = self._level_order.get(self.min_threat_level, 2)
        if level_val < min_val:
            return False
        last = self._last_sent.get(camera_id, 0.0)
        if time.time() - last < self.cooldown_sec:
            return False
        return True

    def send_alert(
        self,
        camera_id: str,
        label: str,
        threat_level: str,
        snapshot_path: str | None = None,
    ) -> None:
        """Send alert in a background thread to avoid blocking."""
        if not self.should_send(camera_id, threat_level):
            return
        self._last_sent[camera_id] = time.time()
        thread = threading.Thread(
            target=self._do_send,
            args=(camera_id, label, threat_level, snapshot_path),
            daemon=True,
        )
        thread.start()

    def _do_send(
        self,
        camera_id: str,
        label: str,
        threat_level: str,
        snapshot_path: str | None,
    ) -> None:
        caption = (
            f"🚨 *NEXUS AI SECURITY ALERT*\n\n"
            f"📹 Camera: `{camera_id}`\n"
            f"⚠️ Threat: *{label}*\n"
            f"🔴 Level: *{threat_level}*\n"
            f"🕐 Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            if snapshot_path and Path(snapshot_path).exists():
                self._send_photo(snapshot_path, caption)
            else:
                self._send_message(caption)
            print(f"[Telegram] Alert sent: {label} ({threat_level})")
        except Exception as e:
            print(f"[Telegram] Failed to send alert: {e}")

    def _send_message(self, text: str) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()

    def _send_photo(self, photo_path: str, caption: str) -> None:
        """Upload a photo using multipart/form-data."""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        boundary = "----PythonFormBoundary"

        photo_data = Path(photo_path).read_bytes()
        filename = Path(photo_path).name

        body = bytearray()
        # chat_id field
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'.encode()
        body += f"{self.chat_id}\r\n".encode()
        # caption field
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="caption"\r\n\r\n'.encode()
        body += f"{caption}\r\n".encode()
        # parse_mode field
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="parse_mode"\r\n\r\n'.encode()
        body += f"Markdown\r\n".encode()
        # photo field
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="photo"; filename="{filename}"\r\n'.encode()
        body += f"Content-Type: image/jpeg\r\n\r\n".encode()
        body += photo_data
        body += f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            url,
            data=bytes(body),
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
