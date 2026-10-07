from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .action_wheel import ActionWheel, ActionWheelSnapshot
from .actions import ActionCommand
from .navigation import Profile
from .navigation_session import NavigationSession, NavigationSnapshot
from .state import StateStore, StateValue
from .widgets import WidgetDefinition, WidgetResolver, WidgetSnapshot


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    navigation: NavigationSnapshot
    widgets: tuple[WidgetSnapshot, ...]


class StreamdeckRuntime:
    """Framework-independent coordinator for navigation, state and interactive widgets."""

    def __init__(self, profile: Profile, state_store: StateStore) -> None:
        self.profile = profile
        self.state_store = state_store
        self.navigation = NavigationSession(profile)
        self.widgets = WidgetResolver(state_store)
        self._wheels: dict[str, ActionWheel] = {}
        self._unsubscribe: Callable[[], None] | None = None
        self._listeners: list[Callable[[StateValue], None]] = []

    def start(self) -> None:
        if self._unsubscribe is None:
            self._unsubscribe = self.state_store.subscribe(self._on_state)

    def stop(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def subscribe_state(self, listener: Callable[[StateValue], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)
        return unsubscribe

    def snapshot(self, widgets: tuple[WidgetDefinition, ...] = ()) -> RuntimeSnapshot:
        return RuntimeSnapshot(self.navigation.snapshot(), self.widgets.resolve_many(widgets))

    def register_wheel(self, wheel_id: str, wheel: ActionWheel) -> None:
        if not wheel_id:
            raise ValueError("wheel_id cannot be empty")
        self._wheels[wheel_id] = wheel

    def rotate_wheel(self, wheel_id: str, delta: int) -> ActionWheelSnapshot:
        return self._wheel(wheel_id).rotate(delta)

    def touch_wheel(self, wheel_id: str, item_id: str) -> ActionWheelSnapshot:
        return self._wheel(wheel_id).select(item_id)

    def activate_wheel(self, wheel_id: str) -> ActionCommand:
        return self._wheel(wheel_id).activate()

    def _wheel(self, wheel_id: str) -> ActionWheel:
        try:
            return self._wheels[wheel_id]
        except KeyError as exc:
            raise KeyError(f"unknown action wheel: {wheel_id!r}") from exc

    def _on_state(self, state: StateValue) -> None:
        for listener in tuple(self._listeners):
            listener(state)
