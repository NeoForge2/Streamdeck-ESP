from __future__ import annotations

import unittest

from streamdeck_companion.core.control_state_bridge import ControlStateBridge
from streamdeck_companion.core.controls import ControlDefinition
from streamdeck_companion.core.events import InputKind
from streamdeck_companion.core.state import StateStore, StateValue
from streamdeck_companion.core.triggers import ActionState


class ControlStateBridgeTests(unittest.TestCase):
    def test_live_update_only_notifies_bound_controls(self) -> None:
        store = StateStore()
        received = []
        bridge = ControlStateBridge(
            store,
            (
                ControlDefinition("button:1", InputKind.BUTTON, state_key="ha:light.salon"),
                ControlDefinition("encoder:1", InputKind.ENCODER, state_key="audio:master-volume"),
            ),
            received.append,
        )
        bridge.start(replay_snapshot=False)
        store.set(StateValue("ha:light.salon", status=ActionState.ON, value="on"))
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].definition.id, "button:1")
        self.assertEqual(received[0].state.status, ActionState.ON)

    def test_start_can_replay_existing_state(self) -> None:
        store = StateStore()
        store.set(StateValue("audio:master-volume", status=ActionState.ACTIVE, value=42))
        received = []
        bridge = ControlStateBridge(
            store,
            (ControlDefinition("encoder:1", InputKind.ENCODER, state_key="audio:master-volume"),),
            received.append,
        )
        bridge.start()
        self.assertEqual(received[0].state.value, 42)

    def test_start_is_idempotent_and_stop_unsubscribes(self) -> None:
        store = StateStore()
        received = []
        bridge = ControlStateBridge(
            store,
            (ControlDefinition("button:1", InputKind.BUTTON, state_key="device:streamdeck"),),
            received.append,
        )
        bridge.start(replay_snapshot=False)
        bridge.start(replay_snapshot=False)
        store.set(StateValue("device:streamdeck", status=ActionState.ACTIVE, value=True))
        self.assertEqual(len(received), 1)
        bridge.stop()
        store.set(StateValue("device:streamdeck", status=ActionState.DISCONNECTED, value=False))
        self.assertEqual(len(received), 1)


if __name__ == "__main__":
    unittest.main()
