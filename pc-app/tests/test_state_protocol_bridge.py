"""Tests for StateStore -> V2 protocol projection."""

import unittest

from streamdeck_companion.core import ActionState, MessageType, StateStore
from streamdeck_companion.state_protocol_bridge import StateProtocolBridge


class StateProtocolBridgeTests(unittest.TestCase):
    def test_live_update_is_projected(self):
        store = StateStore()
        messages = []
        bridge = StateProtocolBridge(store, messages.append)
        bridge.start()

        store.update("device:streamdeck", status=ActionState.ACTIVE, value=True)

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].type, MessageType.UPDATE_STATE)
        self.assertEqual(messages[0].payload["key"], "device:streamdeck")
        self.assertEqual(messages[0].payload["status"], "active")
        self.assertTrue(messages[0].payload["value"])

    def test_snapshot_is_replayed_on_start(self):
        store = StateStore()
        store.update("ha:light.office", status=ActionState.ON, value="on")
        messages = []

        StateProtocolBridge(store, messages.append).start()

        self.assertEqual([message.payload["key"] for message in messages], ["ha:light.office"])

    def test_prefix_filter_limits_forwarded_state(self):
        store = StateStore()
        messages = []
        bridge = StateProtocolBridge(store, messages.append, prefixes=("device:",))
        bridge.start()

        store.update("ha:light.office", status=ActionState.ON, value="on")
        store.update("device:streamdeck", status=ActionState.ACTIVE, value=True)

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].payload["key"], "device:streamdeck")

    def test_stop_unsubscribes(self):
        store = StateStore()
        messages = []
        bridge = StateProtocolBridge(store, messages.append)
        bridge.start()
        bridge.stop()

        store.update("device:streamdeck", status=ActionState.DISCONNECTED, value=False)

        self.assertEqual(messages, [])
        self.assertFalse(bridge.started)

    def test_start_is_idempotent(self):
        store = StateStore()
        messages = []
        bridge = StateProtocolBridge(store, messages.append)
        bridge.start()
        bridge.start()

        store.update("device:streamdeck", status=ActionState.ACTIVE, value=True)

        self.assertEqual(len(messages), 1)


if __name__ == "__main__":
    unittest.main()
