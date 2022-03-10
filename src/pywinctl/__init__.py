# PyWinCtl
# A cross-platform module to get info on and control windows on screen

# pywin32 on Windows
# pyobjc (AppKit and Quartz) on macOS
# Xlib and ewmh on Linux


__version__ = "0.0.28"

import sys, collections, pyrect

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


if sys.platform == "darwin":
    from ._pywinctl_macos import (
        MacOSWindow,
        MacOSNSWindow,
        getActiveWindow,
        getActiveWindowTitle,
        getWindowsAt,
        getWindowsWithTitle,
        getAllWindows,
        getAllTitles,
        getAllAppsTitles,
        getAllAppsWindowsTitles,
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
        getWindowsAt,
        getWindowsWithTitle,
        getAllWindows,
        getAllTitles,
        getAllAppsTitles,
        getAllAppsWindowsTitles,
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
        getWindowsAt,
        getWindowsWithTitle,
        getAllWindows,
        getAllTitles,
        getAllAppsTitles,
        getAllAppsWindowsTitles,
        getMousePos,
        getScreenSize,
        getWorkArea,
    )

    Window = LinuxWindow
else:
    raise NotImplementedError('PyWinCtl currently does not support this platform. If you think you can help, please contribute! https://github.com/Kalmat/PyWinCtl')
