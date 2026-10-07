from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ThemeDefinition:
    id: str
    name: str
    tokens: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("theme id cannot be empty")
        if not self.name:
            raise ValueError("theme name cannot be empty")


class AnimationKind(str, Enum):
    FADE = "fade"
    SCALE = "scale"
    SLIDE = "slide"
    PULSE = "pulse"
    SPIN = "spin"


@dataclass(frozen=True, slots=True)
class AnimationDefinition:
    kind: AnimationKind
    duration_ms: int = 180
    easing: str = "ease-out"
    repeat: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.duration_ms < 0:
            raise ValueError("animation duration cannot be negative")
        if self.repeat < 0:
            raise ValueError("animation repeat cannot be negative")


class ThemeRegistry:
    def __init__(self) -> None:
        self._themes: dict[str, ThemeDefinition] = {}

    def register(self, theme: ThemeDefinition) -> None:
        if theme.id in self._themes:
            raise ValueError(f"theme already registered: {theme.id!r}")
        self._themes[theme.id] = theme

    def get(self, theme_id: str) -> ThemeDefinition:
        try:
            return self._themes[theme_id]
        except KeyError as exc:
            raise KeyError(f"unknown theme: {theme_id!r}") from exc

    def list(self) -> tuple[ThemeDefinition, ...]:
        return tuple(self._themes.values())
