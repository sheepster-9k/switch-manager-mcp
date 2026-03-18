"""Async WebSocket client for Home Assistant Core API."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets

from config import config

logger = logging.getLogger("ha-client")


class HAClient:
    """Persistent WebSocket connection to HA Core for Switch Manager commands."""

    def __init__(self) -> None:
        self._ws: Any = None
        self._msg_id = 0
        self._connect_lock = asyncio.Lock()
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._reader_task: asyncio.Task[None] | None = None

    @property
    def _ws_url(self) -> str:
        base = config.ha_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{base}/api/websocket"

    async def _connect(self) -> None:
        logger.info("Connecting to %s", self._ws_url)
        self._ws = await websockets.connect(self._ws_url)

        # Auth handshake
        raw = await self._ws.recv()
        msg = json.loads(raw)
        if msg.get("type") != "auth_required":
            raise RuntimeError(f"Expected auth_required, got: {msg}")

        await self._ws.send(json.dumps({
            "type": "auth",
            "access_token": config.ha_token,
        }))

        raw = await self._ws.recv()
        msg = json.loads(raw)
        if msg.get("type") != "auth_ok":
            raise RuntimeError(f"Authentication failed: {msg}")

        logger.info("Authenticated with Home Assistant")
        self._msg_id = 0
        self._reader_task = asyncio.create_task(self._reader())

    async def _reader(self) -> None:
        """Read messages and dispatch to waiting futures."""
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                msg_id = msg.get("id")
                if msg_id is not None and msg_id in self._pending:
                    self._pending.pop(msg_id).set_result(msg)
        except Exception:
            logger.exception("WebSocket reader error")
        finally:
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(RuntimeError("Connection lost"))
            self._pending.clear()
            self._ws = None

    async def _ensure_connected(self) -> None:
        async with self._connect_lock:
            if self._ws is not None and self._reader_task and not self._reader_task.done():
                return
            await self._connect()

    async def call(self, command_type: str, **params: Any) -> dict[str, Any]:
        """Send a WebSocket command and return the result dict."""
        await self._ensure_connected()

        self._msg_id += 1
        msg_id = self._msg_id

        fut: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = fut

        payload = {"id": msg_id, "type": command_type, **params}
        await self._ws.send(json.dumps(payload))

        result = await asyncio.wait_for(fut, timeout=30.0)

        if not result.get("success", False):
            error = result.get("error", {})
            raise RuntimeError(
                f"HA command '{command_type}' failed: "
                f"{error.get('code', 'unknown')} — {error.get('message', '')}"
            )

        return result.get("result", {})


client = HAClient()
