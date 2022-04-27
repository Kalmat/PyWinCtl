#!/usr/bin/python
# -*- coding: utf-8 -*-

import subprocess
import sys
import time

import pytest
import pywinctl


def test_basic():

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

        basic_macOS(npw)

        subprocess.Popen(['rm', 'test.py'])

    else:
        raise NotImplementedError('PyWinCtl currently does not support this platform. If you have useful knowledge, please contribute! https://github.com/Kalmat/pywinctl')


def basic_win32(npw):

    assert npw is not None

    wait = True
    timelap = 0.5

    # Test maximize/minimize/restore.
    if npw.isMaximized:  # Make sure it starts un-maximized
        npw.restore(wait=wait)

    assert not npw.isMaximized

    npw.maximize(wait=wait)
    assert npw.isMaximized
    npw.restore(wait=wait)
    assert not npw.isMaximized

    npw.minimize(wait=wait)
    assert npw.isMinimized
    npw.restore(wait=wait)
    assert not npw.isMinimized

    # Test resizing
    npw.resizeTo(800, 600, wait=wait)
    assert npw.size == (800, 600)
    assert npw.width == 800
    assert npw.height == 600

    npw.resizeRel(10, 20, wait=wait)
    assert npw.size == (810, 620)
    assert npw.width == 810
    assert npw.height == 620

    # Test moving
    npw.moveTo(100, 200, wait=wait)
    assert npw.topleft == (100, 200)
    assert npw.left == 100
    assert npw.top == 200
    assert npw.right == 910
    assert npw.bottom == 820
    assert npw.bottomright == (910, 820)
    assert npw.bottomleft == (100, 820)
    assert npw.topright == (910, 200)

    npw.moveRel(1, 2, wait=wait)
    assert npw.topleft == (101, 202)
    assert npw.left == 101
    assert npw.top == 202
    assert npw.right == 911
    assert npw.bottom == 822
    assert npw.bottomright == (911, 822)
    assert npw.bottomleft == (101, 822)
    assert npw.topright == (911, 202)

    # Move via the properties
    npw.resizeTo(800, 600)
    npw.moveTo(200, 200)

    npw.left = 250
    time.sleep(timelap)
    assert npw.left == 250

    npw.right = 950
    time.sleep(timelap)
    assert npw.right == 950

    npw.top = 150
    time.sleep(timelap)
    assert npw.top == 150

    npw.bottom = 775
    time.sleep(timelap)
    assert npw.bottom == 775

    npw.topleft = (155, 350)
    time.sleep(timelap)
    assert npw.topleft == (155, 350)

    npw.topright = (1000, 300)
    time.sleep(timelap)
    assert npw.topright == (1000, 300)

    npw.bottomleft = (300, 975)
    time.sleep(timelap)
    assert npw.bottomleft == (300, 975)

    npw.bottomright = (1000, 900)
    time.sleep(timelap)
    assert npw.bottomright == (1000, 900)

    npw.midleft = (300, 400)
    time.sleep(timelap)
    assert npw.midleft == (300, 400)

    npw.midright = (1050, 600)
    time.sleep(timelap)
    assert npw.midright == (1050, 600)

    npw.midtop = (500, 350)
    time.sleep(timelap)
    assert npw.midtop == (500, 350)

    npw.midbottom = (500, 800)
    time.sleep(timelap)
    assert npw.midbottom == (500, 800)

    npw.center = (500, 350)
    time.sleep(timelap)
    assert npw.center == (500, 350)

    npw.centerx = 1000
    time.sleep(timelap)
    assert npw.centerx == 1000

    npw.centery = 600
    time.sleep(timelap)
    assert npw.centery == 600

    npw.width = 700
    time.sleep(timelap)
    assert npw.width == 700

    npw.height = 500
    time.sleep(timelap)
    assert npw.height == 500

    npw.size = (801, 601)
    time.sleep(timelap)
    assert npw.size == (801, 601)

    # Test window stacking
    npw.lowerWindow()
    time.sleep(timelap)
    npw.raiseWindow()
    time.sleep(timelap)
    npw.alwaysOnTop()
    time.sleep(timelap)
    npw.alwaysOnTop(aot=False)
    time.sleep(timelap)
    npw.alwaysOnBottom()
    time.sleep(timelap)
    npw.alwaysOnBottom(aob=False)
    time.sleep(timelap)
    npw.sendBehind()
    time.sleep(timelap)
    npw.sendBehind(sb=False)
    time.sleep(timelap)

    # Test parent methods
    parent = npw.getParent()
    assert npw.isChild(parent)

    # Test menu options
    menu = npw.menu.getMenu()
    submenu = {}
    for i, key in enumerate(menu.keys()):
        if i == 4:
            submenu = menu[key]["entries"]
    option = {}
    for i, key in enumerate(submenu.keys()):
        if i == 3:
            option = submenu[key]
    if option:
        npw.menu.clickMenuItem(wID=option["wID"])
        time.sleep(5)

    # Test closing
    npw.close()


def basic_linux(npw):
    # WARNING: Xlib/EWMH does not support negative positions, so be careful with positions calculations
    # and/or set proper screen resolution to avoid negative values (tested OK on 1920x1200)

    assert npw is not None

    wait = True
    timelap = 0.5

    # Test maximize/minimize/restore.
    if npw.isMaximized:  # Make sure it starts un-maximized
        npw.restore(wait=wait)

    assert not npw.isMaximized

    npw.maximize(wait=wait)
    assert npw.isMaximized
    npw.restore(wait=wait)
    assert not npw.isMaximized

    npw.minimize(wait=wait)
    assert npw.isMinimized
    npw.restore(wait=wait)
    assert not npw.isMinimized

    # Test resizing
    npw.resizeTo(800, 600, wait=wait)
    assert npw.size == (800, 600)
    assert npw.width == 800
    assert npw.height == 600

    npw.resizeRel(10, 20, wait=wait)
    assert npw.size == (810, 620)
    assert npw.width == 810
    assert npw.height == 620

    # Test moving
    npw.moveTo(100, 200, wait=wait)
    assert npw.topleft == (100, 200)
    assert npw.left == 100
    assert npw.top == 200
    assert npw.right == 910
    assert npw.bottom == 820
    assert npw.bottomright == (910, 820)
    assert npw.bottomleft == (100, 820)
    assert npw.topright == (910, 200)

    npw.moveRel(1, 2, wait=wait)
    assert npw.topleft == (101, 202)
    assert npw.left == 101
    assert npw.top == 202
    assert npw.right == 911
    assert npw.bottom == 822
    assert npw.bottomright == (911, 822)
    assert npw.bottomleft == (101, 822)
    assert npw.topright == (911, 202)

    # Move via the properties
    npw.resizeTo(800, 600)
    npw.moveTo(200, 200)

    npw.left = 250
    time.sleep(timelap)
    assert npw.left == 250

    npw.right = 950
    time.sleep(timelap)
    assert npw.right == 950

    npw.top = 150
    time.sleep(timelap)
    assert npw.top == 150

    npw.bottom = 775
    time.sleep(timelap)
    assert npw.bottom == 775

    npw.topleft = (155, 350)
    time.sleep(timelap)
    assert npw.topleft == (155, 350)

    npw.topright = (1000, 300)
    time.sleep(timelap)
    assert npw.topright == (1000, 300)

    npw.bottomleft = (300, 975)
    time.sleep(timelap)
    assert npw.bottomleft == (300, 975)

    npw.bottomright = (1000, 900)
    time.sleep(timelap)
    assert npw.bottomright == (1000, 900)

    npw.midleft = (300, 400)
    time.sleep(timelap)
    assert npw.midleft == (300, 400)

    npw.midright = (1050, 600)
    time.sleep(timelap)
    assert npw.midright == (1050, 600)

    npw.midtop = (500, 350)
    time.sleep(timelap)
    assert npw.midtop == (500, 350)

    npw.midbottom = (500, 800)
    time.sleep(timelap)
    assert npw.midbottom == (500, 800)

    npw.center = (500, 350)
    time.sleep(timelap)
    assert npw.center == (500, 350)

    npw.centerx = 1000
    time.sleep(timelap)
    assert npw.centerx == 1000

    npw.centery = 600
    time.sleep(timelap)
    assert npw.centery == 600

    npw.width = 700
    time.sleep(timelap)
    assert npw.width == 700

    npw.height = 500
    time.sleep(timelap)
    assert npw.height == 500

    npw.size = (801, 601)
    time.sleep(timelap)
    assert npw.size == (801, 601)

    # Test window stacking
    npw.lowerWindow()
    time.sleep(timelap)
    npw.raiseWindow()
    time.sleep(timelap)
    npw.alwaysOnTop()
    time.sleep(timelap)
    npw.alwaysOnTop(aot=False)
    time.sleep(timelap)
    npw.alwaysOnBottom()
    time.sleep(timelap)
    npw.alwaysOnBottom(aob=False)
    time.sleep(timelap)
    npw.sendBehind()
    time.sleep(timelap)
    npw.sendBehind(sb=False)
    time.sleep(timelap)

    # Test parent methods
    parent = npw.getParent()
    assert npw.isChild(parent)

    # Test closing
    npw.close()


def basic_macOS(npw):

    assert npw is not None

    wait = True
    timelap = 0.00

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
    npw.moveTo(50, 24, wait=wait)
    assert npw.topleft == (50, 24)
    assert npw.left == 50
    assert npw.top == 24
    assert npw.right == 660
    assert npw.bottom == 444
    assert npw.bottomright == (660, 444)
    assert npw.bottomleft == (50, 444)
    assert npw.topright == (660, 24)

    npw.moveRel(1, 2, wait=wait)
    assert npw.topleft == (51, 26)
    assert npw.left == 51
    assert npw.top == 26
    assert npw.right == 661
    assert npw.bottom == 446
    assert npw.bottomright == (661, 446)
    assert npw.bottomleft == (51, 446)
    assert npw.topright == (661, 26)

    # Move via the properties
    npw.resizeTo(601, 401, wait=wait)
    npw.moveTo(100, 250, wait=wait)

    npw.left = 200
    time.sleep(timelap)
    assert npw.left == 200

    npw.right = 200
    time.sleep(timelap)
    assert npw.right == 200

    npw.top = 200
    time.sleep(timelap)
    assert npw.top == 200

    npw.bottom = 800
    time.sleep(timelap)
    assert npw.bottom == 800

    npw.topleft = (300, 400)
    time.sleep(timelap)
    assert npw.topleft == (300, 400)

    npw.topright = (300, 400)
    time.sleep(timelap)
    assert npw.topright == (300, 400)

    npw.bottomleft = (300, 700)
    time.sleep(timelap)
    assert npw.bottomleft == (300, 700)

    npw.bottomright = (300, 900)
    time.sleep(timelap)
    assert npw.bottomright == (300, 900)

    npw.midleft = (300, 400)
    time.sleep(timelap)
    assert npw.midleft == (300, 400)

    npw.midright = (300, 400)
    time.sleep(timelap)
    assert npw.midright == (300, 400)

    npw.midtop = (300, 400)
    time.sleep(timelap)
    assert npw.midtop == (300, 400)

    npw.midbottom = (300, 700)
    time.sleep(timelap)
    assert npw.midbottom == (300, 700)

    npw.center = (300, 400)
    time.sleep(timelap)
    assert npw.center == (300, 400)

    npw.centerx = 1000
    time.sleep(timelap)
    assert npw.centerx == 1000

    npw.centery = 300
    time.sleep(timelap)
    assert npw.centery == 300

    npw.width = 600
    time.sleep(timelap)
    assert npw.width == 600

    npw.height = 400
    time.sleep(timelap)
    assert npw.height == 400

    npw.size = (810, 610)
    time.sleep(timelap)
    assert npw.size == (810, 610)

    npw.lowerWindow()
    time.sleep(timelap)

    npw.raiseWindow()
    time.sleep(timelap)

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
    for i, key in enumerate(menu.keys()):
        if i == 1:
            submenu = menu[key]["entries"]
    option = {}
    for i, key in enumerate(submenu.keys()):
        if i == 0:
            option = submenu[key]
    if option:
        npw.menu.clickMenuItem(wID=option["wID"])
        time.sleep(5)

    # Test closing
    npw.close()


def main():
    test_basic()


if __name__ == '__main__':
    main()
