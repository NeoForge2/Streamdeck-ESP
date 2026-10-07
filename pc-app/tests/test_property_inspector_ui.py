from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PropertyInspectorUiTests(unittest.TestCase):
    def test_base_template_loads_property_inspector_after_page_scripts(self) -> None:
        template = (ROOT / "streamdeck_companion" / "templates" / "base.html").read_text(encoding="utf-8")
        scripts_block = template.index("{% block scripts %}")
        inspector_script = template.index("property-inspector.js")
        self.assertGreater(inspector_script, scripts_block)

    def test_property_inspector_consumes_v2_catalog(self) -> None:
        script = (ROOT / "streamdeck_companion" / "static" / "property-inspector.js").read_text(encoding="utf-8")
        self.assertIn('/api/v2/action-catalog', script)
        self.assertIn('modal-action-type', script)
        self.assertIn('modal-action-target', script)
        self.assertIn('encoder-modal-${direction}-type', script)
        self.assertIn('encoder-modal-${direction}-target', script)

    def test_property_inspector_supports_dynamic_option_sources(self) -> None:
        script = (ROOT / "streamdeck_companion" / "static" / "property-inspector.js").read_text(encoding="utf-8")
        self.assertIn('media_commands', script)
        self.assertIn('/audio-devices', script)
        self.assertIn('/audio-sessions', script)


if __name__ == "__main__":
    unittest.main()
