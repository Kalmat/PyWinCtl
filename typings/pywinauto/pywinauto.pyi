import sys

assert sys.platform == "win32"  # pyright: ignore[reportInvalidStubStatement]
from typing import NamedTuple


class Rect(NamedTuple):
    left: int
    top: int
    right: int
    bottom: int


class WindowSpecification:
    def __init__(
            self
    ) -> None: ...
    def child_window(
            self,
            path: str | None = None,
            title_re: str | None = None,
            title: str | None = None,
            best_match: str | None = None,
            found_index: int | None = None
    ) -> WindowSpecification | None: ...
    def rectangle(
            self
    ) -> Rect | None: ...


class Application:
    backend: str
    def __init__(
            self,
            backend: str | None = ...,
    ) -> None: ...
    def connect(
            self,
            path: str | None = None
    ) -> WindowSpecification | None: ...
    def window(
            self,
            class_name: str | None = None
    ) -> WindowSpecification | None: ...
