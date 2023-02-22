#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys

assert sys.platform == "linux"

import math
import platform
import re
import subprocess
import time
import tkinter as tk
from typing import cast, Union, List, Tuple
from typing_extensions import TypedDict

import Xlib.display
import Xlib.error
import Xlib.protocol
import Xlib.X
import Xlib.Xatom
import Xlib.Xutil
import Xlib.ext
from Xlib.xobject.drawable import Window as XWindow

from pywinctl.xlibcontainer import RootWindow, EwmhWindow, Props, \
    defaultRootWindow, _xlibGetAllWindows, _createTransient, _closeTransient

from pywinctl import BaseWindow, Point, Re, Rect, Size, _WatchDog, pointInRect

# WARNING: Changes are not immediately applied, specially for hide/show (unmap/map)
#          You may set wait to True in case you need to effectively know if/when change has been applied.
WAIT_ATTEMPTS = 10
WAIT_DELAY = 0.025  # Will be progressively increased on every retry


def checkPermissions(activate: bool = False) -> bool:
    """
    macOS ONLY: Check Apple Script permissions for current script/app and, optionally, shows a
    warning dialog and opens security preferences

    :param activate: If ''True'' and if permissions are not granted, shows a dialog and opens security preferences.
                     Defaults to ''False''
    :return: returns ''True'' if permissions are already granted or platform is not macOS
    """
    return True


def getActiveWindow() -> Union[LinuxWindow, None]:
    """
    Get the currently active (focused) Window in default root

    :return: Window object or None
    """
    win_id = defaultRootWindow.getActiveWindow()
    if win_id:
        return LinuxWindow(win_id)
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


def __remove_bad_windows(windows: Union[List[int], None]):
    """
    :param windows: Xlib Windows
    :return: A generator of LinuxWindow that filters out BadWindows
    """
    if windows is not None:
        for window in windows:
            try:
                yield LinuxWindow(window)
            except Xlib.error.XResourceError:
                pass
    else:
        return []


def getAllWindows():
    """
    Get the list of Window objects for all visible windows in default root
    :return: list of Window objects
    """
    return [window for window in __remove_bad_windows(defaultRootWindow.getClientListStacking())]


def getAllTitles() -> List[str]:
    """
    Get the list of titles of all visible windows

    :return: list of titles as strings
    """
    return [window.title for window in getAllWindows()]


def getWindowsWithTitle(title: Union[str, re.Pattern[str]], app: Union[Tuple[str, ...], None] = (), condition: int = Re.IS, flags: int = 0):
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
    matches: List[LinuxWindow] = []
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


def getAllAppsNames() -> List[str]:
    """
    Get the list of names of all visible apps

    :return: list of names as strings
    """
    return list(getAllAppsWindowsTitles())


def getAppsWithName(name: Union[str, re.Pattern[str]], condition: int = Re.IS, flags: int = 0):
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
    def _rect(self):
        return self.__rect

    def __init__(self, hWnd: XWindow | int | str):

        if isinstance(hWnd, XWindow):
            self._hWnd = hWnd.id
        elif isinstance(hWnd, str):
            self._hWnd = int(hWnd, base=16)
        else:
            self._hWnd = int(hWnd)
        self._win = EwmhWindow(self._hWnd)
        self._display: Xlib.display.Display = self._win.display
        self._rootWin: RootWindow = self._win.rootWindow
        self._xWin: XWindow = self._win.xWindow

        self.__rect = self._rectFactory()
        self.watchdog = _WatchDog(self)

        self._currDesktop = os.environ['XDG_CURRENT_DESKTOP'].lower()
        self._motifHints: List[int] = []

    def _getWindowRect(self) -> Rect:
        # https://stackoverflow.com/questions/12775136/get-window-position-and-size-in-python-with-xlib - mgalgs
        win = self._xWin
        geom = win.get_geometry()
        x = geom.x
        y = geom.y
        w = geom.width
        h = geom.height
        while True:
            parent = win.query_tree().parent
            if not isinstance(parent, XWindow):
                break
            pgeom = parent.get_geometry()
            x += pgeom.x
            y += pgeom.y
            if parent.id == self._rootWin.id:
                break
            win = parent
        return Rect(x, y, x + w, y + h)

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
        ret: list[int] = self._win.getFrameExtents()
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
        # res, a = self.XlibAttributes()  -> Should return client area, but it doesn't...
        # if res:
        #     ret = Rect(a.x, a.y, a.x + a.width, a.y + a.height)
        # else:
        #     ret = self.getWindowRect()
        # Didn't find a way to get title bar height using Xlib
        titleHeight, borderWidth = self._getBorderSizes()
        geom = self._win.xWindow.get_geometry()
        ret = Rect(int(geom.x + borderWidth), int(geom.y - titleHeight), int(geom.x + geom.width - borderWidth * 2), int(geom.y + geom.height - borderWidth))
        return ret

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
        self._win.setClosed()
        ids = [w._hWnd for w in getAllWindows()]
        return self._hWnd not in ids

    def minimize(self, wait: bool = False) -> bool:
        """
        Minimizes this window

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :return: ''True'' if window minimized
        """
        if not self.isMinimized:
            self._win.setMinimized()
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
            self._win.setMaximized(True, True)
            retries = 0
            while wait and retries < WAIT_ATTEMPTS and not self.isMaximized:
                retries += 1
                time.sleep(WAIT_DELAY * retries)
        return self.isMaximized

    def restore(self, wait: bool = False, user: bool = True) -> bool:
        """
        If maximized or minimized, restores the window to its normal size

        :param wait: set to ''True'' to confirm action requested (in a reasonable time)
        :param user: ignored on Windows platform
        :return: ''True'' if window restored
        """
        if self.isMaximized:
            self._win.changeWmState(Props.StateAction.REMOVE, Props.State.MAXIMIZED_HORZ, Props.State.MAXIMIZED_VERT)
        self.activate()
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
        self._xWin.map()
        self._xWin.map_sub_windows()
        self._display.flush()
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
        self._xWin.unmap_sub_windows()
        self._xWin.unmap()
        self._display.flush()
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self._isMapped:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self._isMapped

    def activate(self, wait: bool = False, user: bool = True) -> bool:
        """
        Activate this window and make it the foreground (focused) window

        :param wait: set to ''True'' to wait until action is confirmed (in a reasonable time lap)
        :param user: ''True'' indicates a direct user request, as required by some WMs to comply.
        :return: ''True'' if window activated
        """
        if "arm" in platform.platform():
            self._win.changeWmState(Props.StateAction.REMOVE, Props.State.ABOVE)
            self._win.changeWmState(Props.StateAction.ADD, Props.State.ABOVE, Props.State.FOCUSED)
        else:
            # This was not working as expected in Unity
            # Thanks to MestreLion (https://github.com/MestreLion) for his solution!!!!
            self._win.setActive(user)
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
        self._win.setMoveResize(gravity=0, x=self.left, y=self.top, width=newWidth, height=newHeight)
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
        self._win.setMoveResize(gravity=0, x=newLeft, y=newTop, width=self.width, height=self.height)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and (self.left != newLeft or self.top != newTop):
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.left == newLeft and self.top == newTop

    def _moveResizeTo(self, newLeft: int, newTop: int, newWidth: int, newHeight: int):
        newLeft = max(0, newLeft)  # Xlib won't accept negative positions
        newTop = max(0, newTop)
        self._win.setMoveResize(gravity=0, x=newLeft, y=newTop, width=newWidth, height=newHeight)
        return newLeft == self.left and newTop == self.top and newWidth == self.width and newHeight == self.height

    def alwaysOnTop(self, aot: bool = True) -> bool:
        """
        Keeps window on top of all others.

        :param aot: set to ''False'' to deactivate always-on-top behavior
        :return: ''True'' if command succeeded
        """
        action = Props.StateAction.ADD if aot else Props.StateAction.REMOVE
        self._win.changeWmState(action, Props.State.ABOVE)
        states = self._win.getWmState(True)
        return bool(states and Props.State.ABOVE.value in states)

    def alwaysOnBottom(self, aob: bool = True) -> bool:
        """
        Keeps window below of all others, but on top of desktop icons and keeping all window properties

        :param aob: set to ''False'' to deactivate always-on-bottom behavior
        :return: ''True'' if command succeeded
        """
        action = Props.StateAction.ADD if aob else Props.StateAction.REMOVE
        self._win.changeWmState(action, Props.State.BELOW)
        states = self._win.getWmState(True)
        return bool(states and Props.State.BELOW.value in states)

    def lowerWindow(self) -> bool:
        """
        Lowers the window to the bottom so that it does not obscure any sibling windows

        :return: ''True'' if window lowered
        """
        self._xWin.configure(stack_mode=Xlib.X.Below)
        windows = self._rootWin.getClientListStacking()
        return bool(windows and self._hWnd == windows[-1])

    def raiseWindow(self) -> bool:
        """
        Raises the window to top so that it is not obscured by any sibling windows.

        :return: ''True'' if window raised
        """
        self._xWin.configure(stack_mode=Xlib.X.Above)
        windows = self._rootWin.getClientListStacking()
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
        if sb:
            # This sends window below all others, but not behind the desktop icons
            self._win.setWmWindowType(Props.WindowType.DESKTOP)
            # self._sendBehind()

            # This will try to raise the desktop icons layer on top of the window
            # Ubuntu: "@!0,0;BDHF" is the new desktop icons NG extension on Ubuntu 22.04
            # Mint: "Desktop" title is language-dependent. Using its class instead
            # KDE: desktop and icons seem to be the same window. Likely it's not possible to place a window in between
            # TODO: Test / find in other OS
            desktop = _xlibGetAllWindows(title="@!0,0;BDHF", klass=('nemo-desktop', 'Nemo-desktop'))
            self.lowerWindow()
            for d in desktop:
                w: XWindow = self._display.create_resource_object('window', d.id)
                w.raise_window()
                self._display.flush()
            types = self._win.getWmWindowType(True)
            return bool(types and Props.WindowType.DESKTOP.value in types)

        else:
            self._win.setWmWindowType(Props.WindowType.NORMAL)
            types = self._win.getWmWindowType(True)
            return bool(types and Props.WindowType.NORMAL.value in types and self.isActive)

    def acceptInput(self, setTo: bool):
        """
        Toggles the window to accept input and focus
        WARNING: In Linux systems, this effect is not permanent (will work while program is running)

        :param setTo: True/False to toggle window ignoring input and focus
        :return: None
        """
        # TODO: Is it possible to make the window completely transparent to input (click-thru)?
        if setTo:

            self._win.changeWmState(Props.StateAction.REMOVE, Props.State.BELOW)

            onebyte = int(0xFF)
            fourbytes = onebyte | (onebyte << 8) | (onebyte << 16) | (onebyte << 24)
            self._win.xWindow.change_property(self._display.get_atom('_NET_WM_WINDOW_OPACITY'), Xlib.Xatom.CARDINAL, 32, [fourbytes])

            self._win.changeProperty(self._display.get_atom("_MOTIF_WM_HINTS"), self._motifHints)

            self._win.setWmWindowType(Props.WindowType.NORMAL)

        else:

            self._win.changeWmState(Props.StateAction.ADD, Props.State.BELOW)

            onebyte = int(0xFA)  # Calculate as 0xff * target_opacity
            fourbytes = onebyte | (onebyte << 8) | (onebyte << 16) | (onebyte << 24)
            self._win.xWindow.change_property(self._display.get_atom('_NET_WM_WINDOW_OPACITY'), Xlib.Xatom.CARDINAL, 32, [fourbytes])

            ret = self._win.getProperty(self._display.get_atom("_MOTIF_WM_HINTS"))
            if "cinnamon" in self._currDesktop:
                self._motifHints = [a for a in ret.value] if ret and hasattr(ret, "value") else [2, 1, 1, 0, 0]
            else:
                self._motifHints = [a for a in ret.value] if ret and hasattr(ret, "value") else [2, 0, 0, 0, 0]
            self._win.changeProperty(self._display.get_atom("_MOTIF_WM_HINTS"), [0, 0, 0, 0, 0])

            self._win.setWmWindowType(Props.WindowType.DESKTOP)

    def getAppName(self) -> str:
        """
        Get the name of the app current window belongs to

        :return: name of the app as string
        """
        pid = self._win.getPid()
        if pid != 0:
            with subprocess.Popen(f"ps -q {pid} -o comm=", shell=True, stdout=subprocess.PIPE) as p:
                stdout, stderr = p.communicate()
            name = stdout.decode(encoding="utf8").replace("\n", "")
        else:
            name = ""
        return name

    def getParent(self) -> int:
        """
        Get the handle of the current window parent. It can be another window or an application

        :return: handle of the window parent
        """
        return int(self._xWin.query_tree().parent.id)

    def setParent(self, parent: int) -> bool:
        """
        Current window will become child of given parent
        WARNIG: Not implemented in AppleScript (not possible in macOS for foreign (other apps') windows)

        :param parent: window to set as current window parent
        :return: ''True'' if current window is now child of given parent
        """
        self._xWin.reparent(parent, 0, 0)
        return bool(self.isChild(parent))

    def getChildren(self) -> List[int]:
        """
        Get the children handles of current window

        :return: list of handles
        """
        return cast(List[int], self._xWin.query_tree().children)

    def getHandle(self) -> int:
        """
        Get the current window handle

        :return: window handle
        """
        return self._hWnd

    def isParent(self, child: int) -> bool:
        """Returns ''True'' if the window is parent of the given window as input argument

        :param child: handle of the window you want to check if the current window is parent of
        """
        win = self._display.create_resource_object('window', child)
        return bool(win.query_tree().parent.id == self._hWnd)
    isParentOf = isParent  # isParentOf is an alias of isParent method

    def isChild(self, parent: int):
        """
        Check if current window is child of given window/app (handle)

        :param parent: handle of the window/app you want to check if the current window is child of
        :return: ''True'' if current window is child of the given window
        """
        return bool(parent == self.getParent())
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
        state = self._win.getWmState(True)
        return bool(state and Props.State.HIDDEN.value in state)

    @property
    def isMaximized(self) -> bool:
        """
        Check if current window is currently maximized

        :return: ``True`` if the window is maximized
        """
        state = self._win.getWmState(True)
        return bool(state and Props.State.MAXIMIZED_HORZ.value in state and Props.State.MAXIMIZED_VERT.value in state)

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
        name: str | bytes = self._win.getName()
        if isinstance(name, bytes):
            name = name.decode()
        return name

    def _getAttributes(self) -> Xlib.protocol.request.GetWindowAttributes:
        return self._xWin.get_attributes()

    @property
    def visible(self) -> bool:
        """
        Check if current window is visible (minimized windows are also visible)

        :return: ``True`` if the window is currently visible
        """
        attr = self._getAttributes()
        state = attr.map_state
        return bool(state == Xlib.X.IsViewable)

    isVisible: bool = cast(bool, visible)  # isVisible is an alias for the visible property.

    @property
    def isAlive(self) -> bool:
        """
        Check if window (and application) still exists (minimized and hidden windows are included as existing)

        :return: ''True'' if window exists
        """
        try:
            _ = self._getAttributes().map_state
        except Xlib.error.BadWindow:
            return False
        else:
            return True

    # @property
    # def isAlerting(self) -> bool:
    #     """Check if window is flashing/bouncing/demanding attetion on taskbar while demanding user attention
    #
    #     :return:  ''True'' if window is demanding attention
    #     """
    #     return bool(STATE_ATTENTION in self._windowWrapper.getWmState())

    @property
    def _isMapped(self) -> bool:
        # Returns ``True`` if the window is currently mapped
        state: int = self._getAttributes().map_state
        return bool(state != Xlib.X.IsUnmapped)


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
        d = Xlib.display.Display()
        displays = [d.get_display_name()]
        d.close()
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
            wa = root.get_full_property(dsp.get_atom(Props.Root.WORKAREA.value, True), Xlib.X.AnyPropertyType).value
            for output in res.outputs:
                params = dsp.xrandr_get_output_info(output, res.config_timestamp)
                try:
                    crtc = dsp.xrandr_get_crtc_info(params.crtc, res.config_timestamp)
                except:
                    crtc = None

                if crtc and crtc.mode:  # displays with empty (0) mode seem not to be valid
                    name = params.name
                    if name in result:
                        name = name + str(i)
                    id = crtc.sequence_number
                    x, y, w, h = crtc.x, crtc.y, crtc.width, crtc.height
                    wx, wy, wr, wb = x + wa[0], y + wa[1], x + w - (screen.width_in_pixels - wa[2] - wa[0]), y + h - (screen.height_in_pixels - wa[3] - wa[1])
                    # check all these values using dpi, mms or other possible values or props
                    try:
                        dpiX, dpiY = round(crtc.width * 25.4 / params.mm_width), round(crtc.height * 25.4 / params.mm_height)
                    except:
                        try:
                            dpiX, dpiY = round(w * 25.4 / screen.width_in_mms), round(h * 25.4 / screen.height_in_mms)
                        except:
                            dpiX = dpiY = 0
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
    mp = defaultRootWindow.root.query_pointer()
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
    displayWindowsUnderMouse(0, 0)


if __name__ == "__main__":
    main()
