"""
WebSocket Connection Manager
─────────────────────────────
Manages multiple rooms (hospital dashboards, ASHA worker apps).
Supports broadcast-to-room and personal messages.
"""

import json
import asyncio
from typing import Dict, List
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # room_id → list of active WebSocket connections
        self.rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)
        logger.info(f"[WS] Client connected to room '{room}' — total: {len(self.rooms[room])}")

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.rooms:
            self.rooms[room] = [ws for ws in self.rooms[room] if ws != websocket]
            logger.info(f"[WS] Client disconnected from room '{room}' — remaining: {len(self.rooms[room])}")

    async def broadcast(self, message: dict, room: str):
        """Send a message to every client in a room."""
        if room not in self.rooms:
            logger.warning(f"[WS] Broadcast to empty/unknown room '{room}'")
            return
        dead: List[WebSocket] = []
        for ws in self.rooms[room]:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"[WS] Failed to send to client in '{room}': {e}")
                dead.append(ws)
        # Prune dead connections
        for ws in dead:
            self.rooms[room].remove(ws)

    async def send_personal(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"[WS] Failed to send personal message: {e}")

    async def notify_hospital(self, hospital_id: str, payload: dict):
        """Convenience wrapper — push a notification to a hospital's dashboard room."""
        room = f"hospital_{hospital_id}"
        await self.broadcast(payload, room)

    async def notify_asha(self, worker_id: str, payload: dict):
        """Convenience wrapper — push confirmation/status to an ASHA worker's app."""
        room = f"asha_{worker_id}"
        await self.broadcast(payload, room)

    def get_active_connections_count(self) -> Dict[str, int]:
        return {room: len(conns) for room, conns in self.rooms.items()}
