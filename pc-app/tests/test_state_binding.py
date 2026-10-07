from __future__ import annotations

import unittest

from streamdeck_companion.core.state import StateStore, StateValue
from streamdeck_companion.core.state_binding import StateAppearance, StateBinding, StateBindingResolver
from streamdeck_companion.core.triggers import ActionState


class StateBindingTests(unittest.TestCase):
    def test_resolves_appearance_from_real_state(self) -> None:
        store = StateStore()
        store.set(StateValue("ha:switch.office", status=ActionState.ON, value=True))
        binding = StateBinding(
            "ha:switch.office",
            appearances={
                ActionState.OFF: StateAppearance(label="Off", icon="power-off"),
                ActionState.ON: StateAppearance(label="On", icon="power-on"),
            },
        )
        resolved = StateBindingResolver(store).resolve(binding)
        self.assertEqual(resolved.status, ActionState.ON)
        self.assertEqual(resolved.appearance.label, "On")
        self.assertTrue(resolved.source.value)

    def test_missing_source_is_disconnected(self) -> None:
        store = StateStore()
        binding = StateBinding(
            "plugin:missing",
            appearances={ActionState.DISCONNECTED: StateAppearance(label="Offline")},
        )
        resolved = StateBindingResolver(store).resolve(binding)
        self.assertEqual(resolved.status, ActionState.DISCONNECTED)
        self.assertEqual(resolved.appearance.label, "Offline")
        self.assertIsNone(resolved.source)

    def test_loading_and_error_have_distinct_presentations(self) -> None:
        store = StateStore()
        binding = StateBinding(
            "provider:test",
            appearances={
                ActionState.LOADING: StateAppearance(label="Loading"),
                ActionState.ERROR: StateAppearance(label="Error"),
            },
        )
        store.set(StateValue("provider:test", status=ActionState.LOADING))
        self.assertEqual(StateBindingResolver(store).resolve(binding).appearance.label, "Loading")
        store.set(StateValue("provider:test", status=ActionState.ERROR))
        self.assertEqual(StateBindingResolver(store).resolve(binding).appearance.label, "Error")

    def test_unknown_status_uses_fallback(self) -> None:
        store = StateStore()
        store.set(StateValue("system:clock", status=ActionState.ACTIVE, value="12:00"))
        binding = StateBinding("system:clock", fallback=StateAppearance(label="Clock"))
        self.assertEqual(StateBindingResolver(store).resolve(binding).appearance.label, "Clock")


if __name__ == "__main__":
    unittest.main()
