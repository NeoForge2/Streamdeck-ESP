"""Runtime adapters between current ESPHome events and V2 Core events/actions.

This module is deliberately kept outside ``core``: it knows the historical
profile representation and page compatibility helpers. ``DeviceClient`` can
therefore migrate to generic ``InputEvent`` objects without forcing an
immediate dashboard_config.yaml migration.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import profile_pages
from . import profiles as profile_utils
from .core import InputEvent, InputKind
from .device_events import legacy_encoder_direction, translate_esphome_event


def resolve_esphome_action(
    profile: dict,
    entity_name: str,
    event_type: str,
    *,
    action_entity_name: str,
    encoder_entity_names: Sequence[str],
    page_id: str | None = None,
) -> dict | None:
    """Bridge the current firmware vocabulary through the generic Core model.

    The current ESPHome event is translated once into ``InputEvent`` and then
    resolved against the existing profile structure. Special UI events that
    are not generic inputs intentionally return ``None`` and remain handled by
    ``DeviceClient`` during the compatibility phase.
    """
    event = translate_esphome_event(
        entity_name,
        event_type,
        action_entity_name=action_entity_name,
        encoder_entity_names=encoder_entity_names,
    )
    if event is None:
        return None
    return resolve_legacy_action(profile, event, page_id=page_id)


def resolve_legacy_action(
    profile: dict,
    event: InputEvent,
    *,
    page_id: str | None = None,
) -> dict | None:
    """Resolve the configured legacy action for a generic input event.

    Button events optionally resolve against a V2-compatible page while
    encoders remain profile-scoped. Unknown/incomplete events simply resolve
    to ``None``.
    """
    if event.kind == InputKind.BUTTON:
        index = _metadata_index(event, "slot_index")
        if index is None or not (0 <= index < profile_utils.SLOT_COUNT):
            return None
        slot = (
            profile_pages.resolve_page_slot(profile, page_id, index)
            if page_id is not None
            else profile_utils.resolve_slot(profile, index)
        )
        return slot.get("action")

    if event.kind == InputKind.ENCODER:
        index = _metadata_index(event, "encoder_index")
        direction = legacy_encoder_direction(event.trigger)
        if index is None or direction is None:
            return None
        encoders = profile.get("encoders") or []
        if not (0 <= index < len(encoders)):
            return None
        return (encoders[index] or {}).get(direction)

    return None


def _metadata_index(event: InputEvent, key: str) -> int | None:
    value = event.metadata.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    try:
        return int(value)
    except ValueError:
        return None
