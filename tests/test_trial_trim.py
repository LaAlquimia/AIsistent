"""Acceptance tests for the fork's trial trim.

Run with the light dependency set only (mcp, Pillow):
    python -m unittest discover -s tests -v

Pass conditions:
1. Click injection is refused by default (read-only fork).
2. With AISISTENT_ALLOW_CLICK on, the click passes the gate and fails
   only on the missing RDP connection — proving the switch works.
3. The GUI transport is gone: create_transport("gui") raises.
4. The MCP server module imports and registers its tools.
"""

import unittest

from aisistent.config import settings
from aisistent.action import inject_click
from aisistent.transport import create_transport


class TestTrialTrim(unittest.TestCase):
    def setUp(self):
        self._saved = settings.allow_click

    def tearDown(self):
        settings.allow_click = self._saved

    def test_click_refused_by_default(self):
        settings.allow_click = False
        result = inject_click(50.0, 50.0)
        self.assertEqual(result["status"], "error")
        self.assertIn("disabled", result["message"])

    def test_click_gate_opens_with_switch(self):
        settings.allow_click = True
        result = inject_click(50.0, 50.0)
        self.assertEqual(result["status"], "error")
        self.assertNotIn("disabled", result["message"])
        self.assertIn("Not connected", result["message"])

    def test_gui_transport_removed(self):
        with self.assertRaises(ValueError):
            create_transport("gui")

    def test_rdp_transport_available(self):
        t = create_transport("rdp")
        self.assertEqual(type(t).__name__, "RDPTransport")

    def test_server_imports(self):
        import aisistent.server as srv

        self.assertTrue(hasattr(srv, "mcp"))


if __name__ == "__main__":
    unittest.main()
