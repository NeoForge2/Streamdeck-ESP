"""Transport-neutral protocol session built on DevicePort and RequestTracker."""

from __future__ import annotations

from threading import RLock

from .device import DevicePort
from .protocol import MessageType, ProtocolMessage
from .protocol_session import PendingRequest, RequestTracker, RetryPolicy


class ProtocolSession:
    """Coordinate protocol delivery/retries through a concrete DevicePort.

    The runtime can send from UI/worker threads while ESPHome state callbacks
    resolve acknowledgements on its own event-loop thread. A small re-entrant
    lock keeps RequestTracker consistent without leaking transport details into
    the protocol model.
    """

    def __init__(
        self,
        port: DevicePort,
        *,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.port = port
        self.tracker = RequestTracker(retry_policy)
        self._lock = RLock()

    def send(self, message: ProtocolMessage, *, expect_response: bool = True) -> None:
        with self._lock:
            should_track = expect_response and message.type not in (MessageType.ACK, MessageType.ERROR)
            if should_track:
                self.tracker.track(message)
            try:
                self.port.send(message)
            except Exception:
                if should_track:
                    self.tracker.discard(message.message_id)
                raise

    def receive(self, message: ProtocolMessage) -> PendingRequest | None:
        """Resolve an incoming ACK/ERROR against the pending request set."""
        with self._lock:
            return self.tracker.resolve(message)

    def retry_due(self) -> tuple[ProtocolMessage, ...]:
        """Resend requests whose timeout elapsed and return the resent messages."""
        with self._lock:
            messages = self.tracker.due_retries()
            for message in messages:
                self.port.send(message)
            return messages

    def pending(self) -> tuple[PendingRequest, ...]:
        with self._lock:
            return self.tracker.pending()

    def clear(self) -> None:
        with self._lock:
            self.tracker.clear()
