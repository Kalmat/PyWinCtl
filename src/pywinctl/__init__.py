#!/usr/bin/python
# -*- coding: utf-8 -*-

__all__ = [
    "version", "Re",
    # OS Specifics
    "Window", "checkPermissions", "getActiveWindow", "getActiveWindowTitle", "getWindowsWithTitle",
    "getAllWindows", "getAllTitles", "getAppsWithName", "getAllAppsNames", "getAllAppsWindowsTitles",
    "getTopWindowAt", "getWindowsAt", "displayWindowsUnderMouse",
    "getAllScreens", "getScreenSize", "getWorkArea", "getMousePos"
]

import sys

# Mac only
if sys.platform == "darwin":
    __all__ += ["NSWindow"]

__version__ = "0.2"


def version(numberOnly: bool = True) -> str:
    """Returns the current version of PyWinCtl module, in the form ''x.x.xx'' as string"""
    return ("" if numberOnly else "PyWinCtl-")+__version__


from ._main import (Re, Window, checkPermissions, getActiveWindow,
                    getActiveWindowTitle, getAllAppsNames, getAllAppsWindowsTitles,
                    getAllTitles, getAllWindows, getAppsWithName, getWindowsWithTitle,
                    getTopWindowAt, getWindowsAt, displayWindowsUnderMouse,
                    getAllScreens, getScreenSize, getWorkArea, getMousePos
                    )

if sys.platform == "darwin":
    from ._main import NSWindow
