from __future__ import annotations

from collections.abc import Callable, Iterable

from .controls import ControlDefinition, ControlSnapshot
from .state import StateStore, StateValue


ControlListener = Callable[[ControlSnapshot], None]


class ControlStateBridge:
    """Project StateStore changes to controls bound to the changed state key."""

    def __init__(
        self,
        store: StateStore,
        controls: Iterable[ControlDefinition],
        listener: ControlListener,
    ) -> None:
        self.store = store
        self.controls = tuple(controls)
        self.listener = listener
        self._unsubscribe: Callable[[], None] | None = None
        self._by_state_key: dict[str, tuple[ControlDefinition, ...]] = {}
        grouped: dict[str, list[ControlDefinition]] = {}
        for control in self.controls:
            if control.state_key:
                grouped.setdefault(control.state_key, []).append(control)
        self._by_state_key = {key: tuple(values) for key, values in grouped.items()}

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
        for control in self._by_state_key.get(state.key, ()):
            self.listener(ControlSnapshot(definition=control, state=state))
