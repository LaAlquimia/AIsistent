"""Acceptance tests for the mcp 2.x migration (see MIGRATION-BRIEF.md).

T0/T1: the environment carries exactly mcp 2.3.0 (the fork's pin) and
       the server registers exactly the seven expected tools.
T2:    a live stdio JSON-RPC session against the server launched bare
       (`python -m aisistent`, no arguments) — initialize, tools/list,
       the click refusal, a refused connect_rdp, and proof the server
       is still alive afterwards. The session runs with a scrubbed
       environment (no RDP_*/AISISTENT_* variables leak in) and its
       refused connect is aimed at a dead high port (33999), never a
       real RDP server — on the deployment machine 3389 is a live
       GNOME Remote Desktop and must not receive trial credentials.
T6:    concurrent handler calls under v2's worker-thread dispatch all
       return their normal error JSON; none raises.
T7:    the transport lock actually serializes: with a slow fake
       transport installed, parallel capture calls never overlap
       inside the transport (deleting the lock fails this test).

Run from a clean venv built with:  pip install ".[rdp]"
    python -m unittest discover -s tests -v
"""

import asyncio
import importlib.metadata
import importlib.util
import json
import os
import select
import subprocess
import sys
import tempfile
import threading
import time
import unittest

EXPECTED_TOOLS = {
    "benchmark",
    "connect_rdp",
    "disconnect_rdp",
    "capture_rdp_screen",
    "run_apple_ocr",
    "detect_rdp_buttons",
    "inject_rdp_click",
}

STEP_TIMEOUT = 15  # seconds, per JSON-RPC step (brief T2)
SESSION_DEADLINE = 60  # seconds, total for the whole T2 session (brief T2)


class TestSdkVersionAndRegistration(unittest.TestCase):
    def test_mcp_version_is_the_pin(self):
        self.assertEqual(importlib.metadata.version("mcp"), "2.3.0")

    def test_pillow_version_is_the_pin(self):
        self.assertEqual(importlib.metadata.version("Pillow"), "13.0.0")

    @unittest.skipUnless(
        importlib.util.find_spec("simple_rdp"), "simple-rdp not installed"
    )
    def test_simple_rdp_version_is_the_pin(self):
        self.assertEqual(importlib.metadata.version("simple-rdp"), "0.8.10")

    def test_seven_tools_registered(self):
        import aisistent.server as srv

        tools = asyncio.run(srv.mcp.list_tools())
        self.assertEqual({t.name for t in tools}, EXPECTED_TOOLS)


class StdioSession:
    """Minimal newline-delimited JSON-RPC client for the T2 test."""

    def __init__(self, proc):
        self.proc = proc
        self.buf = ""
        self.deadline = time.monotonic() + SESSION_DEADLINE

    def send(self, obj):
        self.proc.stdin.write((json.dumps(obj) + "\n").encode("utf-8"))
        self.proc.stdin.flush()

    def await_id(self, want_id):
        while True:
            if time.monotonic() > self.deadline:
                raise TimeoutError("T2 session exceeded its total deadline")
            line = self._read_line()
            msg = json.loads(line)
            if msg.get("id") == want_id:
                return msg

    def _read_line(self):
        while "\n" not in self.buf:
            ready, _, _ = select.select(
                [self.proc.stdout], [], [], STEP_TIMEOUT
            )
            if not ready:
                raise TimeoutError("server did not answer in time")
            chunk = os.read(self.proc.stdout.fileno(), 65536)
            if not chunk:
                raise ConnectionError("server closed stdout")
            self.buf += chunk.decode("utf-8")
        line, self.buf = self.buf.split("\n", 1)
        return line


class TestLiveProtocol(unittest.TestCase):
    def test_stdio_session(self):
        # Scrubbed environment: only the basics survive, so no ambient
        # RDP_*/AISISTENT_* variable can retarget the session.
        env = {
            k: os.environ[k]
            for k in ("PATH", "HOME", "LANG", "LC_ALL")
            if k in os.environ
        }
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.Popen(
                [sys.executable, "-m", "aisistent"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=tmp,
                env=env,
            )
            try:
                s = StdioSession(proc)
                s.send({
                    "jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "acceptance", "version": "0"},
                    },
                })
                init = s.await_id(1)
                self.assertEqual(
                    init["result"]["serverInfo"]["name"], "AIsistent"
                )
                s.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

                s.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
                listed = s.await_id(2)
                names = {t["name"] for t in listed["result"]["tools"]}
                self.assertEqual(names, EXPECTED_TOOLS)

                body = self._call(s, 3, "inject_rdp_click",
                                  {"x_percent": 50.0, "y_percent": 50.0})
                self.assertEqual(body["status"], "error")
                self.assertIn("disabled", body["message"])

                body = self._call(s, 4, "connect_rdp", {
                    "host": "127.0.0.1",
                    "username": "trial",
                    "password": "trial",
                    # A dead high port: nothing real is dialed, on any
                    # machine — 3389 is a live server on the target box.
                    "port": 33999,
                })
                self.assertEqual(body["status"], "error")
                self.assertTrue(body["message"])
                self.assertNotIn("event loop", body["message"].lower())

                s.send({"jsonrpc": "2.0", "id": 5, "method": "tools/list"})
                again = s.await_id(5)
                self.assertEqual(
                    {t["name"] for t in again["result"]["tools"]},
                    EXPECTED_TOOLS,
                )
            finally:
                proc.terminate()
                proc.wait(timeout=10)

    @staticmethod
    def _call(session, req_id, name, arguments):
        session.send({
            "jsonrpc": "2.0", "id": req_id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        msg = session.await_id(req_id)
        text = msg["result"]["content"][0]["text"]
        return json.loads(text)


class TestConcurrentHandlers(unittest.TestCase):
    def test_parallel_calls_return_error_json(self):
        import aisistent.server as srv

        results, errors = [], []

        def call_capture():
            try:
                results.append(srv.capture_rdp_screen())
            except Exception as e:  # noqa: BLE001 - the test wants them all
                errors.append(e)

        def call_click():
            try:
                results.append(srv.inject_rdp_click(50.0, 50.0))
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [
            threading.Thread(target=call_capture if i % 2 == 0 else call_click)
            for i in range(8)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 8)
        for raw in results:
            self.assertEqual(json.loads(raw)["status"], "error")


class _ConcurrencyProbe:
    """Fake transport whose capture() is slow enough to overlap."""

    def __init__(self):
        self._counter_lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.is_connected = True

    def connect(self, **kwargs):
        self.is_connected = True

    def disconnect(self):
        self.is_connected = False

    def capture(self):
        with self._counter_lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.25)
        with self._counter_lock:
            self.active -= 1
        return 0.0, "aGVsbG8="

    def click(self, x_percent, y_percent):
        return {"status": "success"}


class TestTransportLock(unittest.TestCase):
    """T7: handlers sharing the transport are serialized by the lock.

    Unlike T6 (whose calls all fail before touching the transport),
    these calls succeed against a slow fake — without the lock in
    server.py they would overlap inside capture() and this fails.
    """

    def setUp(self):
        import aisistent.transport as transport_mod

        self.transport_mod = transport_mod
        self._saved = transport_mod._transport
        self.probe = _ConcurrencyProbe()
        transport_mod.set_transport(self.probe)

    def tearDown(self):
        self.transport_mod._transport = self._saved

    def test_parallel_captures_never_overlap(self):
        import aisistent.server as srv

        results, errors = [], []

        def call_capture():
            try:
                results.append(srv.capture_rdp_screen())
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=call_capture) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 4)
        for raw in results:
            self.assertEqual(json.loads(raw)["status"], "success")
        self.assertEqual(self.probe.max_active, 1)


if __name__ == "__main__":
    unittest.main()
