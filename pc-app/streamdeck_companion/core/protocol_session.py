"""Transport-neutral request tracking for the versioned device protocol."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Callable

from .protocol import MessageType, ProtocolMessage


class RequestTimeoutError(TimeoutError):
    """A protocol request exhausted its retry budget."""


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    timeout_seconds: float = 2.0
    max_retries: int = 2

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


@dataclass(slots=True)
class PendingRequest:
    message: ProtocolMessage
    sent_at: float
    retries: int = 0


class RequestTracker:
    """Tracks requests awaiting ACK/ERROR without knowing the transport.

    Callers register outgoing messages, feed incoming ACK/ERROR messages to
    ``resolve`` and periodically call ``due_retries``. The returned messages
    can then be resent by the concrete transport adapter.
    """

    def __init__(
        self,
        policy: RetryPolicy | None = None,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.policy = policy or RetryPolicy()
        self._clock = clock
        self._pending: dict[str, PendingRequest] = {}

    def track(self, message: ProtocolMessage) -> None:
        if message.type in (MessageType.ACK, MessageType.ERROR):
            raise ValueError("control responses must not be tracked as requests")
        self._pending[message.message_id] = PendingRequest(message, self._clock())

    def discard(self, message_id: str) -> PendingRequest | None:
        """Remove one pending request, typically when transport delivery fails."""
        return self._pending.pop(message_id, None)

    def resolve(self, response: ProtocolMessage) -> PendingRequest | None:
        if response.type not in (MessageType.ACK, MessageType.ERROR):
            return None
        if response.reply_to is None:
            return None
        return self._pending.pop(response.reply_to, None)

    def due_retries(self) -> tuple[ProtocolMessage, ...]:
        now = self._clock()
        due: list[ProtocolMessage] = []
        timed_out: list[str] = []
        for message_id, pending in tuple(self._pending.items()):
            if now - pending.sent_at < self.policy.timeout_seconds:
                continue
            if pending.retries >= self.policy.max_retries:
                timed_out.append(message_id)
                continue
            pending.retries += 1
            pending.sent_at = now
            due.append(pending.message)
        if timed_out:
            for message_id in timed_out:
                self._pending.pop(message_id, None)
            raise RequestTimeoutError(
                "request(s) exhausted retry budget: " + ", ".join(timed_out)
            )
        return tuple(due)

    def pending(self) -> tuple[PendingRequest, ...]:
        return tuple(self._pending.values())

    def clear(self) -> None:
        self._pending.clear()
