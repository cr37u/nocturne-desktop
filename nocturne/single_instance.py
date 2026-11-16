"""One Nocturne per user: later launches forward their arguments (links, nocturne:// URIs)."""

from __future__ import annotations

import getpass
import hashlib
import json
import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

log = logging.getLogger(__name__)


def _server_name() -> str:
    try:
        user = getpass.getuser()
    except Exception:  # noqa: BLE001
        user = "user"
    return "nocturne-" + hashlib.sha1(user.encode("utf-8")).hexdigest()[:12]


class SingleInstance(QObject):
    messageReceived = Signal(list)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._name = _server_name()
        self._server: QLocalServer | None = None

    def send_to_running(self, args: list[str]) -> bool:
        sock = QLocalSocket()
        sock.connectToServer(self._name)
        if not sock.waitForConnected(700):
            return False
        sock.write((json.dumps(args) + "\n").encode("utf-8"))
        sock.flush()
        sock.waitForBytesWritten(1500)
        sock.disconnectFromServer()
        return True

    def listen(self) -> bool:
        QLocalServer.removeServer(self._name)  # stale socket after a crash (Unix)
        server = QLocalServer(self)
        server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        if not server.listen(self._name):
            log.warning("Single-instance server failed: %s", server.errorString())
            return False
        server.newConnection.connect(self._on_connection)
        self._server = server
        return True

    def _on_connection(self) -> None:
        assert self._server is not None
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            buffer = bytearray()

            def on_ready(s: QLocalSocket = sock, buf: bytearray = buffer) -> None:
                buf.extend(bytes(s.readAll().data()))
                if b"\n" in buf:
                    line = bytes(buf).split(b"\n", 1)[0]
                    try:
                        args = json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError, ValueError):
                        args = []
                    if isinstance(args, list):
                        self.messageReceived.emit([str(a) for a in args])
                    s.disconnectFromServer()

            sock.readyRead.connect(on_ready)
            sock.disconnected.connect(sock.deleteLater)
