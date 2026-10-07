"""Thread-safe runtime orchestration for configured Multi Actions.

The Core MultiActionRunner remains responsible for sequencing. This adapter
keeps blocking delays and integration effects away from the ESPHome asyncio
loop while preserving the existing ActionEngine boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from .core.actions import ActionCommand, ActionDefinition
from .core.engine import ActionEngine
from .core.multi_action import (
    ActionStep,
    ConditionStep,
    MultiActionDefinition,
    MultiActionExecution,
    MultiActionRunner,
    MultiStep,
)
from .multi_actions_config import definition_by_id

ActionDispatcher = Callable[[ActionCommand], Any]
ConditionEvaluator = Callable[[Mapping[str, Any]], bool]
ConfigProvider = Callable[[], Mapping[str, Any]]


@dataclass(slots=True)
class MultiActionHandle:
    execution: MultiActionExecution
    future: Future[MultiActionExecution]

    def cancel(self) -> None:
        self.execution.cancel()


class MultiActionRuntime:
    """Execute configured Multi Actions on worker threads.

    The dispatcher owns concrete side effects. It may delegate local commands
    to the existing action runtime and Home Assistant/navigation commands to
    their current application adapters.
    """

    def __init__(
        self,
        config_provider: ConfigProvider,
        dispatcher: ActionDispatcher,
        *,
        conditions: Mapping[str, ConditionEvaluator] | None = None,
        max_workers: int = 1,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        self._config_provider = config_provider
        self._dispatcher = dispatcher
        self._conditions = dict(conditions or {})
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="streamdeck-multi-action")

    def register_condition(self, condition_id: str, evaluator: ConditionEvaluator) -> None:
        if not condition_id:
            raise ValueError("condition_id cannot be empty")
        self._conditions[condition_id] = evaluator

    def unregister_condition(self, condition_id: str) -> None:
        self._conditions.pop(condition_id, None)

    def submit(
        self,
        definition_id: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> MultiActionHandle:
        definition = definition_by_id(self._config_provider(), definition_id)
        execution = MultiActionExecution(definition.id)
        future = self._executor.submit(self._run, definition, dict(context or {}), execution)
        return MultiActionHandle(execution=execution, future=future)

    def run_sync(
        self,
        definition_id: str,
        *,
        context: Mapping[str, Any] | None = None,
        execution: MultiActionExecution | None = None,
    ) -> MultiActionExecution:
        definition = definition_by_id(self._config_provider(), definition_id)
        return self._run(definition, dict(context or {}), execution or MultiActionExecution(definition.id))

    def shutdown(self, *, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=False)

    def _run(
        self,
        definition: MultiActionDefinition,
        context: Mapping[str, Any],
        execution: MultiActionExecution,
    ) -> MultiActionExecution:
        engine = ActionEngine()
        for action_id in sorted(_action_ids(definition.steps)):
            engine.register(
                ActionDefinition(id=action_id, name=action_id, category="multi_action"),
                self._dispatcher,
            )
        runner = MultiActionRunner(engine)
        for condition_id, evaluator in self._conditions.items():
            runner.register_condition(condition_id, evaluator)
        return runner.run(definition, context=context, execution=execution)


def _action_ids(steps: tuple[MultiStep, ...]) -> set[str]:
    result: set[str] = set()
    for step in steps:
        if isinstance(step, ActionStep):
            result.add(step.command.action_id)
        elif isinstance(step, ConditionStep):
            result.update(_action_ids(step.if_true))
            result.update(_action_ids(step.if_false))
    return result
