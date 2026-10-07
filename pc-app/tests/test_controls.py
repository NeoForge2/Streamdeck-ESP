from __future__ import annotations

import unittest

from streamdeck_companion.core.actions import ActionCommand
from streamdeck_companion.core.controls import ControlDefinition, ControlRouter, ControlStateResolver
from streamdeck_companion.core.events import InputEvent, InputKind
from streamdeck_companion.core.state import StateStore, StateValue
from streamdeck_companion.core.triggers import ActionState, Trigger


class ControlTests(unittest.TestCase):
    def test_button_supports_multiple_triggers(self) -> None:
        control = ControlDefinition(
            id="button:1",
            kind=InputKind.BUTTON,
            actions={
                Trigger.PRESS: ActionCommand("media.play_pause"),
                Trigger.DOUBLE_PRESS: ActionCommand("media.next"),
                Trigger.HOLD: ActionCommand("app.open", {"name": "spotify"}),
            },
        )
        router = ControlRouter((control,))
        command = router.resolve(InputEvent("button:1", InputKind.BUTTON, Trigger.DOUBLE_PRESS))
        self.assertEqual(command.action_id, "media.next")

    def test_encoder_routes_rotation_press_hold_and_release(self) -> None:
        control = ControlDefinition(
            id="encoder:1",
            kind=InputKind.ENCODER,
            actions={
                Trigger.ROTATE_CW: ActionCommand("volume.change", {"delta": 1}),
                Trigger.ROTATE_CCW: ActionCommand("volume.change", {"delta": -1}),
                Trigger.PRESS: ActionCommand("volume.mute"),
                Trigger.HOLD: ActionCommand("audio.select_device"),
                Trigger.RELEASE: ActionCommand("ui.close_picker"),
            },
            state_key="audio:master-volume",
            context={"display": "volume"},
        )
        router = ControlRouter((control,))
        self.assertEqual(
            router.resolve(InputEvent("encoder:1", InputKind.ENCODER, Trigger.ROTATE_CW)).parameters["delta"],
            1,
        )
        self.assertEqual(router.resolve(InputEvent("encoder:1", InputKind.ENCODER, Trigger.PRESS)).action_id, "volume.mute")

    def test_kind_mismatch_does_not_route(self) -> None:
        control = ControlDefinition(
            id="encoder:1",
            kind=InputKind.ENCODER,
            actions={Trigger.PRESS: ActionCommand("volume.mute")},
        )
        router = ControlRouter((control,))
        self.assertIsNone(router.resolve(InputEvent("encoder:1", InputKind.BUTTON, Trigger.PRESS)))

    def test_control_state_is_read_from_state_store(self) -> None:
        store = StateStore()
        store.set(StateValue("audio:master-volume", status=ActionState.ACTIVE, value=66))
        control = ControlDefinition("encoder:1", InputKind.ENCODER, state_key="audio:master-volume")
        snapshot = ControlStateResolver(store).resolve(control)
        self.assertEqual(snapshot.state.value, 66)
        self.assertEqual(snapshot.state.status, ActionState.ACTIVE)

    def test_duplicate_control_id_is_rejected(self) -> None:
        control = ControlDefinition("button:1", InputKind.BUTTON)
        router = ControlRouter((control,))
        with self.assertRaises(ValueError):
            router.register(control)


if __name__ == "__main__":
    unittest.main()
