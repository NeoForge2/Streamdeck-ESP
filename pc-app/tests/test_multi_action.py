from __future__ import annotations

import unittest

from streamdeck_companion.core.actions import ActionCommand, ActionDefinition
from streamdeck_companion.core.engine import ActionEngine
from streamdeck_companion.core.multi_action import (
    ActionStep,
    ConditionStep,
    DelayStep,
    ErrorPolicy,
    MultiActionDefinition,
    MultiActionExecution,
    MultiActionRunner,
    MultiActionStatus,
    UnknownConditionError,
)


class MultiActionTests(unittest.TestCase):
    def _engine(self, calls: list[str]) -> ActionEngine:
        engine = ActionEngine()
        engine.register(
            ActionDefinition(id="record", name="Record"),
            lambda command: calls.append(str(command.parameters.get("value"))) or command.parameters.get("value"),
        )
        return engine

    def test_runs_action_delay_and_true_branch_in_order(self) -> None:
        calls: list[str] = []
        delays: list[float] = []
        runner = MultiActionRunner(self._engine(calls), sleeper=delays.append)
        runner.register_condition("enabled", lambda context: bool(context.get("enabled")))
        definition = MultiActionDefinition(
            id="cinema",
            name="Cinema",
            steps=(
                ActionStep(ActionCommand("record", {"value": "lights_off"})),
                DelayStep(0.5),
                ConditionStep(
                    "enabled",
                    if_true=(ActionStep(ActionCommand("record", {"value": "tv_on"})),),
                    if_false=(ActionStep(ActionCommand("record", {"value": "skip"})),),
                ),
            ),
        )

        execution = runner.run(definition, context={"enabled": True})

        self.assertEqual(calls, ["lights_off", "tv_on"])
        self.assertEqual(delays, [0.5])
        self.assertEqual(execution.status, MultiActionStatus.COMPLETED)
        self.assertEqual(execution.completed_steps, 4)
        self.assertEqual(execution.results, ["lights_off", "tv_on"])

    def test_false_branch_is_selected(self) -> None:
        calls: list[str] = []
        runner = MultiActionRunner(self._engine(calls), sleeper=lambda _: None)
        runner.register_condition("enabled", lambda context: bool(context.get("enabled")))
        definition = MultiActionDefinition(
            id="branch",
            name="Branch",
            steps=(
                ConditionStep(
                    "enabled",
                    if_true=(ActionStep(ActionCommand("record", {"value": "yes"})),),
                    if_false=(ActionStep(ActionCommand("record", {"value": "no"})),),
                ),
            ),
        )

        runner.run(definition, context={"enabled": False})
        self.assertEqual(calls, ["no"])

    def test_stop_policy_marks_error(self) -> None:
        runner = MultiActionRunner(ActionEngine(), sleeper=lambda _: None)
        definition = MultiActionDefinition(
            id="broken",
            name="Broken",
            steps=(ActionStep(ActionCommand("missing")), DelayStep(1)),
        )
        execution = runner.run(definition)
        self.assertEqual(execution.status, MultiActionStatus.ERROR)
        self.assertEqual(len(execution.errors), 1)
        self.assertEqual(execution.completed_steps, 0)

    def test_continue_policy_keeps_running(self) -> None:
        calls: list[str] = []
        runner = MultiActionRunner(self._engine(calls), sleeper=lambda _: None)
        definition = MultiActionDefinition(
            id="continue",
            name="Continue",
            error_policy=ErrorPolicy.CONTINUE,
            steps=(
                ActionStep(ActionCommand("missing")),
                ActionStep(ActionCommand("record", {"value": "after"})),
            ),
        )
        execution = runner.run(definition)
        self.assertEqual(execution.status, MultiActionStatus.COMPLETED)
        self.assertEqual(calls, ["after"])
        self.assertEqual(len(execution.errors), 1)

    def test_pre_cancelled_execution_never_runs(self) -> None:
        calls: list[str] = []
        runner = MultiActionRunner(self._engine(calls), sleeper=lambda _: None)
        definition = MultiActionDefinition(
            id="cancel",
            name="Cancel",
            steps=(ActionStep(ActionCommand("record", {"value": "never"})),),
        )
        execution = MultiActionExecution("cancel")
        execution.cancel()
        runner.run(definition, execution=execution)
        self.assertEqual(execution.status, MultiActionStatus.CANCELLED)
        self.assertEqual(calls, [])

    def test_unknown_condition_is_reported(self) -> None:
        runner = MultiActionRunner(ActionEngine(), sleeper=lambda _: None)
        definition = MultiActionDefinition(
            id="condition",
            name="Condition",
            steps=(ConditionStep("missing"),),
        )
        execution = runner.run(definition)
        self.assertEqual(execution.status, MultiActionStatus.ERROR)
        self.assertIsInstance(execution.errors[0], UnknownConditionError)


if __name__ == "__main__":
    unittest.main()
