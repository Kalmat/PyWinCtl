#!/usr/bin/python
# -*- coding: utf-8 -*-
# Incomplete type stubs for pyobjc
# mypy: disable_error_code = no-any-return
from __future__ import annotations

import sys

assert sys.platform == "darwin"

import ast
import difflib
import platform
import re
import subprocess
import threading
import time
from collections.abc import Callable, Iterable
from typing import Any, AnyStr, overload, cast, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import TypeAlias, TypedDict, Literal
else:
    # Only needed if the import from typing_extensions is used outside of annotations
    TypeAlias = Any
    from typing import TypedDict
    Literal = AnyStr

import AppKit
import Quartz

from pywinctl import pointInRect, BaseWindow, Rect, Point, Size, Re, _WinWatchDog

Incomplete: TypeAlias = Any
Attribute: TypeAlias = Sequence['tuple[str, str, bool, str]']

WS = AppKit.NSWorkspace.sharedWorkspace()
WAIT_ATTEMPTS = 10
WAIT_DELAY = 0.025  # Will be progressively increased on every retry

SEP = "|&|"


def checkPermissions(activate: bool = False):
    """
    macOS ONLY: Check Apple Script permissions for current script/app and, optionally, shows a
    warning dialog and opens security preferences

    :param activate: If ''True'' and if permissions are not granted, shows a dialog and opens security preferences.
                     Defaults to ''False''
    :return: ''True'' if permissions are already granted or platform is not macOS
    """
    # https://stackoverflow.com/questions/26591560/how-to-grant-applescript-permissions-through-applescript
    if activate:
        cmd = """tell application "System Events"
                    set UI_enabled to UI elements enabled
                end tell
                if UI_enabled is false then
                    display dialog "This script requires Accessibility permissions" & return & return & "You can activate GUI Scripting by selecting the checkbox Enable access for assistive devices in the Security and Privacy > Accessibility preferences" with icon 1 buttons {"Ok"} default button 1
                    tell application "System Preferences"
                        activate
                        set current pane to pane id "com.apple.preference.security"
                    end tell
                end if
                return UI_enabled"""
    else:
        cmd = """tell application "System Events"
                    set UI_enabled to UI elements enabled
                end tell
                return UI_enabled"""
    proc = subprocess.Popen(['osascript'],  stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
    ret, err = proc.communicate(cmd)
    ret = ret.replace("\n", "")
    return ret == "true"

@overload
def getActiveWindow(app: AppKit.NSApplication) -> MacOSNSWindow | None: ...
@overload
def getActiveWindow(app: None = ...) -> MacOSWindow | None: ...

def getActiveWindow(app: AppKit.NSApplication | None = None):
    """
    Get the currently active (focused) Window

    :param app: (optional) NSApp() object. If passed, returns the active (main/key) window of given app
    :return: Window object or None
    """
    if not app:
        # app = WS.frontmostApplication()   # This fails after using .activateWithOptions_()?!?!?!
        cmd = """on run
                    set appName to ""
                    set appID to ""
                    set winData to {}
                    try
                        tell application "System Events"
                            set appName to name of first application process whose frontmost is true
                            set appID to unix id of application process appName
                            tell application process appName
                                set winData to {position, size, name} of (first window whose value of attribute "AXMain" is true)
                            end tell
                        end tell
                    end try
                    return {appID, winData}
                end run"""
        proc = subprocess.Popen(['osascript'],  stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        entries = ret.replace("\n", "").split(", ")
        try:
            appID = entries[0]
            bounds = Rect(int(entries[1]), int(entries[2]), int(entries[3]), int(entries[4]))
            # Thanks to Anthony Molinaro (djnym) for pointing out this bug and provide the solution!!!
            # sometimes the title of the window contains ',' characters, so just get the first entry as the appName and join the rest
            # back together as a string
            title = ", ".join(entries[5:])
            if appID:  # and title:
                activeApps = _getAllApps()
                for a in activeApps:
                    if str(a.processIdentifier()) == appID:
                        return MacOSWindow(a, title, bounds)
        except Exception as e:
            print(e)
    else:
        for win in app.orderedWindows():  # .keyWindow() / .mainWindow() not working?!?!?!
            return MacOSNSWindow(app, win)
    return None


def getActiveWindowTitle(app: AppKit.NSApplication | None = None) -> str:
    """
    Get the title of the currently active (focused) Window

    :param app: (optional) NSApp() object. If passed, returns the title of the main/key window of given app
    :return: window title as string or empty
    """
    win = getActiveWindow(app)
    if win:
        return win.title or ""
    else:
        return ""

@overload
def getAllWindows(app: AppKit.NSApplication) -> list[MacOSNSWindow]: ...
@overload
def getAllWindows(app: None = ...) -> list[MacOSWindow]: ...

def getAllWindows(app: AppKit.NSApplication | None = None):
    """
    Get the list of Window objects for all visible windows

    :param app: (optional) NSApp() object. If passed, returns the Window objects of all windows of given app
    :return: list of Window objects
    """
    # TODO: Find a way to return windows as per the stacking order (not sure if it is even possible!)
    if not app:
        windows: list[MacOSWindow] = []
        activeApps = _getAllApps()
        titleList = _getWindowTitles()
        for item in titleList:
            try:
                pID = item[0]
                title = item[1]
                if len(item) > 3 and len(item[2]) > 1 and len(item[3]) > 1:
                    x = int(item[2][0])
                    y = int(item[2][1])
                    w = int(item[3][0])
                    h = int(item[3][1])
                    rect = Rect(x, y, x + w, y + h)
                else:
                    rect = None
            except:
                continue
            for activeApp in activeApps:
                if activeApp.processIdentifier() == pID:
                    windows.append(MacOSWindow(activeApp, title, rect))
                    break
        return windows
    else:
        nsWindows: list[MacOSNSWindow] = []
        for win in app.orderedWindows():
            nsWindows.append(MacOSNSWindow(app, win))
        return nsWindows


def getAllTitles(app: AppKit.NSApplication | None = None):
    """
    Get the list of titles of all visible windows

    :param app: (optional) NSApp() object. If passed, returns the titles of the windows of given app
    :return: list of titles as strings
    """
    if not app:
        cmd = """osascript -s 's' -e 'tell application "System Events"
                                    set winNames to {}
                                    try
                                        set winNames to {name of every window} of (every process whose background only is false)
                                    end try
                                end tell
                                return winNames'"""
        ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").replace("\n", "").replace("{", "[").replace("}", "]")
        res = ast.literal_eval(ret)
        matches: list[str] = []
        if len(res) > 0:
            for item in res[0]:
                for title in item:
                    matches.append(title)
    else:
        matches = [win.title for win in getAllWindows(app)]
    return matches

@overload
def getWindowsWithTitle(title: str | re.Pattern[str], app: tuple[str, ...] | None = ..., condition: int = ..., flags: int = ...) -> list[MacOSWindow]: ...
@overload
def getWindowsWithTitle(title: str | re.Pattern[str], app: AppKit.NSApp, condition: int = ..., flags: int = ...) -> list[MacOSNSWindow]: ...

def getWindowsWithTitle(title: str | re.Pattern[str], app: AppKit.NSApp | tuple[str, ...] | None = None, condition: int = Re.IS, flags: int = 0):
    """
    Get the list of window objects whose title match the given string with condition and flags.
    Use ''condition'' to delimit the search. Allowed values are stored in pywinctl.Re sub-class (e.g. pywinctl.Re.CONTAINS)
    Use ''flags'' to define additional values according to each condition type:

        - IS -- window title is equal to given title (allowed flags: Re.IGNORECASE)
        - CONTAINS -- window title contains given string (allowed flags: Re.IGNORECASE)
        - STARTSWITH -- window title starts by given string (allowed flags: Re.IGNORECASE)
        - ENDSWITH -- window title ends by given string (allowed flags: Re.IGNORECASE)
        - NOTIS -- window title is not equal to given title (allowed flags: Re.IGNORECASE)
        - NOTCONTAINS -- window title does NOT contains given string (allowed flags: Re.IGNORECASE)
        - NOTSTARTSWITH -- window title does NOT starts by given string (allowed flags: Re.IGNORECASE)
        - NOTENDSWITH -- window title does NOT ends by given string (allowed flags: Re.IGNORECASE)
        - MATCH -- window title matched by given regex pattern (allowed flags: regex flags, see https://docs.python.org/3/library/re.html)
        - NOTMATCH -- window title NOT matched by given regex pattern (allowed flags: regex flags, see https://docs.python.org/3/library/re.html)
        - EDITDISTANCE -- window title matched using Levenshtein edit distance to a given similarity percentage (allowed flags: 0-100. Defaults to 90)
        - DIFFRATIO -- window title matched using difflib similarity ratio (allowed flags: 0-100. Defaults to 90)

    :param title: title or regex pattern to match, as string
    :param app: NSApp object (NSWindow version) / (optional) tuple of app names (Apple Script version), defaults to ALL (empty list)
    :param condition: (optional) condition to apply when searching the window. Defaults to ''Re.IS'' (is equal to)
    :param flags: (optional) specific flags to apply to condition. Defaults to 0 (no flags)
    :return: list of Window objects
    """

    if not (title and condition in Re._cond_dic):
        return []  # pyright: ignore[reportUnknownVariableType]  # Type doesn't matter here

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
        title = title.lower()

    if app is None or isinstance(app, tuple):
        matches: list[MacOSWindow] = []
        activeApps = _getAllApps()
        titleList = _getWindowTitles()
        for item in titleList:
            pID = item[0]
            winTitle = item[1].lower() if lower else item[1]
            if winTitle and Re._cond_dic[condition](title, winTitle, flags):
                x, y, w, h = int(item[2][0]), int(item[2][1]), int(item[3][0]), int(item[3][1])
                rect = Rect(x, y, x + w, y + h)
                for a in activeApps:
                    if (app and a.localizedName() in app) or (a.processIdentifier() == pID):
                        matches.append(MacOSWindow(a, item[1], rect))
                        break
        return matches
    else:
        return [
            win for win
            in getAllWindows(app)
            if win.title and Re._cond_dic[condition](title, win.title.lower() if lower else win.title, flags)
        ]


def getAllAppsNames() -> list[str]:
    """
    Get the list of names of all visible apps

    :return: list of names as strings
    """
    cmd = """osascript -s 's' -e 'tell application "System Events"
                                    set winNames to {}
                                    try
                                        set winNames to name of every process whose background only is false
                                    end try
                                end tell
                                return winNames'"""
    ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").replace("\n", "").replace("{", "[").replace("}", "]")
    res = ast.literal_eval(ret)
    return res or []


def getAppsWithName(name: str | re.Pattern[str], condition: int = Re.IS, flags: int = 0):
    """
    Get the list of app names which match the given string using the given condition and flags.
    Use ''condition'' to delimit the search. Allowed values are stored in pywinctl.Re sub-class (e.g. pywinctl.Re.CONTAINS)
    Use ''flags'' to define additional values according to each condition type:

        - IS -- app name is equal to given title (allowed flags: Re.IGNORECASE)
        - CONTAINS -- app name contains given string (allowed flags: Re.IGNORECASE)
        - STARTSWITH -- app name starts by given string (allowed flags: Re.IGNORECASE)
        - ENDSWITH -- app name ends by given string (allowed flags: Re.IGNORECASE)
        - NOTIS -- app name is not equal to given title (allowed flags: Re.IGNORECASE)
        - NOTCONTAINS -- app name does NOT contains given string (allowed flags: Re.IGNORECASE)
        - NOTSTARTSWITH -- app name does NOT starts by given string (allowed flags: Re.IGNORECASE)
        - NOTENDSWITH -- app name does NOT ends by given string (allowed flags: Re.IGNORECASE)
        - MATCH -- app name matched by given regex pattern (allowed flags: regex flags, see https://docs.python.org/3/library/re.html)
        - NOTMATCH -- app name NOT matched by given regex pattern (allowed flags: regex flags, see https://docs.python.org/3/library/re.html)
        - EDITDISTANCE -- app name matched using Levenshtein edit distance to a given similarity percentage (allowed flags: 0-100. Defaults to 90)
        - DIFFRATIO -- app name matched using difflib similarity ratio (allowed flags: 0-100. Defaults to 90)

    :param name: name or regex pattern to match, as string
    :param condition: (optional) condition to apply when searching the app. Defaults to ''Re.IS'' (is equal to)
    :param flags: (optional) specific flags to apply to condition. Defaults to 0 (no flags)
    :return: list of app names
    """
    matches: list[str] = []
    if name and condition in Re._cond_dic:
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
            name = name.lower()
        for title in getAllAppsNames():
            if title and Re._cond_dic[condition](name, title.lower() if lower else title, flags):
                matches.append(title)
    return matches


def getAllAppsWindowsTitles():
    """
    Get all visible apps names and their open windows titles

    Format:
        Key: app name

        Values: list of window titles as strings

    :return: python dictionary
    """
    cmd = """osascript -s 's' -e 'tell application "System Events"
                                    set winNames to {}
                                    try
                                        set winNames to {name, (name of every window)} of (every process whose background only is false)
                                    end try
                                end tell
                                return winNames'"""
    ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").replace("\n", "").replace("{", "[").replace("}", "]")
    res: tuple[list[str], list[list[str]]] = ast.literal_eval(ret)
    result: dict[str, list[str]] = {}
    if res and len(res) > 0:
        for i, item in enumerate(res[0]):
            result[item] = res[1][i]
    return result


@overload
def getWindowsAt(x: int, y: int, app: AppKit.NSApplication, allWindows: list[MacOSNSWindow] | None = ...) -> list[MacOSNSWindow]: ...
@overload
def getWindowsAt(x: int, y: int, app: None = ..., allWindows: list[MacOSWindow] | None = ...) -> list[MacOSWindow]: ...
@overload
def getWindowsAt(x: int, y: int, app: AppKit.NSApplication | None = ..., allWindows: list[MacOSWindow | MacOSNSWindow] | list[MacOSNSWindow] | list[MacOSWindow] | None = ...) -> list[MacOSWindow | MacOSNSWindow] | list[MacOSNSWindow] | list[MacOSWindow]: ...

def getWindowsAt(x: int, y: int, app: AppKit.NSApplication | None = None, allWindows: list[MacOSNSWindow | MacOSWindow] | list[MacOSNSWindow] | list[MacOSWindow] | None = None) -> list[MacOSWindow | MacOSNSWindow] | list[MacOSNSWindow] | list[MacOSWindow]:
    """
    Get the list of Window objects whose windows contain the point ``(x, y)`` on screen

    :param x: X screen coordinate of the window(s)
    :param y: Y screen coordinate of the window(s)
    :param app: (optional) NSApp() object. If passed, returns the list of windows at (x, y) position of given app
    :param allWindows: (optional) list of window objects (required to improve performance in Apple Script version)
    :return: list of Window objects
    """
    windows = allWindows if allWindows else getAllWindows(app)
    windowBoxGenerator = ((window, window.box) for window in windows)
    return [
        window for (window, box)
        in windowBoxGenerator
        if pointInRect(x, y, box.left, box.top, box.width, box.height)]

@overload
def getTopWindowAt(x: int, y: int, app: AppKit.NSApplication, allWindows: list[MacOSNSWindow] | None = ...) -> MacOSNSWindow | None: ...
@overload
def getTopWindowAt(x: int, y: int, app: None = ..., allWindows: list[MacOSWindow] | None = ...) -> MacOSWindow | None: ...
@overload
def getTopWindowAt(x: int, y: int, app: AppKit.NSApplication | None = ..., allWindows: list[MacOSWindow | MacOSNSWindow] | list[MacOSNSWindow] | list[MacOSWindow] | None = ...) -> MacOSWindow | MacOSNSWindow | None: ...

def getTopWindowAt(x: int, y: int, app: AppKit.NSApplication | None = None, allWindows: list[MacOSNSWindow | MacOSWindow] | list[MacOSNSWindow] | list[MacOSWindow] | None = None):
    """
    Get *a* Window object at the point ``(x, y)`` on screen.
    Which window is not guaranteed. See https://github.com/Kalmat/PyWinCtl/issues/20#issuecomment-1193348238

    :param x: X screen coordinate of the window
    :param y: Y screen coordinate of the window
    :return: Window object or None
    """
    # Once we've figured out why getWindowsAt may not always return all windows
    # (see https://github.com/Kalmat/PyWinCtl/issues/21),
    # we can look into a more efficient implementation that only gets a single window
    windows = getWindowsAt(x, y, app, allWindows)
    return None if len(windows) == 0 else windows[-1]



def _getAllApps(userOnly: bool = True):
    matches: list[AppKit.NSRunningApplication] = []
    for app in WS.runningApplications():
        if not userOnly or (userOnly and app.activationPolicy() == Quartz.NSApplicationActivationPolicyRegular):
            matches.append(app)
    return matches


def _getAllWindows(userLayer: bool = True):
    # Source: https://stackoverflow.com/questions/53237278/obtain-list-of-all-window-titles-on-macos-from-a-python-script/53985082#53985082
    # This returns a list of window info objects, which is static, so needs to be refreshed and takes some time to the OS to refresh it
    # Besides, since it may not have kCGWindowName value and the kCGWindowNumber can't be accessed from Apple Script, it's useless
    ret: list[dict[Incomplete, int]] = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListExcludeDesktopElements | Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
    if userLayer:
        matches: list[dict[Incomplete, int]] = []
        for win in ret:
            if win.get(Quartz.kCGWindowLayer, "") == 0:
                matches.append(win)
        ret = matches
    return ret


def _getAllAppWindows(app: AppKit.NSApplication, userLayer: bool = True):
    windows = _getAllWindows()
    windowsInApp: list[dict[Incomplete, int]] = []
    for win in windows:
        if (not userLayer or (userLayer and win[Quartz.kCGWindowLayer] == 0)) and win[Quartz.kCGWindowOwnerPID] == app.processIdentifier():
            windowsInApp.append(win)
    return windowsInApp


def _getAppWindowsTitles(appName: str):
    cmd = """on run arg1
                set appName to arg1 as string
                set winNames to {}
                try
                    tell application "System Events"
                        set winNames to name of every window of process appName
                    end tell
                end try
                return winNames
            end run"""
    proc = subprocess.Popen(['osascript', '-s', 's', '-', appName],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
    ret, err = proc.communicate(cmd)
    ret = ret.replace("\n", "").replace("{", "[").replace("}", "]")
    res = ast.literal_eval(ret)
    return res or []


def _getWindowTitles() -> list[list[str]]:
    # https://gist.github.com/qur2/5729056 - qur2
    cmd = """osascript -s 's' -e 'tell application "System Events"
                                    set winNames to {}
                                    try
                                        set winNames to {unix id, ({name, position, size} of (every window))} of (every process whose background only is false)
                                    end try
                                end tell
                                return winNames'"""
    ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").replace("\n", "").replace("{", "[").replace("}", "]")
    res = ast.literal_eval(ret)
    result: list[list[str]] = []
    if len(res) > 0:
        for i, pID in enumerate(res[0]):
            try:
                item = res[1][0][i]
                j = 0
                for title in item:  # One-liner script is way faster, but produces complex data structures
                    try:
                        pos = res[1][1][i][j]
                        size = res[1][2][i][j]
                        result.append([pID, title, pos, size])
                    except:
                        pass
                    j += 1
            except:
                pass
    return result


def _getBorderSizes():
    try:  # This will fail if not called on main thread!
        a = AppKit.NSApplication.sharedApplication()
        frame = AppKit.NSMakeRect(400, 800, 250, 100)
        mask = AppKit.NSWindowStyleMaskTitled | AppKit.NSWindowStyleMaskClosable | AppKit.NSWindowStyleMaskMiniaturizable | AppKit.NSWindowStyleMaskResizable
        w = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(frame, mask, AppKit.NSBackingStoreBuffered, False)
        titlebarHeight = int(w.titlebarHeight())
        borderWidth = int(w.frame().size.width - w.contentRectForFrameRect_(frame).size.width)
        # w.display()
        # a.run()
        # w.setReleasedWhenClosed_(True)  # Method not found (?!)
        w.close()
    except:
        titlebarHeight = 0
        borderWidth = 0
    return titlebarHeight, borderWidth


_ItemInfoValue = TypedDict("_ItemInfoValue", {"value": str, "class": str, "settable": bool})
class _SubMenuStructure(TypedDict, total=False):
    hSubMenu: int
    wID: int
    entries: dict[str, _SubMenuStructure]
    parent: int
    rect: Rect
    item_info: dict[str, _ItemInfoValue]
    shortcut: str


class MacOSWindow(BaseWindow):
    @property
    def _rect(self):
        return self.__rect

    def __init__(self, app: AppKit.NSRunningApplication, title: str, bounds: Rect | None = None):
        super().__init__()
        self._app = app
        self._appName: str = app.localizedName()
        self._appPID = app.processIdentifier()
        self._winTitle = title
        # self._parent = self.getParent()  # It is slow and not required by now
        self.__rect = self._rectFactory(bounds=bounds)
        v = platform.mac_ver()[0].split(".")
        ver = float(v[0]+"."+v[1])
        # On Yosemite and below we need to use Zoom instead of FullScreen to maximize windows
        self._use_zoom = (ver <= 10.10)
        self._tt: _SendTop | None = None
        self._tb: _SendBottom | None = None
        self.menu = self._Menu(self)
        self.watchdog = self._WatchDog(self)

    def _getWindowRect(self) -> Rect:
        if not self.title:
            return Rect(0,0,0,0)

        cmd = """on run {arg1, arg2}
                    set procName to arg1
                    set winName to arg2
                    set appBounds to {{0, 0}, {0, 0}}
                    try
                        tell application "System Events" to tell application process procName
                            set appBounds to {position, size} of window winName
                        end tell
                    end try
                    return appBounds
                end run"""
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        if not ret:
            ret = "0, 0, 0, 0"
        w = ret.replace("\n", "").strip().split(", ")
        return Rect(int(w[0]), int(w[1]), int(w[0]) + int(w[2]), int(w[1]) + int(w[3]))

    def getExtraFrameSize(self, includeBorder: bool = True) -> tuple[int, int, int, int]:
        """
        Get the invisible space, in pixels, around the window, including or not the visible resize border

        :param includeBorder: set to ''False'' to avoid including window border
        :return: (left, top, right, bottom) frame size as a tuple of int
        """
        return 0, 0, 0, 0

    def getClientFrame(self):
        """
        Get the client area of window including scroll, menu and status bars, as a Rect (x, y, right, bottom)
        Notice that this method won't match non-standard window decoration style sizes

        :return: Rect struct

        WARNING: it will fail if not called within main thread
        """
        # https://www.macscripter.net/viewtopic.php?id=46336 --> Won't allow access to NSWindow objects, but interesting
        # Didn't find a way to get menu bar height using Apple Script
        titleHeight, borderWidth = _getBorderSizes()
        res = Rect(int(self.left + borderWidth), int(self.top + titleHeight), int(self.right - borderWidth), int(self.bottom - borderWidth))
        return res

    def __repr__(self):
        return '%s(hWnd=%s)' % (self.__class__.__name__, self._app)

    def __eq__(self, other: object):
        return isinstance(other, MacOSWindow) and self._app == other._app

    def close(self, force: bool = False) -> bool:
        """
        Closes this window. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from
        actually closing. This is identical to clicking the X button on the
        window.

        :return: ''True'' if window is closed
        """
        if not self.title:
            return False

        self.show()
        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    try
                        tell application appName
                            tell window winName to close
                        end tell
                    end try
                end run"""
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        if force and self.isAlive:
            self._app.terminate()
        return not self.isAlive

    def minimize(self, wait: bool = False) -> bool:
        """
        Minimizes this window

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :return: ''True'' if window minimized
        """
        if not self.title:
            return False

        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    try
                        tell application "System Events" to tell application process appName
                            set value of attribute "AXMinimized" of window winName to true
                        end tell
                    end try
                end run"""
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.isMinimized:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.isMinimized

    def maximize(self, wait: bool = False) -> bool:
        """
        Maximizes this window

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :return: ''True'' if window maximized
        """
        if not self.title:
            return False

        # Thanks to: macdeport (for this piece of code, his help, and the moral support!!!)
        if not self.isMaximized:
            if self._use_zoom:
                cmd = """on run {arg1, arg2}
                        set appName to arg1 as string
                        set winName to arg2 as string
                        try
                            tell application "System Events" to tell application "%s"
                                tell window winName to set zoomed to true
                            end tell
                        end try
                        end run""" % self._appName
            else:
                cmd = """on run {arg1, arg2}
                            set appName to arg1 as string
                            set winName to arg2 as string
                            try
                                tell application "System Events" to tell application process appName
                                    set value of attribute "AXFullScreen" of window winName to true
                                end tell
                            end try
                        end run"""
            proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
            ret, err = proc.communicate(cmd)
            retries = 0
            while wait and retries < WAIT_ATTEMPTS and not self.isMaximized:
                retries += 1
                time.sleep(WAIT_DELAY * retries)
        return self.isMaximized

    def restore(self, wait: bool = False, user: bool = True) -> bool:
        """
        If maximized or minimized, restores the window to it's normal size

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :param user: ignored on macOS platform
        :return: ''True'' if window restored
        """
        if not self.title:
            return False

        if self.isMaximized:
            if self._use_zoom:
                cmd = """on run {arg1, arg2}
                        set appName to arg1 as string
                        set winName to arg2 as string
                            try
                                tell application "System Events" to tell application "%s"
                                    tell window winName to set zoomed to false
                                end tell
                            end try
                        end run""" % self._appName
                proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
                ret, err = proc.communicate(cmd)
            else:
                cmd = """on run arg1
                            set appName to arg1 as string
                            try
                                tell application "System Events" to tell application process appName
                                    set value of attribute "AXFullScreen" of window 1 to false
                                end tell
                            end try
                        end run"""
                proc = subprocess.Popen(['osascript', '-', self._appName], 
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
                ret, err = proc.communicate(cmd)
        if self.isMinimized:
            cmd = """on run {arg1, arg2}
                        set appName to arg1 as string
                        set winName to arg2 as string
                        try
                            tell application "System Events" to tell application process appName
                                set value of attribute "AXMinimized" of window winName to false
                            end tell
                        end try
                    end run"""
            proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
            ret, err = proc.communicate(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and (self.isMinimized or self.isMaximized):
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self.isMaximized and not self.isMinimized

    def show(self, wait: bool = False) -> bool:
        """
        If hidden or showing, shows the window on screen and in title bar

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window showed
        """
        if not self.title:
            return False

        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    set isPossible to false
                    set isDone to false
                    try
                        tell application "System Events" to tell application "%s"
                            tell window winName to set visible to true
                            set isDone to true
                        end tell
                    end try
                    return (isDone as string)
               end run""" % self._appName
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        ret = ret.replace("\n", "")
        if ret != "true":
            self._app.unhide()
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.visible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.visible and self.isActive

    def hide(self, wait: bool = False) -> bool:
        """
        If hidden or showing, hides the window from screen and title bar

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window hidden
        """
        if not self.title:
            return False

        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    set isPossible to false
                    set isDone to false
                    try
                        tell application "System Events" to tell application "%s"
                            tell window winName to set visible to false
                            set isDone to true
                         end tell
                    end try
                    return (isDone as string)
                end run""" % self._appName
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        ret = ret.replace("\n", "")
        if ret != "true":
            self._app.hide()
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.visible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self.visible

    def activate(self, wait: bool = False, user: bool = True) -> bool:
        """
        Activate this window and make it the foreground (focused) window

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :param user: ignored on macOS platform
        :return: ''True'' if window activated
        """
        if not self.title:
            return False

        if not self.isVisible:
            self.show(wait=wait)
        if self.isMinimized or self.isMaximized:
            self.restore(wait=wait)
        self._app.activateWithOptions_(Quartz.NSApplicationActivateIgnoringOtherApps)
        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    try
                        tell application "System Events" to tell application process appName
                            set frontmost to true
                            tell window winName to set value of attribute "AXMain" to true
                        end tell
                    end try
                end run"""
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.isActive:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.isActive

    def resize(self, widthOffset: int, heightOffset: int, wait: bool = False) -> bool:
        """
        Resizes the window relative to its current size

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window resized to the given size
        """
        return self.resizeTo(int(self.width + widthOffset), int(self.height + heightOffset), wait)

    resizeRel = resize  # resizeRel is an alias for the resize() method.

    def resizeTo(self, newWidth: int, newHeight: int, wait: bool = False) -> bool:
        """
        Resizes the window to a new width and height

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window resized to the given size
        """
        if not self.title:
            return False

        # https://apple.stackexchange.com/questions/350256/how-to-move-mac-os-application-to-specific-display-and-also-resize-automatically
        cmd = """on run {arg1, arg2, arg3, arg4}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    set sizeW to arg3 as integer
                    set sizeH to arg4 as integer
                    try
                        tell application "System Events" to tell application process appName
                            set size of window winName to {sizeW, sizeH}
                        end tell
                    end try
                end run"""
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title, str(newWidth), str(newHeight)], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.width != newWidth and self.height != newHeight:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.width == newWidth and self.height == newHeight

    def move(self, xOffset: int, yOffset: int, wait: bool = False) -> bool:
        """
        Moves the window relative to its current position

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window moved to the given position
        """
        return self.moveTo(int(self.left + xOffset), int(self.top + yOffset), wait)

    moveRel = move  # moveRel is an alias for the move() method.

    def moveTo(self, newLeft:int, newTop: int, wait: bool = False) -> bool:
        """
        Moves the window to new coordinates on the screen

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window moved to the given position
        """
        if not self.title:
            return False

        # https://apple.stackexchange.com/questions/350256/how-to-move-mac-os-application-to-specific-display-and-also-resize-automatically
        cmd = """on run {arg1, arg2, arg3, arg4}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    set posX to arg3 as integer
                    set posY to arg4 as integer
                    try
                        tell application "System Events" to tell application process appName
                            set position of window winName to {posX, posY}
                        end tell
                    end try
                end run"""
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title, str(newLeft), str(newTop)], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.left != newLeft and self.top != newTop:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.left == newLeft and self.top == newTop

    def _moveResizeTo(self, newLeft: int, newTop: int, newWidth: int, newHeight: int) -> bool:
        if not self.title:
            return False

        cmd = """on run {arg1, arg2, arg3, arg4, arg5, arg6}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    set posX to arg3 as integer
                    set posY to arg4 as integer
                    set sizeW to arg5 as integer
                    set sizeH to arg6 as integer
                    try
                        tell application "System Events" to tell application process appName
                            set position of window winName to {posX, posY}
                            set size of window winName to {sizeW, sizeH}
                        end tell
                    end try
                end run"""
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title,
                                 str(newLeft), str(newTop), str(newWidth), str(newHeight)], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        retries = 0
        while retries < WAIT_ATTEMPTS and self.left != newLeft and self.top != newTop and \
                self.width != newWidth and self.height != newHeight:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return newLeft == self.left and newTop == self.top and newWidth == self.width and newHeight == self.height

    def alwaysOnTop(self, aot: bool = True) -> bool:
        """
        Keeps window on top of all others.

        :param aot: set to ''False'' to deactivate always-on-top behavior
        :return: ''True'' if command succeeded
        """
        # TODO: Is there an attribute or similar to force window always on top?
        ret = True
        if aot:
            if self._tb and self._tb.is_alive():
                self._tb.kill()
            if self._tt is None:
                self._tt = _SendTop(self, interval=0.3)
                # Not sure about the best behavior: stop thread when program ends or keeping sending window on top
                self._tt.setDaemon(True)
                self._tt.start()
            else:
                self._tt.restart()
        elif self._tt:
            self._tt.kill()
        return ret

    def alwaysOnBottom(self, aob: bool = True) -> bool:
        """
        Keeps window below of all others, but on top of desktop icons and keeping all window properties

        :param aob: set to ''False'' to deactivate always-on-bottom behavior
        :return: ''True'' if command succeeded
        """
        # TODO: Is there an attribute or similar to force window always at bottom?
        ret = True
        if aob:
            if self._tt and self._tt.is_alive():
                self._tt.kill()
            if self._tb is None:
                self._tb = _SendBottom(self, interval=0.3)
                # Not sure about the best behavior: stop thread when program ends or keeping sending window below
                self._tb.setDaemon(True)
                self._tb.start()
            else:
                self._tb.restart()
        elif self._tb:
            self._tb.kill()
        return ret

    def lowerWindow(self):
        """
        Lowers the window to the bottom so that it does not obscure any sibling windows

        :return: ''True'' if window lowered
        """
        if not self.title:
            return False

        # https://apple.stackexchange.com/questions/233687/how-can-i-send-the-currently-active-window-to-the-back
        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    try
                        tell application "System Events" to tell application "%s"
                            set winList to every window whose visible is true
                            set index of winName to (count of winList as integer)
                            if not winList = {} then
                                repeat with oWin in (items of reverse of winList)
                                    if not name of oWin = winName then
                                        set index of oWin to 1
                                    end if
                                end repeat
                            end if
                        end tell
                    end try
               end run""" % self._appName
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        return not err

    def raiseWindow(self):
        """
        Raises the window to top so that it is not obscured by any sibling windows.

        :return: ''True'' if window raised
        """
        if not self.title:
            return False

        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    try
                        tell application "System Events" to tell application "%s"
                            tell window winName to set index to 1
                       end tell
                    end try
               end run""" % self._appName
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        return not err

    def sendBehind(self, sb: bool = True) -> bool:
        """
        Sends the window to the very bottom, below all other windows, including desktop icons.
        It may also cause that the window does not accept focus nor keyboard/mouse events as well as
        make the window disappear from taskbar and/or pager.

        :param sb: set to ''False'' to bring the window back to front
        :return: ''True'' if window sent behind desktop icons
        """
        # TODO: Is there an attribute or similar to set window level?
        raise NotImplementedError

    def acceptInput(self, setTo: bool) -> None:
        """Toggles the window transparent to input and focus

        :param setTo: True/False to toggle window transparent to input and focus
        :return: None
        """
        raise NotImplementedError

    def getAppName(self) -> str:
        """
        Get the name of the app current window belongs to

        :return: name of the app as string
        """
        return self._appName

    def getParent(self) -> str:
        """
        Get the handle of the current window parent. It can be another window or an application

        :return: handle (role:name) of the window parent as string. Role can take "AXApplication" or "AXWindow" values according to its type
        """
        if not self.title:
            return ""

        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    set parentRole to ""
                    set parentName to ""
                    try
                        tell application "System Events" to tell application process appName
                            set parentRole to value of attribute "AXRole" of (get value of attribute "AXParent" of window winName)
                            set parentName to value of attribute "AXTitle" of (get value of attribute "AXParent" of window winName)
                        end tell
                    end try
                    return {parentRole, parentName}
               end run"""
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        ret = ret.replace("\n", "")
        entries = ret.replace("\n", "").split(", ")
        role = entries[0]
        parent = ", ".join(entries[1:])
        result = ""
        if role and parent:
            result = role + SEP + parent
        return result

    def getChildren(self):
        """
        Get the children handles of current window

        :return: list of handles (role:name) as string. Role can only be "AXWindow" in this case
        """
        result: list[str] = []
        if not self.title:
            return result

        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    set winChildren to {}
                    try
                        tell application "System Events" to tell application process appName
                            set winChildren to value of attribute "AXChildren" of window winName
                        end tell
                    end try
                    return winChildren
               end run"""
        proc = subprocess.Popen(['osascript', '-s', 's', '-', self._appName, self.title], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        ret = ret.replace("\n", "").replace("{", "['").replace("}", "']").replace('"', '').replace(", ", "', '")
        ret = ast.literal_eval(ret)
        for item in ret:
            if item.startswith("window"):
                res = item[item.find("window ")+len("window "):item.rfind(" of window "+self.title)]
                result.append("AXWindow" + SEP + res)
        return result

    def getHandle(self) -> str:
        """
        Get the current window handle

        :return: window handle (role:name) as string. Role can only be "AXWindow" in this case
        """

        return f"AXWindow{SEP}{self.title}"

    def isParent(self, child: str) -> bool:
        """
        Check if current window is parent of given window (handle)

        :param child: handle or name of the window you want to check if the current window is parent of
        :return: ''True'' if current window is parent of the given window
        """
        children = self.getChildren()
        if SEP not in child:
            child = "AXWindow" + SEP + child
        return child in children
    isParentOf = isParent  # isParentOf is an alias of isParent method

    def isChild(self, parent: str) -> bool:
        """
        Check if current window is child of given window/app (handle)

        :param parent: handle or name of the window/app you want to check if the current window is child of
        :return: ''True'' if current window is child of the given window
        """
        currParent = self.getParent()
        if SEP not in parent:
            part = currParent.split(SEP)
            if len(part) > 1:
                currParent = part[1]
        return currParent == parent
    isChildOf = isChild  # isParentOf is an alias of isParent method

    def getDisplay(self):
        """
        Get display name in which current window space is mostly visible

        :return: display name as string
        """
        screens = getAllScreens()
        name = ""
        for key in screens:
            if pointInRect(self.centerx, self.centery, screens[key]["pos"].x, screens[key]["pos"].y, screens[key]["size"].width, screens[key]["size"].height):
                name = key
                break
        return name

    @property
    def isMinimized(self) -> bool:
        """
        Check if current window is currently minimized

        :return: ``True`` if the window is minimized
        """
        if not self.title:
            return False

        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    set isMin to false
                    try
                        tell application "System Events" to tell application process appName
                            set isMin to value of attribute "AXMinimized" of window winName
                        end tell
                    end try
                    return (isMin as string)
                end run"""
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        ret = ret.replace("\n", "")
        return ret == "true"

    @property
    def isMaximized(self) -> bool:
        """
        Check if current window is currently maximized

        :return: ``True`` if the window is maximized
        """
        if not self.title:
            return False

        if self._use_zoom:
            cmd = """on run {arg1, arg2}
                        set appName to arg1 as string
                        set winName to arg2 as string
                        set isZoomed to false
                        try
                            tell application "System Events" to tell application "%s"
                                set isZoomed to zoomed of window winName
                            end tell
                        end try
                        return (isZoomed as text)
                    end run""" % self._appName
        else:
            cmd = """on run {arg1, arg2}
                        set appName to arg1 as string
                        set winName to arg2 as string
                        set isFull to false
                        try
                            tell application "System Events" to tell application process appName
                                set isFull to value of attribute "AXFullScreen" of window winName
                            end tell
                        end try
                        return (isFull as string)
                    end run"""
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        ret = ret.replace("\n", "")
        return ret == "true"

    @property
    def isActive(self) -> bool:
        """
        Check if current window is currently the active, foreground window

        :return: ``True`` if the window is the active, foreground window
        """
        active = getActiveWindow()
        return active is not None and active._app == self._app and active.title == self.title

    @property
    def title(self) -> str | None:  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
        """
        Get the current window title, as string.
        IMPORTANT: window title may change. In that case, it will return None.
        You can use ''updatedTitle'' to try to find the new window title.
        You can also use ''watchdog'' submodule to be notified in case title changes and try to find the new one (Re-start watchdog in that case).

        :return: title as a string or None
        """
        titles = _getAppWindowsTitles(self._appName)
        if self._winTitle not in titles:
            return ""
        return self._winTitle

    @property
    def updatedTitle(self) -> str:
        """
        Get and updated title by finding a similar window title within same application.
        It uses a similarity check to find the best match in case title changes (no way to effectively detect it).
        This can be useful since this class uses window title to identify the target window.
        If watchdog is activated, it will stop in case title changes.

        IMPORTANT:

        - New title may not belong to the original target window, it is just similar within same application
        - If original title or a similar one is not found, window may still exist

        :return: possible new title, empty if no similar title found or same title if it didn't change, as a string
        """
        titles = _getAppWindowsTitles(self._appName)
        if self._winTitle not in titles:
            newTitles = difflib.get_close_matches(self._winTitle, titles, n=1)  # cutoff=0.6 is the default value
            if newTitles:
                self._winTitle = str(newTitles[0])
            else:
                return ""
        return self._winTitle

    @property
    def visible(self) -> bool:
        """
        Check if current window is visible (minimized windows are also visible)

        :return: ``True`` if the window is currently visible
        """
        return self.title in getAllTitles()

    isVisible = visible  # isVisible is an alias for the visible property.

    @property
    def isAlive(self) -> bool:
        """
        Check if window (and application) still exists (minimized and hidden windows are included as existing)
        :return: ''True'' if window exists
        """
        if not self.title:
            return False

        ret = "false"
        if self._app in WS.runningApplications():
            cmd = """on run {arg1, arg2}
                        set appName to arg1 as string
                        set winName to arg2 as string
                        set isDone to false
                        try
                            tell application "System Events" to tell application "%s"
                                tell window winName to set prevIndex to index
                                set isDone to true
                            end tell
                        end try
                        return (isDone as string)
                   end run""" % self._appName
            proc = subprocess.Popen(['osascript', '-', self._appName, self.title], 
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
            ret, err = proc.communicate(cmd)
            ret = ret.replace("\n", "")
        return ret == "true"

    class _WatchDog:
        """
        Set a watchdog, in a separate Thread, to be notified when some window states change

        Notice that changes will be notified according to the window status at the very moment of instantiating this class

        IMPORTANT: This can be extremely slow in macOS Apple Script version

         Available methods:
        :meth start: Initialize and start watchdog and selected callbacks
        :meth updateCallbacks: Change the states this watchdog is hooked to
        :meth updateInterval: Change the interval to check changes
        :meth kill: Stop the entire watchdog and all its hooks
        :meth isAlive: Check if watchdog is running
        """
        def __init__(self, parent: MacOSWindow):
            self._watchdog = None
            self._parent = parent

        def start(
            self,
            isAliveCB: Callable[[bool], None] | None = None,
            isActiveCB: Callable[[bool], None] | None = None,
            isVisibleCB: Callable[[bool], None] | None = None,
            isMinimizedCB: Callable[[bool], None] | None = None,
            isMaximizedCB: Callable[[bool], None] | None = None,
            resizedCB: Callable[[tuple[float, float]], None] | None = None,
            movedCB: Callable[[tuple[float, float]], None] | None = None,
            changedTitleCB: Callable[[str], None] | None = None,
            changedDisplayCB: Callable[[str], None] | None = None,
            interval: float = 0.3
        ):
            """
            Initialize and start watchdog and hooks (callbacks to be invoked when desired window states change)

            Notice that changes will be notified according to the window status at the very moment of execute start()

            The watchdog is asynchronous, so notifications will not be immediate (adjust interval value to your needs)

            The callbacks definition MUST MATCH their return value (boolean, string or (int, int))

            IMPORTANT: This can be extremely slow in macOS Apple Script version

            :param isAliveCB: callback to call if window is not alive. Set to None to not to watch this
                            Returns the new alive status value (False)
            :param isActiveCB: callback to invoke if window changes its active status. Set to None to not to watch this
                            Returns the new active status value (True/False)
            :param isVisibleCB: callback to invoke if window changes its visible status. Set to None to not to watch this
                            Returns the new visible status value (True/False)
            :param isMinimizedCB: callback to invoke if window changes its minimized status. Set to None to not to watch this
                            Returns the new minimized status value (True/False)
            :param isMaximizedCB: callback to invoke if window changes its maximized status. Set to None to not to watch this
                            Returns the new maximized status value (True/False)
            :param resizedCB: callback to invoke if window changes its size. Set to None to not to watch this
                            Returns the new size (width, height)
            :param movedCB: callback to invoke if window changes its position. Set to None to not to watch this
                            Returns the new position (x, y)
            :param changedTitleCB: callback to invoke if window changes its title. Set to None to not to watch this
                            Returns the new title (as string)
            :param changedDisplayCB: callback to invoke if window changes display. Set to None to not to watch this
                            Returns the new display name (as string)
            :param interval: set the interval to watch window changes. Default is 0.3 seconds
            """
            if self._watchdog is None:
                self._watchdog = _WinWatchDog(self._parent, isAliveCB, isActiveCB, isVisibleCB, isMinimizedCB,
                                              isMaximizedCB, resizedCB, movedCB, changedTitleCB, changedDisplayCB,
                                              interval)
                self._watchdog.setDaemon(True)
                self._watchdog.start()
            else:
                self._watchdog.restart(isAliveCB, isActiveCB, isVisibleCB, isMinimizedCB,
                                       isMaximizedCB, resizedCB, movedCB, changedTitleCB, changedDisplayCB,
                                       interval)

        def updateCallbacks(
            self,
            isAliveCB: Callable[[bool], None] | None = None,
            isActiveCB: Callable[[bool], None] | None = None,
            isVisibleCB: Callable[[bool], None] | None = None,
            isMinimizedCB: Callable[[bool], None] | None = None,
            isMaximizedCB: Callable[[bool], None] | None = None,
            resizedCB: Callable[[tuple[float, float]], None] | None = None,
            movedCB: Callable[[tuple[float, float]], None] | None = None,
            changedTitleCB: Callable[[str], None] | None = None,
            changedDisplayCB: Callable[[str], None] | None = None
        ):
            """
            Change the states this watchdog is hooked to

            The callbacks definition MUST MATCH their return value (boolean, string or (int, int))

            IMPORTANT: When updating callbacks, remember to set ALL desired callbacks or they will be deactivated

            IMPORTANT: Remember to set ALL desired callbacks every time, or they will be defaulted to None (and unhooked)

            :param isAliveCB: callback to call if window is not alive. Set to None to not to watch this
                            Returns the new alive status value (False)
            :param isActiveCB: callback to invoke if window changes its active status. Set to None to not to watch this
                            Returns the new active status value (True/False)
            :param isVisibleCB: callback to invoke if window changes its visible status. Set to None to not to watch this
                            Returns the new visible status value (True/False)
            :param isMinimizedCB: callback to invoke if window changes its minimized status. Set to None to not to watch this
                            Returns the new minimized status value (True/False)
            :param isMaximizedCB: callback to invoke if window changes its maximized status. Set to None to not to watch this
                            Returns the new maximized status value (True/False)
            :param resizedCB: callback to invoke if window changes its size. Set to None to not to watch this
                            Returns the new size (width, height)
            :param movedCB: callback to invoke if window changes its position. Set to None to not to watch this
                            Returns the new position (x, y)
            :param changedTitleCB: callback to invoke if window changes its title. Set to None to not to watch this
                            Returns the new title (as string)
            :param changedDisplayCB: callback to invoke if window changes display. Set to None to not to watch this
                            Returns the new display name (as string)
            """
            if self._watchdog:
                self._watchdog.updateCallbacks(isAliveCB, isActiveCB, isVisibleCB, isMinimizedCB, isMaximizedCB,
                                              resizedCB, movedCB, changedTitleCB, changedDisplayCB)

        def updateInterval(self, interval: float = 0.3):
            """
            Change the interval to check changes

            :param interval: set the interval to watch window changes. Default is 0.3 seconds
            """
            if self._watchdog:
                self._watchdog.updateInterval(interval)

        def setTryToFind(self, tryToFind: bool):
            """
            In macOS Apple Script version, if set to ''True'' and in case title changes, watchdog will try to find
            a similar title within same application to continue monitoring it. It will stop if set to ''False'' or
            a similar title is not found.

            IMPORTANT:

            - It will have no effect in other platforms (Windows and Linux) and classes (MacOSNSWindow)
            - This behavior is deactivated by default, so you need to explicitly activate it

            :param tryToFind: set to ''True'' to try to find a similar title. Set to ''False'' to deactivate this behavior
            """
            if self._watchdog:
                self._watchdog.setTryToFind(tryToFind)

        def stop(self):
            """
            Stop the entire WatchDog and all its hooks
            """
            if self._watchdog:
                self._watchdog.kill()

        def isAlive(self):
            """Check if watchdog is running

            :return: ''True'' if watchdog is alive
            """
            try:
                alive = bool(self._watchdog and self._watchdog.is_alive())
            except:
                alive = False
            return alive

    class _Menu:

        def __init__(self, parent: MacOSWindow):
            self._parent = parent
            self._menuStructure: dict[str, _SubMenuStructure] = {}
            self.menuList: list[str] = []
            self.itemList: list[str] = []

        def getMenu(self, addItemInfo: bool = False) -> dict[str, _SubMenuStructure]:
            """
            Loads and returns Menu options, sub-menus and related information, as dictionary.

            It is HIGHLY RECOMMENDED to pre-load the Menu struct by explicitly calling getMenu()
            before invoking any other method.

            WARNING: "item_info" is extremely huge and slow. Instead use getMenuItemInfo() method individually

            WARNING: Notice there are "hidden" menu entries which are not visible, but are returned
            when querying menu. These entries do not have position nor size.

            :param addItemInfo: if ''True'', adds "item_info" struct and "shortcut" to the output
                                "item_info" is extremely huge and slow. Instead use getMenuItemInfo() method individually
            :return: python dictionary with MENU struct

            Output Format:
                Key:
                    item (option or sub-menu) title

                Values:
                    "parent":
                        parent sub-menu handle (main menu handle for level-0 items)


                        item handle (!= 0 for sub-menu items only)
                    "wID":
                        item ID (required for other actions, e.g. clickMenuItem())
                    "rect":
                        Rect struct of the menu item (relative to window position)
                    "item_info" (optional):
                        MENUITEMINFO struct containing all avialable menu item info
                    "shortcut" (optional):
                        shortcut to menu item, if any. Included only if item_info is included as well (addItemInfo=True)
                    "entries":
                        sub-items within the sub-menu (if any)
            """
            self._menuStructure = {}
            self.menuList = []
            self.itemList = []

            nameList: list[Incomplete] = []
            # Nested recursive types. Dept based on size of nameList.
            # Very complex to type.
            sizeList: list[Sequence[Any]] = []
            posList: list[Sequence[Any]] = []
            attrList: list[Sequence[Any]] = []

            def findit():

                level = 0

                while True:
                    part = ""
                    for lev in range(level):
                        if lev % 2 == 0:
                            part = " of every menu" + part
                        else:
                            part = " of every menu item" + part
                    subCmd1 = "set nameList to name" + part + " of every menu bar item"
                    subCmd2 = "set sizeList to size" + part + " of every menu bar item"
                    subCmd3 = "set posList to position" + part + " of every menu bar item"
                    if addItemInfo:
                        subCmd4 = "set attrList to properties of every attribute" + part + " of every menu bar item"
                    else:
                        subCmd4 = "set attrList to {}"

                    if level % 2 == 0:  # Grabbing items only (menus will have non-empty lists on the next level)

                        cmd = """on run arg1
                                    set procName to arg1 as string
                                    set nameList to {}
                                    set sizeList to {}
                                    set posList to {}
                                    set attrList to {}
                                    try
                                        tell application "System Events"
                                            tell process procName
                                                tell menu bar 1
                                                    %s
                                                    %s
                                                    %s
                                                    %s
                                                end tell
                                            end tell
                                        end tell
                                    end try
                                    return {nameList, sizeList, posList, attrList}
                                end run
                                """ % (subCmd1, subCmd2, subCmd3, subCmd4)
                        # https://stackoverflow.com/questions/69774133/how-to-use-global-variables-inside-of-an-applescript-function-for-a-python-code
                        # Didn't find a way to get the "injected code" working if passed this way
                        proc = subprocess.Popen(['osascript', '-s', 's', '-', str(self._parent._app.localizedName())],
                                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
                        ret, err = proc.communicate(cmd)
                        if addItemInfo:
                            ret = ret.replace("\n", "").replace("\t", "").replace('missing value', '"missing value"') \
                                .replace("{", "[").replace("}", "]").replace("value:", "'") \
                                .replace(", class:", "', '").replace(", settable:", "', '").replace(", name:", "', ")
                        else:
                            ret = ret.replace("\n", "").replace("\t", "").replace('missing value', '"missing value"') \
                                .replace("{", "[").replace("}", "]")
                        item = ast.literal_eval(ret)

                        if err is None and not self._isListEmpty(item[0]):
                            nameList.append(item[0])
                            sizeList.append(item[1])
                            posList.append(item[2])
                            attrList.append(item[3])
                        else:
                            break
                    level += 1

                return nameList

            def fillit():

                def subfillit(
                    subNameList: Iterable[str],
                    subSizeList: Sequence[tuple[int,int] | Literal["missing value"]],
                    subPosList: Sequence[tuple[int,int] | Literal["missing value"]],
                    subAttrList: Sequence[Attribute],
                    section: str = "",
                    level: int = 0,
                    mainlevel: int = 0,
                    path: Sequence[int] | None = None,
                    parent: int = 0,
                ):
                    path = list(path or [])
                    option = self._menuStructure
                    if section:
                        for sec in section.split(SEP):
                            if sec:
                                option = cast("dict[str, _SubMenuStructure]", option[sec])

                    for i, name in enumerate(subNameList):
                        pos = subPosList[i] if len(subPosList) > i else "missing value"
                        size = subSizeList[i] if len(subSizeList) > i else "missing value"
                        attr: str | Attribute = subAttrList[i] if (addItemInfo and len(subAttrList) > 0) else []
                        if not name:
                            continue
                        elif name == "missing value":
                            name = "separator"
                            option[name] = {}
                        else:
                            ref = section.replace(SEP + "entries", "") + SEP + name
                            option[name] = {"parent": parent, "wID": self._getNewWid(ref)}
                            if size and pos and size != "missing value" and pos != "missing value":
                                x, y = pos
                                w, h = size
                                option[name]["rect"] = Rect(x, y, x + w, y + h)
                            if addItemInfo and attr:
                                item_info = self._parseAttr(attr)
                                option[name]["item_info"] = item_info
                                option[name]["shortcut"] = self._getaccesskey(item_info)
                            if level + 1 < len(nameList):
                                submenu = nameList[level + 1][mainlevel][0]
                                subPos = posList[level + 1][mainlevel][0]
                                subSize = sizeList[level + 1][mainlevel][0]
                                subAttr: Any = attrList[level + 1][mainlevel][0] if addItemInfo else []
                                subPath = path[3:] + ([0] * (level - 3)) + [i, 0] + ([0] * (level - 2))
                                for j in subPath:
                                    if len(submenu) > j and isinstance(submenu[j], list):
                                        submenu = submenu[j]
                                        subPos = subPos[j]
                                        subSize = subSize[j]
                                        subAttr = subAttr[j] if addItemInfo else []
                                    else:
                                        break
                                if submenu:
                                    option[name]["hSubMenu"] = self._getNewHSubMenu(ref)
                                    option[name]["entries"] = {}
                                    subfillit(submenu, subSize, subPos, subAttr,
                                              section + SEP + name + SEP + "entries",
                                              level=level + 1, mainlevel=mainlevel, path=[level+1, mainlevel, 0]+subPath,
                                              parent=hSubMenu)
                                else:
                                    option[name]["hSubMenu"] = 0

                for i, item in enumerate(cast("list[str]", nameList[0])):
                    hSubMenu = self._getNewHSubMenu(item)
                    self._menuStructure[item] = {"hSubMenu": hSubMenu, "wID": self._getNewWid(item), "entries": {}}
                    subfillit(nameList[1][i][0], sizeList[1][i][0], posList[1][i][0], attrList[1][i][0] if addItemInfo else [],
                              item + SEP + "entries", level=1, mainlevel=i, path=[1, i, 0], parent=hSubMenu)

            if findit(): fillit()

            return self._menuStructure

        def clickMenuItem(self, itemPath: Sequence[str] | None = None, wID: int = 0) -> bool:
            """
            Simulates a click on a menu item

            Notes:
                - It will not work for men/sub-menu entries
                - It will not work if selected option is disabled

            Use one of these input parameters to identify desired menu item:

            :param itemPath: desired menu option and predecessors as list (e.g. ["Menu", "SubMenu", "Item"]). Notice it is language-dependent, so it's better to fulfill it from MENU struct as returned by :meth: getMenu()
            :param wID: item ID within menu struct (as returned by getMenu() method)
            :return: ''True'' if menu item to click is correct and exists (not if it has already been clicked or it had any effect)
            """
            found = False
            if self._checkMenuStruct():
                if not itemPath and wID > 0:
                    itemPath = self._getPathFromWid(wID)

                if itemPath and len(itemPath) > 1:
                    found = True
                    part = ""
                    for i, item in enumerate(itemPath[1:-1]):
                        if i % 2 == 0:
                            part = str(' of menu "%s" of menu item "%s"' % (item, item)) + part
                        else:
                            part = str(' of menu item "%s" of menu "%s"' % (item, item)) + part
                    subCmd = str('click menu item "%s"' % itemPath[-1]) + part + str(' of menu "%s" of menu bar item "%s"' % (itemPath[0], itemPath[0]))

                    cmd = """on run arg1
                                set procName to arg1 as string
                                try
                                    tell application "System Events"
                                        tell process procName
                                            tell menu bar 1
                                                %s
                                            end tell
                                        end tell
                                    end tell
                                end try
                            end run
                            """ % subCmd

                    proc = subprocess.Popen(['osascript', '-s', 's', '-', str(self._parent._app.localizedName())], 
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
                    ret, err = proc.communicate(cmd)

            return found

        def getMenuInfo(self, hSubMenu: int):
            """
            Returns the MENUINFO struct of the given sub-menu or main menu if none given

            Format:
                Key:
                    attribute name

                Values:
                    "value":"
                        value of attribute
                    "class":
                        class of attribute
                    "settable":
                        indicates if attribute can be modified (true/false)

            :param hSubMenu: id of the sub-menu entry (as returned by getMenu() method)
            :return: MENUINFO struct
            """
            return self.getMenuItemInfo(hSubMenu, -1)

        def getMenuItemCount(self, hSubMenu: int) -> int:
            """
            Returns the number of items within a menu (main menu if no sub-menu given)

            :param hSubMenu: id of the sub-menu entry (as returned by getMenu() method)
            :return: number of items as int
            """
            count = 0
            if self._checkMenuStruct():
                menuPath = self._getPathFromHSubMenu(hSubMenu)

                if menuPath:
                    part = ""
                    for i, item in enumerate(menuPath[:-1]):
                        if i % 2 == 0:
                            part = str(' of menu "%s"' % item) + part
                        else:
                            part = str(' of menu item "%s"' % item) + part
                    subCmd = 'set itemCount to count of every menu item' + part + str(' of menu bar item "%s"' % menuPath[0])

                    cmd = """on run arg1
                                set procName to arg1 as string
                                set itemCount to 0
                                try
                                    tell application "System Events"
                                        tell process procName
                                            tell menu bar 1
                                                %s
                                            end tell
                                        end tell
                                    end tell
                                end try
                                return itemCount as integer
                            end run
                            """ % subCmd

                    proc = subprocess.Popen(['osascript', '-s', 's', '-', str(self._parent._app.localizedName())], 
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
                    ret, err = proc.communicate(cmd)
                    ret = ret.replace("\n", "")
                    if ret.isnumeric():
                        count = int(ret)

            return count

        def getMenuItemInfo(self, hSubMenu: int, wID: int):
            """
            Returns the MENUITEMINFO struct for the given menu item

            Format:
                Key:
                    attribute name

                Values:
                    "value":"
                        value of attribute
                    "class":
                        class of attribute
                    "settable":
                        indicates if attribute can be modified (true/false)

            :param hSubMenu: id of the sub-menu entry (as returned by :meth: getMenu())
            :param wID: id of the window within menu struct (as returned by :meth: getMenu())
            :return: MENUITEMINFO struct
            """
            itemInfo = {}
            if self._checkMenuStruct():
                if wID == -1:
                    itemPath = self._getPathFromHSubMenu(hSubMenu)
                else:
                    itemPath = self._getPathFromWid(wID)

                if itemPath:
                    part = ""
                    for lev, item in enumerate(itemPath[:-1]):
                        if lev % 2 == 0:
                            part = str(' of menu "%s"' % item) + part
                        else:
                            part = str(' of menu item "%s"' % item) + part
                    subCmd = str('set attrList to properties of every attribute of menu item "%s"' % itemPath[-1]) + part + str(' of menu bar item "%s"' % itemPath[0])
                    # subCmd2 = str('set propList to properties of menu item "%s"' % itemPath[-1]) + part + str(' of menu bar item "%s"' % itemPath[0])

                    cmd = """on run arg1
                                set procName to arg1 as string
                                set attrList to {}
                                    tell application "System Events"
                                        tell process procName
                                            tell menu bar 1
                                                %s
                                            end tell
                                        end tell
                                    end tell
                                return attrList
                            end run
                            """ % subCmd
                    # https://stackoverflow.com/questions/69774133/how-to-use-global-variables-inside-of-an-applescript-function-for-a-python-code
                    # Didn't find a way to get the "injected code" working if passed this way
                    proc = subprocess.Popen(['osascript', '-s', 's', '-', str(self._parent._app.localizedName())], 
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
                    ret, err = proc.communicate(cmd)
                    itemInfo = self._parseAttr(ret)

            return itemInfo

        def getMenuItemRect(self, hSubMenu: int, wID: int) -> Rect:
            """
            Get the Rect struct (left, top, right, bottom) of the given Menu option

            :param hSubMenu: id of the sub-menu entry (as returned by :meth: getMenu())
            :param wID: id of the window within menu struct (as returned by :meth: getMenu())
            :return: Rect struct
            """
            x = y = w = h = 0
            if self._checkMenuStruct():
                menuPath = self._getPathFromHSubMenu(hSubMenu)
                itemPath = self._getPathFromWid(wID)

                if itemPath and menuPath and len(itemPath) > 1 and itemPath[:-1] == menuPath:
                    part = ""
                    for i, item in enumerate(itemPath[1:-1]):
                        if i % 2 == 0:
                            part = str(' of menu "%s" of menu item "%s"' % (item, item)) + part
                        else:
                            part = str(' of menu item "%s" of menu "%s"' % (item, item)) + part
                    subCmd = str('set itemRect to {position, size} of menu item "%s"' % itemPath[-1]) + part + str(' of menu "%s" of menu bar item "%s"' % (itemPath[0], itemPath[0]))

                    cmd = """on run arg1
                                set procName to arg1 as string
                                set itemRect to {{0, 0}, {0, 0}}
                                try
                                    tell application "System Events"
                                        tell process procName
                                            tell menu bar 1
                                                %s
                                            end tell
                                        end tell
                                    end tell
                                end try
                                return itemRect
                            end run
                            """ % subCmd

                    proc = subprocess.Popen(['osascript', '-s', 's', '-', str(self._parent._app.localizedName())], 
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
                    ret, err = proc.communicate(cmd)
                    ret = ret.replace("\n", "").replace("{", "[").replace("}", "]")
                    rect = ast.literal_eval(ret)
                    x, y = rect[0]
                    w, h = rect[1]

            return Rect(x, y, x + w, y + h)

        def _isListEmpty(self, inList: list[Any]):
            # https://stackoverflow.com/questions/1593564/python-how-to-check-if-a-nested-list-is-essentially-empty/51582274
            if isinstance(inList, list):
                return all(map(self._isListEmpty, inList))
            return False

        def _parseAttr(self, attr: str | Attribute):

            itemInfo: dict[str, _ItemInfoValue] = {}
            if isinstance(attr, str):
                attr = attr.replace("\n", "").replace('missing value', '"missing value"') \
                    .replace("{", "[").replace("}", "]").replace("value:", "'") \
                    .replace(", class:", "', '").replace(", settable:", "', '").replace(", name:", "', ")
                items: Attribute = ast.literal_eval(attr)
            else:
                items = attr
            for item in items:
                if len(item) >= 4:
                    itemInfo[item[3]] = {"value": item[0], "class": item[1], "settable": item[2]}

            return itemInfo

        def _checkMenuStruct(self):
            if not self._menuStructure:
                self.getMenu()
            return self._menuStructure

        def _getNewWid(self, ref: str):
            self.itemList.append(ref)
            return len(self.itemList)

        def _getPathFromWid(self, wID: int):
            itemPath = []
            if self._checkMenuStruct():
                if 0 < wID <= len(self.itemList):
                    itemPath = self.itemList[wID - 1].split(SEP)
            return itemPath

        def _getNewHSubMenu(self, ref: str):
            self.menuList.append(ref)
            return len(self.menuList)

        def _getPathFromHSubMenu(self, hSubMenu: int):
            menuPath = []
            if self._checkMenuStruct():
                if 0 < hSubMenu <= len(self.menuList):
                    menuPath = self.menuList[hSubMenu - 1].split(SEP)
            return menuPath

        def _getMenuItemWid(self, itemPath: str):
            wID = 0
            if itemPath:
                option = self._menuStructure
                for item in itemPath[:-1]:
                    entries = option.get(item, {}).get("entries", None)
                    if entries:
                        option = entries
                    else:
                        option = {}
                        break
                wID = option.get(itemPath[-1], {}).get("wID", 0)
            return wID

        def _getaccesskey(self, item_info: dict[str, dict[str, str]] | dict[str, _ItemInfoValue]):
            # https://github.com/babarrett/hammerspoon/blob/master/cheatsheets.lua
            # https://github.com/pyatom/pyatom/blob/master/atomac/ldtpd/core.py

            mods = ["<command", "<shift><command", "<option><command>", "<option><shift><command>",
                    "<control><command>", "<control><option><command>", "", "<tab>", "", "<option>",
                    "<option><shift>", "<control>", "<control><shift>", "<control><option>"]

            try:
                key = item_info["AXMenuItemCmdChar"]["value"]
            except:
                key = ""
            try:
                modifiers = int(item_info["AXMenuItemCmdModifiers"]["value"])
            except:
                modifiers = -1
            try:
                glyph = int(item_info["AXMenuItemCmdGlyph"]["value"])
            except:
                glyph = -1
            try:
                virtual_key = int(item_info["AXMenuItemCmdVirtualKey"]["value"])
            except:
                virtual_key = -1

            modifiers_type = ""
            if modifiers < len(mods):
                modifiers_type = mods[modifiers]

            # Probably, this is not exhaustive
            # Scroll up
            if virtual_key == 115 and glyph == 102:
                modifiers_type = "<option>"
                key = "<left>"
            # Scroll down
            elif virtual_key == 119 and glyph == 105:
                modifiers_type = "<option>"
                key = "<right>"
            # Page up
            elif virtual_key == 116 and glyph == 98:
                modifiers_type = "<option>"
                key = "<up>"
            # Page down
            elif virtual_key == 121 and glyph == 107:
                modifiers_type = "<option>"
                key = "<down>"
            # Line up
            elif virtual_key == 126 and glyph == 104:
                key = "<up>"
            # Line down
            elif virtual_key == 125 and glyph == 106:
                key = "<down>"
            # Noticed in  Google Chrome navigating next tab
            elif virtual_key == 124 and glyph == 101:
                key = "<right>"
            # Noticed in  Google Chrome navigating previous tab
            elif virtual_key == 123 and glyph == 100:
                key = "<left>"
            # list application in a window to Force Quit
            elif virtual_key == 53 and glyph == 27:
                key = "<escape>"

            if not key:
                modifiers_type = ""

            return modifiers_type + key


class _SendTop(threading.Thread):

    def __init__(self, hWnd: MacOSWindow | MacOSNSWindow, interval: float = 0.5):
        threading.Thread.__init__(self)
        self._hWnd = hWnd
        self._interval = interval
        self._kill = threading.Event()

    def run(self):
        while not self._kill.is_set():
            if not self._hWnd.isActive:
                self._hWnd.activate()
            self._kill.wait(self._interval)

    def kill(self):
        self._kill.set()

    def restart(self):
        self.kill()
        self._kill = threading.Event()
        self.run()


class _SendBottom(threading.Thread):

    def __init__(self, hWnd: MacOSWindow, interval: float = 0.5):
        threading.Thread.__init__(self)
        self._hWnd = hWnd
        self._app = hWnd._app
        self._appPID = hWnd._appPID
        self._interval = interval
        self._kill = threading.Event()
        _apps = _getAllApps()
        self._apps: list[AppKit.NSRunningApplication] = []
        for app in _apps:
            if app.processIdentifier() != self._appPID:
                self._apps.append(app)

    def run(self):
        while not self._kill.is_set():
            if self._hWnd.isActive:
                self._hWnd.lowerWindow()
                for app in self._apps:
                    try:
                        app.activateWithOptions_(Quartz.NSApplicationActivateIgnoringOtherApps)
                    except:
                        continue
            self._kill.wait(self._interval)

    def kill(self):
        self._kill.set()

    def restart(self):
        self.kill()
        self._kill = threading.Event()
        self.run()


class MacOSNSWindow(BaseWindow):
    @property
    def _rect(self):
        return self.__rect

    def __init__(self, app: AppKit.NSApplication, hWnd: AppKit.NSWindow):
        super().__init__()
        self._app = app
        self._hWnd = hWnd
        self._parent = hWnd.parentWindow()
        self.__rect = self._rectFactory()
        self.watchdog = self._WatchDog(self)

    def _getWindowRect(self) -> Rect:
        frame = self._hWnd.frame()
        res = resolution()
        x = int(frame.origin.x)
        y = int(res.height) - int(frame.origin.y) - int(frame.size.height)
        w = x + int(frame.size.width)
        h = y + int(frame.size.height)
        return Rect(x, y, w, h)

    def getExtraFrameSize(self, includeBorder: bool = True) -> tuple[int, int, int, int]:
        """
        Get the extra space, in pixels, around the window, including or not the border

        :param includeBorder: set to ''False'' to avoid including borders
        :return: (left, top, right, bottom) frame size as a tuple of int
        """
        borderWidth = 0
        if includeBorder:
            ret = self._hWnd.contentRectForFrameRect_(self._hWnd.frame())
            borderWidth = ret.left - self.left
        frame = (borderWidth, borderWidth, borderWidth, borderWidth)
        return frame

    def getClientFrame(self):
        """
        Get the client area of window, as a Rect (x, y, right, bottom)
        Notice that scroll bars will be included within this area

        :return: Rect struct
        """
        frame = self._hWnd.contentRectForFrameRect_(self._hWnd.frame())
        res = resolution()
        x = int(frame.origin.x)
        y = int(res.height) - int(frame.origin.y) - int(frame.size.height)
        r = x + int(frame.size.width)
        b = y + int(frame.size.height)
        return Rect(x, y, r, b)

    def __repr__(self):
        return '%s(hWnd=%s)' % (self.__class__.__name__, self._hWnd)

    def __eq__(self, other: object):
        return isinstance(other, MacOSNSWindow) and self._hWnd == other._hWnd

    def close(self) -> bool:
        """
        Closes this window. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from
        actually closing. This is identical to clicking the X button on the
        window.

        :return: ''True'' if window is closed
        """
        return self._hWnd.performClose_(self._app)

    def minimize(self, wait: bool = False) -> bool:
        """
        Minimizes this window

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :return: ''True'' if window minimized
        """
        if not self.isMinimized:
            self._hWnd.performMiniaturize_(self._app)
            retries = 0
            while wait and retries < WAIT_ATTEMPTS and not self.isMinimized:
                retries += 1
                time.sleep(WAIT_DELAY * retries)
        return self.isMinimized

    def maximize(self, wait: bool = False) -> bool:
        """
        Maximizes this window

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :return: ''True'' if window maximized
        """
        if not self.isMaximized:
            self._hWnd.performZoom_(self._app)
            retries = 0
            while wait and retries < WAIT_ATTEMPTS and not self.isMaximized:
                retries += 1
                time.sleep(WAIT_DELAY * retries)
        return self.isMaximized

    def restore(self, wait: bool = False, user: bool = True) -> bool:
        """
        If maximized or minimized, restores the window to it's normal size

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :param user: ignored on macOS platform
        :return: ''True'' if window restored
        """
        self.activate(wait=True)
        if self.isMaximized:
            self._hWnd.performZoom_(self._app)
        if self.isMinimized:
            self._hWnd.deminiaturize_(self._app)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and (self.isMinimized or self.isMaximized):
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self.isMaximized and not self.isMinimized

    def show(self, wait: bool = False) -> bool:
        """
        If hidden or showing, shows the window on screen and in title bar

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window showed
        """
        self.activate(wait=wait)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.visible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.visible

    def hide(self, wait: bool = False) -> bool:
        """
        If hidden or showing, hides the window from screen and title bar

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window hidden
        """
        self._hWnd.orderOut_(self._app)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.visible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self.visible

    def activate(self, wait: bool = False, user: bool = True) -> bool:
        """
        Activate this window and make it the foreground (focused) window

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :param user: ignored on macOS platform
        :return: ''True'' if window activated
        """
        self._app.activateIgnoringOtherApps_(True)
        self._hWnd.makeKeyAndOrderFront_(self._app)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.isActive:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.isActive

    def resize(self, widthOffset: int, heightOffset: int, wait: bool = False) -> bool:
        """
        Resizes the window relative to its current size

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window resized to the given size
        """
        return self.resizeTo(int(self.width + widthOffset), int(self.height + heightOffset), wait)

    resizeRel = resize  # resizeRel is an alias for the resize() method.

    def resizeTo(self, newWidth: int, newHeight: int, wait: bool = False) -> bool:
        """
        Resizes the window to a new width and height

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window resized to the given size
        """
        self._hWnd.setFrame_display_animate_(
            AppKit.NSMakeRect(self.bottomleft.x, self.bottomleft.y, newWidth, newHeight),
            True,
            True
        )
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.width != newWidth and self.height != newHeight:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.width == newWidth and self.height == newHeight

    def move(self, xOffset: int, yOffset: int, wait: bool = False) -> bool:
        """
        Moves the window relative to its current position

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window moved to the given position
        """
        return self.moveTo(int(self.left + xOffset), int(self.top + yOffset), wait)

    moveRel = move  # moveRel is an alias for the move() method.

    def moveTo(self, newLeft:int, newTop: int, wait: bool = False) -> bool:
        """
        Moves the window to new coordinates on the screen

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window moved to the given position
        """
        self._hWnd.setFrame_display_animate_(AppKit.NSMakeRect(newLeft, resolution().height - newTop - self.height, self.width, self.height), True, True)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.left != newLeft and self.top != newTop:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.left == newLeft and self.top == newTop

    def _moveResizeTo(self, newLeft: int, newTop: int, newWidth: int, newHeight: int) -> bool:
        self._hWnd.setFrame_display_animate_(AppKit.NSMakeRect(newLeft, resolution().height - newTop - newHeight, newWidth, newHeight), True, True)
        return self.left == newLeft and self.top == newTop and self.width == newWidth and self.height == newHeight

    def alwaysOnTop(self, aot: bool = True) -> bool:
        """
        Keeps window on top of all others.

        :param aot: set to ''False'' to deactivate always-on-top behavior
        :return: ''True'' if command succeeded
        """
        if aot:
            ret = self._hWnd.setLevel_(Quartz.kCGScreenSaverWindowLevel)
        else:
            ret = self._hWnd.setLevel_(Quartz.kCGNormalWindowLevel)
        return ret

    def alwaysOnBottom(self, aob: bool = True) -> bool:
        """
        Keeps window below of all others, but on top of desktop icons and keeping all window properties

        :param aob: set to ''False'' to deactivate always-on-bottom behavior
        :return: ''True'' if command succeeded
        """
        if aob:
            ret = self._hWnd.setLevel_(Quartz.kCGDesktopWindowLevel)
        else:
            ret = self._hWnd.setLevel_(Quartz.kCGNormalWindowLevel)
        return ret

    def lowerWindow(self) -> bool:
        """
        Lowers the window to the bottom so that it does not obscure any sibling windows

        :return: ''True'' if window lowered
        """
        # self._hWnd.orderBack_(self._app)  # Not working or using it wrong???
        windows = self._app.orderedWindows()
        ret = False
        if windows:
            windows.reverse()
            for win in windows:
                if win != self._hWnd:
                    ret = win.makeKeyAndOrderFront_(self._app)
        return ret

    def raiseWindow(self, sb: bool = True) -> bool:
        """
        Raises the window to top so that it is not obscured by any sibling windows.

        :return: ''True'' if window raised
        """
        return self._hWnd.makeKeyAndOrderFront_(self._app)

    def sendBehind(self, sb: bool = True) -> bool:
        """
        Sends the window to the very bottom, below all other windows, including desktop icons.
        It may also cause that the window does not accept focus nor keyboard/mouse events as well as
        make the window disappear from taskbar and/or pager.

        :param sb: set to ''False'' to bring the window back to front
        :return: ''True'' if window sent behind desktop icons
        """
        # https://stackoverflow.com/questions/4982584/how-do-i-draw-the-desktop-on-mac-os-x
        if sb:
            ret1 = self._hWnd.setLevel_(Quartz.kCGDesktopWindowLevel - 1)
            ret2 = self._hWnd.setCollectionBehavior_(Quartz.NSWindowCollectionBehaviorCanJoinAllSpaces |
                                                     Quartz.NSWindowCollectionBehaviorStationary |
                                                     Quartz.NSWindowCollectionBehaviorIgnoresCycle)
        else:
            ret1 = self._hWnd.setLevel_(Quartz.kCGNormalWindowLevel)
            ret2 = self._hWnd.setCollectionBehavior_(Quartz.NSWindowCollectionBehaviorDefault |
                                                     Quartz.NSWindowCollectionBehaviorParticipatesInCycle |
                                                     Quartz.NSWindowCollectionBehaviorManaged)
        return ret1 and ret2

    def acceptInput(self, setTo: bool) -> None:
        """Toggles the window transparent to input and focus

        :param setTo: True/False to toggle window transparent to input and focus
        :return: None
        """
        # https://stackoverflow.com/questions/53248592/stop-nswindow-from-receiving-input-events-temporarily
        # https://stackoverflow.com/questions/12677976/nswindow-ignore-mouse-keyboard-events
        self._hWnd.setIgnoresMouseEvents_(not setTo)

    def getAppName(self) -> str:
        """
        Get the name of the app current window belongs to

        :return: name of the app as string
        """
        return self._app.localizedName()

    def getParent(self) -> int:
        """
        Get the handle of the current window parent. It can be another window or an application

        :return: handle of the window parent
        """
        return self._hWnd.parentWindow()

    def getChildren(self) -> list[int]:
        """
        Get the children handles of current window

        :return: list of handles
        """
        return self._hWnd.childWindows()

    def getHandle(self):
        """
        Get the current window handle

        :return: window handle
        """
        return self._hWnd

    def isParent(self, child: AppKit.NSWindow) -> bool:
        """
        Check if current window is parent of given window (handle)

        :param child: handle of the window you want to check if the current window is parent of
        :return: ''True'' if current window is parent of the given window
        """
        return child.parentWindow() == self._hWnd
    isParentOf = isParent  # isParentOf is an alias of isParent method

    def isChild(self, parent: int) -> bool:
        """
        Check if current window is child of given window/app (handle)

        :param parent: handle of the window/app you want to check if the current window is child of
        :return: ''True'' if current window is child of the given window
        """
        return parent == self.getParent()
    isChildOf = isChild  # isChildOf is an alias of isParent method

    def getDisplay(self):
        """
        Get display name in which current window space is mostly visible

        :return: display name as string
        """
        screens = getAllScreens()
        name = ""
        for key in screens:
            if pointInRect(self.centerx, self.centery, screens[key]["pos"].x, screens[key]["pos"].y, screens[key]["size"].width, screens[key]["size"].height):
                name = key
                break
        return name

    @property
    def isMinimized(self) -> bool:
        """
        Check if current window is currently minimized

        :return: ``True`` if the window is minimized
        """
        return self._hWnd.isMiniaturized()

    @property
    def isMaximized(self) -> bool:
        """
        Check if current window is currently maximized

        :return: ``True`` if the window is maximized
        """
        return self._hWnd.isZoomed()

    @property
    def isActive(self) -> bool:
        """
        Check if current window is currently the active, foreground window

        :return: ``True`` if the window is the active, foreground window
        """
        windows = getAllWindows(self._app)
        for win in windows:
            return self._hWnd == win._hWnd
        return False

    @property
    def title(self) -> str:
        """
        Get the current window title, as string

        :return: title as a string
        """
        return self._hWnd.title()

    @property
    def updatedTitle(self) -> str:
        raise NotImplementedError

    @property
    def visible(self) -> bool:
        """
        Check if current window is visible (minimized windows are also visible)

        :return: ``True`` if the window is currently visible
        """
        return self._hWnd.isVisible()

    isVisible = visible  # isVisible is an alias for the visible property.

    @property
    def isAlive(self) -> bool:
        """
        Check if window (and application) still exists (minimized and hidden windows are included as existing)

        :return: ''True'' if window exists
        """
        ret = False
        if self._hWnd in self._app.orderedWindows():
            ret = True
        return ret

    class _WatchDog:
        """
        Set a watchdog, in a separate Thread, to be notified when some window states change

        Notice that changes will be notified according to the window status at the very moment of instantiating this class

        IMPORTANT: This can be extremely slow in macOS Apple Script version

         Available methods:
        :meth start: Initialize and start watchdog and selected callbacks
        :meth updateCallbacks: Change the states this watchdog is hooked to
        :meth updateInterval: Change the interval to check changes
        :meth kill: Stop the entire watchdog and all its hooks
        :meth isAlive: Check if watchdog is running
        """
        def __init__(self, parent: MacOSNSWindow):
            self._watchdog = None
            self._parent = parent

        def start(
            self,
            isAliveCB: Callable[[bool], None] | None = None,
            isActiveCB: Callable[[bool], None] | None = None,
            isVisibleCB: Callable[[bool], None] | None = None,
            isMinimizedCB: Callable[[bool], None] | None = None,
            isMaximizedCB: Callable[[bool], None] | None = None,
            resizedCB: Callable[[tuple[float, float]], None] | None = None,
            movedCB: Callable[[tuple[float, float]], None] | None = None,
            changedTitleCB: Callable[[str], None] | None = None,
            changedDisplayCB: Callable[[str], None] | None = None,
            interval: float = 0.3
        ):
            """
            Initialize and start watchdog and hooks (callbacks to be invoked when desired window states change)

            Notice that changes will be notified according to the window status at the very moment of execute start()

            The watchdog is asynchronous, so notifications will not be immediate (adjust interval value to your needs)

            The callbacks definition MUST MATCH their return value (boolean, string or (int, int))

            IMPORTANT: This can be extremely slow in macOS Apple Script version

            :param isAliveCB: callback to call if window is not alive. Set to None to not to watch this
                            Returns the new alive status value (False)
            :param isActiveCB: callback to invoke if window changes its active status. Set to None to not to watch this
                            Returns the new active status value (True/False)
            :param isVisibleCB: callback to invoke if window changes its visible status. Set to None to not to watch this
                            Returns the new visible status value (True/False)
            :param isMinimizedCB: callback to invoke if window changes its minimized status. Set to None to not to watch this
                            Returns the new minimized status value (True/False)
            :param isMaximizedCB: callback to invoke if window changes its maximized status. Set to None to not to watch this
                            Returns the new maximized status value (True/False)
            :param resizedCB: callback to invoke if window changes its size. Set to None to not to watch this
                            Returns the new size (width, height)
            :param movedCB: callback to invoke if window changes its position. Set to None to not to watch this
                            Returns the new position (x, y)
            :param changedTitleCB: callback to invoke if window changes its title. Set to None to not to watch this
                            Returns the new title (as string)
            :param changedDisplayCB: callback to invoke if window changes display. Set to None to not to watch this
                            Returns the new display name (as string)
            :param interval: set the interval to watch window changes. Default is 0.3 seconds
            """
            if self._parent.isAlive:
                if not self._watchdog and not self.isAlive():
                    self._watchdog = _WinWatchDog(self._parent, isAliveCB, isActiveCB, isVisibleCB, isMinimizedCB,
                                                  isMaximizedCB, resizedCB, movedCB, changedTitleCB, changedDisplayCB,
                                                  interval)
                if self._watchdog:
                    self._watchdog.setDaemon(True)
                    self._watchdog.start()
            else:
                self._watchdog = None

        def updateCallbacks(
            self,
            isAliveCB: Callable[[bool], None] | None = None,
            isActiveCB: Callable[[bool], None] | None = None,
            isVisibleCB: Callable[[bool], None] | None = None,
            isMinimizedCB: Callable[[bool], None] | None = None,
            isMaximizedCB: Callable[[bool], None] | None = None,
            resizedCB: Callable[[tuple[float, float]], None] | None = None,
            movedCB: Callable[[tuple[float, float]], None] | None = None,
            changedTitleCB: Callable[[str], None] | None = None,
            changedDisplayCB: Callable[[str], None] | None = None
        ):
            """
            Change the states this watchdog is hooked to

            The callbacks definition MUST MATCH their return value (boolean, string or (int, int))

            IMPORTANT: When updating callbacks, remember to set ALL desired callbacks or they will be deactivated

            IMPORTANT: Remember to set ALL desired callbacks every time, or they will be defaulted to None (and unhooked)

            :param isAliveCB: callback to call if window is not alive. Set to None to not to watch this
                            Returns the new alive status value (False)
            :param isActiveCB: callback to invoke if window changes its active status. Set to None to not to watch this
                            Returns the new active status value (True/False)
            :param isVisibleCB: callback to invoke if window changes its visible status. Set to None to not to watch this
                            Returns the new visible status value (True/False)
            :param isMinimizedCB: callback to invoke if window changes its minimized status. Set to None to not to watch this
                            Returns the new minimized status value (True/False)
            :param isMaximizedCB: callback to invoke if window changes its maximized status. Set to None to not to watch this
                            Returns the new maximized status value (True/False)
            :param resizedCB: callback to invoke if window changes its size. Set to None to not to watch this
                            Returns the new size (width, height)
            :param movedCB: callback to invoke if window changes its position. Set to None to not to watch this
                            Returns the new position (x, y)
            :param changedTitleCB: callback to invoke if window changes its title. Set to None to not to watch this
                            Returns the new title (as string)
            :param changedDisplayCB: callback to invoke if window changes display. Set to None to not to watch this
                            Returns the new display name (as string)
            """
            if self._watchdog and self.isAlive():
                self._watchdog.updateCallbacks(isAliveCB, isActiveCB, isVisibleCB, isMinimizedCB, isMaximizedCB,
                                              resizedCB, movedCB, changedTitleCB, changedDisplayCB)
            else:
                self._watchdog = None

        def updateInterval(self, interval: float = 0.3):
            """
            Change the interval to check changes

            :param interval: set the interval to watch window changes. Default is 0.3 seconds
            """
            if self._watchdog and self.isAlive():
                self._watchdog.updateInterval(interval)
            else:
                self._watchdog = None

        def setTryToFind(self, tryToFind: bool):
            """
            In macOS Apple Script version, if set to ''True'' and in case title changes, watchdog will try to find
            a similar title within same application to continue monitoring it. It will stop if set to ''False'' or
            similar title not found.

            IMPORTANT:

            - It will have no effect in other platforms (Windows and Linux) and classes (MacOSNSWindow)
            - This behavior is deactivated by default, so you need to explicitly activate it

            :param tryToFind: set to ''True'' to try to find a similar title. Set to ''False'' to deactivate this behavior
            """
            pass

        def stop(self):
            """
            Stop the entire WatchDog and all its hooks
            """
            if self._watchdog and self.isAlive():
                self._watchdog.kill()
            self._watchdog = None

        def isAlive(self):
            """Check if watchdog is running

            :return: ''True'' if watchdog is alive
            """
            alive = False
            try:
                alive = bool(self._watchdog and self._watchdog.is_alive())
            except:
                pass
            if not alive:
                self._watchdog = None
            return alive


def getMousePos() -> Point:
    """
    Get the current (x, y) coordinates of the mouse pointer on screen, in pixels
    Notice in macOS the origin is bottom left, so the Y value is flipped for compatibility with the rest of platforms

    :return: Point struct
    """
    # https://stackoverflow.com/questions/3698635/getting-cursor-position-in-python/24567802
    mp = Quartz.NSEvent.mouseLocation()
    screens = getAllScreens()
    x = y = 0
    for key in screens:
        if pointInRect(mp.x, mp.y, screens[key]["pos"].x, screens[key]["pos"].y, screens[key]["size"].width, screens[key]["size"].height):
            x = int(mp.x)
            y = int(screens[key]["size"].height) - abs(int(mp.y))
            break
    return Point(x, y)
cursor = getMousePos  # cursor is an alias for getMousePos

class _ScreenValue(TypedDict):
    id: int
    is_primary: bool
    pos: Point
    size: Size
    workarea: Rect
    scale: tuple[int, int]
    dpi: tuple[int, int]
    orientation: int
    frequency: float
    colordepth: int

def getAllScreens():
    """
    load all monitors plugged to the pc, as a dict

    :return: Monitors info as python dictionary

    Output Format:
        Key:
            Display name

        Values:
            "id":
                display id as returned by AppKit.NSScreen.screens() and Quartz.CGGetOnlineDisplayList()
            "is_primary":
                ''True'' if monitor is primary (shows clock and notification area, sign in, lock, CTRL+ALT+DELETE screens...)
            "pos":
                Point(x, y) struct containing the display position ((0, 0) for the primary screen)
            "size":
                Size(width, height) struct containing the display size, in pixels
            "workarea":
                Rect(left, top, right, bottom) struct with the screen workarea, in pixels
            "scale":
                Scale ratio, as a tuple of (x, y) scale percentage
            "dpi":
                Dots per inch, as a tuple of (x, y) dpi values
            "orientation":
                Display orientation: 0 - Landscape / 1 - Portrait / 2 - Landscape (reversed) / 3 - Portrait (reversed)
            "frequency":
                Refresh rate of the display, in Hz
            "colordepth":
                Bits per pixel referred to the display color depth
    """
    result: dict[str, _ScreenValue] = {}
    screens = AppKit.NSScreen.screens()
    for i, screen in enumerate(screens):
        try:
            name = screen.localizedName()   # In older macOS, screen doesn't have localizedName() method
        except:
            name = "Display" + str(i)

        try:
            desc = screen.deviceDescription()
            display = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
            is_primary = Quartz.CGDisplayIsMain(display) == 1
            x, y, w, h = int(screen.frame().origin.x), int(screen.frame().origin.y), int(screen.frame().size.width), int(screen.frame().size.height)
            wa = screen.visibleFrame()
            wx, wy, wr, wb = int(wa.origin.x), int(wa.origin.y), int(wa.size.width), int(wa.size.height)
            scale = int(screen.backingScaleFactor() * 100)
            dpi = desc[Quartz.NSDeviceResolution].sizeValue()
            dpiX, dpiY = int(dpi.width), int(dpi.height)
            rot = int(Quartz.CGDisplayRotation(display))
            freq = Quartz.CGDisplayModeGetRefreshRate(Quartz.CGDisplayCopyDisplayMode(display))
            depth = Quartz.CGDisplayBitsPerPixel(display)

            result[name] = {
                'id': display,
                'is_primary': is_primary,
                'pos': Point(x, y),
                'size': Size(w, h),
                'workarea': Rect(wx, wy, wr, wb),
                'scale': (scale, scale),
                'dpi': (dpiX, dpiY),
                'orientation': rot,
                'frequency': freq,
                'colordepth': depth
            }
        except:
            # print(traceback.format_exc())
            pass
    return result


def getScreenSize(name: str = "") -> Size:
    """
    Get the width and height of the screen, in pixels

    :return: Size struct
    """
    screens = getAllScreens()
    res = Size(0, 0)
    for key in screens:
        if (name and key == name) or (not name):
            res = screens[key]["size"]
            break
    return res
resolution = getScreenSize  # resolution is an alias for getScreenSize


def getWorkArea(name: str = "") -> Rect:
    """
    Get the Rect struct (left, top, right, bottom) of the working (usable by windows) area of the screen, in pixels

    :return: Rect struct
    """
    screens = getAllScreens()
    res = Rect(0, 0, 0, 0)
    for key in screens:
        if (name and key == name) or (not name):
            res = screens[key]["workarea"]
            break
    return res


def displayWindowsUnderMouse(xOffset: int = 0, yOffset: int = 0) -> None:
    """
    This function is meant to be run from the command line. It will
    automatically display the position of mouse pointer and the titles
    of the windows under it
    """
    if xOffset != 0 or yOffset != 0:
        print('xOffset: %s yOffset: %s' % (xOffset, yOffset))
    try:
        index = 0
        prevWindows = None
        while True:
            x, y = getMousePos()
            positionStr = 'X: ' + str(x - xOffset).rjust(4) + ' Y: ' + str(y - yOffset).rjust(4) + '  (Press Ctrl-C to quit)'
            allWindows = getAllWindows() if index % 20 == 0 else None
            windows = getWindowsAt(x, y, app=None, allWindows=allWindows)
            if windows != prevWindows:
                prevWindows = windows
                print('\n')
                for win in windows:
                    name = win.title or ''
                    eraser = '' if len(name) >= len(positionStr) else ' ' * (len(positionStr) - len(name))
                    sys.stdout.write(name + eraser + '\n')
            sys.stdout.write(positionStr)
            sys.stdout.write('\b' * len(positionStr))
            sys.stdout.flush()
            index += 1
            time.sleep(0.1)
    except KeyboardInterrupt:
        sys.stdout.write('\n\n')
        sys.stdout.flush()


def main():
    """Run this script from command-line to get windows under mouse pointer"""
    print("PLATFORM:", sys.platform)
    print("SCREEN SIZE:", resolution())
    if checkPermissions(activate=True):
        print("ALL WINDOWS", getAllTitles())
        npw = getActiveWindow()
        if npw is None:
            print("ACTIVE WINDOW:", None)
        else:
            print("ACTIVE WINDOW:", npw.title, "/", npw.box)
        print()
        displayWindowsUnderMouse(0, 0)


if __name__ == "__main__":
    main()
