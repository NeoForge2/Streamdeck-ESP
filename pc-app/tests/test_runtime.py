import unittest

from streamdeck_companion.core.action_wheel import ActionWheel, ActionWheelItem
from streamdeck_companion.core.actions import ActionCommand
from streamdeck_companion.core.navigation import Page, Profile
from streamdeck_companion.core.runtime import StreamdeckRuntime
from streamdeck_companion.core.state import StateStore
from streamdeck_companion.core.triggers import ActionState
from streamdeck_companion.core.widgets import WidgetDefinition, WidgetType


class RuntimeTests(unittest.TestCase):
    def test_state_widgets_and_action_wheel_share_runtime(self):
        store = StateStore()
        profile = Profile("p", "Profile", (Page("home", "Home"),), "home")
        runtime = StreamdeckRuntime(profile, store)
        seen = []
        runtime.subscribe_state(seen.append)
        runtime.start()
        store.update("ha:light.office", status=ActionState.ON, value="on")
        widget = WidgetDefinition("light", WidgetType.STATUS, "ha:light.office")
        snapshot = runtime.snapshot((widget,))
        self.assertEqual(snapshot.widgets[0].state.value, "on")
        self.assertEqual(len(seen), 1)

        first = ActionCommand("legacy.none", {"target": ""})
        second = ActionCommand("legacy.none", {"target": "two"})
        runtime.register_wheel("main", ActionWheel((ActionWheelItem("a", "A", first), ActionWheelItem("b", "B", second))))
        self.assertEqual(runtime.rotate_wheel("main", 1).selected.id, "b")
        self.assertEqual(runtime.touch_wheel("main", "a").selected.id, "a")
        self.assertEqual(runtime.activate_wheel("main"), first)
        runtime.stop()
        store.update("ha:light.office", status=ActionState.OFF, value="off")
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()
