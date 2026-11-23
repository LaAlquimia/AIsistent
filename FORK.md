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
5. **mcp SDK pinned below 2.0** (`mcp>=1.0,<2.0`). Found by the acceptance
   tests on day one: upstream's unbounded `mcp>=1.0` now resolves to mcp
   2.x, where `mcp.server.fastmcp` was renamed and upstream code cannot
   import its own server. Migrating to the v2 API is a separate deliberate
   job, not part of the trial trim.

## Acceptance tests

`tests/test_trial_trim.py` — click refused by default, click gate opens with
the switch, GUI transport gone, RDP transport present, server imports.
Run: `python -m unittest discover -s tests -v` with the light deps installed.

## Upstream pulls

Only by deliberate action: diff against the pinned upstream commit, re-run
the scan (code read + OSV sweep), then merge. Never auto-update.
