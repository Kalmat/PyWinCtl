#!/usr/bin/python
# -*- coding: utf-8 -*-

import ast
import platform
import subprocess
import sys
import time
from typing import List

import AppKit
import Quartz

from pywinctl import pointInRect, BaseWindow, Rect, Point, Size

""" 
IMPORTANT NOTICE:
    This script uses NSWindow objects, so you have to pass the app object (NSApp()) when instantiating the class.
    To manage other apps windows, this script uses Apple Script. Bear this in mind:
        - You need to grant permissions on Settings Security & Privacy -> Accessibility
        - It uses the name of the window to address it, which is not always reliable (e.g. Terminal changes its name when changes size)
        - Changes are not immediately applied nor updated, activate wait option if you need to effectively know if/when action has been performed
"""

WS = AppKit.NSWorkspace.sharedWorkspace()
WAIT_ATTEMPTS = 10
WAIT_DELAY = 0.025  # Will be progressively increased on every retry

SEP = "|&|"


def getActiveWindow(app: AppKit.NSApplication = None):
    """Returns a Window object of the currently active Window or None.

    Args:
    ----
        ''app'' - NSApp() Object. If passed, returns the main/key window of the given app
    """
    if not app:
        app = WS.frontmostApplication()
        cmd = """on run arg1
                    set appName to arg1 as string
                    set winName to ""
                    try
                        tell application "System Events" to tell application process appName
                            set winName to name of (first window whose value of attribute "AXMain" is true)
                        end tell
                    end try
                    return winName
                end run"""
        proc = subprocess.Popen(['osascript', '-', app.localizedName()],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        title = ret.replace("\n", "")
        if title:
            return MacOSWindow(app, title)
        else:
            return None
    else:
        for win in getAllWindows(app):  # .keyWindow() / .mainWindow() not working?!?!?!
            return win
    return None


def getActiveWindowTitle(app: AppKit.NSApplication = None) -> str:
    """Returns a Window object of the currently active Window or empty string.

    Args:
    ----
        ''app'' - NSApp() Object. If passed, returns the title of the main/key window of the given app
    """
    win = getActiveWindow(app)
    if win:
        return win.title
    else:
        return ""


def getWindowsAt(x: int, y: int, app: AppKit.NSApplication = None, allWindows=None):
    """Returns a list of windows under the mouse pointer or an empty list.


    Args:
    ----
        ``x`` - x screen coordinate of the window(s)
        ``y`` - y screen coordinate of the window(s)
        ''app'' - NSApp() Object. If passed, returns the windows of the given app under the mouse
    """
    matches = []
    if not allWindows:
        allWindows = getAllWindows(app)
    for win in allWindows:
        box = win.box
        if pointInRect(x, y, box.left, box.top, box.width, box.height):
            matches.append(win)
    return matches


def getWindowsWithTitle(title, app: AppKit.NSApplication = None):
    """Returns a list of window objects matching the given title or an empty list.

    Args:
    ----
        ''app'' - NSApp() Object. If passed, returns the windows of the given app matching the given title
    """
    matches = []
    if not app:
        activeApps = _getAllApps()
        titleList = _getWindowTitles()
        for item in titleList:
            pID = item[0]
            winTitle = item[1]
            if winTitle and winTitle == title:
                x = int(item[2][0])
                y = int(item[2][1])
                w = int(item[3][0])
                h = int(item[3][1])
                rect = Rect(x, y, x + w, y + h)
                for app in activeApps:
                    if app.processIdentifier() == pID:
                        matches.append(MacOSWindow(app, title, rect))
                        break
    else:
        windows = getAllWindows(app)
        for win in windows:
            if win.title == title:
                matches.append(win)
    return matches


def getAllTitlesB(app: AppKit.NSApplication = None) -> List[str]:
    # This is a more "canonical" and legible way of getting all titles, but way slower than one-liner version
    if not app:
        cmd = """osascript -s 's' -e 'tell application "System Events"
                                    set winNames to {}
                                    set procIndex to {}
                                    repeat with p in every process whose background only is false
                                        repeat with w in every window in p
                                            set end of winNames to name of w
                                        end repeat
                                    end repeat
                                end tell
                                return {winNames, procIndex}'"""
        ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").replace("\n", "").replace("{", "[").replace("}", "]")
        res = ast.literal_eval(ret)
        return res


def getAllTitles(app: AppKit.NSApplication = None) -> List[str]:
    """Returns a list of titles for all visible windows.

    Args:
    ----
        ''app'' - NSApp() Object. If passed, returns the list of titles of all windows of the given app
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
        matches = []
        for item in res[0]:
            j = 0
            for title in item:  # One-liner script is way faster, but produces weird data structures
                matches.append(title)
                j += 1
        ret = matches
    else:
        ret = [win.title for win in getAllWindows(app)]
    return ret


def getAllWindows(app: AppKit.NSApplication = None):
    """Returns a list of window objects for all visible windows.

    Args:
    ----
        ''app'' - NSApp() Object. If passed, returns the list of all windows of given app
    """
    windows = []
    if not app:
        activeApps = _getAllApps()
        titleList = _getWindowTitles()
        for item in titleList:
            pID = item[0]
            title = item[1]
            x = int(item[2][0])
            y = int(item[2][1])
            w = int(item[3][0])
            h = int(item[3][1])
            rect = Rect(x, y, x + w, y + h)
            for app in activeApps:
                if app.processIdentifier() == pID:
                    windows.append(MacOSWindow(app, title, rect))
                    break
    else:
        for win in app.orderedWindows():
            windows.append(MacOSNSWindow(app, win))
    return windows


def _getWindowTitles() -> List[List[str]]:
    # https://gist.github.com/qur2/5729056 - qur2
    cmd = """osascript -s s -e 'tell application "System Events"
                                    set winNames to {}
                                    try
                                        set winNames to {unix id, ({name, position, size} of (every window))} of (every process whose background only is false)
                                    end try
                                end tell
                                return winNames'"""
    ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").replace("\n", "").replace("{", "[").replace("}", "]")
    res = ast.literal_eval(ret)
    result = []
    for i, pID in enumerate(res[0]):
        item = res[1][0][i]
        j = 0
        for title in item:  # One-liner script is way faster, but produces weird data structures
            pos = res[1][1][i][j]
            size = res[1][2][i][j]
            result.append([pID, title, pos, size])
            j += 1
    return result


def getAllAppsTitles() -> List[str]:
    """Returns a list of all active apps."""
    cmd = """osascript -e 'tell application "System Events"
                                    set winNames to {}
                                    try
                                        set winNames to name of every process whose background only is false
                                    end try
                                end tell
                                return winNames'"""
    ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").replace("\n", "").split(", ")
    return ret


def getAllAppsWindowsTitles() -> dict:
    """Returns a python dictionary of all active apps and their open windows."""
    cmd = """osascript -s s -e 'tell application "System Events"
                                    set winNames to {}
                                    try
                                        set winNames to {name, (name of every window)} of (every process whose background only is false)
                                    end try
                                end tell
                                return winNames'"""
    ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").replace("\n", "").replace("{", "[").replace("}", "]")
    res = ast.literal_eval(ret)
    result = {}
    for i, item in enumerate(res[0]):
        result[item] = res[1][i]
    return result


def _getAllApps():
    matches = []
    for app in WS.runningApplications():
        if app.activationPolicy() == Quartz.NSApplicationActivationPolicyRegular:
            matches.append(app)
    return matches


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

    def __init__(self, app: AppKit.NSRunningApplication, title: str, bounds: Rect = None):
        # super().__init__()
        self._app = app
        self._appName = app.localizedName()
        self._appPID = app.processIdentifier()
        self._winTitle = title
        # self._parent = self.getParent()  # It is slow and not required by now
        self._setupRectProperties(bounds=bounds)
        v = platform.mac_ver()[0].split(".")
        ver = float(v[0]+"."+v[1])
        # On Yosemite and below we need to use Zoom instead of FullScreen to maximize windows
        self._use_zoom = (ver <= 10.10)
        self.menu = self._Menu(self)

    def _getWindowRect(self) -> Rect:
        """Returns a rect of window position and size (left, top, right, bottom).
        It follows ctypes format for compatibility"""
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
        w = ret.replace("\n", "").strip().split(", ")
        return Rect(int(w[0]), int(w[1]), int(w[0]) + int(w[2]), int(w[1]) + int(w[3]))

    def __repr__(self):
        return '%s(hWnd=%s)' % (self.__class__.__name__, self._app)

    def __eq__(self, other):
        return isinstance(other, MacOSWindow) and self._app == other._app

    def close(self, force: bool = False) -> bool:
        """Closes this window or app. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from actually
        closing. This is identical to clicking the X button on the window.

        Use 'force' option to close the entire app in case window can't be closed"""
        self.show()
        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    try
                        tell application "%s"
                            tell window winName to close
                        end tell
                    end try
                end run""" % self._appName
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title],
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
        """Maximizes this window.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was maximized"""
        # Thanks to: macdeport (for this piece of code, his help, and the moral support!!!)
        if not self.isMaximized:
            if self._use_zoom:
                cmd = """on run {arg1, arg2}
                        set appName to arg1 as string
                        set winName to arg2 as string
                            tell application "System Events" to tell application "%s"
                                tell window winName to set zoomed to true
                            end tell
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

    def restore(self, wait: bool = False) -> bool:
        """If maximized or minimized, restores the window to it's normal size.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was restored"""
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

    def hide(self, wait: bool = False) -> bool:
        """If hidden or showing, hides the app from screen and title bar.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was hidden (unmapped)"""
        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    set isPossible to false
                    try
                        tell application "System Events" to tell application "%s""
                            set isPossible to exists visible of window winName
                            if isPossible then
                                tell window winName to set visible to false
                                set isPossible to true
                            end if
                         end tell
                    end try
                    return (isPossible as string)
                end run""" % self._appName
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        ret = ret.replace("\n", "")
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
                        tell application "System Events" to tell application "%s"
                            set isPossible to exists visible of window winName
                            if isPossible then
                                tell window winName to set visible to true
                            end if
                        end tell
                    end try
                    return (isPossible as string)
               end run""" % self._appName
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        ret = ret.replace("\n", "")
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
                    try
                        tell application "System Events" to tell application process appName
                            set visible to true
                            activate
                            set winName to winName
                            tell window winName to set visible to true 
                            tell window winName to set index to 1
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
        """Keeps window on top of all others.

        Use aot=False to deactivate always-on-top behavior
        """
        # TODO: Is there an attribute or similar to force window always on top?
        raise NotImplementedError

    def alwaysOnBottom(self, aob: bool = True) -> bool:
        """Keeps window below of all others, but on top of desktop icons and keeping all window properties

        Use aob=False to deactivate always-on-bottom behavior
        """
        # TODO: Is there an attribute or similar to force window always at bottom?
        raise NotImplementedError

    def lowerWindow(self) -> None:
        """Lowers the window to the bottom so that it does not obscure any sibling windows.
        """
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

    def raiseWindow(self) -> None:
        """Raises the window to top so that it is not obscured by any sibling windows.
        """
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

    def sendBehind(self, sb: bool = True) -> bool:
        """Sends the window to the very bottom, under all other windows, including desktop icons.
        It may also cause that window does not accept focus nor keyboard/mouse events.
        """
        # TODO: Is there an attribute or similar to set window level?
        raise NotImplementedError

    def getAppName(self) -> str:
        """Returns the name of the app to which current window belongs to, as string"""
        return self._appName

    def getParent(self) -> str:
        """Returns the handle (role:title) of the parent window/app"""
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
        role, parent = ret.split(", ")
        result = ""
        if role and parent:
            result = role + SEP + parent
        return result

    def getChildren(self):
        # Will "AXChildren" do the trick?
        # https://macscripter.net/viewtopic.php?id=16778
        # value of attribute "AXChildren" of UI element 1 of scroll area 1 of group 4 of window 1
        # UI elements of UI element 1 of scroll area 1 of group 4 of window 1
        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    set winChildren to {}
                    tell application "System Events" to tell application process appName
                        set winChildren to value of attribute "AXChildren" of window winName
                    end tell
                    return winChildren
               end run"""
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        ret = ret.replace("\n", "").split(", ")
        result = []
        for item in ret:
            if item.startswith("window"):
                result.append(item)
        return result

    def getHandle(self) -> str:
        """Returns the handle (role:title) of the window"""
        return "AXWindow" + SEP + self.title

    def isParent(self, child: str) -> bool:
        """Returns ''True'' if the window is parent of the given window as input argument

        Args:
        ----
            ''child'' title/handle (role:title) of the window you want to check if the current window is parent of
        """
        if SEP in child:
            part = child.split(SEP)
            if len(part) > 1:
                child = part[1]
        windows = getWindowsWithTitle(child)
        found = False
        for win in windows:
            if win.getParent() == self.getHandle():
                found = True
                break
        return found
    isParentOf = isParent  # isParentOf is an alias of isParent method

    def isChild(self, parent: str) -> bool:
        """Returns ''True'' if the window is child of the given window as input argument

                Args:
                ----
                    ''parent'' title/handle (role:title) of the window/app you want to check if the current window is child of
                """
        currParent = self.getParent()
        if SEP not in parent:
            part = currParent.split(SEP)
            if len(part) > 1:
                currParent = part[1]
        return currParent == parent
    isChildOf = isChild  # isParentOf is an alias of isParent method

    @property
    def isMinimized(self) -> bool:
        """Returns ``True`` if the window is currently minimized."""
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
        """Returns ``True`` if the window is currently maximized (full screen)."""
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
        """Returns ``True`` if the window is currently the active, foreground window."""
        ret = "false"
        if self._app.isActive():
            cmd = """on run {arg1, arg2}
                        set appName to arg1 as string
                        set winName to arg2 as string
                        set isFront to false
                        try
                            tell application "System Events" to tell application process appName
                                set isFront to value of attribute "AXMain" of window winName
                            end tell
                        end try
                        return (isFront as string)
                    end run"""
            proc = subprocess.Popen(['osascript', '-', self._appName, self.title],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
            ret, err = proc.communicate(cmd)
            ret = ret.replace("\n", "")
        return ret == "true" or self.isMaximized

    @property
    def title(self) -> str:
        return self._winTitle

    @property
    def visible(self) -> bool:
        """Returns ``True`` if the window is currently visible.

        Non-existing and Hidden windows are not visible"""
        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    set isPossible to false
                    set isMapped to false
                    try
                        tell application "System Events" to tell application "%s"
                            set isPossible to exists visible of window winName
                            if isPossible then
                                tell window winName to set isMapped to visible
                            end if
                        end tell
                    end try
                    if not isPossible then
                        try
                            tell application "System Events" to tell application process appName
                                set isMapped to visible
                            end tell
                        end try
                    end if
                    return (isMapped as string)
                end run""" % self._appName
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        ret = ret.replace("\n", "")
        return (ret == "true") or self.isMaximized

    isVisible = visible  # isVisible is an alias for the visible property.

    def _exists(self) -> bool:
        cmd = """on run {arg1, arg2}
                    set appName to arg1 as string
                    set winName to arg2 as string
                    set isAlive to "false"
                    try
                        tell application "System Events" to tell application process appName
                            set isAlive to exists window winName
                        end tell
                    end try
                    return (isAlive as string)
                end run"""
        proc = subprocess.Popen(['osascript', '-', self._appName, self.title],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf8')
        ret, err = proc.communicate(cmd)
        ret = ret.replace("\n", "")
        return ret == "true"

    class _Menu:

        def __init__(self, parent: BaseWindow):
            self._parent = parent
            self._menuStructure = {}
            self.menuList = []
            self.itemList = []

        def getMenu(self, addItemInfo: bool = False) -> dict:
            """Loads and returns the MENU struct in a dictionary format, if exists, or empty.

            Format:
            ------
                Key:    item title

                Values:
                    "parent":       parent sub-menu handle (main menu handle for level-0 items)

                    "hSubMenu":     item handle (!= 0 for sub-menu items only)

                    "wID":          item ID (required for other actions, e.g. clickMenuItem())

                    "item_info":    (optional) dictionary containing all menu item attributes

                    "shortcut":     shortcut to menu item (if any)

                    "rect":         Rect struct of the menu item (relative to window position)

                    "entries":      sub-items within the sub-menu (if any)

            Notes:
                "item_info" is extremely huge and slow. Instead use getMenuItemInfo() method individually.
                if you really want/require item_info data, set ''addItemInfo'' to ''True''
            """

            self._menuStructure = {}
            self.menuList = []
            self.itemList = []

            nameList = []
            sizeList = []
            posList = []
            attrList = []

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

                return nameList != []

            flatNameList = []
            flatSizeList = []
            flatPosList = []
            flatAttrList = []

            def flatenit():

                level = len(nameList)
                mainlevel = len(nameList[0])
                for i in range(level):
                    subNameList = nameList[i]
                    subSizeList = sizeList[i]
                    subPosList = posList[i]
                    subAttrList = attrList[i] if addItemInfo else []
                    while len(subNameList) != mainlevel:
                        subNameList = subNameList[0]
                        subSizeList = subSizeList[0]
                        subPosList = subPosList[0]
                        subAttrList = subAttrList[0] if addItemInfo else []
                    otherNameList = []
                    otherSizeList = []
                    otherPosList = []
                    otherAttrList = []
                    for j in range(len(subNameList)):
                        lastNameList = subNameList[j]
                        lastSizeList = subSizeList[j]
                        lastPosList = subPosList[j]
                        lastAttrList = subAttrList[j] if addItemInfo else []
                        for k in range(i):
                            if isinstance(lastNameList, list) and len(lastNameList) > 0:
                                lastNameList = lastNameList[0]
                                lastSizeList = lastSizeList[0]
                                lastPosList = lastPosList[0]
                                lastAttrList = lastAttrList[0] if addItemInfo else []
                            else:
                                break
                        otherNameList.append(lastNameList)
                        otherSizeList.append(lastSizeList)
                        otherPosList.append(lastPosList)
                        otherAttrList.append(lastAttrList)
                    flatNameList.append(otherNameList)
                    flatSizeList.append(otherSizeList)
                    flatPosList.append(otherPosList)
                    if addItemInfo: flatAttrList.append(otherAttrList)

            def fillit():

                def subfillit(subNameList, subSizeList, subPosList, subAttrList, section="", level=0, mainlevel=0, parent=0):

                    option = self._menuStructure
                    if section:
                        for sec in section.split(SEP):
                            if sec:
                                option = option[sec]

                    for i, item in enumerate(subNameList):
                        item, size, pos, attr = self._cleanLists(i, subNameList, subSizeList, subPosList, subAttrList)
                        if item == "missing value":
                            item = "separator"
                            option[item] = {}
                        else:
                            ref = section.replace(SEP + "entries", "") + SEP + item
                            option[item] = {"parent": parent, "wID": self._getNewWid(ref)}
                            if size and pos and size != "missing value" and pos != "missing value":
                                x, y = pos
                                w, h = size
                                option[item]["rect"] = Rect(x, y, w + x, y + h)
                            if addItemInfo:
                                option[item]["item_info"] = self._parseAttr(attr)
                            if level+1 < len(flatNameList):
                                submenu, subSize, subPos, subAttr = self._cleanLists(i, flatNameList[level + 1][mainlevel], flatSizeList[level + 1][mainlevel], flatPosList[level + 1][mainlevel], flatAttrList[level + 1][mainlevel] if addItemInfo else [], subLists=False)
                                if submenu:
                                    option[item]["hSubMenu"] = self._getNewHSubMenu(ref)
                                    option[item]["entries"] = {}
                                    subfillit(submenu, subSize, subPos, subAttr,
                                              section + SEP + item + SEP + "entries",
                                              level=level+1, mainlevel=mainlevel, parent=hSubMenu)
                                else:
                                    option[item]["hSubMenu"] = 0

                for i, item in enumerate(flatNameList[0]):
                    hSubMenu = self._getNewHSubMenu(item)
                    self._menuStructure[item] = {"hSubMenu": hSubMenu, "wID": self._getNewWid(item), "entries": {}}
                    subfillit(flatNameList[1][i], flatSizeList[1][i], flatPosList[1][i], flatAttrList[1][i] if addItemInfo else [],
                              item + SEP + "entries", level=1, mainlevel=i, parent=hSubMenu)

            if findit():
                flatenit()
                fillit()

            return self._menuStructure

        def clickMenuItem(self, itemPath: list = None, wID: int = 0) -> bool:
            """Simulates a click on a menu item

            Args:
            ----
            Use one of these input parameters to identify desired menu item:
                - ''itemPath'' corresponds to the desired menu option and predecessors as list (e.g. ["Menu", "SubMenu", "Item"])

                - ''wID'' is the item ID within menu struct (as returned by getMenu() method)

            Notes:
                - ''itemPath'' is language-dependent, so it's better not to use it or fulfill it from MENU struct
                - Will not work if item is disabled (not clickable) or path/item doesn't exist
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

        def getMenuInfo(self, hSubMenu: int) -> dict:
            """Returns the MENUINFO struct of the given sub-menu or main menu if none given

            Args:
            ----
                ''hSubMenu'' is the id of the sub-menu entry (as returned by getMenu() method)
            """
            return self.getMenuItemInfo(hSubMenu, -1)

        def getMenuItemCount(self, hSubMenu: int) -> int:
            """Returns the number of items within a menu (main menu if no sub-menu given)

            Args:
            ----
                ''hSubMenu'' is the id of the sub-menu entry (as returned by getMenu() method)
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

        def getMenuItemInfo(self, hSubMenu: int, wID: int) -> dict:
            """Returns the ITEMINFO dictionary for the given menu item

            Args:
            ----
                ''hSubMenu'' is the id of the parent sub-menu entry (as returned by getMenu() method)

                ''wID'' is the item ID within menu struct (as returned by getMenu() method)
            """
            itemInfo = []
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
                    itemInfo = self._parseAttr(ret, convert=True)

            return itemInfo

        def getMenuItemRect(self, hSubMenu: int, itemPos: int) -> Rect:
            """Returns the Rect struct of the Menu option

            Args:
            ----
                ''hSubMenu'' is the id of the parent sub-menu entry (as returned by getMenu() method)

                ''itemPos'' is the position (zero-based ordinal) of the item within the sub-menu
            """
            x = y = w = h = 0
            if self._checkMenuStruct():
                menuPath = self._getPathFromHSubMenu(hSubMenu)

                if menuPath and len(menuPath) > 1:
                    option = self._menuStructure
                    for item in menuPath:
                        if item in option.keys() and "entries" in option[item].keys():
                            option = option[item]["entries"]
                        else:
                            option = {}
                            break

                    if option:
                        itemPath = []
                        for i, key in enumerate(option.keys()):
                            if i == itemPos:
                                itemPath = menuPath
                                itemPath.append(key)
                                break

                        if itemPath and len(itemPath) > 1:
                            part = ""
                            for i, item in enumerate(itemPath[1:-1]):
                                if i % 2 == 0:
                                    part = str(' of menu "%s" of menu item "%s"' % (item, item)) + part
                                else:
                                    part = str(' of menu item "%s" of menu "%s"' % (item, item)) + part
                            subCmd = str('set itemRect to {position, size} of menu item %i' % itemPos) + part + str(' of menu "%s" of menu bar item "%s"' % (itemPath[0], itemPath[0]))

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

        def _isListEmpty(self, inList):
            # https://stackoverflow.com/questions/1593564/python-how-to-check-if-a-nested-list-is-essentially-empty/51582274
            if isinstance(inList, list):
                return all(map(self._isListEmpty, inList))
            return False

        def _cleanLists(self, i, subNameList, subSizeList, subPosList, subAttrList, subLists=True):

            if isinstance(subNameList, list) and i < len(subNameList):
                item = subNameList[i]
                size = subSizeList[i]
                pos = subPosList[i]
                attr = subAttrList[i] if subAttrList else []

                if subLists:
                    while isinstance(item, list) and len(item) > 0:
                        item = item[0]
                        pos = pos[0]
                        size = size[0]
                        attr = attr[0] if attr else []
                else:
                    while len(item) > 0 and isinstance(item[0], list):
                        item = item[0]
                        size = size[0]
                        pos = pos[0]
                        attr = attr[0] if attr else []
            else:
                item = subNameList
                size = subSizeList
                pos = subPosList
                attr = subAttrList

            return item, size, pos, attr

        def _parseAttr(self, attr, convert=False):

            itemInfo = {}
            if convert:
                attr = attr.replace("\n", "").replace('missing value', '"missing value"') \
                    .replace("{", "[").replace("}", "]").replace("value:", "'") \
                    .replace(", class:", "', '").replace(", settable:", "', '").replace(", name:", "', ")
                attr = ast.literal_eval(attr)
            for item in attr:
                if len(item) >= 4:
                    itemInfo[item[3]] = {"value": item[0], "class": item[1], "settable": item[2]}

            return itemInfo

        def _checkMenuStruct(self):
            if not self._menuStructure:
                self.getMenu()
            return self._menuStructure

        def _getNewWid(self, ref):
            self.itemList.append(ref)
            return len(self.itemList)

        def _getPathFromWid(self, wID):
            itemPath = []
            if self._checkMenuStruct():
                if 0 < wID <= len(self.itemList):
                    itemPath = self.itemList[wID - 1].split(SEP)
            return itemPath

        def _getNewHSubMenu(self, ref):
            self.menuList.append(ref)
            return len(self.menuList)

        def _getPathFromHSubMenu(self, hSubMenu):
            menuPath = []
            if self._checkMenuStruct():
                if 0 < hSubMenu <= len(self.menuList):
                    menuPath = self.menuList[hSubMenu - 1].split(SEP)
            return menuPath

        def _getMenuItemWid(self, itemPath: str) -> str:
            wID = ""
            if itemPath:
                option = self._menuStructure
                for item in itemPath[:-1]:
                    if item in option.keys() and "entries" in option[item].keys():
                        option = option[item]["entries"]
                    else:
                        option = {}
                        break

                if option and itemPath and itemPath[-1] in option.keys() and "wID" in option[itemPath[-1]]:
                    wID = option[itemPath[-1]]["wID"]

            return wID


class MacOSNSWindow(BaseWindow):

    def __init__(self, app: AppKit.NSApplication, hWnd: AppKit.NSWindow):
        super().__init__()
        self._app = app
        self._hWnd = hWnd
        self._parent = hWnd.parentWindow()
        self._setupRectProperties()

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

    def getAppName(self) -> str:
        """Returns the name of the app to which current window belongs to, as string"""
        return self._app.localizedName()

    def getParent(self) -> int:
        """Returns the handle of the window parent"""
        return self._hWnd.parentWindow()

    def getChildren(self) -> List[int]:
        return self._hWnd.childWindows()

    def getHandle(self) -> int:
        """Returns the handle of the window"""
        return self._hWnd

    def isParent(self, child) -> bool:
        """Returns True if the window is parent of the given window as input argument"""
        return child.parentWindow() == self._hWnd
    isParentOf = isParent  # isParentOf is an alias of isParent method

    def isChild(self, parent) -> bool:
        """Returns True if the window is child of the given window as input argument"""
        return parent == self.getParent()
    isChildOf = isChild  # isParentOf is an alias of isParent method

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


def getMousePos() -> Point:
    """Returns the current xy coordinates of the mouse cursor as Point struct

    Returns:
      (x, y) tuple of the current xy coordinates of the mouse cursor.
    """
    # https://stackoverflow.com/questions/3698635/getting-cursor-position-in-python/24567802
    mp = Quartz.NSEvent.mouseLocation()
    x = int(mp.x)
    y = int(getScreenSize().height) - int(mp.y)
    return Point(x, y)

cursor = getMousePos  # cursor is an alias for getMousePos


def getScreenSize() -> Size:
    """Returns the width and height of the screen as a Size struct.

    Returns:
      (width, height) tuple of the screen size, in pixels.
    """
    screen_area = AppKit.NSScreen.mainScreen().frame()
    return Size(int(screen_area.size.width), int(screen_area.size.height))

resolution = getScreenSize  # resolution is an alias for getScreenSize


def getWorkArea() -> Rect:
    """Returns the x, y, width, height of the working area of the screen as a Rect struct.

    Returns:
      (left, top, right, bottom) tuple of the working area of the screen, in pixels.
    """
    work_area = AppKit.NSScreen.mainScreen().visibleFrame()
    x = int(work_area.origin.x)
    y = 0
    w = int(work_area.size.width)
    h = int(work_area.size.height)
    return Rect(x, y, x + w, y + h)


def displayWindowsUnderMouse(xOffset:int = 0, yOffset: int = 0) -> None:
    """This function is meant to be run from the command line. It will
    automatically show mouse pointer position and windows names under it"""
    if xOffset != 0 or yOffset != 0:
        print('xOffset: %s yOffset: %s' % (xOffset, yOffset))
    try:
        index = 0
        prevWindows = None
        while True:
            x, y = getMousePos()
            positionStr = 'X: ' + str(x - xOffset).rjust(4) + ' Y: ' + str(y - yOffset).rjust(4) + '  (Press Ctrl-C to quit)'
            if prevWindows is not None:
                sys.stdout.write(positionStr)
                sys.stdout.write('\b' * len(positionStr))
            if index % 50 == 0:
                allWindows = getAllWindows()
            windows = getWindowsAt(x, y, app=None, allWindows=allWindows)
            if windows != prevWindows:
                prevWindows = windows
                print('\n')
                for win in windows:
                    name = win.title
                    eraser = '' if len(name) >= len(positionStr) else ' ' * (len(positionStr) - len(name))
                    sys.stdout.write(name + eraser + '\n')
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
    print("ALL WINDOWS", getAllTitles())
    time.sleep(3)
    npw = getActiveWindow()
    print("ACTIVE WINDOW:", npw.title, "/", npw.box)
    print()
    displayWindowsUnderMouse(0, 0)


if __name__ == "__main__":
    main()
