# Postmortem — giving an AI a usable desktop: the trial, the verdict, and the FreeRDP transport

This fork began as an experiment: can an MCP server drive a
real desktop on a Fedora Silverblue host — screenshots,
mouse, keyboard — well enough for an AI to do general
computer work there? The answer is yes, but not with the
client library the project ships. This document is the whole
story: what was tried, what failed and why, and what this
fork changes as a result. It accompanies the pull request.

## Safety shape, set before any code

The desktop session runs as a dedicated scoped account (own
group only, no sudo, a home directory the other services on
the host cannot be reached from, and which cannot reach
theirs). The RDP listener binds localhost only. Input
injection sits behind explicit switches, off by default.

## The trial: three session types, one verdict

The upstream code was read in full and its dependencies
checked before anything ran. Its bundled client library
(simple-rdp) then met the host:

- **GNOME's RDP server** requires the MS-RDPEGFX graphics
  pipeline; the library does not implement it. Dead end.
- **xrdp + Xorg**: the session ran (proven server-side), the
  client received black frames and a pointer — it cannot
  consume the offscreen blits that path sends.
- **xrdp + Xvnc**: server-composited frames; the client
  received exactly one color — pure black, every pixel.

The server side was complete at every step; the client
cannot render any paint path this host offers. Two smaller
findings from the same rounds: the library's logon flags omit
a bit xrdp requires (INFO_MAXIMIZESHELL; fork change 9), and
desktop sessions persist across client disconnects — which
became a design feature: disconnect ends the client, never
the session.

## The proof that chose the direction

The standard FreeRDP client, pointed at the same Xvnc
session, rendered it completely on the first attempt:
258,733 non-black pixels (12.5%), 400 distinct colors,
against the bundled library's 0 pixels / 1 color — measured
against a pass bar stated before the run. Decision: keep the
project's MCP surface and safety gates; replace the transport
with one that drives FreeRDP.

## The build

Planned before code, reviewed by a zero-context pre-build
pass (16 findings, all resolved in the plan), built in
slices with tests first:

- **Transport + display bridge.** xfreerdp runs as a
  subprocess on a private Xvfb display. The bridge is the
  only module that talks X: capture by root GetImage, input
  by XTEST. Key mapping is codepoint-based (measured: the
  name-based lookup fails on space, slash, minus, period);
  unmapped keysyms ride a donor keycode remapped for the
  press.
- **Gates.** Clicks and keyboard are gated independently,
  enforced in the action layer and backstopped in the
  transport. Audit logs record payload lengths, never
  content.
- **Honest connect.** Connect returns only when a frame
  passes a render bar (>5% non-black, >50 distinct colors)
  and is not the server's login dialog, whose measured
  signature the guard matches explicitly. A session that
  stays blank gets one pointer nudge (blanked displays
  repaint on activity); a timeout saves its last frame as
  evidence.
- **Credentials** reach the client as the /p argument — the
  plan's named fallback, taken after the stdin route was
  measured not to deliver (below). That exposes them to the
  local process listing for the client's lifetime: accepted
  for a localhost connection to a disposable scoped account,
  flagged in the code and docs for revisiting before any
  non-trial use. They are never placed in the child's
  environment and never logged.
- **One switch table.** Every changeable value (backend
  selection, session size, display, timeouts, clipboard,
  gates) is defined once in config. The legacy backend
  remains available behind the switch.

## Acceptance: four runs, three honest failures

The live suite runs against a real xrdp/Xvnc host through
the MCP tools only.

- **Run 1** "passed" its render check onto the server's
  login screen — no session ever existed. Bisect proved the
  credential feed had never arrived: an earlier probe had
  concluded the stdin credential route worked, and that
  conclusion was a misread (a rejected password and an empty
  submission produce the same screen). Fixes: the /p route, a
  login-dialog guard, and a backwards color-count read that
  had made the render bar's non-black term always 100%. The
  plan document carries the correction, dated, in the open.
- **Run 2**: 8 of 9. The failing typing test typed without
  clicking first — keystrokes go to the session's focused
  window, and a fresh terminal is not guaranteed focus. The
  sibling test that clicked first passed with identical
  typing. The test now does what a person does; its pass
  condition is unchanged.
- **Run 3** timed out at connect against a session proven
  healthy afterward — the poll never saw a painted frame and
  kept no picture. Hence the wake nudge and the saved
  evidence frame above.
- **Run 4: all live tests pass** — the rendered desktop
  measured from the frame itself, typed commands proven by
  files they created on disk, both gates proven shut, the
  session reattached with identical process IDs, and a
  browser opened on a planted page through the tools alone.
  The backend default then flipped to FreeRDP. The unit suite
  stands at 70 tests, green on two machines.

## The Silverblue side

The host is Fedora Silverblue: the OS is image-based and
nothing installs "normally." System pieces with no Flatpak
route (xrdp, TigerVNC, FreeRDP, Xvfb, a window manager, a
terminal) were layered with rpm-ostree, each landing on a
reboot. Two notes for anyone repeating this: the layering
tool's local-file reader rejected a signature-valid RPM that
every other tool read fine (installing from the vendor's
repository worked), and applications belong in Flatpak where
one exists — the browser installed for this desktop at the
end went in as a Flatpak, no layer, no reboot.

## Known gaps, named

- No tool ends a server-side session; disconnect detaches
  the client only, by design, and session cleanup is the
  operator's.
- The /p credential exposure described above.
- The upstream OCR helper downloads model weights on first
  use, which is outside any no-network claim for the server
  as a whole.

## What the pull request contains

The MCP SDK migration prepared earlier in this fork, the
FreeRDP transport with its display bridge and key mapping,
the keyboard tools behind their gate, the logon-flags fix,
and the connect-honesty machinery (render bar, login-dialog
guard, wake nudge, evidence frame) — each change documented
in FORK.md with its reason and its measurements.
