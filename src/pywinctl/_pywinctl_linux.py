#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import threading

assert sys.platform == "linux"

import math
import platform
import re
import subprocess
import time
from ctypes import Structure, byref, c_ulong, cdll, c_uint32, c_int32
from ctypes.util import find_library
from typing import Iterable, TYPE_CHECKING, cast, Any
import tkinter as tk

if TYPE_CHECKING:
    from typing_extensions import TypedDict
else:
    # Only needed if the import from typing_extensions is used outside of annotations
    from typing import TypedDict

import Xlib.display
import Xlib.error
import Xlib.protocol
import Xlib.X
import Xlib.Xatom
import Xlib.Xutil
from Xlib.xobject.drawable import Window

from pywinctl import BaseWindow, Point, Re, Rect, Size, _WatchDog, pointInRect

# WARNING: Changes are not immediately applied, specially for hide/show (unmap/map)
#          You may set wait to True in case you need to effectively know if/when change has been applied.
WAIT_ATTEMPTS = 10
WAIT_DELAY = 0.025  # Will be progressively increased on every retry

# These values are documented at https://specifications.freedesktop.org/wm-spec/wm-spec-1.3.html
# WM_STATE values
WM_CHANGE_STATE = 'WM_CHANGE_STATE'
WM_STATE = '_NET_WM_STATE'
STATE_MODAL = '_NET_WM_STATE_MODAL'
STATE_STICKY = '_NET_WM_STATE_STICKY'
STATE_MAX_VERT = '_NET_WM_STATE_MAXIMIZED_VERT'
STATE_MAX_HORZ = '_NET_WM_STATE_MAXIMIZED_HORZ'
STATE_SHADED = '_NET_WM_STATE_SHADED'
STATE_SKIP_TASKBAR = '_NET_WM_STATE_SKIP_TASKBAR'
STATE_SKIP_PAGER = '_NET_WM_STATE_SKIP_PAGER'
STATE_HIDDEN = '_NET_WM_STATE_HIDDEN'
STATE_FULLSCREEN = '_NET_WM_STATE_FULLSCREEN'
STATE_ABOVE = '_NET_WM_STATE_ABOVE'
STATE_BELOW = '_NET_WM_STATE_BELOW'
STATE_ATTENTION = '_NET_WM_STATE_DEMANDS_ATTENTION'
STATE_FOCUSED = '_NET_WM_STATE_FOCUSED'
STATE_NULL = 0

# Set state actions
ACTION_UNSET = 0   # Remove state
ACTION_SET = 1     # Add state
ACTION_TOGGLE = 2  # Toggle state

# WM_WINDOW_TYPE values
WM_WINDOW_TYPE = '_NET_WM_WINDOW_TYPE'
WINDOW_DESKTOP = '_NET_WM_WINDOW_TYPE_DESKTOP'
WINDOW_NORMAL = '_NET_WM_WINDOW_TYPE_NORMAL'

# State Hints
HINT_STATE_WITHDRAWN = 0
HINT_STATE_NORMAL = 1
HINT_STATE_ICONIC = 3

# Stacking and Misc Atoms
WINDOW_LIST_STACKING = '_NET_CLIENT_LIST_STACKING'
ACTIVE_WINDOW = '_NET_ACTIVE_WINDOW'
WM_PID = '_NET_WM_PID'
WORKAREA = '_NET_WORKAREA'
MOVERESIZE_WINDOW = '_NET_MOVERESIZE_WINDOW'
CLOSE_WINDOW = '_NET_CLOSE_WINDOW'


def checkPermissions(activate: bool = False):
    """
    macOS ONLY: Check Apple Script permissions for current script/app and, optionally, shows a
    warning dialog and opens security preferences

    :param activate: If ''True'' and if permissions are not granted, shows a dialog and opens security preferences.
                     Defaults to ''False''
    :return: returns ''True'' if permissions are already granted or platform is not macOS
    """
    return True


def getActiveWindow() -> LinuxWindow | None:
    """
    Get the currently active (focused) Window

    :return: Window object or None
    """
    dsp = Xlib.display.Display()
    root = dsp.screen().root
    win: Xlib.protocol.request.GetProperty = root.get_full_property(dsp.get_atom(ACTIVE_WINDOW), Xlib.Xatom.WINDOW)
    dsp.close()
    if win:
        win_id = win.value
        if win_id:
            return LinuxWindow(win_id[0])
    return None


def getActiveWindowTitle():
    """
    Get the title of the currently active (focused) Window

    :return: window title as string or empty
    """
    win = getActiveWindow()
    if win:
        return win.title
    else:
        return ""


def __remove_bad_windows(windows: Iterable[Window | int | None]):
    """
    :param windows: Xlib Windows
    :return: A generator of LinuxWindow that filters out BadWindows
    """
    for window in windows:
        try:
            yield LinuxWindow(window)  # type: ignore[arg-type]  # pyright: ignore[reportGeneralTypeIssues]  # We expect an error here
        except Xlib.error.XResourceError:
            pass


def _getWindowListStacking():
    dsp = Xlib.display.Display()
    root = dsp.screen().root
    atom: int = dsp.get_atom(WINDOW_LIST_STACKING)
    properties: Xlib.protocol.request.GetProperty = root.get_full_property(atom, Xlib.X.AnyPropertyType)
    dsp.close()
    if properties:
        return [p for p in properties.value]


def getAllWindows():
    """
    Get the list of Window objects for all visible windows
    :return: list of Window objects
    """
    return [window for window in __remove_bad_windows(_getWindowListStacking())]


def getAllTitles() -> list[str]:
    """
    Get the list of titles of all visible windows

    :return: list of titles as strings
    """
    return [window.title for window in getAllWindows()]


def getWindowsWithTitle(title: str | re.Pattern[str], app: tuple[str, ...] | None = (), condition: int = Re.IS, flags: int = 0):
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
    :param app: (optional) tuple of app names. Defaults to ALL (empty list)
    :param condition: (optional) condition to apply when searching the window. Defaults to ''Re.IS'' (is equal to)
    :param flags: (optional) specific flags to apply to condition. Defaults to 0 (no flags)
    :return: list of Window objects
    """
    matches: list[LinuxWindow] = []
    if title and condition in Re._cond_dic:
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
        for win in getAllWindows():
            if win.title and Re._cond_dic[condition](title, win.title.lower() if lower else win.title, flags)  \
                    and (not app or (app and win.getAppName() in app)):
                matches.append(win)
    return matches


def getAllAppsNames() -> list[str]:
    """
    Get the list of names of all visible apps

    :return: list of names as strings
    """
    return list(getAllAppsWindowsTitles())


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
    result: dict[str, list[str]] = {}
    for win in getAllWindows():
        appName = win.getAppName()
        if appName in result.keys():
            result[appName].append(win.title)
        else:
            result[appName] = [win.title]
    return result


def getWindowsAt(x: int, y: int):
    """
    Get the list of Window objects whose windows contain the point ``(x, y)`` on screen

    :param x: X screen coordinate of the window(s)
    :param y: Y screen coordinate of the window(s)
    :return: list of Window objects
    """
    return [
        window for window
        in getAllWindows()
        if pointInRect(x, y, window.left, window.top, window.width, window.height)]


def getTopWindowAt(x: int, y: int):
    """
    Get the Window object at the top of the stack at the point ``(x, y)`` on screen

    :param x: X screen coordinate of the window
    :param y: Y screen coordinate of the window
    :return: Window object or None
    """
    windows: list[LinuxWindow] = getAllWindows()
    for window in reversed(windows):
        if pointInRect(x, y, window.left, window.top, window.width, window.height):
            return window
    else:
        return None


class LinuxWindow(BaseWindow):

    @property
    def _rect(self) -> Rect:
        return self.__rect

    def __init__(self, hWnd: Window | int | str):
        super().__init__()

        self._windowWrapper = _XWindowWrapper(hWnd)
        self._hWnd: int = self._windowWrapper.id
        self._windowObject = self._windowWrapper.getWindow()

        assert isinstance(self._hWnd, int)
        assert isinstance(self._windowObject, Window)

        self.__rect: Rect = self._rectFactory()
        self.watchdog = _WatchDog(self)

    def _getWindowRect(self) -> Rect:
        # https://stackoverflow.com/questions/12775136/get-window-position-and-size-in-python-with-xlib - mgalgs
        return self._windowWrapper.getWindowRect()

    def getExtraFrameSize(self, includeBorder: bool = True) -> tuple[int, int, int, int]:
        """
        Get the extra space, in pixels, around the window, including or not the border.
        Notice not all applications/windows will use this property values

        :param includeBorder: set to ''False'' to avoid including borders
        :return: (left, top, right, bottom) additional frame size in pixels, as a tuple of int
        """
        return self._windowWrapper.getExtraFrameSize()

    def getClientFrame(self) -> Rect:
        """
        Get the client area of window including scroll, menu and status bars, as a Rect (x, y, right, bottom)
        Notice that this method won't match non-standard window decoration sizes

        :return: Rect struct
        """
        return self._windowWrapper.getClientFrame()

    def __repr__(self):
        return '%s(hWnd=%s)' % (self.__class__.__name__, self._hWnd)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, LinuxWindow) and self._hWnd == other._hWnd

    def close(self) -> bool:
        """
        Closes this window. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from
        actually closing. This is identical to clicking the X button on the
        window.

        :return: ''True'' if window is closed
        """
        self._windowWrapper.close()
        ids = [w._hWnd for w in getAllWindows()]
        return self._hWnd not in ids

    def minimize(self, wait: bool = False) -> bool:
        """
        Minimizes this window

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :return: ''True'' if window minimized
        """
        if not self.isMinimized:
            self._windowWrapper.sendMessage(WM_CHANGE_STATE, [Xlib.Xutil.IconicState])
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
            self._windowWrapper.setWmState(ACTION_SET, STATE_MAX_VERT, STATE_MAX_HORZ)
            retries = 0
            while wait and retries < WAIT_ATTEMPTS and not self.isMaximized:
                retries += 1
                time.sleep(WAIT_DELAY * retries)
        return self.isMaximized

    def restore(self, wait: bool = False, user: bool = False) -> bool:
        """
        If maximized or minimized, restores the window to it's normal size

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :param user: ignored on Windows platform
        :return: ''True'' if window restored
        """
        if self.isMinimized:
            # self._windowWrapper.sendMessage(WM_CHANGE_STATE, [Xlib.Xutil.NormalState])
            self.activate()
        elif self.isMaximized:
            self._windowWrapper.setWmState(ACTION_UNSET, STATE_MAX_VERT, STATE_MAX_HORZ)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and (self.isMaximized or self.isMinimized):
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return bool(not self.isMaximized and not self.isMinimized)

    def show(self, wait: bool = False) -> bool:
        """
        If hidden or showing, shows the window on screen and in title bar

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window showed
        """
        self._windowWrapper.show()
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self._isMapped:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self._isMapped

    def hide(self, wait: bool = False) -> bool:
        """
        If hidden or showing, hides the window from screen and title bar

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window hidden
        """
        self._windowWrapper.hide()
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self._isMapped:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self._isMapped

    def activate(self, wait: bool = False, user: bool = False, ) -> bool:
        """
        Activate this window and make it the foreground (focused) window

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :param user: ''True'' indicates a direct user request, as required by some WMs to comply.
        :return: ''True'' if window activated
        """
        if "arm" in platform.platform():
            self._windowWrapper.setWmState(ACTION_UNSET, STATE_BELOW, STATE_NULL)
            self._windowWrapper.setWmState(ACTION_SET, STATE_ABOVE, STATE_FOCUSED)
        else:
            # This was not working as expected in Unity
            # Thanks to MestreLion (https://github.com/MestreLion) for his solution!!!!
            sourceInd = 2 if user else 1
            self._windowWrapper.sendMessage(ACTIVE_WINDOW, [sourceInd, Xlib.X.CurrentTime, self._hWnd])
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.isActive:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return bool(self.isActive)

    def resize(self, widthOffset: int, heightOffset: int, wait: bool = False):
        """
        Resizes the window relative to its current size

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window resized to the given size
        """
        return self.resizeTo(int(self.width + widthOffset), int(self.height + heightOffset), wait)

    resizeRel = resize  # resizeRel is an alias for the resize() method.

    def resizeTo(self, newWidth: int, newHeight: int, wait: bool = False):
        """
        Resizes the window to a new width and height

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window resized to the given size
        """
        self._windowWrapper.setMoveResize(x=self.left, y=self.top, width=newWidth, height=newHeight)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and (self.width != newWidth or self.height != newHeight):
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.width == newWidth and self.height == newHeight

    def move(self, xOffset: int, yOffset: int, wait: bool = False):
        """
        Moves the window relative to its current position

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window moved to the given position
        """
        newLeft = max(0, self.left + xOffset)  # Xlib won't accept negative positions
        newTop = max(0, self.top + yOffset)
        return self.moveTo(int(newLeft), int(newTop), wait)

    moveRel = move  # moveRel is an alias for the move() method.

    def moveTo(self, newLeft: int, newTop: int, wait: bool = False):
        """
        Moves the window to new coordinates on the screen

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :return: ''True'' if window moved to the given position
        """
        newLeft = max(0, newLeft)  # Xlib won't accept negative positions
        newTop = max(0, newTop)
        self._windowWrapper.setMoveResize(x=newLeft, y=newTop, width=self.width, height=self.height)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and (self.left != newLeft or self.top != newTop):
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.left == newLeft and self.top == newTop

    def _moveResizeTo(self, newLeft: int, newTop: int, newWidth: int, newHeight: int):
        newLeft = max(0, newLeft)  # Xlib won't accept negative positions
        newTop = max(0, newTop)
        self._windowWrapper.setMoveResize(x=newLeft, y=newTop, width=newWidth, height=newHeight)
        return newLeft == self.left and newTop == self.top and newWidth == self.width and newHeight == self.height

    def alwaysOnTop(self, aot: bool = True) -> bool:
        """
        Keeps window on top of all others.

        :param aot: set to ''False'' to deactivate always-on-top behavior
        :return: ''True'' if command succeeded
        """
        action = ACTION_SET if aot else ACTION_UNSET
        self._windowWrapper.setWmState(action, STATE_ABOVE)
        return STATE_ABOVE in self._windowWrapper.getWmState()

    def alwaysOnBottom(self, aob: bool = True) -> bool:
        """
        Keeps window below of all others, but on top of desktop icons and keeping all window properties

        :param aob: set to ''False'' to deactivate always-on-bottom behavior
        :return: ''True'' if command succeeded
        """
        action = ACTION_SET if aob else ACTION_UNSET
        self._windowWrapper.setWmState(action, STATE_BELOW)
        return STATE_BELOW in self._windowWrapper.getWmState()

    def lowerWindow(self) -> bool:
        """
        Lowers the window to the bottom so that it does not obscure any sibling windows

        :return: ''True'' if window lowered
        """
        self._windowWrapper.setStacking(stack_mode=Xlib.X.Below)
        windows = [w for w in _getWindowListStacking()]
        return bool(windows and self._hWnd == windows[-1])

    def raiseWindow(self) -> bool:
        """
        Raises the window to top so that it is not obscured by any sibling windows.

        :return: ''True'' if window raised
        """
        self._windowWrapper.setStacking(stack_mode=Xlib.X.Above)
        windows = [w for w in _getWindowListStacking()]
        return bool(windows and self._hWnd == windows[0])

    def sendBehind(self, sb: bool = True) -> bool:
        """
        Sends the window to the very bottom, below all other windows, including desktop icons.
        It may also cause that the window does not accept focus nor keyboard/mouse events as well as
        make the window disappear from taskbar and/or pager.

        :param sb: set to ''False'' to bring the window back to front
        :return: ''True'' if window sent behind desktop icons

        Notes:
            - On GNOME it will obscure desktop icons... by the moment
        """
        if sb and WINDOW_DESKTOP not in self._windowWrapper.getWmWindowType():
            # https://stackoverflow.com/questions/58885803/can-i-use-net-wm-window-type-dock-ewhm-extension-in-openbox

            # This sends window below all others, but not behind the desktop icons
            self._windowWrapper.setWmType(WINDOW_DESKTOP)
            # This will try to raise the desktop icons layer on top of the window
            # Ubuntu: "@!0,0;BDHF" is the new desktop icons NG extension on Ubuntu
            # Mint: "Desktop" name is language-dependent. Using its class instead
            # TODO: Test / find in other OS
            desktop = _xlibGetAllWindows(title="@!0,0;BDHF", klass=('nemo-desktop', 'Nemo-desktop'))
            # if not desktop:
            #     for win in _getRooTPropertty(ROOT, WINDOW_LIST_STACKING):  --> Should _xlibGetWindows() be used instead?
            #         state = _getWmState(win)
            #         winType = _getWmWindowType(win)
            #         if STATE_SKIP_PAGER in state and STATE_SKIP_TASKBAR in state and WINDOW_DESKTOP in winType:
            #             desktop.append(win)
            dsp = Xlib.display.Display()
            for d in desktop:
                w: Window = dsp.create_resource_object('window', d.id)
                w.raise_window()
            dsp.close()
            return WINDOW_DESKTOP in self._windowWrapper.getWmWindowType()

        else:
            pos = self.topleft
            self._windowWrapper.setWmType(WINDOW_NORMAL)
            self.activate(user=True)
            self.moveTo(pos.x, pos.y)
            return WINDOW_NORMAL in self._windowWrapper.getWmWindowType() and self.isActive

    def acceptInput(self, setTo: bool = True) -> None:
        """Toggles the window transparent to input and focus

        :param setTo: True/False to toggle window transparent to input and focus
        :return: None
        """
        self._windowWrapper.setAcceptInput(setTo)

    def getAppName(self) -> str:
        """
        Get the name of the app current window belongs to

        :return: name of the app as string
        """
        pids = self._windowWrapper.getProperty(WM_PID)
        pid = 0
        if pids:
            pid = pids[0]
        if pid != 0:
            with subprocess.Popen(f"ps -q {pid} -o comm=", shell=True, stdout=subprocess.PIPE) as p:
                stdout, stderr = p.communicate()
            name = stdout.decode(encoding="utf8").replace("\n", "")
        else:
            name = ""
        return name

    def getParent(self) -> Window:
        """
        Get the handle of the current window parent. It can be another window or an application

        :return: handle of the window parent
        """
        return self._windowWrapper.query_tree().parent  # type: ignore[no-any-return]

    def setParent(self, parent) -> bool:
        """
        Current window will become child of given parent
        WARNIG: Not implemented in AppleScript (not possible in macOS for foreign (other apps') windows)

        :param parent: window to set as current window parent
        :return: ''True'' if current window is now child of given parent
        """
        self._windowObject.reparent(parent, 0, 0)
        return bool(self.isChild(parent))

    def getChildren(self) -> list[int]:
        """
        Get the children handles of current window

        :return: list of handles
        """
        return self._windowWrapper.query_tree().children  # type: ignore[no-any-return]

    def getHandle(self) -> int:
        """
        Get the current window handle

        :return: window handle
        """
        return self._hWnd

    def isParent(self, child: Window) -> bool:
        """Returns ''True'' if the window is parent of the given window as input argument

        Args:
        ----
            ''child'' handle of the window you want to check if the current window is parent of
        """
        return bool(child.query_tree().parent.id == self._hWnd)  # type: ignore[no-any-return]
    isParentOf = isParent  # isParentOf is an alias of isParent method

    def isChild(self, parent: Window):
        """
        Check if current window is child of given window/app (handle)

        :param parent: handle of the window/app you want to check if the current window is child of
        :return: ''True'' if current window is child of the given window
        """
        return bool(parent.id == self.getParent().id)
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
        state = self._windowWrapper.getWmState()
        return bool(STATE_HIDDEN in state)

    @property
    def isMaximized(self) -> bool:
        """
        Check if current window is currently maximized

        :return: ``True`` if the window is maximized
        """
        state = self._windowWrapper.getWmState()
        return bool(STATE_MAX_VERT in state and STATE_MAX_HORZ in state)

    @property
    def isActive(self):
        """
        Check if current window is currently the active, foreground window

        :return: ``True`` if the window is the active, foreground window
        """
        win = getActiveWindow()
        return bool(win and win.getHandle() == self._hWnd)

    @property
    def title(self) -> str:
        """
        Get the current window title, as string

        :return: title as a string
        """
        name: str | bytes = self._windowWrapper.getWmName()
        if isinstance(name, bytes):
            name = name.decode()
        return name

    @property
    def visible(self) -> bool:
        """
        Check if current window is visible (minimized windows are also visible)

        :return: ``True`` if the window is currently visible
        """
        attr = self._windowWrapper.getAttributes()
        state = attr.map_state
        return bool(state == Xlib.X.IsViewable)  # type: ignore[no-any-return]

    isVisible: bool = cast(bool, visible)  # isVisible is an alias for the visible property.

    @property
    def isAlive(self) -> bool:
        """
        Check if window (and application) still exists (minimized and hidden windows are included as existing)

        :return: ''True'' if window exists
        """
        try:
            _ = self._windowWrapper.getAttributes().map_state
        except Xlib.error.BadWindow:
            return False
        else:
            return True

    @property
    def isAlerting(self) -> bool:
        """Check if window is flashing/bouncing/demanding attetion on taskbar while demanding user attention

        :return:  ''True'' if window is demanding attention
        """
        return bool(STATE_ATTENTION in self._windowWrapper.getWmState())

    @property
    def _isMapped(self) -> bool:
        # Returns ``True`` if the window is currently mapped
        state: int = self._windowWrapper.getAttributes().map_state
        return bool(state != Xlib.X.IsUnmapped)


class _XWindowWrapper:

    def __init__(self, win: str | int | Window = None, display: Xlib.display.Display = None, root: Window = None):

        if not display:
            display = Xlib.display.Display()
        self.display = display

        if not root:
            root = self.display.screen().root
        self.root = root
        self.rid = self.root.id
        self.xlib = None

        if not win:
            win = self.display.create_resource_object('window', self.rid)
        elif isinstance(win, int):
            win = self.display.create_resource_object('window', win)
        elif isinstance(win, str):
            win = display.create_resource_object('window', int(win, base=16))
        self.win: Window = win
        assert isinstance(self.win, Window)
        self.id = self.win.id
        # self._saveWindowInitValues()  # Store initial Window parameters to allow reset and other actions
        self.transientWindow: _XWindowWrapper | None = None
        self.keepCheckin: bool = False

    def _saveWindowInitValues(self) -> None:
        # Saves initial rect values to allow reset to original position, size, state and hints.
        self._init_rect = self.getWindowRect()
        self._init_state = self.getWmState()
        self._init_hints = self.win.get_wm_hints()
        self._init_normal_hints = self.win.get_wm_normal_hints()
        self._init_attributes = self.getAttributes()  # can't be modified
        self._init_xAttributes = self.XlibAttributes()
        self._init_wm_prots = self.win.get_wm_protocols()
        self._init_states = self.getWmState()
        self._init_types = self.getWmWindowType()

    def renewWindowObject(self) -> _XWindowWrapper:
        # Not sure if this is necessary.
        #     - Window object may change (I can't remember in which cases, but it did)
        #     - It's assuming at least id doesn't change... if it does, well, nothing to do with that window anymore
        self.display.close()  # -> Is this necessary... and when?
        self.display = Xlib.display.Display()
        self.root = self.display.screen().root
        self.rid = self.root.id
        self.win = self.display.create_resource_object('window', self.id)
        return self

    def getWindow(self) -> Window:
        return self.win

    def getDisplay(self) -> Xlib.display.Display:
        return self.display

    def getScreen(self) -> Xlib.protocol.rq.DictWrapper:
        return cast(Xlib.protocol.rq.DictWrapper, self.display.screen())

    def getRoot(self) -> Window:
        return self.root

    def getProperty(self, name: str, prop_type: int = Xlib.X.AnyPropertyType) -> list[int]:

        atom: int = self.display.get_atom(name)
        properties: Xlib.protocol.request.GetProperty = self.win.get_full_property(atom, prop_type)
        if properties:
            props: list[int] = properties.value
            return [p for p in props]
        return []

    def getWmState(self, text: bool = True) -> list[str] | list[int] | list[Any]:

        states = self.win.get_full_property(self.display.get_atom(WM_STATE, False), Xlib.X.AnyPropertyType)
        if states:
            stats: list[int] = states.value
            if not text:
                return [s for s in stats]
            else:
                return [self.display.get_atom_name(s) for s in stats]
        return []

    def getWmWindowType(self, text: bool = True) -> list[str] | list[int]:
        types = self.getProperty(WM_WINDOW_TYPE)
        if not text:
            return [t for t in types]
        else:
            return [self.display.get_atom_name(t) for t in types]

    def sendMessage(self, prop: str | int, data: list[int]):

        if isinstance(prop, str):
            prop = self.display.get_atom(prop)

        if type(data) is str:
            dataSize = 8
        else:
            data = (data + [0] * (5 - len(data)))[:5]
            dataSize = 32

        ev = Xlib.protocol.event.ClientMessage(window=self.win, client_type=prop, data=(dataSize, data))
        mask = Xlib.X.SubstructureRedirectMask | Xlib.X.SubstructureNotifyMask
        self.display.send_event(destination=self.rid, event=ev, event_mask=mask)
        self.display.flush()

    def setProperty(self, prop: str | int, data: list[int], mode: int = Xlib.X.PropModeReplace):

        if isinstance(prop, str):
            prop = self.display.get_atom(prop)

        # Format value can be 8, 16 or 32... depending on the content of data
        format = 32
        self.win.change_property(prop, Xlib.Xatom.ATOM, format, data, mode)
        self.display.flush()

    def setWmState(self, action: int, state: str | int, state2: str | int = 0):

        if isinstance(state, str):
            state = self.display.get_atom(state, True)
        if isinstance(state2, str):
            state2 = self.display.get_atom(state2, True)
        self.setProperty(WM_STATE, [action, state, state2, 1])
        self.display.flush()

    def setWmType(self, prop: str | int, mode: int = Xlib.X.PropModeReplace):

        if isinstance(prop, str):
            prop = self.display.get_atom(prop, False)

        geom = self.win.get_geometry()
        self.win.unmap()
        self.setProperty(WM_WINDOW_TYPE, [prop], mode)
        self.win.map()
        self.display.flush()
        self.setMoveResize(x=geom.x, y=geom.y, width=geom.width, height=geom.height)

    def setMoveResize(self, x: int, y: int, width: int, height: int):
        self.win.configure(x=x, y=y, width=width, height=height)
        self.display.flush()

    def setStacking(self, stack_mode: int):
        self.win.configure(stack_mode=stack_mode)
        self.display.flush()

    def hide(self):
        self.win.unmap_sub_windows()
        self.display.flush()
        self.win.unmap()
        self.display.flush()

    def show(self):
        self.win.map()
        self.display.flush()
        self.win.map_sub_windows()
        self.display.flush()

    def close(self):
        self.sendMessage(CLOSE_WINDOW, [])

    def getWmName(self) -> str | None:
        return self.win.get_wm_name()

    # def _globalEventListener(self, events):
    #
    #     from Xlib import X
    #     from Xlib.ext import record
    #     from Xlib.display import Display
    #     from Xlib.protocol import rq
    #
    #     def handler(reply):
    #         data = reply.data
    #         while len(data):
    #             event, data = rq.EventField(None).parse_binary_value(data, display.display, None, None)
    #
    #             if event.type == X.KeyPress:
    #                 print('pressed')
    #             elif event.type == X.KeyRelease:
    #                 print('released')
    #
    #     display = Display()
    #     context = display.record_create_context(0, [record.AllClients], [{
    #         'core_requests': (0, 0),
    #         'core_replies': (0, 0),
    #         'ext_requests': (0, 0, 0, 0),
    #         'ext_replies': (0, 0, 0, 0),
    #         'delivered_events': (0, 0),
    #         'device_events': (X.KeyReleaseMask, X.ButtonReleaseMask),
    #         'errors': (0, 0),
    #         'client_started': False,
    #         'client_died': False,
    #     }])
    #     display.record_enable_context(context, handler)
    #     display.record_free_context(context)
    #
    #     while True:
    #         display.screen().root.display.next_event()

    def _createTransient(self, parent, d):

        if self.transientWindow is not None:
            self._closeTransientWindow(d)

        geom = self.win.get_geometry()
        window = self.xlib.XCreateSimpleWindow(
            d,
            self.id,
            0, 0, geom.width, geom.height,
            0,
            0,
            0
        )
        self.xlib.XSelectInput(d, window,
                               Xlib.X.ButtonPressMask | Xlib.X.ButtonReleaseMask | Xlib.X.KeyPressMask | Xlib.X.KeyReleaseMask)
        self.xlib.XFlush(d)
        self.xlib.XMapWindow(d, window)
        self.xlib.XFlush(d)
        self.xlib.XSetTransientForHint(d, window, parent)
        self.xlib.XFlush(d)
        self.xlib.XRaiseWindow(d, window)
        self.xlib.XFlush(d)
        return window

    def _closeTransientWindow(self, d):

        if self.transientWindow is not None:
            self.transientWindow.win.unmap()
            self.transientWindow.close()
            self.xlib.XFlush(d)
            self.xlib.XClearWindow(d, self.id)
            self.xlib.XFlush(d)
            time.sleep(0.1)
            self.transientWindow = None

    def _checkDisplayEvents(self, events: list[int], keep, d):

        self.keep = keep
        self.root.change_attributes(event_mask=Xlib.X.PropertyChangeMask | Xlib.X.SubstructureNotifyMask)

        while keep.is_set():
            if self.root.display.pending_events():
                event = self.root.display.next_event()
                try:
                    child = event.child
                except:
                    child = None
                if self.win in (event.window, child) and event.type in events:
                    if event.type == Xlib.X.ConfigureNotify:
                        self.transientWindow = _XWindowWrapper(self._createTransient(self.id, d))
                        # Should be enough just moving/resizing transient window, but it's not
                        # self.transientWindow.win.configure(x=0, y=0, width=event.width, height=event.height, stack_mode=Xlib.X.Above)
                        # xlib.XFlush(d)
                    elif event.type == Xlib.X.DestroyNotify:
                        if self.transientWindow is not None:
                            self.transientWindow.close()
                            self.transientWindow = None
                        keep.is_set.clear()
            time.sleep(0.1)

    def setAcceptInput(self, setTo: bool):

        if self.xlib is None:
            x11 = find_library('X11')
            self.xlib = cdll.LoadLibrary(str(x11))
        d = self.xlib.XOpenDisplay(0)
        root = self.xlib.XRootWindow(d, self.xlib.XDefaultScreen(d))

        if setTo:
            if self.transientWindow is not None:
                self.keep.clear()
                self.checkThread.join()
                self._closeTransientWindow(d)
        else:
            window = self._createTransient(self.id, d)
            self.transientWindow = _XWindowWrapper(window)
            self.keep = threading.Event()
            self.keep.set()
            self.checkThread: threading.Thread = threading.Thread(target=self._checkDisplayEvents, args=([Xlib.X.ConfigureNotify, Xlib.X.DestroyNotify], self.keep, d, ))
            self.checkThread.daemon = True
            self.checkThread.start()

    def setWmHints(self, hint):
        # Leaving this as an example
        # {'flags': 103, 'input': 1, 'initial_state': 1, 'icon_pixmap': <Pixmap 0x02a22304>, 'icon_window': <Window 0x00000000>, 'icon_x': 0, 'icon_y': 0, 'icon_mask': <Pixmap 0x02a2230b>, 'window_group': <Window 0x02a00001>}
        hints: Xlib.protocol.rq.DictWrapper = self.win.get_wm_hints()
        if hints:
            hints.input = 1
        self.win.set_wm_hints(hints)
        self.display.flush()

    def addWmProtocol(self, atom):
        prots = self.win.get_wm_protocols()
        if atom not in prots:
            prots.append(atom)
        self.win.set_wm_protocols(prots)
        self.display.flush()

    def delWmProtocol(self, atom):
        prots = self.win.get_wm_protocols()
        new_prots = [p for p in prots if p != atom]
        prots = new_prots
        self.win.set_wm_protocols(prots)

    def getAttributes(self) -> Xlib.protocol.request.GetWindowAttributes:
        return self.win.get_attributes()

    class _XWindowAttributes(Structure):
        _fields_ = [('x', c_int32), ('y', c_int32),
                    ('width', c_int32), ('height', c_int32), ('border_width', c_int32),
                    ('depth', c_int32), ('visual', c_ulong), ('root', c_ulong),
                    ('class', c_int32), ('bit_gravity', c_int32),
                    ('win_gravity', c_int32), ('backing_store', c_int32),
                    ('backing_planes', c_ulong), ('backing_pixel', c_ulong),
                    ('save_under', c_int32), ('colourmap', c_ulong),
                    ('mapinstalled', c_uint32), ('map_state', c_uint32),
                    ('all_event_masks', c_ulong), ('your_event_mask', c_ulong),
                    ('do_not_propagate_mask', c_ulong), ('override_redirect', c_int32), ('screen', c_ulong)]

    def XlibAttributes(self) -> tuple[bool, _XWindowWrapper._XWindowAttributes]:
        attr = _XWindowWrapper._XWindowAttributes()
        try:
            if self.xlib is None:
                x11 = find_library('X11')
                self.xlib = cdll.LoadLibrary(str(x11))
            d = self.xlib.XOpenDisplay(0)
            self.xlib.XGetWindowAttributes(d, self.id, byref(attr))
            self.xlib.XCloseDisplay(d)
            resOK = True
        except:
            resOK = False
        return resOK, attr

        # Leaving this as reference of using X11 library
        # https://github.com/evocount/display-management/blob/c4f58f6653f3457396e44b8c6dc97636b18e8d8a/displaymanagement/rotation.py
        # https://github.com/nathanlopez/Stitch/blob/master/Configuration/mss/linux.py
        # https://gist.github.com/ssokolow/e7c9aae63fb7973e4d64cff969a78ae8
        # https://stackoverflow.com/questions/36188154/get-x11-window-caption-height
        # https://refspecs.linuxfoundation.org/LSB_1.3.0/gLSB/gLSB/libx11-ddefs.html
        # s = xlib.XDefaultScreen(d)
        # root = xlib.XDefaultRootWindow(d)
        # fg = xlib.XBlackPixel(d, s)
        # bg = xlib.XWhitePixel(d, s)
        # w = xlib.XCreateSimpleWindow(d, root, 600, 300, 400, 200, 0, fg, bg)
        # xlib.XMapWindow(d, w)
        # time.sleep(4)
        # a = xlib.XInternAtom(d, "_GTK_FRAME_EXTENTS", True)
        # if not a:
        #     a = xlib.XInternAtom(d, "_NET_FRAME_EXTENTS", True)
        # t = c_int()
        # f = c_int()
        # n = c_ulong()
        # b = c_ulong()
        # xlib.XGetWindowProperty(d, w, a, 0, 4, False, Xlib.X.AnyPropertyType, byref(t), byref(f), byref(n), byref(b), byref(attr))
        # r = c_ulong()
        # x = c_int()
        # y = c_int()
        # w = c_uint()
        # h = c_uint()
        # b = c_uint()
        # d = c_uint()
        # xlib.XGetGeometry(d, hWnd.id, byref(r), byref(x), byref(y), byref(w), byref(h), byref(b), byref(d))
        # print(x, y, w, h)
        # Other references (send_event and setProperty):
        # prop = DISP.intern_atom(WM_CHANGE_STATE, False)
        # data = (32, [Xlib.Xutil.IconicState, 0, 0, 0, 0])
        # ev = Xlib.protocol.event.ClientMessage(window=self._hWnd.id, client_type=prop, data=data)
        # mask = Xlib.X.SubstructureRedirectMask | Xlib.X.SubstructureNotifyMask
        # DISP.send_event(destination=ROOT, event=ev, event_mask=mask)
        # data = [Xlib.Xutil.IconicState, 0, 0, 0, 0]
        # _setProperty(_type="WM_CHANGE_STATE", data=data, mask=mask)
        # for atom in w.list_properties():
        #     print(DISP.atom_name(atom))
        # props = DISP.xrandr_list_output_properties(output)
        # for atom in props.atoms:
        #     print(atom, DISP.get_atom_name(atom))
        #     print(DISP.xrandr_get_output_property(output, atom, 0, 0, 1000)._data['value'])

    def _getBorderSizes(self):

        class App(tk.Tk):

            def __init__(self):
                super().__init__()
                self.geometry('0x0+200+200')
                self.update_idletasks()

                pos = self.geometry().split('+')
                self.bar_height = self.winfo_rooty() - int(pos[2])
                self.border_width = self.winfo_rootx() - int(pos[1])
                self.destroy()

            def getTitlebarHeight(self):
                return self.bar_height

            def getBorderWidth(self):
                return self.border_width

        app = App()
        # app.mainloop()
        return app.getTitlebarHeight(), app.getBorderWidth()

    def getExtraFrameSize(self, includeBorder: bool = True) -> tuple[int, int, int, int]:
        """
        Get the extra space, in pixels, around the window, including or not the border.
        Notice not all applications/windows will use this property values

        :param includeBorder: set to ''False'' to avoid including borders
        :return: (left, top, right, bottom) additional frame size in pixels, as a tuple of int
        """
        display = self.display
        prop = "_GTK_FRAME_EXTENTS"
        atom = display.intern_atom(prop, True)
        if not atom:
            prop = "_NET_FRAME_EXTENTS"
        ret: list[int] = self.getProperty(prop)
        if not ret: ret = [0, 0, 0, 0]
        borderWidth = 0
        if includeBorder:
            # _, a = self.XlibAttributes()
            # borderWidth = a.border_width
            if includeBorder:
                titleHeight, borderWidth = self._getBorderSizes()
        frame = (ret[0] + borderWidth, ret[2] + borderWidth, ret[1] + borderWidth, ret[3] + borderWidth)
        return frame

    def getClientFrame(self) -> Rect:
        """
        Get the client area of window including scroll, menu and status bars, as a Rect (x, y, right, bottom)
        Notice that this method won't match non-standard window decoration sizes

        :return: Rect struct
        """
        # res, a = self.XlibAttributes()
        # if res:
        #     ret = Rect(a.x, a.y, a.x + a.width, a.y + a.height)
        # else:
        #     ret = Rect(self.left, self.top, self.right, self.bottom)
        # Didn't find a way to get title bar height using Xlib
        titleHeight, borderWidth = self._getBorderSizes()
        geom = self.win.get_geometry()
        ret = Rect(int(geom.left + borderWidth), int(geom.y + titleHeight), int(geom.x + geom.width - borderWidth), int(geom.y + geom.widh - borderWidth))
        return ret

    def getWindowRect(self) -> Rect:
        # https://stackoverflow.com/questions/12775136/get-window-position-and-size-in-python-with-xlib - mgalgs
        win = self.win
        geom = win.get_geometry()
        x = geom.x
        y = geom.y
        while True:
            parent = win.query_tree().parent
            pgeom = parent.get_geometry()
            x += pgeom.x
            y += pgeom.y
            if parent.id == self.rid:
                break
            win = parent
        w = geom.width
        h = geom.height
        return Rect(x, y, x + w, y + h)


def _xlibGetAllWindows(parent: Window | None = None, title: str = "", klass: tuple[str, str] | None = None) -> list[Window]:

    dsp = Xlib.display.Display()
    parent = parent or dsp.screen().root
    allWindows = [parent]

    def findit(hwnd: Window):
        query = hwnd.query_tree()
        for child in query.children:
            try:
                winTitle = child.get_wm_name()
            except:
                winTitle = ""
            try:
                winClass = child.get_wm_class()
            except:
                winClass = ""
            if (not title and not klass) or (title and winTitle == title) or (klass and winClass == klass):
                allWindows.append(child)
            findit(child)

    findit(parent)
    dsp.close()
    return allWindows


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
                display sequence_number as identified by Xlib.Display()
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
                Display orientation: 0 - Landscape / 1 - Portrait / 2 - Landscape (reversed) / 3 - Portrait (reversed) / 4 - Reflect X / 5 - Reflect Y
            "frequency":
                Refresh rate of the display, in Hz
            "colordepth":
                Bits per pixel referred to the display color depth
    """
    # https://stackoverflow.com/questions/8705814/get-display-count-and-resolution-for-each-display-in-python-without-xrandr
    # https://www.x.org/releases/X11R7.7/doc/libX11/libX11/libX11.html#Obtaining_Information_about_the_Display_Image_Formats_or_Screens

    displays = []
    try:
        files = os.listdir("/tmp/.X11-unix")
    except:
        files = []
    for f in files:
        if f.startswith("X"):
            displays.append(":"+f[1:])
    if not displays:
        displays = [":0"]
    result: dict[str, _ScreenValue] = {}
    for display in displays:
        dsp = Xlib.display.Display(display)
        for i in range(dsp.screen_count()):
            try:
                screen = dsp.screen(i)
                root = screen.root
            except:
                continue

            res = root.xrandr_get_screen_resources()
            modes = res.modes
            wa = root.get_full_property(dsp.get_atom(WORKAREA, True), Xlib.X.AnyPropertyType).value
            for output in res.outputs:
                params = dsp.xrandr_get_output_info(output, res.config_timestamp)
                crtc = None
                try:
                    crtc = dsp.xrandr_get_crtc_info(params.crtc, res.config_timestamp)
                except:
                    continue

                if crtc and crtc.mode:  # displays with empty (0) mode seem not to be valid
                    name = params.name
                    if name in result:
                        name = name + str(i)
                    id = crtc.sequence_number
                    x, y, w, h = crtc.x, crtc.y, crtc.width, crtc.height
                    wx, wy, wr, wb = x + wa[0], y + wa[1], x + w - (screen.width_in_pixels - wa[2] - wa[0]), y + h - (screen.height_in_pixels - wa[3] - wa[1])
                    # check all these values using dpi, mms or other possible values or props
                    dpiX = dpiY = 0
                    try:
                        dpiX, dpiY = round(crtc.width * 25.4 / params.mm_width), round(crtc.height * 25.4 / params.mm_height)
                    except:
                        dpiX, dpiY = round(w * 25.4 / screen.width_in_mms), round(h * 25.4 / screen.height_in_mms)
                    scaleX, scaleY = round(dpiX / 96 * 100), round(dpiY / 96 * 100)
                    rot = int(math.log(crtc.rotation, 2))
                    freq = 0.0
                    for mode in modes:
                        if crtc.mode == mode.id:
                            freq = mode.dot_clock / (mode.h_total * mode.v_total)
                            break
                    depth = screen.root_depth

                    result[name] = {
                        'id': id,
                        'is_primary': (x, y) == (0, 0),
                        'pos': Point(x, y),
                        'size': Size(w, h),
                        'workarea': Rect(wx, wy, wr, wb),
                        'scale': (scaleX, scaleY),
                        'dpi': (dpiX, dpiY),
                        'orientation': rot,
                        'frequency': freq,
                        'colordepth': depth
                    }
        dsp.close()
    return result


def getMousePos() -> Point:
    """
    Get the current (x, y) coordinates of the mouse pointer on screen, in pixels

    :return: Point struct
    """
    dsp = Xlib.display.Display()
    mp = dsp.screen().root.query_pointer()
    dsp.close()
    return Point(mp.root_x, mp.root_y)
cursor = getMousePos  # cursor is an alias for getMousePos


def getScreenSize(name: str = "") -> Size:
    """
    Get the width and height, in pixels, of the given screen, or main screen if no screen given or not found

    :param name: name of screen as returned by getAllScreens() and getDisplay()
    :return: Size struct or None
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

    :param name: name of screen as returned by getAllScreens() and getDisplay()
    :return: Rect struct or None
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
        prevWindows = None
        while True:
            x, y = getMousePos()
            positionStr = 'X: ' + str(x - xOffset).rjust(4) + ' Y: ' + str(y - yOffset).rjust(4) + '  (Press Ctrl-C to quit)'
            windows = getWindowsAt(x, y)
            if windows != prevWindows:
                print('\n')
                prevWindows = windows
                for win in windows:
                    name = win.title
                    eraser = '' if len(name) >= len(positionStr) else ' ' * (len(positionStr) - len(name))
                    sys.stdout.write(name + eraser + '\n')
            sys.stdout.write(positionStr)
            sys.stdout.write('\b' * len(positionStr))
            sys.stdout.flush()
            time.sleep(0.3)
    except KeyboardInterrupt:
        sys.stdout.write('\n\n')
        sys.stdout.flush()


def main():
    """Run this script from command-line to get windows under mouse pointer"""
    print("PLATFORM:", sys.platform)
    print("SCREEN SIZE:", resolution())
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
