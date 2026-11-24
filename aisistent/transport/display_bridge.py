"""Display bridge — the only module that talks X.

Owns the private virtual display (Xvfb) the FreeRDP client
paints into, and injects keyboard/pointer input into it via
XTEST (python-xlib; the import is lazy, so the package loads
without it and fails loudly only when the bridge is used).
The keymap rules live in keymap.py; the remap/settle and
no-range-probing rules were proven by the slice-0 spike
(plan S0b) and are marked where they apply below.
"""

import os
import subprocess
import time

from PIL import Image

from .keymap import BridgeError, char_keysym, resolve_key

__all__ = [
    "BridgeError",
    "XlibDisplayBridge",
    "char_keysym",
    "resolve_key",
]

_REMAP_SETTLE_S = 0.35
_TYPE_CAP = 4096

# Donor candidates for the remap path, in preference order:
# Scroll_Lock, Caps_Lock, Num_Lock, F13.
_DONOR_KEYSYMS = (0xFF14, 0xFFE5, 0xFF7F, 0xFFCA)


class XlibDisplayBridge:
    """python-xlib bridge: one Xvfb display, its client, its X."""

    def __init__(self, width: int = 1920, height: int = 1080,
                 display_spec: str = "auto"):
        self._width = width
        self._height = height
        self._spec = display_spec
        self._num: int | None = None
        self._xvfb: subprocess.Popen | None = None
        self._clients: dict[int, subprocess.Popen] = {}
        self._d = None
        self._xtest = None
        self._donor: int | None = None

    # -- lifecycle -------------------------------------------------

    def _load_x(self):
        if self._d is not None:
            return
        try:
            from Xlib import display as xdisplay
            from Xlib.ext import xtest
        except ImportError as e:
            raise BridgeError(
                "python-xlib not installed. "
                "Run: pip install aisistent[rdp]"
            ) from e
        self._xtest = xtest
        try:
            self._d = xdisplay.Display(f":{self._num}")
        except Exception as e:
            raise BridgeError(f"cannot open display :{self._num}: {e}") from e

    def start_display(self) -> int:
        if self._spec == "auto":
            num = next(
                (n for n in range(90, 100)
                 if not os.path.exists(f"/tmp/.X{n}-lock")),
                None,
            )
            if num is None:
                raise BridgeError("no free display in :90-:99")
        else:
            try:
                num = int(self._spec)
            except ValueError:
                raise BridgeError(
                    f"bad AISISTENT_DISPLAY value: {self._spec!r}")
        self._num = num
        self._xvfb = subprocess.Popen(
            ["Xvfb", f":{num}", "-screen", "0",
             f"{self._width}x{self._height}x24"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 5.0
        while time.time() < deadline:
            try:
                self._load_x()
                return num
            except BridgeError:
                self._d = None
                time.sleep(0.2)
        raise BridgeError(f"Xvfb :{num} did not come up")

    def stop_display(self) -> None:
        for pid in list(self._clients):
            self.kill_client(pid)
        if self._d is not None:
            try:
                self._d.close()
            except Exception:
                pass
            self._d = None
        if self._xvfb is not None:
            self._xvfb.terminate()
            try:
                self._xvfb.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._xvfb.kill()
            self._xvfb = None

    # -- client processes ------------------------------------------

    def spawn_client(self, argv, log_file=None) -> int:
        env = dict(os.environ)
        env["DISPLAY"] = f":{self._num}"
        out = subprocess.DEVNULL
        err = subprocess.DEVNULL
        handle = None
        if log_file:
            handle = open(log_file, "ab")
            out = err = handle
        proc = subprocess.Popen(
            argv, env=env, stdin=subprocess.PIPE,
            stdout=out, stderr=err,
        )
        self._clients[proc.pid] = proc
        return proc.pid

    def write_client_stdin(self, pid: int, text: str) -> None:
        proc = self._clients.get(pid)
        if proc is None or proc.stdin is None:
            raise BridgeError(f"no stdin for client pid {pid}")
        proc.stdin.write(text.encode("utf-8"))
        proc.stdin.flush()

    def client_alive(self, pid: int) -> bool:
        proc = self._clients.get(pid)
        return proc is not None and proc.poll() is None

    def kill_client(self, pid: int) -> None:
        proc = self._clients.pop(pid, None)
        if proc is None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

    # -- windows ----------------------------------------------------

    def client_window(self, pid: int) -> int:
        self._load_x()
        from Xlib import X
        d = self._d
        root = d.screen().root
        pid_atom = d.intern_atom("_NET_WM_PID")
        best = None
        best_area = 0
        stack = [root]
        while stack:
            win = stack.pop()
            try:
                prop = win.get_full_property(pid_atom, X.AnyPropertyType)
                if prop and list(prop.value) == [pid]:
                    return win.id
                geom = win.get_geometry()
                area = geom.width * geom.height
                if area > best_area:
                    best, best_area = win, area
                stack.extend(win.query_tree().children)
            except Exception:
                continue
        half = self._width * self._height / 2
        if best is not None and best_area > half:
            return best.id
        raise BridgeError(f"no window found for client pid {pid}")

    def focus_window(self, wid: int) -> None:
        self._load_x()
        from Xlib import X
        win = self._d.create_resource_object("window", wid)
        win.set_input_focus(X.RevertToParent, X.CurrentTime)
        win.configure(stack_mode=X.Above)
        self._d.sync()

    # -- capture ------------------------------------------------------

    def grab_frame(self) -> Image.Image:
        self._load_x()
        from Xlib import X
        root = self._d.screen().root
        try:
            raw = root.get_image(
                0, 0, self._width, self._height,
                X.ZPixmap, 0xFFFFFFFF)
        except Exception as e:
            raise BridgeError(f"frame grab failed: {e}") from e
        return Image.frombytes(
            "RGB", (self._width, self._height),
            raw.data, "raw", "BGRX")

    # -- input --------------------------------------------------------

    def _press_keysym(self, ks: int) -> None:
        self._load_x()
        from Xlib import X
        d = self._d
        cands = list(d.keysym_to_keycodes(ks))
        if not cands:
            self._press_via_donor(ks)
            return
        kc, idx = cands[0]
        shift_kc = d.keysym_to_keycode(0xFFE1)
        shifted = idx % 2 == 1
        if shifted:
            self._xtest.fake_input(d, X.KeyPress, shift_kc)
        self._xtest.fake_input(d, X.KeyPress, kc)
        self._xtest.fake_input(d, X.KeyRelease, kc)
        if shifted:
            self._xtest.fake_input(d, X.KeyRelease, shift_kc)
        d.sync()

    def _press_via_donor(self, ks: int) -> None:
        from Xlib import X
        d = self._d
        if self._donor is None:
            for cand_ks in _DONOR_KEYSYMS:
                kc = d.keysym_to_keycode(cand_ks)
                if kc:
                    self._donor = kc
                    break
            if self._donor is None:
                raise BridgeError(
                    f"no donor keycode available for keysym 0x{ks:x}")
        orig = d.get_keyboard_mapping(self._donor, 1)
        d.change_keyboard_mapping(self._donor, [[ks]])
        d.sync()
        self._xtest.fake_input(d, X.KeyPress, self._donor)
        self._xtest.fake_input(d, X.KeyRelease, self._donor)
        d.sync()
        # Settle BEFORE restoring, or the restore wins and the
        # press reads back as the donor's own keysym (spike S0b).
        time.sleep(_REMAP_SETTLE_S)
        d.change_keyboard_mapping(self._donor, orig)
        d.sync()

    def key(self, name: str) -> None:
        mods, ks = resolve_key(name)
        self._load_x()
        from Xlib import X
        d = self._d
        mod_kcs = []
        for mks in mods:
            kc = d.keysym_to_keycode(mks)
            if not kc:
                raise BridgeError(f"modifier keysym unmapped: 0x{mks:x}")
            mod_kcs.append(kc)
        for kc in mod_kcs:
            self._xtest.fake_input(d, X.KeyPress, kc)
        try:
            self._press_keysym(ks)
        finally:
            for kc in reversed(mod_kcs):
                self._xtest.fake_input(d, X.KeyRelease, kc)
            d.sync()

    def type_text(self, text: str) -> None:
        if len(text) > _TYPE_CAP:
            raise BridgeError(
                f"type_text is capped at {_TYPE_CAP} characters")
        for ch in text:
            self._press_keysym(char_keysym(ch))

    def pointer_move(self, x: int, y: int) -> None:
        self._load_x()
        from Xlib import X
        root = self._d.screen().root
        self._xtest.fake_input(
            self._d, X.MotionNotify, 0, X.CurrentTime, root.id, x, y)
        self._d.sync()

    def pointer_down(self, button: int) -> None:
        self._load_x()
        from Xlib import X
        self._xtest.fake_input(self._d, X.ButtonPress, button)
        self._d.sync()

    def pointer_up(self, button: int) -> None:
        self._load_x()
        from Xlib import X
        self._xtest.fake_input(self._d, X.ButtonRelease, button)
        self._d.sync()
