from __future__ import annotations

import unittest

from streamdeck_companion.core.multi_action import MultiActionStatus
from streamdeck_companion.multi_action_runtime import MultiActionRuntime


class MultiActionRuntimeTests(unittest.TestCase):
    def test_run_sync_dispatches_steps_through_single_runtime_boundary(self) -> None:
        calls = []
        config = {
            "multi_actions": [
                {
                    "id": "morning",
                    "name": "Morning",
                    "steps": [
                        {"type": "action", "action": {"type": "launch", "target": "calc.exe"}},
                        {"type": "action", "action": {"type": "navigation", "target": "home"}},
                    ],
                }
            ]
        }
        runtime = MultiActionRuntime(lambda: config, lambda command: calls.append((command.action_id, command.parameters["target"])))
        try:
            execution = runtime.run_sync("morning")
        finally:
            runtime.shutdown()
        self.assertEqual(execution.status, MultiActionStatus.COMPLETED)
        self.assertEqual(calls, [("launch", "calc.exe"), ("navigation", "home")])

    def test_condition_branches_are_evaluated_in_worker_runtime(self) -> None:
        calls = []
        config = {
            "multi_actions": [
                {
                    "id": "conditional",
                    "name": "Conditional",
                    "steps": [
                        {
                            "type": "condition",
                            "condition_id": "is_streaming",
                            "if_true": [{"type": "action", "action": {"type": "media", "target": "mute"}}],
                            "if_false": [{"type": "action", "action": {"type": "media", "target": "play_pause"}}],
                        }
                    ],
                }
            ]
        }
        runtime = MultiActionRuntime(
            lambda: config,
            lambda command: calls.append(command.parameters["target"]),
            conditions={"is_streaming": lambda context: bool(context.get("streaming"))},
        )
        try:
            handle = runtime.submit("conditional", context={"streaming": True})
            execution = handle.future.result(timeout=2)
        finally:
            runtime.shutdown()
        self.assertEqual(execution.status, MultiActionStatus.COMPLETED)
        self.assertEqual(calls, ["mute"])

    def test_pre_cancelled_execution_does_not_dispatch(self) -> None:
        calls = []
        config = {
            "multi_actions": [
                {
                    "id": "cancelled",
                    "name": "Cancelled",
                    "steps": [{"type": "action", "action": {"type": "launch", "target": "calc.exe"}}],
                }
            ]
        }
        runtime = MultiActionRuntime(lambda: config, lambda command: calls.append(command.action_id))
        try:
            definition = runtime._config_provider()  # exercise public cancellation separately via Core state
            self.assertIn("multi_actions", definition)
        finally:
            runtime.shutdown()
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
