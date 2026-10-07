"""Composable Multi Actions executed through the existing ActionEngine."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from time import sleep
from typing import Any, TypeAlias

from .actions import ActionCommand
from .engine import ActionEngine


class MultiActionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class ErrorPolicy(str, Enum):
    STOP = "stop"
    CONTINUE = "continue"


@dataclass(frozen=True, slots=True)
class ActionStep:
    command: ActionCommand


@dataclass(frozen=True, slots=True)
class DelayStep:
    seconds: float

    def __post_init__(self) -> None:
        if self.seconds < 0:
            raise ValueError("delay cannot be negative")


@dataclass(frozen=True, slots=True)
class ConditionStep:
    condition_id: str
    if_true: tuple[MultiStep, ...] = ()
    if_false: tuple[MultiStep, ...] = ()

    def __post_init__(self) -> None:
        if not self.condition_id:
            raise ValueError("condition_id cannot be empty")


MultiStep: TypeAlias = ActionStep | DelayStep | ConditionStep
ConditionEvaluator = Callable[[Mapping[str, Any]], bool]
SleepFunction = Callable[[float], None]


@dataclass(frozen=True, slots=True)
class MultiActionDefinition:
    id: str
    name: str
    steps: tuple[MultiStep, ...]
    error_policy: ErrorPolicy = ErrorPolicy.STOP

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("multi action id cannot be empty")
        if not self.name:
            raise ValueError("multi action name cannot be empty")


@dataclass(slots=True)
class MultiActionExecution:
    definition_id: str
    status: MultiActionStatus = MultiActionStatus.IDLE
    completed_steps: int = 0
    errors: list[Exception] = field(default_factory=list)
    results: list[Any] = field(default_factory=list)
    cancel_requested: bool = False

    def cancel(self) -> None:
        self.cancel_requested = True
        if self.status == MultiActionStatus.IDLE:
            self.status = MultiActionStatus.CANCELLED


class UnknownConditionError(KeyError):
    pass


class MultiActionRunner:
    """Execute Action/Delay/Condition sequences without duplicating action effects."""

    def __init__(self, engine: ActionEngine, *, sleeper: SleepFunction = sleep) -> None:
        self.engine = engine
        self._sleeper = sleeper
        self._conditions: dict[str, ConditionEvaluator] = {}

    def register_condition(self, condition_id: str, evaluator: ConditionEvaluator) -> None:
        if not condition_id:
            raise ValueError("condition_id cannot be empty")
        self._conditions[condition_id] = evaluator

    def unregister_condition(self, condition_id: str) -> None:
        self._conditions.pop(condition_id, None)

    def run(
        self,
        definition: MultiActionDefinition,
        *,
        context: Mapping[str, Any] | None = None,
        execution: MultiActionExecution | None = None,
    ) -> MultiActionExecution:
        state = execution or MultiActionExecution(definition.id)
        if state.definition_id != definition.id:
            raise ValueError("execution belongs to another multi action")
        if state.cancel_requested:
            state.status = MultiActionStatus.CANCELLED
            return state

        state.status = MultiActionStatus.RUNNING
        self._run_steps(definition.steps, definition.error_policy, context or {}, state)
        if state.status == MultiActionStatus.CANCELLED:
            return state
        if state.errors and definition.error_policy == ErrorPolicy.STOP:
            state.status = MultiActionStatus.ERROR
        else:
            state.status = MultiActionStatus.COMPLETED
        return state

    def _run_steps(
        self,
        steps: Sequence[MultiStep],
        error_policy: ErrorPolicy,
        context: Mapping[str, Any],
        state: MultiActionExecution,
    ) -> None:
        for step in steps:
            if state.cancel_requested:
                state.status = MultiActionStatus.CANCELLED
                return
            try:
                self._run_step(step, error_policy, context, state)
                state.completed_steps += 1
            except Exception as exc:
                state.errors.append(exc)
                if error_policy == ErrorPolicy.STOP:
                    return

    def _run_step(
        self,
        step: MultiStep,
        error_policy: ErrorPolicy,
        context: Mapping[str, Any],
        state: MultiActionExecution,
    ) -> None:
        if isinstance(step, ActionStep):
            state.results.append(self.engine.execute(step.command))
            return
        if isinstance(step, DelayStep):
            self._sleeper(step.seconds)
            return
        evaluator = self._conditions.get(step.condition_id)
        if evaluator is None:
            raise UnknownConditionError(step.condition_id)
        branch = step.if_true if evaluator(context) else step.if_false
        self._run_steps(branch, error_policy, context, state)
