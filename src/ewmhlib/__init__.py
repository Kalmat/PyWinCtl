from __future__ import annotations

import sys
assert sys.platform == "linux"

from ._ewmhlib import (displaysCount, getDisplaysNames, getDisplaysInfo, getDisplayFromRoot, getDisplayFromWindow,
                       getProperty, getPropertyValue, changeProperty, sendMessage, _xlibGetAllWindows,
                       defaultDisplay, defaultScreen, defaultRoot, RootWindow, defaultRootWindow, EwmhWindow
                       )
import ewmhlib.Props as Props
import ewmhlib.Structs as Structs

__all__ = [
    "version", "displaysCount", "getDisplaysNames", "getDisplaysInfo", "getDisplayFromRoot", "getDisplayFromWindow",
    "getProperty", "getPropertyValue", "changeProperty", "sendMessage",
    "defaultDisplay", "defaultScreen", "defaultRoot", "defaultRootWindow", "RootWindow", "EwmhWindow",
    "Props", "Structs"
]


__version__ = "0.0.1"


def version(numberOnly: bool = True):
    """Returns the current version of ewmhlib module, in the form ''x.x.xx'' as string"""
    return ("" if numberOnly else "EWMHlib-")+__version__
