"""Slice 2 tests (plan T4): keyboard on the surface.

T4: send_key/type_text reach the transport with the exact
payload; unknown key names raise. Plus the gate discipline:
the action layer refuses with the keyboard switch off, each
transport backstops it, and a type_text result never echoes
the typed content (audit logs length only, plan G15).
"""

import unittest

from aisistent import action
from aisistent.config import settings
from aisistent.transport import keymap
from aisistent.transport.freerdp import FreeRDPTransport
from aisistent.transport.rdp import RDPTransport, _simple_rdp_key_plan

from test_freerdp_transport import FakeBridge, _creds


class FakeTransport:
    """Records keyboard calls; validates names like a real one."""

    def __init__(self):
        self.keys = []
        self.texts = []

    def send_key(self, key):
        keymap.resolve_key(key)  # unknown names raise, as in prod
        self.keys.append(key)
        return {"status": "success", "action": f"Sent key: {key}"}

    def type_text(self, text):
        self.texts.append(text)
        return {
            "status": "success",
            "action": f"Typed {len(text)} characters",
        }

    def disconnect(self):
        pass


class RecordingBridge(FakeBridge):
    def __init__(self, frame=None):
        super().__init__(frame)
        self.key_calls = []
        self.type_calls = []

    def key(self, name):
        self.key_calls.append(name)

    def type_text(self, text):
        self.type_calls.append(text)


class TestActionKeyboard(unittest.TestCase):
    def setUp(self):
        import aisistent.transport as tmod
        self._tmod = tmod
        self._saved_transport = tmod._transport
        self._saved_kb = settings.allow_keyboard
        self.fake = FakeTransport()
        tmod._transport = self.fake

    def tearDown(self):
        self._tmod._transport = self._saved_transport
        settings.allow_keyboard = self._saved_kb

    def test_gate_off_refuses_and_sends_nothing(self):
        settings.allow_keyboard = False
        r1 = action.send_key("ctrl+l")
        r2 = action.type_text("echo hi")
        for r in (r1, r2):
            self.assertEqual(r["status"], "error")
            self.assertIn("AISISTENT_ALLOW_KEYBOARD", r["message"])
        self.assertEqual(self.fake.keys, [])
        self.assertEqual(self.fake.texts, [])

    def test_gate_on_exact_payloads_reach_transport(self):
        settings.allow_keyboard = True
        action.send_key("ctrl+l")
        action.type_text("echo hi")
        self.assertEqual(self.fake.keys, ["ctrl+l"])
        self.assertEqual(self.fake.texts, ["echo hi"])

    def test_unknown_key_surfaces_as_error(self):
        settings.allow_keyboard = True
        r = action.send_key("no-such-key")
        self.assertEqual(r["status"], "error")
        self.assertIn("no-such-key", r["message"])

    def test_type_result_never_echoes_content(self):
        settings.allow_keyboard = True
        r = action.type_text("echo a-very-secret-marker")
        self.assertEqual(r["status"], "success")
        self.assertNotIn("a-very-secret-marker", str(r))
        self.assertIn("25", r["action"])  # the length, only

    def test_type_cap_enforced_at_the_surface(self):
        settings.allow_keyboard = True
        r = action.type_text("x" * (action.MAX_TYPE_CHARS + 1))
        self.assertEqual(r["status"], "error")
        self.assertEqual(self.fake.texts, [])


class TestFreeRDPKeyboardBackstop(unittest.TestCase):
    def setUp(self):
        self._saved_kb = settings.allow_keyboard
        self.bridge = RecordingBridge()
        self.t = FreeRDPTransport(bridge=self.bridge)
        self.t.connect(**_creds())

    def tearDown(self):
        settings.allow_keyboard = self._saved_kb

    def test_gate_off_refuses_with_zero_bridge_calls(self):
        settings.allow_keyboard = False
        r1 = self.t.send_key("Return")
        r2 = self.t.type_text("echo hi")
        for r in (r1, r2):
            self.assertEqual(r["status"], "error")
            self.assertIn("AISISTENT_ALLOW_KEYBOARD", r["message"])
        self.assertEqual(self.bridge.key_calls, [])
        self.assertEqual(self.bridge.type_calls, [])

    def test_gate_on_reaches_bridge(self):
        settings.allow_keyboard = True
        self.t.send_key("Return")
        self.t.type_text("echo hi")
        self.assertEqual(self.bridge.key_calls, ["Return"])
        self.assertEqual(self.bridge.type_calls, ["echo hi"])


class TestLegacyKeyboard(unittest.TestCase):
    def setUp(self):
        self._saved_kb = settings.allow_keyboard
        self.t = RDPTransport()

    def tearDown(self):
        settings.allow_keyboard = self._saved_kb

    def test_gate_off_refuses(self):
        settings.allow_keyboard = False
        for r in (self.t.send_key("Return"),
                  self.t.type_text("echo hi")):
            self.assertEqual(r["status"], "error")
            self.assertIn("AISISTENT_ALLOW_KEYBOARD", r["message"])

    def test_gate_on_without_client_is_not_connected(self):
        settings.allow_keyboard = True
        with self.assertRaises(RuntimeError):
            self.t.send_key("Return")

    def test_key_plan_translation(self):
        self.assertEqual(
            _simple_rdp_key_plan("Return"), [("enter", "press")])
        self.assertEqual(
            _simple_rdp_key_plan("ctrl+l"),
            [("ctrl", "hold"), ("l", "press"), ("ctrl", "release")],
        )
        self.assertEqual(
            _simple_rdp_key_plan("F5"), [("f5", "press")])
        self.assertEqual(
            _simple_rdp_key_plan("a"), [("a", "press")])
        with self.assertRaises(Exception):
            _simple_rdp_key_plan("no-such-key")


if __name__ == "__main__":
    unittest.main()
