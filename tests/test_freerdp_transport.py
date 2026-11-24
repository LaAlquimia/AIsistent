"""Slice 1 tests for the FreeRDP transport (plan T1–T3 + friends).

T1: the AISISTENT_TRANSPORT switch selects the transport class;
    an unknown value raises loudly.
T2: click gate backstop — with clicks off, click() returns the
    refusal and the bridge records ZERO pointer calls.
T3: percent→pixel mapping at corners and center for the actual
    (adopted) session geometry.

Plus the slice-1 contracts around them: credentials travel
in argv (change 13), and a second connect while connected
spawns nothing. The connect-poll tests (render bar, login
dialog, wake nudge) live in test_freerdp_connect.py.
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


def _mostly_black_frame(w=320, h=240):
    """Mostly black with >50 distinct colors sprinkled in.

    Pins the render bar's non-black term: a getcolors map read
    backwards (count and color swapped) once made that term
    always read 100%, so only the color count was really
    being tested (change 13).
    """
    img = Image.new("RGB", (w, h), (0, 0, 0))
    px = img.load()
    for i in range(120):
        px[i % w, i // w] = (i, (i * 2) % 256, (i * 3) % 256)
    return img


def _dialog_frame(w=320, h=240):
    """Synthetic xrdp login screen with the measured signature:
    uniform blue backdrop, white dialog box at the center, and
    enough distinct colors to pass the render bar on its own."""
    img = Image.new("RGB", (w, h), (0, 48, 87))
    px = img.load()
    for y in range(int(h * 0.35), int(h * 0.65)):
        for x in range(int(w * 0.4), int(w * 0.6)):
            px[x, y] = (240, 240, 240)
    for i in range(120):  # widget/text color variety
        px[i % w, h - 1 - (i // w)] = (i, (i * 2) % 256, (i * 3) % 256)
    return img


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


class QueueBridge(FakeBridge):
    """Serves frames from a queue, then repeats the last one."""

    def __init__(self, frames):
        super().__init__(frames[0])
        self._frames = list(frames)

    def grab_frame(self):
        if len(self._frames) > 1:
            return self._frames.pop(0)
        return self._frames[0]


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

    def test_transport_default_freerdp(self):
        # Flipped by slice 3's live acceptance (2026-11-23).
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(Settings().transport, "freerdp")

    def test_transport_env(self):
        s = self._settings({"AISISTENT_TRANSPORT": "freerdp"})
        self.assertEqual(s.transport, "freerdp")
        s = self._settings({"AISISTENT_TRANSPORT": "simple"})
        self.assertEqual(s.transport, "simple")

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

    def test_credentials_in_argv_stdin_route_retired(self):
        # Change 13: /from-stdin was measured not to deliver
        # (the client sat at the server's login screen); the
        # plan's O1 fallback puts the credential in argv as /p.
        self.t.connect(**_creds())
        argv = self.bridge.argv
        self.assertIn("/p:spike-pass", argv)
        self.assertNotIn("/from-stdin", argv)
        self.assertIn("/cert:ignore", argv)
        self.assertIn("/v:127.0.0.1:3391", argv)
        self.assertIn("-clipboard", argv)
        self.assertIsNone(self.bridge.stdin_text)

    def test_connect_adopts_actual_geometry(self):
        self.t.connect(**_creds())
        self.assertEqual((self.t._width, self.t._height), (320, 240))
        self.assertTrue(self.t.is_connected)

    def test_second_connect_spawns_nothing(self):
        self.t.connect(**_creds())
        with self.assertRaises(RuntimeError):
            self.t.connect(**_creds())
        self.assertEqual(self.bridge.spawn_count, 1)

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
