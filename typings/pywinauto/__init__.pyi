import sys

assert sys.platform == "win32"  # pyright: ignore[reportInvalidStubStatement]

from .pywinauto import Application as Application
from .pywinauto import WindowSpecification as WindowSpecification

