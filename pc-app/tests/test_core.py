"""Unit tests for the framework-independent Streamdeck Core."""

import unittest

from streamdeck_companion.core import (
    ActionCommand,
    ActionDefinition,
    ActionEngine,
    ActionRegistry,
    ActionState,
    ActionValidationError,
    DuplicateActionError,
    InputEvent,
    InputKind,
    MissingExecutorError,
    StateStore,
    Trigger,
    TriggerBindings,
    UnknownActionError,
)
from streamdeck_companion.core.legacy import from_legacy, to_legacy


class ActionRegistryTests(unittest.TestCase):
    def test_register_get_and_filter(self):
        registry = ActionRegistry()
        launch = ActionDefinition(
            id="launch",
            name="Launch application",
            category="windows",
            supported_triggers=frozenset({Trigger.PRESS, Trigger.DOUBLE_PRESS}),
        )
        registry.register(launch)

        self.assertIs(registry.get("launch"), launch)
        self.assertEqual(registry.list("windows"), (launch,))
        self.assertEqual(len(registry), 1)

    def test_duplicate_action_is_rejected(self):
        registry = ActionRegistry()
        definition = ActionDefinition(id="url", name="Open URL")
        registry.register(definition)
        with self.assertRaises(DuplicateActionError):
            registry.register(definition)

    def test_unknown_action_is_rejected(self):
        registry = ActionRegistry()
        with self.assertRaises(UnknownActionError):
            registry.get("missing")

    def test_definition_validator_is_used(self):
        def require_target(values):
            if not values.get("target"):
                raise ActionValidationError("target is required")

        registry = ActionRegistry()
        registry.register(ActionDefinition(id="url", name="Open URL", validator=require_target))
        with self.assertRaises(ActionValidationError):
            registry.validate(ActionCommand("url", {}))


class ActionEngineTests(unittest.TestCase):
    def test_execute_validates_then_calls_executor(self):
        seen = []
        engine = ActionEngine()
        engine.register(
            ActionDefinition(id="echo", name="Echo"),
            lambda command: seen.append(command.parameters["value"]),
        )

        engine.execute(ActionCommand("echo", {"value": "ok"}))
        self.assertEqual(seen, ["ok"])

    def test_known_action_without_executor_is_rejected(self):
        registry = ActionRegistry()
        registry.register(ActionDefinition(id="known", name="Known"))
        engine = ActionEngine(registry)
        with self.assertRaises(MissingExecutorError):
            engine.execute(ActionCommand("known", {}))


class EventBindingTests(unittest.TestCase):
    def test_same_source_can_bind_independent_triggers(self):
        bindings = TriggerBindings()
        press = ActionCommand("press_action")
        hold = ActionCommand("hold_action")
        bindings.bind("button:1", Trigger.PRESS, press)
        bindings.bind("button:1", Trigger.HOLD, hold)

        self.assertEqual(
            bindings.resolve(InputEvent("button:1", InputKind.BUTTON, Trigger.PRESS)),
            press,
        )
        self.assertEqual(
            bindings.resolve(InputEvent("button:1", InputKind.BUTTON, Trigger.HOLD)),
            hold,
        )

    def test_encoder_rotation_uses_generic_trigger(self):
        bindings = TriggerBindings()
        command = ActionCommand("volume_up")
        bindings.bind("encoder:2", Trigger.ROTATE_CW, command)
        event = InputEvent("encoder:2", InputKind.ENCODER, Trigger.ROTATE_CW)
        self.assertEqual(bindings.resolve(event), command)


class StateStoreTests(unittest.TestCase):
    def test_update_notifies_subscribers_and_updates_snapshot(self):
        store = StateStore()
        seen = []
        unsubscribe = store.subscribe(seen.append)

        state = store.update("light.salon", status=ActionState.ON, value=True)
        self.assertEqual(store.get("light.salon"), state)
        self.assertEqual(store.snapshot()["light.salon"], state)
        self.assertEqual(seen, [state])

        unsubscribe()
        store.update("light.salon", status=ActionState.OFF, value=False)
        self.assertEqual(len(seen), 1)


class LegacyAdapterTests(unittest.TestCase):
    def test_legacy_round_trip_preserves_existing_shape(self):
        legacy = {"type": "keys", "target": ["ctrl", "shift", "s"]}
        command = from_legacy(legacy)
        self.assertEqual(command.action_id, "keys")
        self.assertEqual(to_legacy(command), legacy)

    def test_none_action_stays_empty(self):
        self.assertIsNone(from_legacy({"type": "none", "target": ""}))
        self.assertEqual(to_legacy(None), {"type": "none", "target": ""})


if __name__ == "__main__":
    unittest.main()
