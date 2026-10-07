from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True, slots=True)
class BackoffPolicy:
    initial_seconds: float = 1.0
    maximum_seconds: float = 60.0
    multiplier: float = 2.0

    def __post_init__(self) -> None:
        if self.initial_seconds <= 0:
            raise ValueError("initial_seconds must be positive")
        if self.maximum_seconds < self.initial_seconds:
            raise ValueError("maximum_seconds cannot be lower than initial_seconds")
        if self.multiplier < 1:
            raise ValueError("multiplier must be at least 1")


class RetryGate:
    """Track reconnect eligibility without sleeping or owning a thread."""

    def __init__(
        self,
        policy: BackoffPolicy | None = None,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.policy = policy or BackoffPolicy()
        self._clock = clock
        self._failures = 0
        self._next_attempt_at = 0.0

    @property
    def failures(self) -> int:
        return self._failures

    @property
    def next_attempt_at(self) -> float:
        return self._next_attempt_at

    def ready(self) -> bool:
        return self._clock() >= self._next_attempt_at

    def record_success(self) -> None:
        self._failures = 0
        self._next_attempt_at = 0.0

    def record_failure(self) -> float:
        delay = min(
            self.policy.initial_seconds * (self.policy.multiplier ** self._failures),
            self.policy.maximum_seconds,
        )
        self._failures += 1
        self._next_attempt_at = self._clock() + delay
        return delay
