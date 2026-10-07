"""Adapters that feed external runtime state into the V2 StateStore."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .core import ActionState, StateStore, StateValue


def update_device_connection(store: StateStore, connected: bool, device_id: str = "streamdeck") -> StateValue:
    return store.update(
        f"device:{device_id}",
        status=ActionState.ACTIVE if connected else ActionState.DISCONNECTED,
        value=connected,
    )


def update_home_assistant_entity(
    store: StateStore,
    entity_id: str,
    state: Mapping[str, Any] | None,
) -> StateValue:
    if not entity_id:
        raise ValueError("entity_id cannot be empty")
    if state is None:
        return store.update(f"ha:{entity_id}", status=ActionState.DISCONNECTED)

    raw_value = state.get("state")
    attributes = state.get("attributes")
    if not isinstance(attributes, Mapping):
        attributes = {}

    return store.update(
        f"ha:{entity_id}",
        status=_ha_status(raw_value),
        value=raw_value,
        attributes=attributes,
    )


def _ha_status(raw_value: Any) -> ActionState:
    value = str(raw_value).lower() if raw_value is not None else ""
    if value in {"unavailable", "unknown", "none", ""}:
        return ActionState.DISCONNECTED
    if value == "on":
        return ActionState.ON
    if value == "off":
        return ActionState.OFF
    return ActionState.ACTIVE
