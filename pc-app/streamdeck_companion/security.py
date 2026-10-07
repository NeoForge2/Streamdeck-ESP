"""Host-side security helpers. Secrets never belong in the Core or firmware."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from pathlib import PurePath
from typing import Protocol
from urllib.parse import urlparse


REDACTED = "***"
SENSITIVE_KEYS = frozenset({"token", "password", "secret", "api_key", "access_token", "refresh_token"})


class SecretStore(Protocol):
    def get(self, key: str) -> str | None: ...


class EnvironmentSecretStore:
    """Read secrets from process environment without persisting plaintext."""

    def __init__(self, *, prefix: str = "STREAMDECK_") -> None:
        self.prefix = prefix

    def get(self, key: str) -> str | None:
        if not key:
            raise ValueError("secret key cannot be empty")
        env_key = self.prefix + key.upper().replace(".", "_").replace("-", "_")
        return os.getenv(env_key)


class CompositeSecretStore:
    """Resolve secrets through ordered host-side backends."""

    def __init__(self, stores: Sequence[SecretStore]) -> None:
        self.stores = tuple(stores)

    def get(self, key: str) -> str | None:
        for store in self.stores:
            value = store.get(key)
            if value:
                return value
        return None


@dataclass(frozen=True, slots=True)
class NetworkPolicy:
    """Explicit outbound policy for integrations/plugins.

    By default only loopback/private/link-local destinations are accepted.
    Public hosts must be explicitly allow-listed. This is a policy check for
    runtime adapters; it does not pretend to be an OS sandbox/firewall.
    """

    allow_public_hosts: frozenset[str] = frozenset()
    allow_private: bool = True

    def validate_url(self, raw_url: str) -> str:
        parsed = urlparse(raw_url)
        if parsed.scheme not in {"http", "https", "ws", "wss"} or not parsed.hostname:
            raise ValueError("network URL must use http(s) or ws(s) with a host")
        host = parsed.hostname.casefold()
        if host in {item.casefold() for item in self.allow_public_hosts}:
            return raw_url
        try:
            address = ip_address(host)
        except ValueError:
            # DNS names are public/unknown unless explicitly allow-listed.
            if host in {"localhost"} and self.allow_private:
                return raw_url
            raise PermissionError(f"network host is not allow-listed: {host}")
        if self.allow_private and (address.is_private or address.is_loopback or address.is_link_local):
            return raw_url
        raise PermissionError(f"network address is not allowed: {host}")

    def allows_address(self, address: str, *, networks: Sequence[str] = ()) -> bool:
        candidate = ip_address(address)
        if self.allow_private and (candidate.is_private or candidate.is_loopback or candidate.is_link_local):
            return True
        return any(candidate in ip_network(network, strict=False) for network in networks)


@dataclass(frozen=True, slots=True)
class PluginModulePolicy:
    """Restrict plugin imports to approved Python package namespaces."""

    allowed_prefixes: tuple[str, ...] = ("streamdeck_companion.example_plugins",)

    def validate(self, module_name: str) -> str:
        if not module_name or module_name.startswith("."):
            raise PermissionError("plugin module name must be absolute")
        if any(part in {"", ".", ".."} for part in PurePath(module_name.replace(".", "/")).parts):
            raise PermissionError("invalid plugin module path")
        if not any(module_name == prefix or module_name.startswith(prefix + ".") for prefix in self.allowed_prefixes):
            raise PermissionError(f"plugin module is outside approved namespaces: {module_name}")
        return module_name


def redact_mapping(values: Mapping[str, object]) -> dict[str, object]:
    """Return a logging-safe copy with common secret fields recursively redacted."""

    result: dict[str, object] = {}
    for key, value in values.items():
        normalized = key.casefold()
        if normalized in SENSITIVE_KEYS or normalized.endswith("_token") or normalized.endswith("_password"):
            result[key] = REDACTED
        elif isinstance(value, Mapping):
            result[key] = redact_mapping(value)
        elif isinstance(value, list):
            result[key] = [redact_mapping(item) if isinstance(item, Mapping) else item for item in value]
        else:
            result[key] = value
    return result


def require_secret(store: SecretStore, key: str) -> str:
    value = store.get(key)
    if not value:
        raise RuntimeError(f"required secret is not configured: {key}")
    return value
