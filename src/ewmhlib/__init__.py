from __future__ import annotations

import sys
assert sys.platform == "linux"

from ._ewmhlib import (Props, Structs, getAllDisplaysInfo, getDisplayFromRoot, getDisplayFromWindow,
                       getProperty, getPropertyValue, changeProperty, sendMessage, _xlibGetAllWindows,
                       defaultDisplay, defaultScreen, defaultRoot, RootWindow, defaultRootWindow, EwmhWindow
                       )


__all__ = [
    "version", "Props", "Structs", "getAllDisplaysInfo", "getDisplayFromRoot", "getDisplayFromWindow",
    "getProperty", "getPropertyValue", "changeProperty", "sendMessage",
    "defaultDisplay", "defaultScreen", "defaultRoot", "defaultRootWindow", "RootWindow", "EwmhWindow"
]


__version__ = "0.0.1"


def version(numberOnly: bool = True):
    """Returns the current version of ewmhlib module, in the form ''x.x.xx'' as string"""
    return ("" if numberOnly else "EWMHlib-")+__version__
