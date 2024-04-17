#!/usr/bin/python
# -*- coding: utf-8 -*-#from typing import List

from typing_extensions import TypedDict
from typing import List

from ctypes import Structure, c_int32, c_ulong, c_uint32
import Xlib.xobject
from Xlib.protocol.rq import Struct
from Xlib.xobject.drawable import Window as XWindow


class ScreensInfo(TypedDict):
    """
    Container class to handle ScreensInfo struct:

        - screen_number (str): int (sequential)
        - is_default (bool): ''True'' if the screen is the default screen
        - screen (Xlib.Struct): screen Struct (see Xlib documentation)
        - root (Xlib.xobject.drawable.Window): root X-Window object belonging to screen
    """
    screen_number: str
    is_default: bool
    screen: Struct
    root: XWindow


class DisplaysInfo(TypedDict):
    """
    Container class to handle DisplaysInfo struct:

        - name: Display name (as per Xlib.display.Display(name))
        - is_default: ''True'' if the display is the default display
        - screens: list of ScreensInfo structs belonging to display
    """
    display: Xlib.display.Display
    name: str
    is_default: bool
    screens: List[ScreensInfo]


"""
Perhaps unnecesary since structs below are defined in Xlib.xobject.icccm.*, though in a more complex way.
"""
class WmHints(TypedDict):
    """
    Container class to handle WmHints struct:

    Example:
         {
            'flags': 103,
            'input': 1,
            'initial_state': 1,
            'icon_pixmap': <Pixmap 0x02a22304>,
            'icon_window': <Window 0x00000000>,
            'icon_x': 0,
            'icon_y': 0,
            'icon_mask': <Pixmap 0x02a2230b>,
            'window_group': <Window 0x02a00001>
        }
    """
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
    """Container class to handle Aspect struct (num, denum)"""
    num: int
    denum: int


class WmNormalHints(TypedDict):
    """
    Container class to handle WmNormalHints

    Example:
        {
            'flags': 848,
            'min_width': 387,
            'min_height': 145,
            'max_width': 0,
            'max_height': 0,
            'width_inc': 9,
            'height_inc': 18,
            'min_aspect': <class 'Xlib.protocol.rq.DictWrapper'>({'num': 0, 'denum': 0}),
            'max_aspect': <class 'Xlib.protocol.rq.DictWrapper'>({'num': 0, 'denum': 0}),
            'base_width': 66,
            'base_height': 101,
            'win_gravity': 1
        }
    """
    flags: int
    min_width: int
    min_height: int
    max_width: int
    max_height: int
    width_inc: int
    height_inc: int
    min_aspect: Aspect
    max_aspect: Aspect
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
