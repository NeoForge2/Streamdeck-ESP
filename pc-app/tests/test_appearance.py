from __future__ import annotations

import unittest

from streamdeck_companion.core.appearance import AnimationDefinition, AnimationKind, ThemeDefinition, ThemeRegistry


class AppearanceTests(unittest.TestCase):
    def test_theme_registry_keeps_design_tokens_renderer_independent(self) -> None:
        registry = ThemeRegistry()
        theme = ThemeDefinition("navy", "Navy", {"surface": "navy", "accent": "signal"})
        registry.register(theme)
        self.assertEqual(registry.get("navy").tokens["accent"], "signal")

    def test_animation_contract_validates_duration_and_repeat(self) -> None:
        animation = AnimationDefinition(AnimationKind.PULSE, duration_ms=250, repeat=2)
        self.assertEqual(animation.kind, AnimationKind.PULSE)
        with self.assertRaises(ValueError):
            AnimationDefinition(AnimationKind.FADE, duration_ms=-1)
        with self.assertRaises(ValueError):
            AnimationDefinition(AnimationKind.FADE, repeat=-1)


if __name__ == "__main__":
    unittest.main()
