import sys

assert sys.platform == "darwin"

# https://github.com/ronaldoussoren/pyobjc/issues/198
# https://github.com/ronaldoussoren/pyobjc/issues/417
# https://github.com/ronaldoussoren/pyobjc/issues/419
from typing import Any

import objc as objc
from AppKit import *
from Quartz.CoreGraphics import *
from Quartz.CoreVideo import *
from Quartz.ImageIO import *
from Quartz.ImageKit import *
from Quartz.PDFKit import *
from Quartz.QuartzComposer import *
from Quartz.QuartzCore import *
from Quartz.QuartzFilters import *
from Quartz.QuickLookUI import *

def __getattr__(name: str, /) -> Any: ...  # pyright: ignore[reportIncompleteStub]
