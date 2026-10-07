from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .actions import ActionDefinition
from .registry import ActionRegistry


class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    HOTKEY = "hotkey"
    ENTITY = "entity"


@dataclass(frozen=True, slots=True)
class InspectorField:
    key: str
    label: str
    field_type: FieldType = FieldType.TEXT
    required: bool = False
    default: Any = None
    options: tuple[str, ...] = ()
    options_source: str | None = None

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("field key cannot be empty")
        if not self.label:
            raise ValueError("field label cannot be empty")
        if self.field_type == FieldType.SELECT and not self.options and not self.options_source:
            raise ValueError("select fields require options or options_source")


@dataclass(frozen=True, slots=True)
class InspectorSchema:
    action_id: str
    fields: tuple[InspectorField, ...]


class PropertyInspector:
    def __init__(self, registry: ActionRegistry) -> None:
        self.registry = registry

    def schema(self, action_id: str) -> InspectorSchema:
        definition = self.registry.get(action_id)
        return InspectorSchema(action_id=action_id, fields=self._fields(definition))

    def _fields(self, definition: ActionDefinition) -> tuple[InspectorField, ...]:
        ui_fields = definition.ui_config.get("fields") if isinstance(definition.ui_config, Mapping) else None
        if isinstance(ui_fields, (list, tuple)):
            return tuple(self._field_from_spec(item) for item in ui_fields if isinstance(item, Mapping))

        fields: list[InspectorField] = []
        for key, raw_spec in definition.parameters.items():
            spec = raw_spec if isinstance(raw_spec, Mapping) else {}
            fields.append(self._field_from_spec({"key": key, **spec}))
        return tuple(fields)

    @staticmethod
    def _field_from_spec(spec: Mapping[str, Any]) -> InspectorField:
        key = str(spec.get("key") or "")
        label = str(spec.get("label") or key.replace("_", " ").title())
        raw_type = str(spec.get("type") or FieldType.TEXT.value)
        try:
            field_type = FieldType(raw_type)
        except ValueError:
            field_type = FieldType.TEXT
        raw_options = spec.get("options") or ()
        options = tuple(str(option) for option in raw_options) if isinstance(raw_options, (list, tuple)) else ()
        raw_options_source = spec.get("options_source")
        options_source = str(raw_options_source) if raw_options_source else None
        return InspectorField(
            key=key,
            label=label,
            field_type=field_type,
            required=bool(spec.get("required", False)),
            default=spec.get("default"),
            options=options,
            options_source=options_source,
        )
