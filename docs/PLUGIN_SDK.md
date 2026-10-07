# Streamdeck-ESP Plugin SDK

The V2 plugin API lets integrations add actions, widgets, state providers, events, settings and assets without changing `streamdeck_companion.core`.

## API version

Current API: `PLUGIN_API_VERSION = 1`.

A plugin declares a `PluginManifest` with a stable ID, name, plugin version, API version and the permissions it requires. Registration fails when the API version is unsupported or a requested permission has not been granted.

## Permissions

Available permissions are currently:

- `network`
- `filesystem`
- `process`
- `home_assistant`
- `audio`

Permissions are capabilities granted by the host. Plugins must not assume a permission that is not declared in their manifest.

## Contributions

A `PluginContribution` can provide:

- `actions`: `ActionDefinition` instances;
- `action_executors`: runtime executors for those actions;
- `widgets`: `WidgetDefinition` instances;
- `providers`: `StateProvider` implementations that publish into the shared `StateStore`;
- `events`: plugin-owned event IDs;
- `settings`: declarative settings metadata;
- `assets`: logical asset names/paths.

`PluginRegistry` wires these contributions into the existing `ActionRegistry`, `ActionEngine` and `ProviderManager`. Registration is transactional: if one contribution fails, previously registered pieces from that plugin are rolled back.

## Minimal example

```python
from streamdeck_companion.core.actions import ActionDefinition
from streamdeck_companion.core.plugins import PluginContribution, PluginManifest

manifest = PluginManifest(id="example", name="Example", version="1.0.0")
contribution = PluginContribution(
    actions=(ActionDefinition(id="example.hello", name="Hello", category="Plugins"),),
    settings={"name": {"type": "text", "default": "World"}},
)
```

The host registers it with `PluginRegistry.register(manifest, contribution)`. No Core source file needs modification.

## Action executors

Action metadata belongs to the Core-facing contribution; side effects stay outside the Core. Executors are injected into the shared `ActionEngine`.

A plugin must only provide executors for actions it declares. The registry rejects unknown executor IDs.

## State providers and widgets

Providers publish `StateValue` objects into `StateStore`. Widgets only reference `state_key` and consume snapshots from that store.

Required dependency direction:

`Integration / Provider -> StateStore -> Widget / Control -> Renderer`

A widget must never perform Home Assistant, HTTP, MQTT or OS communication directly.

## Events

Plugins may register event IDs for integration-specific events. Event IDs are owned by one plugin and collisions are rejected.

## Lifecycle

1. Host loads plugin metadata.
2. Host checks API version and requested permissions.
3. Host creates the plugin contribution.
4. `PluginRegistry.register()` atomically attaches contributions.
5. Runtime uses the shared generic registries.
6. `PluginRegistry.unregister()` removes all contributions owned by that plugin.

## Compatibility rules

- Core must not import individual plugins.
- Plugins must not depend on Flask, ESPHome or the current hardware unless the plugin is explicitly a runtime adapter for one of those systems.
- Public IDs should be stable across plugin updates.
- Breaking plugin API changes require a new `PLUGIN_API_VERSION`.
- Secrets belong in host-side configuration; they must not be embedded in firmware or committed to the repository.

Reference implementations live in `pc-app/streamdeck_companion/example_plugins/`:

- `system_plugin.py` — system actions with injected launch/hotkey executors;
- `home_assistant_plugin.py` — Home Assistant actions plus a state provider;
- `obs_plugin.py` — OBS actions with injected runtime callbacks.

`pc-app/tests/test_example_plugins.py` registers all three in the same `PluginRegistry`, executes representative actions through the shared `ActionEngine`, and refreshes the Home Assistant provider. This is the regression proof that integrations can be added without editing the Core.