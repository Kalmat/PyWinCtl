#!/usr/bin/python
"""Tests for the KDE Plasma 6 (KWin) Wayland backend. Run it directly: python test_kwin_backend.py

Backend selection tests run on any Linux. Live tests only run inside a KDE Plasma 6 Wayland session
and open (and close) their own 'kitty' terminal window.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

if sys.platform != "linux":
    print("KWin backend tests: skipped (Linux only)")
    sys.exit(0)

from pywinctl import _pywinctl_linux_kwin as kwin

_ENV_VARS = ("XDG_SESSION_TYPE", "XDG_CURRENT_DESKTOP", "KDE_SESSION_VERSION", "PYWINCTL_LINUX_BACKEND")


def test_backend_selection() -> None:
    cases: list[tuple[dict[str, str], bool]] = [
        ({"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE", "KDE_SESSION_VERSION": "6"}, True),
        ({"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE", "KDE_SESSION_VERSION": "7"}, True),
        ({"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE", "KDE_SESSION_VERSION": "5"}, False),
        ({"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE"}, False),
        ({"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "GNOME"}, False),
        ({"XDG_SESSION_TYPE": "x11", "XDG_CURRENT_DESKTOP": "KDE", "KDE_SESSION_VERSION": "6"}, False),
        ({"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE", "KDE_SESSION_VERSION": "6",
          "PYWINCTL_LINUX_BACKEND": "x11"}, False),
        ({"XDG_SESSION_TYPE": "x11", "XDG_CURRENT_DESKTOP": "GNOME", "PYWINCTL_LINUX_BACKEND": "kwin"}, True),
    ]
    saved = {var: os.environ.get(var) for var in _ENV_VARS}
    try:
        for env, expected in cases:
            for var in _ENV_VARS:
                os.environ.pop(var, None)
            os.environ.update(env)
            assert kwin.isKWinWayland() is expected, f"isKWinWayland() should be {expected} with {env}"
    finally:
        for var, value in saved.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
    print("BACKEND SELECTION: OK")


def test_normalize_id() -> None:
    expected = "{5be5f3ae-5564-4f99-a3a7-80f695bc478d}"
    assert kwin._normalizeId("5BE5F3AE-5564-4f99-a3a7-80f695bc478d") == expected
    assert kwin._normalizeId("{5be5f3ae-5564-4f99-a3a7-80f695bc478d}") == expected
    print("NORMALIZE ID: OK")


def _kwinAvailable() -> bool:
    if not kwin.isKWinWayland() or not shutil.which("kitty"):
        return False
    try:
        kwin._bridge.run("reply(true);")
    except (kwin.KWinError, OSError):
        return False
    return True


def test_live() -> None:
    if not _kwinAvailable():
        print("LIVE TESTS: skipped (needs a KDE Plasma 6 Wayland session and kitty)")
        return

    title = "pywinctl-kwin-test-%d" % time.time_ns()
    proc = subprocess.Popen(["kitty", "--title", title, "sleep", "60"])
    try:
        win = None
        deadline = time.time() + 10
        while win is None and time.time() < deadline:
            time.sleep(0.2)
            found = kwin.getWindowsWithTitle(title)
            win = found[0] if found else None
        assert win is not None, "Test window did not appear"

        # Listing
        assert win in kwin.getAllWindows()
        assert win.title in kwin.getAllTitles()
        assert "kitty" in kwin.getAllAppsNames()
        assert win.getAppName() == "kitty"
        assert win.getPID()
        assert win.getDisplay()

        # Actions
        assert win.activate(wait=True)
        assert kwin.getActiveWindow() == win
        assert win.moveTo(150, 120, wait=True)
        assert win.resizeTo(700, 450, wait=True)
        assert win.box == (150, 120, 700, 450)
        assert kwin.getTopWindowAt(400, 300) == win
        assert win.maximize(wait=True)
        assert win.restore(wait=True)
        assert win.minimize(wait=True)
        assert win.restore(wait=True)
        assert win.alwaysOnTop(True)
        assert win.alwaysOnTop(False)
        assert min(win.getExtraFrameSize()) >= 0
        assert win.close()
        assert not win.isAlive
    finally:
        proc.kill()
    print("LIVE TESTS: OK")


if __name__ == '__main__':
    test_backend_selection()
    test_normalize_id()
    test_live()
