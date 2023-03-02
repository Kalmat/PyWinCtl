#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import math
from abc import abstractmethod
from collections.abc import Callable
from typing import NamedTuple, Optional


class Box(NamedTuple):
    left: int
    top: int
    width: int
    height: int


class Rect(NamedTuple):
    left: int
    top: int
    right: int
    bottom: int
BoundingBox = Rect  # BoundingBox is an alias for Rect class

class Point(NamedTuple):
    x: int
    y: int


class Size(NamedTuple):
    width: int
    height: int


class MyRect:

    def __init__(self, windowBox: Box, onSet: Callable[[Box, bool, bool], None], onQuery: Callable[[], Box]):
        self._box: Box = windowBox
        self._onSet: Callable[[Box], None] = onSet
        self._onQuery: Callable[[], Box] = onQuery

    def __repr__(self):
        """Return a string of the constructor function call to create this Rect object."""
        return "%s(left=%s, top=%s, width=%s, height=%s)" % (
            self.__class__.__name__,
            self._box.left,
            self._box.top,
            self._box.width,
            self._box.height,
        )

    def __str__(self):
        """Return a string representation of this Rect object."""
        return "(x=%s, y=%s, w=%s, h=%s)" % (
            self._box.left,
            self._box.top,
            self._box.width,
            self._box.height,
        )

    @property
    def left(self) -> int:
        self._box = self._onQuery()
        return self._box.left

    @left.setter
    def left(self, value: int):
        self._box = self._onQuery()
        self._box = Box(value, self._box.top, self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def right(self) -> int:
        self._box = self._onQuery()
        return self._box.left + self._box.width

    @right.setter
    def right(self, value: int):
        self._box = self._onQuery()
        self._box = Box(value - self._box.width, self._box.top, self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def top(self) -> int:
        self._box = self._onQuery()
        return self._box.top

    @top.setter
    def top(self, value: int):
        self._box = self._onQuery()
        self._box = Box(self._box.left, value, self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def bottom(self) -> int:
        self._box = self._onQuery()
        return int(math.copysign(1, self._box.top) * (abs(self._box.top) + self._box.height))

    @bottom.setter
    def bottom(self, value: int):
        self._box = self._onQuery()
        self._box = Box(self._box.left, value - self._box.height, self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def width(self) -> int:
        self._box = self._onQuery()
        return self._box.width

    @width.setter
    def width(self, value: int):
        self._box = self._onQuery()
        self._box = Box(self._box.left, self._box.top, value, self._box.height)
        self._onSet(self._box, False, True)

    @property
    def height(self) -> int:
        self._box = self._onQuery()
        return self._box.height

    @height.setter
    def height(self, value: int):
        self._box = self._onQuery()
        self._box = Box(self._box.left, self._box.top, self._box.width, value)
        self._onSet(self._box, False, True)

    @property
    def position(self) -> Point:
        self._box = self._onQuery()
        return Point(self._box.left, self._box.top)

    @position.setter
    def position(self, value: Point):
        self._box = self._onQuery()
        self._box = Box(value[0], value[1], self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def size(self) -> Size:
        self._box = self._onQuery()
        return Size(self._box.width, self._box.height)

    @size.setter
    def size(self, value: Size):
        self._box = self._onQuery()
        self._box = Box(self._box.left, self._box.top, value[0], value[1])
        self._onSet(self._box, False, True)

    @property
    def box(self) -> Box:
        self._box = self._onQuery()
        return self._box

    @box.setter
    def box(self, value: Box):
        self._box = value
        self._onSet(self._box, True, True)

    @property
    def bbox(self) -> BoundingBox:
        self._box = self._onQuery()
        return BoundingBox(self._box.left, self._box.top, self._box.left + self._box.width,
                           int(math.copysign(1, self._box.top) * (abs(self._box.top) + self._box.height)))

    @bbox.setter
    def bbox(self, value: BoundingBox):
        self._box = Box(value.left, value.top, value.right - value.left, value.bottom - value.top)
        self._onSet(self._box, True, True)

    @property
    def rect(self) -> Rect:
        self._box = self._onQuery()
        return Rect(self._box.left, self._box.top, self._box.left + self._box.width,
                    int(math.copysign(1, self._box.top) * (abs(self._box.top) + self._box.height)))

    @rect.setter
    def rect(self, value: Rect):
        self._box = Box(value.left, value.top, value.right - value.left, value.bottom - value.top)
        self._onSet(self._box, True, True)

    @property
    def topleft(self) -> Point:
        self._box = self._onQuery()
        return Point(x=self._box.left, y=self._box.top)

    @topleft.setter
    def topleft(self, value: Point):
        self._box = self._onQuery()
        self._box = Box(value[0], value[1], self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def bottomleft(self) -> Point:
        self._box = self._onQuery()
        return Point(x=self._box.left, y=self._box.top + self._box.height)

    @bottomleft.setter
    def bottomleft(self, value: Point):
        self._box = self._onQuery()
        self._box = Box(value[0], value[1] - self._box.height, self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def topright(self) -> Point:
        self._box = self._onQuery()
        return Point(x=self._box.left + self._box.width, y=self._box.top)

    @topright.setter
    def topright(self, value: Point):
        self._box = self._onQuery()
        self._box = Box(value[0] - self._box.width, value[1], self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def bottomright(self) -> Point:
        self._box = self._onQuery()
        return Point(x=self._box.left + self._box.width, y=self._box.top + self._box.height)

    @bottomright.setter
    def bottomright(self, value: Point):
        self._box = self._onQuery()
        self._box = Box(value[0] - self._box.width, value[1] - self._box.height, self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def midtop(self) -> Point:
        self._box = self._onQuery()
        return Point(x=self._box.left + (self._box.width // 2), y=self._box.top)

    @midtop.setter
    def midtop(self, value: Point):
        self._box = self._onQuery()
        self._box = Box(value[0] - (self._box.width // 2), value[1], self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def midbottom(self) -> Point:
        self._box = self._onQuery()
        return Point(x=self._box.left + (self._box.width // 2), y=self._box.top + self._box.height)

    @midbottom.setter
    def midbottom(self, value: Point):
        self._box = self._onQuery()
        self._box = Box(value[0] - (self._box.width // 2), value[1] - self._box.height, self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def midleft(self) -> Point:
        self._box = self._onQuery()
        return Point(x=self._box.left, y=self._box.top + (self._box.height // 2))

    @midleft.setter
    def midleft(self, value: Point):
        self._box = self._onQuery()
        self._box = Box(value[0], value[1] - (self._box.height // 2), self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def midright(self) -> Point:
        self._box = self._onQuery()
        return Point(x=self._box.left + self._box.width, y=self._box.top + (self._box.height // 2))

    @midright.setter
    def midright(self, value: Point):
        self._box = self._onQuery()
        self._box = Box(value[0] - self._box.width, value[1] - (self._box.height // 2), self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def center(self) -> Point:
        self._box = self._onQuery()
        return Point(x=self._box.left + (self._box.width // 2), y=self._box.top + (self._box.height // 2))

    @center.setter
    def center(self, value: Point):
        self._box = self._onQuery()
        self._box = Box(value[0] - (self._box.width // 2), value[1] - (self._box.height // 2), self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def centerx(self) -> int:
        self._box = self._onQuery()
        return self._box.left + (self._box.width // 2)

    @centerx.setter
    def centerx(self, value: int):
        self._box = self._onQuery()
        self._box = Box(value - (self._box.width // 2), self._box.top, self._box.width, self._box.height)
        self._onSet(self._box, True, False)

    @property
    def centery(self) -> int:
        self._box = self._onQuery()
        return self._box.top + (self._box.height // 2)

    @centery.setter
    def centery(self, value: int):
        self._box = self._onQuery()
        self._box = Box(self._box.left, value - (self._box.height // 2), self._box.width, self._box.height)
        self._onSet(self._box, True, False)
