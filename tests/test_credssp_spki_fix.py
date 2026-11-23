"""Acceptance tests for the CredSSP SPKI shim (FORK.md change 6).

Problem (measured on Yggi, 2026-11-23): simple-rdp 0.8.10's
RDPClient._extract_public_key_from_cert returns the RAW public key
(270 bytes for an RSA-2048 cert), but CredSSP v5+ pubKeyAuth is defined
over the full SubjectPublicKeyInfo DER (294 bytes). GNOME/FreeRDP
rejects the client's proof before credentials are ever sent.

Pass conditions:
1. The shim's extraction equals the certificate's SPKI DER exactly.
2. The shim's output is longer than the upstream raw-key extraction
   (294 vs 270 bytes on the committed RSA-2048 fixture).
3. The switch AISISTENT_CREDSSP_SPKI_FIX defaults OFF (the measured
   behavior of Yggi's GNOME/FreeRDP server), only the exact value
   "1" turns it on — a blank or garbage value stays OFF — and
   RDPTransport's client-class selection follows the switch.

The certificate is a committed fixture (tests/fixtures/test_cert.der,
a throwaway self-signed RSA-2048 cert) — no network, no local keys.
Run with:  python -m unittest discover -s tests -v
"""

import os
import unittest
from pathlib import Path
from unittest import mock

from aisistent.config import Settings, settings
from aisistent.transport import rdp as rdp_mod

FIXTURE = Path(__file__).parent / "fixtures" / "test_cert.der"


def _spki_der(cert_der: bytes) -> bytes:
    from asn1crypto.x509 import Certificate

    cert = Certificate.load(cert_der)
    return cert["tbs_certificate"]["subject_public_key_info"].dump()


def _raw_key_upstream(cert_der: bytes) -> bytes:
    """Replicates simple-rdp 0.8.10's extraction, for comparison."""
    from asn1crypto.x509 import Certificate

    cert = Certificate.load(cert_der)
    pubkey = cert["tbs_certificate"]["subject_public_key_info"][
        "public_key"
    ].contents
    if pubkey[0] == 0x00:
        pubkey = pubkey[1:]
    return bytes(pubkey)


@unittest.skipUnless(rdp_mod._HAS_SIMPLE_RDP, "simple-rdp not installed")
class TestSpkiExtraction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cert_der = FIXTURE.read_bytes()
        # Stateless method: build the client without running __init__.
        cls.client = object.__new__(rdp_mod.CredsspSpkiRDPClient)

    def test_shim_returns_full_spki_der(self):
        got = self.client._extract_public_key_from_cert(self.cert_der)
        self.assertEqual(got, _spki_der(self.cert_der))

    def test_shim_longer_than_raw_key(self):
        got = self.client._extract_public_key_from_cert(self.cert_der)
        raw = _raw_key_upstream(self.cert_der)
        self.assertGreater(len(got), len(raw))
        # Measured on the fixture: raw RSA key 270, SPKI DER 294.
        self.assertEqual((len(raw), len(got)), (270, 294))


class TestSpkiSwitch(unittest.TestCase):
    def setUp(self):
        self._saved = settings.credssp_spki_fix

    def tearDown(self):
        settings.credssp_spki_fix = self._saved

    def test_switch_defaults_off(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("AISISTENT_CREDSSP_SPKI_FIX", None)
            self.assertFalse(Settings().credssp_spki_fix)

    def test_switch_explicit_on(self):
        with mock.patch.dict(
            os.environ, {"AISISTENT_CREDSSP_SPKI_FIX": "1"}
        ):
            self.assertTrue(Settings().credssp_spki_fix)

    def test_switch_blank_stays_off(self):
        with mock.patch.dict(
            os.environ, {"AISISTENT_CREDSSP_SPKI_FIX": ""}
        ):
            self.assertFalse(Settings().credssp_spki_fix)

    def test_switch_garbage_stays_off(self):
        with mock.patch.dict(
            os.environ, {"AISISTENT_CREDSSP_SPKI_FIX": "enabled"}
        ):
            self.assertFalse(Settings().credssp_spki_fix)

    @unittest.skipUnless(rdp_mod._HAS_SIMPLE_RDP, "simple-rdp not installed")
    def test_transport_client_selection_follows_switch(self):
        settings.credssp_spki_fix = True
        self.assertIs(rdp_mod._client_class(), rdp_mod.CredsspSpkiRDPClient)
        settings.credssp_spki_fix = False
        self.assertIs(rdp_mod._client_class(), rdp_mod._RDPClientBase)


if __name__ == "__main__":
    unittest.main()
