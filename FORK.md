# FORK.md — why this fork exists and what changed

Forked 2026-11-23 from **LaAlquimia/AIsistent** at upstream commit
`4fecab6fd42d8acb360ca76086fe76b5dbd48897` ("Add headless RDP transport via
simple-rdp"), MIT license, upstream version 0.2.0.

## Why fork

This server holds RDP credentials and can act on a desktop. The running code
must be exactly the code that was reviewed — never a moving upstream branch.
The fork was scanned before first use on 2026-11-23: full code read (no
network calls in the package besides the RDP client itself, no telemetry,
credentials only from env/args, nothing persisted) and an OSV vulnerability
sweep of all nine dependencies at then-current versions (zero known
vulnerabilities).

## Changes vs upstream

1. **Click switch (read-only by default).** `inject_rdp_click` is refused
   unless `AISISTENT_ALLOW_CLICK=1` is set in the environment — only the
   exact value `1` opens it; any other value leaves it off. The gate is
   enforced at two layers: `aisistent/action.py` (the tool path) and
   `RDPTransport.click` itself (a backstop, so no internal caller can
   bypass the switch), both driven by `settings.allow_click` in
   `aisistent/config.py`.
2. **GUI transport removed.** `aisistent/transport/gui.py` deleted (it was
   the only module spawning subprocesses, for local-screen capture).
   `create_transport("gui")` raises; the default transport is RDP.
   `disconnect_rdp` now simply tears the RDP session down instead of
   switching to a GUI transport.
3. **Light core dependencies.** Core is now just `mcp` + `Pillow`.
   `torch`/`ultralytics` moved to the `detect` extra, OCR stays in
   `cpu`/`cuda`, `pyautogui` dropped entirely. `platform.py` imported
   torch unconditionally at module level; it now treats torch as optional
   and falls back to CPU device detection without it.
4. **simple-rdp pinned** to `==0.8.10` (the scanned version) in the `rdp`
   and `all` extras. The RDP protocol risk lives in that library, which is
   NOT forked; re-scan before any version bump.
5. **Migrated to the mcp 2.x SDK** (2026-11-23; this replaces an interim
   `mcp<2` pin). Upstream's unbounded `mcp>=1.0` now resolves to mcp 2.x,
   where `mcp.server.fastmcp` was renamed, so upstream code cannot import
   its own server. The fork's server now uses
   `from mcp.server.mcpserver import MCPServer` and pins `mcp==2.3.0`
   exactly — the version the migration was reviewed and tested against
   (EGM-reviewed brief: ../MIGRATION-BRIEF.md). SDK bumps get the same
   re-scan treatment as simple-rdp bumps. Two migration companions ship
   with it: `main()` now connects at startup only when `--host` is given
   (a bare launch serves unconnected, the standard MCP pattern — the old
   `--mode gui` default was removed with the GUI transport), and a
   module-level lock serializes the handlers that share the global
   transport, because mcp 2.x can run sync handlers concurrently where
   v1 serialized them.
   RESIDUAL RISK, named at review: a successful connect builds the
   simple-rdp client inside one asyncio event loop and stores it; later
   capture/click calls run new loops, possibly on other threads. Local
   tests prove the connect path only. The cross-loop question is settled
   at deployment, by the first real connect + capture against a live
   RDP server, read-only, before any reliance.
6. **CredSSP key-form switch** (2026-11-23). Getting a first real
   connect against Yggi's GNOME Remote Desktop took three measured
   corrections, recorded here so nobody re-walks them:
   (a) The first failures were NOT the key at all: the daemon's
   remote-login credential store (`grdctl --system rdp
   set-credentials`) had no entry for the connecting user, so the
   server failed NTLM with SEC_E_NO_CREDENTIALS ("Could not find user
   in SAM database", daemon journal). simple-rdp labels any error at
   that stage "public key verification failed", which misled the
   first diagnosis. Registering the dedicated rdp-ai user with the
   daemon fixed that leg.
   (b) With NTLM passing, the pubKeyAuth hash check failed
   server-side ("Could not verify server's hash"). The SPKI theory —
   CredSSP v5+ defines the hash over the full SubjectPublicKeyInfo
   DER (294 bytes for this cert) while simple-rdp extracts the RAW
   key (270) — was implemented as the shim below and measured WRONG
   for this server: the shim's output is byte-identical to the
   presented cert's SPKI (verified by a direct TLS probe), yet the
   server still rejected it, and with the shim OFF (raw key)
   authentication COMPLETED end to end. This GNOME/FreeRDP build
   verifies the hash over the raw key.
   (c) What the shim is now: `aisistent/transport/rdp.py` defines
   `CredsspSpkiRDPClient`, a subclass overriding
   `_extract_public_key_from_cert` to return
   `subject_public_key_info.dump()` (the complete SPKI DER), selected
   only when the switch is ON. The shim imports `asn1crypto`; it
   arrives as a direct dependency of simple-rdp 0.8.10 itself
   (`Requires-Dist: asn1crypto>=1.5.1`), and the fork ALSO declares
   it directly in the `rdp` extra (`asn1crypto==1.5.1`) so the shim
   never depends on upstream's metadata staying unchanged.
   Switch: `AISISTENT_CREDSSP_SPKI_FIX`, default **OFF** (stock
   raw-key behavior — what Yggi's server accepts); `=1` selects the
   SPKI form for a server that rejects the raw-key proof
   (spec-strict servers, e.g. Windows).
   PIN DISCIPLINE: the shim overrides a PRIVATE method of
   simple-rdp==0.8.10. It is locked to that exact pin — on any
   simple-rdp version bump, re-verify the private method still exists
   with this signature and that upstream has not fixed the extraction
   (if it has, drop the shim), then re-run the acceptance tests.
   Tests: `tests/test_credssp_spki_fix.py` against a committed
   throwaway RSA-2048 fixture cert (`tests/fixtures/test_cert.der`) —
   shim output equals the SPKI DER exactly, 294 vs 270 bytes, switch
   default (off) and explicit-on selection proven.
   Post-auth note: with authentication passing, the connect reached
   the graphics phase and the GNOME daemon closed it: "Client did
   not advertise support for the Graphics Pipeline" — g-r-d requires
   MS-RDPEGFX, which simple-rdp does not implement. That gap is a
   server-choice question, not something this fork patches.
7. **RDP port plumbing** (2026-11-23). Upstream `connect_rdp` had no
   port parameter and simple-rdp's client defaults to 3389, so a
   server on any other port was unreachable. The trial's server is
   xrdp on 127.0.0.1:3391 (3391 chosen so GNOME Remote Desktop keeps
   3389/3390 untouched). `connect_rdp` gains a `port` argument,
   `RDPTransport` passes it to `RDPClient(port=...)`, and
   `settings.rdp_port` reads the `RDP_PORT` env var (default 3389;
   a non-numeric or out-of-range value leaves the default). Ports are
   validated everywhere they enter: an explicit port outside
   1..65535 is rejected with a named error at the tool and the
   transport. The startup path is plumbed too: `main()` accepts
   `--port` for its `--host` startup connection (falling back to
   RDP_PORT, then 3389). Tests: `tests/test_rdp_port.py` — settings
   default/env/garbage/range handling, transport pass-through and
   rejection against a fake client, and the tool layer's mapping.
8. **EGM fork-review fix round** (2026-11-23; a zero-context review of
   this fork returned NO-GO — 1 Blocker, 17 Major, 8 Nit — and every
   finding was resolved in the open; the package and resolutions live
   at ../EGM-PACKAGE-FORK-2026-11-23.md). What changed beyond the
   items folded into changes 1, 6 and 7 above:
   - The SPKI class docstring in `transport/rdp.py` carried the
     disproven theory (that GNOME/FreeRDP verifies the SPKI form) as
     fact. It now records the measured result, matching change 6(b).
   - Both env switches parse as strict whitelists: only the exact
     value `1` turns either on; blank or garbage values fail safe to
     OFF. (The CredSSP switch previously used a blacklist — a blank
     value turned the shim ON.)
   - Transport state on error paths: `set_transport` never lets a
     failing old disconnect block a new session; `disconnect` clears
     the client even when the disconnect itself fails; `connect`
     tears down a live session before replacing it. `disconnect_rdp`
     with no live session now answers honestly ("Not connected")
     instead of claiming success, and `capture_rdp_screen`'s result
     no longer labels the server's own OS as the remote platform.
   - Detection reads only the fork's own weights path:
     upstream's silent fallbacks to weights in sibling projects
     outside this tree (self-operating-computer, OmniParser) are
     removed, and `Settings` no longer computes those external paths.
   - Pin discipline, scoped honestly: the exact pins cover the
     fork's trial surface — core (`mcp==2.3.0`, `Pillow==13.0.0`)
     plus the `rdp` extra (`simple-rdp==0.8.10`,
     `asn1crypto==1.5.1`) — and the version tests assert all four.
     The `detect`/`cpu`/`cuda` extras are NOT pinned and are outside
     the trial; pin them before any use. `mss` was dropped from the
     extras entirely (nothing imports it; the local-capture transport
     it served is deleted).
   - Network guarantee, scoped honestly: with the core + `rdp`
     install, nothing but the RDP connection touches the network.
     The OCR and detection tools are outside the trial and outside
     that guarantee: EasyOCR downloads its model files on first use,
     so those tools are not network-clean until their models are
     pre-provisioned.
   - Test honesty: the concurrency test now exercises a live (fake)
     transport and fails if the serialization lock is removed; the
     protocol-session test runs with a scrubbed environment and aims
     its refused connect at a dead high port, never a real server;
     the session has a total deadline, not just per-read timeouts.
   - The fork carries its own version from this round: 0.2.1
     (pyproject + `__version__`), so logs and installs can no longer
     be confused with unmodified upstream 0.2.0. Upstream's
     "aistent" typos in install instructions are corrected.

## Change 9 — logon flags fix (found live, 2026-11-23)

- The xrdp trial failed at logon: xrdp logged "received wrong flags,
  likely decrypt not working" and dropped the connection, with TLS
  negotiated and crypt_level at high AND at none. The encryption
  theory behind the crypt_level change was WRONG — the correction is
  recorded here in the open. xrdp's own source (libxrdp/xrdp_sec.c,
  xrdp_sec_process_logon_info, v0.10.6) shows the check: the
  TS_INFO_PACKET flags field must carry every RDP_LOGON_NORMAL bit
  (0x33); the "decrypt" wording is historical (with classic RDP
  security, a bad decrypt garbles that field first).
- Root cause: simple-rdp 0.8.10's build_client_info_pdu defaults the
  info flags to 0x53, which omits INFO_MAXIMIZESHELL (0x20):
  0x53 & 0x33 = 0x13 != 0x33.
- Fix: `_ForkClientBase` in transport/rdp.py overrides
  _send_client_info, replicating upstream's method with the missing
  bit added; both client classes (stock and SPKI) inherit it, and
  _client_class returns the fork base when the SPKI switch is off.
  Locked to simple-rdp==0.8.10 — re-verify on any bump; drop the
  override if upstream fixes its default (a test pins upstream's
  current default so the bump surfaces it).
- Tests: tests/test_logon_flags.py (3 tests). Suite: 37 tests.

## Change 10 — disconnect teardown survives the closed connect loop (2026-11-23)

- Trial attempt 4 connected, captured, and refused the click, but
  disconnect_rdp reported an error: the transport drives the client
  through one asyncio.run per operation, so the TLS transport
  belongs to the connect call's event loop, which is closed by
  disconnect time. Upstream's disconnect closes the writer,
  asyncio's SSL layer schedules its shutdown timeout on the dead
  loop, and RuntimeError ("Event loop is closed") escapes — while
  the session is in fact over (xrdp's journal showed the client
  gone; no session remained).
- Fix: `_ForkClientBase.disconnect()` swallows exactly that
  artifact — marks the client disconnected, drops the stream
  references, closes the raw socket directly (best effort; a socket
  close does not touch the event loop). Any other error still
  propagates: honest failures stay failures.
- Tests: tests/test_disconnect_teardown.py (3 tests). Suite: 40 tests.

## Acceptance tests

`tests/test_trial_trim.py` — click refused by default, click gate opens with
the switch, GUI transport gone, RDP transport present, server imports, and
the click switch's env parsing (only "1" opens it).
`tests/test_mcp2_migration.py` — the mcp 2.x migration (change 5) and the
pin set: exact versions asserted (mcp, Pillow, simple-rdp), seven tools
registered, a bare-launch stdio protocol session in a scrubbed environment,
concurrent error-path calls, and the transport-serialization test (T7).
`tests/test_credssp_spki_fix.py` — the CredSSP key-form switch (change 6):
extraction equals the fixture cert's SPKI DER, longer than the raw key,
switch default (off), blank/garbage stay off, and client selection.
`tests/test_rdp_port.py` — the port plumbing (change 7): settings
default 3389, RDP_PORT override and range handling, transport
pass-through and rejection, and the connect_rdp tool's port mapping.
`tests/test_logon_flags.py` — the logon-flags fix (change 9):
upstream's default flags pinned as failing xrdp's 0x33 mask, and both
fork client classes emit flags that satisfy it.
`tests/test_disconnect_teardown.py` — the disconnect fix
(change 10): the closed-loop artifact is swallowed with state
cleaned up and the raw socket closed; every other error propagates.
Run: `python -m unittest discover -s tests -v` in a venv built with the
`rdp` extra (`pip install ".[rdp]"`). With only the light core deps
installed, the simple-rdp-dependent tests skip instead of passing, and
the suite is green with skips — the full evidence requires the extra.

## Upstream pulls

Only by deliberate action: diff against the pinned upstream commit, re-run
the scan (code read + OSV sweep), then merge. Never auto-update.
