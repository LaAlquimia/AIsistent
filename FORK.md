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

## Acceptance tests

`tests/test_trial_trim.py` — click refused by default, click gate opens with
the switch, GUI transport gone, RDP transport present, server imports.
Run: `python -m unittest discover -s tests -v` with the light deps installed.

## Upstream pulls

Only by deliberate action: diff against the pinned upstream commit, re-run
the scan (code read + OSV sweep), then merge. Never auto-update.
