from __future__ import annotations

import unittest

from streamdeck_companion.core.providers import ProviderManager
from streamdeck_companion.core.state import StateStore, StateValue
from streamdeck_companion.core.triggers import ActionState


class GoodProvider:
    provider_id = "good"

    def refresh(self):
        return (StateValue("good:value", status=ActionState.ACTIVE, value=2),)


class FailingProvider:
    provider_id = "bad"

    def refresh(self):
        raise ConnectionError("offline")


class ProviderResilienceTests(unittest.TestCase):
    def test_failed_provider_does_not_prevent_other_refreshes(self) -> None:
        store = StateStore()
        manager = ProviderManager(store)
        manager.register(FailingProvider())
        manager.register(GoodProvider())
        results = manager.refresh_safe()
        self.assertEqual([result.provider_id for result in results], ["bad", "good"])
        self.assertFalse(results[0].ok)
        self.assertTrue(results[1].ok)
        self.assertEqual(store.get("good:value").value, 2)
        self.assertEqual(store.get("provider:bad").status, ActionState.ERROR)
        self.assertEqual(store.get("provider:good").status, ActionState.ACTIVE)

    def test_failure_preserves_last_known_target_state(self) -> None:
        store = StateStore()
        store.set(StateValue("ha:light.office", status=ActionState.ON, value=True))
        manager = ProviderManager(store)
        manager.register(FailingProvider())
        manager.refresh_safe("bad")
        self.assertEqual(store.get("ha:light.office").status, ActionState.ON)
        self.assertTrue(store.get("ha:light.office").value)

    def test_unknown_provider_still_fails_explicitly(self) -> None:
        with self.assertRaises(KeyError):
            ProviderManager(StateStore()).refresh_safe("missing")


if __name__ == "__main__":
    unittest.main()
