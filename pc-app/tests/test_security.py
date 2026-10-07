from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from streamdeck_companion.security import EnvironmentSecretStore, REDACTED, redact_mapping, require_secret


class SecurityTests(unittest.TestCase):
    def test_environment_secret_store_uses_prefixed_normalized_key(self) -> None:
        with patch.dict(os.environ, {"STREAMDECK_HA_TOKEN": "abc"}, clear=False):
            self.assertEqual(EnvironmentSecretStore().get("ha.token"), "abc")

    def test_redaction_is_recursive(self) -> None:
        safe = redact_mapping(
            {
                "url": "http://localhost",
                "token": "abc",
                "nested": {"password": "pw", "name": "ok"},
                "items": [{"access_token": "nested-secret"}],
            }
        )
        self.assertEqual(safe["token"], REDACTED)
        self.assertEqual(safe["nested"]["password"], REDACTED)
        self.assertEqual(safe["items"][0]["access_token"], REDACTED)
        self.assertEqual(safe["url"], "http://localhost")

    def test_require_secret_fails_without_value(self) -> None:
        class EmptyStore:
            def get(self, key):
                return None

        with self.assertRaises(RuntimeError):
            require_secret(EmptyStore(), "ha.token")


if __name__ == "__main__":
    unittest.main()
