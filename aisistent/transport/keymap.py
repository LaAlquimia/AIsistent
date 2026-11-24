"""Keymap vocabulary for the display bridge (plan G8).

Pure functions — no X connection needed — so the character and
chord rules are unit-testable anywhere. The character rule is
CODEPOINT-based, proven by the slice-0 spike: XK's
string_to_keysym is name-based and returns 0 for characters
whose keysym name differs from the glyph (' ', '/', '-', '.').
"""

# X keysym values for the named vocabulary.
_NAMED_KEYS = {
    "Return": 0xFF0D, "enter": 0xFF0D,
    "Tab": 0xFF09, "Escape": 0xFF1B, "BackSpace": 0xFF08,
    "Delete": 0xFFFF, "space": 0x20,
    "Home": 0xFF50, "End": 0xFF57,
    "Prior": 0xFF55, "Next": 0xFF56,
    "Left": 0xFF51, "Up": 0xFF52, "Right": 0xFF53,
    "Down": 0xFF54,
}
_MODIFIERS = {
    "ctrl": 0xFFE3, "alt": 0xFFE9,
    "shift": 0xFFE1, "super": 0xFFEB,
}


class BridgeError(RuntimeError):
    """Any bridge failure, with the underlying error text."""


def char_keysym(ch: str) -> int:
    """Keysym for one character, by the codepoint rule."""
    if ch == "\n":
        return 0xFF0D
    if ch == "\t":
        return 0xFF09
    o = ord(ch)
    if 0x20 <= o <= 0xFF:
        return o
    return 0x01000000 | o


def resolve_key(name: str) -> tuple[list[int], int]:
    """Resolve a key name or chord to (modifier keysyms, keysym).

    Vocabulary: X keysym names, F1-F35, printable characters as
    themselves; modifiers ctrl/alt/shift/super joined with '+'.
    Unknown names raise BridgeError — never a silent drop.
    """
    parts = [p.strip() for p in name.split("+")]
    mods: list[int] = []
    for part in parts[:-1]:
        low = part.lower()
        if low not in _MODIFIERS:
            raise BridgeError(f"unknown modifier in key: {name!r}")
        mods.append(_MODIFIERS[low])
    token = parts[-1]
    if len(token) == 1:
        return mods, char_keysym(token)
    if token in _NAMED_KEYS:
        return mods, _NAMED_KEYS[token]
    if token.lower() in _MODIFIERS and not mods:
        return [], _MODIFIERS[token.lower()]
    if token.startswith("F") and token[1:].isdigit():
        n = int(token[1:])
        if 1 <= n <= 35:
            return mods, 0xFFBE + (n - 1)
    raise BridgeError(f"unknown key name: {name!r}")
