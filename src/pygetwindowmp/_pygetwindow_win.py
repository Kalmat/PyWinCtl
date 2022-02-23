#!/usr/bin/python
# -*- coding: utf-8 -*-

import ctypes
import sys
import time
import threading
from typing import List

import win32con
import win32gui
import win32gui_struct

from pygetwindowmp import pointInRect, BaseWindow, Rect, Point, Size

# WARNING: Changes are not immediately applied, specially for hide/show (unmap/map)
#          You may set wait to True in case you need to effectively know if/when change has been applied.
WAIT_ATTEMPTS = 10
WAIT_DELAY = 0.025  # Will be progressively increased on every retry


def getActiveWindow():
    """Returns a Window object of the currently active (focused) Window."""
    hWnd = win32gui.GetForegroundWindow()
    if hWnd:
        return Win32Window(hWnd)
    else:
        return None


def getActiveWindowTitle() -> str:
    """Returns a string of the title text of the currently active (focused) Window."""
    hWnd = getActiveWindow()
    if hWnd:
        return hWnd.title
    else:
        return ""


def getWindowsAt(x: int, y: int):
    """Returns a list of Window objects whose windows contain the point ``(x, y)``.

    * ``x`` (int, optional): The x position of the window(s).
    * ``y`` (int, optional): The y position of the window(s)."""
    windowsAtXY = []
    for win in getAllWindows():
        if pointInRect(x, y, win.left, win.top, win.width, win.height):
            windowsAtXY.append(win)
    return windowsAtXY


def getWindowsWithTitle(title: str):
    """Returns a Window object list with the given name."""
    matches = []
    for win in getAllWindows():
        if win.title == title:
            matches.append(win)
    return matches


def getAllTitles() -> List[str]:
    """Returns a list of strings of window titles for all visible windows."""
    return [window.title for window in getAllWindows()]


def getAllWindows():
    """Returns a list of Window objects for all visible windows.
    """
    matches = []
    windowObjs = _findWindowHandles(onlyVisible=True)
    for win in windowObjs:
        if win32gui.IsWindowVisible(win):
            matches.append(Win32Window(win))
    return matches


def _findWindowHandles(parent: int = None, window_class: str = None, title: str = None, onlyVisible: bool = False) -> List[int]:
    # https://stackoverflow.com/questions/56973912/how-can-i-set-windows-10-desktop-background-with-smooth-transition
    # Fixed: original post returned duplicated handles when trying to retrieve all windows (no class nor title)

    def _make_filter(class_name: str, title: str, onlyVisible=False):

        def enum_windows(handle: int, h_list: list):
            if class_name and class_name not in win32gui.GetClassName(handle):
                return True  # continue enumeration
            if title and title not in win32gui.GetWindowText(handle):
                return True  # continue enumeration
            if not onlyVisible or (onlyVisible and win32gui.IsWindowVisible(handle)):
                h_list.append(handle)

        return enum_windows

    cb = _make_filter(window_class, title, onlyVisible)
    try:
        handle_list = []
        if parent:
            win32gui.EnumChildWindows(parent, cb, handle_list)
        else:
            win32gui.EnumWindows(cb, handle_list)
        return handle_list
    except:
        return []


class Win32Window(BaseWindow):
    def __init__(self, hWnd):
        super().__init__()
        self._hWnd = hWnd
        self._setupRectProperties()
        self._parent = win32gui.GetParent(self._hWnd)
        self._t = None
        self.menu = self._Menu(self)

    def _getWindowRect(self) -> Rect:
        x, y, r, b = win32gui.GetWindowRect(self._hWnd)
        return Rect(x, y, r, b)

    def __repr__(self):
        return '%s(hWnd=%s)' % (self.__class__.__name__, self._hWnd)

    def __eq__(self, other):
        return isinstance(other, Win32Window) and self._hWnd == other._hWnd

    def close(self) -> bool:
        """Closes this window. This may trigger "Are you sure you want to
        quit?" dialogs or other actions that prevent the window from
        actually closing. This is identical to clicking the X button on the
        window."""
        win32gui.PostMessage(self._hWnd, win32con.WM_CLOSE, 0, 0)
        return win32gui.IsWindow(self._hWnd)

    def minimize(self, wait: bool = False) -> bool:
        """Minimizes this window."""
        if not self.isMinimized:
            win32gui.ShowWindow(self._hWnd, win32con.SW_MINIMIZE)
            retries = 0
            while wait and retries < WAIT_ATTEMPTS and not self.isMinimized:
                retries += 1
                time.sleep(WAIT_DELAY * retries)
        return self.isMinimized

    def maximize(self, wait: bool = False) -> bool:
        """Maximizes this window."""
        if not self.isMaximized:
            win32gui.ShowWindow(self._hWnd, win32con.SW_MAXIMIZE)
            retries = 0
            while wait and retries < WAIT_ATTEMPTS and not self.isMaximized:
                retries += 1
                time.sleep(WAIT_DELAY * retries)
        return self.isMaximized

    def restore(self, wait: bool = False) -> bool:
        """If maximized or minimized, restores the window to it's normal size."""
        win32gui.ShowWindow(self._hWnd, win32con.SW_RESTORE)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and (self.isMaximized or self.isMinimized):
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self.isMaximized and not self.isMinimized
        
    def show(self, wait: bool = False) -> bool:
        """If hidden or showing, shows the window on screen and in title bar."""
        win32gui.ShowWindow(self._hWnd, win32con.SW_SHOW)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and not self.isVisible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.isVisible

    def hide(self, wait: bool = False) -> bool:
        """If hidden or showing, hides the window from screen and title bar."""
        win32gui.ShowWindow(self._hWnd, win32con.SW_HIDE)
        retries = 0
        while wait and retries < WAIT_ATTEMPTS and self.isVisible:
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return not self.isVisible

    def activate(self, wait: bool = False) -> bool:
        """Activate this window and make it the foreground (focused) window."""
        win32gui.SetForegroundWindow(self._hWnd)
        return self.isActive

    def resize(self, widthOffset: int, heightOffset: int, wait: bool = False) -> bool:
        """Resizes the window relative to its current size."""
        return self.resizeTo(self.width + widthOffset, self.height + heightOffset, wait)

    resizeRel = resize  # resizeRel is an alias for the resize() method.

    def resizeTo(self, newWidth: int, newHeight: int, wait: bool = False) -> bool:
        """Resizes the window to a new width and height."""
        result = win32gui.SetWindowPos(self._hWnd, win32con.HWND_TOP, self.left, self.top, newWidth, newHeight, 0)
        retries = 0
        while result != 0 and wait and retries < WAIT_ATTEMPTS and (self.width != newWidth or self.height != newHeight):
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.width == newWidth and self.height == newHeight

    def move(self, xOffset: int, yOffset: int, wait: bool = False) -> bool:
        """Moves the window relative to its current position."""
        return self.moveTo(self.left + xOffset, self.top + yOffset, wait)

    moveRel = move  # moveRel is an alias for the move() method.

    def moveTo(self, newLeft:int, newTop: int, wait: bool = False) -> bool:
        """Moves the window to new coordinates on the screen."""
        result = win32gui.SetWindowPos(self._hWnd, win32con.HWND_TOP, newLeft, newTop, self.width, self.height, 0)
        retries = 0
        while result != 0 and wait and retries < WAIT_ATTEMPTS and (self.left != newLeft or self.top != newTop):
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return self.left == newLeft and self.top == newTop

    def _moveResizeTo(self, newLeft: int, newTop: int, newWidth: int, newHeight: int) -> bool:
        result = win32gui.SetWindowPos(self._hWnd, win32con.HWND_TOP, newLeft, newTop, newWidth, newHeight, 0)
        retries = 0
        while result != 0 and retries < WAIT_ATTEMPTS and (self.left != newLeft or self.top != newTop):
            retries += 1
            time.sleep(WAIT_DELAY * retries)
        return newLeft == self.left and newTop == self.top and newWidth == self.width and newHeight == self.height

    def alwaysOnTop(self, aot: bool = True) -> bool:
        """Keeps window on top of all others.

        Use aot=False to deactivate always-on-top behavior
        """
        # https://stackoverflow.com/questions/25381589/pygame-set-window-on-top-without-changing-its-position/49482325 (kmaork)
        zorder = win32con.HWND_TOPMOST if aot else win32con.HWND_NOTOPMOST
        result = win32gui.SetWindowPos(self._hWnd, zorder, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        return result != 0

    def alwaysOnBottom(self, aob: bool = True) -> bool:
        """Keeps window below of all others, but on top of desktop icons and keeping all window properties

        Use aob=False to deactivate always-on-bottom behavior
        """

        ret = False
        if aob:
            result = win32gui.SetWindowPos(self._hWnd, win32con.HWND_BOTTOM, 0, 0, 0, 0,
                                  win32con.SWP_NOSENDCHANGING | win32con.SWP_NOOWNERZORDER | win32con.SWP_ASYNCWINDOWPOS | win32con.SWP_NOSIZE | win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE | win32con.SWP_NOREDRAW | win32con.SWP_NOCOPYBITS)
            if result != 0:
                # There is no HWND_TOPBOTTOM (similar to TOPMOST), so it won't keep window below all others as desired
                # May be catching WM_WINDOWPOSCHANGING event? Not sure if possible for a "foreign" window, and seems really complex
                # https://stackoverflow.com/questions/64529896/attach-keyboard-hook-to-specific-window
                ret = True
                if self._t is None:
                    self._t = _SendBottom(self._hWnd)
                    # Not sure about the best behavior: stop thread when program ends or keeping sending window below
                    self._t.setDaemon(True)
                if not self._t.is_alive():
                    self._t.start()
        else:
            if self._t.is_alive():
                self._t.kill()
            ret = self.sendBehind(sb=False)
        return ret

    def lowerWindow(self) -> bool:
        """Lowers the window to the bottom so that it does not obscure any sibling windows.
        """
        result = win32gui.SetWindowPos(self._hWnd, win32con.HWND_BOTTOM, 0, 0, 0, 0,
                                       win32con.SWP_NOSIZE | win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE)
        return result != 0

    def raiseWindow(self) -> bool:
        """Raises the window to top so that it is not obscured by any sibling windows.
        """
        result = win32gui.SetWindowPos(self._hWnd, win32con.HWND_TOP, 0, 0, 0, 0,
                                       win32con.SWP_NOSIZE | win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE)
        return result != 0

    def sendBehind(self, sb: bool = True) -> bool:
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
            win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)
            workerw = getWorkerW()
            result = 0
            if workerw:
                result = win32gui.SetParent(self._hWnd, workerw[0])
        else:
            result = win32gui.SetParent(self._hWnd, self._parent)
            # Window raises, but completely transparent
            # Sometimes this fixes it, but not always
            # result = result | win32gui.ShowWindow(self._hWnd, win32con.SW_SHOW)
            # win32gui.SetLayeredWindowAttributes(self._hWnd, win32api.RGB(255, 255, 255), 255, win32con.LWA_COLORKEY)
            # win32gui.UpdateWindow(self._hWnd)
            # Didn't find a better way to update window content by the moment (also tried redraw(), update(), ...)
            result = result | win32gui.ShowWindow(self._hWnd, win32con.SW_MINIMIZE)
            result = result | win32gui.ShowWindow(self._hWnd, win32con.SW_RESTORE)
        return result != 0

    @property
    def isMinimized(self) -> bool:
        """Returns ``True`` if the window is currently minimized."""
        return win32gui.IsIconic(self._hWnd) != 0

    @property
    def isMaximized(self) -> bool:
        """Returns ``True`` if the window is currently maximized."""
        state = win32gui.GetWindowPlacement(self._hWnd)
        return state[1] == win32con.SW_SHOWMAXIMIZED

    @property
    def isActive(self) -> bool:
        """Returns ``True`` if the window is currently the active, foreground window."""
        return win32gui.GetForegroundWindow() == self._hWnd

    @property
    def title(self) -> str:
        """Returns the window title as a string."""
        name = win32gui.GetWindowText(self._hWnd)
        if isinstance(name, bytes):
            name = name.decode()
        return name

    @property
    def visible(self) -> bool:
        """Returns ``True`` if the window is currently visible."""
        return win32gui.IsWindowVisible(self._hWnd)

    isVisible = visible  # isVisible is an alias for the visible property.

    class _Menu:

        def __init__(self, parent: BaseWindow):
            self._parent = parent
            self._hWnd = parent._hWnd
            self._hMenu = win32gui.GetMenu(self._hWnd)
            self._menuStructure = {}
            self._sep = "|&|"

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

            def findit(parent: int, level: str = "", parentRect: Rect = None) -> None:

                option = self._menuStructure
                if level:
                    for section in level.split(self._sep)[1:]:
                        option = option[section]

                for i in range(win32gui.GetMenuItemCount(parent)):
                    item_info = self._getMenuItemInfo(hSubMenu=parent, itemPos=i)
                    text = item_info.text.split("\t")
                    title = (text[0].replace("&", "")) or "separator"
                    shortcut = "" if len(text) < 2 else text[1]
                    rect = self._getMenuItemRect(hSubMenu=parent, itemPos=i, relative=True, parentRect=parentRect)
                    option[title] = {"parent": parent, "hSubMenu": item_info.hSubMenu, "wID": item_info.wID,
                                     "shortcut": shortcut, "rect": rect, "entries": {}}
                    if addItemInfo:
                        option[title]["item_info"] = item_info
                    findit(item_info.hSubMenu, level + self._sep + title + self._sep + "entries", rect)

            if self._hMenu:
                findit(self._hMenu)
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
            itemID = 0
            if self._hMenu:
                if wID:
                    itemID = wID
                elif itemPath:
                    if not self._menuStructure:
                        self.getMenu()
                    option = self._menuStructure
                    for item in itemPath[:-1]:
                        if item in option.keys() and "entries" in option[item].keys():
                            option = option[item]["entries"]
                        else:
                            option = {}
                            break

                    if option and itemPath[-1] in option.keys() and "wID" in option[itemPath[-1]].keys():
                        itemID = option[itemPath[-1]]["wID"]

                if itemID:
                    win32gui.PostMessage(self._hWnd, win32con.WM_COMMAND, itemID, 0)
                    found = True

            return found

        def getMenuInfo(self, hSubMenu: int = 0) -> win32gui_struct.UnpackMENUINFO:
            """Returns the MENUINFO struct of the given sub-menu or main menu if none given

            Args:
            ----
                ''hSubMenu'' is the id of the sub-menu entry (as returned by getMenu() method)
            """
            if not hSubMenu:
                hSubMenu = self._hMenu

            menu_info = None
            if hSubMenu:
                buf = win32gui_struct.EmptyMENUINFO()
                win32gui.GetMenuInfo(self._hMenu, buf)
                menu_info = win32gui_struct.UnpackMENUINFO(buf)
            return menu_info

        def getMenuItemCount(self, hSubMenu: int = 0) -> int:
            """Returns the number of items within a menu (main menu if no sub-menu given)

            Args:
            ----
                ''hSubMenu'' is the id of the sub-menu entry (as returned by getMenu() method)
            """
            if not hSubMenu:
                hSubMenu = self._hMenu
            return win32gui.GetMenuItemCount(hSubMenu)

        def getMenuItemInfo(self, hSubMenu: int, wID: int) -> win32gui_struct.UnpackMENUITEMINFO:
            """Returns the ITEMINFO struct for the given menu item

            Args:
            ----
                ''hSubMenu'' is the id of the parent sub-menu entry (as returned by getMenu() method)

                ''wID'' is the item ID within menu struct (as returned by getMenu() method)
            """
            item_info = None
            if self._hMenu:
                buf, extras = win32gui_struct.EmptyMENUITEMINFO()
                win32gui.GetMenuItemInfo(hSubMenu, wID, False, buf)
                item_info = win32gui_struct.UnpackMENUITEMINFO(buf)
            return item_info

        def _getMenuItemInfo(self, hSubMenu: int, itemPos: int) -> win32gui_struct.UnpackMENUITEMINFO:
            """Returns the ITEMINFO struct for the given menu item

            Args:
            ----
                ''hSubMenu'' is the id of the parent sub-menu entry (as returned by getMenu() method)

                ''wID'' is the item ID within menu struct (as returned by getMenu() method)
            """
            item_info = None
            if self._hMenu:
                buf, extras = win32gui_struct.EmptyMENUITEMINFO()
                win32gui.GetMenuItemInfo(hSubMenu, itemPos, True, buf)
                item_info = win32gui_struct.UnpackMENUITEMINFO(buf)
            return item_info

        def getMenuItemRect(self, hSubMenu: int, itemPos: int) -> Rect:
            """Returns the Rect struct of the Menu option

            Args:
            ----
                ''hSubMenu'' is the id of the parent sub-menu entry (as returned by getMenu() method)

                ''itemPos'' is the position (zero-based ordinal) of the item within the sub-menu
            """
            ret = None
            if self._hMenu and 0 <= itemPos < self.getMenuItemCount(hSubMenu=hSubMenu):
                [result, (x, y, r, b)] = win32gui.GetMenuItemRect(self._hWnd, hSubMenu, itemPos)
                if result != 0:
                    ret = Rect(x, y, r, b)
            return ret

        def _getMenuItemRect(self, hSubMenu: int, itemPos: int, parentRect: Rect = None, relative: bool = False) -> Rect:
            ret = None
            if self._hMenu and hSubMenu and 0 <= itemPos < self.getMenuItemCount(hSubMenu=hSubMenu):
                [result, (x, y, r, b)] = win32gui.GetMenuItemRect(self._hWnd, hSubMenu, itemPos)
                if result != 0:
                    if relative:
                        x = abs(abs(x) - abs(self._parent.left))
                        y = abs(abs(y) - abs(self._parent.top))
                        r = abs(abs(r) - abs(self._parent.left))
                        b = abs(abs(b) - abs(self._parent.top))
                    if parentRect:
                        x = parentRect.left
                    ret = Rect(x, y, r, b)
            return ret


class _SendBottom(threading.Thread):

    def __init__(self, hWnd, interval=0.5):
        threading.Thread.__init__(self)
        self._hWnd = hWnd
        self._interval = interval
        self._kill = threading.Event()

    def _isLast(self):
        # This avoids flickering and CPU consumption. Not very smart, but no other option found... by the moment
        h = win32gui.GetWindow(self._hWnd, win32con.GW_HWNDLAST)
        last = True
        while h != 0 and h != self._hWnd:
            h = win32gui.GetWindow(h, win32con.GW_HWNDPREV)
            # not sure if this always guarantees these other windows are "system" windows (not user windows)
            if h != self._hWnd and win32gui.IsWindowVisible(h) and win32gui.GetClassName(h) not in ("WorkerW", "Progman"):
                last = False
                break
        return last

    def run(self):
        while not self._kill.is_set() and win32gui.IsWindow(self._hWnd):
            if not self._isLast():
                win32gui.SetWindowPos(self._hWnd, win32con.HWND_BOTTOM, 0, 0, 0, 0,
                                      win32con.SWP_NOSENDCHANGING | win32con.SWP_NOOWNERZORDER | win32con.SWP_ASYNCWINDOWPOS | win32con.SWP_NOSIZE | win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE | win32con.SWP_NOREDRAW | win32con.SWP_NOCOPYBITS)
            self._kill.wait(self._interval)

    def kill(self):
        self._kill.set()


def cursor():
    """Returns the current xy coordinates of the mouse cursor as a two-integer
    tuple by calling the GetCursorPos() win32 function.

    Returns:
      (x, y) tuple of the current xy coordinates of the mouse cursor.
    """

    cursor = win32gui.GetCursorPos()
    return Point(x=cursor[0], y=cursor[1])


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
