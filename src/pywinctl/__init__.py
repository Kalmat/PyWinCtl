#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations


import difflib
import re
import sys
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, cast, List, Tuple, Union, TypedDict, Optional, Dict

from ._mybox import MyBox, Box, BoundingBox, Rect, Point, Size


__all__ = [
    "BaseWindow", "version", "Re", "monitorPlugDetection", "isMonitorPlugDetectionEnabled",
    # OS Specifics
    "Window", "checkPermissions", "getActiveWindow", "getActiveWindowTitle", "getAllAppsNames",
    "getAllAppsWindowsTitles", "getAllScreens", "getAllTitles", "getAllWindows", "getAppsWithName", "getMousePos",
    "getScreenSize", "getTopWindowAt", "getWindowsAt", "getWindowsWithTitle", "getWorkArea",
]
# Mac only
if sys.platform == "darwin":
    __all__ += ["NSWindow"]

__version__ = "0.1"


def version(numberOnly: bool = True):
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
    DIFFRATIO = 30

    IGNORECASE = re.IGNORECASE

    # Does not play well with static typing and current implementation of TypedDict
    _cond_dic: dict[int, Callable[[str | re.Pattern[str], str, float], bool]] = {
        IS: lambda s1, s2, fl: s1 == s2,
        CONTAINS: lambda s1, s2, fl: s1 in s2,  # type: ignore  # pyright: ignore
        STARTSWITH: lambda s1, s2, fl: s2.startswith(s1),  # type: ignore  # pyright: ignore
        ENDSWITH: lambda s1, s2, fl: s2.endswith(s1),  # type: ignore  # pyright: ignore
        NOTIS: lambda s1, s2, fl: s1 != s2,
        NOTCONTAINS: lambda s1, s2, fl: s1 not in s2,  # type: ignore  # pyright: ignore
        NOTSTARTSWITH: lambda s1, s2, fl: not s2.startswith(s1),  # type: ignore  # pyright: ignore
        NOTENDSWITH: lambda s1, s2, fl: not s2.endswith(s1),  # type: ignore  # pyright: ignore
        MATCH: lambda s1, s2, fl: bool(s1.search(s2)),  # type: ignore  # pyright: ignore
        NOTMATCH: lambda s1, s2, fl: not (bool(s1.search(s2))),  # type: ignore  # pyright: ignore
        EDITDISTANCE: lambda s1, s2, fl: _levenshtein(s1, s2) >= fl,  # type: ignore  # pyright: ignore
        DIFFRATIO: lambda s1, s2, fl: difflib.SequenceMatcher(None, s1, s2).ratio() * 100 >= fl  # type: ignore  # pyright: ignore
    }


def _levenshtein(seq1: str, seq2: str) -> float:
    # https://stackabuse.com/levenshtein-distance-and-text-similarity-in-python/
    # Adapted to return a similarity percentage, which is easier to define
    # Removed numpy to reduce dependencies. This is likely slower, but titles are not too long
    size_x = len(seq1) + 1
    size_y = len(seq2) + 1
    matrix = [[0 for _y in range(size_y)] for _x in range(size_x)]
    for x in range(size_x):
        matrix[x][0] = x
    matrix[0] = list(range(0, size_y))

    for x in range(1, size_x):
        for y in range(1, size_y):
            if seq1[x - 1] == seq2[y - 1]:
                matrix[x][y] = min(
                    matrix[x - 1][y] + 1,
                    matrix[x - 1][y - 1],
                    matrix[x][y - 1] + 1
                )
            else:
                matrix[x][y] = min(
                    matrix[x - 1][y] + 1,
                    matrix[x - 1][y - 1] + 1,
                    matrix[x][y - 1] + 1
                )
    dist = matrix[size_x - 1][size_y - 1]
    return (1 - dist / max(len(seq1), len(seq2))) * 100


class _ScreenValue(TypedDict):
    id: int
    is_primary: bool
    pos: Point
    size: Size
    workarea: Rect
    scale: Tuple[int, int]
    dpi: Tuple[int, int]
    orientation: int
    frequency: float
    colordepth: int


class BaseWindow(ABC):

    def _boxFactory(self, box: Box) -> MyBox:
        self._box: MyBox = MyBox(box, self._onSet, self._onQuery)
        return self._box

    def _onSet(self, newBox: Box):
        self._moveResizeTo(newBox)

    @abstractmethod
    def _moveResizeTo(self, newBox: Box) -> bool:
        raise NotImplementedError

    def _onQuery(self) -> Box:
        box: Box = self._getWindowRect()
        return box

    @abstractmethod
    def _getWindowRect(self) -> Box:
        raise NotImplementedError

    def __str__(self):
        r = self._getWindowRect()
        return '<%s left="%s", top="%s", width="%s", height="%s", title="%s">' % (
            self.__class__.__qualname__,
            self.title,
            r.left,
            r.top,
            r.width,
            r.height,
        )

    @abstractmethod
    def getExtraFrameSize(self, includeBorder: bool = True) -> Tuple[int, int, int, int]:
        """
        Get the extra space, in pixels, around the window, including or not the border.
        Notice not all applications/windows will use this property values

        :param includeBorder: set to ''False'' to avoid including borders
        :return: (left, top, right, bottom) frame size as a tuple of int
        """
        raise NotImplementedError

    @abstractmethod
    def getClientFrame(self) -> Tuple[int, int, int, int]:
        """
        Get the client area of window, as a Rect (x, y, right, bottom)
        Notice that scroll and status bars might be included, or not, depending on the application

        :return: Rect struct
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> bool:
        """Closes this window. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from
        actually closing. This is identical to clicking the X button on the
        window."""
        raise NotImplementedError

    @abstractmethod
    def minimize(self, wait: bool = False) -> bool:
        """Minimizes this window."""
        raise NotImplementedError

    @abstractmethod
    def maximize(self, wait: bool = False) -> bool:
        """Maximizes this window."""
        raise NotImplementedError

    @abstractmethod
    def restore(self, wait: bool = False, user: bool = True) -> bool:
        """If maximized or minimized, restores the window to it's normal size."""
        raise NotImplementedError

    @abstractmethod
    def hide(self, wait: bool = False) -> bool:
        """If hidden or showing, hides the app from screen and title bar."""
        raise NotImplementedError

    @abstractmethod
    def show(self, wait: bool = False) -> bool:
        """If hidden or showing, shows the window on screen and in title bar."""
        raise NotImplementedError

    @abstractmethod
    def activate(self, wait: bool = False, user: bool = True) -> bool:
        """Activate this window and make it the foreground window."""
        raise NotImplementedError

    @abstractmethod
    def resize(self, widthOffset: int, heightOffset: int, wait: bool = False) -> bool:
        """Resizes the window relative to its current size."""
        raise NotImplementedError
    resizeRel = resize  # resizeRel is an alias for the resize() method.

    @abstractmethod
    def resizeTo(self, newWidth: int, newHeight: int, wait: bool = False) -> bool:
        """Resizes the window to a new width and height."""
        raise NotImplementedError

    @abstractmethod
    def move(self, xOffset: int, yOffset: int, wait: bool = False) -> bool:
        """Moves the window relative to its current position."""
        raise NotImplementedError
    moveRel = move  # moveRel is an alias for the move() method.

    @abstractmethod
    def moveTo(self, newLeft: int, newTop: int, wait: bool = False) -> bool:
        """Moves the window to new coordinates on the screen."""
        raise NotImplementedError

    @abstractmethod
    def alwaysOnTop(self, aot: bool = True) -> bool:
        """Keeps window on top of all others.

        Use aot=False to deactivate always-on-top behavior
        """
        raise NotImplementedError

    @abstractmethod
    def alwaysOnBottom(self, aob: bool = True) -> bool:
        """Keeps window below of all others, but on top of desktop icons and keeping all window properties

        Use aob=False to deactivate always-on-bottom behavior
        """
        raise NotImplementedError

    @abstractmethod
    def lowerWindow(self) -> bool:
        """Lowers the window to the bottom so that it does not obscure any sibling windows.
        """
        raise NotImplementedError

    @abstractmethod
    def raiseWindow(self) -> bool:
        """Raises the window to top so that it is not obscured by any sibling windows.
        """
        raise NotImplementedError

    @abstractmethod
    def sendBehind(self, sb: bool = True) -> bool:
        """Sends the window to the very bottom, below all other windows, including desktop icons.
        It may also cause that the window does not accept focus nor keyboard/mouse events.

        Use sb=False to bring the window back from background

        WARNING: On GNOME it will obscure desktop icons... by the moment"""
        raise NotImplementedError

    @abstractmethod
    def acceptInput(self, setTo: bool) -> None:
        """Toggles the window transparent to input and focus

        :param setTo: True/False to toggle window transparent to input and focus
        :return: None
        """
        raise NotImplementedError

    @abstractmethod
    def getAppName(self) -> str:
        """Returns the name of the app to which current window belongs to, as string"""
        raise NotImplementedError

    @abstractmethod
    def getParent(self) -> object:
        """Returns the handle of the window parent"""
        raise NotImplementedError

    @abstractmethod
    def setParent(self, parent) -> bool:
        """
        Current window will become child of given parent
        WARNIG: Not possible in macOS for foreign (other apps') windows

        :param parent: window to set as current window parent
        :return: ''True'' if current window is now child of given parent
        """
        raise NotImplementedError

    @abstractmethod
    def getChildren(self) -> List[Any]:
        """
        Get the children handles of current window

        :return: list of handles
        """
        raise NotImplementedError

    @abstractmethod
    def getHandle(self) -> int | object:
        """Returns the handle of the window"""
        raise NotImplementedError

    @abstractmethod
    def isParent(self, child: Any) -> bool:
        """Returns ''True'' if the window is parent of the given window as input argument"""
        raise NotImplementedError
    isParentOf = isParent  # isParentOf is an alias of isParent method

    @abstractmethod
    def isChild(self, parent: Any) -> bool:
        """Returns ''True'' if the window is child of the given window as input argument"""
        raise NotImplementedError
    isChildOf = isChild  # isParentOf is an alias of isParent method

    @abstractmethod
    def getDisplay(self) -> str:
        """Returns the name of the current window display (monitor)"""
        raise NotImplementedError

    @property
    @abstractmethod
    def isMinimized(self) -> bool:
        """Returns ''True'' if the window is currently minimized."""
        raise NotImplementedError

    @property
    @abstractmethod
    def isMaximized(self) -> bool:
        """Returns ''True'' if the window is currently maximized."""
        raise NotImplementedError

    @property
    @abstractmethod
    def isActive(self) -> bool:
        """Returns ''True'' if the window is currently the active, foreground window."""
        raise NotImplementedError

    @property
    @abstractmethod
    def title(self) -> str:
        """Returns the window title as a string."""
        raise NotImplementedError

    if sys.platform == "darwin":
        @property
        @abstractmethod
        def updatedTitle(self) -> str:
            """macOS Apple Script ONLY. Returns a similar window title from same app as a string."""
            raise NotImplementedError

    @property
    @abstractmethod
    def visible(self) -> bool:
        raise NotImplementedError
    isVisible: bool = cast(bool, visible)  # isVisible is an alias for the visible property.

    @property
    @abstractmethod
    def isAlive(self) -> bool:
        raise NotImplementedError

    # @property
    # @abstractmethod
    # def isAlerting(self) -> bool:
    #     raise NotImplementedError

    @property
    def left(self) -> int:
        return self._box.left

    @left.setter
    def left(self, value: int):
        self._box.left = value

    @property
    def right(self) -> int:
        return self._box.right

    @right.setter
    def right(self, value: int):
        self._box.right = value

    @property
    def top(self) -> int:
        return self._box.top

    @top.setter
    def top(self, value: int):
        self._box.top = value

    @property
    def bottom(self) -> int:
        return self._box.bottom

    @bottom.setter
    def bottom(self, value: int):
        self._box.bottom = value

    @property
    def width(self) -> int:
        return self._box.width

    @width.setter
    def width(self, value: int):
        self._box.width = value

    @property
    def height(self) -> int:
        return self._box.height

    @height.setter
    def height(self, value: int):
        self._box.height = value

    @property
    def position(self) -> Point:
        return self._box.position

    @position.setter
    def position(self, value: Union[Point, Tuple[int, int]]):
        self._box.position = value

    @property
    def size(self) -> Size:
        return self._box.size

    @size.setter
    def size(self, value: Union[Size, Tuple[int, int]]):
        self._box.size = value

    @property
    def box(self) -> Box:
        return self._box.box

    @box.setter
    def box(self, value: Union[Box, Tuple[int, int, int, int]]):
        self._box.box = value

    @property
    def bbox(self) -> BoundingBox:
        return self._box.bbox

    @bbox.setter
    def bbox(self, value: Union[BoundingBox, Tuple[int, int, int, int]]):
        self._box.bbox = value

    @property
    def rect(self) -> Rect:
        return self._box.rect

    @rect.setter
    def rect(self, value: Union[Rect, Tuple[int, int, int, int]]):
        self._box.rect = value

    @property
    def topleft(self) -> Point:
        return self._box.topleft

    @topleft.setter
    def topleft(self, value: Union[Point, Tuple[int, int]]):
        self._box.topleft = value

    @property
    def bottomleft(self) -> Point:
        return self._box.bottomleft

    @bottomleft.setter
    def bottomleft(self, value: Union[Point, Tuple[int, int]]):
        self._box.bottomleft = value

    @property
    def topright(self) -> Point:
        return self._box.topright

    @topright.setter
    def topright(self, value: Union[Point, Tuple[int, int]]):
        self._box.topright = value

    @property
    def bottomright(self) -> Point:
        return self._box.bottomright

    @bottomright.setter
    def bottomright(self, value: Union[Point, Tuple[int, int]]):
        self._box.bottomright = value

    @property
    def midtop(self) -> Point:
        return self._box.midtop

    @midtop.setter
    def midtop(self, value: Union[Point, Tuple[int, int]]):
        self._box.midtop = value

    @property
    def midbottom(self) -> Point:
        return self._box.midbottom

    @midbottom.setter
    def midbottom(self, value: Union[Point, Tuple[int, int]]):
        self._box.midbottom = value

    @property
    def midleft(self) -> Point:
        return self._box.midleft

    @midleft.setter
    def midleft(self, value: Union[Point, Tuple[int, int]]):
        self._box.midleft = value

    @property
    def midright(self) -> Point:
        return self._box.midright

    @midright.setter
    def midright(self, value: Union[Point, Tuple[int, int]]):
        self._box.midright = value

    @property
    def center(self) -> Point:
        return self._box.center

    @center.setter
    def center(self, value: Union[Point, Tuple[int, int]]):
        self._box.center = value

    @property
    def centerx(self) -> int:
        return self._box.centerx

    @centerx.setter
    def centerx(self, value: int):
        self._box.centerx = value

    @property
    def centery(self) -> int:
        return self._box.centery

    @centery.setter
    def centery(self, value: int):
        self._box.centery = value


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
    def __init__(self, parent: BaseWindow):
        self._watchdog: _WatchDogWorker | None = None
        self._parent = parent

    def start(
        self,
        isAliveCB: Callable[[bool], None] | None = None,
        isActiveCB: Callable[[bool], None] | None = None,
        isVisibleCB: Callable[[bool], None] | None = None,
        isMinimizedCB: Callable[[bool], None] | None = None,
        isMaximizedCB: Callable[[bool], None] | None = None,
        resizedCB: Callable[[Tuple[int, int]], None] | None = None,
        movedCB: Callable[[Tuple[int, int]], None] | None = None,
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

        :param isAliveCB: callback to call if window is not alive. Set to None to not watch this
                        Returns the new alive status value (False)
        :param isActiveCB: callback to invoke if window changes its active status. Set to None to not watch this
                        Returns the new active status value (True/False)
        :param isVisibleCB: callback to invoke if window changes its visible status. Set to None to not watch this
                        Returns the new visible status value (True/False)
        :param isMinimizedCB: callback to invoke if window changes its minimized status. Set to None to not watch this
                        Returns the new minimized status value (True/False)
        :param isMaximizedCB: callback to invoke if window changes its maximized status. Set to None to not watch this
                        Returns the new maximized status value (True/False)
        :param resizedCB: callback to invoke if window changes its size. Set to None to not watch this
                        Returns the new size (width, height)
        :param movedCB: callback to invoke if window changes its position. Set to None to not watch this
                        Returns the new position (x, y)
        :param changedTitleCB: callback to invoke if window changes its title. Set to None to not watch this
                        Returns the new title (as string)
        :param changedDisplayCB: callback to invoke if window changes display. Set to None to not watch this
                        Returns the new display name (as string)
        :param interval: set the interval to watch window changes. Default is 0.3 seconds
        """
        if self._watchdog is None:
            self._watchdog = _WatchDogWorker(self._parent, isAliveCB, isActiveCB, isVisibleCB, isMinimizedCB,
                                             isMaximizedCB, resizedCB, movedCB, changedTitleCB, changedDisplayCB,
                                             interval)
            self._watchdog.daemon = True
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
        resizedCB: Callable[[Tuple[int, int]], None] | None = None,
        movedCB: Callable[[Tuple[int, int]], None] | None = None,
        changedTitleCB: Callable[[str], None] | None = None,
        changedDisplayCB: Callable[[str], None] | None = None
    ):
        """
        Change the states this watchdog is hooked to

        The callbacks definition MUST MATCH their return value (boolean, string or (int, int))

        IMPORTANT: When updating callbacks, remember to set ALL desired callbacks or they will be deactivated

        IMPORTANT: Remember to set ALL desired callbacks every time, or they will be defaulted to None (and unhooked)

        :param isAliveCB: callback to call if window is not alive. Set to None to not watch this
                        Returns the new alive status value (False)
        :param isActiveCB: callback to invoke if window changes its active status. Set to None to not watch this
                        Returns the new active status value (True/False)
        :param isVisibleCB: callback to invoke if window changes its visible status. Set to None to not watch this
                        Returns the new visible status value (True/False)
        :param isMinimizedCB: callback to invoke if window changes its minimized status. Set to None to not watch this
                        Returns the new minimized status value (True/False)
        :param isMaximizedCB: callback to invoke if window changes its maximized status. Set to None to not watch this
                        Returns the new maximized status value (True/False)
        :param resizedCB: callback to invoke if window changes its size. Set to None to not watch this
                        Returns the new size (width, height)
        :param movedCB: callback to invoke if window changes its position. Set to None to not watch this
                        Returns the new position (x, y)
        :param changedTitleCB: callback to invoke if window changes its title. Set to None to not watch this
                        Returns the new title (as string)
        :param changedDisplayCB: callback to invoke if window changes display. Set to None to not watch this
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


class _WatchDogWorker(threading.Thread):

    def __init__(
        self,
        win: BaseWindow,
        isAliveCB: Callable[[bool], None] | None = None,
        isActiveCB: Callable[[bool], None] | None = None,
        isVisibleCB: Callable[[bool], None] | None = None,
        isMinimizedCB: Callable[[bool], None] | None = None,
        isMaximizedCB: Callable[[bool], None] | None = None,
        resizedCB: Callable[[Tuple[int, int]], None] | None = None,
        movedCB: Callable[[Tuple[int, int]], None] | None = None,
        changedTitleCB: Callable[[str], None] | None = None,
        changedDisplayCB: Callable[[str], None] | None = None,
        interval: float = 0.3
    ):
        threading.Thread.__init__(self)
        self._win = win
        self._interval = interval
        self._tryToFind = False
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

        try:
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
        except:
            if self._isAliveCB:
                self._isAliveCB(False)
            self.kill()

    def run(self):

        self._getInitialValues()

        while not self._kill.is_set():

            self._kill.wait(self._interval)

            try:
                # In macOS AppScript version, if title changes, it will consider window is not alive anymore
                if sys.platform == "darwin" and (self._isAliveCB or self._tryToFind) and not self._win.isAlive:
                    if self._isAliveCB:
                        self._isAliveCB(False)
                    if self._tryToFind:
                        title = self._win.title
                        if self._title != title:
                            title = self._win.updatedTitle
                            self._title = title
                            if self._changedTitleCB:
                                self._changedTitleCB(title)
                    if not self._tryToFind or (self._tryToFind and not self._title):
                        self.kill()
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
                        self._isVisibleCB(visible)  # type: ignore[arg-type]  # mypy bug

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
                if self._isAliveCB:
                    self._isAliveCB(False)
                self.kill()
                break

    def updateCallbacks(
        self,
        isAliveCB: Callable[[bool], None] | None = None,
        isActiveCB: Callable[[bool], None] | None = None,
        isVisibleCB: Callable[[bool], None] | None = None,
        isMinimizedCB: Callable[[bool], None] | None = None,
        isMaximizedCB: Callable[[bool], None] | None = None,
        resizedCB: Callable[[Tuple[int, int]], None] | None = None,
        movedCB: Callable[[Tuple[int, int]], None] | None = None,
        changedTitleCB: Callable[[str], None] | None = None,
        changedDisplayCB: Callable[[str], None] | None = None
    ):

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

    def updateInterval(self, interval: float = 0.3):
        self._interval = interval

    def setTryToFind(self, tryToFind: bool):
        if sys.platform == "darwin" and type(self._win).__name__ == Window.__name__:
            self._tryToFind = tryToFind

    def kill(self):
        self._kill.set()

    def restart(
        self,
        isAliveCB: Callable[[bool], None] | None = None,
        isActiveCB: Callable[[bool], None] | None = None,
        isVisibleCB: Callable[[bool], None] | None = None,
        isMinimizedCB: Callable[[bool], None] | None = None,
        isMaximizedCB: Callable[[bool], None] | None = None,
        resizedCB: Callable[[Tuple[int, int]], None] | None = None,
        movedCB: Callable[[Tuple[int, int]], None] | None = None,
        changedTitleCB: Callable[[str], None] | None = None,
        changedDisplayCB: Callable[[str], None] | None = None,
        interval: float = 0.3
    ):
        self._kill.set()
        self._kill.clear()
        self.updateCallbacks(isAliveCB, isActiveCB, isVisibleCB, isMinimizedCB, isMaximizedCB, resizedCB, movedCB, changedTitleCB, changedDisplayCB)
        self.updateInterval(interval)
        self.run()


class _UpdateScreens:

    def __init__(self):
        self._worker: _UpdateScreensWorker = _UpdateScreensWorker()
        self._worker.daemon = True
        self._worker.start()

    def getScreens(self) -> Optional[_ScreenValue]:
        return self._worker.getScreens()

    def stop(self):
        self._worker.kill()
        self._worker.join()


class _UpdateScreensWorker(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

        self._screens: Optional[_ScreenValue] = None
        self._kill = threading.Event()
        self._interval = 0.3

    def run(self):

        while not self._kill.is_set():
            self._screens = getAllScreens()
            self._kill.wait(self._interval)

    def getScreens(self) -> Optional[_ScreenValue]:
        return self._screens

    def kill(self):
        self._kill.set()


_updateScreens: Optional[_UpdateScreens] = None


def monitorPlugDetection(enable: bool):
    """
    Enable this only in a multi-monitor setup in which monitors can be dynamically plugged or unplugged, and
    only if you need to keep track of these monitors to manipulate or control the window objects.

    If enabled, it will activate a separate thread which will periodically update the list of Monitors
    connected to or disconnected from the system.

    If disabled, the information on the monitors connected to the system will be static as it was when
    the window object was created (if a monitor is connected or disconnected afterward, it will not be detected)

    :param enable: Set to ''True'' to activate monitor plug/unplug detection.
                   Set to ''False'' to stop and kill the thread.
    """
    global _updateScreens
    if enable:
        if _updateScreens is None:
            _updateScreens = _UpdateScreens()
    else:
        if _updateScreens is not None:
            _updateScreens.stop()
            _updateScreens = None


def isMonitorPlugDetectionEnabled() -> bool:
    """
    Returns ''True'' if the dynamic monitor detection is enabled. ''False'' otherwise
    """
    global _updateScreens
    return bool(_updateScreens is not None)


def _getScreens() -> Optional[_ScreenValue]:
    global _updateScreens
    if _updateScreens is not None:
        return _updateScreens.getScreens()
    else:
        return None


if sys.platform == "darwin":
    from ._pywinctl_macos import (MacOSNSWindow as NSWindow, MacOSWindow as Window, checkPermissions, getActiveWindow,
                                  getActiveWindowTitle, getAllAppsNames, getAllAppsWindowsTitles, getAllScreens,
                                  getAllTitles, getAllWindows, getAppsWithName, getMousePos, getScreenSize,
                                  getTopWindowAt, getWindowsAt, getWindowsWithTitle, getWorkArea)

elif sys.platform == "win32":
    from ._pywinctl_win import (Win32Window as Window, checkPermissions, getActiveWindow, getActiveWindowTitle,
                                getAllAppsNames, getAllAppsWindowsTitles, getAllScreens, getAllTitles, getAllWindows,
                                getAppsWithName, getMousePos, getScreenSize, getTopWindowAt, getWindowsAt,
                                getWindowsWithTitle, getWorkArea)

elif sys.platform == "linux":
    from ._pywinctl_linux import (LinuxWindow as Window, checkPermissions, getActiveWindow, getActiveWindowTitle,
                                  getAllAppsNames, getAllAppsWindowsTitles, getAllScreens, getAllTitles, getAllWindows,
                                  getAppsWithName, getMousePos, getScreenSize, getTopWindowAt, getWindowsAt,
                                  getWindowsWithTitle, getWorkArea)

else:
    raise NotImplementedError('PyWinCtl currently does not support this platform. If you think you can help, please contribute! https://github.com/Kalmat/PyWinCtl')
