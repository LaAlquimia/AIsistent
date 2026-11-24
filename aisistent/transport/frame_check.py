"""Frame checks for the FreeRDP transport: is it a desktop yet?

Pure functions over PIL images, split out of freerdp.py for
the line cap and unit-tested through the transport tests.
"""

# The render bar, pre-stated by the FreeRDP proof test: a frame
# counts as a rendered desktop only past both thresholds. The
# trial's black frames measured 0-15 non-black pixels / 1 color;
# the bare desktop measured 12.5% / 400 colors.
_RENDER_MIN_NONBLACK = 0.05
_RENDER_MIN_COLORS = 50


def _counts(rgb) -> dict:
    """{color: count} from PIL getcolors' (count, color) pairs."""
    return {color: n for n, color in rgb.getcolors(
        rgb.width * rgb.height) or []}


def frame_passes(img) -> bool:
    rgb = img.convert("RGB")
    total = rgb.width * rgb.height
    counts = _counts(rgb)
    if len(counts) <= _RENDER_MIN_COLORS:
        return False
    nonblack = total - counts.get((0, 0, 0), 0)
    return nonblack / total > _RENDER_MIN_NONBLACK


def frame_is_blank(img) -> bool:
    """Essentially nothing on screen (<0.1% non-black).

    Distinct from failing the render bar: a login dialog or a
    dark desktop fails the bar without being blank. Blank is
    the screen-saver / not-yet-painting state, and the only
    state the connect poll nudges (change 14).
    """
    rgb = img.convert("RGB")
    total = rgb.width * rgb.height
    nonblack = total - _counts(rgb).get((0, 0, 0), 0)
    return nonblack / total < 0.001


def looks_like_login_dialog(img) -> bool:
    """The xrdp login screen's measured signature (change 13).

    Sampled from real captures 2026-11-23: a uniform backdrop
    (the three sample points identical, that color covering
    over half the frame) with the white dialog box at the
    center (center pixel near-white). The session desktop —
    dark terminal, dark backdrop, non-uniform corners — does
    not match. The guard only ever turns a would-be success
    into a loud failure, never the reverse.
    """
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    backdrop = px[int(w * 0.02), int(h * 0.02)]
    if px[int(w * 0.98), int(h * 0.02)] != backdrop:
        return False
    if px[int(w * 0.5), int(h * 0.05)] != backdrop:
        return False
    center = px[w // 2, h // 2]
    if not all(c >= 235 for c in center):
        return False
    return _counts(rgb).get(backdrop, 0) / (w * h) > 0.5
