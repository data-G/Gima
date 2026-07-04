from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import Settings


@dataclass(frozen=True)
class NotificationResult:
    provider: str
    status: str
    message_id: str | None
    detail: str


class WhatsAppNotificationService:
    """Sends paper-trading notifications; inbound messages never execute trades."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def send_text(self, body: str, recipient: str | None = None) -> NotificationResult:
        if not self.settings.notifications_enabled:
            return NotificationResult("disabled", "SKIPPED", None, "Notifications are disabled.")

        to_number = recipient or self.settings.whatsapp_default_recipient
        if self.settings.whatsapp_mode == "mock":
            return NotificationResult("mock_whatsapp", "SENT", f"MOCK-WA-{int(datetime.now(timezone.utc).timestamp())}", body)

        if not to_number:
            raise ValueError("WhatsApp recipient is required.")
        if not self.settings.whatsapp_phone_number_id or not self.settings.whatsapp_access_token:
            raise ValueError("WhatsApp Cloud API credentials are not configured.")

        token = self.settings.whatsapp_access_token.get_secret_value()
        url = f"https://graph.facebook.com/{self.settings.whatsapp_graph_version}/{self.settings.whatsapp_phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {"body": body},
        }
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        messages = data.get("messages") or []
        message_id = messages[0].get("id") if messages else None
        return NotificationResult("whatsapp_cloud", "SENT", message_id, "WhatsApp Cloud API message sent.")


def paper_order_message(order_id: int, symbol: str, side: str, quantity: int) -> str:
    return (
        "Gima Safe Trading Agent paper order needs review.\n"
        f"Order: #{order_id}\n"
        f"Symbol: {symbol}\n"
        f"Side: {side}\n"
        f"Quantity: {quantity}\n"
        "Human approval required in the dashboard. WhatsApp replies do not execute trades. Trading involves risk."
    )
