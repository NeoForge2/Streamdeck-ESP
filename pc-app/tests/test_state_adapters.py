"""Tests for application-layer StateStore adapters."""

import unittest

from streamdeck_companion.core import ActionState, StateStore
from streamdeck_companion.state_adapters import update_device_connection, update_home_assistant_entity


class StateAdapterTests(unittest.TestCase):
    def test_device_connection_uses_stable_key(self):
        store = StateStore()
        value = update_device_connection(store, True)
        self.assertEqual(value.key, "device:streamdeck")
        self.assertEqual(value.status, ActionState.ACTIVE)
        self.assertTrue(value.value)

    def test_device_disconnect_is_explicit(self):
        store = StateStore()
        value = update_device_connection(store, False)
        self.assertEqual(value.status, ActionState.DISCONNECTED)
        self.assertFalse(value.value)

    def test_ha_on_off_map_to_core_states(self):
        store = StateStore()
        on_value = update_home_assistant_entity(store, "light.bureau", {"state": "on", "attributes": {"brightness": 200}})
        off_value = update_home_assistant_entity(store, "switch.pc", {"state": "off", "attributes": {}})
        self.assertEqual(on_value.status, ActionState.ON)
        self.assertEqual(on_value.attributes["brightness"], 200)
        self.assertEqual(off_value.status, ActionState.OFF)

    def test_unavailable_entity_maps_to_disconnected(self):
        store = StateStore()
        value = update_home_assistant_entity(store, "sensor.test", {"state": "unavailable", "attributes": {}})
        self.assertEqual(value.status, ActionState.DISCONNECTED)

    def test_numeric_sensor_remains_active_and_preserves_value(self):
        store = StateStore()
        value = update_home_assistant_entity(store, "sensor.temperature", {"state": "21.5", "attributes": {"unit_of_measurement": "°C"}})
        self.assertEqual(value.status, ActionState.ACTIVE)
        self.assertEqual(value.value, "21.5")
        self.assertEqual(store.get("ha:sensor.temperature"), value)


if __name__ == "__main__":
    unittest.main()
