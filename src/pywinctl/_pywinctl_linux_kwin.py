#!/usr/bin/python
"""
KDE Plasma (KWin) on Wayland backend.

Wayland does not allow clients to inspect or control other clients' windows. On KDE Plasma, however,
the compositor (KWin) can be scripted: this module loads a tiny KWin script through KWin's D-Bus
interface (org.kde.kwin.Scripting), the script reads / changes the requested window(s) and sends the
result back to us with callDBus(). This works for all windows, including native Wayland ones.

Requirements: KDE Plasma 6 (KWin 6) and the pure-Python 'jeepney' D-Bus module.
"""
from __future__ import annotations

import sys

if sys.platform != "linux":
    raise OSError(f"Cannot import {__name__} on {sys.platform}")

import itertools
import json
import os
import re
import tempfile
import threading
import time
from typing import Any, cast

from pywinbox import Box, PyWinBox, Rect, pointInBox

from ._main import _WINDATA, _WINDICT, BaseWindow, Re, _WatchDog

WAIT_ATTEMPTS = 10
WAIT_DELAY = 0.025  # Will be progressively increased on every retry
KWIN_TIMEOUT = 2.0  # Seconds to wait for KWin to answer

_REPLY_PATH = "/org/pywinctl/KWinReply"
_REPLY_INTERFACE = "org.pywinctl.KWinReply"

# Helpers available to every script. ARGS is injected as a JSON literal (always valid JavaScript)
_JS_PRELUDE = """
function reply(v) { callDBus(%(me)s, %(path)s, %(iface)s, "reply", %(token)s, JSON.stringify(v === undefined ? null : v)); }
function wid(w) { return w.internalId.toString(); }
function findWin(id) { return workspace.windowList().find(w => wid(w) === id) || null; }
function rect(r) { return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; }
function isUserWindow(w) { return w.managed && !w.deleted && (w.normalWindow || w.dialog) && !w.skipTaskbar; }
function info(w) {
    return {
        id: wid(w), title: w.caption, pid: w.pid,
        frame: rect(w.frameGeometry), client: rect(w.clientGeometry),
        minimized: w.minimized, maximized: w.maximizeMode === 3, hidden: w.hidden,
        active: workspace.activeWindow === w, output: w.output ? w.output.name : "",
        parent: w.transientFor ? wid(w.transientFor) : ""
    };
}
const ARGS = %(args)s;
try {
%(body)s
} catch (e) {
    reply({__error__: String(e)});
}
"""


class KWinError(RuntimeError):
    """Raised when KWin can not be reached or the KWin script fails"""


def isKWinWayland() -> bool:
    """
    Check if current session is a KDE Plasma 6 (or newer) session running on Wayland, so this backend must be used.
    Older Plasma versions use a different KWin scripting API, so they keep using the X11 backend.
    Set PYWINCTL_LINUX_BACKEND environment variable to "x11" or "kwin" to force one backend.
    """
    forced = os.environ.get("PYWINCTL_LINUX_BACKEND", "").lower()
    if forced in ("x11", "xlib"):
        return False
    if forced == "kwin":
        return True
    try:
        # Set by Plasma itself on session startup
        plasmaVersion = int(os.environ.get("KDE_SESSION_VERSION", ""))
    except ValueError:
        return False
    return (plasmaVersion >= 6
            and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
            and "kde" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower())


class _KWinBridge:
    """Runs JavaScript snippets inside KWin and returns their (JSON) result"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._conn: Any = None
        self._counter = itertools.count()

    def _connection(self) -> Any:
        if self._conn is None:
            from jeepney.io.blocking import open_dbus_connection
            self._conn = open_dbus_connection(bus="SESSION")
        return self._conn

    def run(self, body: str, args: Any = None) -> Any:
        try:
            from jeepney import DBusAddress, MessageType, new_method_call, new_method_return
            from jeepney.bus_messages import MatchRule
        except ImportError as e:
            raise KWinError("KDE Wayland support requires the 'jeepney' module (pip install jeepney)") from e

        with self._lock:
            conn = self._connection()
            token = "%d-%d" % (os.getpid(), next(self._counter))
            pluginName = "pywinctl_" + token.replace("-", "_")
            script = _JS_PRELUDE % {
                "me": json.dumps(conn.unique_name), "path": json.dumps(_REPLY_PATH),
                "iface": json.dumps(_REPLY_INTERFACE), "token": json.dumps(token),
                "args": json.dumps(args), "body": body,
            }
            scripting = DBusAddress("/Scripting", bus_name="org.kde.KWin", interface="org.kde.kwin.Scripting")
            fd, path = tempfile.mkstemp(prefix="pywinctl_", suffix=".js")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(script)
                rule = MatchRule(type="method_call", interface=_REPLY_INTERFACE, path=_REPLY_PATH)
                with conn.filter(rule) as queue:
                    msg = conn.send_and_get_reply(new_method_call(scripting, "loadScript", "ss", (path, pluginName)),
                                                  timeout=KWIN_TIMEOUT)
                    if msg.header.message_type == MessageType.error or msg.body[0] < 0:
                        raise KWinError("KWin refused to load script: %s" % (msg.body,))
                    script_obj = DBusAddress("/Scripting/Script%d" % msg.body[0], bus_name="org.kde.KWin",
                                             interface="org.kde.kwin.Script")
                    conn.send_and_get_reply(new_method_call(script_obj, "run"), timeout=KWIN_TIMEOUT)
                    deadline = time.monotonic() + KWIN_TIMEOUT
                    while True:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise KWinError("Timed out waiting for KWin")
                        try:
                            msg = conn.recv_until_filtered(queue, timeout=remaining)
                        except TimeoutError as e:
                            raise KWinError("Timed out waiting for KWin") from e
                        conn.send(new_method_return(msg))
                        if msg.body and msg.body[0] == token:
                            break
            finally:
                try:
                    conn.send_and_get_reply(new_method_call(scripting, "unloadScript", "s", (pluginName,)),
                                            timeout=KWIN_TIMEOUT)
                except (OSError, TimeoutError):
                    # Best effort: an orphan script does no harm and KWin unloads it on restart
                    pass
                os.unlink(path)

        result = json.loads(msg.body[1])
        if isinstance(result, dict) and "__error__" in result:
            raise KWinError(result["__error__"])
        return result


_bridge = _KWinBridge()


def checkPermissions(activate: bool = False) -> bool:
    """
    macOS ONLY: Check Apple Script permissions for current script/app and, optionally, shows a
    warning dialog and opens security preferences

    :param activate: If ''True'' and if permissions are not granted, shows a dialog and opens security preferences.
                     Defaults to ''False''
    :return: returns ''True'' if permissions are already granted or platform is not macOS
    """
    return True


def _getAllWindowsInfo() -> list[dict[str, Any]]:
    # Bottom-to-top stacking order, same as X11's _NET_CLIENT_LIST_STACKING
    return _bridge.run("reply(workspace.stackingOrder.filter(isUserWindow).map(info));") or []


def getActiveWindow() -> KWinWindow | None:
    """
    Get the currently active (focused) Window

    :return: Window object or None
    """
    winId = _bridge.run("const w = workspace.activeWindow; reply(w ? wid(w) : null);")
    return KWinWindow(winId) if winId else None


def getActiveWindowTitle() -> str:
    """
    Get the title of the currently active (focused) Window

    :return: window title as string or empty
    """
    return _bridge.run("const w = workspace.activeWindow; reply(w ? w.caption : '');") or ""


def getAllWindows() -> list[KWinWindow]:
    """
    Get the list of Window objects for all visible windows

    :return: list of Window objects
    """
    return [KWinWindow(w["id"]) for w in _getAllWindowsInfo()]


def getAllTitles() -> list[str]:
    """
    Get the list of titles of all visible windows

    :return: list of titles as strings
    """
    return [w["title"] for w in _getAllWindowsInfo()]


def getWindowsWithTitle(title: str | re.Pattern[str], app: tuple[str, ...] | None = (), condition: int = Re.IS, flags: int = 0) -> list[KWinWindow]:
    """
    Get the list of window objects whose title match the given string with condition and flags.
    Use ''condition'' to delimit the search. Allowed values are stored in pywinctl.Re sub-class (e.g. pywinctl.Re.CONTAINS)
    Use ''flags'' to define additional values according to each condition type (see pywinctl.Re)

    :param title: title or regex pattern to match, as string
    :param app: (optional) tuple of app names. Defaults to ALL (empty list)
    :param condition: (optional) condition to apply when searching the window. Defaults to ''Re.IS'' (is equal to)
    :param flags: (optional) specific flags to apply to condition. Defaults to 0 (no flags)
    :return: list of Window objects
    """
    if not (title and condition in Re._cond_dic):
        return []

    lower = False
    if condition in (Re.MATCH, Re.NOTMATCH):
        title = re.compile(title, flags)
    elif condition in (Re.EDITDISTANCE, Re.DIFFRATIO):
        if not isinstance(flags, int) or not (0 < flags <= 100):
            flags = 90
    elif flags == Re.IGNORECASE:
        lower = True
        if isinstance(title, re.Pattern):
            title = title.pattern
        else:
            title = title.lower()
    return [
        KWinWindow(w["id"]) for w in _getAllWindowsInfo()
        if w["title"] and Re._cond_dic[condition](title, w["title"].lower() if lower else w["title"], flags)
        and (not app or _getProcessName(w["pid"]) in app)
    ]


def getAllAppsNames() -> list[str]:
    """
    Get the list of names of all visible apps

    :return: list of names as strings
    """
    return list(getAllAppsWindowsTitles())


def getAppsWithName(name: str | re.Pattern[str], condition: int = Re.IS, flags: int = 0) -> list[str]:
    """
    Get the list of app names which match the given string using the given condition and flags.
    Use ''condition'' to delimit the search. Allowed values are stored in pywinctl.Re sub-class (e.g. pywinctl.Re.CONTAINS)
    Use ''flags'' to define additional values according to each condition type (see pywinctl.Re)

    :param name: name or regex pattern to match, as string
    :param condition: (optional) condition to apply when searching the app. Defaults to ''Re.IS'' (is equal to)
    :param flags: (optional) specific flags to apply to condition. Defaults to 0 (no flags)
    :return: list of app names
    """
    if not (name and condition in Re._cond_dic):
        return []

    lower = False
    if condition in (Re.MATCH, Re.NOTMATCH):
        name = re.compile(name, flags)
    elif condition in (Re.EDITDISTANCE, Re.DIFFRATIO):
        if not isinstance(flags, int) or not (0 < flags <= 100):
            flags = 90
    elif flags == Re.IGNORECASE:
        lower = True
        if isinstance(name, re.Pattern):
            name = name.pattern
        else:
            name = name.lower()
    return [
        appName for appName in getAllAppsNames()
        if appName and Re._cond_dic[condition](name, appName.lower() if lower else appName, flags)
    ]


def getAllAppsWindowsTitles() -> dict[str, list[str]]:
    """
    Get all visible apps names and their open windows titles

    Format:
        Key: app name

        Values: list of window titles as strings

    :return: python dictionary
    """
    result: dict[str, list[str]] = {}
    for w in _getAllWindowsInfo():
        result.setdefault(_getProcessName(w["pid"]), []).append(w["title"])
    return result


def getAllWindowsDict(tryToFilter: bool = False) -> dict[str, _WINDICT]:
    """
    Get all visible apps and windows info

    Format:
        Key: app name

        Values:
            "pid": app PID
            "windows": subdictionary of all app windows
                "title": subdictionary of window info
                    "id": window handle
                    "display": display in which window is mostly visible
                    "position": window position (x, y) within display
                    "size": window size (width, height)
                    "status": 0 - normal, 1 - minimized, 2 - maximized

    :param tryToFilter: Windows ONLY. Set to ''True'' to try to get User (non-system) apps only (may skip real user apps)
    :return: python dictionary
    """
    result: dict[str, _WINDICT] = {}
    for w in _getAllWindowsInfo():
        appName = _getProcessName(w["pid"])
        status = 1 if w["minimized"] else 2 if w["maximized"] else 0
        x, y, width, height = w["frame"]
        winDict: _WINDATA = {
            "id": w["id"],
            "display": [w["output"]] if w["output"] else [],
            "position": (x, y),
            "size": (width, height),
            "status": status
        }
        if appName not in result:
            result[appName] = {"pid": w["pid"], "windows": {}}
        result[appName]["windows"][w["title"]] = winDict
    return result


def getWindowsAt(x: int, y: int) -> list[KWinWindow]:
    """
    Get the list of Window objects whose windows contain the point ``(x, y)`` on screen

    :param x: X screen coordinate of the window(s)
    :param y: Y screen coordinate of the window(s)
    :return: list of Window objects
    """
    return [
        KWinWindow(w["id"]) for w in _getAllWindowsInfo()
        if not w["minimized"] and pointInBox(x, y, Box(*w["frame"]))
    ]


def getTopWindowAt(x: int, y: int) -> KWinWindow | None:
    """
    Get the Window object at the top of the stack at the point ``(x, y)`` on screen

    :param x: X screen coordinate of the window
    :param y: Y screen coordinate of the window
    :return: Window object or None
    """
    windows = getWindowsAt(x, y)
    return windows[-1] if windows else None


def _getProcessName(pid: int) -> str:
    # Same as "ps -q <pid> -o comm=", used by the X11 backend
    try:
        with open("/proc/%d/comm" % pid, encoding="utf-8") as f:
            return f.read().strip()
    except (OSError, TypeError):
        return ""


def _normalizeId(hWnd: Any) -> str:
    winId = str(hWnd).strip()
    if winId and not winId.startswith("{"):
        winId = "{%s}" % winId
    return winId.lower()


class KWinWindow(BaseWindow):
    """
    Window managed through KWin scripting (KDE Plasma on Wayland).
    The window handle is the KWin internal id (a UUID string such as "{5be5f3ae-...}")
    """

    def __init__(self, hWnd: str) -> None:
        self._hWnd: str = _normalizeId(hWnd)
        self._box: PyWinBox = PyWinBox(onQuery=self._getWindowBox, onSet=self._moveResizeWindow)
        self.watchdog = _WatchDog(self)

    # --- KWin helpers -----------------------------------------------------------------------------------------

    def _info(self) -> dict[str, Any] | None:
        return cast("dict[str, Any] | None",
                    _bridge.run("const w = findWin(ARGS.id); reply(w ? info(w) : null);", {"id": self._hWnd}))

    def _infoOrFail(self) -> dict[str, Any]:
        data = self._info()
        if data is None:
            raise KWinError("Window %s does not exist" % self._hWnd)
        return data

    def _do(self, body: str, **kwargs: Any) -> Any:
        # Runs 'body' with 'w' bound to this window. Returns None if the window no longer exists
        kwargs["id"] = self._hWnd
        return _bridge.run("const w = findWin(ARGS.id); if (!w) { reply(null); } else {\n%s\n}" % body, kwargs)

    def _waitFor(self, condition: Any, wait: bool) -> bool:
        result = condition()
        retries = 0
        while wait and not result and retries < WAIT_ATTEMPTS:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
            result = condition()
        return bool(result)

    def _getWindowBox(self) -> Box:
        return Box(*self._infoOrFail()["frame"])

    def _moveResizeWindow(self, box: Box) -> None:
        self._do("w.frameGeometry = {x: ARGS.x, y: ARGS.y, width: ARGS.width, height: ARGS.height}; reply(true);",
                 x=box.left, y=box.top, width=box.width, height=box.height)

    # --- BaseWindow API ---------------------------------------------------------------------------------------

    def __repr__(self) -> str:
        return '%s(hWnd=%s)' % (self.__class__.__name__, self._hWnd)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, KWinWindow) and self._hWnd == other._hWnd

    def getExtraFrameSize(self, includeBorder: bool = True) -> tuple[int, int, int, int]:
        """
        Get the extra space, in pixels, around the window (decorations drawn by KWin: title bar and borders)

        :param includeBorder: ignored on KWin (borders are part of the decoration)
        :return: additional frame size in pixels, as a tuple of int (left, top, right, bottom)
        """
        data = self._infoOrFail()
        fx, fy, fw, fh = data["frame"]
        cx, cy, cw, ch = data["client"]
        return cx - fx, cy - fy, (fx + fw) - (cx + cw), (fy + fh) - (cy + ch)

    def getClientFrame(self) -> Rect:
        """
        Get the client area of window (without decorations), as a Rect (x, y, right, bottom)

        :return: Rect struct
        """
        x, y, w, h = self._infoOrFail()["client"]
        return Rect(x, y, x + w, y + h)

    def close(self) -> bool:
        """
        Closes this window. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from
        actually closing. This is identical to clicking the X button on the
        window.

        :return: ''True'' if window is closed
        """
        self._do("w.closeWindow(); reply(true);")
        return self._waitFor(lambda: not self.isAlive, True)

    def minimize(self, wait: bool = False) -> bool:
        """
        Minimizes this window

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :return: ''True'' if window minimized
        """
        self._do("w.minimized = true; reply(true);")
        return self._waitFor(lambda: self.isMinimized, wait)

    def maximize(self, wait: bool = False) -> bool:
        """
        Maximizes this window

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :return: ''True'' if window maximized
        """
        self._do("w.setMaximize(true, true); reply(true);")
        return self._waitFor(lambda: self.isMaximized, wait)

    def restore(self, wait: bool = False, user: bool = True) -> bool:
        """
        If maximized or minimized, restores the window to its normal size

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :param user: ignored on KWin
        :return: ''True'' if window restored
        """
        self._do("w.minimized = false; if (w.maximizeMode !== 0) { w.setMaximize(false, false); }"
                 " workspace.activeWindow = w; reply(true);")

        def restored() -> bool:
            data = self._info()
            return bool(data and not data["minimized"] and not data["maximized"])
        return self._waitFor(restored, wait)

    def show(self, wait: bool = False) -> bool:
        """
        If hidden or showing, shows the window on screen and in title bar.
        On KWin, this is equivalent to un-minimizing the window

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window showed
        """
        self._do("w.minimized = false; reply(true);")
        return self._waitFor(lambda: not self.isMinimized, wait)

    def hide(self, wait: bool = False) -> bool:
        """
        If hidden or showing, hides the window from screen.
        Wayland does not allow to unmap other clients' windows, so on KWin this is equivalent to minimizing it

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window hidden
        """
        return self.minimize(wait)

    def activate(self, wait: bool = False, user: bool = True) -> bool:
        """
        Activate this window and make it the foreground (focused) window

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :param user: ignored on KWin
        :return: ''True'' if window activated
        """
        self._do("w.minimized = false; workspace.activeWindow = w; reply(true);")
        return self._waitFor(lambda: self.isActive, wait)

    def resize(self, widthOffset: int, heightOffset: int, wait: bool = False) -> bool:
        """
        Resizes the window relative to its current size

        :param widthOffset: offset to add to current window width as target width
        :param heightOffset: offset to add to current window height as target height
        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window resized to the given size
        """
        box = self.box
        return self.resizeTo(box.width + widthOffset, box.height + heightOffset, wait)

    resizeRel = resize  # resizeRel is an alias for the resize() method.

    def resizeTo(self, newWidth: int, newHeight: int, wait: bool = False) -> bool:
        """
        Resizes the window to a new width and height

        :param newWidth: target window width
        :param newHeight: target window height
        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window resized to the given size
        """
        self._do("const g = w.frameGeometry;"
                 " w.frameGeometry = {x: g.x, y: g.y, width: ARGS.width, height: ARGS.height}; reply(true);",
                 width=newWidth, height=newHeight)

        def resized() -> bool:
            box = self.box
            return box.width == newWidth and box.height == newHeight
        return self._waitFor(resized, wait)

    def move(self, xOffset: int, yOffset: int, wait: bool = False) -> bool:
        """
        Moves the window relative to its current position

        :param xOffset: offset relative to current X coordinate to move the window to
        :param yOffset: offset relative to current Y coordinate to move the window to
        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window moved to the given position
        """
        box = self.box
        return self.moveTo(box.left + xOffset, box.top + yOffset, wait)

    moveRel = move  # moveRel is an alias for the move() method.

    def moveTo(self, newLeft: int, newTop: int, wait: bool = False) -> bool:
        """
        Moves the window to new coordinates on the screen

        :param newLeft: target X coordinate to move the window to
        :param newTop: target Y coordinate to move the window to
        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window moved to the given position
        """
        self._do("const g = w.frameGeometry;"
                 " w.frameGeometry = {x: ARGS.x, y: ARGS.y, width: g.width, height: g.height}; reply(true);",
                 x=newLeft, y=newTop)

        def moved() -> bool:
            box = self.box
            return box.left == newLeft and box.top == newTop
        return self._waitFor(moved, wait)

    def alwaysOnTop(self, aot: bool = True) -> bool:
        """
        Keeps window on top of all others.

        :param aot: set to ''False'' to deactivate always-on-top behavior
        :return: ''True'' if command succeeded
        """
        return bool(self._do("w.keepAbove = ARGS.v; reply(w.keepAbove === ARGS.v);", v=bool(aot)))

    def alwaysOnBottom(self, aob: bool = True) -> bool:
        """
        Keeps window below of all others, but on top of desktop icons and keeping all window properties

        :param aob: set to ''False'' to deactivate always-on-bottom behavior
        :return: ''True'' if command succeeded
        """
        return bool(self._do("w.keepBelow = ARGS.v; reply(w.keepBelow === ARGS.v);", v=bool(aob)))

    def lowerWindow(self) -> bool:
        """
        Lowers the window to the bottom so that it does not obscure any sibling windows.
        KWin scripting only allows to raise windows, so all other windows are raised above this one
        (keeping their relative order and without changing the active window)

        :return: ''True'' if window lowered
        """
        return bool(self._do(
            "const others = workspace.stackingOrder.filter(o => o !== w && isUserWindow(o) && !o.keepBelow);"
            " for (const o of others) { workspace.raiseWindow(o); }"
            " const order = workspace.stackingOrder.filter(isUserWindow);"
            " reply(order.indexOf(w) === order.findIndex(o => !o.keepBelow) || order[0] === w);"
        ))

    def raiseWindow(self) -> bool:
        """
        Raises the window to top so that it is not obscured by any sibling windows.

        :return: ''True'' if window raised
        """
        return bool(self._do(
            "workspace.raiseWindow(w);"
            " const order = workspace.stackingOrder.filter(o => isUserWindow(o) && !o.keepAbove);"
            " reply(order[order.length - 1] === w || w.keepAbove);"
        ))

    def sendBehind(self, sb: bool = True) -> bool:
        """
        Sends the window to the very bottom, below all other windows.
        Wayland does not allow to place windows below the desktop, so on KWin this keeps the window below all
        others (same as alwaysOnBottom())

        :param sb: set to ''False'' to bring the window back to front
        :return: ''True'' if command succeeded
        """
        if sb:
            return self.alwaysOnBottom(True)
        return self.alwaysOnBottom(False) and self.activate()

    def acceptInput(self, setTo: bool) -> None:
        """
        Toggles the window to accept input and focus

        WARNING: Not supported on KDE Wayland (KWin scripting can not make a window transparent to input)

        :param setTo: True/False to toggle window ignoring input and focus
        :return: None
        """
        raise NotImplementedError("acceptInput() is not supported on KDE Wayland")

    def getAppName(self) -> str:
        """
        Get the name of the app current window belongs to

        :return: name of the app as string
        """
        return _getProcessName(self._infoOrFail()["pid"])

    def getParent(self) -> str:
        """
        Get the handle of the window this window is transient for (e.g. the main window of a dialog)

        :return: handle of the window parent, or empty string if it has no parent
        """
        return str(self._infoOrFail()["parent"])

    def setParent(self, parent: str) -> bool:
        """
        Current window will become child of given parent

        WARNING: Not supported on KDE Wayland (windows can not be reparented)

        :param parent: window to set as current window parent
        :return: ''True'' if current window is now child of given parent
        """
        return False

    def getChildren(self) -> list[str]:
        """
        Get the children handles of current window (windows which are transient for this window)

        :return: list of handles
        """
        return self._do("reply(workspace.windowList().filter(o => o.transientFor === w).map(wid));") or []

    def getHandle(self) -> str:
        """
        Get the current window handle (KWin internal id)

        :return: window handle
        """
        return self._hWnd

    def getPID(self) -> int | None:
        """
        Get the current application PID the window belongs to

        :return: application PID or None if it couldn't be retrieved
        """
        data = self._info()
        return data["pid"] if data and data["pid"] > 0 else None

    def isParent(self, child: str) -> bool:
        """Returns ''True'' if the window is parent of the given window as input argument

        :param child: handle of the window you want to check if the current window is parent of
        """
        return _normalizeId(child) in self.getChildren()
    isParentOf = isParent  # isParentOf is an alias of isParent method

    def isChild(self, parent: str) -> bool:
        """
        Check if current window is child of given window/app (handle)

        :param parent: handle of the window/app you want to check if the current window is child of
        :return: ''True'' if current window is child of the given window
        """
        return bool(_normalizeId(parent) == self.getParent())
    isChildOf = isChild  # isChildOf is an alias of isParent method

    def getDisplay(self) -> list[str]:
        """
        Get display names in which current window space is mostly visible

        If you need to get info or control the monitor, use these names as input to PyMonCtl's findMonitorWithName().

        :return: display name as list of strings or empty (couldn't retrieve it or window is off-screen)
        """
        output = self._infoOrFail()["output"]
        return [output] if output else []
    getMonitor = getDisplay  # getMonitor is an alias of getDisplay method

    @property
    def isMinimized(self) -> bool:
        """
        Check if current window is currently minimized

        :return: ``True`` if the window is minimized
        """
        data = self._info()
        return bool(data and data["minimized"])

    @property
    def isMaximized(self) -> bool:
        """
        Check if current window is currently maximized

        :return: ``True`` if the window is maximized
        """
        data = self._info()
        return bool(data and data["maximized"])

    @property
    def isActive(self) -> bool:
        """
        Check if current window is currently the active, foreground window

        :return: ``True`` if the window is the active, foreground window
        """
        data = self._info()
        return bool(data and data["active"])

    @property
    def title(self) -> str:
        """
        Get the current window title, as string

        :return: title as a string
        """
        data = self._info()
        return data["title"] if data else ""

    @property
    def visible(self) -> bool:
        """
        Check if current window is visible (minimized windows are also visible)

        :return: ``True`` if the window is currently visible
        """
        data = self._info()
        return bool(data and not data["hidden"])

    isVisible = visible  # isVisible is an alias for the visible property.

    @property
    def isAlive(self) -> bool:
        """
        Check if window (and application) still exists (minimized and hidden windows are included as existing)

        :return: ''True'' if window exists
        """
        try:
            return self._info() is not None
        except KWinError:
            return False
