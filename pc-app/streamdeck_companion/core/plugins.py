from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from .actions import ActionDefinition
from .engine import ActionEngine, ActionExecutor
from .providers import ProviderManager, StateProvider
from .registry import ActionRegistry
from .widgets import WidgetDefinition

PLUGIN_API_VERSION = 1


class PluginPermission(str, Enum):
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    PROCESS = "process"
    HOME_ASSISTANT = "home_assistant"
    AUDIO = "audio"


@dataclass(frozen=True, slots=True)
class PluginManifest:
    id: str
    name: str
    version: str
    api_version: int = PLUGIN_API_VERSION
    permissions: frozenset[PluginPermission] = field(default_factory=frozenset)
    description: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("plugin id cannot be empty")
        if not self.name:
            raise ValueError("plugin name cannot be empty")
        if not self.version:
            raise ValueError("plugin version cannot be empty")
        if self.api_version != PLUGIN_API_VERSION:
            raise ValueError(f"unsupported plugin API version: {self.api_version}")


@dataclass(frozen=True, slots=True)
class PluginContribution:
    actions: tuple[ActionDefinition, ...] = ()
    action_executors: Mapping[str, ActionExecutor] = field(default_factory=dict, compare=False, repr=False)
    widgets: tuple[WidgetDefinition, ...] = ()
    providers: tuple[StateProvider, ...] = ()
    events: tuple[str, ...] = ()
    settings: Mapping[str, Any] = field(default_factory=dict)
    assets: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RegisteredPlugin:
    manifest: PluginManifest
    contribution: PluginContribution


class PluginRegistrationError(ValueError):
    pass


class PluginRegistry:
    """Registers plugin contributions into existing generic Core registries."""

    def __init__(
        self,
        actions: ActionRegistry,
        *,
        engine: ActionEngine | None = None,
        providers: ProviderManager | None = None,
        granted_permissions: frozenset[PluginPermission] = frozenset(),
    ) -> None:
        if engine is not None and engine.registry is not actions:
            raise ValueError("plugin ActionEngine must use the same ActionRegistry")
        self.actions = actions
        self.engine = engine
        self.providers = providers
        self.granted_permissions = granted_permissions
        self._plugins: dict[str, RegisteredPlugin] = {}
        self._widgets: dict[str, tuple[str, WidgetDefinition]] = {}
        self._events: dict[str, str] = {}

    def register(self, manifest: PluginManifest, contribution: PluginContribution) -> RegisteredPlugin:
        if manifest.id in self._plugins:
            raise PluginRegistrationError(f"plugin already registered: {manifest.id!r}")
        missing = manifest.permissions - self.granted_permissions
        if missing:
            names = ", ".join(sorted(permission.value for permission in missing))
            raise PluginRegistrationError(f"plugin permissions not granted: {names}")

        action_ids = [action.id for action in contribution.actions]
        widget_ids = [widget.id for widget in contribution.widgets]
        if len(action_ids) != len(set(action_ids)):
            raise PluginRegistrationError("plugin contains duplicate action ids")
        if len(widget_ids) != len(set(widget_ids)):
            raise PluginRegistrationError("plugin contains duplicate widget ids")
        unknown_executors = set(contribution.action_executors) - set(action_ids)
        if unknown_executors:
            raise PluginRegistrationError("plugin provides executors for unknown actions")
        if contribution.action_executors and self.engine is None:
            raise PluginRegistrationError("plugin action executors require an ActionEngine")
        if any(widget_id in self._widgets for widget_id in widget_ids):
            raise PluginRegistrationError("widget id already registered")
        if any(event in self._events for event in contribution.events):
            raise PluginRegistrationError("event id already registered")

        registered_actions: list[str] = []
        registered_providers: list[str] = []
        try:
            for action in contribution.actions:
                executor = contribution.action_executors.get(action.id)
                if executor is not None and self.engine is not None:
                    self.engine.register(action, executor)
                else:
                    self.actions.register(action)
                registered_actions.append(action.id)
            if contribution.providers and self.providers is None:
                raise PluginRegistrationError("plugin provides state providers but no ProviderManager is configured")
            if self.providers is not None:
                for provider in contribution.providers:
                    self.providers.register(provider)
                    registered_providers.append(provider.provider_id)
            for widget in contribution.widgets:
                self._widgets[widget.id] = (manifest.id, widget)
            for event in contribution.events:
                if not event:
                    raise PluginRegistrationError("event id cannot be empty")
                self._events[event] = manifest.id
        except Exception:
            for action_id in registered_actions:
                if self.engine is not None and action_id in contribution.action_executors:
                    self.engine.unregister(action_id)
                else:
                    self.actions.unregister(action_id)
            if self.providers is not None:
                for provider_id in registered_providers:
                    self.providers.unregister(provider_id)
            for widget_id in widget_ids:
                self._widgets.pop(widget_id, None)
            for event in contribution.events:
                self._events.pop(event, None)
            raise

        plugin = RegisteredPlugin(manifest, contribution)
        self._plugins[manifest.id] = plugin
        return plugin

    def unregister(self, plugin_id: str) -> None:
        plugin = self._plugins.pop(plugin_id, None)
        if plugin is None:
            return
        for action in plugin.contribution.actions:
            if self.engine is not None and action.id in plugin.contribution.action_executors:
                self.engine.unregister(action.id)
            else:
                self.actions.unregister(action.id)
        if self.providers is not None:
            for provider in plugin.contribution.providers:
                self.providers.unregister(provider.provider_id)
        for widget in plugin.contribution.widgets:
            self._widgets.pop(widget.id, None)
        for event in plugin.contribution.events:
            self._events.pop(event, None)

    def get(self, plugin_id: str) -> RegisteredPlugin | None:
        return self._plugins.get(plugin_id)

    def list(self) -> tuple[RegisteredPlugin, ...]:
        return tuple(self._plugins.values())

    def widgets(self, plugin_id: str | None = None) -> tuple[WidgetDefinition, ...]:
        return tuple(
            widget
            for owner, widget in self._widgets.values()
            if plugin_id is None or owner == plugin_id
        )

    def event_owner(self, event_id: str) -> str | None:
        return self._events.get(event_id)
