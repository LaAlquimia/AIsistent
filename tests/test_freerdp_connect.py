"""Connect-poll tests for the FreeRDP transport.

The poll is where the 2026-11-23 acceptance runs were won and
lost: the render bar (change 11), the login-dialog guard
(change 13), and the wake nudge + timeout evidence frame
(change 14). Split out of test_freerdp_transport.py for the
line cap; the fakes and frame builders are imported from it.
"""

import unittest

from aisistent.config import settings
from aisistent.transport.freerdp import FreeRDPTransport
from test_freerdp_transport import (
    FakeBridge,
    QueueBridge,
    _black_frame,
    _creds,
    _dialog_frame,
    _mostly_black_frame,
    _passing_frame,
)


class TestFreeRDPConnectPoll(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.t = FreeRDPTransport(bridge=self.bridge)

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

    def test_login_dialog_never_counts_as_connected(self):
        # Change 13 regression: the render bar alone passed on
        # the login screen during the 2026-11-23 acceptance run.
        self.bridge.frame = _dialog_frame()
        self.t._poll_s = 0.05
        saved = settings.connect_timeout_s
        settings.connect_timeout_s = 0.3
        try:
            with self.assertRaises(RuntimeError) as cm:
                self.t.connect(**_creds())
        finally:
            settings.connect_timeout_s = saved
        self.assertIn("login screen", str(cm.exception))
        self.assertEqual(self.bridge.killed, [4242])
        self.assertTrue(self.bridge.stopped)

    def test_dialog_then_desktop_connects(self):
        bridge = QueueBridge([_dialog_frame(), _passing_frame()])
        t = FreeRDPTransport(bridge=bridge)
        t._poll_s = 0.05
        t.connect(**_creds())
        self.assertTrue(t.is_connected)

    def test_mostly_black_frame_fails_the_bar(self):
        self.bridge.frame = _mostly_black_frame()
        self.t._poll_s = 0.05
        saved = settings.connect_timeout_s
        settings.connect_timeout_s = 0.3
        try:
            with self.assertRaises(RuntimeError):
                self.t.connect(**_creds())
        finally:
            settings.connect_timeout_s = saved

    def test_blank_session_wakes_on_nudge(self):
        # Change 14: a blanked / unpainted session repaints on
        # activity. The bridge serves black until the pointer
        # moves, then a passing desktop frame.
        class WakeBridge(FakeBridge):
            def grab_frame(self):
                if self.pointer_calls:
                    return _passing_frame()
                return _black_frame()

        bridge = WakeBridge()
        t = FreeRDPTransport(bridge=bridge)
        t._poll_s = 0.05
        saved = settings.connect_timeout_s
        settings.connect_timeout_s = 2.0
        try:
            t.connect(**_creds())
        finally:
            settings.connect_timeout_s = saved
        self.assertTrue(t.is_connected)
        self.assertTrue(
            any(c[0] == "move" for c in bridge.pointer_calls))

    def test_persistent_blank_timeout_saves_last_frame(self):
        # Change 14: a connect timeout keeps the last frame as
        # evidence and names it in the error.
        self.bridge.frame = _black_frame()
        self.t._poll_s = 0.05
        saved = settings.connect_timeout_s
        settings.connect_timeout_s = 0.3
        try:
            with self.assertRaises(RuntimeError) as cm:
                self.t.connect(**_creds())
        finally:
            settings.connect_timeout_s = saved
        self.assertIn("connect-timeout.png", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
