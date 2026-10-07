from __future__ import annotations

import unittest

from streamdeck_companion.core.layout import LayoutEngine, LayoutError
from streamdeck_companion.core.navigation import GridRect, Placement
from streamdeck_companion.core.providers import ProviderManager
from streamdeck_companion.core.state import StateStore, StateValue
from streamdeck_companion.core.triggers import ActionState
from streamdeck_companion.core.widgets import WidgetDefinition, WidgetResolver, WidgetType


class FakeProvider:
    provider_id = "fake"

    def refresh(self):
        return (
            StateValue("system:cpu", status=ActionState.ACTIVE, value=42),
            StateValue("ha:light.office", status=ActionState.ON, value=True),
        )


class LayoutWidgetsProvidersTests(unittest.TestCase):
    def test_layout_move_resize_duplicate_and_bounds(self) -> None:
        engine = LayoutEngine(9, 4)
        placements = (
            Placement("a", "button-a", GridRect(0, 0, 1, 1)),
            Placement("b", "button-b", GridRect(2, 0, 1, 1)),
        )
        moved = engine.move(placements, "a", 0, 1)
        resized = engine.resize(moved, "a", 2, 1)
        duplicated = engine.duplicate(resized, "b", "c", GridRect(4, 0, 2, 2))
        self.assertEqual(duplicated[0].grid, GridRect(0, 1, 2, 1))
        self.assertEqual(len(duplicated), 3)
        with self.assertRaises(LayoutError):
            engine.move(duplicated, "c", 8, 3)

    def test_layout_rejects_overlap_by_default(self) -> None:
        engine = LayoutEngine(9, 4)
        placements = (
            Placement("a", "one", GridRect(0, 0, 2, 2)),
            Placement("b", "two", GridRect(1, 1, 1, 1)),
        )
        with self.assertRaises(LayoutError):
            engine.validate(placements)

    def test_layout_can_explicitly_allow_overlap(self) -> None:
        engine = LayoutEngine(9, 4, allow_overlap=True)
        placements = (
            Placement("a", "one", GridRect(0, 0, 2, 2)),
            Placement("b", "two", GridRect(1, 1, 1, 1)),
        )
        engine.validate(placements)

    def test_provider_manager_feeds_state_store(self) -> None:
        store = StateStore()
        manager = ProviderManager(store)
        manager.register(FakeProvider())
        refreshed = manager.refresh()
        self.assertEqual(len(refreshed), 2)
        self.assertEqual(store.get("system:cpu").value, 42)
        self.assertEqual(store.get("ha:light.office").status, ActionState.ON)

    def test_widget_resolver_only_reads_state_store(self) -> None:
        store = StateStore()
        store.set(StateValue("system:cpu", status=ActionState.ACTIVE, value=73))
        widget = WidgetDefinition("cpu", WidgetType.GAUGE, state_key="system:cpu", config={"unit": "%"})
        snapshot = WidgetResolver(store).resolve(widget)
        self.assertEqual(snapshot.state.value, 73)
        self.assertEqual(snapshot.definition.config["unit"], "%")


if __name__ == "__main__":
    unittest.main()
