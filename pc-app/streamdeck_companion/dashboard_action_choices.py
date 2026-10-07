"""Project the V2 Action Library into choices consumable by the legacy dashboard.

This is a migration adapter only: the dashboard keeps its current HTML/JS while
its action menus stop owning a duplicate list of action types and labels.
"""

from __future__ import annotations

from typing import Any, Mapping


NONE_ACTION_ID = "none"
NONE_ACTION_NAME = "Aucune"


def action_choices(catalog: Mapping[str, Any], input_kind: str) -> tuple[dict[str, str], ...]:
    """Return id/label choices allowed for ``button`` or ``encoder`` inputs."""
    if input_kind not in {"button", "encoder"}:
        raise ValueError(f"unsupported input kind: {input_kind!r}")

    choices: list[dict[str, str]] = [{"id": NONE_ACTION_ID, "label": NONE_ACTION_NAME}]
    actions = catalog.get("actions") or ()
    for action in actions:
        if not isinstance(action, Mapping):
            continue
        inputs = tuple(str(value) for value in (action.get("inputs") or ()))
        if input_kind not in inputs:
            continue
        action_id = str(action.get("id") or "")
        name = str(action.get("name") or action_id)
        if action_id:
            choices.append({"id": action_id, "label": name})
    return tuple(choices)


def choice_ids(catalog: Mapping[str, Any], input_kind: str) -> tuple[str, ...]:
    return tuple(choice["id"] for choice in action_choices(catalog, input_kind))


def choice_labels(catalog: Mapping[str, Any]) -> dict[str, str]:
    """Return one label map for both dashboard input contexts."""
    labels = {NONE_ACTION_ID: NONE_ACTION_NAME}
    for input_kind in ("button", "encoder"):
        labels.update({choice["id"]: choice["label"] for choice in action_choices(catalog, input_kind)})
    return labels
