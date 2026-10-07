"""Read-only adapters from current profile controls to V2 Core controls."""

from __future__ import annotations

from typing import Any, Mapping

from . import profiles as profile_utils
from .core.actions import ActionCommand
from .core.controls import ControlDefinition
from .core.events import InputKind
from .core.legacy import from_legacy
from .core.triggers import Trigger


_BUTTON_TRIGGER_KEYS: dict[str, Trigger] = {
    "press": Trigger.PRESS,
    "double_press": Trigger.DOUBLE_PRESS,
    "hold": Trigger.HOLD,
    "long_press": Trigger.LONG_PRESS,
    "release": Trigger.RELEASE,
}

_ENCODER_TRIGGER_KEYS: dict[str, Trigger] = {
    "clockwise": Trigger.ROTATE_CW,
    "anticlockwise": Trigger.ROTATE_CCW,
    "press": Trigger.PRESS,
    "hold": Trigger.HOLD,
    "release": Trigger.RELEASE,
}


def controls_from_legacy_profile(profile: Mapping[str, Any]) -> tuple[ControlDefinition, ...]:
    controls: list[ControlDefinition] = []
    profile_dict = dict(profile)

    for index in range(profile_utils.SLOT_COUNT):
        slot = profile_utils.resolve_slot(profile_dict, index)
        if not slot.get("visible"):
            continue
        actions: dict[Trigger, ActionCommand] = {}
        primary = _legacy_command(slot.get("action"))
        if primary is not None:
            actions[Trigger.PRESS] = primary
        for key, raw in (slot.get("trigger_actions") or {}).items():
            trigger = _BUTTON_TRIGGER_KEYS.get(str(key))
            command = _legacy_command(raw)
            if trigger is not None and command is not None:
                actions[trigger] = command
        controls.append(
            ControlDefinition(
                id=f"button:{index + 1}",
                kind=InputKind.BUTTON,
                actions=actions,
                state_key=_state_key(slot),
                context={"slot_index": index, "library_id": slot.get("library_id")},
            )
        )

    for index, encoder in enumerate(profile.get("encoders") or []):
        actions: dict[Trigger, ActionCommand] = {}
        for key, trigger in _ENCODER_TRIGGER_KEYS.items():
            command = _legacy_command((encoder or {}).get(key))
            if command is not None:
                actions[trigger] = command
        controls.append(
            ControlDefinition(
                id=f"encoder:{index + 1}",
                kind=InputKind.ENCODER,
                actions=actions,
                state_key=str((encoder or {}).get("state_key") or "") or None,
                context={"encoder_index": index, "display": (encoder or {}).get("display") or {}},
            )
        )
    return tuple(controls)


def _legacy_command(raw: object) -> ActionCommand | None:
    if not isinstance(raw, Mapping):
        return None
    return from_legacy(raw)


def _state_key(slot: Mapping[str, Any]) -> str | None:
    explicit = slot.get("state_key")
    if explicit:
        return str(explicit)
    entity = slot.get("ha_entity")
    return f"ha:{entity}" if entity else None
