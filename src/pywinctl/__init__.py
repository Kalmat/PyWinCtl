from importlib.metadata import version as _importlib_version

from ._main import (
    Re,
    Window,
    checkPermissions,
    displayWindowsUnderMouse,
    getActiveWindow,
    getActiveWindowTitle,
    getAllAppsNames,
    getAllAppsWindowsTitles,
    getAllScreens,
    getAllTitles,
    getAllWindows,
    getAllWindowsDict,
    getAppsWithName,
    getMousePos,
    getScreenSize,
    getTopWindowAt,
    getWindowsAt,
    getWindowsWithTitle,
    getWorkArea,
)

__all__ = [  # noqa: RUF022
    "version", "Re",
    # OS Specifics
    "Window", "checkPermissions", "getActiveWindow", "getActiveWindowTitle", "getWindowsWithTitle",
    "getAllWindows", "getAllTitles", "getAppsWithName", "getAllAppsNames", "getAllAppsWindowsTitles",
    "getAllWindowsDict", "getTopWindowAt", "getWindowsAt", "displayWindowsUnderMouse",
    "getAllScreens", "getScreenSize", "getWorkArea", "getMousePos"
]

__version__ = _importlib_version("pywinctl")


def version(numberOnly: bool = True) -> str:
    """Returns the current version of PyWinCtl module, in the form ''x.x.xx'' as string"""
    return ("" if numberOnly else "PyWinCtl-")+__version__


