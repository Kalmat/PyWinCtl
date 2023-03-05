#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple, Union, Tuple


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


BoundingBox = Rect  # BoundingBox is an alias for Rect class (just for retro-compatibility)


class Point(NamedTuple):
    x: int
    y: int


class Size(NamedTuple):
    width: int
    height: int


class MyBox:

    def __init__(self, windowBox: Box, onSet: Callable[[Box], None], onQuery: Callable[[], Box]):
        self._box: Box = windowBox
        self._onSet: Callable[[Box], None] = onSet
        self._onQuery: Callable[[], Box] = onQuery

    def __repr__(self):
        """Return a string of the constructor function call to create this Box object."""
        return "%s(left=%s, top=%s, width=%s, height=%s)" % (
            self.__class__.__name__,
            self._box.left,
            self._box.top,
            self._box.width,
            self._box.height,
        )

    def __str__(self):
        """Return a string representation of this Box object."""
        return "(%s, %s, w=%s, h=%s)" % (
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
        self._onSet(self._box)

    @property
    def right(self) -> int:
        self._box = self._onQuery()
        return self._box.left + self._box.width

    @right.setter
    def right(self, value: int):
        self._box = self._onQuery()
        self._box = Box(value - self._box.width, self._box.top, self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def top(self) -> int:
        self._box = self._onQuery()
        return self._box.top

    @top.setter
    def top(self, value: int):
        self._box = self._onQuery()
        self._box = Box(self._box.left, value, self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def bottom(self) -> int:
        self._box = self._onQuery()
        return int(self._box.top / abs(self._box.top) * (abs(self._box.top) + self._box.height))

    @bottom.setter
    def bottom(self, value: int):
        self._box = self._onQuery()
        self._box = Box(self._box.left, value - self._box.height, self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def width(self) -> int:
        self._box = self._onQuery()
        return self._box.width

    @width.setter
    def width(self, value: int):
        self._box = self._onQuery()
        self._box = Box(self._box.left, self._box.top, value, self._box.height)
        self._onSet(self._box)

    @property
    def height(self) -> int:
        self._box = self._onQuery()
        return self._box.height

    @height.setter
    def height(self, value: int):
        self._box = self._onQuery()
        self._box = Box(self._box.left, self._box.top, self._box.width, value)
        self._onSet(self._box)

    @property
    def position(self) -> Point:
        self._box = self._onQuery()
        return Point(self._box.left, self._box.top)

    @position.setter
    def position(self, value: Union[Point, Tuple[int, int]]):
        val: Point = Point(*value)
        self._box = self._onQuery()
        self._box = Box(val.x, val.y, self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def size(self) -> Size:
        self._box = self._onQuery()
        return Size(self._box.width, self._box.height)

    @size.setter
    def size(self, value: Union[Size, Tuple[int, int]]):
        val: Size = Size(*value)
        self._box = self._onQuery()
        self._box = Box(self._box.left, self._box.top, val.width, val.height)
        self._onSet(self._box)

    @property
    def box(self) -> Box:
        self._box = self._onQuery()
        return self._box

    @box.setter
    def box(self, value: Union[Box, Tuple[int, int, int, int]]):
        val: Box = Box(*value)
        self._box = val
        self._onSet(self._box)

    @property
    def bbox(self) -> BoundingBox:
        self._box = self._onQuery()
        return BoundingBox(self._box.left, self._box.top, self._box.left + self._box.width,
                           int((self._box.top / abs(self._box.top)) * (abs(self._box.top) + self._box.height)))

    @bbox.setter
    def bbox(self, value: Union[BoundingBox, Tuple[int, int, int, int]]):
        val: BoundingBox = BoundingBox(*value)
        self._box = Box(val.left, val.top, val.right - val.left, val.bottom - val.top)
        self._onSet(self._box)

    @property
    def rect(self) -> Rect:
        self._box = self._onQuery()
        return Rect(self._box.left, self._box.top, self._box.left + self._box.width,
                    int((self._box.top / abs(self._box.top)) * (abs(self._box.top) + self._box.height)))

    @rect.setter
    def rect(self, value: Union[Rect, Tuple[int, int, int, int]]):
        val: Rect = Rect(*value)
        self._box = Box(val.left, val.top, val.right - val.left, val.bottom - val.top)
        self._onSet(self._box)

    @property
    def topleft(self) -> Point:
        self._box = self._onQuery()
        return Point(self._box.left, self._box.top)

    @topleft.setter
    def topleft(self, value: Union[Point, Tuple[int, int]]):
        val: Point = Point(*value)
        self._box = self._onQuery()
        self._box = Box(val.x, val.y, self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def bottomleft(self) -> Point:
        self._box = self._onQuery()
        return Point(self._box.left, self._box.top + self._box.height)

    @bottomleft.setter
    def bottomleft(self, value: Union[Point, Tuple[int, int]]):
        val: Point = Point(*value)
        self._box = self._onQuery()
        self._box = Box(val.x, val.y - self._box.height, self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def topright(self) -> Point:
        self._box = self._onQuery()
        return Point(self._box.left + self._box.width, self._box.top)

    @topright.setter
    def topright(self, value: Union[Point, Tuple[int, int]]):
        val: Point = Point(*value)
        self._box = self._onQuery()
        self._box = Box(val.x - self._box.width, val.y, self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def bottomright(self) -> Point:
        self._box = self._onQuery()
        return Point(self._box.left + self._box.width, self._box.top + self._box.height)

    @bottomright.setter
    def bottomright(self, value: Union[Point, Tuple[int, int]]):
        val: Point = Point(*value)
        self._box = self._onQuery()
        self._box = Box(val.x - self._box.width, val.y - self._box.height, self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def midtop(self) -> Point:
        self._box = self._onQuery()
        return Point(self._box.left + (self._box.width // 2), self._box.top)

    @midtop.setter
    def midtop(self, value: Union[Point, Tuple[int, int]]):
        val: Point = Point(*value)
        self._box = self._onQuery()
        self._box = Box(val.x - (self._box.width // 2), val.y, self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def midbottom(self) -> Point:
        self._box = self._onQuery()
        return Point(self._box.left + (self._box.width // 2), self._box.top + self._box.height)

    @midbottom.setter
    def midbottom(self, value: Union[Point, Tuple[int, int]]):
        val: Point = Point(*value)
        self._box = self._onQuery()
        self._box = Box(val.x - (self._box.width // 2), val.y - self._box.height, self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def midleft(self) -> Point:
        self._box = self._onQuery()
        return Point(self._box.left, self._box.top + (self._box.height // 2))

    @midleft.setter
    def midleft(self, value: Union[Point, Tuple[int, int]]):
        val: Point = Point(*value)
        self._box = self._onQuery()
        self._box = Box(val.x, val.y - (self._box.height // 2), self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def midright(self) -> Point:
        self._box = self._onQuery()
        return Point(self._box.left + self._box.width, self._box.top + (self._box.height // 2))

    @midright.setter
    def midright(self, value: Union[Point, Tuple[int, int]]):
        val: Point = Point(*value)
        self._box = self._onQuery()
        self._box = Box(val.x - self._box.width, val.y - (self._box.height // 2), self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def center(self) -> Point:
        self._box = self._onQuery()
        return Point(self._box.left + (self._box.width // 2), self._box.top + (self._box.height // 2))

    @center.setter
    def center(self, value: Union[Point, Tuple[int, int]]):
        val: Point = Point(*value)
        self._box = self._onQuery()
        self._box = Box(val.x - (self._box.width // 2), val.y - (self._box.height // 2), self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def centerx(self) -> int:
        self._box = self._onQuery()
        return self._box.left + (self._box.width // 2)

    @centerx.setter
    def centerx(self, value: int):
        self._box = self._onQuery()
        self._box = Box(value - (self._box.width // 2), self._box.top, self._box.width, self._box.height)
        self._onSet(self._box)

    @property
    def centery(self) -> int:
        self._box = self._onQuery()
        return self._box.top + (self._box.height // 2)

    @centery.setter
    def centery(self, value: int):
        self._box = self._onQuery()
        self._box = Box(self._box.left, value - (self._box.height // 2), self._box.width, self._box.height)
        self._onSet(self._box)
