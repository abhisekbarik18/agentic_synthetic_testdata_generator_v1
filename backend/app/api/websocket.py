"""
WebSocket manager for real-time progress updates.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by job_id."""

    def __init__(self) -> None:
        # job_id → list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str) -> None:
        await websocket.accept()
        self._connections.setdefault(job_id, []).append(websocket)
        logger.info("WebSocket connected for job %s (total: %d)", job_id, len(self._connections[job_id]))

    def disconnect(self, websocket: WebSocket, job_id: str) -> None:
        conns = self._connections.get(job_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(job_id, None)
        logger.info("WebSocket disconnected for job %s", job_id)

    async def broadcast_to_job(self, job_id: str, message: dict[str, Any]) -> None:
        """Send a JSON message to all connections listening to this job."""
        conns = list(self._connections.get(job_id, []))
        payload = json.dumps(message, default=str)
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                self.disconnect(ws, job_id)

    async def send_personal(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception:
            pass


# Singleton manager instance used by the rest of the app.
manager = ConnectionManager()

