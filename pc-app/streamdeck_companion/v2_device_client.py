"""Progressive V2 runtime wrapper around the historical DeviceClient.

The existing DeviceClient remains the hardware/ESPHome implementation while
this subclass injects V2 event, state, navigation and protocol concepts around
it. Special UI behavior and existing firmware commands stay in the historical
class.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import actions as action_runner
from . import profile_pages
from .core.legacy import to_legacy
from .core.navigator import NavigationError, Navigator
from .core.protocol import MessageType, ProtocolMessage
from .core.session import ProtocolSession
from .device_client import (
    ACTION_EVENT_ENTITY,
    ENCODER_EVENT_ENTITIES,
    SLOT_COLOR_NAMES,
    SLOT_GRID_NAMES,
    SLOT_ICON_NAMES,
    SLOT_LABEL_NAMES,
    SLOT_TYPE_NAMES,
    SLOT_VALUE_NAMES,
    SLOT_VISIBLE_NAMES,
    DeviceClient,
)
from .device_event_runtime import resolve_esphome_action
from .esphome_port_runtime import (
    PROTOCOL_ACK_ENTITY_NAME,
    PROTOCOL_REQUEST_ENTITY_NAME,
    build_esphome_device_port,
)
from .esphome_slot_projection import SlotProjection, project_button_payload, project_widget_payload
from .multi_action_runtime import MultiActionRuntime
from .navigation_legacy import profile_from_legacy
from .protocol_retry_runtime import ProtocolRetryRuntime
from .runtime_state import STATE_STORE
from .state_adapters import update_device_connection
from .v2_runtime_actions import execute_navigation_target, register_multi_action, register_navigation_action


_ACKED_PROTOCOL_TYPES = frozenset(
    {
        MessageType.SET_PROFILE,
        MessageType.SET_PAGE,
        MessageType.SET_BUTTON,
        MessageType.SET_WIDGET,
        MessageType.SYNC,
        MessageType.PING,
    }
)


class V2DeviceClient(DeviceClient):
    """DeviceClient using V2 adapters without changing legacy ESPHome behavior."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._navigator: Navigator | None = None
        self._navigator_source_key: tuple[object, ...] | None = None
        self._multi_action_runtime = MultiActionRuntime(lambda: self.config, self._dispatch_multi_action_command)
        self.device_port = build_esphome_device_port(self)
        self.protocol_session = ProtocolSession(self.device_port)
        self._protocol_retry_runtime = ProtocolRetryRuntime(self.protocol_session)
        self._protocol_retry_runtime.start()
        register_navigation_action(self)
        register_multi_action(self._multi_action_runtime)

    async def connect(self) -> None:
        """Connect legacy runtime, then discover the optional V2 ACK entities."""
        await super().connect()
        if self.client is None:
            return
        entities, _services = await self.client.list_entities_services()
        for entity in entities:
            name = getattr(entity, "name", "")
            key = getattr(entity, "key", None)
            if key is None:
                continue
            if name == PROTOCOL_REQUEST_ENTITY_NAME:
                self.entity_keys[name] = key
            elif name == PROTOCOL_ACK_ENTITY_NAME:
                self.entity_keys[name] = key
                self.key_to_entity_name[key] = name

    @property
    def connected(self) -> bool:
        return getattr(self, "_v2_connected", False)

    @connected.setter
    def connected(self, value: bool) -> None:
        connected = bool(value)
        self._v2_connected = connected
        update_device_connection(STATE_STORE, connected)
        if not connected and hasattr(self, "protocol_session"):
            self.protocol_session.clear()

    def send_protocol(self, message: ProtocolMessage, *, expect_response: bool | None = None) -> None:
        """Send one V2 message through the live DevicePort.

        Configuration/control messages use the firmware ACK channel by default.
        UPDATE_STATE remains fire-and-forget to avoid acknowledgement traffic for
        high-frequency state propagation. Older firmware remains compatible: if
        the ACK entities are absent, tracked requests naturally retry then time
        out instead of pretending that the device confirmed the command.
        """
        if expect_response is None:
            expect_response = message.type in _ACKED_PROTOCOL_TYPES
        self.protocol_session.send(message, expect_response=expect_response)

    def schedule_protocol_request(self, message_id: str, timeout: float = 5.0) -> None:
        """Push a message id through the P4 acknowledgement round-trip entity."""

        def _send_request() -> None:
            if self.client is None or not self.connected:
                raise RuntimeError("Pas encore connecte a l'ecran")
            key = self.entity_keys.get(PROTOCOL_REQUEST_ENTITY_NAME)
            if key is None:
                # Backward compatibility with firmware flashed before the V2
                # ACK channel. ProtocolSession will retry/timeout when tracking.
                return
            self.client.text_command(key, message_id[:64])

        self._run_threadsafe(_send_request, timeout)

    def on_state(self, state) -> None:
        entity_name = self.key_to_entity_name.get(getattr(state, "key", None))
        if entity_name == PROTOCOL_ACK_ENTITY_NAME:
            reply_to = str(getattr(state, "state", "") or "").strip()
            if reply_to:
                self.protocol_session.receive(ProtocolMessage(MessageType.ACK, reply_to=reply_to))
            return
        super().on_state(state)

    def _base_active_profile(self) -> dict:
        return super()._active_profile()

    def _ensure_navigator(self, profile: dict) -> Navigator:
        core_profile = profile_from_legacy(profile)
        source_key = (
            id(profile),
            core_profile.id,
            core_profile.home_page_id,
            tuple(page.id for page in core_profile.pages),
            tuple((folder.id, folder.page_id, folder.parent_id) for folder in core_profile.folders),
        )
        if self._navigator is None:
            self._navigator = Navigator(core_profile)
            self._navigator_source_key = source_key
        elif self._navigator_source_key != source_key:
            self._navigator.reset_profile(core_profile)
            self._navigator_source_key = source_key
        return self._navigator

    def _active_legacy_page_id(self, profile: dict | None = None) -> str:
        base_profile = profile or self._base_active_profile()
        navigator = self._ensure_navigator(base_profile)
        return str(navigator.current_page.metadata.get("legacy_page_id") or profile_pages.HOME_PAGE_ID)

    def _active_profile(self) -> dict:
        """Return a legacy-compatible view whose root slots are the active page."""
        base_profile = self._base_active_profile()
        page_id = self._active_legacy_page_id(base_profile)
        home_id = str(base_profile.get("home_page_id") or profile_pages.HOME_PAGE_ID)
        if page_id == home_id:
            return base_profile
        view = dict(base_profile)
        view["slots"] = profile_pages.page_slots(base_profile, page_id)
        view["_v2_active_page_id"] = page_id
        return view

    @property
    def active_page_id(self) -> str:
        return self._active_legacy_page_id()

    def navigate(self, command: str, target: str | None = None) -> str:
        """Navigate pages through the pure Core Navigator and refresh the screen."""
        base_profile = self._base_active_profile()
        navigator = self._ensure_navigator(base_profile)
        normalized = command.strip().lower().replace("-", "_")

        if normalized == "next":
            page = navigator.next()
        elif normalized == "previous":
            page = navigator.previous()
        elif normalized == "home":
            page = navigator.home()
        elif normalized == "back":
            page = navigator.back()
        elif normalized in {"go_to", "goto"}:
            if not target:
                raise NavigationError("go_to requires a target page id")
            page = navigator.go_to(self._core_page_id(navigator, target))
        else:
            raise NavigationError(f"unknown navigation command: {command!r}")

        self._refresh_after_navigation()
        return str(page.metadata.get("legacy_page_id") or profile_pages.HOME_PAGE_ID)

    def schedule_navigation(
        self,
        command: str,
        target: str | None = None,
        timeout: float = 5.0,
    ) -> str:
        """Run navigation safely from non-ESPHome threads (protocol/UI workers)."""
        result: list[str] = []
        self._run_threadsafe(lambda: result.append(self.navigate(command, target)), timeout)
        if not result:
            raise RuntimeError("navigation did not return a page")
        return result[0]

    def schedule_slot_payload(
        self,
        kind: str,
        payload: Mapping[str, Any],
        timeout: float = 5.0,
    ) -> None:
        """Validate a V2 slot payload then apply it on the ESPHome loop."""
        projection = project_button_payload(payload) if kind == "button" else project_widget_payload(payload)
        self._run_threadsafe(lambda: self._push_slot_projection(projection), timeout)

    def _push_slot_projection(self, projection: SlotProjection) -> None:
        """Apply one partial slot update using the current ESPHome entities.

        The firmware exposes each slot property as a separate optimistic
        entity, so this is intentionally a best-effort sequence rather than an
        atomic transaction. Full consistency can always be restored with SYNC.
        """
        if self.client is None or not self.connected:
            raise RuntimeError("Pas encore connecte a l'ecran")
        idx = projection.slot_index

        type_key = self.entity_keys.get(SLOT_TYPE_NAMES[idx])
        if type_key is not None:
            self.client.select_command(type_key, projection.slot_type)
        if projection.label is not None:
            key = self.entity_keys.get(SLOT_LABEL_NAMES[idx])
            if key is not None:
                self.client.text_command(key, projection.label)
        if projection.icon is not None:
            key = self.entity_keys.get(SLOT_ICON_NAMES[idx])
            if key is not None:
                self.client.text_command(key, projection.icon)
        if projection.visible is not None:
            key = self.entity_keys.get(SLOT_VISIBLE_NAMES[idx])
            if key is not None:
                self.client.switch_command(key, projection.visible)
        if projection.grid is not None:
            key = self.entity_keys.get(SLOT_GRID_NAMES[idx])
            if key is not None:
                self.client.text_command(key, projection.grid)
        if projection.value is not None:
            key = self.entity_keys.get(SLOT_VALUE_NAMES[idx])
            if key is not None:
                self.client.text_command(key, projection.value)
        if projection.color is not None:
            key = self.entity_keys.get(SLOT_COLOR_NAMES[idx])
            if key is not None:
                self.client.text_command(key, projection.color)

    def open_folder(self, folder_id: str) -> str:
        """Open a nested folder through the same Navigator used by page actions."""
        navigator = self._ensure_navigator(self._base_active_profile())
        page = navigator.open_folder(folder_id)
        self._refresh_after_navigation()
        return str(page.metadata.get("legacy_page_id") or profile_pages.HOME_PAGE_ID)

    def _refresh_after_navigation(self) -> None:
        if self.connected:
            self.push_config()

    def _dispatch_multi_action_command(self, command):
        legacy = to_legacy(command)
        if command.action_id == "home_assistant":
            return self._run_home_assistant_action(legacy)
        if command.action_id == "ha_adjust":
            return self._run_ha_adjust(legacy)
        if command.action_id == "navigation":
            target = str(command.parameters.get("target") or "")
            return self._run_threadsafe(lambda: execute_navigation_target(self, target), 5.0)
        if command.action_id == "multi_action":
            raise ValueError("nested multi actions are not supported yet")
        return action_runner.run(legacy)

    @staticmethod
    def _core_page_id(navigator: Navigator, legacy_page_id: str) -> str:
        for page in navigator.profile.pages:
            if page.metadata.get("legacy_page_id") == legacy_page_id:
                return page.id
        raise NavigationError(f"unknown page: {legacy_page_id!r}")

    def _resolve_action(self, entity_name: str, event_type: str) -> dict | None:
        """Resolve current config through ESPHome -> Core -> active V2 page."""
        profile = self._base_active_profile()
        return resolve_esphome_action(
            profile,
            entity_name,
            event_type,
            action_entity_name=ACTION_EVENT_ENTITY,
            encoder_entity_names=ENCODER_EVENT_ENTITIES,
            page_id=self._active_legacy_page_id(profile),
        )
