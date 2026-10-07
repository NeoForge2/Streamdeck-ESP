"""Application-layer bridge between Core runtime objects and protocol messages.

This adapter keeps firmware/ESPHome vocabulary outside the Core while allowing
DeviceClient migration to happen progressively: ESPHome -> InputEvent
(`device_events.py`), then InputEvent -> versioned ProtocolMessage. Dynamic
Core state can likewise be projected to UPDATE_STATE messages without making
StateStore depend on any transport.
"""

from __future__ import annotations

from .core import InputEvent, InputKind, MessageType, ProtocolMessage, StateValue, Trigger


def input_event_to_protocol(event: InputEvent) -> ProtocolMessage:
    """Convert a generic Core input event into the V2 device->PC protocol."""
    payload = {
        "source_id": event.source_id,
        "trigger": event.trigger.value,
        **dict(event.metadata),
    }

    if event.kind == InputKind.BUTTON:
        if event.trigger == Trigger.HOLD:
            message_type = MessageType.BUTTON_HOLD
        else:
            message_type = MessageType.BUTTON_PRESS
    elif event.kind == InputKind.ENCODER:
        if event.trigger in (Trigger.ROTATE_CW, Trigger.ROTATE_CCW):
            message_type = MessageType.ENCODER_ROTATE
            payload["direction"] = "cw" if event.trigger == Trigger.ROTATE_CW else "ccw"
        else:
            message_type = MessageType.ENCODER_PRESS
    elif event.kind == InputKind.TOUCH:
        message_type = MessageType.TOUCH
    else:  # pragma: no cover - InputKind currently exhausts supported inputs.
        raise ValueError(f"Unsupported input kind: {event.kind!r}")

    return ProtocolMessage(message_type, payload)


def state_value_to_protocol(state: StateValue) -> ProtocolMessage:
    """Convert one synchronized Core state into a PC->device UPDATE_STATE."""
    return ProtocolMessage(
        MessageType.UPDATE_STATE,
        {
            "key": state.key,
            "status": state.status.value,
            "value": state.value,
            "attributes": dict(state.attributes),
            "updated_at": state.updated_at,
        },
    )
