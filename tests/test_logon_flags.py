"""Acceptance tests for the logon-flags fix (FORK.md change 9).

Problem (measured on Yggi, 2026-11-23; xrdp source libxrdp/xrdp_sec.c):
xrdp's xrdp_sec_process_logon_info requires every RDP_LOGON_NORMAL bit
(0x33) in the TS_INFO_PACKET flags field — its first check of the
packet — and drops the connection otherwise, logging "received wrong
flags, likely decrypt not working". simple-rdp 0.8.10's
build_client_info_pdu defaults the flags to 0x53, which lacks
INFO_MAXIMIZESHELL (0x20): 0x53 & 0x33 = 0x13 != 0x33.

Pass conditions:
1. Upstream's default flags do NOT satisfy 0x33 (pins the defect; if a
   future simple-rdp fixes its default, this fails and the fork's
   override should be dropped).
2. The fork client's _send_client_info emits a Client Info PDU whose
   flags satisfy 0x33, including INFO_MAXIMIZESHELL.
3. Both client classes the fork can select carry the fix (they share
   the _ForkClientBase override).

Run with:  python -m unittest discover -s tests -v
"""

import asyncio
import struct
import unittest

from aisistent.transport import rdp as rdp_mod

RDP_LOGON_NORMAL = 0x33


def _flags_of(pdu_with_security_header: bytes) -> int:
    # security header (4) + code page (4) + flags (4)
    return struct.unpack("<I", pdu_with_security_header[8:12])[0]


@unittest.skipUnless(rdp_mod._HAS_SIMPLE_RDP, "simple-rdp not installed")
class TestLogonFlags(unittest.TestCase):
    def test_upstream_default_flags_miss_the_mask(self):
        from simple_rdp.pdu import build_client_info_pdu

        pdu = build_client_info_pdu(username="u", password="p")
        # build_client_info_pdu returns the bare info packet:
        # code page (4) + flags (4)
        flags = struct.unpack("<I", pdu[4:8])[0]
        self.assertNotEqual(flags & RDP_LOGON_NORMAL, RDP_LOGON_NORMAL)

    def _capture_sent_info(self, client_cls):
        client = object.__new__(client_cls)
        client._domain = ""
        client._username = "u"
        client._password = "p"
        client._show_wallpaper = False
        client._io_channel_id = 1004
        sent = {}

        async def fake_send(data, channel_id):
            sent["data"] = data
            sent["channel_id"] = channel_id

        client._send_mcs_data = fake_send
        asyncio.run(client._send_client_info())
        return sent["data"]

    def test_fork_client_flags_satisfy_xrdp_mask(self):
        from simple_rdp.pdu import INFO_MAXIMIZESHELL

        data = self._capture_sent_info(rdp_mod._ForkClientBase)
        flags = _flags_of(data)
        self.assertEqual(flags & RDP_LOGON_NORMAL, RDP_LOGON_NORMAL)
        self.assertTrue(flags & INFO_MAXIMIZESHELL)

    def test_spki_client_carries_the_fix_too(self):
        data = self._capture_sent_info(rdp_mod.CredsspSpkiRDPClient)
        flags = _flags_of(data)
        self.assertEqual(flags & RDP_LOGON_NORMAL, RDP_LOGON_NORMAL)


if __name__ == "__main__":
    unittest.main()
