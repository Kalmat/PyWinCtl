import sys

assert sys.platform == "linux"  # pyright: ignore[reportInvalidStubStatement]

from .ewmh import EWMH as EWMH
