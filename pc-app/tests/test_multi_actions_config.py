from __future__ import annotations

import unittest

from streamdeck_companion.core.multi_action import ActionStep, ConditionStep, DelayStep, ErrorPolicy
from streamdeck_companion.multi_actions_config import (
    MultiActionConfigError,
    definition_by_id,
    definitions_from_config,
    new_multi_action,
)


class MultiActionConfigTests(unittest.TestCase):
    def test_parses_action_delay_and_condition_branches(self) -> None:
        config = {
            "multi_actions": [
                {
                    "id": "cinema",
                    "name": "Mode cinéma",
                    "error_policy": "continue",
                    "steps": [
                        {"type": "action", "action": {"type": "media", "target": "mute"}},
                        {"type": "delay", "milliseconds": 500},
                        {
                            "type": "condition",
                            "condition_id": "tv_available",
                            "if_true": [
                                {"type": "action", "action": {"type": "url", "target": "https://example.test"}}
                            ],
                            "if_false": [],
                        },
                    ],
                }
            ]
        }
        definition = definition_by_id(config, "cinema")
        self.assertEqual(definition.error_policy, ErrorPolicy.CONTINUE)
        self.assertIsInstance(definition.steps[0], ActionStep)
        self.assertIsInstance(definition.steps[1], DelayStep)
        self.assertEqual(definition.steps[1].seconds, 0.5)
        self.assertIsInstance(definition.steps[2], ConditionStep)
        self.assertEqual(definition.steps[2].if_true[0].command.action_id, "url")

    def test_duplicate_ids_are_rejected(self) -> None:
        config = {
            "multi_actions": [
                {"id": "same", "steps": []},
                {"id": "same", "steps": []},
            ]
        }
        with self.assertRaises(MultiActionConfigError):
            definitions_from_config(config)

    def test_new_multi_action_uses_backward_compatible_mapping(self) -> None:
        raw = new_multi_action("Morning", definition_id="morning")
        self.assertEqual(raw["id"], "morning")
        self.assertEqual(raw["steps"], [])
        self.assertEqual(raw["error_policy"], "stop")

    def test_invalid_step_type_is_rejected(self) -> None:
        with self.assertRaises(MultiActionConfigError):
            definitions_from_config({"multi_actions": [{"id": "x", "steps": [{"type": "unknown"}]}]})


if __name__ == "__main__":
    unittest.main()
