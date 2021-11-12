#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import platform
import subprocess
import sys
import time
import AppKit
import Quartz
from pygetwindow import PyGetWindowException, pointInRect, BaseWindow, Rect, Point, Size

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


def getActiveWindow(app=None):
    """Returns a Window object of the currently active Window or None."""
    if not app:
        app = WS.frontmostApplication()
        cmd = """osascript -e 'tell application "System Events" to tell application process "%s"
                                    set winName to ""
                                    try
                                        set winName to name of (first window whose value of attribute "AXMain" is true)
                                    end try
                                end tell
                                return winName'""" % app.localizedName()
        title = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").strip()
        if title:
            return MacOSWindow(app, title)
        else:
            return None
    else:
        for win in getAllWindows(app):  # .keyWindow() / .mainWindow() not working?!?!?!
            return win
    return None


def getActiveWindowTitle(app=None):
    """Returns a Window object of the currently active Window or empty string."""
    win = getActiveWindow(app)
    if win:
        return win.title
    else:
        return ""


def getWindowsAt(x, y, app=None):
    """Returns a list of windows under the mouse pointer or an empty list."""
    matches = []
    for win in getAllWindows(app):
        box = win.box
        if pointInRect(x, y, box.left, box.top, box.width, box.height):
            matches.append(win)
    return matches


def getWindowsWithTitle(title, app=None):
    """Returns a list of window objects matching the given title or an empty list."""
    matches = []
    windows = getAllWindows(app)
    for win in windows:
        if win.title == title:
            matches.append(win)
    return matches


def getAllTitles(app=None):
    """Returns a list of strings of window titles for all visible windows."""
    return [win.title for win in getAllWindows(app)]


def getAllWindows(app=None):
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


def _getWindowTitles():
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


def _getAllApps():
    return WS.runningApplications()


def _getAllWindows(excludeDesktop=True, screenOnly=True):
    # Source: https://stackoverflow.com/questions/53237278/obtain-list-of-all-window-titles-on-macos-from-a-python-script/53985082#53985082
    # This returns a list of window info objects, which is static, so needs to be refreshed and takes some time to the OS to refresh it
    # Besides, since it may not have kCGWindowName value and the kCGWindowNumber can't be accessed from Apple Script, it's useless
    flags = Quartz.kCGWindowListExcludeDesktopElements if excludeDesktop else 0 | \
            Quartz.kCGWindowListOptionOnScreenOnly if screenOnly else 0
    return Quartz.CGWindowListCopyWindowInfo(flags, Quartz.kCGNullWindowID)


def _getAllAppWindows(app):
    windows = _getAllWindows()
    windowsInApp = []
    for win in windows:
        if win[Quartz.kCGWindowLayer] == 0 and win[Quartz.kCGWindowOwnerPID] == app.processIdentifier():
            windowsInApp.append(win)
    return windowsInApp


class MacOSWindow(BaseWindow):

    def __init__(self, app, title):
        self._app = app
        self.appName = app.localizedName()
        self.appPID = app.processIdentifier()
        self.winTitle = title
        self._setupRectProperties()
        v = platform.mac_ver()[0].split(".")
        ver = float(v[0]+"."+v[1])
        # On Yosemite and below we need to use Zoom instead of FullScreen to maximize windows
        self.use_zoom = (ver <= 10.10)

    def _getWindowRect(self):
        """Returns a rect of window position and size (left, top, right, bottom).
        It follows ctypes format for compatibility"""
        cmd = """osascript -e 'tell application "System Events" to tell application process "%s"
                                    set winName to "%s"
                                    set appBounds to {0, 0, 0, 0}
                                    try
                                        set appPos to get position of window winName
                                        set appSize to get size of window winName
                                        set appBounds to {appPos, appSize}
                                    end try
                                end tell
                                return appBounds'""" % (self.appName, self.title)
        w = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").strip().split(", ")
        return Rect(int(w[0]), int(w[1]), int(w[0]) + int(w[2]), int(w[1]) + int(w[3]))

    def __repr__(self):
        return '%s(hWnd=%s)' % (self.__class__.__name__, self._app)

    def __eq__(self, other):
        return isinstance(other, MacOSWindow) and self._app == other._app

    def close(self, force=False):
        """Closes this window or app. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from actually
        closing. This is identical to clicking the X button on the window.

        Use 'force' option to close the entire app in case window can't be closed"""
        self.show()
        cmd = """osascript -e 'tell application "%s" 
                                    try
                                        tell window "%s" to close
                                    end try
                                end tell'""" % (self.appName, self.title)
        os.system(cmd)
        if force and self._exists():
            self._app.terminate()
        return not self._exists()

    def minimize(self, wait=False):
        """Minimizes this window.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was minimized"""
        cmd = """osascript -e 'tell application "System Events" to tell application process "%s" 
                                try
                                    set value of attribute "AXMinimized" of window "%s" to true
                                end try
                            end tell'""" % (self.appName, self.title)
        os.system(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.isMinimized:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.isMinimized

    def maximize(self, wait=False, force=False):
        """Maximizes this window.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was maximized"""
        # Thanks to: macdeport (for this piece of code, his help, and the moral support!!!)
        if not self.isMaximized:
            if self.use_zoom:
                cmd = """osascript -e 'tell application "System Events" to tell application "%s" 
                                            try
                                                tell window "%s" to set zoomed to true
                                            end try
                                        end tell'""" % (self.appName, self.title)
            else:
                cmd = """osascript -e 'tell application "System Events" to tell application process "%s"
                                        try
                                            set value of attribute "AXFullScreen" of window "%s" to true
                                        end try
                                        end tell'""" % (self.appName, self.title)
            os.system(cmd)
            retries = 0
            while wait and retries < WAIT_ATTEMPTS and not self.isMaximized:
                retries += 1
                time.sleep(WAIT_DELAY * retries)
        return self.isMaximized

    def restore(self, wait=False):
        """If maximized or minimized, restores the window to it's normal size.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was restored"""
        if self.isMaximized:
            if self.use_zoom:
                cmd = """osascript -e 'tell application "System Events" to tell application "%s" 
                                            try
                                                tell window "%s" to set zoomed to false
                                            end try
                                        end tell'""" % (self.appName, self.title)
                os.system(cmd)
            else:
                cmd = """osascript -e 'tell application "System Events" to tell application process "%s" 
                                            try
                                                set value of attribute "AXFullScreen" of window 1 to false
                                            end try
                                        end tell'""" % self.appName
                os.system(cmd)
        if self.isMinimized:
            cmd = """osascript -e 'tell application "System Events" to tell application process "%s" 
                                        try
                                            set value of attribute "AXMinimized" of window "%s" to false
                                        end try
                                    end tell'""" % (self.appName, self.title)
            os.system(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and (self.isMinimized or self.isMaximized):
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self.isMaximized and not self.isMinimized

    def hide(self, wait=False):
        """If hidden or showing, hides the app from screen and title bar.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was hidden (unmapped)"""
        cmd = """osascript -e 'tell application "System Events" to tell application "%s"
                                    set isPossible to false
                                    set winName to "%s"
                                    try
                                        set isPossible to exists visible of window winName
                                        if isPossible then
                                            tell window winName to set visible to false
                                            set isPossible to true
                                        end if
                                    end try
                                 end tell
                                return (isPossible as string)'""" % (self.appName, self.title)
        ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").strip()
        if ret == "false":
            self._app.hide()
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.visible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self.visible

    def show(self, wait=False):
        """If hidden or showing, shows the window on screen and in title bar.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window is showing (mapped)"""
        cmd = """osascript -e 'set isPossible to false
                               try
                                   tell application "System Events" to tell application "%s"
                                        set winName to "%s"
                                        set isPossible to exists visible of window winName
                                        if isPossible then
                                            tell window winName to set visible to true
                                        end if
                                    end tell
                               end try
                               return (isPossible as string)'""" % (self.appName, self.title)
        ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").strip()
        if ret == "false":
            self._app.unhide()
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.visible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.visible

    def activate(self, wait=False):
        """Activate this window and make it the foreground (focused) window.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was activated"""
        # self._app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        cmd = """osascript -e 'tell application "System Events" to tell application process "%s"
                                    try
                                        set visible to true
                                        activate
                                        set winName to "%s"
                                        tell window winName to set visible to true 
                                        tell window winName to set index to 1
                                    end try
                                end tell'""" % (self.appName, self.title)
        os.system(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.isActive:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.isActive

    def resize(self, widthOffset, heightOffset, wait=False):
        """Resizes the window relative to its current size.
        Use 'wait' option to confirm action requested (in a reasonable time)

        Returns ''True'' if window was resized to the given size"""
        return self.resizeTo(self.width + widthOffset, self.height + heightOffset, wait)

    resizeRel = resize  # resizeRel is an alias for the resize() method.

    def resizeTo(self, newWidth, newHeight, wait=False):
        """Resizes the window to a new width and height.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was resized to the given size"""
        # https://apple.stackexchange.com/questions/350256/how-to-move-mac-os-application-to-specific-display-and-also-resize-automatically
        cmd = """osascript -e 'tell application "System Events" to tell application process "%s"
                                    try
                                        set size of window "%s" to {%i, %i}
                                    end try
                                end tell'""" % (self.appName, self.title, newWidth, newHeight)
        os.system(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.width != newWidth and self.height != newHeight:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.width == newWidth and self.height == newHeight

    def move(self, xOffset, yOffset, wait=False):
        """Moves the window relative to its current position.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was moved to the given position"""
        return self.moveTo(self.left + xOffset, self.top + yOffset, wait)

    moveRel = move  # moveRel is an alias for the move() method.

    def moveTo(self, newLeft, newTop, wait=False):
        """Moves the window to new coordinates on the screen.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was moved to the given position"""
        # https://apple.stackexchange.com/questions/350256/how-to-move-mac-os-application-to-specific-display-and-also-resize-automatically
        cmd = """osascript -e 'tell application "System Events" to tell application process "%s"
                                    try
                                        set position of window "%s" to {%i, %i}
                                    end try
                                end tell'""" % (self.appName, self.title, newLeft, newTop)
        os.system(cmd)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.left != newLeft and self.top != newTop:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.left == newLeft and self.top == newTop

    def _moveResizeTo(self, newLeft, newTop, newWidth, newHeight):
        cmd = """osascript -e 'tell application "System Events" to tell application process "%s"
                                    set winName to "%s"
                                    try
                                        set position of window winName to {%i, %i}
                                    end try
                                    try
                                        set size of window winName to {%i, %i}
                                    end try
                                end tell'""" % \
              (self.appName, self.title, newLeft, newTop, newWidth, newHeight)
        os.system(cmd)
        retries = 0
        while retries < WAIT_ATTEMPTS and self.left != newLeft and self.top != newTop and \
                self.width != newWidth and self.height != newHeight:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return

    @property
    def isMinimized(self):
        """Returns ``True`` if the window is currently minimized."""
        cmd = """osascript -e 'tell application "System Events" to tell application process "%s" 
                                    set isMin to false
                                    try
                                        set isMin to value of attribute "AXMinimized" of window "%s"
                                    end try
                                end tell
                                return (isMin as string)'""" % (self.appName, self.title)
        ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").strip()
        return ret == "true"

    @property
    def isMaximized(self):
        """Returns ``True`` if the window is currently maximized (full screen)."""
        if self.use_zoom:
            cmd = """osascript -e 'tell application "System Events" to tell application "%s" 
                                        set isZoomed to false
                                        try
                                            set isZoomed to zoomed of window "%s"
                                        end try
                                    end tell 
                                    return (isZoomed as string)'""" % (self.appName, self.title)
        else:
            cmd = """osascript -e 'tell application "System Events" to tell application process "%s"
                                        set isFull to false
                                        try
                                            set isFull to value of attribute "AXFullScreen" of window "%s"
                                        end try
                                    end tell
                                    return (isFull as string)'""" % (self.appName, self.title)
        ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").strip()
        return ret == "true"

    @property
    def isActive(self):
        """Returns ``True`` if the window is currently the active, foreground window."""
        ret = "false"
        if self._app.isActive():
            cmd = """osascript -e 'tell application "System Events" to tell application process "%s"
                                        set isFront to false
                                        try
                                            set isFront to value of attribute "AXMain" of window "%s"
                                        end try
                                    end tell
                                    return (isFront as string)'""" % (self.appName, self.title)
            ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").strip()
        return ret == "true" or self.isMaximized

    @property
    def title(self):
        return self.winTitle

    @property
    def visible(self):
        """Returns ``True`` if the window is currently visible.

        Non-existing and Hidden windows are not visible"""
        cmd = """osascript -e 'set winName to "%s"
                                set isPossible to false
                                set isMapped to false
                                tell application "System Events" to tell application "%s"
                                    try
                                        set isPossible to exists visible of window winName
                                        if isPossible then
                                            tell window winName to set isMapped to visible
                                        end if
                                    end try
                                end tell
                                if not isPossible then
                                    tell application "System Events" to tell application process "%s"
                                        try
                                            set isMapped to visible
                                        end try
                                    end tell
                                end if
                                return (isMapped as string)'""" % (self.title, self.appName, self.appName)
        ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").strip()
        return (ret == "true") or self.isMaximized

    def _exists(self):
        cmd = """osascript -e 'tell application "System Events" to tell application process "%s"
                                    set isAlive to exists window "%s"
                                end tell
                                return (isAlive as string)'""" % (self.appName, self.title)
        ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").strip()
        return ret == "true"


class MacOSNSWindow(BaseWindow):

    def __init__(self, app, hWnd):
        self._app = app
        self._hWnd = hWnd
        self._setupRectProperties()

    def _getWindowRect(self):
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

    def close(self):
        """Closes this window. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from actually
        closing. This is identical to clicking the X button on the window."""
        self._hWnd.performClose_(self._app)

    def minimize(self, wait=False):
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

    def maximize(self, wait=False):
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

    def restore(self, wait=False):
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

    def hide(self, wait=False):
        """If hidden or showing, hides the app from screen and title bar.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was hidden (unmapped)"""
        self._hWnd.orderOut_(self._app)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.visible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self.visible

    def show(self, wait=False):
        """If hidden or showing, shows the window on screen and in title bar.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window is showing (mapped)"""
        self.activate(wait=wait)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.visible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.visible

    def activate(self, wait=False):
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

    def resize(self, widthOffset, heightOffset, wait=False):
        """Resizes the window relative to its current size.
        Use 'wait' option to confirm action requested (in a reasonable time)

        Returns ''True'' if window was resized to the given size"""
        return self.resizeTo(self.width + widthOffset, self.height + heightOffset, wait)

    resizeRel = resize  # resizeRel is an alias for the resize() method.

    def resizeTo(self, newWidth, newHeight, wait=False):
        """Resizes the window to a new width and height.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was resized to the given size"""
        self._hWnd.setFrame_display_animate_(AppKit.NSMakeRect(self.bottomleft.x, self.bottomleft.y, newWidth, newHeight), True, True)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.width != newWidth and self.height != newHeight:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.width == newWidth and self.height == newHeight

    def move(self, xOffset, yOffset, wait=False):
        """Moves the window relative to its current position.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was moved to the given position"""
        return self.moveTo(self.left + xOffset, self.top + yOffset, wait)

    moveRel = move  # moveRel is an alias for the move() method.

    def moveTo(self, newLeft, newTop, wait=False):
        """Moves the window to new coordinates on the screen.
        Use 'wait' option to confirm action requested (in a reasonable time).

        Returns ''True'' if window was moved to the given position"""
        self._hWnd.setFrame_display_animate_(AppKit.NSMakeRect(newLeft, resolution().height - newTop - self.height, self.width, self.height), True, True)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.left != newLeft and self.top != newTop:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.left == newLeft and self.top == newTop

    def _moveResizeTo(self, newLeft, newTop, newWidth, newHeight):
        self._hWnd.setFrame_display_animate_(AppKit.NSMakeRect(newLeft, resolution().height - newTop - newHeight, newWidth, newHeight), True, True)
        return

    @property
    def isMinimized(self):
        """Returns ``True`` if the window is currently minimized."""
        return self._hWnd.isMiniaturized()

    @property
    def isMaximized(self):
        """Returns ``True`` if the window is currently maximized (fullscreen)."""
        return self._hWnd.isZoomed()

    @property
    def isActive(self):
        """Returns ``True`` if the window is currently the active, foreground window."""
        windows = getAllWindows(self._app)
        for win in windows:
            return self._hWnd == win
        return False

    @property
    def title(self):
        """Returns the window title as a string."""
        return self._hWnd.title()

    @property
    def visible(self):
        """Returns ``True`` if the window is currently visible."""
        return self._hWnd.isVisible()


def cursor():
    """Returns the current xy coordinates of the mouse cursor as a two-integer tuple

    Returns:
      (x, y) tuple of the current xy coordinates of the mouse cursor.
    """
    # https://stackoverflow.com/questions/3698635/getting-cursor-position-in-python/24567802
    mp = Quartz.NSEvent.mouseLocation()
    x = mp.x
    y = resolution().height - mp.y
    return Point(x, y)


def resolution():
    """Returns the width and height of the screen as a two-integer tuple.

    Returns:
      (width, height) tuple of the screen size, in pixels.
    """
    # https://stackoverflow.com/questions/1281397/how-to-get-the-desktop-resolution-in-mac-via-python
    mainMonitor = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
    return Size(mainMonitor.size.width, mainMonitor.size.height)


def displayWindowsUnderMouse(xOffset=0, yOffset=0):
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
