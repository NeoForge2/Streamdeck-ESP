"""Declarative catalog for actions currently supported by the companion app."""

from __future__ import annotations

from .core.actions import ActionDefinition
from .core.registry import ActionRegistry
from .core.triggers import Trigger


BUTTON_TRIGGERS = frozenset(
    {Trigger.PRESS, Trigger.DOUBLE_PRESS, Trigger.HOLD, Trigger.LONG_PRESS, Trigger.RELEASE}
)
ENCODER_TRIGGERS = frozenset(
    {Trigger.ROTATE_CW, Trigger.ROTATE_CCW, Trigger.PRESS, Trigger.HOLD, Trigger.RELEASE}
)
ALL_TRIGGERS = BUTTON_TRIGGERS | ENCODER_TRIGGERS
BUTTON_INPUT = ("button",)
ENCODER_INPUT = ("encoder",)
ALL_INPUTS = ("button", "encoder")


def build_runtime_action_registry() -> ActionRegistry:
    registry = ActionRegistry()
    for definition in runtime_action_definitions():
        registry.register(definition)
    return registry


def runtime_action_definitions() -> tuple[ActionDefinition, ...]:
    return (
        _definition(
            "keys", "Raccourci clavier", "Windows", "hotkey", "Raccourci", ALL_TRIGGERS, inputs=ALL_INPUTS
        ),
        _definition(
            "launch", "Lancer une application", "Windows", "path", "Application", ALL_TRIGGERS, inputs=ALL_INPUTS
        ),
        _definition("url", "Ouvrir un site web", "Windows", "url", "URL", ALL_TRIGGERS, inputs=ALL_INPUTS),
        _definition(
            "media",
            "Musique / volume du PC",
            "Windows",
            "select",
            "Commande média",
            ALL_TRIGGERS,
            inputs=ALL_INPUTS,
            options_source="media_commands",
        ),
        _definition(
            "audio_output",
            "Changer de haut-parleur",
            "Windows",
            "select",
            "Sortie audio",
            ALL_TRIGGERS,
            inputs=ALL_INPUTS,
            options_source="audio_outputs",
        ),
        _definition(
            "app_volume",
            "Volume d'une application",
            "Windows",
            "select",
            "Application",
            ENCODER_TRIGGERS,
            inputs=ENCODER_INPUT,
            options_source="audio_apps",
        ),
        _definition(
            "app_mute",
            "Couper le son d'une application",
            "Windows",
            "select",
            "Application",
            ALL_TRIGGERS,
            inputs=ALL_INPUTS,
            options_source="audio_apps",
        ),
        _definition(
            "home_assistant",
            "Action Home Assistant",
            "Home Assistant",
            "home_assistant_service",
            "Service / entité",
            ALL_TRIGGERS,
            inputs=ALL_INPUTS,
        ),
        _definition(
            "ha_adjust",
            "Ajuster un appareil Home Assistant",
            "Home Assistant",
            "home_assistant_adjust",
            "Entité / pas",
            ENCODER_TRIGGERS,
            inputs=ENCODER_INPUT,
        ),
        _definition(
            "navigation",
            "Navigation Streamdeck",
            "Streamdeck",
            "navigation",
            "Commande / cible",
            ALL_TRIGGERS,
            inputs=ALL_INPUTS,
        ),
        _definition(
            "multi_action",
            "Multi Action",
            "Streamdeck",
            "multi_action",
            "Séquence",
            BUTTON_TRIGGERS,
            inputs=BUTTON_INPUT,
        ),
    )


def _definition(
    action_id: str,
    name: str,
    category: str,
    field_type: str,
    label: str,
    triggers: frozenset[Trigger],
    *,
    inputs: tuple[str, ...],
    options_source: str | None = None,
) -> ActionDefinition:
    parameter = {
        "type": field_type,
        "label": label,
        "required": True,
    }
    field = {
        "key": "target",
        "type": field_type,
        "label": label,
        "required": True,
    }
    if options_source:
        parameter["options_source"] = options_source
        field["options_source"] = options_source

    return ActionDefinition(
        id=action_id,
        name=name,
        category=category,
        parameters={"target": parameter},
        supported_triggers=triggers,
        ui_config={"fields": (field,), "inputs": inputs},
    )


# Canonical mutable metadata registry for the running companion app.
# PluginRegistry instances can receive this exact registry so newly loaded
# plugin actions become immediately discoverable by the dashboard catalog.
RUNTIME_ACTION_REGISTRY = build_runtime_action_registry()
