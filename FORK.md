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
6. **CredSSP SPKI shim** (2026-11-23). The first real connect against
   Yggi's GNOME Remote Desktop failed with "CredSSP public key
   verification failed" — measured, not guessed: the diagnostic run
   (job dd91740caed7, dummy credentials, debug logging) showed the
   server negotiates CredSSP version 6, the client runs the v5+
   hash-based pubKeyAuth, and the public key it feeds that hash is
   **270 bytes**. Root cause, read in simple-rdp 0.8.10's own source:
   `RDPClient._extract_public_key_from_cert` returns the RAW public
   key contents, but CredSSP v5+ pubKeyAuth is defined over the full
   **SubjectPublicKeyInfo DER (294 bytes** for Yggi's RSA-2048 cert).
   The server verifies the client's proof, gets a mismatch, and
   answers with an error code at the pubKeyAuth step — before
   credentials are ever sent, so the password was never implicated.
   Fix: `aisistent/transport/rdp.py` defines `CredsspSpkiRDPClient`, a
   subclass overriding that one method to return
   `subject_public_key_info.dump()` (the complete SPKI DER), and
   `RDPTransport` connects with it. `asn1crypto` needed no new
   dependency entry: it is already a direct dependency of
   simple-rdp 0.8.10 itself (`Requires-Dist: asn1crypto>=1.5.1`), and
   it is the same library upstream's broken method uses.
   Switch: `AISISTENT_CREDSSP_SPKI_FIX`, default **ON** (the library
   is broken without it); `=0` (or false/no/off) selects the stock
   upstream client class cleanly.
   PIN DISCIPLINE: the shim overrides a PRIVATE method of
   simple-rdp==0.8.10. It is locked to that exact pin — on any
   simple-rdp version bump, re-verify the private method still exists
   with this signature and that upstream has not fixed the extraction
   (if it has, drop the shim), then re-run the acceptance tests.
   Tests: `tests/test_credssp_spki_fix.py` against a committed
   throwaway RSA-2048 fixture cert (`tests/fixtures/test_cert.der`) —
   shim output equals the SPKI DER exactly, 294 vs 270 bytes, switch
   default/selection proven.

## Acceptance tests

`tests/test_trial_trim.py` — click refused by default, click gate opens with
the switch, GUI transport gone, RDP transport present, server imports.
`tests/test_credssp_spki_fix.py` — the CredSSP SPKI shim (change 6):
extraction equals the fixture cert's SPKI DER, longer than the raw key,
switch default and client selection.
Run: `python -m unittest discover -s tests -v` with the light deps installed.

## Upstream pulls

Only by deliberate action: diff against the pinned upstream commit, re-run
the scan (code read + OSV sweep), then merge. Never auto-update.
