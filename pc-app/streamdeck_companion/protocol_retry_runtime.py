"""Small retry supervisor for the live V2 protocol session."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from .core.protocol_session import RequestTimeoutError
from .core.session import ProtocolSession

LOG = logging.getLogger("streamdeck_protocol")


class ProtocolRetryRuntime:
    """Periodically resend timed-out protocol requests in a daemon thread."""

    def __init__(
        self,
        session: ProtocolSession,
        *,
        interval_seconds: float = 0.25,
        on_timeout: Callable[[RequestTimeoutError], None] | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.session = session
        self.interval_seconds = interval_seconds
        self.on_timeout = on_timeout
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="streamdeck-protocol-retry", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def tick(self) -> None:
        try:
            self.session.retry_due()
        except RequestTimeoutError as exc:
            if self.on_timeout is not None:
                self.on_timeout(exc)
            else:
                LOG.warning("Requete protocole V2 en timeout: %s", exc)

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.tick()
