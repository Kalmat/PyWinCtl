#!/usr/bin/python
# -*- coding: utf-8 -*-

import ctypes
import sys
import time
import threading
from ctypes import wintypes  # We can't use ctypes.wintypes, we must import wintypes this way.

import win32con
import win32gui
from pygetwindowmp import PyGetWindowException, pointInRect, BaseWindow, Rect, Point, Size

NULL = 0 # Used to match the Win32 API value of "null".

# These FORMAT_MESSAGE_ constants are used for FormatMesage() and are
# documented at https://docs.microsoft.com/en-us/windows/desktop/api/winbase/nf-winbase-formatmessage#parameters
FORMAT_MESSAGE_ALLOCATE_BUFFER = 0x00000100
FORMAT_MESSAGE_FROM_SYSTEM = 0x00001000
FORMAT_MESSAGE_IGNORE_INSERTS = 0x00000200

# These SW_ constants are used for ShowWindow() and are documented at
# https://docs.microsoft.com/en-us/windows/desktop/api/winuser/nf-winuser-showwindow#parameters
SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_HIDE = 0
SW_SHOW = 5
SW_RESTORE = 9

# SetWindowPos constants:
HWND_TOP = 0
HWND_BOTTOM = 1

# Window Message constants:
WM_CLOSE = 0x0010
SMTO_NORMAL = 0

# This ctypes structure is for a Win32 POINT structure,
# which is documented here: http://msdn.microsoft.com/en-us/library/windows/desktop/dd162805(v=vs.85).aspx
# The POINT structure is used by GetCursorPos().
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long),
                ("y", ctypes.c_long)]

enumWindows = ctypes.windll.user32.EnumWindows
enumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
getWindowText = ctypes.windll.user32.GetWindowTextW
getWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
isWindowVisible = ctypes.windll.user32.IsWindowVisible


class RECT(ctypes.Structure):
    """A nice wrapper of the RECT structure.

    Microsoft Documentation:
    https://msdn.microsoft.com/en-us/library/windows/desktop/dd162897(v=vs.85).aspx
    """
    _fields_ = [('left', ctypes.c_long),
                ('top', ctypes.c_long),
                ('right', ctypes.c_long),
                ('bottom', ctypes.c_long)]


def _getAllTitles():
    # This code taken from https://sjohannes.wordpress.com/2012/03/23/win32-python-getting-all-window-titles/
    # A correction to this code (for enumWindowsProc) is here: http://makble.com/the-story-of-lpclong
    titles = []

    def foreach_window(hWnd, lParam):
        if isWindowVisible(hWnd):
            length = getWindowTextLength(hWnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            getWindowText(hWnd, buff, length + 1)
            titles.append((hWnd, buff.value))
        return True
    enumWindows(enumWindowsProc(foreach_window), 0)

    return titles


def _formatMessage(errorCode):
    """A nice wrapper for FormatMessageW(). TODO

    Microsoft Documentation:
    https://docs.microsoft.com/en-us/windows/desktop/api/winbase/nf-winbase-formatmessagew

    Additional information:
    https://stackoverflow.com/questions/18905702/python-ctypes-and-mutable-buffers
    https://stackoverflow.com/questions/455434/how-should-i-use-formatmessage-properly-in-c
    """
    lpBuffer = wintypes.LPWSTR()

    ctypes.windll.kernel32.FormatMessageW(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_IGNORE_INSERTS,
                                          NULL,
                                          errorCode,
                                          0, # dwLanguageId
                                          ctypes.cast(ctypes.byref(lpBuffer), wintypes.LPWSTR),
                                          0, # nSize
                                          NULL)
    msg = lpBuffer.value.rstrip()
    ctypes.windll.kernel32.LocalFree(lpBuffer) # Free the memory allocated for the error message's buffer.
    return msg


def _raiseWithLastError():
    """A helper function that raises PyGetWindowException using the error
    information from GetLastError() and FormatMessage()."""
    errorCode = ctypes.windll.kernel32.GetLastError()
    raise PyGetWindowException('Error code from Windows: %s - %s' % (errorCode, _formatMessage(errorCode)))


def getActiveWindow():
    """Returns a Window object of the currently active (focused) Window."""
    hWnd = ctypes.windll.user32.GetForegroundWindow()
    if hWnd == 0:
        # TODO - raise error instead
        return None # Note that this function doesn't use GetLastError().
    else:
        return Win32Window(hWnd)


def getActiveWindowTitle():
    """Returns a string of the title text of the currently active (focused) Window."""
    # NOTE - This function isn't threadsafe because it relies on a global variable. I don't use nonlocal because I want this to work on Python 2.

    global activeWindowTitle
    activeWindowHwnd = ctypes.windll.user32.GetForegroundWindow()
    if activeWindowHwnd == 0:
        # TODO - raise error instead
        return None # Note that this function doesn't use GetLastError().

    def foreach_window(hWnd, lParam):
        global activeWindowTitle
        if hWnd == activeWindowHwnd:
            length = getWindowTextLength(hWnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            getWindowText(hWnd, buff, length + 1)
            activeWindowTitle =  buff.value
        return True
    enumWindows(enumWindowsProc(foreach_window), 0)

    return activeWindowTitle


def getWindowsAt(x, y):
    """Returns a list of Window objects whose windows contain the point ``(x, y)``.

    * ``x`` (int, optional): The x position of the window(s).
    * ``y`` (int, optional): The y position of the window(s)."""
    windowsAtXY = []
    for window in getAllWindows():
        if pointInRect(x, y, window.left, window.top, window.width, window.height):
            windowsAtXY.append(window)
    return windowsAtXY


def getWindowsWithTitle(title):
    """Returns a list of Window objects that substring match ``title`` in their title text."""
    hWndsAndTitles = _getAllTitles()
    windowObjs = []
    for hWnd, winTitle in hWndsAndTitles:
        if title.upper() in winTitle.upper(): # do a case-insensitive match
            windowObjs.append(Win32Window(hWnd))
    return windowObjs


def getAllTitles():
    """Returns a list of strings of window titles for all visible windows.
    """
    return [window.title for window in getAllWindows()]


def getAllWindows():
    """Returns a list of Window objects for all visible windows.
    """
    windowObjs = []
    def foreach_window(hWnd, lParam):
        if ctypes.windll.user32.IsWindowVisible(hWnd) != 0:
            windowObjs.append(Win32Window(hWnd))
        return True
    enumWindows(enumWindowsProc(foreach_window), 0)

    return windowObjs

def _getChildWindows(parent):

    children = []

    def foreach_window(hwnd, param):
        children.append(hwnd)

    ctypes.windll.user32.EnumChildWindows(parent, enumWindowsProc(foreach_window), None)
    return children


class Win32Window(BaseWindow):
    def __init__(self, hWnd):
        self._hWnd = hWnd # TODO fix this, this is a LP_c_long insead of an int.
        self._parent = win32gui.GetParent(self._hWnd)
        self._t = None
        self._tContinue = False
        self._setupRectProperties()


    def _getWindowRect(self):
        """A nice wrapper for GetWindowRect(). TODO

        Syntax:
        BOOL GetWindowRect(
          HWND   hWnd,
          LPRECT lpRect
        );

        Microsoft Documentation:
        https://docs.microsoft.com/en-us/windows/desktop/api/winuser/nf-winuser-getwindowrect
        """
        rect = RECT()
        result = ctypes.windll.user32.GetWindowRect(self._hWnd, ctypes.byref(rect))
        if result != 0:
            return Rect(rect.left, rect.top, rect.right, rect.bottom)
        else:
            _raiseWithLastError()


    def __repr__(self):
        return '%s(hWnd=%s)' % (self.__class__.__name__, self._hWnd)


    def __eq__(self, other):
        return isinstance(other, Win32Window) and self._hWnd == other._hWnd


    def close(self):
        """Closes this window. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from
        actually closing. This is identical to clicking the X button on the
        window."""
        result = ctypes.windll.user32.PostMessageA(self._hWnd, WM_CLOSE, 0, 0)
        if result == 0:
            _raiseWithLastError()


    def minimize(self):
        """Minimizes this window."""
        ctypes.windll.user32.ShowWindow(self._hWnd, SW_MINIMIZE)


    def maximize(self):
        """Maximizes this window."""
        ctypes.windll.user32.ShowWindow(self._hWnd, SW_MAXIMIZE)


    def restore(self):
        """If maximized or minimized, restores the window to it's normal size."""
        ctypes.windll.user32.ShowWindow(self._hWnd, SW_RESTORE)
        
    def show(self):
        """If hidden or showing, shows the window on screen and in title bar."""
        ctypes.windll.user32.ShowWindow(self._hWnd,SW_SHOW)

    def hide(self):
        """If hidden or showing, hides the window from screen and title bar."""
        ctypes.windll.user32.ShowWindow(self._hWnd,SW_HIDE)

    def activate(self):
        """Activate this window and make it the foreground (focused) window."""
        result = ctypes.windll.user32.SetForegroundWindow(self._hWnd)
        if result == 0:
            _raiseWithLastError()


    def resize(self, widthOffset, heightOffset):
        """Resizes the window relative to its current size."""
        result = ctypes.windll.user32.SetWindowPos(self._hWnd, HWND_TOP, self.left, self.top, self.width + widthOffset, self.height + heightOffset, 0)
        if result == 0:
            _raiseWithLastError()
    resizeRel = resize # resizeRel is an alias for the resize() method.

    def resizeTo(self, newWidth, newHeight):
        """Resizes the window to a new width and height."""
        result = ctypes.windll.user32.SetWindowPos(self._hWnd, HWND_TOP, self.left, self.top, newWidth, newHeight, 0)
        if result == 0:
            _raiseWithLastError()


    def move(self, xOffset, yOffset):
        """Moves the window relative to its current position."""
        result = ctypes.windll.user32.SetWindowPos(self._hWnd, HWND_TOP, self.left + xOffset, self.top + yOffset, self.width, self.height, 0)
        if result == 0:
            _raiseWithLastError()
    moveRel = move # moveRel is an alias for the move() method.

    def moveTo(self, newLeft, newTop):
        """Moves the window to new coordinates on the screen."""
        result = ctypes.windll.user32.SetWindowPos(self._hWnd, HWND_TOP, newLeft, newTop, self.width, self.height, 0)
        if result == 0:
            _raiseWithLastError()

    def alwaysOnTop(self, aot=True):
        """Keeps window on top of all others.

        Use aot=False to deactivate always-on-top behavior
        """
        # https://stackoverflow.com/questions/25381589/pygame-set-window-on-top-without-changing-its-position/49482325 (kmaork)
        zorder = win32con.HWND_TOPMOST if aot else win32con.HWND_NOTOPMOST
        result = win32gui.SetWindowPos(self._hWnd, zorder, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        if result == 0:
            _raiseWithLastError()

    def alwaysOnBottom(self, aob=True):
        """Keeps window below of all others, but on top of desktop icons and keeping all window properties

        Use aob=False to deactivate always-on-bottom behavior
        """

        if aob:
            result = win32gui.SetWindowPos(self._hWnd, HWND_BOTTOM, 0, 0, 0, 0,
                                           win32con.SWP_NOSIZE | win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE)
            # there is no HWND_TOPBOTTOM (similar to TOPMOST), so it won't keep window below all others as desired
            if self._t is None:
                self._t = _sendBottom(self._hWnd)
                self._t.daemon = True
            if not self._t.is_alive():
                self._t.start()
            # TODO: Catch win32con.WM_WINDOWPOSCHANGING and resend window to bottom (is it possible with pywin32?)
            # https://stackoverflow.com/questions/527950/how-to-make-always-on-bottom-window
        else:
            if self._t.is_alive():
                self._t.stop()
            result = self.sendBehind(sb=False)
        if result == 0:
            _raiseWithLastError()

    def lowerWindow(self):
        """Lowers the window to the bottom so that it does not obscure any sibling windows.
        """
        result = ctypes.windll.user32.SetWindowPos(self._hWnd, HWND_BOTTOM, 0, 0, 0, 0,
                                                   win32con.SWP_NOSIZE | win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE)
        if result == 0:
            _raiseWithLastError()

    def raiseWindow(self):
        """Raises the window to top so that it is not obscured by any sibling windows.
        """
        result = ctypes.windll.user32.SetWindowPos(self._hWnd, HWND_TOP, 0, 0, 0, 0,
                                                   win32con.SWP_NOSIZE | win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE)
        if result == 0:
            _raiseWithLastError()

    def sendBehind(self, sb=True):
        """Sends the window to the very bottom, below all other windows, including desktop icons.
        It may also cause that the window does not accept focus nor keyboard/mouse events.

        Use sb=False to bring the window back from background

        WARNING: On GNOME it will obscure desktop icons... by the moment"""
        if sb:
            def getWorkerW():

                thelist = []

                def findit(hwnd, ctx):
                    p = win32gui.FindWindowEx(hwnd, None, "SHELLDLL_DefView", "")
                    if p != 0:
                        thelist.append(win32gui.FindWindowEx(None, hwnd, "WorkerW", ""))

                win32gui.EnumWindows(findit, None)
                return thelist

            # https://www.codeproject.com/Articles/856020/Draw-Behind-Desktop-Icons-in-Windows-plus
            progman = win32gui.FindWindow("Progman", None)
            win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, SMTO_NORMAL, 1000)
            workerw = getWorkerW()
            result = 0
            if workerw:
                result = win32gui.SetParent(self._hWnd, workerw[0])
        else:
            result = win32gui.SetParent(self._hWnd, self._parent)
            # Window raises, but completely transparent
            # Sometimes this works, but not always
            # result = result | win32gui.ShowWindow(self._hWnd, win32con.SW_SHOW)
            # win32gui.SetLayeredWindowAttributes(self._hWnd, win32api.RGB(255, 255, 255), 255, win32con.LWA_COLORKEY)
            # win32gui.UpdateWindow(self._hWnd)
            # Didn't find a better way to update window content by the moment (tried redraw(), update(), ...)
            result = result | win32gui.ShowWindow(self._hWnd, win32con.SW_MINIMIZE)
            result = result | win32gui.ShowWindow(self._hWnd, win32con.SW_RESTORE)

        if result == 0:
            _raiseWithLastError()
        return result

    @property
    def isMinimized(self):
        """Returns ``True`` if the window is currently minimized."""
        return ctypes.windll.user32.IsIconic(self._hWnd) != 0

    @property
    def isMaximized(self):
        """Returns ``True`` if the window is currently maximized."""
        return ctypes.windll.user32.IsZoomed(self._hWnd) != 0

    @property
    def isActive(self):
        """Returns ``True`` if the window is currently the active, foreground window."""
        return getActiveWindow() == self

    @property
    def title(self):
        """Returns the window title as a string."""
        textLenInCharacters = ctypes.windll.user32.GetWindowTextLengthW(self._hWnd)
        stringBuffer = ctypes.create_unicode_buffer(textLenInCharacters + 1) # +1 for the \0 at the end of the null-terminated string.
        ctypes.windll.user32.GetWindowTextW(self._hWnd, stringBuffer, textLenInCharacters + 1)

        # TODO it's ambiguous if an error happened or the title text is just empty. Look into this later.
        return stringBuffer.value

    @property
    def visible(self):
        """Return ``True`` if the window is currently visible."""
        return isWindowVisible(self._hWnd)

    isVisible = visible  # isVisible is an alias for the visible property.


class _sendBottom(threading.Thread):

    def __init__(self, hWnd, interval=0.5):
        threading.Thread.__init__(self)
        self._hWnd = hWnd
        self._interval = interval
        self._stop = threading.Event()

    def run(self):

        while not self._stop.is_set() and win32gui.IsWindow(self._hWnd):
            # TODO: Find a smart way (not a for) to get if this is necessary (window is not already at the bottom)
            # Window flickers a bit. All these parameters are intended to minimize it... with limited success
            win32gui.SetWindowPos(self._hWnd, win32con.HWND_BOTTOM, 0, 0, 0, 0,
                                  win32con.SWP_NOSENDCHANGING | win32con.SWP_NOOWNERZORDER | win32con.SWP_ASYNCWINDOWPOS | win32con.SWP_NOSIZE | win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE | win32con.SWP_NOREDRAW | win32con.SWP_NOCOPYBITS)
            self._stop.wait(self._interval)

    def stop(self):
        self._stop.set()


def cursor():
    """Returns the current xy coordinates of the mouse cursor as a two-integer
    tuple by calling the GetCursorPos() win32 function.

    Returns:
      (x, y) tuple of the current xy coordinates of the mouse cursor.
    """

    cursor = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor))
    return Point(x=cursor.x, y=cursor.y)


def resolution():
    """Returns the width and height of the screen as a two-integer tuple.

    Returns:
      (width, height) tuple of the screen size, in pixels.
    """
    return Size(width=ctypes.windll.user32.GetSystemMetrics(0), height=ctypes.windll.user32.GetSystemMetrics(1))


def displayWindowsUnderMouse(xOffset=0, yOffset=0):
    """This function is meant to be run from the command line. It will
    automatically display the location and RGB of the mouse cursor."""
    print('Press Ctrl-C to quit.')
    if xOffset != 0 or yOffset != 0:
        print('xOffset: %s yOffset: %s' % (xOffset, yOffset))
    try:
        prevWindows = None
        while True:
            x, y = cursor()
            positionStr = 'X: ' + str(x - xOffset).rjust(4) + ' Y: ' + str(y - yOffset).rjust(
                4) + '  (Press Ctrl-C to quit)'
            if prevWindows is not None:
                sys.stdout.write(positionStr)
                sys.stdout.write('\b' * len(positionStr))
            windows = getWindowsAt(x, y)
            if windows != prevWindows:
                print('\n')
                prevWindows = windows
                for win in windows:
                    name = win.title
                    eraser = '' if len(name) >= len(positionStr) else ' ' * (len(positionStr) - len(name))
                    sys.stdout.write((name or ("<No Name> ID: " + str(win._hWnd))) + eraser + '\n')
            sys.stdout.flush()
            time.sleep(0.3)
    except KeyboardInterrupt:
        sys.stdout.write('\n\n')
        sys.stdout.flush()


def main():
    """Run this script from command-line to get windows under mouse pointer"""
    print("PLATFORM:", sys.platform)
    print("SCREEN SIZE:", resolution())
    npw = getActiveWindow()
    print("ACTIVE WINDOW:", npw.title, "/", npw.box)
    print()
    displayWindowsUnderMouse(0, 0)


if __name__ == "__main__":
    main()
