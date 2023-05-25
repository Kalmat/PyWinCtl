from __future__ import annotations

import sys
assert sys.platform == "linux"

import array
import os
import threading
import time
from enum import Enum, IntEnum
from typing import Optional, cast, Callable, Union, List, Tuple, Iterable

from typing_extensions import TypedDict

from ctypes import cdll, Structure, c_int32, c_ulong, c_uint32, byref, CDLL
from ctypes.util import find_library

import Xlib.display
import Xlib.protocol
import Xlib.X
import Xlib.Xatom
import Xlib.Xutil
import Xlib.ext
import Xlib.xobject
from Xlib.protocol.rq import Struct
from Xlib.xobject.drawable import Window as XWindow


defaultDisplay = Xlib.display.Display()
defaultScreen = defaultDisplay.screen()
defaultRoot = defaultScreen.root


class Props:

    class Root(Enum):
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
        # Additional Root properties (always related to a specific window)
        CLOSE = "_NET_CLOSE_WINDOW"
        MOVERESIZE = "_NET_MOVERESIZE_WINDOW"
        WM_MOVERESIZE = "_NET_WM_MOVERESIZE"
        RESTACK = "_NET_RESTACK_WINDOW"
        REQ_FRAME_EXTENTS = "_NET_REQUEST_FRAME_EXTENTS"
        # WM_PROTOCOLS messages
        PROTOCOLS = "WM_PROTOCOLS"
        PING = "_NET_WM_PING"
        SYNC = "_NET_WM_SYNC_REQUEST"

    class DesktopLayout(IntEnum):
        ORIENTATION_HORZ = 0
        ORIENTATION_VERT = 1
        TOPLEFT = 0
        TOPRIGHT = 1
        BOTTOMRIGHT = 2
        BOTTOMLEFT = 3

    class Window(Enum):
        NAME = "_NET_WM_NAME"
        VISIBLE_NAME = "_NET_WM_VISIBLE_NAME"
        ICON_NAME = "_NET_WM_ICON_NAME"
        VISIBLE_ICON_NAME = "_NET_WM_VISIBLE_ICON_NAME"
        DESKTOP = "_NET_WM_DESKTOP"
        WM_WINDOW_TYPE = "_NET_WM_WINDOW_TYPE"
        CHANGE_STATE = "WM_CHANGE_STATE"
        WM_STATE = "_NET_WM_STATE"
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
        WM_MOVERESIZE = "_NET_WM_MOVERESIZE"
        RESTACK = "_NET_RESTACK_WINDOW"
        REQ_FRAME_EXTENTS = "_NET_REQUEST_FRAME_EXTENTS"
        OPAQUE_REGION = "_NET_WM_OPAQUE_REGION"
        BYPASS_COMPOSITOR = "_NET_WM_BYPASS_COMPOSITOR"

    class WindowType(Enum):
        DESKTOP = "_NET_WM_WINDOW_TYPE_DESKTOP"
        DOCK = "_NET_WM_WINDOW_TYPE_DOCK"
        TOOLBAR = "_NET_WM_WINDOW_TYPE_TOOLBAR"
        MENU = "_NET_WM_WINDOW_TYPE_MENU"
        UTILITY = "_NET_WM_WINDOW_TYPE_UTILITY"
        SPLASH = "_NET_WM_WINDOW_TYPE_SPLASH"
        DIALOG = "_NET_WM_WINDOW_TYPE_DIALOG"
        NORMAL = "_NET_WM_WINDOW_TYPE_NORMAL"

    class State(Enum):
        NULL = "0"
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

    class StateAction(IntEnum):
        REMOVE = 0
        ADD = 1
        TOGGLE = 2

    class MoveResize(IntEnum):
        SIZE_TOPLEFT = 0
        SIZE_TOP = 1
        SIZE_TOPRIGHT = 2
        SIZE_RIGHT = 3
        SIZE_BOTTOMRIGHT = 4
        SIZE_BOTTOM = 5
        SIZE_BOTTOMLEFT = 6
        SIZE_LEFT = 7
        MOVE = 8  # movement only
        SIZE_KEYBOARD = 9  # size via keyboard
        MOVE_KEYBOARD = 10  # move via keyboard

    class DataFormat(IntEnum):
        STR = 8
        INT = 32

    class Mode(IntEnum):
        REPLACE = Xlib.X.PropModeReplace
        APPEND = Xlib.X.PropModeAppend
        PREPEND = Xlib.X.PropModePrepend

    class StackMode(IntEnum):
        ABOVE = Xlib.X.Above
        BELOW = Xlib.X.Below

    class HintAction(IntEnum):
        KEEP = -1
        REMOVE = -2


class Structs:
    """
    Aimed to facilitate understanding and handling replies data structures and fields
    """

    class ScreensInfo(TypedDict):
        screen_number: str
        is_default: bool
        screen: Struct
        root: XWindow

    class DisplaysInfo(TypedDict):
        name: str
        is_default: bool
        screens: List[Structs.ScreensInfo]

    """
    Perhaps unnecesary since structs below are defined in Xlib.xobject.icccm.*, though in a more complex way.
    """
    class WmHints(TypedDict):
        # {'flags': 103, 'input': 1, 'initial_state': 1, 'icon_pixmap': <Pixmap 0x02a22304>, 'icon_window': <Window 0x00000000>, 'icon_x': 0, 'icon_y': 0, 'icon_mask': <Pixmap 0x02a2230b>, 'window_group': <Window 0x02a00001>}
        flags: int
        input_mode: int
        initial_state: int
        icon_pixmap: Xlib.xobject.drawable.Pixmap
        icon_window: Xlib.xobject.drawable.Window
        icon_x: int
        icon_y: int
        icon_mask: Xlib.xobject.drawable.Pixmap
        window_group: Xlib.xobject.drawable.Window

    class Aspect(TypedDict):
        num: int
        denum: int

    class WmNormalHints(TypedDict):
        # {'flags': 848, 'min_width': 387, 'min_height': 145, 'max_width': 0, 'max_height': 0, 'width_inc': 9, 'height_inc': 18, 'min_aspect': <class 'Xlib.protocol.rq.DictWrapper'>({'num': 0, 'denum': 0}), 'max_aspect': <class 'Xlib.protocol.rq.DictWrapper'>({'num': 0, 'denum': 0}), 'base_width': 66, 'base_height': 101, 'win_gravity': 1}
        flags: int
        min_width: int
        min_height: int
        max_width: int
        max_height: int
        width_inc: int
        height_inc: int
        min_aspect: Structs.Aspect
        max_aspect: Structs.Aspect
        base_width: int
        base_height: int
        win_gravity: int

    class _XWindowAttributes(Structure):
        _fields_ = [('x', c_int32), ('y', c_int32),
                    ('width', c_int32), ('height', c_int32), ('border_width', c_int32),
                    ('depth', c_int32), ('visual', c_ulong), ('root', c_ulong),
                    ('class', c_int32), ('bit_gravity', c_int32),
                    ('win_gravity', c_int32), ('backing_store', c_int32),
                    ('backing_planes', c_ulong), ('backing_pixel', c_ulong),
                    ('save_under', c_int32), ('colourmap', c_ulong),
                    ('mapinstalled', c_uint32), ('map_state', c_uint32),
                    ('all_event_masks', c_ulong), ('your_event_mask', c_ulong),
                    ('do_not_propagate_mask', c_ulong), ('override_redirect', c_int32), ('screen', c_ulong)]


def getAllDisplaysInfo() -> dict[str, Structs.DisplaysInfo]:
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
    dspInfo: dict[str, Structs.DisplaysInfo] = {}
    for d in displays:
        if d.startswith("X"):
            name: str = ":" + d[1:]
            display: Xlib.display.Display = Xlib.display.Display(name)
            screens: List[Structs.ScreensInfo] = []
            for s in range(display.screen_count()):
                try:
                    screen: Struct = display.screen(s)
                    screenInfo: Structs.ScreensInfo = {
                        "screen_number": str(s),
                        "is_default": (screen.root.id == defaultRoot.id),
                        "screen": screen,
                        "root": screen.root
                    }
                    screens.append(screenInfo)
                except:
                    pass
            displayInfo: Structs.DisplaysInfo = {
                "name": name,
                "is_default": (display.get_display_name() == defaultDisplay.get_display_name()),
                "screens": screens
            }
            display.close()
            dspInfo[name] = displayInfo
    return dspInfo


def getDisplayFromWindow(winId: int) -> Tuple[Xlib.display.Display, Struct, XWindow]:
    """
    Gets display connection, screen and root window from a given window id to which it belongs

    :param winId: id of the window
    :return: tuple containing display connection, screen struct and root window
    """
    # res, attr = _XlibAttributes(winId)
    # if res and hasattr(attr, "root"):
    #     return getDisplayFromRoot(attr.root)
    # else:
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
                atom: int = display.get_atom(Props.Root.CLIENT_LIST.value)
                for s in range(display.screen_count()):
                    try:
                        scr: Struct = display.screen(s)
                        r: XWindow = scr.root
                        ret: Optional[Xlib.protocol.request.GetProperty] = r.get_full_property(atom, Xlib.X.AnyPropertyType)
                        if ret and hasattr(ret, "value"):
                            if winId in ret.value:
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


def getProperty(window: XWindow, prop: Union[str, int], prop_type: int = Xlib.X.AnyPropertyType, sizehint: int = 10,
                display: Xlib.display.Display = defaultDisplay) -> Optional[Xlib.protocol.request.GetProperty]:
    """
    Get given window/root property

    :param window: window from which get the property
    :param prop: property to retrieve as int or str (will be translated to int)
    :param prop_type: property type (e.g. Xlib.X.AnyPropertyType or Xlib.Xatom.ATOM)
    :param sizehint: Expected data length hint (defaults to 10)
    :param display: display to which window belongs to (defaults to default display)
    :return: Xlib.protocol.request.GetProperty struct or None (property couldn't be obtained)
    """
    if isinstance(prop, str):
        prop = display.get_atom(prop)

    if isinstance(prop, int) and prop != 0:
        return window.get_full_property(prop, prop_type, sizehint)
    return None


def changeProperty(window: XWindow, prop: Union[str, int], data: Union[List[int], str],
                   prop_type: int = Xlib.Xatom.ATOM, propMode: int = Xlib.X.PropModeReplace,
                   display: Xlib.display.Display = defaultDisplay):
    """
    Change given window/root property

    :param window: window to which change the property
    :param prop: property to change as int or str (will be translated to int)
    :param data: data of the property as string or List of int (atoms)
    :param prop_type: property type (e.g. Xlib.Xatom.STRING or Xlib.Xatom.ATOM)
    :param propMode: Property mode: APPEND/PREPEND/REPLACE (defaults to Xlib.X.PropModeReplace)
    :param display: display to which window belongs to (defaults to default display)
    """
    if isinstance(prop, str):
        prop = display.get_atom(prop)

    if isinstance(prop, int) and prop != 0:
        # I think (to be confirmed) that 16 is not used in Python (no difference between short and long int)
        if isinstance(data, str):
            dataFormat: int = 8
            data = data.encode(encoding="utf-8")
        else:
            data = (data + [0] * (5 - len(data)))[:5]
            dataFormat = 32

        window.change_property(prop, prop_type, dataFormat, data, propMode)
        display.flush()


def sendMessage(winId: int, prop: Union[str, int], data: Union[List[int], str],
                display: Xlib.display.Display = defaultDisplay, root: XWindow = defaultRoot):
    """
    Send Client Message to given window/root

    :param winId: window id (int) to which send the message
    :param prop: property to change as int or str (will be translated to int)
    :param data: data of the message as string or list of int (atoms)
    :param display: display to which window belongs to (defaults to default display)
    :param root: root to which window is placed (defaults to default root)
    """
    if isinstance(prop, str):
        prop = display.get_atom(prop)

    if isinstance(prop, int) and prop != 0:
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


def getPropertyValue(prop: Optional[Xlib.protocol.request.GetProperty], text: bool = False,
                     display: Xlib.display.Display = defaultDisplay) -> Optional[Union[List[int], List[str]]]:
    """
    Extract data from retrieved window/root property

    :param prop: Xlib.protocol.request.GetProperty struct from which extract data
    :param text: set to ''True'' to convert the atoms (int) to their names (str)
    :param display: display to which window belongs to (defaults to default display)
    :return: extracted property data (as a list of integers or strings) or None
    """
    if prop is not None:
        # Value is either bytes (separated by '\x00' when multiple values) or array.array of integers.
        # The type of array values is stored in array.typecode ('I' in this case).
        valueData: Union[array.array[int], bytes] = prop.value
        if isinstance(valueData, bytes):
            resultStr: List[str] = [a for a in valueData.decode().split("\x00") if a]
            return resultStr
        elif isinstance(valueData, array.array):
            if text:
                resultStr = [display.get_atom_name(a) for a in valueData if isinstance(a, int) and a != 0]
                return resultStr
            else:
                resultInt: List[int] = [a for a in valueData]
                return resultInt
        # Leaving this to detect if data has an unexpected type
        return [a for a in valueData] if isinstance(valueData, Iterable) else [valueData]
    return None


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

    WM_PROTOCOLS messages (PING/SYNC) are accessible using wmProtocols subclass (RootWindow.wmProtocols.Ping/Sync)
    """

    def __init__(self, root: Optional[XWindow] = None):

        if root and root.id != defaultRoot.id:
            self.display, self.screen, self.root = getDisplayFromRoot(root.id)
        else:
            self.display = defaultDisplay
            self.screen = defaultScreen
            self.root = defaultRoot
        self.id: int = self.root.id
        self.wmProtocols = self._WmProtocols(self.display, self.root)

    def getProperty(self, prop: Union[str, int], prop_type: int = Xlib.X.AnyPropertyType, sizehint: int = 10) \
            -> Optional[Xlib.protocol.request.GetProperty]:
        """
        Retrieves given property from root

        :param prop: Property to query (int or str format)
        :param prop_type: Property type (e.g. X.AnyPropertyType or Xatom.STRING)
        :param sizehint: Expected data length
        :return: List of int, List of str or None (nothing obtained)
        """
        if isinstance(prop, str):
            prop = self.display.get_atom(prop)
        return getProperty(self.root, prop, prop_type, sizehint)

    def setProperty(self, prop: Union[str, int], data: Union[List[int], str]):
        """
        Sets the given property for root

        :param prop: property to set in int or str format. The property can be either an existing property, known and
         managed by the Window Manager, or completely new, non-previously existing property. In this last case, the
         Wndow Manager will store the property and return its values in a getProperty call but will also ignore it.
        :param data: Data related to given property, in List of int or str (like in name) format
        """
        sendMessage(self.root.id, prop, data, self.display, self.root)

    def sendMessage(self, winId: int, prop: Union[str, int], data: Union[List[int], str]):
        """
        Sends a ClientMessage event to given window

        :param winId: id of the target window
        :param prop: property/atom of the event in int or str format
        :param data: Data related to the event. It can be str or a list of up to 5 integers
        """
        sendMessage(winId, prop, data, self.display, self.root)

    def getSupportedHints(self, text: bool = False) -> Optional[Union[List[int], List[str]]]:
        """
        Returns the list of supported hints by the Window Manager.

        This property MUST be set by the Window Manager to indicate which hints it supports. For example:
        considering _NET_WM_STATE both this atom and all supported states e.g. _NET_WM_STATE_MODAL,
        _NET_WM_STATE_STICKY, would be listed. This assumes that backwards incompatible changes will not be made
        to the hints (without being renamed).

        :param text: if ''True'' the values will be returned as strings, or as integers if ''False''
        :return: supported hints as a list of strings / integers
        """
        return getPropertyValue(self.getProperty(Props.Root.SUPPORTED.value), text, self.display)

    def getClientList(self) -> Optional[List[int]]:
        """
        Returns the list of XWindows currently opened and managed by the Window Manager, ordered older-to-newer.

        These arrays contain all X Windows managed by the Window Manager. _NET_CLIENT_LIST has initial mapping order,
        starting with the oldest window. These properties SHOULD be set and updated by the Window Manager.

        :return: list of integers (XWindows id's)
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.CLIENT_LIST.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getClientListStacking(self) -> Optional[List[int]]:
        """
        Returns the list of XWindows currently opened and managed by the Window Manager, ordered in bottom-to-top.

        These arrays contain all X Windows managed by the Window Manager. _NET_CLIENT_LIST_STACKING has
        bottom-to-top stacking order. These properties SHOULD be set and updated by the Window Manager.

        :return: list of integers (XWindows id's)
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.CLIENT_LIST_STACKING.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getNumberOfDesktops(self) -> Optional[int]:
        """
        This property SHOULD be set and updated by the Window Manager to indicate the number of virtual desktops.

        :return: number of desktops in int format or None
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.NUMBER_OF_DESKTOPS.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
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
        self.setProperty(Props.Root.NUMBER_OF_DESKTOPS.value, [number])

    def getDesktopGeometry(self) -> Optional[List[int]]:
        """
        Array of two cardinals that defines the common size of all desktops (this is equal to the screen size if the
        Window Manager doesn't support large desktops, otherwise it's equal to the virtual size of the desktop).
        This property SHOULD be set by the Window Manager.

        :return: tuple of integers (width, height) or None if it couldn't be retrieved
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.DESKTOP_GEOMETRY.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)
        return res

    def setDesktopGeometry(self, newWidth: int, newHeight: int):
        """
        Array of two cardinals that defines the common size of all desktops (this is equal to the screen size if the
        Window Manager doesn't support large desktops, otherwise it's equal to the virtual size of the desktop).
        This property SHOULD be set by the Window Manager.

        A Pager can request a change in the desktop geometry by sending a _NET_DESKTOP_GEOMETRY client message
        to the root window.

        The Window Manager MAY choose to ignore this message, in which case _NET_DESKTOP_GEOMETRY property will
        remain unchanged.

        :param newWidth: value for the new target desktop width
        :param newHeight: value for the new target desktop height
        """
        self.setProperty(Props.Root.DESKTOP_GEOMETRY.value, [newWidth, newHeight])

    def getDesktopViewport(self) -> Optional[List[Tuple[int, int]]]:
        """
        Array of pairs of cardinals that define the top left corner of each desktop's viewport.
        For Window Managers that don't support large desktops, this MUST always be set to (0,0).

        :return: list of int tuples or None (if the value couldn't be retrieved)
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.DESKTOP_VIEWPORT.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            result: List[Tuple[int, int]] = []
            for i in range(len(res)):
                if i % 2 != 0:
                    item: Tuple[int, int] = (res[i-1], res[i])
                    result.append(item)
        else:
            result = []
        return result

    def setDesktopViewport(self, newWidth: int, newHeight: int):
        """
        Array of pairs of cardinals that define the top left corner of each desktop's viewport.
        For Window Managers that don't support large desktops, this MUST always be set to (0,0).

        A Pager can request to change the viewport for the current desktop by sending a _NET_DESKTOP_VIEWPORT
        client message to the root window.
        The Window Manager MAY choose to ignore this message, in which case _NET_DESKTOP_VIEWPORT property will
        remain unchanged.
        """
        self.setProperty(Props.Root.DESKTOP_VIEWPORT.value, [newWidth, newHeight])

    def getCurrentDesktop(self) -> Optional[int]:
        """
        The index of the current desktop. This is always an integer between 0 and _NET_NUMBER_OF_DESKTOPS - 1.
        This MUST be set and updated by the Window Manager. If a Pager wants to switch to another virtual desktop,
        it MUST send a _NET_CURRENT_DESKTOP client message to the root window

        :return: index of current desktop in int format or None if couldn't be retrieved
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.CURRENT_DESKTOP.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res and isinstance(res[0], int):
            return res[0]
        return None

    def setCurrentDesktop(self, newDesktop: int):
        """
        Change the current desktop to the given desktop. The index of the current desktop is always an integer
        between 0 and _NET_NUMBER_OF_DESKTOPS - 1. This MUST be set and updated by the Window Manager. If a
        Pager wants to switch to another virtual desktop, it MUST send a _NET_CURRENT_DESKTOP client message to the root window

        :param newDesktop: Index of the target desktop
        """
        desks = self.getNumberOfDesktops()
        if desks and newDesktop < desks and newDesktop != self.getCurrentDesktop():
            self.setProperty(Props.Root.CURRENT_DESKTOP.value, [newDesktop, Xlib.X.CurrentTime])

    def getDesktopNames(self) -> Optional[List[str]]:
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
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.DESKTOP_NAMES.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[str], res)
        return res

    def getActiveWindow(self) -> Optional[int]:
        """
        The window ID of the currently active window or None if no window has the focus. This is a read-only
        property set by the Window Manager. If a Client wants to activate another window, it MUST send a
        _NET_ACTIVE_WINDOW client message to the root window:

        :return: window id or None
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.ACTIVE.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res and isinstance(res[0], int):
            return res[0]
        return None

    def getWorkArea(self) -> Optional[List[int]]:
        """
        This property MUST be set by the Window Manager upon calculating the work area for each desktop.
        Contains a geometry for each desktop. These geometries are specified relative to the viewport on each
        desktop and specify an area that is completely contained within the viewport. Work area SHOULD be used
        by desktop applications to place desktop icons appropriately.

        The Window Manager SHOULD calculate this space by taking the current page minus space occupied by dock
        and panel windows, as indicated by the _NET_WM_STRUT or _NET_WM_STRUT_PARTIAL properties set on client windows.

        :return: tuple containing workarea coordinates (x, y, width, height)
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.WORKAREA.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getSupportingWMCheck(self) -> Optional[List[int]]:
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
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.SUPPORTING_WM_CHECK.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getVirtualRoots(self) -> Optional[List[int]]:
        """
        To implement virtual desktops, some Window Managers reparent client windows to a child of the root window.
        Window Managers using this technique MUST set this property to a list of IDs for windows that are acting
        as virtual root windows. This property allows background setting programs to work with virtual roots and
        allows clients to figure out the window manager frame windows of their windows.

        :return: List of virtual roots id's as integers
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.VIRTUAL_ROOTS.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getDesktopLayout(self) -> Optional[List[int]]:
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.DESKTOP_LAYOUT.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)
        return res

    def setDesktopLayout(self, orientation: int, columns: int, rows: int, starting_corner: int):
        """
        Values (as per RootWindow.DesktopLayout):
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
        self.setProperty(Props.Root.DESKTOP_LAYOUT.value, [orientation, columns, rows, starting_corner])

    def getShowingDesktop(self) -> Optional[bool]:
        """
        Some Window Managers have a "showing the desktop" mode in which windows are hidden, and the desktop
        background is displayed and focused. If a Window Manager supports the _NET_SHOWING_DESKTOP hint, it
        MUST set it to a value of 1 when the Window Manager is in "showing the desktop" mode, and a value of
        zero if the Window Manager is not in this mode.

        :return: ''True'' if showing desktop
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Root.SHOWING_DESKTOP.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res:
            return res[0] != 0
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
            self.setProperty(Props.Root.SHOWING_DESKTOP.value, [1 if show else 0])

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
        self.sendMessage(winId, Props.Root.CLOSE.value, [Xlib.X.CurrentTime, 2 if userAction else 1])

    def setMoveResize(self, winId: int, gravity: int = 0, x: Optional[int] = None, y: Optional[int] = None, width: Optional[int] = None, height: Optional[int] = None, userAction: bool = True):
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
        # gravity_flags calculations from 'old' ewmh seem to be wrong
        # Thanks to elraymond (https://github.com/elraymond) for his help!
        gravity_flags = gravity
        if x is None:
            x = 0
        else:
            gravity_flags = gravity_flags | (1 << 8)
        if y is None:
            y = 0
        else:
            gravity_flags = gravity_flags | (1 << 9)
        if width is None:
            width = 0
        else:
            gravity_flags = gravity_flags | (1 << 10)
        if height is None:
            height = 0
        else:
            gravity_flags = gravity_flags | (1 << 11)
        if userAction:
            gravity_flags = gravity_flags | (1 << 12)
        else:
            gravity_flags = gravity_flags | (1 << 13)
        self.sendMessage(winId, Props.Root.MOVERESIZE.value, [gravity_flags, x, y, width, height])

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
        self.sendMessage(winId, Props.Root.WM_MOVERESIZE.value, [x_root, y_root, orientation, button, 2 if userAction else 1])

    def setWmStacking(self, winId: int, siblingId: int, mode: int, userAction: bool = True):
        """
        This request is similar to ConfigureRequest with CWSibling and CWStackMode flags. It should be used only by
        pagers, applications can use normal ConfigureRequests. The source indication field should be therefore
        set to 2, see the section called “Source indication in requests” for details.

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
        the user to bring a currently active window to the top and return it back when the window looses focus.

        Rationale: A Window Manager may put restrictions on configure requests from applications, for example it may
        under some conditions refuse to raise a window. This request makes it clear it comes from a pager or similar
        tool, and therefore the Window Manager should always obey it.

        If a sibling and a stack_mode are specified, the window is restacked as follows:

            Above	    The window is placed just above the sibling.
            Below	    The window is placed just below the sibling.
            TopIf	    If the sibling occludes the window, the window is placed at the top of the stack.
            BottomIf	If the window occludes the sibling, the window is placed at the bottom of the stack.
            Opposite	If the sibling occludes the window, the window is placed at the top of the stack. If the window occludes the sibling, the window is placed at the bottom of the stack.

        If a stack_mode is specified but no sibling is specified, the window is restacked as follows:

            Above	    The window is placed at the top of the stack.
            Below	    The window is placed at the bottom of the stack.
            TopIf	    If any sibling occludes the window, the window is placed at the top of the stack.
            BottomIf	If the window occludes any sibling, the window is placed at the bottom of the stack.
            Opposite	If any sibling occludes the window, the window is placed at the top of the stack. If the window occludes any sibling, the window is placed at the bottom of the stack.

        :param winId: id of window to be restacked
        :param siblingId: id of sibling window related to restacking action
        :param mode: Stacking mode as per table above
        :param userAction: set to ''True'' to force action, as if it was requested by a user action. Defaults to True
        """
        # Need to understand this property
        self.sendMessage(winId, Props.Root.RESTACK.value, [2 if userAction else 1, siblingId, mode])

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
        self.sendMessage(winId, Props.Root.REQ_FRAME_EXTENTS.value, [])

    class _WmProtocols:
        # Is all this necessary/interesting?
        # Besides, should they be included within RootWindow class or outside?

        def __init__(self, display: Xlib.display.Display, root: XWindow):
            self._display = display
            self._root = root

        def ping(self, winId: int):
            """
            This protocol allows the Window Manager to determine if the Client is still processing X events.
            This can be used by the Window Manager to determine if a window which fails to close after being
            sent WM_DELETE_WINDOW has stopped responding or has stalled for some other reason, such as waiting
            for user confirmation. A Client SHOULD indicate that it is willing to participate in this protocol
            by listing _NET_WM_PING in the WM_PROTOCOLS property of the client window.

            A Window Manager can use this protocol at any time by sending a client message as follows:

            type = ClientMessage
            window = the respective client window
            message_type = WM_PROTOCOLS
            format = 32
            data.l[0] = _NET_WM_PING
            data.l[1] = timestamp
            data.l[2] = the respective client window
            other data.l[] elements = 0

            A participating Client receiving this message MUST send it back to the root window immediately,
            by setting window = root, and calling XSendEvent with the same event mask like all other root
            window messages in this specification use. The Client MUST NOT alter any field in the event
            other than the window. This includes all 5 longs in the data.l[5] array. The Window Manager
            can uniquely identify the ping by the timestamp and the data.l[2] field if necessary. Note
            that some older clients may not preserve data.l[2] through data.l[4].

            The Window Manager MAY kill the Client (using _NET_WM_PID) if it fails to respond to this protocol
            within a reasonable time.

            See also the implementation notes on killing hung processes.
            """
            sendMessage(winId, self._display.get_atom(Props.Root.PROTOCOLS.value),
                        [self._display.get_atom(Props.Root.PING.value), Xlib.X.CurrentTime, winId], self._display,
                        self._root)

        def sync(self, winId: int, lowValue: int, highValue: int):
            """
            This protocol uses the XSync extension (see the protocol specification and the library documentation) to
            let client and window manager synchronize the repaint of the window manager frame and the client window.
            A client indicates that it is willing to participate in the protocol by listing _NET_WM_SYNC_REQUEST in
            the WM_PROTOCOLS property of the client window and storing the XID of an XSync counter in the property
            _NET_WM_SYNC_REQUEST_COUNTER. The initial value of this counter is not defined by this specification.

            A window manager uses this protocol by preceding a ConfigureNotify event sent to a client by a client
            message as follows:

            type = ClientMessage
            window = the respective client window
            message_type = WM_PROTOCOLS
            format = 32
            data.l[0] = _NET_WM_SYNC_REQUEST
            data.l[1] = timestamp
            data.l[2] = low 32 bits of the update request number
            data.l[3] = high 32 bits of the update request number
            other data.l[] elements = 0

            After receiving one or more such message/ConfigureNotify pairs, and having handled all repainting
            associated with the ConfigureNotify events, the client MUST set the _NET_WM_SYNC_REQUEST_COUNTER to
            the 64-bit number indicated by the data.l[2] and data.l[3] fields of the last client message received.

            By using either the Alarm or the Await mechanisms of the XSync extension, the window manager can
            know when the client has finished handling the ConfigureNotify events. The window manager SHOULD
            not resize the window faster than the client can keep up.

            The update request number in the client message is determined by the window manager subject to
            the restriction that it MUST NOT be 0. The number is generally intended to be incremented by one
            for each message sent. Since the initial value of the XSync counter is not defined by this specification,
            the window manager MAY set the value of the XSync counter at any time, and MUST do so when it first
            manages a new window.
            """
            sendMessage(winId, self._display.get_atom(Props.Root.PROTOCOLS.value),
                        [self._display.get_atom(Props.Root.SYNC.value), Xlib.X.CurrentTime, lowValue, highValue],
                        self._display, self._root)


defaultRootWindow = RootWindow()


class EwmhWindow:
    """
    Base class to access application windows related features.

    To instantiate this class only a window id is required. It's possible to retrieve this value in several ways:

    - Target a specific window using an external module (e.g. PyWinCtl.getAllWindowsWithTitle(title))

    - Retrieve it from your own application (e.g. PyQt's winId() or TKinter's frame())

    Note that, although a root is also a window, these methods will not likely work with it.

    Apart from given methods, there are some values you can use with python-xlib:

    - display: XDisplay connection

    - screen: screen Struct

    - root: root X Window object

    - rootWindow: object to access RootWindow methods

    - xWindow: X Window object associated to current window

    - id: current window's id

    Additional, non-EWMH features, related to low-level window properties like hints, protocols and events are
    available using extensions subclass (EwmhWindow.extensions.*)
    """

    def __init__(self, winId: int, root: XWindow = defaultRoot):

        self.root = root
        if root.id != defaultRoot.id:
            self.display, self.screen, _ = getDisplayFromRoot(root.id)
        else:
            self.display = defaultDisplay
            self.screen = defaultScreen
        self.rootWindow: RootWindow = defaultRootWindow if self.root.id == defaultRoot.id else RootWindow(self.root)
        self.xWindow: XWindow = self.display.create_resource_object('window', winId)
        self.id: int = winId
        self.extensions = _Extensions(winId, self.display, self.root)

        self._currDesktop = os.environ['XDG_CURRENT_DESKTOP'].lower()

    def getProperty(self, prop: Union[str, int], prop_type: int = Xlib.X.AnyPropertyType, sizehint: int = 10) \
            -> Optional[Xlib.protocol.request.GetProperty]:
        """
        Retrieves given property data from given window

        :param prop: Property to query (int or str format)
        :param prop_type: Property type (e.g. X.AnyPropertyType or Xatom.STRING)
        :param sizehint: Expected data length
        :return: List of int, List of str or None (nothing obtained)
        """
        if isinstance(prop, str):
            prop = self.display.get_atom(prop)
        return getProperty(self.xWindow, prop, prop_type, sizehint)

    def sendMessage(self, prop: Union[str, int], data: Union[List[int], str]):
        """
        Sends a ClientMessage event to current window

        :param prop: Property/atom of the event in int or str format
        :param data: Data related to the event. It can be str (format is 8) or a list of up to 5 integers (format is 32)
        """
        return sendMessage(self.id, prop, data)

    def changeProperty(self, prop: Union[str, int], data: Union[List[int], str],
                       prop_type: int = Xlib.Xatom.ATOM, propMode: Props.Mode = Props.Mode.REPLACE):
        """
        Sets given property for the current window. The property might be ignored by the Window Manager, but returned
        in getProperty() calls together with its data.

        :param prop: Property/atom of the event in int or str format
        :param data: Data related to the event. It can be a string or a list of up to 5 integers
        :param prop_type: Property type (e.g. X.AnyPropertyType or Xatom.STRING)
        :param propMode: whether to Replace/Append/Prepend (Props.Mode.*) the property in relation to the rest of
                    existing properties
        """
        changeProperty(self.xWindow, prop, data, prop_type, propMode.value, self.display)

    def getName(self) -> Optional[str]:
        """
        Get the name of the current window.
        Some windows may not have a title, the title may change or even this query may fail (e.g. for root windows)

        The Client SHOULD set this to the title of the window in UTF-8 encoding. If set, the Window Manager should
        use this in preference to WM_NAME.

        :return: name of the window as str or None (nothing obtained)
        """
        return self.xWindow.get_wm_name()

    def setName(self, name: str):
        """
        Change the name of the current window

        :param name: new name as string
        """
        self.xWindow.set_wm_name(name)

    def getVisibleName(self) -> Optional[str]:
        """
        Get the visible name of the current window.
        Some windows may not have a title, the title may change or even this query may fail (e.g. for root windows)

        If the Window Manager displays a window name other than _NET_WM_NAME the Window Manager MUST set this to
        the title displayed in UTF-8 encoding.
        Rationale: This property is for Window Managers that display a title different from the _NET_WM_NAME or
        WM_NAME of the window (i.e. xterm <1>, xterm <2>, ... is shown, but _NET_WM_NAME / WM_NAME is still xterm
        for each window) thereby allowing Pagers to display the same title as the Window Manager.

        :return: visible name of the window as str or None (nothing obtained)
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Window.VISIBLE_NAME.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res:
            return str(res[0])
        return None

    def setVisibleName(self, name: str):
        """
        Set the visible name of the current window

        :param name: new visible name as string
        """
        self.changeProperty(Props.Window.VISIBLE_NAME.value, name)

    def getIconName(self) -> Optional[str]:
        """
        Get the name of the window icon

        The Client SHOULD set this to the title of the icon for this window in UTF-8 encoding. If set, the Window
        Manager should use this in preference to WM_ICON_NAME.

        :return: icon name as string
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Xlib.Xatom.WM_ICON_NAME)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res:
            return str(res[0])
        return None

    def setIconName(self, name: str):
        """
        Change the name of the window icon

        :param name: new icon name as string
        """
        self.changeProperty(Xlib.Xatom.WM_ICON_NAME, name)

    def getVisibleIconName(self) -> Optional[str]:
        """
        Get the visible name of the window icon.

        If the Window Manager displays an icon name other than _NET_WM_ICON_NAME the Window Manager MUST set this
        to the title displayed in UTF-8 encoding.

        :return: visible icon name as string
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Window.VISIBLE_ICON_NAME.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res:
            return str(res[0])
        return None

    def setVisibleIconName(self, name: str):
        """
        Change the visible name of window icon

        :param name: new visible icon name as string
        """
        self.changeProperty(Props.Window.VISIBLE_ICON_NAME.value, name)

    def getDesktop(self) -> Optional[int]:
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
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Window.DESKTOP.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res and isinstance(res[0], int):
            return int(res[0])
        return None

    def setDesktop(self, newDesktop: int, userAction: bool = True):
        """
        Move the window to the given desktop

        :param newDesktop: target desktop index (as per getNumberOfDesktops())
        :param userAction: source indication (user or pager/manager action). Defaults to True
        """
        numDesktops: Optional[int] = self.rootWindow.getNumberOfDesktops()
        currDesktop: Optional[int] = self.rootWindow.getCurrentDesktop()
        if numDesktops is not None and 0 <= newDesktop <= numDesktops and currDesktop is not None and newDesktop != currDesktop:
            self.sendMessage(Props.Window.DESKTOP.value, [newDesktop, Xlib.X.CurrentTime, 2 if userAction else 1])

    def getWmWindowType(self, text: bool = False) -> Optional[Union[List[int], List[str]]]:
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
        return getPropertyValue(self.getProperty(Props.Window.WM_WINDOW_TYPE.value), text, self.display)

    def setWmWindowType(self, winType: Props.WindowType):
        """
        Changes the type of current window.

        See getWmWindowType() documentation for more information about window types.

        :param winType: target window type as WindowType (Props.WindowType.*)
        """
        x, y, w, h = _getWindowGeom(self.xWindow, self.root.id)
        self.xWindow.unmap()  # -> Needed in Mint/Cinnamon
        atom = self.display.get_atom(winType.value, True)
        self.changeProperty(Props.Window.WM_WINDOW_TYPE.value, [atom])
        self.xWindow.map()
        self.display.flush()
        self.setMoveResize(x=x, y=y, width=w, height=h)

    def getWmState(self, text: bool = False) -> Optional[Union[List[int], List[str]]]:
        """
        Get the window states values of current window.

        A list of hints describing the window Props.State. Atoms present in the list MUST be considered set, atoms not
        present in the list MUST be considered not set. The Window Manager SHOULD honor _NET_WM_STATE whenever a
        withdrawn window requests to be mapped. A Client wishing to change the state of a window MUST send a
        _NET_WM_STATE client message to the root window (see below). The Window Manager MUST keep this property
        updated to reflect the current state of the window.

        The Window Manager should remove the property whenever a window is withdrawn, but it should leave the
        property in place when it is shutting down, e.g. in response to losing ownership of the WM_Sn manager
        selection.

        Rationale: Removing the property upon window withdrawal helps legacy applications which want to reuse
        withdrawn windows. Not removing the property upon shutdown allows the next Window Manager to restore
        windows to their previous Props.State.

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
        The canonical example is that minimized windows should be in the _NET_WM_STATE_HIDDEN Props.State. Pagers and
        similar applications should use _NET_WM_STATE_HIDDEN instead of WM_STATE to decide whether to display a
        window in miniature representations of the windows on a desktop.

        Implementation note: if an Application asks to toggle _NET_WM_STATE_HIDDEN the Window Manager should
        probably just ignore the request, since _NET_WM_STATE_HIDDEN is a function of some other aspect of the
        window such as minimization, rather than an independent Props.State.

        _NET_WM_STATE_FULLSCREEN indicates that the window should fill the entire screen and have no window
        decorations. Additionally, the Window Manager is responsible for restoring the original geometry after
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
        return getPropertyValue(self.getProperty(Props.Window.WM_STATE.value), text, self.display)

    def changeWmState(self, action: Props.StateAction, state: Props.State, state2: Props.State = Props.State.NULL, userAction: bool = True):
        """
        Sets the window states values of current window.

        See setWmState() documentation for more information on Window States.

        This message allows two properties to be changed simultaneously, specifically to allow both horizontal
        and vertical maximization to be altered together. l[2] MUST be set to zero if only one property is to
        be changed. See the section called “Source indication in requests” for details on the source indication.
        l[0], the action, MUST be one of:

        _NET_WM_STATE_REMOVE        0    # remove/unset property
        _NET_WM_STATE_ADD           1    # add/set property
        _NET_WM_STATE_TOGGLE        2    # toggle property

        :param action: Action to perform with the state: ADD/REMOVE/TOGGLE (Props.StateAction.*)
        :param state: Target new state as State (Props.State.*)
        :param state2: Up to two states can be changed at once. Defaults to 0 (no second state to change).
        :param userAction: source indication (user or pager/manager action). Defaults to True
        """
        st1: int = self.display.get_atom(state.value)
        st2: int = self.display.get_atom(state2.value) if state2 != Props.State.NULL else 0
        self.sendMessage(self.display.get_atom(Props.Window.WM_STATE.value), [action.value, st1, st2, 2 if userAction else 1])

    def setMaximized(self, maxHorz: bool, maxVert: bool):
        """
        Set or unset the values of maximized states (horizontal/vertical), individually.

        :param maxHorz: ''True'' / ''False'' to indicate whether the window should be horizontally maximized or not
        :param maxVert: ''True'' / ''False'' to indicate whether the window should be vertically maximized or not
        """
        NULL = Props.State.NULL
        state1 = NULL
        state2 = NULL
        ret: Optional[Union[List[int], List[str]]] = self.getWmState(True)
        states: List[str] = [] if ret is None else [a for a in ret if a and isinstance(a, str)]
        if maxHorz and maxVert:
            if Props.State.MAXIMIZED_HORZ.value not in states:
                state1 = Props.State.MAXIMIZED_HORZ
            if Props.State.MAXIMIZED_VERT.value not in states:
                state2 = Props.State.MAXIMIZED_VERT
            if state1 or state2:
                self.changeWmState(Props.StateAction.ADD, state1 if state1 != NULL else state2, state2 if state1 != NULL else NULL)
        elif maxHorz:
            if Props.State.MAXIMIZED_HORZ.value not in states:
                state = Props.State.MAXIMIZED_HORZ
                self.changeWmState(Props.StateAction.ADD, state, NULL)
            if Props.State.MAXIMIZED_VERT.value in states:
                state = Props.State.MAXIMIZED_VERT
                self.changeWmState(Props.StateAction.REMOVE, state, NULL)
        elif maxVert:
            if Props.State.MAXIMIZED_HORZ.value in states:
                state = Props.State.MAXIMIZED_HORZ
                self.changeWmState(Props.StateAction.REMOVE, state, NULL)
            if Props.State.MAXIMIZED_VERT.value not in states:
                state = Props.State.MAXIMIZED_VERT
                self.changeWmState(Props.StateAction.ADD, state, NULL)
        else:
            if Props.State.MAXIMIZED_HORZ.value in states:
                state1 = Props.State.MAXIMIZED_HORZ
            if Props.State.MAXIMIZED_VERT.value in states:
                state2 = Props.State.MAXIMIZED_VERT
            if state1 or state2:
                self.changeWmState(Props.StateAction.REMOVE, state1 if state1 != NULL else state2, state2 if state1 != NULL else NULL)

    def setMinimized(self):
        """
        Set Iconified (minimized) state for current window

        Unlike maximized, this action can only be reverted by using setActive() method.
        """
        states = self.getWmState(True)
        if not states or (states and Props.State.HIDDEN.value not in states):
            atom = self.display.get_atom(Props.Window.CHANGE_STATE.value, True)
            self.sendMessage(atom, [Xlib.Xutil.IconicState])

    def getAllowedActions(self, text: bool = False) -> Optional[Union[List[int], List[str]]]:
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

        _NET_WM_ACTION_FULLSCREEN indicates that the window may be brought to fullscreen Props.State.

        _NET_WM_ACTION_CHANGE_DESKTOP indicates that the window may be moved between desktops.

        _NET_WM_ACTION_CLOSE indicates that the window may be closed (i.e. a WM_DELETE_WINDOW message may be sent).

        :param text: if ''True'', the actions will be returned in string format, or as integers if ''False''
        :return: List of integers or strings
        """
        return getPropertyValue(self.getProperty(Props.Window.ALLOWED_ACTIONS.value), text, self.display)

    # Can this be set??? If not, investigate hints and protocols, which might be related (e.g. 'WM_DELETE_WINDOW')
    # def setAllowedActions(self, newActions: Union[List[int], List[str]]):
    #     """
    #     Set the allowed actions of current window.
    #
    #     :param newActions: List of new actions allowed, in integer or string format
    #     """
    #     pass

    def getStrut(self) -> Optional[List[int]]:
        """
        This property is equivalent to a _NET_WM_STRUT_PARTIAL property where all start values are 0 and all
        end values are the height or width of the logical screen. _NET_WM_STRUT_PARTIAL was introduced later
        than _NET_WM_STRUT, however, so clients MAY set this property in addition to _NET_WM_STRUT_PARTIAL to
        ensure backward compatibility with Window Managers supporting older versions of the Specification.

        :return: List of integers (left, right, top, bottom) defining the width of the reserved area at each border of
        the screen
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Window.STRUT.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)
        return res

    def setStrut(self, left: int, right: int, top: int, bottom: int):
        """
        Set a new desktop strut (reserved space at the screen borders)

        See getStrut() and getStrutPartial() documentation for more info on this feature

        :param left: left coordinate of strut
        :param right: left coordinate of strut
        :param top: top coordinate of strut
        :param bottom: bottom coordinate of strut
        """
        # Need to understand this
        self.sendMessage(Props.Window.STRUT.value, [left, right, top, bottom])

    def getStrutPartial(self) -> Optional[List[int]]:
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
        extension. Assume that the set-up uses two monitors, one running at 1280x1024 and the other to the right
        running at 1024x768, with the top edge of the two physical displays aligned. If the panel wants to fill the
        entire bottom edge of the smaller display with a panel 50 pixels tall, it should set a bottom strut of 306,
        with bottom_start_x of 1280, and bottom_end_x of 2303. Note that the strut is relative to the screen edge,
        and not the edge of the xinerama monitor.

        Rationale: A simple "do not cover" hint is not enough for dealing with e.g. auto-hide panels.

        Notes: An auto-hide panel SHOULD set the strut to be its minimum, hidden size. A "corner" panel that does not
        extend for the full length of a screen border SHOULD only set one strut.

        :return: List of integers containing 4 cardinals specifying the width of the reserved area at each border of
        the screen, and an additional 8 cardinals specifying the beginning and end corresponding to each of the
        four struts. The order of the values is left, right, top, bottom, left_start_y, left_end_y, right_start_y,
        right_end_y, top_start_x, top_end_x, bottom_start_x, bottom_end_x
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Window.STRUT_PARTIAL.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)
        return res

    # Need to understand this / Can it be set and, if so, how to pass all those values???
    # def setStrutPartial(self, left: int, right: int, top: int, bottom: int,
    #                     left_start_y: int, left_end_y: int, right_start_y: int, right_end_y: int,
    #                     top_start_x: int, top_end_x: int, bottom_start_x: int, bottom_end_x: int):
    #     """
    #     Set new Strut Partial property.
    #
    #     See getStrutPartial() documentation for more information on this property.
    #     """
    #     pass

    def getIconGeometry(self) -> Optional[List[int]]:
        """
        Get the geometry of current window icon.

        This optional property MAY be set by stand-alone tools like a taskbar or an iconbox. It specifies the geometry
        of a possible icon in case the window is iconified.

        Rationale: This makes it possible for a Window Manager to display a nice animation like morphing the window
        into its icon.

        :return: List of integers containing the icon geometry or None (no obtained)
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Window.ICON_GEOMETRY.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getPid(self) -> Optional[int]:
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
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Window.PID.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res:
            return int(res[0])
        return None

    def getHandledIcons(self) -> Optional[List[int]]:
        """
        Get the id of icons handled by the window.

        This property can be set by a Pager on one of its own toplevel windows to indicate that the Window Manager
        need not provide icons for iconified windows, for example if it is a taskbar and provides buttons for
        iconified windows.

        :return: List of integers or None (not obtained)
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Window.HANDLED_ICONS.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getUserTime(self) -> Optional[List[int]]:
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
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Window.USER_TIME.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)

        return res

    def _getNetFrameExtents(self) -> Optional[Union[List[int], List[str]]]:
        return getPropertyValue(self.getProperty("_NET_FRAME_EXTENTS"))

    def _getGtkFrameExtents(self) -> Optional[Union[List[int], List[str]]]:
        return getPropertyValue(self.getProperty("_GTK_FRAME_EXTENTS"))

    def getFrameExtents(self) -> Optional[List[int]]:
        """
        Get the current window frame extents (space reserved by the window manager around window)

        The Window Manager MUST set _NET_FRAME_EXTENTS to the extents of the window's frame. left, right, top
        and bottom are widths of the respective borders added by the Window Manager.

        AUTHOR COMMENT: Since GNOME doesn't obey this rule, _GTK_FRAME_EXTENTS has been added to try to get
        the proper values (though, again, GNOME uses them in a very different way).

        :return: left, right, top, bottom
        """
        res: Optional[Union[List[int], List[str]]] = self._getNetFrameExtents() or self._getGtkFrameExtents()
        if res is not None:
            res = cast(List[int], res)
        return res

    def getOpaqueRegion(self) -> Optional[List[int]]:
        """
        The Client MAY set this property to a list of 4-tuples [x, y, width, height], each representing a rectangle
        in window coordinates where the pixels of the window's contents have a fully opaque alpha value. If the
        window is drawn by the compositor without adding any transparency, then such a rectangle will occlude
        whatever is drawn behind it. When the window has an RGB visual rather than an ARGB visual, this property
        is not typically useful, since the effective opaque region of a window is exactly the bounding region of
        the window as set via the shape extension. For windows with an ARGB visual and also a bounding region set
        via the shape extension, the effective opaque region is given by the intersection of the region set by this
        property and the bounding region set via the shape extension. The compositing manager MAY ignore this hint.

        Rationale: This gives the compositing manager more room for optimizations. For example, it can avoid drawing
        occluded portions behind the window.
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Window.OPAQUE_REGION.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res is not None:
            res = cast(List[int], res)
        return res

    def getBypassCompositor(self) -> Optional[int]:
        """
        The Client MAY set this property to a list of 4-tuples [x, y, width, height], each representing a rectangle
        in window coordinates where the pixels of the window's contents have a fully opaque alpha value. If the window
        is drawn by the compositor without adding any transparency, then such a rectangle will occlude whatever is
        drawn behind it. When the window has an RGB visual rather than an ARGB visual, this property is not typically
        useful, since the effective opaque region of a window is exactly the bounding region of the window as set via
        the shape extension. For windows with an ARGB visual and also a bounding region set via the shape extension,
        the effective opaque region is given by the intersection of the region set by this property and the bounding
        region set via the shape extension. The compositing manager MAY ignore this hint.

        Rationale: This gives the compositing manager more room for optimizations. For example, it can avoid
        drawing occluded portions behind the window.
        """
        ret: Optional[Xlib.protocol.request.GetProperty] = self.getProperty(Props.Window.BYPASS_COMPOSITOR.value)
        res: Optional[Union[List[int], List[str]]] = getPropertyValue(ret, display=self.display)
        if res:
            return int(res[0])
        return None

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
        atom = self.display.get_atom(Props.Window.ACTIVE.value, True)
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
        atom = self.display.get_atom(Props.Window.CLOSE.value, True)
        self.sendMessage(atom, [Xlib.X.CurrentTime, 2 if userAction else 1])

    def changeStacking(self, mode: int, sibling: Optional[XWindow] = None):
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
        the user to bring a currently active window to the top and return it back when the window looses focus.

        If a sibling and a stack_mode are specified, the window is restacked as follows:

            Above	    The window is placed just above the sibling.
            Below	    The window is placed just below the sibling.
            TopIf	    If the sibling occludes the window, the window is placed at the top of the stack.
            BottomIf	If the window occludes the sibling, the window is placed at the bottom of the stack.
            Opposite	If the sibling occludes the window, the window is placed at the top of the stack. If the window occludes the sibling, the window is placed at the bottom of the stack.

        If a stack_mode is specified but no sibling is specified, the window is restacked as follows:

            Above	    The window is placed at the top of the stack.
            Below	    The window is placed at the bottom of the stack.
            TopIf	    If any sibling occludes the window, the window is placed at the top of the stack.
            BottomIf	If the window occludes any sibling, the window is placed at the bottom of the stack.
            Opposite	If any sibling occludes the window, the window is placed at the top of the stack. If the window occludes any sibling, the window is placed at the bottom of the stack.

        :param mode: stack mode as per table above
        :param sibling: Sibling window to which re-stacking action will be related to
        """
        if sibling is not None:
            self.xWindow.configure(sibling=sibling, stack_mode=mode)
        else:
            self.xWindow.configure(stack_mode=mode)
        self.display.flush()

    def setMoveResize(self, gravity: int = 0, x: Optional[int] = None, y: Optional[int] = None, width: Optional[int] = None, height: Optional[int] = None, userAction: bool = True):
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
        # gravity_flags calculations from 'old' ewmh seem to be wrong
        # Thanks to elraymond (https://github.com/elraymond) for his help!
        gravity_flags = gravity
        if x is None:
            x = 0
        else:
            gravity_flags = gravity_flags | (1 << 8)
        if y is None:
            y = 0
        else:
            gravity_flags = gravity_flags | (1 << 9)
        if width is None:
            width = 0
        else:
            gravity_flags = gravity_flags | (1 << 10)
        if height is None:
            height = 0
        else:
            gravity_flags = gravity_flags | (1 << 11)
        if userAction:
            gravity_flags = gravity_flags | (1 << 12)
        else:
            gravity_flags = gravity_flags | (1 << 13)
        self.sendMessage(Props.Root.MOVERESIZE.value, [gravity_flags, x, y, width, height])

    def setWmMoveResize(self, x_root: int, y_root: int, orientation: int, button: int, userAction: bool = True):
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
        :param userAction: set to ''True'' to force action, as if it was requested by a user action. Defaults to True
        """
        # Need to understand this property
        self.sendMessage(Props.Window.WM_MOVERESIZE.value, [x_root, y_root, orientation, button, 2 if userAction else 1])

    def setWmStacking(self, siblingId: int, detail: int, userAction: bool = True):
        """
        This request is similar to ConfigureRequest with CWSibling and CWStackMode flags. It should be used only by
        pagers, applications can use normal ConfigureRequests. The source indication field should be therefore
        set to 2, see the section called “Source indication in requests” for details.

        Rationale: A Window Manager may put restrictions on configure requests from applications, for example it may
        under some conditions refuse to raise a window. This request makes it clear it comes from a pager or similar
        tool, and therefore the Window Manager should always obey it.

        :param siblingId: id of sibling window related to restacking action
        :param detail: details of action as integer (does this include mode???)
        :param userAction: should be set to 2 (typically used by pagers)
        """
        # Need to understand this property
        self.sendMessage(Props.Window.RESTACK.value, [2 if userAction else 1, siblingId, detail])

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
        self.sendMessage(Props.Window.REQ_FRAME_EXTENTS.value, [self.id])


class _Extensions:
    """
    Additional, non-EWMH features, related to low-level window properties like hints, protocols and events
    """

    def __init__(self, winId: int, display: Xlib.display.Display, root: XWindow):
        self.winId = winId
        self.display = display
        self.root = root
        self.xWindow = self.display.create_resource_object('window', winId)
        self.checkEvents = self._CheckEvents(winId, display, root)

    def getWmHints(self) -> Optional[Structs.WmHints]:
        """
        Get window hints.

        {'flags': 103, 'input': 1, 'initial_state': 1, 'icon_pixmap': <Pixmap 0x02a22304>, 'icon_window': <Window 0x00000000>, 'icon_x': 0, 'icon_y': 0, 'icon_mask': <Pixmap 0x02a2230b>, 'window_group': <Window 0x02a00001>}

        Xlib provides functions that you can use to set and read the WM_HINTS property for a given window.
        These functions use the flags and the XWMHints structure, as defined in Xlib.Xutil.*

        The XWMHints structure contains:

            flags: int
            input: int
            initial_state: int
            icon_pixmap: Xlib.xobject.drawable.Pixmap
            icon_window: Xlib.xobject.drawable.Window
            icon_x: int
            icon_y: int
            icon_mask: Xlib.xobject.drawable.Pixmap
            window_group: Xlib.xobject.drawable.Window

        To check if a hint is present or not, use bitwise operand OR ('|') between flags and following values in
        Xlib.Xutil.*

            InputHint	        (1L << 0)
            StateHint	        (1L << 1)
            IconPixmapHint	    (1L << 2)
            IconWindowHint	    (1L << 3)
            IconPositionHint	(1L << 4)
            IconMaskHint	    (1L << 5)
            WindowGroupHint	    (1L << 6)
            UrgencyHint	        (1L << 8)

        The input member is used to communicate to the window manager the input focus model used by the application.
        Applications that expect input but never explicitly set focus to any of their subwindows (that is, use the
        push model of focus management), such as X Version 10 style applications that use real-estate driven focus,
        should set this member to True. Similarly, applications that set input focus to their subwindows only when
        it is given to their top-level window by a window manager should also set this member to True. Applications
        that manage their own input focus by explicitly setting focus to one of their subwindows whenever they want
        keyboard input (that is, use the pull model of focus management) should set this member to False.
        Applications that never expect any keyboard input also should set this member to False.

        Pull model window managers should make it possible for push model applications to get input by setting
        input focus to the top-level windows of applications whose input member is True. Push model window managers
        should make sure that pull model applications do not break them by resetting input focus to PointerRoot
        when it is appropriate (for example, whenever an application whose input member is False sets input focus
        to one of its subwindows).

        The definitions for the initial_state flag are:

            Xlib.X.WithdrawnState	0
            Xlib.X.NormalState	    1	# most applications start this way
            Xlib.X.IconicState	    3	# application wants to start as an icon

        The icon_mask specifies which pixels of the icon_pixmap should be used as the icon. This allows for
        non-rectangular icons. Both icon_pixmap and icon_mask must be bitmaps. The icon_window lets an application
        provide a window for use as an icon for window managers that support such use. The window_group lets you
        specify that this window belongs to a group of other windows. For example, if a single application
        manipulates multiple top-level windows, this allows you to provide enough information that a window
        manager can iconify all the windows rather than just the one window.

        The UrgencyHint flag, if set in the flags field, indicates that the client deems the window contents
        to be urgent, requiring the timely response of the user. The window manager will make some effort to
        draw the user's attention to this window while this flag is set. The client must provide some means
        by which the user can cause the urgency flag to be cleared (either mitigating the condition that made
        the window urgent or merely shutting off the alarm) or the window to be withdrawn.

        :return: Hints struct
        """
        hints: Optional[Xlib.protocol.rq.DictWrapper] = self.xWindow.get_wm_hints()
        if hints is not None:
            ret: Structs.WmHints = Structs.WmHints(
                flags=hints.flags,
                input_mode=hints.input,
                initial_state=hints.initial_state,
                icon_pixmap=hints.icon_pixmap,
                icon_window=hints.icon_window,
                icon_x=hints.icon_x,
                icon_y=hints.icon_y,
                icon_mask=hints.icon_mask,
                window_group=hints.window_group
            )
            return ret
        return None

    def setWmHints(self, input_mode: int = Props.HintAction.KEEP, initial_state: int = Props.HintAction.KEEP,
                   icon_pixmap: Union[Xlib.xobject.drawable.Pixmap, int] = Props.HintAction.KEEP,
                   icon_window: Union[XWindow, int] = Props.HintAction.KEEP,
                   icon_x: int = Props.HintAction.KEEP, icon_y: int = Props.HintAction.KEEP,
                   icon_mask: Union[Xlib.xobject.drawable.Pixmap, int] = Props.HintAction.KEEP,
                   window_group: Union[XWindow, int] = Props.HintAction.KEEP,
                   urgency: Union[bool, int] = Props.HintAction.KEEP):
        """
        Set new hints for current window.

        Current window hints can be retrieved using getWmHints(), then apply desired changes.
        To calculate new flags in case of adding or removing hints (not needed if just changing its value),
        use bitwise operands between current flags and appropriate values in Xlib.Xutil to
        add ('|') or remove ('| ~') hints (e.g. to remove icon_mask, do: flags = flags | ~Xlib.Xutil.IconMaskHint)

        Hints mask values:

            InputHint	        (1L << 0)
            StateHint	        (1L << 1)
            IconPixmapHint	    (1L << 2)
            IconWindowHint	    (1L << 3)
            IconPositionHint	(1L << 4)
            IconMaskHint	    (1L << 5)
            WindowGroupHint	    (1L << 6)
            UrgencyHint	        (1L << 8)

        See getWmHints() documentation for more info about hints.

        To modify existing window hints use:

            Props.HintAction.KEEP       Keeps current value so if it's present or not (Default behavior)
            Props.HintAction.REMOVE     Removes hint from existing window hints
            Target value                (int/Pixmap/XWindow/bool) Adds new value or changes existing one

        :param input_mode: input focus model used by the application (0 / 1)
        :param initial_state: WithdrawnState/NormalState/IconicState initial state preferred by window
        :param icon_pixmap: bitmap to use as window icon
        :param icon_window: window to use as icon
        :param icon_x: x position of icon
        :param icon_y: y position of icon
        :param icon_mask: pixels of the icon_pixmap should be used as the icon. This allows for non-rectangular icons
        :param window_group: group of windows the current window belongs to
        :param urgency: True/False to activate/deactivate urgency falg
        """
        hints: Optional[Xlib.protocol.rq.DictWrapper] = self.xWindow.get_wm_hints()
        if hints is not None:
            # If None: WM doesn't use them or should we initialize them (and how)?
            if input_mode != Props.HintAction.KEEP:
                if input_mode != Props.HintAction.REMOVE:
                    if input_mode in (0, 1):
                        hints.input_mode = input_mode
                        hints.flags = hints.flags | Xlib.Xutil.InputHint
                else:
                    hints.flags = hints.flags & ~Xlib.Xutil.InputHint
            if initial_state != Props.HintAction.KEEP:
                if initial_state != Props.HintAction.REMOVE:
                    if initial_state in (Xlib.Xutil.NormalState, Xlib.Xutil.IconicState, Xlib.Xutil.WithdrawnState, Xlib.Xutil.ZoomState):
                        hints.initial_state = initial_state
                        hints.flags = hints.flags | Xlib.Xutil.StateHint
                else:
                    hints.flags = hints.flags & ~Xlib.Xutil.StateHint
            if icon_pixmap != Props.HintAction.KEEP:
                if icon_pixmap != Props.HintAction.REMOVE:
                    if isinstance(icon_pixmap, Xlib.xobject.drawable.Pixmap):
                        hints.icon_pixmap = icon_pixmap
                        hints.flags = hints.flags | Xlib.Xutil.IconPixmapHint
                else:
                    hints.flags = hints.flags & ~Xlib.Xutil.IconPixmapHint
            if icon_window != Props.HintAction.KEEP:
                if icon_window != Props.HintAction.REMOVE:
                    if isinstance(icon_window, XWindow):
                        hints.icon_window = icon_window
                        hints.flags = hints.flags | Xlib.Xutil.IconWindowHint
                else:
                    hints.flags = hints.flags & ~Xlib.Xutil.IconWindowHint
            if icon_x != Props.HintAction.KEEP:
                if icon_x != Props.HintAction.REMOVE:
                    hints.icon_x = icon_x
                    hints.flags = hints.flags | Xlib.Xutil.IconPositionHint
                else:
                    hints.flags = hints.flags & ~Xlib.Xutil.IconPositionHint
            if icon_y != Props.HintAction.KEEP:
                if icon_y != Props.HintAction.REMOVE:
                    hints.icon_y = icon_y
                    hints.flags = hints.flags | Xlib.Xutil.IconPositionHint
                else:
                    hints.flags = hints.flags & ~Xlib.Xutil.IconPositionHint
            if icon_mask != Props.HintAction.KEEP:
                if icon_mask != Props.HintAction.REMOVE:
                    if isinstance(icon_mask, Xlib.xobject.drawable.Pixmap):
                        hints.icon_mask = icon_mask
                        hints.flags = hints.flags | Xlib.Xutil.IconMaskHint
                else:
                    hints.flags = hints.flags & ~Xlib.Xutil.IconMaskHint
            if window_group != Props.HintAction.KEEP:
                if window_group != Props.HintAction.REMOVE:
                    if isinstance(window_group, XWindow):
                        hints.window_group = window_group
                        hints.flags = hints.flags | Xlib.Xutil.WindowGroupHint
                else:
                    hints.flags = hints.flags & ~Xlib.Xutil.WindowGroupHint
            if urgency != Props.HintAction.KEEP:
                if urgency != Props.HintAction.REMOVE:
                    if isinstance(urgency, bool):
                        if urgency:
                            hints.flags = hints.flags | Xlib.Xutil.UrgencyHint
                        else:
                            hints.flags = hints.flags & ~Xlib.Xutil.UrgencyHint
            self.xWindow.set_wm_hints(hints)
            self.display.flush()

    def getWmNormalHints(self) -> Optional[Structs.WmNormalHints]:
        """
        Xlib provides functions that you can use to set or read the WM_NORMAL_HINTS property for a given window.
        The functions use the flags and the XSizeHints structure, as defined in the X11/Xutil.h header file.
        The size of the XSizeHints structure may grow in future releases, as new components are added to support
        new ICCCM features. Passing statically allocated instances of this structure into Xlib may result in memory
        corruption when running against a future release of the library. As such, it is recommended that only
        dynamically allocated instances of the structure be used.

        To allocate an XSizeHints structure, use XAllocSizeHints().

        The XSizeHints structure contains:

        # Size hints mask bits

            USPosition	(1L << 0)	# user specified x, y
            USSize		(1L << 1)	# user specified width, height
            PPosition	(1L << 2)	# program specified position
            PSize		(1L << 3)	# program specified size
            PMinSize	(1L << 4)	# program specified minimum size
            PMaxSize	(1L << 5)	# program specified maximum size
            PResizeInc	(1L << 6)	# program specified resize increments
            PAspect		(1L << 7)	# program specified min and max aspect ratios
            PBaseSize	(1L << 8)
            PWinGravity	(1L << 9)
            PAllHints	(PPosition|PSize|PMinSize|PMaxSize|PResizeInc|PAspect)

        # Values

            typedef struct {
                long flags;		# marks which fields in this structure are defined
                int x, y;		# Obsolete
                int width, height;	# Obsolete
                int min_width, min_height;
                int max_width, max_height;
                int width_inc, height_inc;
                struct {
                       int x;		# numerator
                       int y;		# denominator
                } min_aspect, max_aspect;
                int base_width, base_height;
                int win_gravity;
                # this structure may be extended in the future
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
        normal_hints: Optional[Xlib.protocol.rq.DictWrapper] = self.xWindow.get_wm_normal_hints()
        if normal_hints is not None:
            min_aspect: Structs.Aspect = Structs.Aspect(
                num=normal_hints.min_aspect.num,
                denum=normal_hints.min_aspect.denum
            )
            max_aspect: Structs.Aspect = Structs.Aspect(
                num=normal_hints.max_aspect.num,
                denum=normal_hints.max_aspect.denum
            )
            ret: Structs.WmNormalHints = Structs.WmNormalHints(
                flags=normal_hints.flags,
                min_width=normal_hints.min_width,
                min_height=normal_hints.min_height,
                max_width=normal_hints.max_width,
                max_height=normal_hints.max_height,
                width_inc=normal_hints.width_inc,
                height_inc=normal_hints.height_inc,
                min_aspect=min_aspect,
                max_aspect=max_aspect,
                base_width=normal_hints.base_width,
                base_height=normal_hints.base_height,
                win_gravity=normal_hints.win_gravity
            )
            return ret
        return None

    def setWmNormalHints(self, min_width: int = Props.HintAction.KEEP, min_height: int = Props.HintAction.KEEP,
                         max_width: int = Props.HintAction.KEEP, max_height: int = Props.HintAction.KEEP,
                         width_inc: int = Props.HintAction.KEEP, height_inc: int = Props.HintAction.KEEP,
                         min_aspect: Union[Structs.Aspect, int] = Props.HintAction.KEEP,
                         max_aspect: Union[Structs.Aspect, int] = Props.HintAction.KEEP,
                         base_width: int = Props.HintAction.KEEP, base_height: int = Props.HintAction.KEEP,
                         win_gravity: int = Props.HintAction.KEEP):
        """
        Set new normal hints for current window.

        Current window normal hints can be retrieved using getWmNormalHints(), then apply desired changes.

        To calculate new flags in case of adding or removing hints (not needed if just changing its value),
        use bitwise operands between current flags and appropriate values in Xlib.Xutil to
        add ('|') or remove ('& ~') hints (e.g. to remove PSize hint, do: flags = flags & ~Xlib.Xutil.PSize)

            USPosition	(1L << 0)	# user specified x, y
            USSize		(1L << 1)	# user specified width, height
            PPosition	(1L << 2)	# program specified position
            PSize		(1L << 3)	# program specified size
            PMinSize	(1L << 4)	# program specified minimum size
            PMaxSize	(1L << 5)	# program specified maximum size
            PResizeInc	(1L << 6)	# program specified resize increments
            PAspect		(1L << 7)	# program specified min and max aspect ratios
            PBaseSize	(1L << 8)
            PWinGravity	(1L << 9)

        See getWmNormalHints() documentation for more info about normal hints.

        To modify existing window normal hints use:

            Props.HintAction.KEEP       Keeps current value so if it's present or not (Default behavior)
            Props.HintAction.REMOVE     Removes hint from existing window normal hints
            Target value                (int/Pixmap/XWindow/bool) Adds new value or changes existing one

        :param min_width: minimum width of window
        :param min_height: minimum height of window
        :param max_width: max width of window
        :param max_height: max height of window
        :param width_inc: width changes increments (in pixels)
        :param height_inc: height changes increments (in pixels)
        :param min_aspect: X (numerator), Y (denumerator) ratio for min_aspect
        :param max_aspect: X (numerator), Y (denumerator) ratio for max_aspect
        :param base_width: Preferred width of window
        :param base_height: Preferred height of window
        :param int win_gravity: window gravity for placing an re-stacking
        """
        normal_hints: Optional[Xlib.protocol.rq.DictWrapper] = self.xWindow.get_wm_normal_hints()
        if normal_hints is not None:
            # If None: WM doesn't use them or should we initialize them (and how)?
            if min_width != Props.HintAction.KEEP:
                if min_width != Props.HintAction.REMOVE or min_width == 0:
                    normal_hints.min_width = min_width
                    normal_hints.flags = normal_hints.flags | Xlib.Xutil.PMinSize
                else:
                    normal_hints.flags = normal_hints.flags & ~Xlib.Xutil.PMinSize
            if min_height != Props.HintAction.KEEP:
                if min_height != Props.HintAction.REMOVE or min_height == 0:
                    normal_hints.min_height = min_height
                    normal_hints.flags = normal_hints.flags | Xlib.Xutil.PMinSize
                else:
                    normal_hints.flags = normal_hints.flags & ~Xlib.Xutil.PMinSize
            if max_width != Props.HintAction.KEEP:
                if max_width != Props.HintAction.REMOVE and max_width != 0:
                    normal_hints.max_width = max_width
                    normal_hints.flags = normal_hints.flags | Xlib.Xutil.PMaxSize
                else:
                    normal_hints.flags = normal_hints.flags & ~Xlib.Xutil.PMaxSize
            if max_height != Props.HintAction.KEEP:
                if max_height != Props.HintAction.REMOVE and max_height != 0:
                    normal_hints.max_height = max_height
                    normal_hints.flags = normal_hints.flags | Xlib.Xutil.PMaxSize
                else:
                    normal_hints.flags = normal_hints.flags & ~Xlib.Xutil.PMaxSize
            if width_inc != Props.HintAction.KEEP:
                if width_inc != Props.HintAction.REMOVE or width_inc == 0:
                    normal_hints.width_inc = width_inc
                    normal_hints.flags = normal_hints.flags | Xlib.Xutil.PResizeInc
                else:
                    normal_hints.flags = normal_hints.flags & ~Xlib.Xutil.PResizeInc
            if height_inc != Props.HintAction.KEEP or height_inc == 0:
                if height_inc != Props.HintAction.REMOVE:
                    normal_hints.height_inc = height_inc
                    normal_hints.flags = normal_hints.flags | Xlib.Xutil.PResizeInc
                else:
                    normal_hints.flags = normal_hints.flags & ~Xlib.Xutil.PResizeInc
            if min_aspect != Props.HintAction.KEEP:
                if isinstance(min_aspect, dict) and min_aspect["num"] != 0 and min_aspect["denum"] != 0:
                    normal_hints.min_aspect.x = min_aspect["num"]
                    normal_hints.min_aspect.y = min_aspect["denum"]
                    normal_hints.flags = normal_hints.flags | Xlib.Xutil.PAspect
                elif min_aspect == Props.HintAction.REMOVE or \
                        (isinstance(min_aspect, dict) and min_aspect["num"] == 0 and min_aspect["denum"] == 0):
                    normal_hints.flags = normal_hints.flags & ~Xlib.Xutil.PAspect
            if max_aspect != Props.HintAction.KEEP:
                if isinstance(max_aspect, dict) and max_aspect["num"] != 0 and max_aspect["denum"] != 0:
                    normal_hints.max_aspect.x = max_aspect["num"]
                    normal_hints.max_aspect.y = max_aspect["denum"]
                    normal_hints.flags = normal_hints.flags | Xlib.Xutil.PAspect
                elif max_aspect == Props.HintAction.REMOVE or \
                        (isinstance(max_aspect, dict) and max_aspect["num"] == 0 and max_aspect["denum"] == 0):
                    normal_hints.flags = normal_hints.flags & ~Xlib.Xutil.PAspect
            if base_width != Props.HintAction.KEEP:
                if base_width != Props.HintAction.REMOVE or base_width == 0:
                    normal_hints.base_width = base_width
                    normal_hints.flags = normal_hints.flags | Xlib.Xutil.PBaseSize
                else:
                    normal_hints.flags = normal_hints.flags & ~Xlib.Xutil.PBaseSize
            if base_height != Props.HintAction.KEEP:
                if base_height != Props.HintAction.REMOVE or base_height == 0:
                    normal_hints.base_height = base_height
                    normal_hints.flags = normal_hints.flags | Xlib.Xutil.PBaseSize
                else:
                    normal_hints.flags = normal_hints.flags & ~Xlib.Xutil.PBaseSize
            if win_gravity != Props.HintAction.KEEP:
                if win_gravity != Props.HintAction.REMOVE:
                    normal_hints.win_gravity = win_gravity
                    normal_hints.flags = normal_hints.flags | Xlib.Xutil.PWinGravity
                else:
                    normal_hints.flags = normal_hints.flags & ~Xlib.Xutil.PWinGravity
            self.xWindow.set_wm_normal_hints(normal_hints)
            self.display.flush()

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

            Protocol	        Section	    Purpose
            WM_TAKE_FOCUS	    4.1.7	    Assignment of input focus
            WM_SAVE_YOURSELF	Appendix C	Save client state request (deprecated)
            WM_DELETE_WINDOW	4.2.8.1 	Request to delete top-level window

        :param text: select whether the protocols will be returned as integers or strings
        :return: List of protocols in integer or string format
        """
        prots: List[int] = self.xWindow.get_wm_protocols()
        if text:
            return [self.display.get_atom_name(p) for p in prots if isinstance(p, int) and p != 0]
        else:
            return [p for p in prots]

    def addWmProtocols(self, atoms: Union[List[str], List[int]]):
        """
        Adds new protocols atoms for current window.

        See getWmProtocols() documentation for more info about protocols.

        The X Consortium will maintain a registry of protocols to avoid collisions in the name space. The following
        table lists the protocols that have been defined to date.

            Protocol	        Section	    Purpose
            WM_TAKE_FOCUS	    4.1.7	    Assignment of input focus
            WM_SAVE_YOURSELF	Appendix C	Save client state request (deprecated)
            WM_DELETE_WINDOW	4.2.8.1 	Request to delete top-level window

        :param atoms: List of protocols to be added
        """
        prots: List[int] = self.xWindow.get_wm_protocols()
        newAtoms: List[int] = []
        for atom in atoms:
            if isinstance(atom, str):
                a: int = self.display.get_atom(atom)
            else:
                a = int(atom)
            if a not in prots:
                newAtoms.append(a)
        self.xWindow.set_wm_protocols(newAtoms)
        self.display.flush()

    def delWmProtocols(self, atoms: Union[List[str], List[int]]):
        """
        Deletes existing protocols atoms for current window.

        See getWmProtocols() documentation for more info about protocols.

        The X Consortium will maintain a registry of protocols to avoid collisions in the name space. The following
        table lists the protocols that have been defined to date.

            Protocol	        Section	    Purpose
            WM_TAKE_FOCUS	    4.1.7	    Assignment of input focus
            WM_SAVE_YOURSELF	Appendix C	Save client state request (deprecated)
            WM_DELETE_WINDOW	4.2.8.1 	Request to delete top-level window

        :param atoms: List of protocols to be deleted
        """
        atomsList: List[int] = []
        for atom in atoms:
            if isinstance(atom, str):
                atomsList.append(self.display.get_atom(atom))
            else:
                atomsList.append(int(atom))
        prots: List[int] = self.xWindow.get_wm_protocols()
        newAtoms: List[int] = [a for a in prots if a not in atomsList]
        self.xWindow.set_wm_protocols(newAtoms)
        self.display.flush()

    class _CheckEvents:
        """
        Activate a watchdog to be notified on given events (to provided callback function).

        It's important to define proper mask and event list accordingly. See checkEvents() documentation.
        """

        def __init__(self, winId: int, display: Xlib.display.Display, root: XWindow):

            self._winId: int = winId
            self._display: Xlib.display.Display = display
            self._root: XWindow = root

            self._keep: threading.Event = threading.Event()
            self._stopRequested: bool = False
            self._checkThread: Optional[threading.Thread] = None
            self._threadStarted: bool = False

            # self._isCinnamon = "cinnamon" in os.environ['XDG_CURRENT_DESKTOP'].lower()

        def _checkDisplayEvents(self):

            while self._keep.wait() and not self._stopRequested:
                i = self._root.display.pending_events()
                while i > 0 and not self._stopRequested:
                    event = self._root.display.next_event()
                    if event.type in self._events:
                        if event.window.id == self._winId:
                            self._callback(event)
                        else:
                            tree = event.window.query_tree()
                            if tree and hasattr(tree, "children"):
                                for child in tree.children:
                                    if isinstance(child, XWindow) and child.id == self._winId:
                                        self._callback(event)
                                        break
                    i -= 1
                time.sleep(0.1)

            # Is this necessary to somehow "free" the events catching???
            self._root.change_attributes(event_mask=Xlib.X.NoEventMask)
            self._display.flush()

        def start(self, events: List[int], mask: int, callback: Callable[[Xlib.protocol.rq.Event], None]):
            """
            Activate a watchdog to be notified on given events (to provided callback function).

            It is possible to update target events, mask or callback function just invoking start() again and
            passing new arguments.

            Be aware it is important to define proper mask and event list accordingly.

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

            The following table lists the events constants you can pass to the events argument (defined in Xlib.X.*):

                Keyboard events	                    KeyPress, KeyRelease
                Pointer events	                    ButtonPress, ButtonRelease, MotionNotify
                Window crossing events	            EnterNotify, LeaveNotify
                Input focus events	                FocusIn, FocusOut
                Keymap state notification event	    KeymapNotify
                Exposure events	                    Expose, GraphicsExpose, NoExpose
                Structure control events	        CirculateRequest, ConfigureRequest, MapRequest, ResizeRequest
                Window state notification events	CirculateNotify, ConfigureNotify, CreateNotify, DestroyNotify, GravityNotify, MapNotify, MappingNotify, ReparentNotify, UnmapNotify, VisibilityNotify
                Colormap state notification event	ColormapNotify
                Client communication events	        ClientMessage, PropertyNotify, SelectionClear, SelectionNotify, SelectionRequest

            The following table lists the event mask constants you can pass to the event_mask argument and the
            circumstances in which you would want to specify the event mask (defined in Xlib.X.*):

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

            :param events: List of events to be notified on as a list of integers: [Xlib.X.event1, Xlib.X.event2, ...]
            :param mask: Events mask according to selected events as integer: Xlib.X.mask1 | Xlib.mask2 | ...
            :param callback: Function to be invoked when a selected event is received, passing received event to it
            """
            self._events: List[int] = events
            self._mask: int = mask
            self._callback: Callable[[Xlib.protocol.rq.Event], None] = callback

            self._root.change_attributes(event_mask=self._mask)
            self._display.flush()

            if not self._threadStarted and self._checkThread is None:
                self._checkThread = threading.Thread(target=self._checkDisplayEvents)
                self._checkThread.daemon = True
                self._threadStarted = True
                self._checkThread.start()
            self._stopRequested = False
            self._keep.set()

        def pause(self):
            """
            Pause the watchdog so the callback is not invoked.

            Restart the watchdog just invoking start() again using same arguments or new ones.
            """
            self._keep.clear()

        def stop(self):
            """
            Stop the watchdog so the thread is ended.

            Start a new watchdog using start() again.
            """
            if self._threadStarted and self._checkThread is not None:
                self._threadStarted = False
                self._stopRequested = True
                self._keep.set()
                self._checkThread.join()
                self._checkThread = None


def _getWindowParent(win: XWindow, rootId: int) -> int:
    while True:
        parent = win.query_tree().parent
        if parent.id == rootId or not isinstance(parent, XWindow):
            break
        win = parent
    return win.id


def _getWindowGeom(win: XWindow, rootId: int = defaultRoot.id) -> Tuple[int, int, int, int]:
    # https://stackoverflow.com/questions/12775136/get-window-position-and-size-in-python-with-xlib - mgalgs
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
        if parent.id == rootId:
            break
        win = parent
    return x, y, w, h


def _xlibGetAllWindows(parent: Optional[XWindow] = None, title: str = "", klass: Optional[Tuple[str, str]] = None) -> List[XWindow]:
    """
    Retrieves all open windows, including "system", non-user windows (unlike getClientList() or getClientListStacking()).

    :param parent: parent window to limit the search to its children. Defaults to root window
    :param title: include only windows that match given title
    :param klass: include only windows that match given class
    :return: List of windows objects (X-Window)
    """

    parentWin: XWindow = parent or defaultRoot
    allWindows: List[XWindow] = []

    def findit(hwnd: XWindow) -> None:
        try:
            query = hwnd.query_tree()
            children: List[XWindow] = query.children
        except:
            children = []
        for child in children:
            try:
                ret: Optional[str] = child.get_wm_name()
            except:
                ret = None
            if ret is not None:
                winTitle: str = ret
            else:
                winTitle = ""
            winClass: Optional[Tuple[str, str]] = None
            try:
                winClass = child.get_wm_class()
            except:
                pass
            if winClass is None:
                winClass = ("", "")
            if (not title and not klass) or (title and winTitle == title) or (klass and winClass == klass):
                allWindows.append(child)
            findit(child)

    findit(parentWin)
    return allWindows


def _createSimpleWindow(parent: XWindow, x: int, y: int, width: int, height: int, override: bool = False,
                        inputOnly: bool = False, display: Xlib.display.Display = defaultDisplay) -> EwmhWindow:
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
    window: EwmhWindow = EwmhWindow(win.id)
    return window


def _createTransient(display: Xlib.display.Display, parent: XWindow, transient_for: XWindow,
                     callback: Callable[[Xlib.protocol.rq.Event], None], x: int, y: int, width: int, height: int,
                     override: bool = False, inputOnly: bool = False) -> Tuple[EwmhWindow, List[int]]:
    # https://shallowsky.com/blog/programming/click-thru-translucent-update.html
    # https://github.com/python-xlib/python-xlib/issues/200

    transientWindow: EwmhWindow = _createSimpleWindow(parent, x, y, width, height, override, inputOnly, display)
    xWin: XWindow = transientWindow.xWindow

    onebyte: int = int(0xAA)  # Calculate as 0xff * target_opacity
    fourbytes: int = onebyte | (onebyte << 8) | (onebyte << 16) | (onebyte << 24)
    xWin.change_property(display.get_atom('_NET_WM_WINDOW_OPACITY'), Xlib.Xatom.CARDINAL, 32, [fourbytes])

    input_pm: Xlib.xobject.drawable.Pixmap = xWin.create_pixmap(width, height, 1)
    gc: Xlib.xobject.fontable.GC = input_pm.create_gc(foreground=0, background=0)
    input_pm.fill_rectangle(gc.id, 0, 0, width, height)
    xWin.shape_mask(Xlib.ext.shape.SO.Set, Xlib.ext.shape.SK.Input, 0, 0, input_pm)  # type: ignore[attr-defined]  # pyright: ignore[reportGeneralTypeIssues, reportUnknownMemberType]
    # xWin.shape_select_input(0)

    xWin.map()
    display.flush()

    xWin.set_wm_transient_for(transient_for)
    display.flush()

    currDesktop = os.environ['XDG_CURRENT_DESKTOP'].lower()
    # otherDesktop = os.environ.get("DESKTOP_SESSION").lower()  # -> Returns None
    if "gnome" in currDesktop:
        gaps = [24, 24, -40, -80]
    elif "cinnamon" in currDesktop:
        gaps = [-2, -32, +46, +112]
    elif "kde" in currDesktop:
        # KDE has a totally different behavior. Must investigate/test
        gaps = [0, 0, 0, 0]
    else:
        gaps = [0, 0, 0, 0]

    pgeom: Xlib.protocol.request.GetGeometry = transient_for.get_geometry()
    xWin.configure(x=max(0, x + gaps[0]), y=max(0, y + gaps[1]), width=pgeom.width + gaps[2], height=pgeom.height + gaps[3])
    display.flush()

    transientWindow.extensions.checkEvents.start(
        [Xlib.X.ConfigureNotify],
        Xlib.X.StructureNotifyMask | Xlib.X.SubstructureNotifyMask,
        callback
    )

    # Removing actions but not decoration, since it causes not to capture Keyboard and mouse,
    transientWindow.changeProperty(display.get_atom("_MOTIF_WM_HINTS"), [1, 0, 1, 0, 0])
    # Same happens with DESKTOP (???), SPLASH, DOCK or override_redirect
    # transientWindow.setWmWindowType(Props.WindowType.DESKTOP)
    # MODAL doesn't behave as expected (it doesn't block main window)
    transientWindow.changeWmState(Props.StateAction.ADD, Props.State.MODAL, Props.State.BELOW)
    # x, y, w, h = _getWindowGeom(transientWindow.xWindow, defaultRoot)
    # normal_hints = transient_for.get_wm_normal_hints()
    # normal_hints.flags = 808
    # normal_hints.min_width = normal_hints.max_width = w + gaps[2]
    # normal_hints.min_height = normal_hints.max_height = h + gaps[3]
    # transientWindow.xWindow.set_wm_normal_hints(normal_hints)
    # hints = transient_for.get_wm_hints()
    # transientWindow.xWindow.set_wm_hints(hints)

    return transientWindow, gaps


def _closeTransient(transientWindow: EwmhWindow):
    transientWindow.extensions.checkEvents.stop()
    transientWindow.xWindow.set_wm_transient_for(transientWindow.root)
    transientWindow.display.flush()
    transientWindow.xWindow.unmap()  # It seems not to properly close if not unmapped first
    transientWindow.display.flush()
    transientWindow.setClosed()


_xlib: Optional[Union[CDLL, int]] = None
_xcomp: Optional[Union[CDLL, int]] = None


def _loadX11Library() -> Optional[Union[CDLL, int]]:
    global _xlib
    if _xlib is None:
        lib: Union[CDLL, int] = -1
        try:
            libPath: Optional[str] = find_library('X11')
            if libPath:
                lib = cdll.LoadLibrary(libPath)
        except:
            pass
        _xlib = lib
    return _xlib


def _loadXcompLibrary() -> Optional[Union[CDLL, int]]:
    global _xcomp
    if _xcomp is None:
        lib: Union[CDLL, int] = -1
        try:
            libPath: Optional[str] = find_library('Xcomposite')
            if libPath:
                lib = cdll.LoadLibrary(libPath)
        except:
            pass
        _xcomp = lib
    return _xcomp


def _XGetAttributes(winId: int, dpyName: str = "") -> Tuple[bool, Structs._XWindowAttributes]:
    resOK: bool = False
    attr: Structs._XWindowAttributes = Structs._XWindowAttributes()

    xlib: Optional[Union[CDLL, int]] = _loadX11Library()

    if isinstance(xlib, CDLL):
        try:
            if not dpyName:
                dpyName = defaultDisplay.get_display_name()
            dpy: int = xlib.XOpenDisplay(dpyName.encode())
            xlib.XGetWindowAttributes(dpy, winId, byref(attr))
            xlib.XCloseDisplay(dpy)
            resOK = True
        except:
            pass
    return resOK, attr

    # Leaving this as reference of using X11 library
    # https://github.com/evocount/display-management/blob/c4f58f6653f3457396e44b8c6dc97636b18e8d8a/displaymanagement/rotation.py
    # https://github.com/nathanlopez/Stitch/blob/master/Configuration/mss/linux.py
    # https://gist.github.com/ssokolow/e7c9aae63fb7973e4d64cff969a78ae8
    # https://stackoverflow.com/questions/36188154/get-x11-window-caption-height
    # https://refspecs.linuxfoundation.org/LSB_1.3.0/gLSB/gLSB/libx11-ddefs.html
    # s = xlib.XDefaultScreen(d)
    # root = xlib.XDefaultRootWindow(d)
    # fg = xlib.XBlackPixel(d, s)
    # bg = xlib.XWhitePixel(d, s)
    # w = xlib.XCreateSimpleWindow(d, root, 600, 300, 400, 200, 0, fg, bg)
    # xlib.XMapWindow(d, w)
    # time.sleep(4)
    # a = xlib.XInternAtom(d, "_GTK_FRAME_EXTENTS", True)
    # if not a:
    #     a = xlib.XInternAtom(d, "_NET_FRAME_EXTENTS", True)
    # t = c_int()
    # f = c_int()
    # n = c_ulong()
    # b = c_ulong()
    # xlib.XGetProps.WindowProperty(d, w, a, 0, 4, False, Xlib.X.AnyPropertyType, byref(t), byref(f), byref(n), byref(b), byref(attr))
    # r = c_ulong()
    # x = c_int()
    # y = c_int()
    # w = c_uint()
    # h = c_uint()
    # b = c_uint()
    # d = c_uint()
    # xlib.XGetGeometry(d, hWnd.id, byref(r), byref(x), byref(y), byref(w), byref(h), byref(b), byref(d))
    # print(x, y, w, h)
    # Other references (send_event and setProperty):
    # prop = DISP.intern_atom(WM_CHANGE_STATE, False)
    # data = (32, [Xlib.Xutil.IconicState, 0, 0, 0, 0])
    # ev = Xlib.protocol.event.ClientMessage(window=self._hWnd.id, client_type=prop, data=data)
    # mask = Xlib.X.SubstructureRedirectMask | Xlib.X.SubstructureNotifyMask
    # DISP.send_event(destination=ROOT, event=ev, event_mask=mask)
    # data = [Xlib.Xutil.IconicState, 0, 0, 0, 0]
    # _setProperty(_type="WM_CHANGE_STATE", data=data, mask=mask)
    # for atom in w.list_properties():
    #     print(DISP.atom_name(atom))
    # props = DISP.xrandr_list_output_properties(output)
    # for atom in atoms:
    #     print(atom, DISP.get_atom_name(atom))
    #     print(DISP.xrandr_get_output_property(output, atom, 0, 0, 1000)._data['value'])
