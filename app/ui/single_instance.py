"""Ensure only one tiqo process; second launch asks the first to raise."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

_SERVER_NAME = "tiqo-single-instance"


class SingleInstance(QObject):
    raiseRequested = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        server_name: str = _SERVER_NAME,
    ) -> None:
        super().__init__(parent)
        self._server_name = server_name
        self._server: QLocalServer | None = None
        self._last_error = ""

    @property
    def last_error(self) -> str:
        return self._last_error

    def ensure_primary(self) -> bool:
        """Return True if this process is the primary instance."""
        probe = QLocalSocket(self)
        probe.connectToServer(self._server_name)
        if probe.waitForConnected(200):
            probe.write(b"raise\n")
            probe.flush()
            probe.waitForBytesWritten(200)
            probe.disconnectFromServer()
            return False

        QLocalServer.removeServer(self._server_name)
        server = QLocalServer(self)
        self._server = server
        if not server.listen(self._server_name):
            # Another race — treat as secondary.
            self._last_error = server.errorString()
            return False
        server.newConnection.connect(self._on_new_connection)
        return True

    def _on_new_connection(self) -> None:
        if self._server is None:
            return
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            if sock is None:
                continue
            sock.readyRead.connect(lambda s=sock: self._read_and_raise(s))

    def _read_and_raise(self, sock: QLocalSocket) -> None:
        _ = sock.readAll().data()
        sock.disconnectFromServer()
        self.raiseRequested.emit()
