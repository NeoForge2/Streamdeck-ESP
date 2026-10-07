"""Tests for the V2 hardware-independent Device API."""

import unittest

from streamdeck_companion.core import DeviceCapability, DeviceDescriptor, DisplaySpec


class DeviceApiTests(unittest.TestCase):
    def test_current_streamdeck_can_be_described_without_hardware_imports(self):
        descriptor = DeviceDescriptor(
            id="guition-main",
            name="Streamdeck ESP",
            model="JC1060P470C_I_W",
            display=DisplaySpec(1024, 600),
            encoder_count=3,
            capabilities=frozenset(
                {
                    DeviceCapability.DISPLAY,
                    DeviceCapability.TOUCH,
                    DeviceCapability.ENCODERS,
                }
            ),
        )

        self.assertEqual(descriptor.display.width, 1024)
        self.assertEqual(descriptor.display.height, 600)
        self.assertEqual(descriptor.encoder_count, 3)
        self.assertTrue(descriptor.supports(DeviceCapability.TOUCH))
        self.assertFalse(descriptor.supports(DeviceCapability.HAPTICS))

    def test_virtual_device_can_use_same_contract(self):
        descriptor = DeviceDescriptor(
            id="virtual-preview",
            name="Desktop Preview",
            display=DisplaySpec(1024, 600),
            capabilities=frozenset({DeviceCapability.DISPLAY, DeviceCapability.TOUCH}),
        )
        self.assertEqual(descriptor.encoder_count, 0)
        self.assertTrue(descriptor.supports(DeviceCapability.DISPLAY))

    def test_display_requires_display_capability(self):
        with self.assertRaises(ValueError):
            DeviceDescriptor(id="bad", name="Bad", display=DisplaySpec(320, 240))

    def test_encoder_count_requires_encoder_capability(self):
        with self.assertRaises(ValueError):
            DeviceDescriptor(id="bad", name="Bad", encoder_count=3)

    def test_invalid_display_dimensions_are_rejected(self):
        with self.assertRaises(ValueError):
            DisplaySpec(0, 600)


if __name__ == "__main__":
    unittest.main()
