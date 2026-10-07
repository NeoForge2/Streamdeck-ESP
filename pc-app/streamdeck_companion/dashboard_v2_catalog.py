"""Serializable V2 action catalog for the existing Flask dashboard."""

from __future__ import annotations

from typing import Any

from .core.action_library import ActionLibrary
from .core.property_inspector import PropertyInspector
from .core.registry import ActionRegistry
from .runtime_action_catalog import RUNTIME_ACTION_REGISTRY


def build_dashboard_action_catalog(registry: ActionRegistry | None = None) -> dict[str, Any]:
    """Return Action Library + Property Inspector metadata for the current UI.

    By default the live shared runtime registry is used. Plugins registering
    actions into that same registry therefore become visible without changing
    this module or rebuilding a second catalog.
    """
    action_registry = registry or RUNTIME_ACTION_REGISTRY
    library = ActionLibrary(action_registry)
    inspector = PropertyInspector(action_registry)

    actions = []
    for definition in action_registry.list():
        schema = inspector.schema(definition.id)
        raw_inputs = definition.ui_config.get("inputs", ())
        inputs = tuple(str(value) for value in raw_inputs) if isinstance(raw_inputs, (list, tuple)) else ()
        actions.append(
            {
                "id": definition.id,
                "name": definition.name,
                "category": definition.category,
                "description": definition.description,
                "triggers": tuple(sorted(trigger.value for trigger in definition.supported_triggers)),
                "inputs": inputs,
                "fields": tuple(
                    {
                        "key": field.key,
                        "label": field.label,
                        "type": field.field_type.value,
                        "required": field.required,
                        "default": field.default,
                        "options": field.options,
                        "options_source": field.options_source,
                    }
                    for field in schema.fields
                ),
            }
        )

    return {
        "categories": library.categories(),
        "actions": tuple(actions),
    }
