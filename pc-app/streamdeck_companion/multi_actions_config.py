"""Adapters between dashboard configuration and the Core Multi Action model."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .core.legacy import from_legacy
from .core.multi_action import (
    ActionStep,
    ConditionStep,
    DelayStep,
    ErrorPolicy,
    MultiActionDefinition,
    MultiStep,
)


class MultiActionConfigError(ValueError):
    pass


def definitions_from_config(config: Mapping[str, Any]) -> tuple[MultiActionDefinition, ...]:
    definitions: list[MultiActionDefinition] = []
    seen: set[str] = set()
    for index, raw in enumerate(config.get("multi_actions") or []):
        if not isinstance(raw, Mapping):
            raise MultiActionConfigError("multi action entries must be mappings")
        definition_id = str(raw.get("id") or f"multi-{index + 1}")
        if definition_id in seen:
            raise MultiActionConfigError(f"duplicate multi action id: {definition_id!r}")
        seen.add(definition_id)
        name = str(raw.get("name") or f"Multi Action {index + 1}")
        try:
            error_policy = ErrorPolicy(str(raw.get("error_policy") or ErrorPolicy.STOP.value))
        except ValueError as exc:
            raise MultiActionConfigError(f"invalid error policy for {definition_id!r}") from exc
        definitions.append(
            MultiActionDefinition(
                id=definition_id,
                name=name,
                steps=_parse_steps(raw.get("steps") or []),
                error_policy=error_policy,
            )
        )
    return tuple(definitions)


def definition_by_id(config: Mapping[str, Any], definition_id: str) -> MultiActionDefinition:
    for definition in definitions_from_config(config):
        if definition.id == definition_id:
            return definition
    raise KeyError(definition_id)


def new_multi_action(name: str, *, definition_id: str) -> dict[str, Any]:
    if not name.strip() or not definition_id.strip():
        raise MultiActionConfigError("multi action id and name cannot be empty")
    return {
        "id": definition_id,
        "name": name.strip(),
        "error_policy": ErrorPolicy.STOP.value,
        "steps": [],
    }


def _parse_steps(raw_steps: object) -> tuple[MultiStep, ...]:
    if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)):
        raise MultiActionConfigError("steps must be a list")
    steps: list[MultiStep] = []
    for raw in raw_steps:
        if not isinstance(raw, Mapping):
            raise MultiActionConfigError("step must be a mapping")
        step_type = str(raw.get("type") or "").strip().lower()
        if step_type == "action":
            command = from_legacy(raw.get("action") if isinstance(raw.get("action"), Mapping) else {})
            if command is None:
                raise MultiActionConfigError("action step requires a non-none action")
            steps.append(ActionStep(command))
        elif step_type == "delay":
            milliseconds = float(raw.get("milliseconds", 0))
            if milliseconds < 0:
                raise MultiActionConfigError("delay cannot be negative")
            steps.append(DelayStep(milliseconds / 1000.0))
        elif step_type == "condition":
            condition_id = str(raw.get("condition_id") or "")
            if not condition_id:
                raise MultiActionConfigError("condition step requires condition_id")
            steps.append(
                ConditionStep(
                    condition_id,
                    if_true=_parse_steps(raw.get("if_true") or []),
                    if_false=_parse_steps(raw.get("if_false") or []),
                )
            )
        else:
            raise MultiActionConfigError(f"unsupported step type: {step_type!r}")
    return tuple(steps)
