#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import threading
import time
from typing import Union, List, Any, Iterable, TypedDict, Optional, Tuple, cast, Callable

import Xlib.display
import Xlib.protocol
import Xlib.X
import Xlib.Xutil
import Xlib.ext
from Xlib.protocol.rq import Struct
from Xlib.xobject.drawable import Window as XWindow

defaultDisplay = Xlib.display.Display()
defaultScreen = defaultDisplay.screen()
defaultRoot = defaultScreen.root


class _ScreenInfo(TypedDict):
    screen: Struct
    root: XWindow
    is_default: bool


class _ScreenSeq(TypedDict):
    scrSeq: Optional[_ScreenInfo]


class _DisplayInfo(TypedDict):
    is_default: bool
    screens: Optional[List[_ScreenSeq]]


class _DisplaySeq(TypedDict):
    name: Optional[_DisplayInfo]


def getAllDisplaysInfo() -> _DisplaySeq:
    """
    Gets relevant information on all present displays, including its screens and roots

    Returned dictionary has the following structure:

    "name": display name (use Xlib.display.Display(name) to get a connection)
        "is_default": ''True'' if it's the default display, ''False'' otherwise
        "screens": List of sub-dict containing all screens owned by the display
            "scrSeq": number of the screen (as per display.screen(M))
            "screen": Struct containing all screen info
            "root": root window (Xlib Window) which belongs to the screen
            "is_default": ''True'' if it's the default screen/root, ''False'' otherwise

    :return: dict with all displays, screens and roots info
    """
    displays: List[str] = os.listdir("/tmp/.X11-unix")
    dspInfo: _DisplaySeq = cast(_DisplaySeq, {})
    for i, d in enumerate(displays):
        if d.startswith("X"):
            name: str = ":" + d[1:]
            display: Xlib.display.Display = Xlib.display.Display(name)
            screens: List[_ScreenSeq] = []
            for s in range(display.screen_count()):
                try:
                    screen: Struct = display.screen(s)
                    screenInfo: _ScreenInfo = {
                        "screen": screen,
                        "root": screen.root,
                        "is_default": (screen.root.id == defaultRoot.id)
                    }
                    scrSeq = str(s)
                    screenSeq: _ScreenSeq = cast(_ScreenSeq, {scrSeq: screenInfo})
                    screens.append(screenSeq)
                except:
                    pass
            displayInfo: _DisplayInfo = {
                "is_default": (display.get_display_name() == defaultDisplay.get_display_name()),
                "screens": screens
            }
            display.close()
            # How to use variables as keys to add new items???
            # https://github.com/python/mypy/issues/7178
            dspInfo[name] = displayInfo  # type: ignore[literal-required]
    return dspInfo


def getDisplayFromWindow(winId: int) -> Tuple[Xlib.display.Display, Struct, XWindow]:
    """
    Gets display connection, screen and root window from a given window id to which it belongs

    :param winId: id of the window
    :return: tuple containing display connection, screen struct and root window
    """
    displays: List[str] = os.listdir("/tmp/.X11-unix")
    check = False
    if len(displays) > 1:
        check = True
    elif len(displays) == 1:
        name: str = ":" + displays[0][1:]
        display: Xlib.display.Display = Xlib.display.Display(name)
        if display.screen_count() > 1:
            display.close()
            check = True
    if check:
        for i, d in enumerate(displays):
            if d.startswith("X"):
                name = ":" + d[1:]
                display = Xlib.display.Display(name)
                atom: int = display.get_atom(Props.Root.CLIENT_LIST)
                for s in range(display.screen_count()):
                    try:
                        scr: Struct = display.screen(s)
                        r: XWindow = scr.root
                        ret: Union[Xlib.protocol.request.GetProperty, None] = r.get_full_property(atom, Xlib.X.AnyPropertyType)
                        windows = []
                        if ret and hasattr(ret, "value"):
                            windows = ret.value
                        for w in windows:
                            if w == winId:
                                return display, scr, r
                    except:
                        pass
                display.close()
    return defaultDisplay, defaultScreen, defaultRoot


def getDisplayFromRoot(rootId: int) -> Tuple[Xlib.display.Display, Struct, XWindow]:
    """
    Gets display connection, screen and root window from a given root id to which it belongs.
    For default root, this is not needed. Use defaultDisplay, defaultScreen and defaultRoot instead.

    :param rootId: id of the target root
    :return: tuple containing display connection, screen struct and root window
    """
    displays: List[str] = os.listdir("/tmp/.X11-unix")
    check = False
    if len(displays) > 1:
        check = True
    elif len(displays) == 1:
        name: str = ":" + displays[0][1:]
        display: Xlib.display.Display = Xlib.display.Display(name)
        if display.screen_count() > 1:
            display.close()
            check = True
    if check:
        for i, d in enumerate(displays):
            if d.startswith("X"):
                name = ":" + d[1:]
                display = Xlib.display.Display(name)
                for s in range(display.screen_count()):
                    try:
                        scr: Struct = display.screen(s)
                        r: XWindow = scr.root
                        if rootId == r.id:
                            return display, scr, r
                    except:
                        pass
                display.close()
    return defaultDisplay, defaultScreen, defaultRoot


class WmProtocols:
    # Is this necessary/interesting?

    class Requests:
        PING = "_NET_WM_PING"
        SYNC = "_NET_WM_SYNC_REQUEST"

    def ping(self, winId):
        pass

    def sync(self, winId):
        pass


class Props:

    class Root:

        SUPPORTED = "_NET_SUPPORTED"
        CLIENT_LIST = "_NET_CLIENT_LIST"
        CLIENT_LIST_STACKING = "_NET_CLIENT_LIST_STACKING"
        NUMBER_OF_DESKTOPS = "_NET_NUMBER_OF_DESKTOPS"
        DESKTOP_GEOMETRY = "_NET_DESKTOP_GEOMETRY"
        DESKTOP_VIEWPORT = "_NET_DESKTOP_VIEWPORT"
        CURRENT_DESKTOP = "_NET_CURRENT_DESKTOP"
        DESKTOP_NAMES = "_NET_DESKTOP_NAMES"
        ACTIVE = "_NET_ACTIVE_WINDOW"
        WORKAREA = "_NET_WORKAREA"
        SUPPORTING_WM_CHECK = "_NET_SUPPORTING_WM_CHECK"
        VIRTUAL_ROOTS = "_NET_VIRTUAL_ROOTS"
        SHOWING_DESKTOP = "_NET_SHOWING_DESKTOP"

        DESKTOP_LAYOUT = "_NET_DESKTOP_LAYOUT"
        class DesktopLayout:
            ORIENTATION_HORZ = 0
            ORIENTATION_VERT = 1
            TOPLEFT = 0
            TOPRIGHT = 1
            BOTTOMRIGHT = 2
            BOTTOMLEFT = 3

        # Additional Root properties (always related to a specific window)
        CLOSE = "_NET_CLOSE_WINDOW"
        MOVERESIZE = "_NET_MOVERESIZE_WINDOW"
        WM_MOVERESIZE = "_NET_WM_MOVERESIZE"
        RESTACK = "_NET_RESTACK_WINDOW"
        REQ_FRAME_EXTENTS = "_NET_REQUEST_FRAME_EXTENTS"

    class Window:

        NAME = "_NET_WM_NAME"
        VISIBLE_NAME = "_NET_WM_VISIBLE_NAME"
        ICON_NAME = "_NET_WM_ICON_NAME"
        VISIBLE_ICON_NAME = "_NET_WM_VISIBLE_ICON_NAME"
        DESKTOP = "_NET_WM_DESKTOP"

        WM_WINDOW_TYPE = "_NET_WM_WINDOW_TYPE"
        class WindowType:
            DESKTOP = "_NET_WM_WINDOW_TYPE_DESKTOP"
            DOCK = "_NET_WM_WINDOW_TYPE_DOCK"
            TOOLBAR = "_NET_WM_WINDOW_TYPE_TOOLBAR"
            MENU = "_NET_WM_WINDOW_TYPE_MENU"
            UTILITY = "_NET_WM_WINDOW_TYPE_UTILITY"
            SPLASH = "_NET_WM_WINDOW_TYPE_SPLASH"
            DIALOG = "_NET_WM_WINDOW_TYPE_DIALOG"
            NORMAL = "_NET_WM_WINDOW_TYPE_NORMAL"

        CHANGE_STATE = "WM_CHANGE_STATE"
        WM_STATE = "_NET_WM_STATE"
        class State:
            MODAL = "_NET_WM_STATE_MODAL"
            STICKY = "_NET_WM_STATE_STICKY"
            MAXIMIZED_VERT = "_NET_WM_STATE_MAXIMIZED_VERT"
            MAXIMIZED_HORZ = "_NET_WM_STATE_MAXIMIZED_HORZ"
            SHADED = "_NET_WM_STATE_SHADED"
            SKIP_TASKBAR = "_NET_WM_STATE_SKIP_TASKBAR"
            SKIP_PAGER = "_NET_WM_STATE_SKIP_PAGER"
            HIDDEN = "_NET_WM_STATE_HIDDEN"
            FULLSCREEN = "_NET_WM_STATE_FULLSCREEN"
            ABOVE = "_NET_WM_STATE_ABOVE"
            BELOW = "_NET_WM_STATE_BELOW"
            DEMANDS_ATTENTION = "_NET_WM_STATE_DEMANDS_ATTENTION"
            FOCUSED = "_NET_WM_STATE_FOCUSED"

            class Action:
                REMOVE = 0
                ADD = 1
                TOGGLE = 2

        ALLOWED_ACTIONS = "_NET_WM_ALLOWED_ACTIONS"
        STRUT = "_NET_WM_STRUT"
        STRUT_PARTIAL = "_NET_WM_STRUT_PARTIAL"
        ICON_GEOMETRY = "_NET_WM_ICON_GEOMETRY"
        ICON = "_NET_WM_ICON"
        PID = "_NET_WM_PID"
        HANDLED_ICONS = "_NET_WM_HANDLED_ICONS"
        USER_TIME = "_NET_WM_USER_TIME"
        FRAME_EXTENTS = "_NET_FRAME_EXTENTS"

        # These are Root properties, but always related to a specific window
        ACTIVE = "_NET_ACTIVE_WINDOW"
        CLOSE = "_NET_CLOSE_WINDOW"

        MOVERESIZE = "_NET_MOVERESIZE_WINDOW"
        class MoveResize:
            SIZE_TOPLEFT = 0
            SIZE_TOP = 1
            SIZE_TOPRIGHT = 2
            SIZE_RIGHT = 3
            SIZE_BOTTOMRIGHT = 4
            SIZE_BOTTOM = 5
            SIZE_BOTTOMLEFT = 6
            SIZE_LEFT = 7
            MOVE = 8            # movement only
            SIZE_KEYBOARD = 9   # size via keyboard
            MOVE_KEYBOARD = 10  # move via keyboard

        WM_MOVERESIZE = "_NET_WM_MOVERESIZE"
        RESTACK = "_NET_RESTACK_WINDOW"
        REQ_FRAME_EXTENTS = "_NET_REQUEST_FRAME_EXTENTS"

    class Format:
        STR = 8
        INT = 32

    class Mode:
        REPLACE = Xlib.X.PropModeReplace
        APPEND = Xlib.X.PropModeAppend
        PREPEND = Xlib.X.PropModePrepend


class Structs:
    """
    Will this be really necessary?

    Leaving these as examples...
    """

    class GetProperty(TypedDict):
        # <class 'Xlib.protocol.request.GetProperty'> serial = 105, data = {'sequence_number': 105, 'property_type': 33, 'bytes_after': 0, 'value': (32, array('I', [44040202]))}, error = None>
        # how to parse this: (32, array('I', [44040202])). It contains format, type and value itself... useful!
        sequence_number: int
        property_type: int
        bytes_after: int
        value: Union[List[int], List[str], int, str]

    class WmHints(TypedDict):
        # {'flags': 103, 'input': 1, 'initial_state': 1, 'icon_pixmap': <Pixmap 0x02a22304>, 'icon_window': <Window 0x00000000>, 'icon_x': 0, 'icon_y': 0, 'icon_mask': <Pixmap 0x02a2230b>, 'window_group': <Window 0x02a00001>}
        flags: int
        input: int
        initial_state: int
        icon_pixmap: Xlib.xobject.drawable.Pixmap
        icon_window: Xlib.xobject.drawable.Window
        icon_x: int
        icon_y: int
        icon_mask: Xlib.xobject.drawable.Pixmap
        window_group: Xlib.xobject.drawable.Window


class RootWindow:
    """
    Base class to access root features.

    To get a RootWindow object it's necessary to pass the target root id. This can be achieved in several ways:

    - You already have a root, so pass root.id param

    - You have some criteria to select a root, so use the convenience function getAllDisplaysInfo(), to look
      for all roots and select the desired one

    - You have a target window, so use the convenience function getDisplayFromWindow(window.id), so you will
      retrieve the associated display connection and root window

    - Instantiate this class with no param (None), so it will retrieve the default display and root

    Apart from given methods, you can access these other values to be used with python-xlib:

    - display: XDisplay connection

    - screen: screen Struct

    - root: root X Window object

    - id: root window id
    """

    def __init__(self, root: Union[XWindow, None] = None):

        if root:
            self.display, self.screen, self.root = getDisplayFromRoot(root.id)
        else:
            self.display = defaultDisplay
            self.screen = defaultScreen
            self.root = defaultRoot
        self.id: int = self.root.id

    def getProperty(self, prop: Union[str, int]) -> Union[Xlib.protocol.request.GetProperty, None]:
        """
        Retrieves given property from root

        :param prop: Property to query (int or str format)
        :return: List of int, List of str, str or None (nothing obtained)
        """
        return _getProperty(self.display, self.root, prop)

    def setProperty(self, prop: Union[str, int], data: Union[List[int], str]):
        """
        Sets the given property for root

        :param prop: property to set in int or str format. The property can be either an existing property, known and
         managed by the Window Manager, o completely  new, non-previously existing property. In this last case, the
         Wndow Manager will store the property but will also ignore it. The application is therefore responsible to manage it.
        :param data: Data related to given property, in List of int or str (like in name) format
        """
        _sendMessage(self.display, self.root, self.root.id, prop, data)

    def sendMessage(self, winId: int, prop: Union[str, int], data: Union[List[int], str]):
        """
        Sends a ClientMessage event to given window

        :param winId: id of the target window
        :param prop: property/atom of the event in int or str format
        :param data: Data related to the event. It can be str (format is 8) or a list of up to 5 integers (format is 32)
        """
        _sendMessage(self.display, self.root, winId, prop, data)

    def getSupported(self, text=False) -> Union[List[int], List[str], None]:
        """
        Returns the list of supported hints by the Window Manager.

        This property MUST be set by the Window Manager to indicate which hints it supports. For example:
        considering _NET_WM_STATE both this atom and all supported states e.g. _NET_WM_STATE_MODAL,
        _NET_WM_STATE_STICKY, would be listed. This assumes that backwards incompatible changes will not be made
        to the hints (without being renamed).

        :param text: if ''True'' the values will be returned as strings, or as integers if ''False''
        :return: supported hints as a list of strings / integers
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.SUPPORTED)
        return _getPropertyValue(self.display, ret, text)

    def getClientList(self) -> Union[List[int], None]:
        """
        Returns the list of XWindows currently opened and managed by the Window Manager, ordered older-to-newer.

        These arrays contain all X Windows managed by the Window Manager. _NET_CLIENT_LIST has initial mapping order,
        starting with the oldest window. These properties SHOULD be set and updated by the Window Manager.

        :return: list of integers (XWindows id's)
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.CLIENT_LIST)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getClientListStacking(self) -> Union[List[int], None]:
        """
        Returns the list of XWindows currently opened and managed by the Window Manager, ordered in bottom-to-top.

        These arrays contain all X Windows managed by the Window Manager. _NET_CLIENT_LIST_STACKING has
        bottom-to-top stacking order. These properties SHOULD be set and updated by the Window Manager.

        :return: list of integers (XWindows id's)
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.CLIENT_LIST_STACKING)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], ret)
        return res

    def getNumberOfDesktops(self) -> Union[int, None]:
        """
        This property SHOULD be set and updated by the Window Manager to indicate the number of virtual desktops.

        :return: number of desktops in int format or None
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.NUMBER_OF_DESKTOPS)
        res = _getPropertyValue(self.display, ret)
        if res and isinstance(res[0], int):
            return res[0]
        return None

    def setNumberOfDesktops(self, number: int):
        """
        This property SHOULD be set and updated by the Window Manager to indicate the number of virtual desktops.

        A Pager can request a change in the number of desktops by sending a _NET_NUMBER_OF_DESKTOPS message to the
        root window.

        The Window Manager is free to honor or reject this request. If the request is honored _NET_NUMBER_OF_DESKTOPS
        MUST be set to the new number of desktops, _NET_VIRTUAL_ROOTS MUST be set to store the new number of desktop
        virtual root window IDs and _NET_DESKTOP_VIEWPORT and _NET_WORKAREA must also be changed accordingly.
        The _NET_DESKTOP_NAMES property MAY remain unchanged.

        If the number of desktops is shrinking and _NET_CURRENT_DESKTOP is out of the new range of available desktops,
        then this MUST be set to the last available desktop from the new set. Clients that are still present on
        desktops that are out of the new range MUST be moved to the very last desktop from the new set. For these
         _NET_WM_DESKTOP MUST be updated.

        :param number: desired number of desktops to be set by Window Manager
        """
        self.setProperty(Props.Root.NUMBER_OF_DESKTOPS, [number])

    def getDesktopGeometry(self) -> Union[List[int], None]:
        """
        Array of two cardinals that defines the common size of all desktops (this is equal to the screen size if the
        Window Manager doesn't support large desktops, otherwise it's equal to the virtual size of the desktop).
        This property SHOULD be set by the Window Manager.

        :return: tuple of integers (width, height) or None if it couldn't be retrieved
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.DESKTOP_GEOMETRY)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], res)
        return res

    def setDesktopGeometry(self, newWidth, newHeight):
        """
        Array of two cardinals that defines the common size of all desktops (this is equal to the screen size if the
        Window Manager doesn't support large desktops, otherwise it's equal to the virtual size of the desktop).
        This property SHOULD be set by the Window Manager.

        A Pager can request a change in the desktop geometry by sending a _NET_DESKTOP_GEOMETRY client message
        to the root window
        The Window Manager MAY choose to ignore this message, in which case _NET_DESKTOP_GEOMETRY property will
        remain unchanged.

        :param newWidth: value for the new target desktop width
        :param newHeight: value for the new target desktop height
        """
        self.setProperty(Props.Root.DESKTOP_GEOMETRY, [newWidth, newHeight])

    def getDesktopViewport(self) -> Union[List[Tuple[int, int]], None]:
        """
        Array of pairs of cardinals that define the top left corner of each desktop's viewport.
        For Window Managers that don't support large desktops, this MUST always be set to (0,0).

        :return: list of int tuples or None if the value couldn't be retrieved
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.DESKTOP_VIEWPORT)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            result = []
            for r in res:
                item: Tuple[int, int] = cast(Tuple[int, int], r)
                result.append(item)
        else:
            result = None
        return result

    def setDesktopViewport(self, newWidth, newHeight):
        """
        Array of pairs of cardinals that define the top left corner of each desktop's viewport.
        For Window Managers that don't support large desktops, this MUST always be set to (0,0).

        A Pager can request to change the viewport for the current desktop by sending a _NET_DESKTOP_VIEWPORT
        client message to the root window.
        The Window Manager MAY choose to ignore this message, in which case _NET_DESKTOP_VIEWPORT property will remain unchanged.
        """
        self.setProperty(Props.Root.DESKTOP_VIEWPORT, [newWidth, newHeight])

    def getCurrentDesktop(self) -> Union[int, None]:
        """
        The index of the current desktop. This is always an integer between 0 and _NET_NUMBER_OF_DESKTOPS - 1.
        This MUST be set and updated by the Window Manager. If a Pager wants to switch to another virtual desktop,
        it MUST send a _NET_CURRENT_DESKTOP client message to the root window

        :return: index of current desktop in int format or None if couldn't be retrieved
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.CURRENT_DESKTOP)
        res = _getPropertyValue(self.display, ret)
        if res and isinstance(res[0], int):
            return res[0]
        return None

    def setCurrentDesktop(self, newDesktop: int):
        """
        Move the window to the target desktop. The index of the current desktop is always an integer between 0 and
        _NET_NUMBER_OF_DESKTOPS - 1. This MUST be set and updated by the Window Manager. If a Pager wants to switch
        to another virtual desktop, it MUST send a _NET_CURRENT_DESKTOP client message to the root window

        :param newDesktop: Index of the target desktop
        """
        desks = self.getNumberOfDesktops()
        if desks and newDesktop < desks and newDesktop != self.getCurrentDesktop():
            self.setProperty(Props.Root.CURRENT_DESKTOP, [newDesktop, Xlib.X.CurrentTime])

    def getDesktopNames(self) -> Union[List[str], None]:
        """
        The names of all virtual desktops. This is a list of NULL-terminated strings in UTF-8 encoding [UTF8].
        This property MAY be changed by a Pager or the Window Manager at any time.

        Note: The number of names could be different from _NET_NUMBER_OF_DESKTOPS. If it is less than
        _NET_NUMBER_OF_DESKTOPS, then the desktops with high numbers are unnamed. If it is larger than
         _NET_NUMBER_OF_DESKTOPS, then the excess names outside of the _NET_NUMBER_OF_DESKTOPS are considered
         to be reserved in case the number of desktops is increased.

        Rationale: The name is not a necessary attribute of a virtual desktop. Thus the availability or
        unavailability of names has no impact on virtual desktop functionality. Since names are set by users
        and users are likely to preset names for a fixed number of desktops, it doesn't make sense to shrink
        or grow this list when the number of available desktops changes.

        :return: list of desktop names in str format
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.DESKTOP_NAMES)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[str], res)
        return res

    def getActiveWindow(self) -> Union[int, None]:
        """
        The window ID of the currently active window or None if no window has the focus. This is a read-only
        property set by the Window Manager. If a Client wants to activate another window, it MUST send a
        _NET_ACTIVE_WINDOW client message to the root window:

        :return: window id or None
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.ACTIVE)
        res = _getPropertyValue(self.display, ret)
        if res and isinstance(res[0], int):
            return res[0]
        return None

    def getWorkArea(self) -> Union[List[int], None]:
        """
        This property MUST be set by the Window Manager upon calculating the work area for each desktop.
        Contains a geometry for each desktop. These geometries are specified relative to the viewport on each
        desktop and specify an area that is completely contained within the viewport. Work area SHOULD be used
        by desktop applications to place desktop icons appropriately.

        The Window Manager SHOULD calculate this space by taking the current page minus space occupied by dock
        and panel windows, as indicated by the _NET_WM_STRUT or _NET_WM_STRUT_PARTIAL properties set on client windows.

        :return: tuple containing workarea coordinates (x, y, width, height)
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.WORKAREA)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getSupportingWMCheck(self) -> Union[List[int], None]:
        """
        The Window Manager MUST set this property on the root window to be the ID of a child window created by himself,
        to indicate that a compliant window manager is active. The child window MUST also have the
        _NET_SUPPORTING_WM_CHECK property set to the ID of the child window. The child window MUST also have the
        _NET_WM_NAME property set to the name of the Window Manager.

        Rationale: The child window is used to distinguish an active Window Manager from a stale
        _NET_SUPPORTING_WM_CHECK property that happens to point to another window. If the _NET_SUPPORTING_WM_CHECK
        window on the client window is missing or not properly set, clients SHOULD assume that no conforming
        Window Manager is present.

        :return: ''True'' if compliant Window Manager is active or None if it couldn't be retrieved
        """
        # Not sure what this property is intended to return. In my system it returns None!
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.SUPPORTING_WM_CHECK)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getVirtualRoots(self) -> Union[List[int], None]:
        """
        To implement virtual desktops, some Window Managers reparent client windows to a child of the root window.
        Window Managers using this technique MUST set this property to a list of IDs for windows that are acting
        as virtual root windows. This property allows background setting programs to work with virtual roots and
        allows clients to figure out the window manager frame windows of their windows.

        :return: List of virtual roots id's as integers
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.VIRTUAL_ROOTS)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getDesktopLayout(self) -> Union[List[int], None]:
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.DESKTOP_LAYOUT)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], res)
        return res

    def setDesktopLayout(self, orientation, columns, rows, starting_corner):
        """
        Values (as per Props.RootWindow.DesktopLayout):
          _NET_WM_ORIENTATION_HORZ 0
          _NET_WM_ORIENTATION_VERT 1

          _NET_WM_TOPLEFT     0
          _NET_WM_TOPRIGHT    1
          _NET_WM_BOTTOMRIGHT 2
          _NET_WM_BOTTOMLEFT  3

        This property is set by a Pager, not by the Window Manager. When setting this property, the Pager must
        own a manager selection (as defined in the ICCCM 2.8). The manager selection is called _NET_DESKTOP_LAYOUT_Sn
        where n is the screen number. The purpose of this property is to allow the Window Manager to know the desktop
        layout displayed by the Pager.

        _NET_DESKTOP_LAYOUT describes the layout of virtual desktops relative to each other. More specifically,
        it describes the layout used by the owner of the manager selection. The Window Manager may use this layout
        information or may choose to ignore it. The property contains four values: the Pager orientation, the number
        of desktops in the X direction, the number in the Y direction, and the starting corner of the layout, i.e.
        the corner containing the first desktop.

        Note: In order to inter-operate with Pagers implementing an earlier draft of this document, Window Managers
        should accept a _NET_DESKTOP_LAYOUT property of length 3 and use _NET_WM_TOPLEFT as the starting corner in
        this case.

        The virtual desktops are arranged in a rectangle with rows rows and columns columns. If rows times columns
        does not match the total number of desktops as specified by _NET_NUMBER_OF_DESKTOPS, the highest-numbered
        workspaces are assumed to be nonexistent. Either rows or columns (but not both) may be specified as 0 in
        which case its actual value will be derived from _NET_NUMBER_OF_DESKTOPS.

        When the orientation is _NET_WM_ORIENTATION_HORZ the desktops are laid out in rows, with the first desktop
        in the specified starting corner. So a layout with four columns and three rows starting in the _NET_WM_TOPLEFT
        corner looks like this:

         +--+--+--+--+
         | 0| 1| 2| 3|
         +--+--+--+--+
         | 4| 5| 6| 7|
         +--+--+--+--+
         | 8| 9|10|11|
         +--+--+--+--+
        With starting_corner _NET_WM_BOTTOMRIGHT, it looks like this:

         +--+--+--+--+
         |11|10| 9| 8|
         +--+--+--+--+
         | 7| 6| 5| 4|
         +--+--+--+--+
         | 3| 2| 1| 0|
         +--+--+--+--+
        When the orientation is _NET_WM_ORIENTATION_VERT the layout with four columns and three rows starting in
        the _NET_WM_TOPLEFT corner looks like:

         +--+--+--+--+
         | 0| 3| 6| 9|
         +--+--+--+--+
         | 1| 4| 7|10|
         +--+--+--+--+
         | 2| 5| 8|11|
         +--+--+--+--+
        With starting_corner _NET_WM_TOPRIGHT, it looks like:

         +--+--+--+--+
         | 9| 6| 3| 0|
         +--+--+--+--+
         |10| 7| 4| 1|
         +--+--+--+--+
         |11| 8| 5| 2|
         +--+--+--+--+
        The numbers here are the desktop numbers, as for _NET_CURRENT_DESKTOP.
        """
        self.setProperty(Props.Root.DESKTOP_LAYOUT, [orientation, columns, rows, starting_corner])

    def getShowingDesktop(self) -> Union[bool, None]:
        """
        Some Window Managers have a "showing the desktop" mode in which windows are hidden, and the desktop
        background is displayed and focused. If a Window Manager supports the _NET_SHOWING_DESKTOP hint, it
        MUST set it to a value of 1 when the Window Manager is in "showing the desktop" mode, and a value of
        zero if the Window Manager is not in this mode.

        :return: ''True'' if showing desktop
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Root.SHOWING_DESKTOP)
        res = _getPropertyValue(self.display, ret)
        if res:
            return res != 0
        return None

    def setShowingDesktop(self, show: bool):
        """
        Force showing desktop (minimizing or somehow hiding all open windows)
        Some Window Managers have a "showing the desktop" mode in which windows are hidden, and the desktop
        background is displayed and focused. If a Window Manager supports the _NET_SHOWING_DESKTOP hint, it
        MUST set it to a value of 1 when the Window Manager is in "showing the desktop" mode, and a value of
        zero if the Window Manager is not in this mode.

        :param show: ''True'' to enter showing desktop mode, ''False'' to exit
        """
        if self.getShowingDesktop() != show:
            self.setProperty(Props.Root.SHOWING_DESKTOP, [1 if show else 0])

    """
    Methods below are always related to a given window. 
    Makes it sense to include them within Window class in addition to or instead of here?
    """

    def setClosed(self, winId: int, userAction: bool = True):
        """
        Close target window

        The Window Manager MUST then attempt to close the window specified. See the section called “Source indication
        in requests” for details on the source indication.

        Rationale: A Window Manager might be more clever than the usual method (send WM_DELETE message if the protocol
        is selected, XKillClient otherwise). It might introduce a timeout, for example. Instead of duplicating the
        code, the Window Manager can easily do the job.

        :param winId: id of window to be closed
        :param userAction: set to ''True'' to force action, as if it was requested by an user action
        """
        atom: int = self.display.get_atom(Props.Root.CLOSE, True)
        self.sendMessage(winId, atom, [Xlib.X.CurrentTime, 2 if userAction else 1])

    def setMoveResize(self, winId: int, gravity: int = 0, x: Union[int, None] = None, y: Union[int, None] = None, width: Union[int, None]= None, height: Union[int, None] = None, userAction: bool = True):
        """
        Moves and/or resize given window

        The low byte of data.l[0] contains the gravity to use; it may contain any value allowed for the
        WM_SIZE_HINTS.win_gravity property: NorthWest (1), North (2), NorthEast (3), West (4), Center (5),
        East (6), SouthWest (7), South (8), SouthEast (9), Static (10)

        A gravity of 0 indicates that the Window Manager should use the gravity specified in WM_SIZE_HINTS.win_gravity.

        The bits 8 to 11 indicate the presence of x, y, width and height.

        The bits 12 to 15 indicate the source (see the section called “Source indication
        in requests”), so 0001 indicates the application and 0010 indicates a Pager or a Taskbar.

        The remaining bits should be set to zero.

        Pagers wanting to move or resize a window may send a _NET_MOVERESIZE_WINDOW client message request to the
        root window instead of using a ConfigureRequest.

        Window Managers should treat a _NET_MOVERESIZE_WINDOW message exactly like a ConfigureRequest (in particular,
        adhering to the ICCCM rules about synthetic ConfigureNotify events), except that they should use the gravity
        specified in the message.

        Rationale: Using a _NET_MOVERESIZE_WINDOW message with StaticGravity allows Pagers to exactly position and
        resize a window including its decorations without knowing the size of the decorations.

        :param winId: id of target window to be moved/resized
        :param gravity: gravity to apply to the window action. Defaults to 0 (using window defined gravity)
        :param x: target x coordinate of window. Defaults to None (unchanged)
        :param y: target y coordinate of window. Defaults to None (unchanged)
        :param width: target width of window. Defaults to None (unchanged)
        :param height: target height of window. Defaults to None (unchanged)
        :param userAction: set to ''True'' to force action, as if it was requested by a user action. Defaults to True
        """
        # gravitiy_flags calculations directly taken from 'old' ewmh
        gravity_flags = gravity | 0b0000100000000000
        if x is None:
            x = 0
        else:
            gravity_flags = gravity_flags | 0b0000010000000000
        if y is None:
            y = 0
        else:
            gravity_flags = gravity_flags | 0b0000001000000000
        if width is None:
            width = 0
        else:
            gravity_flags = gravity_flags | 0b0000000100000000
        if height is None:
            height = 0
        else:
            gravity_flags = gravity_flags | 0b0000000010000000
        win = self.display.create_resource_object('window', winId)
        if win.get_wm_transient_for():
            # sendMessage doesn't properly work for transient windows???
            win.configure(x=x, y=y, width=width, height=height)
            self.display.flush()
        else:
            atom: int = self.display.get_atom(Props.Root.MOVERESIZE, True)
            self.sendMessage(winId, atom, [gravity_flags, x, y, width, height, 2 if userAction else 1])

    def setWmMoveResize(self, winId: int, x_root: int, y_root: int, orientation: int, button: int, userAction: bool = True):
        """
        This message allows Clients to initiate window movement or resizing. They can define their own move and size
        "grips", whilst letting the Window Manager control the actual operation. This means that all moves/resizes
        can happen in a consistent manner as defined by the Window Manager. See the section called “Source indication
        in requests” for details on the source indication.

        When sending this message in response to a button press event, button SHOULD indicate the button which
        was pressed, x_root and y_root MUST indicate the position of the button press with respect to the root window
        and direction MUST indicate whether this is a move or resize event, and if it is a resize event, which edges
        of the window the size grip applies to. When sending this message in response to a key event, the direction
        MUST indicate whether this is a move or resize event and the other fields are unused.

        The Client MUST release all grabs prior to sending such message.

        The Window Manager can use the button field to determine the events on which it terminates the operation
        initiated by the _NET_WM_MOVERESIZE message. Since there is a race condition between a client sending the
        _NET_WM_MOVERESIZE message and the user releasing the button, Window Managers are advised to offer some
        other means to terminate the operation, e.g. by pressing the ESC key.

        :param winId: id of the window to be moved/resized
        :param x_root: position of the button press with respect to the root window
        :param y_root: position of the button press with respect to the root window
        :param orientation: move or resize event
        :param button: button pressed
        :param userAction: set to ''True'' to force action, as if it was requested by a user action. Defaults to True
        """
        # Need to understand this property
        atom: int = self.display.get_atom(Props.Root.WM_MOVERESIZE, True)
        self.sendMessage(winId, atom, [x_root, y_root, orientation, button, 2 if userAction else 1])

    def setWmStacking(self, winId: int, siblingId: int, detail: int, userAction: bool = True):
        """
        This request is similar to ConfigureRequest with CWSibling and CWStackMode flags. It should be used only by
        pagers, applications can use normal ConfigureRequests. The source indication field should be therefore
        set to 2, see the section called “Source indication in requests” for details.

        Rationale: A Window Manager may put restrictions on configure requests from applications, for example it may
        under some conditions refuse to raise a window. This request makes it clear it comes from a pager or similar
        tool, and therefore the Window Manager should always obey it.

        :param winId: id of window to be restacked
        :param siblingId: id of sibling window related to restacking action
        :param detail: ???
        :param userAction: set to ''True'' to force action, as if it was requested by a user action. Defaults to True
        """
        # Need to understand this property
        atom: int = self.display.get_atom(Props.Root.RESTACK, True)
        self.sendMessage(winId, atom, [2 if userAction else 1, siblingId, detail])

    def requestFrameExtents(self, winId: int):
        """
        A Client whose window has not yet been mapped can request of the Window Manager an estimate of the
        frame extents it will be given upon mapping. To retrieve such an estimate, the Client MUST send a
        _NET_REQUEST_FRAME_EXTENTS message to the root window. The Window Manager MUST respond by estimating
        the prospective frame extents and setting the window's _NET_FRAME_EXTENTS property accordingly.
        The Client MUST handle the resulting _NET_FRAME_EXTENTS PropertyNotify event. So that the Window Manager
        has a good basis for estimation, the Client MUST set any window properties it intends to set before
        sending this message. The Client MUST be able to cope with imperfect estimates.

        Rationale: A client cannot calculate the dimensions of its window's frame before the window is mapped,
        but some toolkits need this information. Asking the window manager for an estimate of the extents is a
        workable solution. The estimate may depend on the current theme, font sizes or other window properties.
        The client can track changes to the frame's dimensions by listening for _NET_FRAME_EXTENTS PropertyNotify event

        :param winId: id of window for which estimate the frame extents
        """
        # Need to understand this property
        atom: int = self.display.get_atom(Props.Root.REQ_FRAME_EXTENTS, True)
        self.sendMessage(winId, atom, [])


defaultRootWindow = RootWindow()


class Window:
    """
    Base class to access application windows related features.

    To instantiate this class only a window id is required. It's possible to retrieve this value in several ways:

    - Target a specific window using an external module (e.g. PyWinCtl.getAllWindowsWithTitle(title))

    - Retrieve it from your own application (e.g. PyQt's winId() or TKinter's frame())

    Note that, although a root is also a window, these methods will not likely work with it.

    Apart from given methods, there are some values you can use with python-xlib:

    - display: XDisplay connection

    - root: root X Window object

    - rootWindow: object to access RootWindow methods

    - xWindow: X Window object associated to current window

    - id: current window's id

    - extensions: additional, non-EWMH features, related to low-level window properties like hints, protocols and events
    """

    def __init__(self, winId: int):

        self.display, self.screen, self.root = getDisplayFromWindow(winId)
        self.rootWindow: RootWindow = defaultRootWindow if self.root.id == defaultRoot.id else RootWindow(self.root)
        self.xWindow: XWindow = self.display.create_resource_object('window', winId)
        self.id: int = winId
        self.extensions = _Extensions(winId, self.display, self.root)

    def getProperty(self, prop: Union[str, int]) -> Union[Xlib.protocol.request.GetProperty, None]:
        """
        Retrieves given property data from given window

        :param prop: Property to query (int or str format)
        :return: List of int, List of str, str or None (nothing obtained)
        """
        return _getProperty(self.display, self.xWindow, prop)

    def sendMessage(self, prop: Union[str, int], data: Union[List[int], str]):
        """
        Sends a ClientMessage event to current window

        :param prop: property/atom of the event in int or str format
        :param data: Data related to the event. It can be str (format is 8) or a list of up to 5 integers (format is 32)
        """
        return _sendMessage(self.display, self.root, self.id, prop, data)

    def changeProperty(self, prop: Union[str, int], data: List[int], propMode: int = Xlib.X.PropModeReplace):
        """
        Sets given property for the current window. The property is not managed by Window Manager, but returned
        in getProperty() calls together with its data.

        :param prop: property/atom of the event in int or str format
        :param data: Data related to the event. It can be str (format is 8) or a list of up to 5 integers (format is 32)
        :param propMode: whether to Replace/Append/Prepend the property in relation with the rest of existing properties
        """
        _changeProperty(self.display, self.xWindow, prop, data, propMode)

    def getName(self) -> Union[str, None]:
        """
        Gets the name of the current window.
        Some windows may not have a title, the title may change or even this query may fail (e.g. for root windows)

        The Client SHOULD set this to the title of the window in UTF-8 encoding. If set, the Window Manager should use this in preference to WM_NAME.

        :return: name of the window as str or None (nothing obtained)
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.NAME)
        res = _getPropertyValue(self.display, ret)
        if res:
            return str(res[0])
        return None

    def setName(self, name: str):
        """
        Changes the name of the current window

        :param name: new name as string
        """
        self.sendMessage(Props.Window.NAME, name)

    def getVisibleName(self) -> Union[str, None]:
        """
        Gets the visible name of the current window.
        Some windows may not have a title, the title may change or even this query may fail (e.g. for root windows)

        If the Window Manager displays a window name other than _NET_WM_NAME the Window Manager MUST set this to
        the title displayed in UTF-8 encoding.
        Rationale: This property is for Window Managers that display a title different from the _NET_WM_NAME or
        WM_NAME of the window (i.e. xterm <1>, xterm <2>, ... is shown, but _NET_WM_NAME / WM_NAME is still xterm
        for each window) thereby allowing Pagers to display the same title as the Window Manager.

        :return: visible name of the window as str or None (nothing obtained)
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.VISIBLE_NAME)
        res = _getPropertyValue(self.display, ret)
        if res:
            return str(res[0])
        return None

    def setVisibleName(self, name: str):
        """
        Sets the visible name of the current window

        :param name: new visible name as string
        """
        self.sendMessage(Props.Window.VISIBLE_NAME, name)

    def getIconName(self) -> Union[str, None]:
        """
        Gets the name of the window icon

        The Client SHOULD set this to the title of the icon for this window in UTF-8 encoding. If set, the Window
        Manager should use this in preference to WM_ICON_NAME.

        :return: icon name as string
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.ICON_NAME)
        res = _getPropertyValue(self.display, ret)
        if res:
            return str(res[0])
        return None

    def setIconName(self, name: str):
        """
        Change the name of the window icon

        :param name: new icon name as string
        """
        self.sendMessage(Props.Window.ICON, name)

    def getVisibleIconName(self) -> Union[str, None]:
        """
        Gets the visible name of the window icon.

        If the Window Manager displays an icon name other than _NET_WM_ICON_NAME the Window Manager MUST set this
        to the title displayed in UTF-8 encoding.

        :return: visible icon name as string
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.VISIBLE_ICON_NAME)
        res = _getPropertyValue(self.display, ret)
        if res:
            return str(res[0])
        return None

    def setVisibleIconName(self, name: str):
        """
        Change the visible name of window icon

        :param name: new visible icon name as string
        """

        self.sendMessage(Props.Window.VISIBLE_ICON_NAME, name)

    def getDesktop(self) -> Union[int, None]:
        """
        Cardinal to determine the desktop the window is in (or wants to be) starting with 0 for the first desktop.
        A Client MAY choose not to set this property, in which case the Window Manager SHOULD place it as it wishes.
        0xFFFFFFFF indicates that the window SHOULD appear on all desktops.

        The Window Manager should honor _NET_WM_DESKTOP whenever a withdrawn window requests to be mapped.

        The Window Manager should remove the property whenever a window is withdrawn but it should leave the
        property in place when it is shutting down, e.g. in response to losing ownership of the WM_Sn manager
        selection.

        Rationale: Removing the property upon window withdrawal helps legacy applications which want to reuse
        withdrawn windows. Not removing the property upon shutdown allows the next Window Manager to restore
        windows to their previous desktops.

        :return: desktop index on which current window is showing
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.DESKTOP)
        res = _getPropertyValue(self.display, ret)
        if res and isinstance(res[0], int):
            return int(res[0])
        return None

    def setDesktop(self, newDesktop, userAction: bool = True):
        """
        Move the window to the given desktop

        :param newDesktop: target desktop index (as per getNumberOfDesktops())
        :param userAction: source indication (user or pager/manager action). Defaults to True
        """
        if newDesktop <= self.rootWindow.getNumberOfDesktops() and newDesktop != self.rootWindow.getCurrentDesktop():
            self.sendMessage(Props.Window.DESKTOP, [newDesktop, Xlib.X.CurrentTime, 2 if userAction else 1])

    def getWmWindowType(self, text: bool = False) -> Union[List[int], List[str], None]:
        """
        Gets the window type of current window

        This SHOULD be set by the Client before mapping to a list of atoms indicating the functional type of the window.
        This property SHOULD be used by the window manager in determining the decoration, stacking position and other
        behavior of the window. The Client SHOULD specify window types in order of preference (the first being most
        preferable) but MUST include at least one of the basic window type atoms from the list below. This is to allow
        for extension of the list of types whilst providing default behavior for Window Managers that do not recognize
        the extensions.

        Rationale: This hint is intended to replace the MOTIF hints. One of the objections to the MOTIF hints is that
        they are a purely visual description of the window decoration. By describing the function of the window,
        the Window Manager can apply consistent decoration and behavior to windows of the same type. Possible examples
        of behavior include keeping dock/panels on top or allowing pinnable menus / toolbars to only be hidden when
        another window has focus (NextStep style).

        _NET_WM_WINDOW_TYPE_DESKTOP indicates a desktop feature. This can include a single window containing desktop
        icons with the same dimensions as the screen, allowing the desktop environment to have full control of the
        desktop, without the need for proxying root window clicks.

        _NET_WM_WINDOW_TYPE_DOCK indicates a dock or panel feature. Typically a Window Manager would keep such windows
        on top of all other windows.

        _NET_WM_WINDOW_TYPE_TOOLBAR and _NET_WM_WINDOW_TYPE_MENU indicate toolbar and pinnable menu windows,
        respectively (i.e. toolbars and menus "torn off" from the main application). Windows of this type may
        set the WM_TRANSIENT_FOR hint indicating the main application window.

        _NET_WM_WINDOW_TYPE_UTILITY indicates a small persistent utility window, such as a palette or toolbox.
        It is distinct from type TOOLBAR because it does not correspond to a toolbar torn off from the main
        application. It's distinct from type DIALOG because it isn't a transient dialog, the user will probably
        keep it open while they're working. Windows of this type may set the WM_TRANSIENT_FOR hint indicating
        the main application window.

        _NET_WM_WINDOW_TYPE_SPLASH indicates that the window is a splash screen displayed as an application
        is starting up.

        _NET_WM_WINDOW_TYPE_DIALOG indicates that this is a dialog window. If _NET_WM_WINDOW_TYPE is not set,
        then windows with WM_TRANSIENT_FOR set MUST be taken as this type.

        _NET_WM_WINDOW_TYPE_NORMAL indicates that this is a normal, top-level window. Windows with neither
        _NET_WM_WINDOW_TYPE nor WM_TRANSIENT_FOR set MUST be taken as this type.

        :param text: if ''True'', the types will be returned in string format, or as integers if ''False''
        :return: List of window types as integer or strings
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.WM_WINDOW_TYPE)
        return _getPropertyValue(self.display, ret, text)

    def setWmWindowType(self, winType: Union[int, str]):
        """
        Changes the type of current window.

        See getWmWindowType() documentation for more information about window types.

        :param winType: target window type as integer or str
        """
        if isinstance(winType, str):
            winType = self.display.get_atom(winType, True)

        x, y, w, h = _getWindowGeom(self.xWindow, self.root.id)
        self.xWindow.unmap()  # -> Needed in Mint/Cinnamon
        self.changeProperty(Props.Window.WM_WINDOW_TYPE, [winType])
        self.xWindow.map()
        self.display.flush()
        self.setMoveResize(x=x, y=y, width=w, height=h)

    def getWmState(self, text: bool = False) -> Union[List[int], List[str], None]:
        """
        Get the window states values of current window.

        A list of hints describing the window state. Atoms present in the list MUST be considered set, atoms not
        present in the list MUST be considered not set. The Window Manager SHOULD honor _NET_WM_STATE whenever a
        withdrawn window requests to be mapped. A Client wishing to change the state of a window MUST send a
        _NET_WM_STATE client message to the root window (see below). The Window Manager MUST keep this property
        updated to reflect the current state of the window.

        The Window Manager should remove the property whenever a window is withdrawn, but it should leave the
        property in place when it is shutting down, e.g. in response to losing ownership of the WM_Sn manager
        selection.

        Rationale: Removing the property upon window withdrawal helps legacy applications which want to reuse
        withdrawn windows. Not removing the property upon shutdown allows the next Window Manager to restore
        windows to their previous state.

        An implementation MAY add new atoms to this list. Implementations without extensions MUST ignore any
        unknown atoms, effectively removing them from the list. These extension atoms MUST NOT start with the
        prefix _NET.

        _NET_WM_STATE_MODAL indicates that this is a modal dialog box. If the WM_TRANSIENT_FOR hint is set to
        another toplevel window, the dialog is modal for that window; if WM_TRANSIENT_FOR is not set or set to
        the root window the dialog is modal for its window group.

        _NET_WM_STATE_STICKY indicates that the Window Manager SHOULD keep the window's position fixed on the
        screen, even when the virtual desktop scrolls.

        _NET_WM_STATE_MAXIMIZED_{VERT,HORZ} indicates that the window is {vertically,horizontally} maximized.

        _NET_WM_STATE_SHADED indicates that the window is shaded.

        _NET_WM_STATE_SKIP_TASKBAR indicates that the window should not be included on a taskbar. This hint should
        be requested by the application, i.e. it indicates that the window by nature is never in the taskbar.
        Applications should not set this hint if _NET_WM_WINDOW_TYPE already conveys the exact nature of the window.

        _NET_WM_STATE_SKIP_PAGER indicates that the window should not be included on a Pager. This hint should
        be requested by the application, i.e. it indicates that the window by nature is never in the Pager.
        Applications should not set this hint if _NET_WM_WINDOW_TYPE already conveys the exact nature of the window.

        _NET_WM_STATE_HIDDEN should be set by the Window Manager to indicate that a window would not be visible
        on the screen if its desktop/viewport were active and its coordinates were within the screen bounds.
        The canonical example is that minimized windows should be in the _NET_WM_STATE_HIDDEN state. Pagers and
        similar applications should use _NET_WM_STATE_HIDDEN instead of WM_STATE to decide whether to display a
        window in miniature representations of the windows on a desktop.

        Implementation note: if an Application asks to toggle _NET_WM_STATE_HIDDEN the Window Manager should
        probably just ignore the request, since _NET_WM_STATE_HIDDEN is a function of some other aspect of the
        window such as minimization, rather than an independent state.

        _NET_WM_STATE_FULLSCREEN indicates that the window should fill the entire screen and have no window
        decorations. Additionally the Window Manager is responsible for restoring the original geometry after
        a switch from fullscreen back to normal window. For example, a presentation program would use this hint.

        _NET_WM_STATE_ABOVE indicates that the window should be on top of most windows (see the section called
        “Stacking order” for details).

        _NET_WM_STATE_BELOW indicates that the window should be below most windows (see the section called
        “Stacking order” for details).

        _NET_WM_STATE_ABOVE and _NET_WM_STATE_BELOW are mainly meant for user preferences and should not be
        used by applications e.g. for drawing attention to their dialogs (the Urgency hint should be used in
        that case, see the section called “Urgency”).'

        _NET_WM_STATE_DEMANDS_ATTENTION indicates that some action in or with the window happened. For example,
        it may be set by the Window Manager if the window requested activation but the Window Manager refused it,
        or the application may set it if it finished some work. This state may be set by both the Client and the
        Window Manager. It should be unset by the Window Manager when it decides the window got the required
        attention (usually, that it got activated).

        :param text: if ''True'', the states will be returned in string format, or as integers if ''False''
        :return: List of integers or strings
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.WM_STATE)
        return _getPropertyValue(self.display, ret, text)

    def changeWmState(self, action: int, state: Union[int, str], state2: Union[int, str] = 0, userAction: bool = True):
        """
        Sets the window states values of current window.

        See setWmState() documentation for more information on Window States.

        This message allows two properties to be changed simultaneously, specifically to allow both horizontal
        and vertical maximization to be altered together. l[2] MUST be set to zero if only one property is to
        be changed. See the section called “Source indication in requests” for details on the source indication.
        l[0], the action, MUST be one of:

        _NET_WM_STATE_REMOVE        0    /* remove/unset property */
        _NET_WM_STATE_ADD           1    /* add/set property */
        _NET_WM_STATE_TOGGLE        2    /* toggle property  */

        :param action: Action to perform with the state: ADD/REMOVE/TOGGLE
        :param state: Target new state
        :param state2: Up to two states can be changed at once. Defaults to 0 (no second state to change).
        :param userAction: source indication (user or pager/manager action). Defaults to True
        """
        if action in (Props.Window.State.Action.ADD, Props.Window.State.Action.REMOVE, Props.Window.State.Action.TOGGLE):
            if isinstance(state, str):
                state = self.display.get_atom(state, True)
            if isinstance(state2, str):
                state2 = self.display.get_atom(state2, True)
            self.sendMessage(Props.Window.WM_STATE, [action, state, state2, 2 if userAction else 1])

    def setMaximized(self, maxHorz: bool, maxVert: bool):
        """
        Set or unset the values of maximized states, individually.

        :param maxHorz: ''True'' / ''False'' to indicate whether the window should be horizontally maximized or not
        :param maxVert: ''True'' / ''False'' to indicate whether the window should be vertically maximized or not
        """
        state1 = 0
        state2 = 0
        ret: Union[List[int], List[str], None] = self.getWmState(True)
        if ret is None:
            states = []
        else:
            states = cast(List[str], ret)
        if maxHorz and maxVert:
            if Props.Window.State.MAXIMIZED_HORZ not in states:
                state1 = self.display.get_atom(Props.Window.State.MAXIMIZED_HORZ, True)
            if Props.Window.State.MAXIMIZED_VERT not in states:
                state2 = self.display.get_atom(Props.Window.State.MAXIMIZED_VERT, True)
            if state1 or state2:
                self.changeWmState(Props.Window.State.Action.ADD, state1 if state1 else state2, state2 if state1 else 0)
        elif maxHorz:
            if Props.Window.State.MAXIMIZED_HORZ not in states:
                state = self.display.get_atom(Props.Window.State.MAXIMIZED_HORZ, True)
                self.changeWmState(Props.Window.State.Action.ADD, state, 0)
            if Props.Window.State.MAXIMIZED_VERT in states:
                state = self.display.get_atom(Props.Window.State.MAXIMIZED_VERT, True)
                self.changeWmState(Props.Window.State.Action.REMOVE, state, 0)
        elif maxVert:
            if Props.Window.State.MAXIMIZED_HORZ in states:
                state = self.display.get_atom(Props.Window.State.MAXIMIZED_HORZ, True)
                self.changeWmState(Props.Window.State.Action.REMOVE, state, 0)
            if Props.Window.State.MAXIMIZED_VERT not in states:
                state = self.display.get_atom(Props.Window.State.MAXIMIZED_VERT, True)
                self.changeWmState(Props.Window.State.Action.ADD, state, 0)
        else:
            if Props.Window.State.MAXIMIZED_HORZ in states:
                state1 = self.display.get_atom(Props.Window.State.MAXIMIZED_HORZ, True)
            if Props.Window.State.MAXIMIZED_VERT in states:
                state2 = self.display.get_atom(Props.Window.State.MAXIMIZED_VERT, True)
            if state1 or state2:
                self.changeWmState(Props.Window.State.Action.REMOVE, state1 if state1 else state2, state2 if state1 else 0)

    def setMinimized(self):
        """
        Sets Iconified (minimized) state for current window

        Unlike maximized, this action can only be reverted by using activate() or restore() methods.
        """
        states = self.getWmState(True)
        if not states or (states and Props.Window.State.HIDDEN not in states):
            atom = self.display.get_atom(Props.Window.CHANGE_STATE, True)
            self.sendMessage(atom, [Xlib.Xutil.IconicState])

    def getAllowedActions(self, text=False) -> Union[List[int], None]:
        """
        Gets the list of allowed actions for current window.

        A list of atoms indicating user operations that the Window Manager supports for this window. Atoms
        present in the list indicate allowed actions, atoms not present in the list indicate actions that are
        not supported for this window. The Window Manager MUST keep this property updated to reflect the actions
        which are currently "active" or "sensitive" for a window. Taskbars, Pagers, and other tools use
        _NET_WM_ALLOWED_ACTIONS to decide which actions should be made available to the user.

        An implementation MAY add new atoms to this list. Implementations without extensions MUST ignore any
        unknown atoms, effectively removing them from the list. These extension atoms MUST NOT start with the
        prefix _NET.

        Note that the actions listed here are those that the Window Manager will honor for this window. The
        operations must still be requested through the normal mechanisms outlined in this specification. For example,
         _NET_WM_ACTION_CLOSE does not mean that clients can send a WM_DELETE_WINDOW message to this window; it means
         that clients can use a _NET_CLOSE_WINDOW message to ask the Window Manager to do so.

        Window Managers SHOULD ignore the value of _NET_WM_ALLOWED_ACTIONS when they initially manage a window.
        This value may be left over from a previous Window Manager with different policies.

        _NET_WM_ACTION_MOVE indicates that the window may be moved around the screen.

        _NET_WM_ACTION_RESIZE indicates that the window may be resized. (Implementation note: Window Managers can
        identify a non-resizable window because its minimum and maximum size in WM_NORMAL_HINTS will be the same.)

        _NET_WM_ACTION_MINIMIZE indicates that the window may be iconified.

        _NET_WM_ACTION_SHADE indicates that the window may be shaded.

        _NET_WM_ACTION_STICK indicates that the window may have its sticky state toggled (as for _NET_WM_STATE_STICKY).
         Note that this state has to do with viewports, not desktops.

        _NET_WM_ACTION_MAXIMIZE_HORZ indicates that the window may be maximized horizontally.

        _NET_WM_ACTION_MAXIMIZE_VERT indicates that the window may be maximized vertically.

        _NET_WM_ACTION_FULLSCREEN indicates that the window may be brought to fullscreen state.

        _NET_WM_ACTION_CHANGE_DESKTOP indicates that the window may be moved between desktops.

        _NET_WM_ACTION_CLOSE indicates that the window may be closed (i.e. a WM_DELETE_WINDOW message may be sent).

        :param text: if ''True'', the actions will be returned in string format, or as integers if ''False''
        :return: List of integers or strings
        """
        ret = self.getProperty(Props.Window.ALLOWED_ACTIONS)
        res = _getPropertyValue(self.display, ret, text)
        if res is not None:
            res = cast(List[int], res)
        return res

    def setAllowedActions(self, newActions: Union[List[int], List[str]]):
        """
        Sets the allowed actions of current window.

        :param newActions: List of new actions allowed, in integer or string format
        """
        # Can this be set??? Investigate wm_protocols, which might be related (e.g. 'WM_DELETE_WINDOW')
        pass

    def getStrut(self) -> Union[List[int], None]:
        """
        This property is equivalent to a _NET_WM_STRUT_PARTIAL property where all start values are 0 and all
        end values are the height or width of the logical screen. _NET_WM_STRUT_PARTIAL was introduced later
        than _NET_WM_STRUT, however, so clients MAY set this property in addition to _NET_WM_STRUT_PARTIAL to
        ensure backward compatibility with Window Managers supporting older versions of the Specification.

        :return:
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.STRUT)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], res)
        return res

    def setStrut(self, left, right, top, bottom):
        # Need to understand this
        self.sendMessage(Props.Window.STRUT, [left, right, top, bottom])

    def getStrutPartial(self) -> Union[List[int], None]:
        """
        This property MUST be set by the Client if the window is to reserve space at the edge of the screen.
        The property contains 4 cardinals specifying the width of the reserved area at each border of the screen,
        and an additional 8 cardinals specifying the beginning and end corresponding to each of the four struts.
        The order of the values is left, right, top, bottom, left_start_y, left_end_y, right_start_y, right_end_y,
        top_start_x, top_end_x, bottom_start_x, bottom_end_x. All coordinates are root window coordinates.
        The client MAY change this property at any time, therefore the Window Manager MUST watch for property
        notify events if the Window Manager uses this property to assign special semantics to the window.

        If both this property and the _NET_WM_STRUT property are set, the Window Manager MUST ignore the _NET_WM_STRUT
        property values and use instead the values for _NET_WM_STRUT_PARTIAL. This will ensure that Clients can safely
        set both properties without giving up the improved semantics of the new property.

        The purpose of struts is to reserve space at the borders of the desktop. This is very useful for a docking area,
        a taskbar or a panel, for instance. The Window Manager should take this reserved area into account when
        constraining window positions - maximized windows, for example, should not cover that area.

        The start and end values associated with each strut allow areas to be reserved which do not span the entire
        width or height of the screen. Struts MUST be specified in root window coordinates, that is, they are not
        relative to the edges of any view port or Xinerama monitor.

        For example, for a panel-style Client appearing at the bottom of the screen, 50 pixels tall, and occupying
        the space from 200-600 pixels from the left of the screen edge would set a bottom strut of 50, and set
        bottom_start_x to 200 and bottom_end_x to 600. Another example is a panel on a screen using the Xinerama
        extension. Assume that the set up uses two monitors, one running at 1280x1024 and the other to the right
        running at 1024x768, with the top edge of the two physical displays aligned. If the panel wants to fill the
        entire bottom edge of the smaller display with a panel 50 pixels tall, it should set a bottom strut of 306,
        with bottom_start_x of 1280, and bottom_end_x of 2303. Note that the strut is relative to the screen edge,
        and not the edge of the xinerama monitor.

        Rationale: A simple "do not cover" hint is not enough for dealing with e.g. auto-hide panels.

        Notes: An auto-hide panel SHOULD set the strut to be its minimum, hidden size. A "corner" panel that does not
        extend for the full length of a screen border SHOULD only set one strut.

        :return:
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.STRUT_PARTIAL)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], res)
        return res

    def setStrutPartial(self, left, right, top, bottom,
                        left_start_y, left_end_y, right_start_y, right_end_y,
                        top_start_x, top_end_x, bottom_start_x, bottom_end_x,):
        """
        Set new Strut Partial property.

        See getStrutPartial() documentation for more information on this property.
        """
        # Need to understand this
        pass

    def getIconGeometry(self) -> Union[List[int], None]:
        """
        Get the geometry of current window icon.

        This optional property MAY be set by stand alone tools like a taskbar or an iconbox. It specifies the geometry
        of a possible icon in case the window is iconified.

        Rationale: This makes it possible for a Window Manager to display a nice animation like morphing the window
        into its icon.

        :return: List of integers containing the icon geometry or None (no obtained)
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.ICON_GEOMETRY)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getPid(self) -> Union[int, None]:
        """
        Get the Process ID (pid) of the process to which current window belongs to.

        If set, this property MUST contain the process ID of the client owning this window. This MAY be used by
        the Window Manager to kill windows which do not respond to the _NET_WM_PING protocol.

        If _NET_WM_PID is set, the ICCCM-specified property WM_CLIENT_MACHINE MUST also be set. While the ICCCM
        only requests that WM_CLIENT_MACHINE is set “ to a string that forms the name of the machine running the
        client as seen from the machine running the server” conformance to this specification requires that
        WM_CLIENT_MACHINE be set to the fully-qualified domain name of the client's host.

        :return: pid of current process as integer
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.PID)
        res = _getPropertyValue(self.display, ret)
        if res:
            return int(res[0])
        return None

    def getHandledIcons(self) -> Union[List[int], None]:
        """
        Get the id of icons handled by the window.

        This property can be set by a Pager on one of its own toplevel windows to indicate that the Window Manager
        need not provide icons for iconified windows, for example if it is a taskbar and provides buttons for
        iconified windows.

        :return: List of integers or None (not obtained)
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.HANDLED_ICONS)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getUserTime(self) -> Union[List[int], None]:
        """
        Get time since last user activity on current window.

        This property contains the XServer time at which last user activity in this window took place.

        Clients should set this property on every new toplevel window, before mapping the window, to the
        timestamp of the user interaction that caused the window to appear. A client that only deals with
        core events, might, for example, use the timestamp of the last KeyPress or ButtonPress event.
        ButtonRelease and KeyRelease events should not generally be considered to be user interaction,
        because an application may receive KeyRelease events from global keybindings, and generally release
        events may have later timestamp than actions that were triggered by the matching press events.
        Clients can obtain the timestamp that caused its first window to appear from the DESKTOP_STARTUP_ID
        environment variable, if the app was launched with startup notification. If the client does not know
        the timestamp of the user interaction that caused the first window to appear (e.g. because it was not
        launched with startup notification), then it should not set the property for that window. The special
        value of zero on a newly mapped window can be used to request that the window not be initially focused
         when it is mapped.

        If the client has the active window, it should also update this property on the window whenever there's
        user activity.

        Rationale: This property allows a Window Manager to alter the focus, stacking, and/or placement behavior
        of windows when they are mapped depending on whether the new window was created by a user action or is a
        "pop-up" window activated by a timer or some other event.

        :return: timestamp in integer format or None (not obtained)
        """
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(Props.Window.USER_TIME)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getFrameExtents(self) -> Union[List[int], None]:
        """
        Get the current window frame extents (space reserved by the window manager around window)

        The Window Manager MUST set _NET_FRAME_EXTENTS to the extents of the window's frame. left, right, top
        and bottom are widths of the respective borders added by the Window Manager.

        :return: left, right, top, bottom
        """
        prop = "_GTK_FRAME_EXTENTS"
        atom = self.display.intern_atom(prop, True)
        if not atom:
            prop = "_NET_FRAME_EXTENTS"
        ret: Union[Xlib.protocol.request.GetProperty, None] = self.getProperty(prop)
        res = _getPropertyValue(self.display, ret)
        if res is not None:
            res = cast(List[int], res)
        return res

    def setActive(self, userAction: bool = True):
        """
        Set current window as active (focused).

        Source indication should be 1 when the request comes from an application, and 2 when it comes from a pager.
        Clients using older version of this spec use 0 as source indication, see the section called “Source indication
        in requests” for details. The timestamp is Client's last user activity timestamp (see _NET_WM_USER_TIME) at
        the time of the request, and the currently active window is the Client's active toplevel window, if any
        (the Window Manager may be e.g. more likely to obey the request if it will mean transferring focus from one
        active window to another).

        Depending on the information provided with the message, the Window Manager may decide to refuse the request
        (either completely ignore it, or e.g. use _NET_WM_STATE_DEMANDS_ATTENTION).

        :param userAction: source indication (user or pager/manager action). Defaults to True
        """
        atom = self.display.get_atom(Props.Window.ACTIVE, True)
        self.sendMessage(atom, [2 if userAction else 1, Xlib.X.CurrentTime, self.xWindow.id])

    def setClosed(self, userAction: bool = True):
        """
        Request to close current window.

        The Window Manager MUST then attempt to close the window specified. See the section called “Source
        indication in requests” for details on the source indication.

        Rationale: A Window Manager might be more clever than the usual method (send WM_DELETE message if the
        protocol is selected, XKillClient otherwise). It might introduce a timeout, for example. Instead of
        duplicating the code, the Window Manager can easily do the job.

        :param userAction: source indication (user or pager/manager action). Defaults to True
        """
        atom = self.display.get_atom(Props.Window.CLOSE, True)
        self.sendMessage(atom, [Xlib.X.CurrentTime, 2 if userAction else 1])

    def changeStacking(self, mode: int):
        """
        Changes current window position (stacking) in relation to its siblings.

        To obtain good interoperability between different Desktop Environments, the following layered stacking
        order is recommended, from the bottom:

        windows of type _NET_WM_TYPE_DESKTOP

        windows having state _NET_WM_STATE_BELOW

        windows not belonging in any other layer

        windows of type _NET_WM_TYPE_DOCK (unless they have state _NET_WM_TYPE_BELOW) and windows having state
        _NET_WM_STATE_ABOVE

        focused windows having state _NET_WM_STATE_FULLSCREEN

        Windows that are transient for another window should be kept above this window.

        The window manager may choose to put some windows in different stacking positions, for example to allow
        the user to bring currently a active window to the top and return it back when the window looses focus.

        :param mode: allowed values are Above / Below
        """
        self.xWindow.configure(stack_mode=mode)
        self.display.flush()

    def setMoveResize(self, gravity: int = 0, x: Union[int, None] = None, y: Union[int, None] = None, width: Union[int, None] = None, height: Union[int, None] = None, userAction: bool = True):
        """
        Move and/or resize current window

        The low byte of data.l[0] contains the gravity to use; it may contain any value allowed for the
        WM_SIZE_HINTS.win_gravity property: NorthWest (1), North (2), NorthEast (3), West (4), Center (5),
        East (6), SouthWest (7), South (8), SouthEast (9), Static (10)

        A gravity of 0 indicates that the Window Manager should use the gravity specified in WM_SIZE_HINTS.win_gravity.

        The bits 8 to 11 indicate the presence of x, y, width and height.

        The bits 12 to 15 indicate the source (see the section called “Source indication
        in requests”), so 0001 indicates the application and 0010 indicates a Pager or a Taskbar.

        The remaining bits should be set to zero.

        Pagers wanting to move or resize a window may send a _NET_MOVERESIZE_WINDOW client message request to the
        root window instead of using a ConfigureRequest.

        Window Managers should treat a _NET_MOVERESIZE_WINDOW message exactly like a ConfigureRequest (in particular,
        adhering to the ICCCM rules about synthetic ConfigureNotify events), except that they should use the gravity
        specified in the message.

        Rationale: Using a _NET_MOVERESIZE_WINDOW message with StaticGravity allows Pagers to exactly position and
        resize a window including its decorations without knowing the size of the decorations.

        :param gravity: gravity to apply to the window action. Defaults to 0 (using window defined gravity)
        :param x: target x coordinate of window. Defaults to None (unchanged)
        :param y: target y coordinate of window. Defaults to None (unchanged)
        :param width: target width of window. Defaults to None (unchanged)
        :param height: target height of window. Defaults to None (unchanged)
        :param userAction: set to ''True'' to force action, as if it was requested by a user action. Defaults to True
        """
        # gravity_flags directly taken from 'old' ewmh module
        gravity_flags = gravity | 0b0000100000000000
        if x is None:
            x = 0
        else:
            gravity_flags = gravity_flags | 0b0000010000000000
        if y is None:
            y = 0
        else:
            gravity_flags = gravity_flags | 0b0000001000000000
        if width is None:
            width = 0
        else:
            gravity_flags = gravity_flags | 0b0000000100000000
        if height is None:
            height = 0
        else:
            gravity_flags = gravity_flags | 0b0000000010000000

        if self.xWindow.get_wm_transient_for() or True:
            # sendMessage doesn't properly work for transient windows???
            self.xWindow.configure(x=x, y=y, width=width, height=height)
            self.display.flush()
        else:
            atom = self.display.get_atom(Props.Window.MOVERESIZE, True)
            self.sendMessage(atom, [gravity_flags, x, y, width, height, 2 if userAction else 1])

    def setWmMoveResize(self, x_root, y_root, orientation, button, userAction: bool = True):
        """
        This message allows Clients to initiate window movement or resizing. They can define their own move and size
        "grips", whilst letting the Window Manager control the actual operation. This means that all moves/resizes
        can happen in a consistent manner as defined by the Window Manager. See the section called “Source indication
        in requests” for details on the source indication.

        When sending this message in response to a button press event, button SHOULD indicate the button which
        was pressed, x_root and y_root MUST indicate the position of the button press with respect to the root window
        and direction MUST indicate whether this is a move or resize event, and if it is a resize event, which edges
        of the window the size grip applies to. When sending this message in response to a key event, the direction
        MUST indicate whether this is a move or resize event and the other fields are unused.

        The Client MUST release all grabs prior to sending such message.

        The Window Manager can use the button field to determine the events on which it terminates the operation
        initiated by the _NET_WM_MOVERESIZE message. Since there is a race condition between a client sending the
        _NET_WM_MOVERESIZE message and the user releasing the button, Window Managers are advised to offer some
        other means to terminate the operation, e.g. by pressing the ESC key.

        :param x_root: position of the button press with respect to the root window
        :param y_root: position of the button press with respect to the root window
        :param orientation: move or resize event
        :param button: button pressed
        :param userAction:
        """
        # Need to understand this property
        atom = self.display.get_atom(Props.Window.WM_MOVERESIZE, True)
        self.sendMessage(atom, [x_root, y_root, orientation, button, 2 if userAction else 1])

    def setWmStacking(self):
        """
        This request is similar to ConfigureRequest with CWSibling and CWStackMode flags. It should be used only by
        pagers, applications can use normal ConfigureRequests. The source indication field should be therefore
        set to 2, see the section called “Source indication in requests” for details.

        Rationale: A Window Manager may put restrictions on configure requests from applications, for example it may
        under some conditions refuse to raise a window. This request makes it clear it comes from a pager or similar
        tool, and therefore the Window Manager should always obey it.

        :param winId: id of window to be restacked
        :param siblingId: id of sibling window related to restacking action
        :param detail: ???
        :param userAction: should be set to 2 (typically used by pagers)
        """
        # Need to understand this property
        atom = self.display.get_atom(Props.Window.RESTACK, True)
        self.sendMessage(atom, [])

    def requestFrameExtents(self):
        """
        Ask Window Manager to estimate frame extents before mapping current window.

        A Client whose window has not yet been mapped can request of the Window Manager an estimate of the
        frame extents it will be given upon mapping. To retrieve such an estimate, the Client MUST send a
        _NET_REQUEST_FRAME_EXTENTS message to the root window. The Window Manager MUST respond by estimating
        the prospective frame extents and setting the window's _NET_FRAME_EXTENTS property accordingly.
        The Client MUST handle the resulting _NET_FRAME_EXTENTS PropertyNotify event. So that the Window Manager
        has a good basis for estimation, the Client MUST set any window properties it intends to set before
        sending this message. The Client MUST be able to cope with imperfect estimates.

        Rationale: A client cannot calculate the dimensions of its window's frame before the window is mapped,
        but some toolkits need this information. Asking the window manager for an estimate of the extents is a
        workable solution. The estimate may depend on the current theme, font sizes or other window properties.
        The client can track changes to the frame's dimensions by listening for _NET_FRAME_EXTENTS PropertyNotify event
        """
        # Need to understand this property
        atom = self.display.get_atom(Props.Window.REQ_FRAME_EXTENTS, True)
        self.sendMessage(atom, [])


class _Extensions:
    """
     Additional, non-EWMH features, related to low-level window properties like hints, protocols and events
    """

    def __init__(self, winId: int, display, root):
        self.winId = winId
        self.display = display
        self.root = root
        self.win = self.display.create_resource_object('window', winId)

    def getWmHints(self) -> Structs.WmHints:
        """
        Get window hints.

        {'flags': 103, 'input': 1, 'initial_state': 1, 'icon_pixmap': <Pixmap 0x02a22304>, 'icon_window': <Window 0x00000000>, 'icon_x': 0, 'icon_y': 0, 'icon_mask': <Pixmap 0x02a2230b>, 'window_group': <Window 0x02a00001>}

        Xlib provides functions that you can use to set and read the WM_HINTS property for a given window.
        These functions use the flags and the XWMHints structure, as defined in the X11/Xutil.h header file.
        To allocate an XWMHints structure, use XAllocWMHints().

        The XWMHints structure contains:

        typedef struct {
            long flags;		/* marks which fields in this structure are defined */
            Bool input;		/* does this application rely on the window manager to
                           get keyboard input? */
            int initial_state;	/* see below */
            Pixmap icon_pixmap;	/* pixmap to be used as icon */
            Window icon_window;	/* window to be used as icon */
            int icon_x, icon_y;	/* initial position of icon */
            Pixmap icon_mask;	/* pixmap to be used as mask for icon_pixmap */
            XID window_group;	/* id of related window group */
            /* this structure may be extended in the future */
        } XWMHints;
        The input member is used to communicate to the window manager the input focus model used by the application. Applications that expect input but never explicitly set focus to any of their subwindows (that is, use the push model of focus management), such as X Version 10 style applications that use real-estate driven focus, should set this member to True. Similarly, applications that set input focus to their subwindows only when it is given to their top-level window by a window manager should also set this member to True. Applications that manage their own input focus by explicitly setting focus to one of their subwindows whenever they want keyboard input (that is, use the pull model of focus management) should set this member to False. Applications that never expect any keyboard input also should set this member to False.

        Pull model window managers should make it possible for push model applications to get input by setting input focus to the top-level windows of applications whose input member is True. Push model window managers should make sure that pull model applications do not break them by resetting input focus to PointerRoot when it is appropriate (for example, whenever an application whose input member is False sets input focus to one of its subwindows).

        The definitions for the initial_state flag are:

        #define	WithdrawnState	0
        #define	NormalState	1	/* most applications start this way */
        #define	IconicState	3	/* application wants to start as an icon */
        The icon_mask specifies which pixels of the icon_pixmap should be used as the icon. This allows for nonrectangular icons. Both icon_pixmap and icon_mask must be bitmaps. The icon_window lets an application provide a window for use as an icon for window managers that support such use. The window_group lets you specify that this window belongs to a group of other windows. For example, if a single application manipulates multiple top-level windows, this allows you to provide enough information that a window manager can iconify all of the windows rather than just the one window.
        The UrgencyHint flag, if set in the flags field, indicates that the client deems the window contents to be urgent, requiring the timely response of the user. The window manager will make some effort to draw the user's attention to this window while this flag is set. The client must provide some means by which the user can cause the urgency flag to be cleared (either mitigating the condition that made the window urgent or merely shutting off the alarm) or the window to be withdrawn.

        :return: Hints struct
        """
        return cast(Structs.WmHints, self.win.get_wm_hints())

    def setWmHints(self, hint: str, value: Any):
        """
        Set new hints for current window.

        See getWmHints() documentation for more info about hints.

        ---> TODO: CHANGE this function to accept hints as input params and recalculate flags according to it.
        """
        hints: Xlib.protocol.rq.DictWrapper = self.win.get_wm_hints()
        if hints:
            hints[hint] = value
            # We should also re-calculate and re-write flags
        self.win.set_wm_hints(hints)
        self.display.flush()

    def getWmNormalHints(self):
        """
        Xlib provides functions that you can use to set or read the WM_NORMAL_HINTS property for a given window.
        The functions use the flags and the XSizeHints structure, as defined in the X11/Xutil.h header file.
        The size of the XSizeHints structure may grow in future releases, as new components are added to support
        new ICCCM features. Passing statically allocated instances of this structure into Xlib may result in memory
        corruption when running against a future release of the library. As such, it is recommended that only
        dynamically allocated instances of the structure be used.

        To allocate an XSizeHints structure, use XAllocSizeHints().

        The XSizeHints structure contains:

        /* Size hints mask bits */

        #define USPosition	(1L << 0)	/* user specified x, y */
        #define USSize		(1L << 1)	/* user specified width, height */
        #define PPosition	(1L << 2)	/* program specified position */
        #define PSize		(1L << 3)	/* program specified size */
        #define PMinSize	(1L << 4)	/* program specified minimum size */
        #define PMaxSize	(1L << 5)	/* program specified maximum size */
        #define PResizeInc	(1L << 6)	/* program specified resize increments */
        #define PAspect		(1L << 7)	/* program specified min and max aspect ratios */
        #define PBaseSize	(1L << 8)
        #define PWinGravity	(1L << 9)
        #define PAllHints	(PPosition|PSize|PMinSize|PMaxSize|PResizeInc|PAspect)

        /* Values */

        typedef struct {
            long flags;		/* marks which fields in this structure are defined */
            int x, y;		/* Obsolete */
            int width, height;	/* Obsolete */
            int min_width, min_height;
            int max_width, max_height;
            int width_inc, height_inc;
            struct {
                   int x;		/* numerator */
                   int y;		/* denominator */
            } min_aspect, max_aspect;
            int base_width, base_height;
            int win_gravity;
            /* this structure may be extended in the future */
        } XSizeHints;
        The x, y, width, and height members are now obsolete and are left solely for compatibility reasons.

        The min_width and min_height members specify the minimum window size that still allows the application to
        be useful.

        The max_width and max_height members specify the maximum window size. The width_inc and height_inc
        members define an arithmetic progression of sizes (minimum to maximum) into which the window prefers
        to be resized. The min_aspect and max_aspect members are expressed as ratios of x and y, and they
        allow an application to specify the range of aspect ratios it prefers. The base_width and base_height
        members define the desired size of the window. The window manager will interpret the position of the
        window and its border width to position the point of the outer rectangle of the overall window specified
        by the win_gravity member. The outer rectangle of the window includes any borders or decorations supplied
        by the window manager. In other words, if the window manager decides to place the window where the
        client asked, the position on the parent window's border named by the win_gravity will be placed where
        the client window would have been placed in the absence of a window manager.
        """
        return self.win.get_wm_normal_hints()

    def setWmNormalHints(self, hint, value):
        """
        Set new normal hints for current window.

        See getWmNormalHints() documentation for more info about hints.

        ---> TODO: this function to accept hints as input params and recalculate flags according to it.
        """
        pass

    def getWmProtocols(self, text: bool = False) -> Union[List[int], List[str]]:
        """
        Get the protocols supported by current window.

        The WM_PROTOCOLS property (of type ATOM) is a list of atoms. Each atom identifies a communication protocol
        between the client and the window manager in which the client is willing to participate. Atoms can identify
        both standard protocols and private protocols specific to individual window managers.

        All the protocols in which a client can volunteer to take part involve the window manager sending the
        client a ClientMessage event and the client taking appropriate action. For details of the contents of
        the event, see section 4.2.8. In each case, the protocol transactions are initiated by the window manager.

        The WM_PROTOCOLS property is not required. If it is not present, the client does not want to participate
        in any window manager protocols.

        The X Consortium will maintain a registry of protocols to avoid collisions in the name space. The following
        table lists the protocols that have been defined to date.

        Protocol	Section	Purpose
        WM_TAKE_FOCUS	4.1.7	Assignment of input focus
        WM_SAVE_YOURSELF	Appendix C	Save client state request (deprecated)
        WM_DELETE_WINDOW	4.2.8.1	Request to delete top-level window

        :param text: select whether the procols will be returned as integers or strings
        :return: List of protocols in integer or string format
        """
        ret = self.win.get_wm_protocols()
        prots = ret if ret else []
        if text:
            res = []
            for p in prots:
                try:
                    res.append(self.display.get_atom_name(p))
                except:
                    pass
            return res
        else:
            return [p for p in prots]

    def addWmProtocol(self, atom: int):
        """
        Adds a new protocol for current window.

        See getWmProtocols() documentation for more info about protocols.

        :param atom: protocol to be added
        """
        prots = self.win.get_wm_protocols()
        if atom not in prots:
            prots.append(atom)
        self.win.set_wm_protocols(prots)
        self.display.flush()

    def delWmProtocol(self, atom: int):
        """
        Deletes existing protocol for current window.

        See getWmProtocols() documentation for more info about protocols.

        :param atom: protocol to be deleted
        """
        prots = self.win.get_wm_protocols()
        new_prots = [p for p in prots if p != atom]
        prots = new_prots
        self.win.set_wm_protocols(prots)

    class _CheckEvents:
        """
        Activate a watchdog to be notified on given events (to provided callback function).

        It's important to define proper mask and event list accordingly. See checkEvents() documentation.
        """

        def __init__(self, winId: int, display: Xlib.display.Display, root: XWindow, events: List[int], mask: int,
                     callback: Callable[[Xlib.protocol.rq.Event], None]):

            self._winId = winId
            self._display = display
            self._root = root
            self._events = events
            self._mask = mask

            self._root.change_attributes(event_mask=self._mask)
            self._display.flush()

            self._keep = threading.Event()
            self._stopRequested = False
            self._callback = callback
            self._checkThread = None
            self._threadStarted = False

        def _checkDisplayEvents(self):

            while self._keep.wait():
                if not self._stopRequested:
                    if self._root.display.pending_events():
                        event = self._root.display.next_event()
                        if event.type in self._events:
                            if event.window.id == self._winId:
                                self._callback(event)
                            elif hasattr(event, "above_sibling"):
                                # This is needed for Mint/Cinnamon
                                self._callback(event)
                                try:
                                    children = event.above_sibling.query_tree().children
                                except:
                                    children = []
                                for child in children:
                                    if self._winId == child.id:
                                        self._callback(event)
                                        break
                    time.sleep(0.01)
                else:
                    # Is this necessary to somehow "free" the events catching???
                    self._root.change_attributes(event_mask=Xlib.X.NoEventMask)
                    self._display.flush()
                    break

        def start(self):
            self._keep.set()
            if not self._threadStarted and self._checkThread is None:
                self._checkThread = threading.Thread(target=self._checkDisplayEvents)
                self._checkThread.daemon = True
                self._threadStarted = True
                self._checkThread.start()

        def pause(self):
            self._keep.clear()

        def stop(self):
            if self._threadStarted:
                self._threadStarted = False
                self._stopRequested = True
                self._keep.set()
                self._checkThread.join()
                self._checkThread = None

    def checkEvents(self, events: List[int], mask: int, callback: Callable[[Xlib.protocol.rq.Event], None], winId: int = 0) -> _CheckEvents:
        """
        Activate a watchdog to be notified on given events (to provided callback function).

        It's important to define proper mask and event list accordingly:

        Clients select event reporting of most events relative to a window. To do this, pass an event mask to an
        Xlib event-handling function that takes an event_mask argument. The bits of the event mask are defined in
        X11/X.h. Each bit in the event mask maps to an event mask name, which describes the event or events you
        want the X server to return to a client application.

        Unless the client has specifically asked for them, most events are not reported to clients when they are
        generated. Unless the client suppresses them by setting graphics-exposures in the GC to False ,
        GraphicsExpose and NoExpose are reported by default as a result of XCopyPlane() and XCopyArea().
        SelectionClear, SelectionRequest, SelectionNotify, or ClientMessage cannot be masked. Selection related
        events are only sent to clients cooperating with selections (see section "Selections"). When the keyboard
        or pointer mapping is changed, MappingNotify is always sent to clients.

        The following table lists the event mask constants you can pass to the event_mask argument and the
        circumstances in which you would want to specify the event mask:

        NoEventMask	                No events wanted
        KeyPressMask	            Keyboard down events wanted
        KeyReleaseMask	            Keyboard up events wanted
        ButtonPressMask	            Pointer button down events wanted
        ButtonReleaseMask	        Pointer button up events wanted
        EnterWindowMask	            Pointer window entry events wanted
        LeaveWindowMask	            Pointer window leave events wanted
        PointerMotionMask	        Pointer motion events wanted
        PointerMotionHintMask	    Pointer motion hints wanted
        Button1MotionMask	        Pointer motion while button 1 down
        Button2MotionMask	        Pointer motion while button 2 down
        Button3MotionMask	        Pointer motion while button 3 down
        Button4MotionMask	        Pointer motion while button 4 down
        Button5MotionMask	        Pointer motion while button 5 down
        ButtonMotionMask	        Pointer motion while any button down
        KeymapStateMask	            Keyboard state wanted at window entry and focus in
        ExposureMask	            Any exposure wanted
        VisibilityChangeMask	    Any change in visibility wanted
        StructureNotifyMask	        Any change in window structure wanted
        ResizeRedirectMask	        Redirect resize of this window
        SubstructureNotifyMask	    Substructure notification wanted
        SubstructureRedirectMask	Redirect structure requests on children
        FocusChangeMask	            Any change in input focus wanted
        PropertyChangeMask	        Any change in property wanted
        ColormapChangeMask	        Any change in colormap wanted
        OwnerGrabButtonMask	        Automatic grabs should activate with owner_events set to True

        --> TODO: Calculate mask from given events list

        :param events: List of events to be notified on
        :param mask: Events mask according to selected events
        :param callback: Function to be invoked when a selected event is received
        :param winId: id of window whose events must be watched
        """
        if not winId:
            winId = self.winId
        eventsObject = self._CheckEvents(winId, self.display, self.root, events, mask, callback)
        return eventsObject


def _getWindowParent(win: XWindow, rootId: int) -> int:
    while True:
        parent = win.query_tree().parent
        if parent.id == rootId or parent == 0:
            break
        win = parent
    return win.id


def _getWindowGeom(win: XWindow, rootId: int = defaultRoot.id) -> Tuple[int, int, int, int]:
    # https://stackoverflow.com/questions/12775136/get-window-position-and-size-in-python-with-xlib - mgalgs
    geom = win.get_geometry()
    x = geom.x
    y = geom.y
    while True:
        parent = win.query_tree().parent
        if not isinstance(parent, XWindow):
            break
        pgeom = parent.get_geometry()
        x += pgeom.x
        y += pgeom.y
        if parent.id == rootId:
            break
        win = parent
    w = geom.width
    h = geom.height
    return x, y, w, h


def _xlibGetAllWindows(parent: Union[XWindow, None] = None, title: str = "", klass: Union[Tuple[str, str], None] = None) -> List[XWindow]:
    """
    Retrieves all open windows, including "system", non-user windows (unlike getClientList() or getClientListStacking()).

    :param parent: parent window to limit the search to its children. Defaults to root window
    :param title: include only windows that match given title
    :param klass: include only windows that match given class
    :return: List of windows objects (X-Window)
    """

    parent = parent or defaultRoot
    allWindows = []

    def findit(hwnd: XWindow) -> None:
        try:
            query = hwnd.query_tree()
            children = query.children
        except:
            children = []
        for child in children:
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
    return allWindows


def _getPropertyValue(display: Xlib.display.Display, ret: Union[Xlib.protocol.request.GetProperty, None],
                      text: bool = False) -> Union[List[int], List[str], None]:
    # Can also ask for getattr(ret, "value")[0] to check returned data format, but don't see much benefit
    if ret and hasattr(ret, "value"):
        res: Union[List[int], List[str], None] = ret.value
        if isinstance(res, bytes):
            result: List[int] = ret.value.decode().split("\x00")
            if result and isinstance(res, list) and res[-1] == "":
                return result[:-1]
        elif isinstance(res, Iterable) and not isinstance(res, str):
            if text:
                result2: List[str] = []
                for a in ret.value:
                    if isinstance(a, int) and a != 0:
                        result2.append(display.get_atom_name(a))
                return res
            else:
                result3: List[int] = [a for a in ret.value]
                return result3
        if res and (isinstance(res, int) or isinstance(res, str)):
            return [res]
        return res
    return None


def _getProperty(display: Xlib.display.Display, window: XWindow, prop: Union[str, int],
                 prop_type: int = Xlib.X.AnyPropertyType) -> Union[Xlib.protocol.request.GetProperty, None]:

    if isinstance(prop, str):
        prop = display.get_atom(prop, False)

    if prop != 0:
        return window.get_full_property(prop, Xlib.X.AnyPropertyType)
    return None


def _changeProperty(display: Xlib.display.Display, window: XWindow, prop: Union[str, int], data: List[int],
                    propMode: int = Xlib.X.PropModeReplace):
    if isinstance(prop, str):
        prop = display.get_atom(prop, True)

    if prop != 0:
        # I think (to be confirmed) that 16 is not used in Python (no difference between short and long int)
        if isinstance(data, str):
            dataFormat: int = 8
        else:
            data = (data + [0] * (5 - len(data)))[:5]
            dataFormat = 32

        window.change_property(prop, Xlib.Xatom.ATOM, dataFormat, data, propMode)
        display.flush()


def _sendMessage(display: Xlib.display.Display, root: XWindow, winId: int, prop: Union[str, int],
                 data: Union[List[int], str]):
    if isinstance(prop, str):
        prop = display.get_atom(prop, True)

    if prop != 0:
        # I think (to be confirmed) that 16 is not used in Python (no difference between short and long int)
        if isinstance(data, str):
            dataFormat: int = 8
        else:
            data = (data + [0] * (5 - len(data)))[:5]
            dataFormat = 32

        ev: Xlib.protocol.event.ClientMessage = Xlib.protocol.event.ClientMessage(window=winId, client_type=prop,
                                                                                  data=(dataFormat, data))
        mask: int = Xlib.X.SubstructureRedirectMask | Xlib.X.SubstructureNotifyMask
        root.send_event(event=ev, event_mask=mask)
        display.flush()


def _createSimpleWindow(display: Xlib.display.Display, parent: XWindow, x: int, y: int, width: int, height: int,
                        override: bool = False, inputOnly: bool = False) -> Window:
    if inputOnly:
        mask = Xlib.X.ButtonPressMask | Xlib.X.ButtonReleaseMask | Xlib.X.KeyPressMask | Xlib.X.KeyReleaseMask
    else:
        mask = Xlib.X.NoEventMask
    win: XWindow = parent.create_window(x=x, y=y, width=width, height=height,
                                        border_width=0, depth=Xlib.X.CopyFromParent,
                                        window_class=Xlib.X.InputOutput,
                                        # window_class=Xlib.X.InputOnly,  # -> This fails!
                                        visual=Xlib.X.CopyFromParent,
                                        background_pixel=Xlib.X.CopyFromParent,
                                        event_mask=mask,
                                        colormap=Xlib.X.CopyFromParent,
                                        override_redirect=override,
                                        )
    win.map()
    display.flush()
    window: Window = Window(win.id)
    return window


def _createTransient(display: Xlib.display.Display, parent: XWindow, transient_for: XWindow,
                     callback: Callable[[Xlib.protocol.rq.Event], None], x: int, y: int, width: int, height: int,
                     override: bool = False, inputOnly: bool = False) \
        -> Tuple[Window, Union[_Extensions._CheckEvents, None], Union[Xlib.protocol.rq.DictWrapper, None]]:
    # https://shallowsky.com/blog/programming/click-thru-translucent-update.html
    # https://github.com/python-xlib/python-xlib/issues/200

    window: Window = _createSimpleWindow(display, parent, x, y, width, height, override, inputOnly)
    win: XWindow = window.xWindow

    onebyte = int(0x01)  # Calculate as 0xff * target_opacity
    fourbytes = onebyte | (onebyte << 8) | (onebyte << 16) | (onebyte << 24)
    win.change_property(display.get_atom('_NET_WM_WINDOW_OPACITY'), Xlib.Xatom.CARDINAL, 32, [fourbytes])

    input_pm = win.create_pixmap(width, height, 1)
    gc = input_pm.create_gc(foreground=0, background=0)
    input_pm.fill_rectangle(gc.id, 0, 0, width, height)
    win.shape_mask(Xlib.ext.shape.SO.Set, Xlib.ext.shape.SK.Input, 0, 0, input_pm)  # type: ignore[attr-defined]
    # win.shape_select_input(0)  # type: ignore[attr-defined]

    win.map()
    display.flush()

    win.set_wm_transient_for(transient_for)
    display.flush()

    checkEvents = None
    currDesktop = os.environ['XDG_CURRENT_DESKTOP'].lower()
    # otherDesktop = os.environ.get("DESKTOP_SESSION".lower())  # -> Returns None
    if "cinnamon" in currDesktop:
        # In Mint/Cinnamon the transient window is not placing itself in the same coordinates that its transient_for window
        pgeom = transient_for.get_geometry()
        win.configure(x=x-2, y=y-32, width=pgeom.width + 40 + 6, height=pgeom.height + 80 + 32)
        display.flush()

        checkEvents = window.extensions.checkEvents(
            [Xlib.X.ConfigureNotify],
            Xlib.X.StructureNotifyMask | Xlib.X.SubstructureNotifyMask,
            callback,
            transient_for.id
        )
        checkEvents.start()

    elif "kde" in currDesktop:
        # TODO: KDE has a totally different behavior. Must investigate/test
        pass

    normal_hints = transient_for.get_wm_normal_hints()
    window.changeProperty(display.get_atom("_MOTIF_WM_HINTS"), [1, 0, 1, 0, 0])
    # flags = normal_hints.flags | Xlib.Xutil.PMinSize | Xlib.Xutil.PMaxSize
    flags = 808  # Empirically found... no idea about how to calculate it in Python
    transient_for.set_wm_normal_hints(flags=flags, min_width=width, max_width=width, min_height=height, max_height=height)
    win.set_wm_normal_hints(flags=flags, min_width=width, max_width=width, min_height=height, max_height=height)
    window.changeWmState(Props.Window.State.Action.ADD, Props.Window.State.MODAL)

    return window, checkEvents, normal_hints


def _closeTransient(display: Xlib.display.Display, transientWindow: Window, checkEvents: Union[_Extensions._CheckEvents, None], transient_for: XWindow, normal_hints: Union[Xlib.protocol.rq.DictWrapper, None]):
    if checkEvents is not None:
        checkEvents.stop()
    transientWindow.xWindow.unmap()  # It seems not to properly close if not unmapped first
    display.flush()
    transientWindow.setClosed()
    if normal_hints is not None:
        transient_for.set_wm_normal_hints(normal_hints)
        display.flush()


# from ctypes import cdll
# from ctypes.util import find_library

# class _XWindowAttributes(Structure):
#     _fields_ = [('x', c_int32), ('y', c_int32),
#                 ('width', c_int32), ('height', c_int32), ('border_width', c_int32),
#                 ('depth', c_int32), ('visual', c_ulong), ('root', c_ulong),
#                 ('class', c_int32), ('bit_gravity', c_int32),
#                 ('win_gravity', c_int32), ('backing_store', c_int32),
#                 ('backing_planes', c_ulong), ('backing_pixel', c_ulong),
#                 ('save_under', c_int32), ('colourmap', c_ulong),
#                 ('mapinstalled', c_uint32), ('map_state', c_uint32),
#                 ('all_event_masks', c_ulong), ('your_event_mask', c_ulong),
#                 ('do_not_propagate_mask', c_ulong), ('override_redirect', c_int32), ('screen', c_ulong)]
#
# def XlibAttributes(self) -> tuple[bool, _XWindowWrapper._XWindowAttributes]:
#     attr = _XWindowWrapper._XWindowAttributes()
#     try:
#         if self.xlib is None:
#             x11 = find_library('X11')
#             self.xlib = cdll.LoadLibrary(str(x11))
#         d = self.xlib.XOpenDisplay(0)
#         self.xlib.XGetWindowAttributes(d, self.id, byref(attr))
#         self.xlib.XCloseDisplay(d)
#         resOK = True
#     except:
#         resOK = False
#     return resOK, attr
#
#     # Leaving this as reference of using X11 library
#     # https://github.com/evocount/display-management/blob/c4f58f6653f3457396e44b8c6dc97636b18e8d8a/displaymanagement/rotation.py
#     # https://github.com/nathanlopez/Stitch/blob/master/Configuration/mss/linux.py
#     # https://gist.github.com/ssokolow/e7c9aae63fb7973e4d64cff969a78ae8
#     # https://stackoverflow.com/questions/36188154/get-x11-window-caption-height
#     # https://refspecs.linuxfoundation.org/LSB_1.3.0/gLSB/gLSB/libx11-ddefs.html
#     # s = xlib.XDefaultScreen(d)
#     # root = xlib.XDefaultRootWindow(d)
#     # fg = xlib.XBlackPixel(d, s)
#     # bg = xlib.XWhitePixel(d, s)
#     # w = xlib.XCreateSimpleWindow(d, root, 600, 300, 400, 200, 0, fg, bg)
#     # xlib.XMapWindow(d, w)
#     # time.sleep(4)
#     # a = xlib.XInternAtom(d, "_GTK_FRAME_EXTENTS", True)
#     # if not a:
#     #     a = xlib.XInternAtom(d, "_NET_FRAME_EXTENTS", True)
#     # t = c_int()
#     # f = c_int()
#     # n = c_ulong()
#     # b = c_ulong()
#     # xlib.XGetWindowProperty(d, w, a, 0, 4, False, Xlib.X.AnyPropertyType, byref(t), byref(f), byref(n), byref(b), byref(attr))
#     # r = c_ulong()
#     # x = c_int()
#     # y = c_int()
#     # w = c_uint()
#     # h = c_uint()
#     # b = c_uint()
#     # d = c_uint()
#     # xlib.XGetGeometry(d, hWnd.id, byref(r), byref(x), byref(y), byref(w), byref(h), byref(b), byref(d))
#     # print(x, y, w, h)
#     # Other references (send_event and setProperty):
#     # prop = DISP.intern_atom(WM_CHANGE_STATE, False)
#     # data = (32, [Xlib.Xutil.IconicState, 0, 0, 0, 0])
#     # ev = Xlib.protocol.event.ClientMessage(window=self._hWnd.id, client_type=prop, data=data)
#     # mask = Xlib.X.SubstructureRedirectMask | Xlib.X.SubstructureNotifyMask
#     # DISP.send_event(destination=ROOT, event=ev, event_mask=mask)
#     # data = [Xlib.Xutil.IconicState, 0, 0, 0, 0]
#     # _setProperty(_type="WM_CHANGE_STATE", data=data, mask=mask)
#     # for atom in w.list_properties():
#     #     print(DISP.atom_name(atom))
#     # props = DISP.xrandr_list_output_properties(output)
#     # for atom in props.atoms:
#     #     print(atom, DISP.get_atom_name(atom))
#     #     print(DISP.xrandr_get_output_property(output, atom, 0, 0, 1000)._data['value'])


def main():
    print("ALL DISPLAYS")
    print(getAllDisplaysInfo())
    root = RootWindow()
    print("DESKTOP LAYOUT")
    print(root.getDesktopLayout())
    print("NUMBER OF DESKTOPS")
    print(root.getNumberOfDesktops())
    print("CLIENT LIST")
    print(root.getClientList())
    print("CLIENT LIST STACKING")
    print(root.getClientListStacking())
    print("SUPPORTED HINTS")
    print(root.getSupported(True))
    print("DESKTOP GEOMETRY")
    print(root.getDesktopGeometry())
    print("DESKTOP NAMES")
    print(root.getDesktopNames())
    print("DESKTOP VIEWPORT")
    print(root.getDesktopViewport())
    print("SHOWING DESKTOP")
    print(root.getShowingDesktop())
    print("SUPPORTING WM CHECK")
    print(root.getSupportingWMCheck())
    w = root.getActiveWindow()
    if w:
        print("REQ FRAME EXTENTS")
        print(root.requestFrameExtents(w))
        win = Window(w)
        print("NAME", win.getName())
        print("TYPE", win.getWmWindowType())
        print("TYPE STR", win.getWmWindowType(text=True))
        print("STATE", win.getWmState())
        print("STATE STR", win.getWmState(text=True))
        print("ALLOWED ACTIONS", win.getAllowedActions(True))
        print("PID", win.getPid())
        print("FRAME EXT", win.getFrameExtents())
        # These are returning None... is it OK???
        print("STRUT", win.getStrut())
        print("STRUT PARTIAL", win.getStrutPartial())
        print("ICON GEOM", win.getIconGeometry())
        print("HANDLED ICONS", win.getHandledIcons())
        print("USER TIME", win.getUserTime())

        print("MOVING/RESIZING")
        root.setMoveResize(w, x=100, y=100, width=800, height=600, userAction=True)  # Equivalent to win.setMoveResize()

        def callback(event):
            print("EVENT RECEIVED", event)

        eventLoop = win.extensions.checkEvents([Xlib.X.ConfigureNotify],
                                               Xlib.X.StructureNotifyMask | Xlib.X.SubstructureNotifyMask,
                                               callback)
        eventLoop.start()

        print("BELOW ON")
        win.changeWmState(Props.Window.State.Action.ADD, Props.Window.State.BELOW)
        time.sleep(4)
        print("BELOW OFF")
        win.changeWmState(Props.Window.State.Action.REMOVE, Props.Window.State.BELOW)
        time.sleep(4)
        print("DESKTOP")
        win.setWmWindowType(Props.Window.WindowType.DESKTOP)
        time.sleep(4)
        print("NORMAL")
        win.setWmWindowType(Props.Window.WindowType.NORMAL)
        print("MAX HORZ ON")
        win.setMaximized(True, False)
        time.sleep(4)
        print("MAX HORZ OFF")
        win.setMaximized(False, False)
        time.sleep(4)
        print("MAX")
        win.setMaximized(True, True)
        time.sleep(4)
        print("MAX HORZ OFF")
        win.setMaximized(False, True)
        time.sleep(4)
        print("MAX OFF")
        win.setMaximized(False, False)
        time.sleep(4)
        print("ICONIFY")
        win.setMinimized()
        time.sleep(4)
        print("RESTORE")
        win.setActive()
        time.sleep(4)
        print("END EVENT LOOP")
        eventLoop.stop()

        print("WM HINTS")
        print(win.extensions.getWmHints())
        print("WM NORMAL HINTS")
        print(win.extensions.getWmNormalHints())
        print("WM PROTOCOLS")
        print(win.extensions.getWmProtocols(True))
        print("REQUEST CLOSE")
        root.setClosed(win.id)  # equivalent to w.setClosed(), but accepts any window id


if __name__ == "__main__":
    main()
