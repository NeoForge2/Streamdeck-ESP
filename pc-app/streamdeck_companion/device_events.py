"""Translate current ESPHome events to framework-independent Core events.

This module belongs to the application/device adapter layer: the Core does not
know ESPHome entity names or the historical firmware event vocabulary.
"""

from __future__ import annotations

from collections.abc import Sequence

from .core import InputEvent, InputKind, Trigger


_ENCODER_TRIGGERS = {
    "clockwise": Trigger.ROTATE_CW,
    "anticlockwise": Trigger.ROTATE_CCW,
    "press": Trigger.PRESS,
    "hold": Trigger.HOLD,
    "release": Trigger.RELEASE,
}


def translate_esphome_event(
    entity_name: str,
    event_type: str,
    *,
    action_entity_name: str,
    encoder_entity_names: Sequence[str],
) -> InputEvent | None:
    """Translate one existing firmware event without changing its protocol."""
    if entity_name == action_entity_name:
        if event_type.startswith("action_"):
            index = _slot_index(event_type, "action_")
            if index is not None:
                return InputEvent(f"button:{index + 1}", InputKind.BUTTON, Trigger.PRESS, {"slot_index": index})
        if event_type.startswith("hold_"):
            index = _slot_index(event_type, "hold_")
            if index is not None:
                return InputEvent(f"button:{index + 1}", InputKind.BUTTON, Trigger.HOLD, {"slot_index": index})
        return None

    if entity_name in encoder_entity_names:
        trigger = _ENCODER_TRIGGERS.get(event_type)
        if trigger is None:
            return None
        index = encoder_entity_names.index(entity_name)
        return InputEvent(
            f"encoder:{index + 1}",
            InputKind.ENCODER,
            trigger,
            {"encoder_index": index},
        )
    return None


def legacy_encoder_direction(trigger: Trigger) -> str | None:
    """Map Core triggers back to the current profile config keys during migration."""
    return {
        Trigger.ROTATE_CW: "clockwise",
        Trigger.ROTATE_CCW: "anticlockwise",
        Trigger.PRESS: "press",
        Trigger.HOLD: "hold",
        Trigger.RELEASE: "release",
    }.get(trigger)


def _slot_index(event_type: str, prefix: str) -> int | None:
    try:
        value = int(event_type[len(prefix):]) - 1
    except ValueError:
        return None
    return value if value >= 0 else None
