#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
import sys
import time
from typing import Any, cast

import pywinctl


def test_basic():

    print("PLATFORM:", sys.platform)
    print()
    print("MONITORS:")
    monitors = pywinctl.getAllScreens()
    for monitor in monitors.keys():
        print(monitor, monitors[monitor])
        print()
    print("ALL WINDOWS")
    print(pywinctl.getAllTitles())
    print()
    print("ALL APPS & WINDOWS")
    print(pywinctl.getAllAppsWindowsTitles())
    print()

    if sys.platform == "win32":
        subprocess.Popen('notepad')
        time.sleep(0.5)

        testWindows = [pywinctl.getActiveWindow()]
        # testWindows = pywinctl.getWindowsWithTitle('Untitled - Notepad')   # Not working in other languages
        assert len(testWindows) == 1

        npw = testWindows[0]

        basic_win32(npw)

    elif sys.platform == "linux":
        subprocess.Popen('gedit')
        time.sleep(5)

        testWindows = [pywinctl.getActiveWindow()]
        assert len(testWindows) == 1

        npw = testWindows[0]

        basic_linux(npw)

    elif sys.platform == "darwin":
        if not pywinctl.checkPermissions(activate=True):
            exit()
        subprocess.Popen(['touch', 'test.py'])
        time.sleep(2)
        subprocess.Popen(['open', '-a', 'TextEdit', 'test.py'])
        time.sleep(5)

        testWindows = pywinctl.getWindowsWithTitle('test.py')
        assert len(testWindows) == 1

        npw = testWindows[0]
        assert isinstance(npw, pywinctl.Window)

        npw = testWindows[0]

        basic_macOS(npw)

        subprocess.Popen(['rm', 'test.py'])

    else:
        raise NotImplementedError('PyWinCtl currently does not support this platform. If you have useful knowledge, please contribute! https://github.com/Kalmat/pywinctl')


if sys.platform == "win32":
    def basic_win32(npw: pywinctl.Window | None):

        assert npw is not None

        def test_move(attr, value):
            setattr(npw, attr, value)
            time.sleep(timelap)
            new_value = getattr(npw, attr)
            assert new_value == value, f"Error while moving the window using the attribute {attr}. Expected value {value}, instead found {new_value}"

        wait = True
        timelap = 0.50

        print("ACTIVE WINDOW:", npw.title, "/", npw.box)
        print()
        print("CLIENT FRAME:", npw.getClientFrame(), "EXTRA FRAME:", npw.getExtraFrameSize())
        print()
        print("MINIMIZED:", npw.isMinimized, "MAXIMIZED:", npw.isMaximized, "ACTIVE:", npw.isActive, "ALIVE:",
              npw.isAlive, "VISIBLE:", npw.isVisible)
        print()
        print("APP NAME:", npw.getAppName())
        print()
        dpys = npw.getDisplay()
        for dpy in dpys:
            print("WINDOW DISPLAY:", dpy)
            print()
        parent = npw.getParent()
        if parent:
            print("WINDOW PARENT:", parent)
            print()
        children = npw.getChildren()
        for child in children:
            print("WINDOW CHILD:", child)
            print()

        # Test maximize/minimize/restore.
        if npw.isMaximized:  # Make sure it starts un-maximized
            npw.restore(wait=wait)

        assert not npw.isMaximized

        npw.maximize(wait=wait)
        time.sleep(timelap)
        assert npw.isMaximized
        npw.restore(wait=wait)
        time.sleep(timelap)
        assert not npw.isMaximized

        npw.minimize(wait=wait)
        time.sleep(timelap)
        assert npw.isMinimized
        npw.restore(wait=wait)
        time.sleep(timelap)
        assert not npw.isMinimized

        # Test resizing
        npw.resizeTo(600, 400, wait=wait)
        time.sleep(timelap)
        assert npw.size == (600, 400)
        assert npw.width == 600
        assert npw.height == 400

        npw.resizeRel(10, 20, wait=wait)
        assert npw.size == (610, 420)
        assert npw.width == 610
        assert npw.height == 420

        # Test moving
        npw.moveTo(50, 54, wait=wait)
        assert npw.topleft == (50, 54)
        assert npw.left == 50
        assert npw.top == 54
        assert npw.right == 660
        assert npw.bottom == 474
        assert npw.bottomright == (660, 474)
        assert npw.bottomleft == (50, 474)
        assert npw.topright == (660, 54)

        npw.moveRel(1, 2, wait=wait)
        assert npw.topleft == (51, 56)
        assert npw.left == 51
        assert npw.top == 56
        assert npw.right == 661
        assert npw.bottom == 476
        assert npw.bottomright == (661, 476)
        assert npw.bottomleft == (51, 476)
        assert npw.topright == (661, 56)

        # Move via the properties
        npw.resizeTo(601, 401, wait=wait)
        npw.moveTo(100, 250, wait=wait)

        test_move('left', 200)
        test_move('right', 200)
        test_move('top', 200)
        test_move('bottom', 800)
        test_move('topleft', (300, 400))
        test_move('topright', (300, 400))
        test_move('bottomleft', (300, 700))
        test_move('bottomright', (300, 900))
        test_move('midleft', (300, 400))
        test_move('midright', (300, 400))
        test_move('midtop', (300, 400))
        test_move('midbottom', (300, 700))
        test_move('center', (300, 400))
        test_move('centerx', 1000)
        test_move('centery', 300)
        test_move('width', 600)
        test_move('height', 400)

        npw.centerx = 400
        npw.centery = 300
        test_move('size', (810, 610))

        lowered = npw.lowerWindow()
        time.sleep(timelap)
        assert lowered, 'Window has not been lowered'

        raised = npw.raiseWindow()
        time.sleep(timelap)
        assert raised, 'Window has not been raised'

        # Test window stacking
        npw.lowerWindow()
        time.sleep(timelap)
        npw.raiseWindow()
        time.sleep(timelap)

        # Test parent methods
        parent = npw.getParent()
        assert parent and npw.isChild(parent)

        # Test menu options
        menu = npw.menu.getMenu()
        submenu = {}
        for i, key in enumerate(menu):
            if i == 1:
                submenu = menu[key].get("entries", {})
        option: dict[str, Any] | None = None
        for i, key in enumerate(submenu):
            if i == 0:
                option = cast("dict[str, Any]", submenu[key])
        if option:
            npw.menu.clickMenuItem(wID=option.get("wID", ""))
            time.sleep(5)

        # Test closing
        npw.close()


if sys.platform == "linux":
    def basic_linux(npw: pywinctl.Window | None):
        # WARNING: Xlib/EWMH does not support negative positions, so be careful with positions calculations
        # and/or set proper screen resolution to avoid negative values (tested OK on 1920x1200)

        assert npw is not None

        def test_move(attr, value):
            setattr(npw, attr, value)
            time.sleep(timelap)
            new_value = getattr(npw, attr)
            assert new_value == value, f"Error while moving the window using the attribute {attr}. Expected value {value}, instead found {new_value}"

        wait = True
        timelap = 0.50

        print("ACTIVE WINDOW:", npw.title, "/", npw.box)
        print()
        print("CLIENT FRAME:", npw.getClientFrame(), "EXTRA FRAME:", npw.getExtraFrameSize())
        print()
        print("MINIMIZED:", npw.isMinimized, "MAXIMIZED:", npw.isMaximized, "ACTIVE:", npw.isActive, "ALIVE:",
              npw.isAlive, "VISIBLE:", npw.isVisible)
        print()
        print("APP NAME:", npw.getAppName())
        print()
        dpys = npw.getDisplay()
        for dpy in dpys:
            print("WINDOW DISPLAY:", dpy)
            print()
        parent = npw.getParent()
        if parent:
            print("WINDOW PARENT:", parent)
            print()
        children = npw.getChildren()
        for child in children:
            print("WINDOW CHILD:", child)
            print()

        # Test maximize/minimize/restore.
        if npw.isMaximized:  # Make sure it starts un-maximized
            npw.restore(wait=wait)

        assert not npw.isMaximized

        npw.maximize(wait=wait)
        time.sleep(timelap)
        assert npw.isMaximized
        npw.restore(wait=wait)
        time.sleep(timelap)
        assert not npw.isMaximized

        npw.minimize(wait=wait)
        time.sleep(timelap)
        assert npw.isMinimized
        npw.restore(wait=wait)
        time.sleep(timelap)
        assert not npw.isMinimized

        # Test resizing
        npw.resizeTo(600, 400, wait=wait)
        time.sleep(timelap)
        assert npw.size == (600, 400)
        assert npw.width == 600
        assert npw.height == 400

        npw.resizeRel(10, 20, wait=wait)
        assert npw.size == (610, 420)
        assert npw.width == 610
        assert npw.height == 420

        # Test moving
        npw.moveTo(50, 54, wait=wait)
        assert npw.topleft == (50, 54)
        assert npw.left == 50
        assert npw.top == 54
        assert npw.right == 660
        assert npw.bottom == 474
        assert npw.bottomright == (660, 474)
        assert npw.bottomleft == (50, 474)
        assert npw.topright == (660, 54)

        npw.moveRel(1, 2, wait=wait)
        assert npw.topleft == (51, 56)
        assert npw.left == 51
        assert npw.top == 56
        assert npw.right == 661
        assert npw.bottom == 476
        assert npw.bottomright == (661, 476)
        assert npw.bottomleft == (51, 476)
        assert npw.topright == (661, 56)

        # Move via the properties
        npw.resizeTo(601, 401, wait=wait)
        npw.moveTo(100, 250, wait=wait)

        test_move('left', 200)
        test_move('right', 860)
        test_move('top', 200)
        test_move('bottom', 800)
        test_move('topleft', (300, 400))
        test_move('topright', (800, 400))
        test_move('bottomleft', (300, 700))
        test_move('bottomright', (850, 900))
        test_move('midleft', (300, 400))
        test_move('midright', (770, 400))
        test_move('midtop', (800, 400))
        test_move('midbottom', (700, 700))
        test_move('center', (760, 400))
        test_move('centerx', 900)
        test_move('centery', 600)
        test_move('width', 600)
        test_move('height', 400)

        npw.centerx = 400
        npw.centery = 300
        test_move('size', (810, 610))

        lowered = npw.lowerWindow()
        time.sleep(timelap)
        assert lowered, 'Window has not been lowered'

        raised = npw.raiseWindow()
        time.sleep(timelap)
        assert raised, 'Window has not been raised'

        # Test window stacking
        npw.lowerWindow()
        time.sleep(timelap)
        npw.raiseWindow()
        time.sleep(timelap)

        # Test parent methods
        parent = npw.getParent()
        assert parent and npw.isChild(parent)

        # Test closing
        npw.close()

if sys.platform == "darwin":
    def basic_macOS(npw: pywinctl.Window):
        assert npw is not None
        
        def test_move(attr, value):
            setattr(npw, attr, value)
            time.sleep(timelap)
            new_value = getattr(npw, attr)
            assert new_value == value, f"Error while moving the window using the attribute {attr}. Expected value {value}, instead found {new_value}"

        wait = True
        timelap = 0.50
        
        print("ACTIVE WINDOW:", npw.title, "/", npw.box)
        print()
        print("CLIENT FRAME:", npw.getClientFrame(), "EXTRA FRAME:", npw.getExtraFrameSize())
        print()
        print("MINIMIZED:", npw.isMinimized, "MAXIMIZED:", npw.isMaximized, "ACTIVE:", npw.isActive, "ALIVE:",
              npw.isAlive, "VISIBLE:", npw.isVisible)
        print()
        print("APP NAME:", npw.getAppName())
        print()
        dpys = npw.getDisplay()
        for dpy in dpys:
            print("WINDOW DISPLAY:", dpy)
            print()
        parent = npw.getParent()
        if parent:
            print("WINDOW PARENT:", parent)
            print()
        children = npw.getChildren()
        for child in children:
            print("WINDOW CHILD:", child)
            print()

        # Test maximize/minimize/restore.
        if npw.isMaximized:  # Make sure it starts un-maximized
            npw.restore(wait=wait)

        assert not npw.isMaximized

        npw.maximize(wait=wait)
        time.sleep(timelap)
        assert npw.isMaximized
        npw.restore(wait=wait)
        time.sleep(timelap)
        assert not npw.isMaximized
        
        npw.minimize(wait=wait)
        time.sleep(timelap)
        assert npw.isMinimized
        npw.restore(wait=wait)
        time.sleep(timelap)
        assert not npw.isMinimized

        # Test resizing
        npw.resizeTo(600, 400, wait=wait)
        time.sleep(timelap)
        assert npw.size == (600, 400)
        assert npw.width == 600
        assert npw.height == 400

        npw.resizeRel(10, 20, wait=wait)
        assert npw.size == (610, 420)
        assert npw.width == 610
        assert npw.height == 420

        # Test moving
        npw.moveTo(50, 54, wait=wait)
        assert npw.topleft == (50, 54)
        assert npw.left == 50
        assert npw.top == 54
        assert npw.right == 660
        assert npw.bottom == 474
        assert npw.bottomright == (660, 474)
        assert npw.bottomleft == (50, 474)
        assert npw.topright == (660, 54)

        npw.moveRel(1, 2, wait=wait)
        assert npw.topleft == (51, 56)
        assert npw.left == 51
        assert npw.top == 56
        assert npw.right == 661
        assert npw.bottom == 476
        assert npw.bottomright == (661, 476)
        assert npw.bottomleft == (51, 476)
        assert npw.topright == (661, 56)

        # Move via the properties
        npw.resizeTo(601, 401, wait=wait)
        npw.moveTo(100, 250, wait=wait)
        
        test_move('left', 200)
        test_move('right', 200)
        test_move('top', 200)
        test_move('bottom', 800)
        test_move('topleft', (300, 400))
        test_move('topright', (300, 400))
        test_move('bottomleft', (300, 700))
        test_move('bottomright', (300, 900))
        test_move('midleft', (300, 400))
        test_move('midright', (300, 400))
        test_move('midtop', (300, 400))
        test_move('midbottom', (300, 700))
        test_move('center', (300, 400))
        test_move('centerx', 1000)
        test_move('centery', 300)
        test_move('width', 600)
        test_move('height', 400)

        npw.centerx = 400
        npw.centery = 300
        test_move('size', (810, 610))
        
        lowered = npw.lowerWindow()
        time.sleep(timelap)
        assert lowered, 'Window has not been lowered'

        raised = npw.raiseWindow()
        time.sleep(timelap)
        assert raised, 'Window has not been raised'

        # Test window stacking
        npw.lowerWindow()
        time.sleep(timelap)
        npw.raiseWindow()
        time.sleep(timelap)
        
        # Test parent methods
        parent = npw.getParent()
        assert parent and npw.isChild(parent)

        # Test menu options
        menu = npw.menu.getMenu()
        submenu = {}
        for i, key in enumerate(menu):
            if i == 1:
                submenu = menu[key].get("entries", {})
        option: dict[str, Any] | None = None
        for i, key in enumerate(submenu):
            if i == 0:
                option = cast("dict[str, Any]", submenu[key])
        if option:
            npw.menu.clickMenuItem(wID=option.get("wID", ""))
            time.sleep(5)

        # Test closing
        npw.close()


def main():
    test_basic()


if __name__ == '__main__':
    main()
