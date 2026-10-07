from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from .state import StateStore, StateValue
from .triggers import ActionState


class StateProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    def refresh(self) -> Iterable[StateValue]: ...


@dataclass(frozen=True, slots=True)
class ProviderRefreshResult:
    provider_id: str
    values: tuple[StateValue, ...] = ()
    error: Exception | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class ProviderManager:
    def __init__(self, store: StateStore) -> None:
        self.store = store
        self._providers: dict[str, StateProvider] = {}

    def register(self, provider: StateProvider) -> None:
        if not provider.provider_id:
            raise ValueError("provider_id cannot be empty")
        if provider.provider_id in self._providers:
            raise ValueError(f"provider already registered: {provider.provider_id!r}")
        self._providers[provider.provider_id] = provider

    def unregister(self, provider_id: str) -> None:
        self._providers.pop(provider_id, None)

    def refresh(self, provider_id: str | None = None) -> tuple[StateValue, ...]:
        providers = self._select(provider_id)
        values: list[StateValue] = []
        for provider in providers:
            for state in provider.refresh():
                self.store.set(state)
                values.append(state)
        return tuple(values)

    def refresh_safe(self, provider_id: str | None = None) -> tuple[ProviderRefreshResult, ...]:
        """Refresh providers independently while preserving last known states.

        A failed provider publishes only its own health state as ERROR. Existing
        target states remain untouched so controls/widgets can keep displaying
        their last known values while the runtime reconnects.
        """
        providers = self._select(provider_id)
        results: list[ProviderRefreshResult] = []
        for provider in providers:
            try:
                values = tuple(provider.refresh())
                for state in values:
                    self.store.set(state)
                self.store.update(
                    f"provider:{provider.provider_id}",
                    status=ActionState.ACTIVE,
                    value=True,
                    attributes={"error": ""},
                )
                results.append(ProviderRefreshResult(provider.provider_id, values))
            except Exception as exc:
                self.store.update(
                    f"provider:{provider.provider_id}",
                    status=ActionState.ERROR,
                    value=False,
                    attributes={"error": type(exc).__name__},
                )
                results.append(ProviderRefreshResult(provider.provider_id, error=exc))
        return tuple(results)

    def list(self) -> tuple[StateProvider, ...]:
        return tuple(self._providers.values())

    def _select(self, provider_id: str | None) -> tuple[StateProvider, ...]:
        if provider_id is None:
            return tuple(self._providers.values())
        provider = self._providers.get(provider_id)
        if provider is None:
            raise KeyError(provider_id)
        return (provider,)
