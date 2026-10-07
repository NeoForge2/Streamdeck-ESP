"""Live runtime binding between ESPHomeDevicePort and V2DeviceClient.

This module keeps the transport adapter small while mapping V2 protocol
messages onto operations the current companion/firmware can represent safely.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .esphome_device_port import ESPHomeDevicePort


PROTOCOL_REQUEST_ENTITY_NAME = "Protocole V2 - requete"
PROTOCOL_ACK_ENTITY_NAME = "Protocole V2 - acquittement"


class V2DeviceRuntime(Protocol):
    connected: bool

    def schedule_set_active_profile(self, name: str, timeout: float = 5.0) -> None: ...

    def schedule_push(self, timeout: float = 5.0) -> None: ...

    def schedule_navigation(self, command: str, target: str | None = None, timeout: float = 5.0) -> str: ...

    def schedule_slot_payload(self, kind: str, payload: Mapping[str, Any], timeout: float = 5.0) -> None: ...

    def schedule_protocol_request(self, message_id: str, timeout: float = 5.0) -> None: ...


def build_esphome_device_port(runtime: V2DeviceRuntime) -> ESPHomeDevicePort:
    """Create the concrete DevicePort used by the current ESPHome runtime."""
    return ESPHomeDevicePort(
        runtime,
        sync_sender=runtime.schedule_push,
        profile_sender=lambda payload: _set_profile(runtime, payload),
        page_sender=lambda payload: _set_page(runtime, payload),
        button_sender=lambda payload: runtime.schedule_slot_payload("button", payload),
        widget_sender=lambda payload: runtime.schedule_slot_payload("widget", payload),
        ack_sender=runtime.schedule_protocol_request,
    )


def _set_profile(runtime: V2DeviceRuntime, payload: Mapping[str, Any]) -> None:
    profile_name = _required_text(payload, "profile_name", fallback_key="profile_id")
    runtime.schedule_set_active_profile(profile_name)


def _set_page(runtime: V2DeviceRuntime, payload: Mapping[str, Any]) -> None:
    page_id = _required_text(payload, "page_id")
    runtime.schedule_navigation("go_to", page_id)


def _required_text(payload: Mapping[str, Any], key: str, *, fallback_key: str | None = None) -> str:
    raw = payload.get(key)
    if (raw is None or str(raw).strip() == "") and fallback_key is not None:
        raw = payload.get(fallback_key)
    value = str(raw or "").strip()
    if not value:
        expected = f"{key!r}" if fallback_key is None else f"{key!r} or {fallback_key!r}"
        raise RuntimePayloadError(f"payload requires {expected}")
    return value


class RuntimePayloadError(ValueError):
    """A protocol payload cannot be projected onto the live runtime."""
