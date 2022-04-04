# PyWinCtl
# A cross-platform module to get info on and control windows on screen

# pywin32 on Windows
# pyobjc (AppKit and Quartz) on macOS
# Xlib and ewmh on Linux


__version__ = "0.0.33"

import collections
import numpy as np
import re
import sys
import threading
from typing import Tuple, List

import pyrect

Rect = collections.namedtuple("Rect", "left top right bottom")
Point = collections.namedtuple("Point", "x y")
Size = collections.namedtuple("Size", "width height")


def pointInRect(x, y, left, top, width, height):
    """Returns ``True`` if the ``(x, y)`` point is within the box described
    by ``(left, top, width, height)``."""
    return left < x < left + width and top < y < top + height


def version(numberOnly=True):
    """Returns the current version of PyWinCtl module, in the form ''x.x.xx'' as string"""
    return ("" if numberOnly else "PyWinCtl-")+__version__


class Re:
    # Thanks to macdeport for this nice piece of code
    IS = 1
    CONTAINS = 2
    STARTSWITH = 3
    ENDSWITH = 4
    NOTIS = -1
    NOTCONTAINS = -2
    NOTSTARTSWITH = -3
    NOTENDSWITH = -4
    MATCH = 10
    NOTMATCH = -10
    EDITDISTANCE = 20

    IGNORECASE = re.IGNORECASE

    _cond_dic = {
        IS: lambda s1, s2, fl: s1 == s2,
        CONTAINS: lambda s1, s2, fl: s1 in s2,
        STARTSWITH: lambda s1, s2, fl: s2.startswith(s1),
        ENDSWITH: lambda s1, s2, fl: s2.endswith(s1),
        NOTIS: lambda s1, s2, fl: s1 != s2,
        NOTCONTAINS: lambda s1, s2, fl: s1 not in s2,
        NOTSTARTSWITH: lambda s1, s2, fl: not s2.startswith(s1),
        NOTENDSWITH: lambda s1, s2, fl: not s2.endswith(s1),
        MATCH: lambda s1, s2, fl: bool(s1.search(s2)),
        NOTMATCH: lambda s1, s2, fl: not (bool(s1.search(s2))),
        EDITDISTANCE: lambda s1, s2, fl: _levenshtein(s1, s2, fl)
    }


def _levenshtein(seq1: str, seq2: str, similarity: int = 90) -> bool:
    # https://stackabuse.com/levenshtein-distance-and-text-similarity-in-python/
    # Adapted to return a similarity percentage, which is easier to define
    size_x = len(seq1) + 1
    size_y = len(seq2) + 1
    matrix = np.zeros((size_x, size_y))
    for x in range(size_x):
        matrix[x, 0] = x
    for y in range(size_y):
        matrix[0, y] = y

    for x in range(1, size_x):
        for y in range(1, size_y):
            if seq1[x - 1] == seq2[y - 1]:
                matrix[x, y] = min(
                    matrix[x - 1, y] + 1,
                    matrix[x - 1, y - 1],
                    matrix[x, y - 1] + 1
                )
            else:
                matrix[x, y] = min(
                    matrix[x - 1, y] + 1,
                    matrix[x - 1, y - 1] + 1,
                    matrix[x, y - 1] + 1
                )
    dist = matrix[size_x - 1, size_y - 1]
    return ((1 - dist / max(len(seq1), len(seq2))) * 100) >= similarity


class BaseWindow:
    def __init__(self):
        pass

    def _setupRectProperties(self, bounds: Rect = None) -> None:

        def _onRead(attrName):
            r = self._getWindowRect()
            self._rect._left = r.left               # Setting _left directly to skip the onRead.
            self._rect._top = r.top                 # Setting _top directly to skip the onRead.
            self._rect._width = r.right - r.left    # Setting _width directly to skip the onRead.
            self._rect._height = r.bottom - r.top   # Setting _height directly to skip the onRead.

        def _onChange(oldBox, newBox):
            self._moveResizeTo(newBox.left, newBox.top, newBox.width, newBox.height)

        if bounds:
            r = bounds
        else:
            r = self._getWindowRect()
        self._rect = pyrect.Rect(r.left, r.top, r.right - r.left, r.bottom - r.top, onChange=_onChange, onRead=_onRead)

    def _getWindowRect(self) -> Rect:
        raise NotImplementedError

    def __str__(self):
        r = self._getWindowRect()
        width = r.right - r.left
        height = r.bottom - r.top
        return '<%s left="%s", top="%s", width="%s", height="%s", title="%s">' % (
            self.__class__.__qualname__,
            r.left,
            r.top,
            width,
            height,
            self.title,
        )

    def getExtraFrameSize(self, includeBorder: bool = True) -> Tuple[int, int, int, int]:
        """
        Get the extra space, in pixels, around the window, including or not the border.
        Notice not all applications/windows will use this property values

        :param includeBorder: set to ''False'' to avoid including borders
        :return: (left, top, right, bottom) frame size as a tuple of int
        """
        raise NotImplementedError

    def getClientFrame(self):
        """
        Get the client area of window, as a Rect (x, y, right, bottom)
        Notice that scroll and status bars might be included, or not, depending on the application

        :return: Rect struct
        """
        raise NotImplementedError

    def close(self) -> bool:
        """Closes this window. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from
        actually closing. This is identical to clicking the X button on the
        window."""
        raise NotImplementedError

    def minimize(self, wait: bool = False) -> bool:
        """Minimizes this window."""
        raise NotImplementedError

    def maximize(self, wait: bool = False) -> bool:
        """Maximizes this window."""
        raise NotImplementedError

    def restore(self, wait: bool = False) -> bool:
        """If maximized or minimized, restores the window to it's normal size."""
        raise NotImplementedError

    def hide(self, wait: bool = False) -> bool:
        """If hidden or showing, hides the app from screen and title bar."""
        raise NotImplementedError

    def show(self, wait: bool = False) -> bool:
        """If hidden or showing, shows the window on screen and in title bar."""
        raise NotImplementedError

    def activate(self, wait: bool = False) -> bool:
        """Activate this window and make it the foreground window."""
        raise NotImplementedError

    def resize(self, widthOffset: int, heightOffset: int, wait: bool = False) -> bool:
        """Resizes the window relative to its current size."""
        raise NotImplementedError
    resizeRel = resize  # resizeRel is an alias for the resize() method.

    def resizeTo(self, newWidth: int, newHeight: int, wait: bool = False) -> bool:
        """Resizes the window to a new width and height."""
        raise NotImplementedError

    def move(self, xOffset: int, yOffset: int, wait: bool = False) -> bool:
        """Moves the window relative to its current position."""
        raise NotImplementedError
    moveRel = move  # moveRel is an alias for the move() method.

    def moveTo(self, newLeft:int, newTop: int, wait: bool = False) -> bool:
        """Moves the window to new coordinates on the screen."""
        raise NotImplementedError

    def _moveResizeTo(self, newLeft: int, newTop: int, newWidth: int, newHeight: int) -> bool:
        raise NotImplementedError

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

    def lowerWindow(self) -> bool:
        """Lowers the window to the bottom so that it does not obscure any sibling windows.
        """
        raise NotImplementedError

    def raiseWindow(self) -> bool:
        """Raises the window to top so that it is not obscured by any sibling windows.
        """
        raise NotImplementedError

    def sendBehind(self, sb: bool = True) -> bool:
        """Sends the window to the very bottom, below all other windows, including desktop icons.
        It may also cause that the window does not accept focus nor keyboard/mouse events.

        Use sb=False to bring the window back from background

        WARNING: On GNOME it will obscure desktop icons... by the moment"""
        raise NotImplementedError

    def getAppName(self) -> str:
        """Returns the name of the app to which current window belongs to, as string"""
        raise NotImplementedError

    def getParent(self):
        """Returns the handle of the window parent"""
        raise NotImplementedError

    def getChildren(self) -> List[int]:
        """
        Get the children handles of current window

        :return: list of handles
        """
        raise NotImplementedError

    def getHandle(self):
        """Returns the handle of the window"""
        raise NotImplementedError

    def isParent(self, child) -> bool:
        """Returns ''True'' if the window is parent of the given window as input argument"""
        raise NotImplementedError
    isParentOf = isParent  # isParentOf is an alias of isParent method

    def isChild(self, parent) -> bool:
        """Returns ''True'' if the window is child of the given window as input argument"""
        raise NotImplementedError
    isChildOf = isChild  # isParentOf is an alias of isParent method

    def getDisplay(self) -> str:
        """Returns the name of the current window display (monitor)"""
        raise NotImplementedError

    @property
    def isMinimized(self) -> bool:
        """Returns ''True'' if the window is currently minimized."""
        raise NotImplementedError

    @property
    def isMaximized(self) -> bool:
        """Returns ''True'' if the window is currently maximized."""
        raise NotImplementedError

    @property
    def isActive(self) -> bool:
        """Returns ''True'' if the window is currently the active, foreground window."""
        raise NotImplementedError

    @property
    def title(self) -> str:
        """Returns the window title as a string."""
        raise NotImplementedError

    @property
    def visible(self) -> bool:
        raise NotImplementedError
    isVisible = visible  # isVisible is an alias for the visible property.

    @property
    def isAlive(self) -> bool:
        raise NotImplementedError

    # Wrappers for pyrect.Rect object's properties:
    @property
    def left(self):
        return self._rect.left

    @left.setter
    def left(self, value):
        # import pdb; pdb.set_trace()
        self._rect.left  # Run rect's onRead to update the Rect object.
        self._rect.left = value

    @property
    def right(self):
        return self._rect.right

    @right.setter
    def right(self, value):
        self._rect.right  # Run rect's onRead to update the Rect object.
        self._rect.right = value

    @property
    def top(self):
        return self._rect.top

    @top.setter
    def top(self, value):
        self._rect.top  # Run rect's onRead to update the Rect object.
        self._rect.top = value

    @property
    def bottom(self):
        return self._rect.bottom

    @bottom.setter
    def bottom(self, value):
        self._rect.bottom  # Run rect's onRead to update the Rect object.
        self._rect.bottom = value

    @property
    def topleft(self):
        return self._rect.topleft

    @topleft.setter
    def topleft(self, value):
        self._rect.topleft  # Run rect's onRead to update the Rect object.
        self._rect.topleft = value

    @property
    def topright(self):
        return self._rect.topright

    @topright.setter
    def topright(self, value):
        self._rect.topright  # Run rect's onRead to update the Rect object.
        self._rect.topright = value

    @property
    def bottomleft(self):
        return self._rect.bottomleft

    @bottomleft.setter
    def bottomleft(self, value):
        self._rect.bottomleft  # Run rect's onRead to update the Rect object.
        self._rect.bottomleft = value

    @property
    def bottomright(self):
        return self._rect.bottomright

    @bottomright.setter
    def bottomright(self, value):
        self._rect.bottomright  # Run rect's onRead to update the Rect object.
        self._rect.bottomright = value

    @property
    def midleft(self):
        return self._rect.midleft

    @midleft.setter
    def midleft(self, value):
        self._rect.midleft  # Run rect's onRead to update the Rect object.
        self._rect.midleft = value

    @property
    def midright(self):
        return self._rect.midright

    @midright.setter
    def midright(self, value):
        self._rect.midright  # Run rect's onRead to update the Rect object.
        self._rect.midright = value

    @property
    def midtop(self):
        return self._rect.midtop

    @midtop.setter
    def midtop(self, value):
        self._rect.midtop  # Run rect's onRead to update the Rect object.
        self._rect.midtop = value

    @property
    def midbottom(self):
        return self._rect.midbottom

    @midbottom.setter
    def midbottom(self, value):
        self._rect.midbottom  # Run rect's onRead to update the Rect object.
        self._rect.midbottom = value

    @property
    def center(self):
        return self._rect.center

    @center.setter
    def center(self, value):
        self._rect.center  # Run rect's onRead to update the Rect object.
        self._rect.center = value

    @property
    def centerx(self):
        return self._rect.centerx

    @centerx.setter
    def centerx(self, value):
        self._rect.centerx  # Run rect's onRead to update the Rect object.
        self._rect.centerx = value

    @property
    def centery(self):
        return self._rect.centery

    @centery.setter
    def centery(self, value):
        self._rect.centery  # Run rect's onRead to update the Rect object.
        self._rect.centery = value

    @property
    def width(self):
        return self._rect.width

    @width.setter
    def width(self, value):
        self._rect.width  # Run rect's onRead to update the Rect object.
        self._rect.width = value

    @property
    def height(self):
        return self._rect.height

    @height.setter
    def height(self, value):
        self._rect.height  # Run rect's onRead to update the Rect object.
        self._rect.height = value

    @property
    def size(self):
        return self._rect.size

    @size.setter
    def size(self, value):
        self._rect.size  # Run rect's onRead to update the Rect object.
        self._rect.size = value

    @property
    def area(self):
        return self._rect.area

    @area.setter
    def area(self, value):
        self._rect.area  # Run rect's onRead to update the Rect object.
        self._rect.area = value

    @property
    def box(self):
        return self._rect.box

    @box.setter
    def box(self, value):
        self._rect.box  # Run rect's onRead to update the Rect object.
        self._rect.box = value


class _WinWatchDog(threading.Thread):

    def __init__(self, win: BaseWindow, isAliveCB=None, isActiveCB=None, isVisibleCB=None, isMinimizedCB=None, isMaximizedCB=None, resizedCB=None, movedCB=None, changedTitleCB=None, changedDisplayCB=None, interval=0.3):
        threading.Thread.__init__(self)
        self._win = win
        self._interval = interval
        self._kill = threading.Event()

        self._isAliveCB = isAliveCB
        self._isActiveCB = isActiveCB
        self._isVisibleCB = isVisibleCB
        self._isMinimizedCB = isMinimizedCB
        self._isMaximizedCB = isMaximizedCB
        self._resizedCB = resizedCB
        self._movedCB = movedCB
        self._changedTitleCB = changedTitleCB
        self._changedDisplayCB = changedDisplayCB

        self._isActive = False
        self._isVisible = False
        self._isMinimized = False
        self._isMaximized = False
        self._size = False
        self._pos = False
        self._title = False
        self._display = False

    def _getInitialValues(self):

        if self._isActiveCB:
            self._isActive = self._win.isActive

        if self._isVisibleCB:
            self._isVisible = self._win.isVisible

        if self._isMinimizedCB:
            self._isMinimized = self._win.isMinimized

        if self._isMaximizedCB:
            self._isMaximized = self._win.isMaximized

        if self._resizedCB:
            self._size = (self._win.width, self._win.height)

        if self._movedCB:
            self._pos = (self._win.left, self._win.top)

        if self._changedTitleCB:
            self._title = self._win.title

        if self._changedDisplayCB:
            self._display = self._win.getDisplay()

    def run(self):

        self._getInitialValues()

        while not self._kill.is_set():

            self._kill.wait(self._interval)

            try:
                if self._isAliveCB:
                    if not self._win.isAlive:
                        self._isAliveCB(False)
                        break

                if self._isActiveCB:
                    active = self._win.isActive
                    if self._isActive != active:
                        self._isActive = active
                        self._isActiveCB(active)

                if self._isVisibleCB:
                    visible = self._win.isVisible
                    if self._isVisible != visible:
                        self._isVisible = visible
                        self._isVisibleCB(visible)

                if self._isMinimizedCB:
                    minimized = self._win.isMinimized
                    if self._isMinimized != minimized:
                        self._isMinimized = minimized
                        self._isMinimizedCB(minimized)

                if self._isMaximizedCB:
                    maximized = self._win.isMaximized
                    if self._isMaximized != maximized:
                        self._isMaximized = maximized
                        self._isMaximizedCB(maximized)

                if self._resizedCB:
                    size = (self._win.width, self._win.height)
                    if self._size != size:
                        self._size = size
                        self._resizedCB(size)

                if self._movedCB:
                    pos = (self._win.left, self._win.top)
                    if self._pos != pos:
                        self._pos = pos
                        self._movedCB(pos)

                if self._changedTitleCB:
                    title = self._win.title
                    if self._title != title:
                        self._title = title
                        self._changedTitleCB(title)

                if self._changedDisplayCB:
                    display = self._win.getDisplay()
                    if self._display != display:
                        self._display = display
                        self._changedDisplayCB(display)
            except:
                self.kill()
                if self._isAliveCB:
                    if not self._win.isAlive:
                        self._isAliveCB(False)
                break

    def updateCallbacks(self, isAliveCB=None, isActiveCB=None, isVisibleCB=None, isMinimizedCB=None, isMaximizedCB=None, resizedCB=None, movedCB=None, changedTitleCB=None, changedDisplayCB=None):

        self._isAliveCB = isAliveCB
        self._isActiveCB = isActiveCB
        self._isVisibleCB = isVisibleCB
        self._isMinimizedCB = isMinimizedCB
        self._isMaximizedCB = isMaximizedCB
        self._resizedCB = resizedCB
        self._movedCB = movedCB
        self._changedTitleCB = changedTitleCB
        self._changedDisplayCB = changedDisplayCB

        self._getInitialValues()

    def updateInterval(self, interval=0.3):
        self._interval = interval

    def kill(self):
        self._kill.set()


if sys.platform == "darwin":
    from ._pywinctl_macos import (
        MacOSWindow,
        MacOSNSWindow,
        getActiveWindow,
        getActiveWindowTitle,
        getAllWindows,
        getAllTitles,
        getWindowsWithTitle,
        getAllAppsNames,
        getAppsWithName,
        getAllAppsWindowsTitles,
        getWindowsAt,
        getAllScreens,
        getMousePos,
        getScreenSize,
        getWorkArea,
    )

    Window = MacOSWindow
    NSWindow = MacOSNSWindow

elif sys.platform == "win32":
    from ._pywinctl_win import (
        Win32Window,
        getActiveWindow,
        getActiveWindowTitle,
        getAllWindows,
        getAllTitles,
        getWindowsWithTitle,
        getAllAppsNames,
        getAppsWithName,
        getAllAppsWindowsTitles,
        getWindowsAt,
        getAllScreens,
        getMousePos,
        getScreenSize,
        getWorkArea,
    )

    Window = Win32Window

elif sys.platform == "linux":
    from ._pywinctl_linux import (
        LinuxWindow,
        getActiveWindow,
        getActiveWindowTitle,
        getAllWindows,
        getAllTitles,
        getWindowsWithTitle,
        getAllAppsNames,
        getAppsWithName,
        getAllAppsWindowsTitles,
        getWindowsAt,
        getAllScreens,
        getMousePos,
        getScreenSize,
        getWorkArea,
    )

    Window = LinuxWindow

else:
    raise NotImplementedError('PyWinCtl currently does not support this platform. If you think you can help, please contribute! https://github.com/Kalmat/PyWinCtl')
