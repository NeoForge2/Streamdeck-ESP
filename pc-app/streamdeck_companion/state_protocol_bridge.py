"""Bridge shared runtime state updates to transport-neutral V2 messages."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from .core import ProtocolMessage, StateStore, StateValue
from .device_protocol import state_value_to_protocol


ProtocolSink = Callable[[ProtocolMessage], None]


class StateProtocolBridge:
    """Projects StateStore changes into UPDATE_STATE protocol messages.

    The bridge does not own a socket or ESPHome connection. Any concrete
    transport can provide a ``sink`` callable, which keeps StateStore and the
    protocol layer independent from hardware/network details.
    """

    def __init__(
        self,
        store: StateStore,
        sink: ProtocolSink,
        *,
        prefixes: Iterable[str] | None = None,
    ) -> None:
        self.store = store
        self.sink = sink
        self.prefixes = tuple(prefixes or ())
        self._unsubscribe: Callable[[], None] | None = None

    @property
    def started(self) -> bool:
        return self._unsubscribe is not None

    def start(self, *, replay_snapshot: bool = True) -> None:
        if self.started:
            return
        self._unsubscribe = self.store.subscribe(self._on_state)
        if replay_snapshot:
            for state in self.store.snapshot().values():
                self._on_state(state)

    def stop(self) -> None:
        if self._unsubscribe is None:
            return
        self._unsubscribe()
        self._unsubscribe = None

    def _on_state(self, state: StateValue) -> None:
        if self.prefixes and not state.key.startswith(self.prefixes):
            return
        self.sink(state_value_to_protocol(state))
