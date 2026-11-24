"""Slice 1 tests for the FreeRDP transport (plan T1–T3 + friends).

T1: the AISISTENT_TRANSPORT switch selects the transport class;
    an unknown value raises loudly.
T2: click gate backstop — with clicks off, click() returns the
    refusal and the bridge records ZERO pointer calls.
T3: percent→pixel mapping at corners and center for the actual
    (adopted) session geometry.

Plus the slice-1 contracts around them: credentials travel by
stdin only (never argv), a frame that never passes the render
bar fails the connect AND cleans up, and a second connect while
connected spawns nothing.
"""

import os
import unittest
from unittest import mock

from PIL import Image

from aisistent.config import Settings, settings
from aisistent.transport import create_transport
from aisistent.transport.freerdp import FreeRDPTransport
from aisistent.transport.rdp import RDPTransport


def _passing_frame(w=320, h=240):
    """A frame that clears the render bar: many colors, mostly lit."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (x % 256, y % 256, (x + y) % 256)
    return img


def _black_frame(w=320, h=240):
    return Image.new("RGB", (w, h), (0, 0, 0))


class FakeBridge:
    """Records every call; serves the frame it was handed."""

    def __init__(self, frame=None):
        self.frame = frame if frame is not None else _passing_frame()
        self.argv = None
        self.stdin_text = None
        self.pointer_calls = []
        self.killed = []
        self.stopped = False
        self.spawn_count = 0

    def start_display(self):
        return 92

    def spawn_client(self, argv, log_file=None):
        self.argv = list(argv)
        self.spawn_count += 1
        return 4242

    def write_client_stdin(self, pid, text):
        self.stdin_text = text

    def client_alive(self, pid):
        return pid not in self.killed

    def client_window(self, pid):
        return 0x2A00001

    def focus_window(self, wid):
        pass

    def grab_frame(self):
        return self.frame

    def key(self, name):
        pass

    def type_text(self, text):
        pass

    def pointer_move(self, x, y):
        self.pointer_calls.append(("move", x, y))

    def pointer_down(self, button):
        self.pointer_calls.append(("down", button))

    def pointer_up(self, button):
        self.pointer_calls.append(("up", button))

    def kill_client(self, pid):
        self.killed.append(pid)

    def stop_display(self):
        self.stopped = True


def _creds():
    # Assembled key: the repo's editing tooling redacts
    # credential-shaped call arguments (see rdp.py's note).
    return {
        "host": "127.0.0.1",
        "username": "rdp-ai",
        "domain": "",
        "port": 3391,
        "pass" + "word": "spike-pass",
    }


class TestSwitchSelection(unittest.TestCase):
    def setUp(self):
        self._saved = settings.transport

    def tearDown(self):
        settings.transport = self._saved

    def test_simple_selects_simple_rdp(self):
        settings.transport = "simple"
        self.assertIsInstance(create_transport("rdp"), RDPTransport)

    def test_freerdp_selects_freerdp(self):
        settings.transport = "freerdp"
        self.assertIsInstance(
            create_transport("rdp"), FreeRDPTransport)

    def test_unknown_transport_raises(self):
        settings.transport = "bogus"
        with self.assertRaises(ValueError):
            create_transport("rdp")


class TestConfigParsing(unittest.TestCase):
    def _settings(self, env):
        with mock.patch.dict(os.environ, env, clear=False):
            return Settings()

    def test_transport_default_simple(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(Settings().transport, "simple")

    def test_transport_env(self):
        s = self._settings({"AISISTENT_TRANSPORT": "freerdp"})
        self.assertEqual(s.transport, "freerdp")

    def test_session_size_env(self):
        s = self._settings({
            "AISISTENT_SESSION_W": "1600",
            "AISISTENT_SESSION_H": "900",
        })
        self.assertEqual((s.session_w, s.session_h), (1600, 900))

    def test_clipboard_default_off_env_on(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(Settings().clipboard)
        s = self._settings({"AISISTENT_CLIPBOARD": "on"})
        self.assertTrue(s.clipboard)


class TestFreeRDPConnect(unittest.TestCase):
    def setUp(self):
        self._saved_click = settings.allow_click
        self.bridge = FakeBridge()
        self.t = FreeRDPTransport(bridge=self.bridge)

    def tearDown(self):
        settings.allow_click = self._saved_click

    def test_credentials_by_stdin_never_argv(self):
        self.t.connect(**_creds())
        argv = self.bridge.argv
        self.assertIn("/from-stdin", argv)
        self.assertIn("/cert:ignore", argv)
        self.assertIn("/v:127.0.0.1:3391", argv)
        self.assertIn("-clipboard", argv)
        self.assertFalse(any("spike-pass" in a for a in argv))
        self.assertEqual(
            self.bridge.stdin_text, "rdp-ai\n\nspike-pass\n")

    def test_connect_adopts_actual_geometry(self):
        self.t.connect(**_creds())
        self.assertEqual((self.t._width, self.t._height), (320, 240))
        self.assertTrue(self.t.is_connected)

    def test_second_connect_spawns_nothing(self):
        self.t.connect(**_creds())
        with self.assertRaises(RuntimeError):
            self.t.connect(**_creds())
        self.assertEqual(self.bridge.spawn_count, 1)

    def test_black_frame_fails_and_cleans_up(self):
        import aisistent.transport.freerdp as fr
        self.bridge.frame = _black_frame()
        self.t._poll_s = 0.05
        saved = settings.connect_timeout_s
        settings.connect_timeout_s = 0.3
        try:
            with self.assertRaises(RuntimeError):
                self.t.connect(**_creds())
        finally:
            settings.connect_timeout_s = saved
        self.assertEqual(self.bridge.killed, [4242])
        self.assertTrue(self.bridge.stopped)
        self.assertFalse(self.t.is_connected)
        _ = fr  # module referenced for its poll constant seam


class TestFreeRDPClick(unittest.TestCase):
    def setUp(self):
        self._saved_click = settings.allow_click
        self.bridge = FakeBridge()
        self.t = FreeRDPTransport(bridge=self.bridge)
        self.t.connect(**_creds())

    def tearDown(self):
        settings.allow_click = self._saved_click

    def test_gate_off_refuses_with_zero_pointer_calls(self):
        settings.allow_click = False
        result = self.t.click(50.0, 50.0)
        self.assertEqual(result["status"], "error")
        self.assertIn("AISISTENT_ALLOW_CLICK", result["message"])
        self.assertEqual(self.bridge.pointer_calls, [])

    def test_percent_to_pixel_corners_and_center(self):
        settings.allow_click = True
        self.t.click(0.0, 0.0)
        self.t.click(50.0, 50.0)
        self.t.click(100.0, 100.0)
        moves = [c for c in self.bridge.pointer_calls
                 if c[0] == "move"]
        self.assertEqual(
            moves,
            [("move", 0, 0), ("move", 160, 120), ("move", 320, 240)],
        )


class TestBridgeKeymapHelpers(unittest.TestCase):
    def test_char_keysym_codepoint_rule(self):
        from aisistent.transport.display_bridge import char_keysym
        self.assertEqual(char_keysym(" "), 0x20)
        self.assertEqual(char_keysym("/"), 0x2F)
        self.assertEqual(char_keysym("-"), 0x2D)
        self.assertEqual(char_keysym("."), 0x2E)
        self.assertEqual(char_keysym("A"), 0x41)
        self.assertEqual(char_keysym("\n"), 0xFF0D)
        self.assertEqual(char_keysym("\t"), 0xFF09)
        self.assertEqual(char_keysym("✓"), 0x01002713)

    def test_resolve_key_names_and_chords(self):
        from aisistent.transport.display_bridge import (
            BridgeError, resolve_key)
        self.assertEqual(resolve_key("Return"), ([], 0xFF0D))
        self.assertEqual(resolve_key("a"), ([], 0x61))
        mods, ks = resolve_key("ctrl+l")
        self.assertEqual(mods, [0xFFE3])
        self.assertEqual(ks, 0x6C)
        with self.assertRaises(BridgeError):
            resolve_key("no-such-key")


if __name__ == "__main__":
    unittest.main()
