from __future__ import annotations

import unittest
from types import ModuleType

from streamdeck_companion.core.actions import ActionDefinition
from streamdeck_companion.core.plugins import PluginContribution, PluginManifest, PluginRegistry
from streamdeck_companion.core.registry import ActionRegistry
from streamdeck_companion.plugin_loader import PluginLoadError, PluginLoader
from streamdeck_companion.security import PluginModulePolicy


class PluginLoaderTests(unittest.TestCase):
    def _module(self) -> ModuleType:
        module = ModuleType("fake_plugin")

        def build_plugin():
            return (
                PluginManifest(id="fake", name="Fake", version="1.0.0"),
                PluginContribution(actions=(ActionDefinition(id="fake.action", name="Fake Action"),)),
            )

        module.build_plugin = build_plugin
        return module

    def _loader(self, registry: PluginRegistry, module: ModuleType) -> PluginLoader:
        return PluginLoader(
            registry,
            importer=lambda name: module,
            module_policy=PluginModulePolicy(allowed_prefixes=("plugins",)),
        )

    def test_load_registers_plugin_and_tracks_module(self) -> None:
        registry = PluginRegistry(ActionRegistry())
        module = self._module()
        loader = self._loader(registry, module)
        registered = loader.load("plugins.fake")
        self.assertEqual(registered.manifest.id, "fake")
        self.assertIs(loader.loaded_module("fake"), module)
        self.assertEqual(len(registry.list()), 1)

    def test_unload_removes_plugin_and_module(self) -> None:
        registry = PluginRegistry(ActionRegistry())
        module = self._module()
        loader = self._loader(registry, module)
        loader.load("plugins.fake")
        loader.unload("fake")
        self.assertEqual(registry.list(), ())
        self.assertIsNone(loader.loaded_module("fake"))

    def test_module_without_builder_is_rejected(self) -> None:
        loader = PluginLoader(
            PluginRegistry(ActionRegistry()),
            importer=lambda name: ModuleType("empty"),
            module_policy=PluginModulePolicy(allowed_prefixes=("plugins",)),
        )
        with self.assertRaises(PluginLoadError):
            loader.load("plugins.empty")

    def test_relative_module_name_is_rejected(self) -> None:
        loader = PluginLoader(PluginRegistry(ActionRegistry()))
        with self.assertRaises(PluginLoadError):
            loader.load(".relative")


if __name__ == "__main__":
    unittest.main()
