"""Acceptance tests for the disconnect teardown fix (FORK.md change 10).

Problem (measured on Yggi, 2026-11-23): the fork's transport drives
the client through one asyncio.run per operation, so the TLS
transport belongs to the connect call's event loop, which is closed
by disconnect time. Upstream's disconnect closes the writer,
asyncio's SSL layer schedules its shutdown timeout on the dead loop,
and RuntimeError ("Event loop is closed") escapes — the tool
reported an error for a session that was in fact over.

Pass conditions:
1. When upstream's disconnect raises the closed-loop artifact, the
   fork's disconnect completes, marks the client disconnected, drops
   the stream references, and closes the raw socket.
2. A RuntimeError about anything else still propagates.
3. Any other exception type still propagates.

Run with:  python -m unittest discover -s tests -v
"""

import asyncio
import unittest

from aisistent.transport import rdp as rdp_mod


class _FakeSocket:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeWriter:
    def __init__(self, sock):
        self._sock = sock

    def get_extra_info(self, name):
        return self._sock if name == "socket" else None


@unittest.skipUnless(rdp_mod._HAS_SIMPLE_RDP, "simple-rdp not installed")
class TestDisconnectTeardown(unittest.TestCase):
    def setUp(self):
        self._orig_disconnect = rdp_mod._RDPClientBase.disconnect

    def tearDown(self):
        rdp_mod._RDPClientBase.disconnect = self._orig_disconnect

    def _client(self, writer=None):
        client = object.__new__(rdp_mod._ForkClientBase)
        client._running = True
        client._connected = True
        client._tcp_reader = object()
        client._tcp_writer = writer
        return client

    def _patch_upstream(self, exc):
        async def raising_disconnect(self):
            raise exc

        rdp_mod._RDPClientBase.disconnect = raising_disconnect

    def test_closed_loop_artifact_is_swallowed_and_socket_closed(self):
        sock = _FakeSocket()
        client = self._client(writer=_FakeWriter(sock))
        self._patch_upstream(RuntimeError("Event loop is closed"))
        asyncio.run(client.disconnect())
        self.assertFalse(client._connected)
        self.assertFalse(client._running)
        self.assertIsNone(client._tcp_writer)
        self.assertIsNone(client._tcp_reader)
        self.assertTrue(sock.closed)

    def test_other_runtime_error_propagates(self):
        client = self._client()
        self._patch_upstream(RuntimeError("some other failure"))
        with self.assertRaises(RuntimeError):
            asyncio.run(client.disconnect())

    def test_other_exception_types_propagate(self):
        client = self._client()
        self._patch_upstream(ValueError("bad state"))
        with self.assertRaises(ValueError):
            asyncio.run(client.disconnect())


if __name__ == "__main__":
    unittest.main()
