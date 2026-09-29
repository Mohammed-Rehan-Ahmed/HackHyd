"""
Notification Service
─────────────────────
Handles dispatch of urgent visual alerts to hospital dashboards
and confirmation messages to ASHA worker apps via WebSockets.
Also provides hooks for SMS / push notifications (stub).
"""

import logging
import asyncio
from typing import Optional
from services.websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)


class NotificationService:

    def __init__(self, manager: ConnectionManager):
        self.manager = manager

    async def push_referral_to_hospital(
        self, hospital_id: str, payload: dict, retries: int = 3
    ) -> bool:
        """
        Pushes a referral notification to the hospital dashboard via WebSocket.
        Returns True if the room had active connections.
        """
        for attempt in range(1, retries + 1):
            try:
                active = self.manager.get_active_connections_count()
                room = f"hospital_{hospital_id}"
                if room in active and active[room] > 0:
                    await self.manager.notify_hospital(hospital_id, payload)
                    logger.info(f"[NOTIFY] Hospital {hospital_id} notified (attempt {attempt})")
                    return True
                else:
                    logger.warning(f"[NOTIFY] Hospital {hospital_id} has no active WS connections")
                    # In production: fall back to SMS/email
                    await self._sms_fallback(hospital_id, payload)
                    return False
            except Exception as e:
                logger.error(f"[NOTIFY] Error notifying hospital {hospital_id}: {e}")
                if attempt < retries:
                    await asyncio.sleep(2)
        return False

    async def push_confirmation_to_asha(
        self, worker_id: str, payload: dict
    ) -> bool:
        """Sends referral confirmation to ASHA worker app."""
        try:
            await self.manager.notify_asha(worker_id, payload)
            logger.info(f"[NOTIFY] ASHA worker {worker_id} confirmed referral")
            return True
        except Exception as e:
            logger.error(f"[NOTIFY] Error notifying ASHA worker {worker_id}: {e}")
            return False

    async def push_status_update(
        self,
        hospital_id: str,
        worker_id: str,
        referral_id: str,
        new_status: str,
        notes: str = "",
    ):
        """Broadcasts a status update to both hospital and ASHA worker."""
        payload = {
            "type": "STATUS_UPDATE",
            "referral_id": referral_id,
            "new_status": new_status,
            "notes": notes,
        }
        await self.manager.notify_hospital(hospital_id, payload)
        await self.manager.notify_asha(worker_id, payload)

    async def _sms_fallback(self, hospital_id: str, payload: dict):
        """
        Stub for SMS/push fallback when WebSocket is unavailable.
        In production, integrate with Twilio / AWS SNS / MSG91.
        """
        logger.info(f"[SMS-STUB] Would send SMS to hospital {hospital_id}: {payload.get('referral_id')}")
        # e.g. await twilio_client.messages.create(...)
