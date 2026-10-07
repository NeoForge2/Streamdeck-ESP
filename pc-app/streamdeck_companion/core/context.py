from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    process: str | None = None
    application: str | None = None
    window_title: str | None = None
    game: str | None = None
    attributes: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ContextRule:
    profile_id: str
    priority: int = 0
    process: str | None = None
    application: str | None = None
    window_title_contains: str | None = None
    game: str | None = None

    def __post_init__(self) -> None:
        if not self.profile_id:
            raise ValueError("profile_id cannot be empty")
        if not any((self.process, self.application, self.window_title_contains, self.game)):
            raise ValueError("context rule needs at least one matcher")

    def matches(self, context: ContextSnapshot) -> bool:
        if self.process and _norm(context.process) != _norm(self.process):
            return False
        if self.application and _norm(context.application) != _norm(self.application):
            return False
        if self.game and _norm(context.game) != _norm(self.game):
            return False
        if self.window_title_contains:
            title = _norm(context.window_title)
            if _norm(self.window_title_contains) not in title:
                return False
        return True


class ContextEngine:
    def __init__(self, default_profile_id: str, rules: tuple[ContextRule, ...] = ()) -> None:
        if not default_profile_id:
            raise ValueError("default_profile_id cannot be empty")
        self.default_profile_id = default_profile_id
        self.rules = rules
        self.manual_override: str | None = None
        self.manual_locked = False
        self._automatic_profile = default_profile_id
        self._previous_automatic_profile = default_profile_id

    @property
    def active_profile_id(self) -> str:
        return self.manual_override or self._automatic_profile

    @property
    def previous_automatic_profile_id(self) -> str:
        return self._previous_automatic_profile

    def resolve(self, context: ContextSnapshot) -> str:
        matches = [rule for rule in self.rules if rule.matches(context)]
        selected = max(matches, key=lambda rule: rule.priority).profile_id if matches else self.default_profile_id
        if selected != self._automatic_profile:
            self._previous_automatic_profile = self._automatic_profile
            self._automatic_profile = selected
        return self.active_profile_id

    def set_manual_override(self, profile_id: str, *, locked: bool = False) -> str:
        if not profile_id:
            raise ValueError("profile_id cannot be empty")
        self.manual_override = profile_id
        self.manual_locked = locked
        return self.active_profile_id

    def set_manual_lock(self, locked: bool) -> str:
        self.manual_locked = bool(locked) and self.manual_override is not None
        return self.active_profile_id

    def clear_manual_override(self, *, force: bool = False) -> str:
        if self.manual_locked and not force:
            return self.active_profile_id
        self.manual_override = None
        self.manual_locked = False
        return self._automatic_profile

    def restore_previous_automatic(self, *, force: bool = False) -> str:
        if self.manual_locked and not force:
            return self.active_profile_id
        self.manual_override = None
        self.manual_locked = False
        current = self._automatic_profile
        self._automatic_profile = self._previous_automatic_profile
        self._previous_automatic_profile = current
        return self._automatic_profile


def _norm(value: str | None) -> str:
    return (value or "").strip().casefold()
