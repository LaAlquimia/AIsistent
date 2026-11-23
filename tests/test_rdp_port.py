"""Acceptance tests for the RDP port plumbing (FORK.md change 7).

Problem: upstream connect_rdp had no port parameter and simple-rdp
defaulted to 3389, so a server on a nonstandard port (the trial's
xrdp on 127.0.0.1:3391, chosen to leave GNOME's 3389/3390 untouched)
was unreachable.

Pass conditions:
1. Settings.rdp_port defaults to 3389; RDP_PORT env overrides it;
   a non-numeric RDP_PORT leaves the default.
2. RDPTransport passes an explicit port through to the client.
3. RDPTransport falls back to settings.rdp_port when no port is given.

Run with:  python -m unittest discover -s tests -v
"""

import os
import unittest
from unittest import mock

from aisistent.config import Settings
from aisistent.transport import rdp as rdp_mod
from aisistent.transport.rdp import RDPTransport


class _FakeClient:
    captured: dict = {}

    def __init__(self, **kwargs):
        _FakeClient.captured = kwargs

    async def connect(self):
        return None


class TestRdpPortSettings(unittest.TestCase):
    def test_default_3389(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("RDP_PORT", None)
            self.assertEqual(Settings().rdp_port, 3389)

    def test_env_override(self):
        with mock.patch.dict(os.environ, {"RDP_PORT": "3391"}):
            self.assertEqual(Settings().rdp_port, 3391)

    def test_env_garbage_keeps_default(self):
        with mock.patch.dict(os.environ, {"RDP_PORT": "abc"}):
            self.assertEqual(Settings().rdp_port, 3389)


class TestRdpPortTransport(unittest.TestCase):
    def _connect(self, **kwargs):
        with mock.patch.object(rdp_mod, "_client_class", lambda: _FakeClient):
            t = RDPTransport()
            t.connect(host="127.0.0.1", username="u", password="p", **kwargs)
        return _FakeClient.captured

    def test_explicit_port_passed_through(self):
        captured = self._connect(port=3391)
        self.assertEqual(captured.get("port"), 3391)

    def test_default_port_from_settings(self):
        captured = self._connect()
        self.assertEqual(captured.get("port"), rdp_mod.settings.rdp_port)


if __name__ == "__main__":
    unittest.main()
