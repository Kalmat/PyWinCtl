#!/usr/bin/python
# -*- coding: utf-8 -*-

import ast
import os
import platform
import subprocess
import sys
import time
from typing import Union, List

import AppKit
import Quartz

from pygetwindowmp import pointInRect, BaseWindow, Rect, Point, Size

""" 
IMPORTANT NOTICE:
    This script uses NSWindow objects, so you have to pass the app object (NSApp()) when instantiating the class.
    To manage other apps windows, this script uses Apple Script. Bear this in mind:
        - You need to grant permissions on Security & Privacy -> Accessibility
        - It uses the name of the window to address it, which is not always reliable (e.g. Terminal changes its name when changes size)
        - Changes are not immediately applied nor updated, activate wait option if you need to effectively know if/when action has been performed
"""

WS = AppKit.NSWorkspace.sharedWorkspace()
WAIT_ATTEMPTS = 10
WAIT_DELAY = 0.025  # Will be progressively increased on every retry
SEP = "|&|"


def getActiveWindow(app: AppKit.NSApplication = None) -> Union[BaseWindow, None]:
    """Returns a Window object of the currently active Window or None."""
    if not app:
        app = WS.frontmostApplication()
        cmd = """on run arg1
                set appName to arg1 as string
                set winName to ""
                tell application "System Events" to tell application process appName
                    try
                        set winName to name of (first window whose value of attribute "AXMain" is true)
                    end try
                end tell
                return winName
                end run"""
        proc = subprocess.Popen(['osascript', '-', app.localizedName()],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        title, err = proc.communicate(cmd)
        if title:
            return MacOSWindow(app, title)
        else:
            return None
    else:
        for win in getAllWindows(app):  # .keyWindow() / .mainWindow() not working?!?!?!
            return win
    return None


def getActiveWindowTitle(app: AppKit.NSApplication = None) -> str:
    """Returns a Window object of the currently active Window or empty string."""
    win = getActiveWindow(app)
    if win:
        return win.title
    else:
        return ""


def getWindowsAt(x: int, y: int, app: AppKit.NSApplication = None) -> List[BaseWindow]:
    """Returns a list of windows under the mouse pointer or an empty list."""
    matches = []
    for win in getAllWindows(app):
        box = win.box
        if pointInRect(x, y, box.left, box.top, box.width, box.height):
            matches.append(win)
    return matches


def getWindowsWithTitle(title, app: AppKit.NSApplication = None) -> List[BaseWindow]:
    """Returns a list of window objects matching the given title or an empty list."""
    matches = []
    windows = getAllWindows(app)
    for win in windows:
        if win.title == title:
            matches.append(win)
    return matches


def getAllTitles(app: AppKit.NSApplication = None) -> List[str]:
    """Returns a list of strings of window titles for all visible windows."""
    return [win.title for win in getAllWindows(app)]


def getAllWindows(app: AppKit.NSApplication = None) -> List[BaseWindow]:
    """Returns a list of window objects for all visible windows."""
    windows = []
    if not app:
        activeApps = _getAllApps()
        titleList = _getWindowTitles()
        for app in activeApps:
            for item in titleList:
                if app.localizedName() == item[0]:
                    windows.append(MacOSWindow(app, item[1]))
    else:
        for win in app.orderedWindows():
            windows.append(MacOSNSWindow(app, win))
    return windows


def _getWindowTitles() -> List[List[str]]:
    # https://gist.github.com/qur2/5729056 - qur2
    cmd = """osascript -e 'tell application "System Events"
                                set winNames to {}
                                repeat with p in every process whose background only is false
                                    repeat with w in every window of p
                                        set end of winNames to {name of p, name of w}
                                    end repeat
                                end repeat
                            end tell
                            return winNames'"""
    ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").strip().split(", ")
    retList = []
    for i in range(len(ret)-1):
        subList = [ret[i], ret[i + 1]]
        retList.append(subList)
    return retList


def _getAllApps() -> List[AppKit.NSRunningApplication]:
    return WS.runningApplications()


def _getAllWindows(excludeDesktop: bool = True, screenOnly: bool = True):
    # Source: https://stackoverflow.com/questions/53237278/obtain-list-of-all-window-titles-on-macos-from-a-python-script/53985082#53985082
    # This returns a list of window info objects, which is static, so needs to be refreshed and takes some time to the OS to refresh it
    # Besides, since it may not have kCGWindowName value and the kCGWindowNumber can't be accessed from Apple Script, it's useless
    flags = Quartz.kCGWindowListExcludeDesktopElements if excludeDesktop else 0 | \
            Quartz.kCGWindowListOptionOnScreenOnly if screenOnly else 0
    return Quartz.CGWindowListCopyWindowInfo(flags, Quartz.kCGNullWindowID)


def _getAllAppWindows(app: AppKit.NSApplication):
    windows = _getAllWindows()
    windowsInApp = []
    for win in windows:
        if win[Quartz.kCGWindowLayer] == 0 and win[Quartz.kCGWindowOwnerPID] == app.processIdentifier():
            windowsInApp.append(win)
    return windowsInApp


class MacOSWindow(BaseWindow):

    def __init__(self, app: AppKit.NSRunningApplication, title: str):
        super().__init__()
        self._app = app
        self.appName = app.localizedName()
        self.appPID = app.processIdentifier()
        self.winTitle = title
        self._setupRectProperties()
        v = platform.mac_ver()[0].split(".")
        ver = float(v[0]+"."+v[1])
        # On Yosemite and below we need to use Zoom instead of FullScreen to maximize windows
        self.use_zoom = (ver <= 10.10)
        self.menu = self._Menu(self)

    def _getWindowRect(self) -> Rect:
        """Returns a rect of window position and size (left, top, right, bottom).
        It follows ctypes format for compatibility"""
        cmd = """on run {arg1, arg2}
                    set procName to arg1 as string
                    set winName to arg2 as string
                    tell application "System Events" to tell application process procName
                        set appBounds to {0, 0, 0, 0}
                        try
                            set appPos to get position of window winName
                            set appSize to get size of window winName
                            set appBounds to {appPos, appSize}
                        end try
                    end tell
                    return appBounds
                    end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        w = ret.strip().split(", ")

        return Rect(int(w[0]), int(w[1]), int(w[0]) + int(w[2]), int(w[1]) + int(w[3]))

    def __repr__(self):
        return '%s(hWnd=%s)' % (self.__class__.__name__, self._app)

    def __eq__(self, other):
        return isinstance(other, MacOSWindow) and self._app == other._app

    def close(self, force:bool = False) -> bool:
        """Closes this window or app. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from actually
        closing. This is identical to clicking the X button on the window.

        Use 'force' option to close the entire app in case window can't be closed"""
        self.show()
        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    tell application appName
                        try
                            tell window winName to close
                        end try
                    end tell
                    end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        if force and self._exists():
            self._app.terminate()
        return not self._exists()

    def minimize(self, wait: bool = False) -> bool:
        """Minimizes this window.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was minimized"""
        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    tell application "System Events" to tell application process appName
                        try
                            set value of attribute "AXMinimized" of window winName to true
                        end try
                    end tell
                    end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.isMinimized:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.isMinimized

    def maximize(self, wait: bool = False) -> bool:
        """Maximizes this window.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was maximized"""
        # Thanks to: macdeport (for this piece of code, his help, and the moral support!!!)
        if not self.isMaximized:
            if self.use_zoom:
                cmd = """on run {arg1, arg2}
                        set appName to arg1 as string
                        set winName to arg2 as string
                        tell application "System Events" to tell application appName
                            try
                                tell window winName to set zoomed to true
                            end try
                        end tell
                        end run"""
            else:
                cmd = """on run {arg1, arg2}
                        set appName to arg1 as string
                        set winName to arg2 as string
                        tell application "System Events" to tell application process sppName
                        try
                            set value of attribute "AXFullScreen" of window winName to true
                        end try
                        end tell
                        end run"""
            proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
            ret, err = proc.communicate(cmd)
            retries = 0
            while wait and retries < WAIT_ATTEMPTS and not self.isMaximized:
                retries += 1
                time.sleep(WAIT_DELAY * retries)
        return self.isMaximized

    def restore(self, wait: bool = False) -> bool:
        """If maximized or minimized, restores the window to it's normal size.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was restored"""
        if self.isMaximized:
            if self.use_zoom:
                cmd = """on run {arg1, arg2}
                        set appName to arg1 as string
                        set winName to arg2 as string
                        tell application "System Events" to tell application appName 
                            try
                                tell window winName to set zoomed to false
                            end try
                        end tell
                        end run"""
                proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
                ret, err = proc.communicate(cmd)
            else:
                cmd = """on run arg1
                        set appName to arg1 as string
                        tell application "System Events" to tell application process appName
                            try
                                set value of attribute "AXFullScreen" of window 1 to false
                            end try
                        end tell
                        end run"""
                proc = subprocess.Popen(['osascript', '-', self.appName],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
                ret, err = proc.communicate(cmd)
        if self.isMinimized:
            cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    tell application "System Events" to tell application process appName
                        try
                            set value of attribute "AXMinimized" of window winName to false
                        end try
                    end tell
                    end run"""
            proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
            ret, err = proc.communicate(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and (self.isMinimized or self.isMaximized):
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self.isMaximized and not self.isMinimized

    def hide(self, wait: bool = False) -> bool:
        """If hidden or showing, hides the app from screen and title bar.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was hidden (unmapped)"""
        cmd = """on run {arg1, arg2}
                set appName to arg1 as string
                set winName to arg2 as string
                tell application "System Events" to tell application appName
                    set isPossible to false
                    try
                        set isPossible to exists visible of window winName
                        if isPossible then
                            tell window winName to set visible to false
                            set isPossible to true
                        end if
                    end try
                 end tell
                return (isPossible as string)
                end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        if ret == "false":
            self._app.hide()
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.visible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self.visible

    def show(self, wait: bool = False) -> bool:
        """If hidden or showing, shows the window on screen and in title bar.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window is showing (mapped)"""
        cmd = """on run {arg1, arg2}
                set appName to arg1 as string
                set winName to arg2 as string
                set isPossible to false
               try
                   tell application "System Events" to tell application appName
                        set isPossible to exists visible of window winName
                        if isPossible then
                            tell window winName to set visible to true
                        end if
                    end tell
               end try
               return (isPossible as string)
               end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        if ret == "false":
            self._app.unhide()
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.visible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.visible

    def activate(self, wait: bool = False) -> bool:
        """Activate this window and make it the foreground (focused) window.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was activated"""
        # self._app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        cmd = """on run {arg1, arg2}
                set appName to arg1 as string
                set winName to arg2 as string
                tell application "System Events" to tell application process appName
                    try
                        set visible to true
                        activate
                        set winName to winName
                        tell window winName to set visible to true 
                        tell window winName to set index to 1
                    end try
                end tell
                end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.isActive:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.isActive

    def resize(self, widthOffset: int, heightOffset: int, wait: bool = False) -> bool:
        """Resizes the window relative to its current size.
        Use 'wait' option to confirm action requested (in a reasonable time)

        Returns ''True'' if window was resized to the given size"""
        return self.resizeTo(self.width + widthOffset, self.height + heightOffset, wait)

    resizeRel = resize  # resizeRel is an alias for the resize() method.

    def resizeTo(self, newWidth: int, newHeight: int, wait: bool = False) -> bool:
        """Resizes the window to a new width and height.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was resized to the given size"""
        # https://apple.stackexchange.com/questions/350256/how-to-move-mac-os-application-to-specific-display-and-also-resize-automatically
        cmd = """on run {arg1, arg2, arg3, arg4}
                set appName to arg1 as string
                set winName to arg2 as string
                set sizeW to arg3 as integer
                set sizeH to arg5 as integer
                tell application "System Events" to tell application process appName
                    try
                        set size of window winName to {sizeW, sizeH}
                    end try
                end tell
                end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title, newWidth, newHeight],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.width != newWidth and self.height != newHeight:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.width == newWidth and self.height == newHeight

    def move(self, xOffset: int, yOffset: int, wait: bool = False) -> bool:
        """Moves the window relative to its current position.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was moved to the given position"""
        return self.moveTo(self.left + xOffset, self.top + yOffset, wait)

    moveRel = move  # moveRel is an alias for the move() method.

    def moveTo(self, newLeft:int, newTop: int, wait: bool = False) -> bool:
        """Moves the window to new coordinates on the screen.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was moved to the given position"""
        # https://apple.stackexchange.com/questions/350256/how-to-move-mac-os-application-to-specific-display-and-also-resize-automatically
        cmd = """on run {arg1, arg2, arg3, arg4}
                set appName to arg1 as string
                set winName to arg2 as string
                set posX to arg3 as integer
                set posY to arg5 as integer
                tell application "System Events" to tell application process appName
                    try
                        set position of window winName to {posX, posY}
                    end try
                end tell
                end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title, newLeft, newTop],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.left != newLeft and self.top != newTop:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.left == newLeft and self.top == newTop

    def _moveResizeTo(self, newLeft: int, newTop: int, newWidth: int, newHeight: int) -> bool:
        cmd = """on run {arg1, arg2, arg3, arg4, arg5, arg6}
                set appName to arg1 as string
                set winName to arg2 as string
                set posX to arg3 as integer
                set posY to arg5 as integer
                set sizeW to arg3 as integer
                set sizeH to arg5 as integer
                tell application "System Events" to tell application process appName
                    try
                        set position of window winName to {posX, posY}
                    end try
                    try
                        set size of window winName to {sizeW, sizeH}
                    end try
                end tell
                end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title, newLeft, newTop, newWidth, newHeight],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        retries = 0
        while retries < WAIT_ATTEMPTS and self.left != newLeft and self.top != newTop and \
                self.width != newWidth and self.height != newHeight:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return newLeft == self.left and newTop == self.top and newWidth == self.width and newHeight == self.height

    def alwaysOnTop(self, aot: bool = True) -> bool:
        """Keeps window on top of all others.

        Use aot=False to deactivate always-on-top behavior
        """
        raise NotImplementedError

    def alwaysOnBottom(self, aob: bool = True) -> bool:
        """Keeps window below of all others, but on top of desktop icons and keeping all window properties

        Use aob=False to deactivate always-on-bottom behavior
        """
        raise NotImplementedError

    def lowerWindow(self) -> None:
        """Lowers the window to the bottom so that it does not obscure any sibling windows.
        """
        # https://apple.stackexchange.com/questions/233687/how-can-i-send-the-currently-active-window-to-the-back
        cmd = """on run {arg1, arg2}
                set appName to arg1 as string
                set winName to arg2 as string
                tell application "System Events" to tell application appName
                    try
                        set winList to every window whose visible is true
                        if not winList = {} then
                            repeat with oWin in (items of reverse of winList)
                                if not name of oWin = winName then
                                    set index of oWin to 1
                                end if
                            end repeat
                        end if
                    end try 
               end tell
               end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)

    def raiseWindow(self) -> None:
        """Raises the window to top so that it is not obscured by any sibling windows.
        """
        cmd = """on run {arg1, arg2}
                set appName to arg1 as string
                set winName to arg2 as string
                tell application "System Events" to tell application appName
                    try
                        tell window winName to set index to 1
                    end try
               end tell
               end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)

    def sendBehind(self, sb: bool = True) -> bool:
        """Sends the window to the very bottom, under all other windows, including desktop icons.
        It may also cause that window does not accept focus nor keyboard/mouse events.

        WARNING: On GNOME it will obscure desktop icons... by the moment"""
        raise NotImplementedError

    @property
    def isMinimized(self) -> bool:
        """Returns ``True`` if the window is currently minimized."""
        cmd = """on run {arg1, arg2}
                set appName to arg1 as string
                set winName to arg2 as string
                tell application "System Events" to tell application process appName
                    set isMin to false
                    try
                        set isMin to value of attribute "AXMinimized" of window winName
                    end try
                end tell
                return (isMin as string)
                end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        return ret == "true"

    @property
    def isMaximized(self) -> bool:
        """Returns ``True`` if the window is currently maximized (full screen)."""
        if self.use_zoom:
            cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    tell application "System Events" to tell application appName
                        set isZoomed to false
                        try
                            set isZoomed to zoomed of window winName
                        end try
                    end tell 
                    return (isZoomed as string)
                    end run"""
        else:
            cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    tell application "System Events" to tell application process appName
                        set isFull to false
                        try
                            set isFull to value of attribute "AXFullScreen" of window winName
                        end try
                    end tell
                    return (isFull as string)
                    end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        return ret == "true"

    @property
    def isActive(self) -> bool:
        """Returns ``True`` if the window is currently the active, foreground window."""
        ret = "false"
        if self._app.isActive():
            cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    tell application "System Events" to tell application process appName
                        set isFront to false
                        try
                            set isFront to value of attribute "AXMain" of window winName
                        end try
                    end tell
                    return (isFront as string)
                    end run"""
            proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
            ret, err = proc.communicate(cmd)
        return ret == "true" or self.isMaximized

    @property
    def title(self) -> str:
        return self.winTitle

    @property
    def visible(self) -> bool:
        """Returns ``True`` if the window is currently visible.

        Non-existing and Hidden windows are not visible"""
        cmd = """on run {arg1, arg2}
                set appName to arg1 as string
                set winName to arg2 as string
                set isPossible to false
                set isMapped to false
                tell application "System Events" to tell application appName
                    try
                        set isPossible to exists visible of window winName
                        if isPossible then
                            tell window winName to set isMapped to visible
                        end if
                    end try
                end tell
                if not isPossible then
                    tell application "System Events" to tell application process appName
                        try
                            set isMapped to visible
                        end try
                    end tell
                end if
                return (isMapped as string)
                end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        return (ret == "true") or self.isMaximized

    isVisible = visible  # isVisible is an alias for the visible property.

    def _exists(self) -> bool:
        cmd = """on run {arg1, arg2}
                set appName to arg1 as string
                set winName to arg2 as string
                tell application "System Events" to tell application process appName
                    set isAlive to exists window winName
                end tell
                return (isAlive as string)
                end run"""
        proc = subprocess.Popen(['osascript', '-', self.appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        return ret == "true"

    class _Menu:

        def __init__(self, parent: BaseWindow):
            self._parent = parent
            self._menuStructure = {}

        def getMenu(self) -> dict:
            """Loads and returns the Menu structure in a dictionary format, if exists, or empty.

            Format:

                Key: item title (text property)
                Values:
                    "wID": Value required to simulate a click on the menu item
                    "items": sub-items within the sub-menu (if any)
            """

            itemList = []

            def findit():

                level = 0

                while True:
                    part = ""
                    for lev in range(level):
                        if lev % 2 == 0:
                            part = " of every menu" + part
                        else:
                            part = " of every menu item" + part
                    subCmd = "set itemList to name" + part + " of every menu bar item"
                    # It's possible to get pos and size as well, but... is it worth if you can click by name?

                    if level % 2 == 0:  # Grabbing items only (menus will have non-empty lists on the next level)

                        cmd = """
                                on run arg1
                                set procName to arg1 as string
                                tell application "System Events"
                                    tell process procName
                                        tell menu bar 1
                                            %s
                                        end tell
                                    end tell
                                end tell
                                return itemList as list
                                end run
                                """ % subCmd
                        # https://stackoverflow.com/questions/69774133/how-to-use-global-variables-inside-of-an-applescript-function-for-a-python-code
                        # Didn't find a way to get the "injected code" working if passed this way
                        proc = subprocess.Popen(['osascript', '-s', 's', '-', str(self._parent._app.localizedName())],
                                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
                        ret, err = proc.communicate(cmd)
                        ret = ret.replace("\n", "").replace('missing value', '"separator"').replace("{", "[").replace("}", "]")
                        item = ast.literal_eval(ret)

                        if err is None and not self._isListEmpty(item):
                            itemList.append(item)
                        else:
                            break
                    level += 1

                return itemList != []

            flatList = []

            def flatenit():

                for i in range(len(itemList)):
                    subList = itemList[i]
                    if i == 0:
                        otherList = subList
                    else:
                        otherList = []
                        for k in range(len(subList)):
                            otherList.append(subList[k][0])
                    flatList.append(otherList)

            def fillit():

                def subfillit(subList, section="", level=0, mainlevel=0):

                    option = self._menuStructure
                    if section:
                        for sec in section.split(SEP):
                            if sec:
                                option = option[sec]

                    for i, item in enumerate(subList):
                        while isinstance(item, list) and len(item) > 0:
                            item = item[0]
                        if item:
                            if item == "separator":
                                option[item] = {}
                            else:
                                option[item] = {"wID": section.replace(SEP + "items", "") + SEP + item}
                                if level+1 < len(flatList):
                                    submenu = flatList[level + 1][mainlevel][i]
                                    while len(submenu) > 0 and isinstance(submenu[0], list):
                                        submenu = submenu[0]
                                    if submenu:
                                        option[item]["items"] = {}
                                        subfillit(submenu, section + SEP + item + SEP + "items", level+1, mainlevel)

                for i, item in enumerate(flatList[0]):
                    self._menuStructure[item] = {}
                    self._menuStructure[item]["items"] = {}
                    subfillit(flatList[1][i], item + SEP + "items", level=1, mainlevel=i)

            if findit():
                flatenit()
                fillit()

            return self._menuStructure

        def _isListEmpty(self, inList):
            # https://stackoverflow.com/questions/1593564/python-how-to-check-if-a-nested-list-is-essentially-empty/51582274
            if isinstance(inList, list):
                return all(map(self._isListEmpty, inList))
            return False

        def clickMenuItem(self, itemPath: list = None, wID: str = "") -> bool:
            """Simulates a click on a menu item

            itemPath is a list with the desired menu item and its predecessors (e.g. ["Menu", "SubMenu", "Item"])
            wID is the ID within menu struct (as returned by getMenu() method)

            Note it will not work if item is disabled (not clickable) or path/item doesn't exist"""

            if not itemPath and wID:
                itemPath = wID.split(SEP + "items")

            option = self._menuStructure
            found = False
            for item in itemPath[:-1]:
                if item in option.keys() and "items" in option[item].keys():
                    option = option[item]["items"]
                else:
                    option = {}
                    break

            if option and itemPath[-1] in option.keys() and "wID" in option[itemPath[-1]]:
                found = True
                itemID = option[itemPath[-1]]["wID"]
                part = ""
                itemPath = itemID.split(SEP)
                for i, lev in enumerate(itemPath[1:-1]):
                    if i % 2 == 0:
                        part = str(' of menu "%s" of menu item "%s"' % (lev, lev)) + part
                    else:
                        part = str(' of menu item "%s" of menu "%s"' % (lev, lev)) + part
                subCmd = str('click menu item "%s"' % itemPath[-1]) + part + str(' of menu "%s" of menu bar item "%s"' % (itemPath[0], itemPath[0]))

                cmd = """
                        on run arg1
                        set procName to arg1 as string
                        tell application "System Events"
                            tell process procName
                                tell menu bar 1
                                    %s
                                end tell
                            end tell
                        end tell
                        end run
                        """ % subCmd

                proc = subprocess.Popen(['osascript', '-s', 's', '-', str(self._parent._app.localizedName())],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
                ret, err = proc.communicate(cmd)

            return found

        def getMenuInfo(self) -> dict:
            """Returns the existing MENUINFO struct of the main menu.
            Note "existing" can be outdated or empty. Call getMenu() if you need an updated version.
            """
            return self._menuStructure

        def getMenuItemCount(self, itemPath: list = None, wID: str = "") -> int:
            """Returns the number of items within a menu (main menu if no sub-menu given)

            itemPath is a list with the desired menu item and its predecessors (e.g. ["Menu", "SubMenu", "Item"])
            wID is the ID within menu struct (as returned by getMenu() method)
            """

            if not itemPath and wID:
                itemPath = wID.split(SEP)

            option = self._menuStructure
            for item in itemPath[:-1]:
                if item in option.keys() and "items" in option[item].keys():
                    option = option[item]["items"]
                else:
                    option = {}
                    break

            i = 0
            if option and itemPath[-1] in option.keys() and "items" in option[itemPath[-1]]:
                for item in option[itemPath[-1]]["items"].keys():
                    i += 1

            return i

        def getMenuItemInfo(self, itemPath: list = None, wID: str = "") -> dict:
            """Returns the ITEMINFO struct for the given menu item

            itemPath is a list with the desired menu item and its predecessors (e.g. ["Menu", "SubMenu", "Item"])
            wID is the ID within menu struct (as returned by getMenu() method)
            """

            if not itemPath and wID:
                itemPath = wID.split(SEP)

            option = self._menuStructure
            for item in itemPath[:-1]:
                if item in option.keys() and "items" in option[item].keys():
                    option = option[item]["items"]
                else:
                    option = {}
                    break

            wID = ""
            if option and itemPath[-1] in option.keys() and "wID" in option[itemPath[-1]]:
                wID = option[itemPath[-1]]["wID"]

            itemInfo = {}
            if len(itemPath) > 0:
                itemInfo[itemPath[-1]] = {"rect": self.getMenuItemRect(itemPath), "wID": wID}

            return itemInfo

        def getMenuItemRect(self, itemPath: list = None, wID: str = "") -> Rect:
            """Returns the Rect occupied by the Menu item

            itemPath is a list with the desired menu item and its predecessors (e.g. ["Menu", "SubMenu", "Item"])
            wID is the ID within menu struct (as returned by getMenu() method)
            """

            if not itemPath and wID:
                itemPath = wID.split(SEP)

            x = y = w = h = 0
            option = self._menuStructure
            for item in itemPath[:-1]:
                if item in option.keys() and "items" in option[item].keys():
                    option = option[item]["items"]
                else:
                    option = {}
                    break

            if option and itemPath[-1] in option.keys() and "wID" in option[itemPath[-1]]:
                itemID = option[itemPath[-1]]["wID"]
                part = ""
                itemPath = itemID.split(SEP)
                for i, lev in enumerate(itemPath[1:-1]):
                    if i % 2 == 0:
                        part = str(' of menu "%s" of menu item "%s"' % (lev, lev)) + part
                    else:
                        part = str(' of menu item "%s" of menu "%s"' % (lev, lev)) + part
                subCmd = str('set itemRect to {position, size} of menu item "%s"' % itemPath[-1]) + part + str(' of menu "%s" of menu bar item "%s"' % (itemPath[0], itemPath[0]))

                cmd = """
                        on run arg1
                        set procName to arg1 as string
                        tell application "System Events"
                            tell process procName
                                tell menu bar 1
                                    %s
                                end tell
                            end tell
                        end tell
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

        def getMenuItemWid(self, itemPath: str) -> str:
            """Returns ID of the menu item within menu struct (as returned by getMenu() method)
            itemPath is a list with the desired menu item and its predecessors (e.g. ["Menu", "SubMenu", "Item"])
            """

            wID = ""
            option = self._menuStructure
            for item in itemPath[:-1]:
                if item in option.keys() and "items" in option[item].keys():
                    option = option[item]["items"]
                else:
                    option = {}
                    break

            if option and itemPath[-1] in option.keys() and "wID" in option[itemPath[-1]]:
                wID = option[itemPath[-1]]["wID"]
            return wID


class MacOSNSWindow(BaseWindow):

    def __init__(self, app: AppKit.NSApplication, hWnd: AppKit.NSWindow):
        super().__init__()
        self._app = app
        self._hWnd = hWnd
        self._setupRectProperties()
        self.menu = self._Menu(self)

    def _getWindowRect(self) -> Rect:
        """Returns a rect of window position and size (left, top, right, bottom).
        It follows ctypes format for compatibility"""
        frame = self._hWnd.frame()
        res = resolution()
        x = int(frame.origin.x)
        y = int(res.height) - int(frame.origin.y) - int(frame.size.height)
        w = x + int(frame.size.width)
        h = y + int(frame.size.height)
        return Rect(x, y, w, h)

    def __repr__(self):
        return '%s(hWnd=%s)' % (self.__class__.__name__, self._hWnd)

    def __eq__(self, other):
        return isinstance(other, MacOSNSWindow) and self._hWnd == other._hWnd

    def close(self) -> bool:
        """Closes this window. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from actually
        closing. This is identical to clicking the X button on the window."""
        return self._hWnd.performClose_(self._app)

    def minimize(self, wait: bool = False) -> bool:
        """Minimizes this window.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was minimized"""
        if not self.isMinimized:
            self._hWnd.performMiniaturize_(self._app)
            retries = 0
            while wait and retries < WAIT_ATTEMPTS and not self.isMinimized:
                retries += 1
                time.sleep(WAIT_DELAY * retries)
        return self.isMinimized

    def maximize(self, wait: bool = False) -> bool:
        """Maximizes this window.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was maximized"""
        if not self.isMaximized:
            self._hWnd.performZoom_(self._app)
            retries = 0
            while wait and retries < WAIT_ATTEMPTS and not self.isMaximized:
                retries += 1
                time.sleep(WAIT_DELAY * retries)
        return self.isMaximized

    def restore(self, wait: bool = False) -> bool:
        """If maximized or minimized, restores the window to it's normal size.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was restored"""
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
        """If hidden or showing, shows the window on screen and in title bar.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window is showing (mapped)"""
        self.activate(wait=wait)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.visible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.visible

    def hide(self, wait: bool = False) -> bool:
        """If hidden or showing, hides the app from screen and title bar.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was hidden (unmapped)"""
        self._hWnd.orderOut_(self._app)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.visible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self.visible

    def activate(self, wait: bool = False) -> bool:
        """Activate this window and make it the foreground (focused) window.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was activated"""
        self._app.activateIgnoringOtherApps_(True)
        self._hWnd.makeKeyAndOrderFront_(self._app)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.isActive:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.isActive

    def resize(self, widthOffset: int, heightOffset: int, wait: bool = False) -> bool:
        """Resizes the window relative to its current size.
        Use 'wait' option to confirm action requested (in a reasonable time)

        Returns ''True'' if window was resized to the given size"""
        return self.resizeTo(self.width + widthOffset, self.height + heightOffset, wait)

    resizeRel = resize  # resizeRel is an alias for the resize() method.

    def resizeTo(self, newWidth: int, newHeight: int, wait: bool = False) -> bool:
        """Resizes the window to a new width and height.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was resized to the given size"""
        self._hWnd.setFrame_display_animate_(AppKit.NSMakeRect(self.bottomleft.x, self.bottomleft.y, newWidth, newHeight), True, True)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.width != newWidth and self.height != newHeight:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.width == newWidth and self.height == newHeight

    def move(self, xOffset: int, yOffset: int, wait: bool = False) -> bool:
        """Moves the window relative to its current position.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was moved to the given position"""
        return self.moveTo(self.left + xOffset, self.top + yOffset, wait)

    moveRel = move  # moveRel is an alias for the move() method.

    def moveTo(self, newLeft:int, newTop: int, wait: bool = False) -> bool:
        """Moves the window to new coordinates on the screen.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was moved to the given position"""
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
        """Keeps window on top of all others.

        Use aot=False to deactivate always-on-top behavior
        """
        if aot:
            ret = self._hWnd.setLevel_(Quartz.kCGScreenSaverWindowLevel)
        else:
            ret = self._hWnd.setLevel_(Quartz.kCGNormalWindowLevel)
        return ret

    def alwaysOnBottom(self, aob: bool = True) -> bool:
        """Keeps window below of all others, but on top of desktop icons and keeping all window properties

        Use aob=False to deactivate always-on-bottom behavior
        """
        if aob:
            ret = self._hWnd.setLevel_(Quartz.kCGDesktopWindowLevel)
        else:
            ret = self._hWnd.setLevel_(Quartz.kCGNormalWindowLevel)
        return ret

    def lowerWindow(self) -> bool:
        """Lowers the window to the bottom so that it does not obscure any sibling windows.
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
        """Raises the window to top so that it is not obscured by any sibling windows.
        """
        return self._hWnd.makeKeyAndOrderFront_(self._app)

    def sendBehind(self, sb: bool = True) -> bool:
        """Sends the window to the very bottom, below all other windows, including desktop icons.
        It may also cause that the window does not accept focus nor keyboard/mouse events.

        Use sb=False to bring the window back from background

        WARNING: On GNOME it will obscure desktop icons... by the moment"""
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

    @property
    def isMinimized(self) -> bool:
        """Returns ``True`` if the window is currently minimized."""
        return self._hWnd.isMiniaturized()

    @property
    def isMaximized(self) -> bool:
        """Returns ``True`` if the window is currently maximized (fullscreen)."""
        return self._hWnd.isZoomed()

    @property
    def isActive(self) -> bool:
        """Returns ``True`` if the window is currently the active, foreground window."""
        windows = getAllWindows(self._app)
        for win in windows:
            return self._hWnd == win
        return False

    @property
    def title(self) -> str:
        """Returns the window title as a string."""
        return self._hWnd.title()

    @property
    def visible(self) -> bool:
        """Returns ``True`` if the window is currently visible."""
        return self._hWnd.isVisible()

    isVisible = visible  # isVisible is an alias for the visible property.

    class _Menu:
        """Does it make sense to get info and control the menu created by yourself?"""

        def __init__(self, parent: BaseWindow):
            self._parent = parent
            self._hWnd = parent._hWnd
            self._hMenu = AppKit.NSApp().mainMenu()
            self._menuStructure = {}

        def getMenu(self) -> dict:
            """Loads and returns the Menu structure in a dictionary format, if exists, or empty.

            Format:

                Key: item title (text property)
                Values:
                    "wID": Value required to simulate a click on the menu item
                    "items": sub-items within the sub-menu (if any)
            """
            raise NotImplementedError

        def clickMenuItem(self, itemPath: list = None, wID: str = "") -> None:
            """Simulates a click on a menu item

            itemPath is a list with the desired menu item and its predecessors (e.g. ["Menu", "SubMenu", "Item"])
            wID is the ID within menu struct (as returned by getMenu() method)

            Note it will not work if item is disabled (not clickable) or path/item doesn't exist"""
            raise NotImplementedError

        def getMenuInfo(self = None, wID: str = "") -> dict:
            """Returns the existing MENUINFO struct of the main menu.
            Note "existing" can be outdated or empty. Call getMenu() if you need an updated version.
            """
            raise NotImplementedError

        def getMenuItemCount(self, itemPath: list = None, wID: str = "") -> int:
            """Returns the number of items within a menu (main menu if no sub-menu given)

            itemPath is a list with the desired menu item and its predecessors (e.g. ["Menu", "SubMenu", "Item"])
            wID is the ID within menu struct (as returned by getMenu() method)
            """
            raise NotImplementedError

        def getMenuItemInfo(self, itemPath: list = None, wID: str = "") -> dict:
            """Returns the ITEMINFO struct for the given menu item

            itemPath is a list with the desired menu item and its predecessors (e.g. ["Menu", "SubMenu", "Item"])
            wID is the ID within menu struct (as returned by getMenu() method)
            """
            raise NotImplementedError

        def getMenuItemRect(self, itemPath: list = None, wID: str = "") -> Rect:
            """Returns the Rect occupied by the Menu item

            itemPath is a list with the desired menu item and its predecessors (e.g. ["Menu", "SubMenu", "Item"])
            wID is the ID within menu struct (as returned by getMenu() method)
            """
            raise NotImplementedError

        def getMenuItemWid(self, itemPath: str) -> str:
            """Returns ID of the menu item within menu struct (as returned by getMenu() method)
            itemPath is a list with the desired menu item and its predecessors (e.g. ["Menu", "SubMenu", "Item"])
            """
            raise NotImplementedError


def cursor() -> Point:
    """Returns the current xy coordinates of the mouse cursor as a two-integer tuple

    Returns:
      (x, y) tuple of the current xy coordinates of the mouse cursor.
    """
    # https://stackoverflow.com/questions/3698635/getting-cursor-position-in-python/24567802
    mp = Quartz.NSEvent.mouseLocation()
    x = mp.x
    y = resolution().height - mp.y
    return Point(x, y)


def resolution() -> Size:
    """Returns the width and height of the screen as a two-integer tuple.

    Returns:
      (width, height) tuple of the screen size, in pixels.
    """
    # https://stackoverflow.com/questions/1281397/how-to-get-the-desktop-resolution-in-mac-via-python
    mainMonitor = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
    return Size(mainMonitor.size.width, mainMonitor.size.height)


def displayWindowsUnderMouse(xOffset:int = 0, yOffset: int = 0) -> None:
    """This function is meant to be run from the command line. It will
    automatically show mouse pointer position and windows names under it"""
    if xOffset != 0 or yOffset != 0:
        print('xOffset: %s yOffset: %s' % (xOffset, yOffset))
    try:
        prevWindows = None
        while True:
            x, y = cursor()
            positionStr = 'X: ' + str(x - xOffset).rjust(4) + ' Y: ' + str(y - yOffset).rjust(4) + '  (Press Ctrl-C to quit)'
            if prevWindows is not None:
                sys.stdout.write(positionStr)
                sys.stdout.write('\b' * len(positionStr))
            windows = getWindowsAt(x, y)
            if windows != prevWindows:
                prevWindows = windows
                print('\n')
                for win in windows:
                    name = win.title
                    eraser = '' if len(name) >= len(positionStr) else ' ' * (len(positionStr) - len(name))
                    sys.stdout.write(name + eraser + '\n')
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
    print("ACTIVE WINDOW:", npw.title, "/", npw.box)
    print("")
    displayWindowsUnderMouse(0, 0)


if __name__ == "__main__":
    main()
