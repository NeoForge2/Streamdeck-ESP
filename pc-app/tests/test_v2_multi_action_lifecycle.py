from __future__ import annotations

from pathlib import Path
import unittest


class V2MultiActionLifecycleTests(unittest.TestCase):
    def test_reconnect_loop_does_not_shutdown_multi_action_runtime(self) -> None:
        """The tray reuses one V2DeviceClient instance across reconnects."""
        source = (
            Path(__file__).parents[1]
            / "streamdeck_companion"
            / "v2_device_client.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("async def run_forever", source)
        self.assertNotIn("_multi_action_runtime.shutdown", source)


if __name__ == "__main__":
    unittest.main()
