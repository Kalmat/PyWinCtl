import sys

assert sys.platform == "linux"  # pyright: ignore[reportInvalidStubStatement]
# TODO: Push this upstream or upload to Typeshed
# https://github.com/parkouss/pyewmh/pull/19
from collections.abc import Iterable
from typing import Any

from typing_extensions import Literal, TypeAlias
from Xlib.display import Display
from Xlib.xobject.drawable import Window

_GetAttrsProperty: TypeAlias = Literal[
    "_NET_CLIENT_LIST",
    "_NET_CLIENT_LIST_STACKING",
    "_NET_NUMBER_OF_DESKTOPS",
    "_NET_DESKTOP_GEOMETRY",
    "_NET_DESKTOP_VIEWPORT",
    "_NET_CURRENT_DESKTOP",
    "_NET_ACTIVE_WINDOW",
    "_NET_WORKAREA",
    "_NET_SHOWING_DESKTOP",
    "_NET_WM_NAME",
    "_NET_WM_VISIBLE_NAME",
    "_NET_WM_DESKTOP",
    "_NET_WM_WINDOW_TYPE",
    "_NET_WM_STATE",
    "_NET_WM_ALLOWED_ACTIONS",
    "_NET_WM_PID",
]
_SetAttrsProperty: TypeAlias = Literal[
    "_NET_NUMBER_OF_DESKTOPS",
    "_NET_DESKTOP_GEOMETRY",
    "_NET_DESKTOP_VIEWPORT",
    "_NET_CURRENT_DESKTOP",
    "_NET_ACTIVE_WINDOW",
    "_NET_SHOWING_DESKTOP",
    "_NET_CLOSE_WINDOW",
    "_NET_MOVERESIZE_WINDOW",
    "_NET_WM_NAME",
    "_NET_WM_VISIBLE_NAME",
    "_NET_WM_DESKTOP",
    "_NET_WM_STATE",
]

class EWMH:
    NET_WM_WINDOW_TYPES: tuple[
        Literal["_NET_WM_WINDOW_TYPE_DESKTOP"],
        Literal["_NET_WM_WINDOW_TYPE_DOCK"],
        Literal["_NET_WM_WINDOW_TYPE_TOOLBAR"],
        Literal["_NET_WM_WINDOW_TYPE_MENU"],
        Literal["_NET_WM_WINDOW_TYPE_UTILITY"],
        Literal["_NET_WM_WINDOW_TYPE_SPLASH"],
        Literal["_NET_WM_WINDOW_TYPE_DIALOG"],
        Literal["_NET_WM_WINDOW_TYPE_DROPDOWN_MENU"],
        Literal["_NET_WM_WINDOW_TYPE_POPUP_MENU"],
        Literal["_NET_WM_WINDOW_TYPE_NOTIFICATION"],
        Literal["_NET_WM_WINDOW_TYPE_COMBO"],
        Literal["_NET_WM_WINDOW_TYPE_DND"],
        Literal["_NET_WM_WINDOW_TYPE_NORMAL"],
    ]
    NET_WM_ACTIONS: tuple[
        Literal["_NET_WM_ACTION_MOVE"],
        Literal["_NET_WM_ACTION_RESIZE"],
        Literal["_NET_WM_ACTION_MINIMIZE"],
        Literal["_NET_WM_ACTION_SHADE"],
        Literal["_NET_WM_ACTION_STICK"],
        Literal["_NET_WM_ACTION_MAXIMIZE_HORZ"],
        Literal["_NET_WM_ACTION_MAXIMIZE_VERT"],
        Literal["_NET_WM_ACTION_FULLSCREEN"],
        Literal["_NET_WM_ACTION_CHANGE_DESKTOP"],
        Literal["_NET_WM_ACTION_CLOSE"],
        Literal["_NET_WM_ACTION_ABOVE"],
        Literal["_NET_WM_ACTION_BELOW"],
    ]
    NET_WM_STATES: tuple[
        Literal["_NET_WM_STATE_MODAL"],
        Literal["_NET_WM_STATE_STICKY"],
        Literal["_NET_WM_STATE_MAXIMIZED_VERT"],
        Literal["_NET_WM_STATE_MAXIMIZED_HORZ"],
        Literal["_NET_WM_STATE_SHADED"],
        Literal["_NET_WM_STATE_SKIP_TASKBAR"],
        Literal["_NET_WM_STATE_SKIP_PAGER"],
        Literal["_NET_WM_STATE_HIDDEN"],
        Literal["_NET_WM_STATE_FULLSCREEN"],
        Literal["_NET_WM_STATE_ABOVE"],
        Literal["_NET_WM_STATE_BELOW"],
        Literal["_NET_WM_STATE_DEMANDS_ATTENTION"],
    ]
    display: Display
    root: Window
    def __init__(
        self, _display: Display | None = ..., root: Window | None = ...
    ) -> None: ...
    def setNumberOfDesktops(self, nb: int) -> None: ...
    def setDesktopGeometry(self, w: int, h: int) -> None: ...
    def setDesktopViewport(self, w: int, h: int) -> None: ...
    def setCurrentDesktop(self, i: int) -> None: ...
    def setActiveWindow(self, win: Window) -> None: ...
    def setShowingDesktop(self, show: bool | int) -> None: ...
    def setCloseWindow(self, win: Window) -> None: ...
    def setWmName(self, win: Window, name: str) -> None: ...
    def setWmVisibleName(self, win: Window, name: str) -> None: ...
    def setWmDesktop(self, win: Window, i: int) -> None: ...
    def setMoveResizeWindow(
        self,
        win: Window,
        gravity: int = ...,
        x: int | None = ...,
        y: int | None = ...,
        w: int | None = ...,
        h: int | None = ...,
    ) -> None: ...
    def setWmState(
        self, win: Window, action: int, state: int | str, state2: int | str = ...
    ) -> None: ...
    def getClientList(self) -> list[Window | None]: ...
    def getClientListStacking(self) -> list[Window | None]: ...
    def getNumberOfDesktops(self) -> int: ...
    def getDesktopGeometry(self) -> tuple[int, int]: ...
    def getDesktopViewPort(self) -> tuple[int, int]: ...
    def getCurrentDesktop(self) -> int: ...
    def getActiveWindow(self) -> Window | None: ...
    def getWorkArea(self) -> tuple[int, int, int, int]: ...
    def getShowingDesktop(self) -> int: ...
    def getWmName(self, win: Window) -> str: ...
    def getWmVisibleName(self, win: Window) -> str: ...
    def getWmDesktop(self, win: Window) -> int | None: ...
    def getWmWindowType(
        self, win: Window, str: bool = ...
    ) -> list[str] | list[int]: ...
    def getWmState(self, win: Window, str: bool = ...) -> list[str] | list[int]: ...
    def getWmAllowedActions(self, win: Window, str: bool) -> list[int] | list[str]: ...
    def getWmPid(self, win: Window) -> int | None: ...
    def getReadableProperties(
        self,
    ) -> Iterable[_GetAttrsProperty]: ...
    # Another good candidate for AnyOf: https://github.com/python/typing/issues/566
    def getProperty(
        self, prop: str, *args: Window | bool, **kwargs: Window | bool
    ) -> Any: ...
    def getWritableProperties(self) -> Iterable[_SetAttrsProperty]: ...
    def setProperty(
        self,
        prop: str,
        *args: Window | str | int | bool | None,
        **kwargs: Window | str | int | bool | None
    ) -> None: ...
