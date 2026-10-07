# Streamdeck-ESP V2 Plugin SDK

The V2 plugin boundary lets integrations add behavior without modifying the Core.

## Core contract

A plugin declares a `PluginManifest` and a `PluginContribution` from `streamdeck_companion.core.plugins`.

The manifest contains a stable plugin id, human-readable name, plugin version, Plugin API version and requested permissions. The current Plugin API version is `1`.

A contribution may provide:

- action definitions and their executors;
- widget definitions;
- state providers;
- event ids;
- declarative settings;
- asset references.

Plugin actions execute through the same shared `ActionEngine` as built-in actions. Providers feed the same `StateStore` used by controls and widgets.

## Permissions

Plugins request only the capabilities they need. Initial permissions are:

- `network`
- `filesystem`
- `process`
- `home_assistant`
- `audio`

`PluginRegistry` refuses registration when requested permissions have not been granted. This is the first security boundary; process isolation and a loader sandbox remain separate runtime concerns.

## Registration

Create the application registries once and give them to the Plugin Registry:

```python
from streamdeck_companion.core.engine import ActionEngine
from streamdeck_companion.core.plugins import PluginRegistry
from streamdeck_companion.core.providers import ProviderManager
from streamdeck_companion.core.registry import ActionRegistry
from streamdeck_companion.core.state import StateStore

actions = ActionRegistry()
engine = ActionEngine(actions)
store = StateStore()
providers = ProviderManager(store)
plugins = PluginRegistry(actions, engine=engine, providers=providers)
```

Register a plugin with:

```python
plugins.register(manifest, contribution)
```

Registration is transactional. If an action, provider, widget or event collides or fails, contributions already added by that registration are rolled back.

## Action definitions and Property Inspector

Actions use `ActionDefinition.parameters` for their generic configuration schema. A plugin may provide `ui_config["fields"]` when it needs an explicit Property Inspector representation.

The application can consume this through `PropertyInspector` and expose the same fields without plugin-specific forms in the dashboard.

## State and widgets

Providers never render widgets directly. The expected data flow is:

```text
Plugin/provider -> StateValue -> StateStore -> WidgetResolver -> renderer
```

This keeps Home Assistant, OBS, system metrics and future integrations out of widget/rendering code.

## Reference plugins

The package `streamdeck_companion.example_plugins` contains three examples:

- `system_plugin.py`: launch application and hotkey actions;
- `home_assistant_plugin.py`: service action, state provider and status widget;
- `obs_plugin.py`: scene/recording actions and recording status widget.

All external effects are dependency-injected callables. The examples therefore demonstrate the SDK contract without adding third-party dependencies to the Core.

## Compatibility rules

A plugin must not import or patch internal Core implementation details. It should use public models/registries only, namespace its action/widget/event ids, request minimal permissions and keep secrets in settings/runtime storage rather than assets or firmware.

The Plugin API version is validated at registration time. A future incompatible SDK will increment the API version and should provide an explicit migration path.
