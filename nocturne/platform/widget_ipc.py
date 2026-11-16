r"""Named-pipe server ``\\.\pipe\nocturne`` for the Windows 11 Widgets board bridge.

Protocol: UTF-8 JSON lines.

* Python → bridge: ``{"type": "state", "title", "artist", "artworkPath", "isPlaying",
  "position", "duration", "recent": [...], "lang"}`` on every change.
* Bridge → Python: ``{"cmd": "play_pause" | "next" | "previous" | "open_add_link"}``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import threading
from typing import Any

from PySide6.QtCore import QObject, Signal

log = logging.getLogger(__name__)

PIPE_NAME = r"\\.\pipe\nocturne"
ALLOWED_COMMANDS = {"play_pause", "play", "pause", "next", "previous", "open_add_link", "show"}


class _PipeProtocol(asyncio.Protocol):
    def __init__(self, server: "WidgetBridgeServer") -> None:
        self._server = server
        self._buffer = b""
        self.transport: asyncio.BaseTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport
        self._server._clients.add(self)  # noqa: SLF001
        log.info("Widget bridge connected")
        if self._server._last_line:  # noqa: SLF001
            self.write(self._server._last_line)  # noqa: SLF001

    def connection_lost(self, exc: Exception | None) -> None:
        self._server._clients.discard(self)  # noqa: SLF001
        log.info("Widget bridge disconnected")

    def data_received(self, data: bytes) -> None:
        self._buffer += data
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue
            cmd = msg.get("cmd") if isinstance(msg, dict) else None
            if cmd in ALLOWED_COMMANDS:
                self._server.commandReceived.emit(cmd)
            elif cmd == "hello":
                if self._server._last_line:  # noqa: SLF001
                    self.write(self._server._last_line)  # noqa: SLF001
        if len(self._buffer) > 65536:
            self._buffer = b""

    def write(self, payload: bytes) -> None:
        transport = self.transport
        if transport is not None and not transport.is_closing():
            transport.write(payload)  # type: ignore[attr-defined]


class WidgetBridgeServer(QObject):
    commandReceived = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._clients: set[_PipeProtocol] = set()
        self._servers: list[Any] = []
        self._last_line = b""
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        if sys.platform != "win32":
            return False
        ready = threading.Event()
        ok: list[bool] = [False]

        def run() -> None:
            loop = asyncio.ProactorEventLoop()  # type: ignore[attr-defined]
            asyncio.set_event_loop(loop)
            self._loop = loop
            try:
                self._servers = loop.run_until_complete(
                    loop.start_serving_pipe(lambda: _PipeProtocol(self), PIPE_NAME)  # type: ignore[attr-defined]
                )
                ok[0] = True
            except Exception:  # noqa: BLE001
                log.exception("Could not open %s", PIPE_NAME)
            ready.set()
            if ok[0]:
                loop.run_forever()

        self._thread = threading.Thread(target=run, name="widget-ipc", daemon=True)
        self._thread.start()
        ready.wait(5)
        if ok[0]:
            log.info("Widget IPC listening on %s", PIPE_NAME)
        return ok[0]

    def publish(self, state: dict[str, Any]) -> None:
        line = (json.dumps({"type": "state", **state}, ensure_ascii=False) + "\n").encode("utf-8")
        if line == self._last_line:
            return
        self._last_line = line
        loop = self._loop
        if loop is None:
            return

        def send() -> None:
            for client in list(self._clients):
                try:
                    client.write(line)
                except Exception:  # noqa: BLE001
                    self._clients.discard(client)

        loop.call_soon_threadsafe(send)

    def stop(self) -> None:
        loop = self._loop
        if loop is None:
            return

        def shutdown() -> None:
            for server in self._servers:
                try:
                    server.close()
                except Exception:  # noqa: BLE001
                    pass
            for client in list(self._clients):
                if client.transport is not None:
                    client.transport.close()
            loop.stop()

        loop.call_soon_threadsafe(shutdown)
