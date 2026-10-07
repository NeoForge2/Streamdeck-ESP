"""Project V2 SET_BUTTON/SET_WIDGET payloads onto current ESPHome slot fields."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

SLOT_COUNT = 36
BUTTON_KIND = "bouton"
WIDGET_KINDS = frozenset({"barre", "texte"})


class SlotProjectionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SlotProjection:
    slot_index: int
    slot_type: str
    label: str | None = None
    icon: str | None = None
    visible: bool | None = None
    grid: str | None = None
    value: str | None = None
    color: str | None = None


def project_button_payload(payload: Mapping[str, Any]) -> SlotProjection:
    return _project(payload, forced_type=BUTTON_KIND, allowed_types=frozenset({BUTTON_KIND}))


def project_widget_payload(payload: Mapping[str, Any]) -> SlotProjection:
    return _project(payload, forced_type=None, allowed_types=WIDGET_KINDS)


def _project(
    payload: Mapping[str, Any],
    *,
    forced_type: str | None,
    allowed_types: frozenset[str],
) -> SlotProjection:
    raw_index = payload.get("slot_index")
    if isinstance(raw_index, bool) or not isinstance(raw_index, (int, str)):
        raise SlotProjectionError("slot_index must be an integer from 0 to 35")
    try:
        slot_index = int(raw_index)
    except ValueError as exc:
        raise SlotProjectionError("slot_index must be an integer from 0 to 35") from exc
    if not 0 <= slot_index < SLOT_COUNT:
        raise SlotProjectionError("slot_index must be between 0 and 35")

    slot_type = forced_type or str(payload.get("type") or "").strip().lower()
    if slot_type not in allowed_types:
        raise SlotProjectionError(f"unsupported slot type: {slot_type!r}")

    label = _optional_text(payload, "label", 24)
    icon = _optional_text(payload, "icon", 20)
    value = _optional_text(payload, "value", 24)
    color = _optional_text(payload, "color", 7)
    if color is not None and color and (len(color) != 7 or not color.startswith("#")):
        raise SlotProjectionError("color must be empty or #RRGGBB")

    visible = payload.get("visible") if "visible" in payload else None
    if visible is not None and not isinstance(visible, bool):
        raise SlotProjectionError("visible must be boolean")

    grid = None
    if "grid" in payload:
        raw_grid = payload["grid"]
        if not isinstance(raw_grid, Mapping):
            raise SlotProjectionError("grid must be a mapping")
        values: list[int] = []
        for key, default in (("col", 0), ("row", 0), ("colspan", 1), ("rowspan", 1)):
            raw = raw_grid.get(key, default)
            if isinstance(raw, bool) or not isinstance(raw, (int, str)):
                raise SlotProjectionError(f"grid.{key} must be an integer")
            try:
                values.append(int(raw))
            except ValueError as exc:
                raise SlotProjectionError(f"grid.{key} must be an integer") from exc
        col, row, colspan, rowspan = values
        if col < 0 or row < 0 or colspan < 1 or rowspan < 1:
            raise SlotProjectionError("grid coordinates/spans are invalid")
        grid = f"{col},{row},{colspan},{rowspan}"

    return SlotProjection(
        slot_index=slot_index,
        slot_type=slot_type,
        label=label,
        icon=icon,
        visible=visible,
        grid=grid,
        value=value,
        color=color,
    )


def _optional_text(payload: Mapping[str, Any], key: str, max_length: int) -> str | None:
    if key not in payload:
        return None
    value = str(payload.get(key) or "")
    return value[:max_length]
