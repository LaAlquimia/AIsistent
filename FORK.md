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
   unless `AISISTENT_ALLOW_CLICK=1` is set in the environment. Gate lives in
   `aisistent/action.py`, driven by `settings.allow_click` in
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
   only when the switch is ON. `asn1crypto` needed no new dependency
   entry: it is already a direct dependency of simple-rdp 0.8.10
   itself (`Requires-Dist: asn1crypto>=1.5.1`).
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
   a non-numeric value leaves the default). Tests:
   `tests/test_rdp_port.py` — settings default/env/garbage handling
   and transport pass-through against a fake client.

## Acceptance tests

`tests/test_trial_trim.py` — click refused by default, click gate opens with
the switch, GUI transport gone, RDP transport present, server imports.
`tests/test_credssp_spki_fix.py` — the CredSSP key-form switch (change 6):
extraction equals the fixture cert's SPKI DER, longer than the raw key,
switch default (off) and client selection.
`tests/test_rdp_port.py` — the port plumbing (change 7): settings
default 3389, RDP_PORT override, transport pass-through.
Run: `python -m unittest discover -s tests -v` with the light deps installed.

## Upstream pulls

Only by deliberate action: diff against the pinned upstream commit, re-run
the scan (code read + OSV sweep), then merge. Never auto-update.
