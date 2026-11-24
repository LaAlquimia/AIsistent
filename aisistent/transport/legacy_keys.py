"""Translate the fork's key vocabulary to simple-rdp's names.

The surface vocabulary is X keysym names + '+' chords
(keymap.py); simple-rdp speaks lowercase friendly names and
builds chords from hold/release modes. Pure translation —
unit-tested without a client.
"""

from .keymap import resolve_key

_KEY_NAMES = {
    0xFF0D: "enter", 0xFF09: "tab", 0xFF1B: "escape",
    0xFF08: "backspace", 0xFFFF: "delete", 0x20: "space",
    0xFF50: "home", 0xFF57: "end",
    0xFF55: "pageup", 0xFF56: "pagedown",
    0xFF51: "left", 0xFF52: "up", 0xFF53: "right",
    0xFF54: "down",
}
_MOD_NAMES = {
    0xFFE3: "ctrl", 0xFFE9: "alt",
    0xFFE1: "shift", 0xFFEB: "win",
}


def _key_name(ks: int) -> str:
    if ks in _KEY_NAMES:
        return _KEY_NAMES[ks]
    if 0xFFBE <= ks <= 0xFFC9:  # F1-F12: the client's map ends there
        return f"f{ks - 0xFFBE + 1}"
    if 0x20 <= ks <= 0x7E:
        return chr(ks)
    raise ValueError(
        f"key has no simple-rdp equivalent: keysym 0x{ks:x}")


def simple_rdp_key_plan(name: str) -> list[tuple[str, str]]:
    """(key, mode) steps for one surface key name or chord."""
    mods, ks = resolve_key(name)
    plan = [(_MOD_NAMES[m], "hold") for m in mods]
    plan.append((_key_name(ks), "press"))
    plan += [(_MOD_NAMES[m], "release") for m in reversed(mods)]
    return plan
