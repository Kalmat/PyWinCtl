#!/usr/bin/env python
# encoding: utf-8

# Lawrence Akka - https://sourceforge.net/p/pyobjc/mailman/pyobjc-dev/thread/0B4BC391-6491-445D-92D0-7B1CEF6F51BE%40me.com/#msg27726282

# We need to import the relevant object definitions from PyObjC

import sys
assert sys.platform == "darwin"

import time

from AppKit import (
    NSApp, NSObject, NSApplication, NSMakeRect, NSWindow, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable, NSBackingStoreBuffered)

import pywinctl


# Cocoa prefers composition to inheritance. The members of an object's
# delegate will be called upon the happening of certain events. Once we define
# methods with particular names, they will be called automatically
class Delegate(NSObject):

    npw = None
    demoMode = False

    def getDemoMode(self):
        return self.demoMode

    def setDemoMode(self):
        self.demoMode = True

    def unsetDemoMode(self):
        self.demoMode = False

    def applicationDidFinishLaunching_(self, aNotification: None):
        '''Called automatically when the application has launched'''
        # Set it as the frontmost application
        NSApp().activateIgnoringOtherApps_(True)
        for win in NSApp().orderedWindows():
            print(win.title(), win.frame(), type(win.frame().origin))

        if self.demoMode:

            if not self.npw:
                self.npw = pywinctl.getActiveWindow(NSApp())

                if self.npw:
                    print("ACTIVE WINDOW:", self.npw.title)

                    def moveChanged(pos):
                        print("CHANGED!!!", pos, self.npw.box, self.npw.rect)

                    self.npw.watchdog.start(movedCB=moveChanged)

                else:
                    print("NO ACTIVE WINDOW FOUND")
                    return

            wait = True
            timelap = 0.3

            self.npw.maximize(wait=wait)
            time.sleep(timelap)
            assert self.npw.isMaximized
            self.npw.restore(wait=wait)
            time.sleep(timelap)
            assert not self.npw.isMaximized

            self.npw.minimize(wait=wait)
            time.sleep(timelap)
            assert self.npw.isMinimized
            self.npw.restore(wait=wait)
            time.sleep(timelap)
            assert not self.npw.isMinimized

            self.npw.hide(wait=wait)
            time.sleep(timelap)
            assert not self.npw.visible
            self.npw.show(wait=wait)
            time.sleep(timelap)
            assert self.npw.visible

            # Test resizing
            self.npw.resizeTo(600, 400, wait=wait)
            print("RESIZE", self.npw.size)
            time.sleep(timelap)
            assert self.npw.size == (600, 400)
            assert self.npw.width == 600
            assert self.npw.height == 400

            self.npw.resizeRel(10, 20, wait=wait)
            print("RESIZEREL", self.npw.size)
            time.sleep(timelap)
            assert self.npw.size == (610, 420)
            assert self.npw.width == 610
            assert self.npw.height == 420

            # Test moving
            self.npw.moveTo(600, 300, wait=wait)
            print("MOVE", self.npw.topleft)
            time.sleep(timelap)
            assert self.npw.topleft == (600, 300)
            assert self.npw.left == 600
            assert self.npw.top == 300
            assert self.npw.right == 1210
            assert self.npw.bottom == 720
            assert self.npw.bottomright == (1210, 720)
            assert self.npw.bottomleft == (600, 720)
            assert self.npw.topright == (1210, 300)

            self.npw.moveRel(1, 2, wait=wait)
            print("MOVEREL", self.npw.topleft)
            time.sleep(timelap)
            assert self.npw.topleft == (601, 302)
            assert self.npw.left == 601
            assert self.npw.top == 302
            assert self.npw.right == 1211
            assert self.npw.bottom == 722
            assert self.npw.bottomright == (1211, 722)
            assert self.npw.bottomleft == (601, 722)
            assert self.npw.topright == (1211, 302)

            # Move via the properties
            self.npw.resizeTo(601, 401, wait=wait)
            print("RESIZE", self.npw.size)
            time.sleep(timelap)
            self.npw.moveTo(100, 600, wait=wait)
            print("MOVE moveTo(100, 600)", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            self.npw.left = 200
            print("MOVE left = 200", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.left == 200

            self.npw.right = 200
            print("MOVE right = 200", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.right == 200

            self.npw.top = 200
            print("MOVE top = 200", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.top == 200

            self.npw.bottom = 800
            print("MOVE bottom = 800", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.bottom == 800

            self.npw.topleft = (300, 400)
            print("MOVE topleft = (300, 400)", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.topleft == (300, 400)

            self.npw.topright = (300, 400)
            print("MOVE topright = (300, 400)", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.topright == (300, 400)

            self.npw.bottomleft = (300, 700)
            print("MOVE bottomleft = (300, 700)", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.bottomleft == (300, 700)

            self.npw.bottomright = (300, 900)
            print("MOVE bottomright = (300, 900)", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.bottomright == (300, 900)

            self.npw.midleft = (300, 400)
            print("MOVE midleft = (300, 400)", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.midleft == (300, 400)

            self.npw.midright = (300, 400)
            print("MOVE midright = (300, 400)", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.midright == (300, 400)

            self.npw.midtop = (300, 400)
            print("MOVE midtop = (300, 400)", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.midtop == (300, 400)

            self.npw.midbottom = (300, 700)
            print("MOVE midbottom = (300, 700)", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.midbottom == (300, 700)

            self.npw.center = (300, 400)
            print("MOVE center = (300, 400)", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.center == (300, 400)

            self.npw.centerx = 1000
            print("MOVE centerx = 1000", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.centerx == 1000

            self.npw.centery = 300
            print("MOVE centery = 300", self.npw.box, self.npw.rect)
            time.sleep(timelap)
            assert self.npw.centery == 300

            self.npw.width = 600
            print("RESIZE width = 600", self.npw.size)
            time.sleep(timelap)
            assert self.npw.width == 600

            self.npw.height = 400
            print("RESIZE height = 400", self.npw.size)
            time.sleep(timelap)
            assert self.npw.height == 400

            self.npw.size = (810, 610)
            print("RESIZE size = (810, 610)", self.npw.size)
            time.sleep(timelap)
            assert self.npw.size == (810, 610)

            # Test lower and raise window
            print("LOWER")
            self.npw.lowerWindow()
            time.sleep(timelap)
            print("RAISE")
            self.npw.raiseWindow()
            time.sleep(timelap)

            # Test managing window stacking
            print("ALWAYS ON TOP")
            self.npw.alwaysOnTop()
            time.sleep(timelap)
            print("DEACTIVATE AOT")
            self.npw.alwaysOnTop(aot=False)
            time.sleep(timelap)
            print("ALWAYS AT BOTTOM")
            self.npw.alwaysOnBottom()
            time.sleep(timelap)
            print("DEACTIVATE AOB")
            self.npw.alwaysOnBottom(aob=False)
            time.sleep(timelap)
            print("SEND BEHIND")
            self.npw.sendBehind()
            time.sleep(timelap)
            print("BRING FROM BEHIND")
            self.npw.sendBehind(sb=False)
            time.sleep(timelap)

            # Test parent methods
            print("GET PARENT")
            parent = self.npw.getParent()
            assert self.npw.isChild(parent)

            # Test visibility
            print("HIDE")
            self.npw.hide()
            time.sleep(timelap)
            assert not self.npw.isVisible
            assert self.npw.isAlive
            print("SHOW")
            self.npw.show()
            time.sleep(timelap)
            assert self.npw.isVisible
            assert self.npw.isAlive

            # Test ClientFrame (called twice to assure no re-registration)
            print("CLIENT FRAME", self.npw.getClientFrame())
            print("CLIENT FRAME", self.npw.getClientFrame())

            # Test closing
            print("CLOSE")
            self.npw.close()
            assert not self.npw.isVisible
            assert not self.npw.isAlive

    def windowWillClose_(self, aNotification: None):
        '''Called automatically when the window is closed'''
        print("Window has been closed")
        # Terminate the application
        NSApp().terminate_(self)

    def windowDidBecomeKey_(self, aNotification: None):
        print("Now I'm ACTIVE")


def demo():
    # Create a new application instance ...
    a = NSApplication.sharedApplication()
    # ... and create its delegate.  Note the use of the
    # Objective C constructors below, because Delegate
    # is a subclass of an Objective C class, NSObject
    delegate = Delegate.alloc().init()
    delegate.setDemoMode()
    # Tell the application which delegate object to use.
    a.setDelegate_(delegate)

    # Now we can start to create the window ...
    frame = NSMakeRect(400, 400, 250, 100)
    # (Don't worry about these parameters for the moment. They just specify
    # the type of window, its size and position etc)
    mask = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable
    w = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(frame, mask, NSBackingStoreBuffered, False)

    # ... tell it which delegate object to use (here it happens
    # to be the same delegate as the application is using)...
    w.setDelegate_(delegate)
    # ... and set some properties. Unicode strings are preferred.
    w.setTitle_(u'Hello, World!')
    # All set. Now we can show the window ...
    w.orderFrontRegardless()

    # ... and start the application
    a.run()
    #AppHelper.runEventLoop()


if __name__ == '__main__':
    demo()

"""
Hello, World! <CoreFoundation.CGRect origin=<CoreFoundation.CGPoint x=400.0 y=400.0> size=<CoreFoundation.CGSize width=250.0 height=122.0>> <class 'CoreFoundation.CGPoint'>
ACTIVE WINDOW: Hello, World!
CHANGED!!! (87, 147) Box(left=87, top=147, width=1557, height=794) Rect(left=87, top=147, right=1644, bottom=941)
CHANGED!!! (0, 77) Box(left=0, top=77, width=1920, height=980) Rect(left=0, top=77, right=1920, bottom=1057)
CHANGED!!! (277, 301) Box(left=277, top=301, width=761, height=385) Rect(left=277, top=301, right=1038, bottom=686)
CHANGED!!! (400, 400) Box(left=400, top=400, width=250, height=122) Rect(left=400, top=400, right=650, bottom=522)
CHANGED!!! (400, 404) Box(left=400, top=404, width=262, height=132) Rect(left=400, top=404, right=662, bottom=536)
CHANGED!!! (400, 521) Box(left=400, top=521, width=600, height=401) Rect(left=400, top=521, right=1000, bottom=922)
RESIZE Size(width=600, height=400)
CHANGED!!! (400, 522) Box(left=400, top=522, width=600, height=400) Rect(left=400, top=522, right=1000, bottom=922)
RESIZEREL Size(width=610, height=420)
CHANGED!!! (400, 637) Box(left=400, top=637, width=610, height=420) Rect(left=400, top=637, right=1010, bottom=1057)
CHANGED!!! (431, 584) Box(left=431, top=584, width=610, height=421) Rect(left=431, top=584, right=1041, bottom=1005)
MOVE Point(x=600, y=300)
CHANGED!!! (600, 300) Box(left=600, top=300, width=610, height=420) Rect(left=600, top=300, right=1210, bottom=720)
MOVEREL Point(x=601, y=302)
CHANGED!!! (601, 302) Box(left=601, top=302, width=610, height=420) Rect(left=601, top=302, right=1211, bottom=722)
CHANGED!!! (601, 305) Box(left=601, top=305, width=610, height=420) Rect(left=601, top=305, right=1211, bottom=725)
CHANGED!!! (601, 656) Box(left=601, top=656, width=601, height=401) Rect(left=601, top=656, right=1202, bottom=1057)
RESIZE Size(width=601, height=401)
CHANGED!!! (131, 603) Box(left=131, top=603, width=602, height=402) Rect(left=131, top=603, right=733, bottom=1005)
MOVE moveTo(100, 600) Box(left=100, top=600, width=601, height=401) Rect(left=100, top=600, right=701, bottom=1001)
CHANGED!!! (100, 600) Box(left=100, top=600, width=601, height=401) Rect(left=100, top=600, right=701, bottom=1001)
MOVE left = 200 Box(left=200, top=600, width=601, height=401) Rect(left=200, top=600, right=801, bottom=1001)
CHANGED!!! (200, 600) Box(left=200, top=600, width=601, height=401) Rect(left=200, top=600, right=801, bottom=1001)
CHANGED!!! (157, 600) Box(left=157, top=600, width=601, height=401) Rect(left=157, top=600, right=758, bottom=1001)
MOVE right = 200 Box(left=-401, top=600, width=601, height=401) Rect(left=-401, top=600, right=200, bottom=1001)
CHANGED!!! (-401, 600) Box(left=-401, top=600, width=601, height=401) Rect(left=-401, top=600, right=200, bottom=1001)
CHANGED!!! (-401, 588) Box(left=-401, top=588, width=601, height=402) Rect(left=-401, top=588, right=200, bottom=990)
CHANGED!!! (-401, 201) Box(left=-401, top=201, width=601, height=402) Rect(left=-401, top=201, right=200, bottom=603)
MOVE top = 200 Box(left=-401, top=200, width=601, height=401) Rect(left=-401, top=200, right=200, bottom=601)
CHANGED!!! (-401, 200) Box(left=-401, top=200, width=601, height=401) Rect(left=-401, top=200, right=200, bottom=601)
MOVE bottom = 800 Box(left=-401, top=399, width=601, height=401) Rect(left=-401, top=399, right=200, bottom=800)
CHANGED!!! (-401, 399) Box(left=-401, top=399, width=601, height=401) Rect(left=-401, top=399, right=200, bottom=800)
CHANGED!!! (269, 400) Box(left=269, top=400, width=602, height=401) Rect(left=269, top=400, right=871, bottom=801)
MOVE topleft = (300, 400) Box(left=300, top=400, width=601, height=401) Rect(left=300, top=400, right=901, bottom=801)
CHANGED!!! (300, 400) Box(left=300, top=400, width=601, height=401) Rect(left=300, top=400, right=901, bottom=801)
CHANGED!!! (-242, 400) Box(left=-242, top=400, width=602, height=401) Rect(left=-242, top=400, right=360, bottom=801)
MOVE topright = (300, 400) Box(left=-301, top=400, width=601, height=401) Rect(left=-301, top=400, right=300, bottom=801)
CHANGED!!! (-301, 400) Box(left=-301, top=400, width=601, height=401) Rect(left=-301, top=400, right=300, bottom=801)
CHANGED!!! (115, 330) Box(left=115, top=330, width=602, height=401) Rect(left=115, top=330, right=717, bottom=731)
MOVE bottomleft = (300, 700) Box(left=300, top=299, width=601, height=401) Rect(left=300, top=299, right=901, bottom=700)
CHANGED!!! (300, 299) Box(left=300, top=299, width=601, height=401) Rect(left=300, top=299, right=901, bottom=700)
CHANGED!!! (37, 386) Box(left=37, top=386, width=601, height=402) Rect(left=37, top=386, right=638, bottom=788)
MOVE bottomright = (300, 900) Box(left=-301, top=499, width=601, height=401) Rect(left=-301, top=499, right=300, bottom=900)
CHANGED!!! (-301, 499) Box(left=-301, top=499, width=601, height=401) Rect(left=-301, top=499, right=300, bottom=900)
CHANGED!!! (-94, 395) Box(left=-94, top=395, width=602, height=402) Rect(left=-94, top=395, right=508, bottom=797)
MOVE midleft = (300, 400) Box(left=300, top=200, width=601, height=401) Rect(left=300, top=200, right=901, bottom=601)
CHANGED!!! (300, 200) Box(left=300, top=200, width=601, height=401) Rect(left=300, top=200, right=901, bottom=601)
CHANGED!!! (236, 200) Box(left=236, top=200, width=602, height=401) Rect(left=236, top=200, right=838, bottom=601)
MOVE midright = (300, 400) Box(left=-301, top=200, width=601, height=401) Rect(left=-301, top=200, right=300, bottom=601)
CHANGED!!! (-301, 200) Box(left=-301, top=200, width=601, height=401) Rect(left=-301, top=200, right=300, bottom=601)
CHANGED!!! (-299, 201) Box(left=-299, top=201, width=602, height=402) Rect(left=-299, top=201, right=303, bottom=603)
MOVE midtop = (300, 400) Box(left=0, top=400, width=601, height=401) Rect(left=0, top=400, right=601, bottom=801)
CHANGED!!! (0, 400) Box(left=0, top=400, width=601, height=401) Rect(left=0, top=400, right=601, bottom=801)
MOVE midbottom = (300, 700) Box(left=0, top=299, width=601, height=401) Rect(left=0, top=299, right=601, bottom=700)
CHANGED!!! (0, 299) Box(left=0, top=299, width=601, height=401) Rect(left=0, top=299, right=601, bottom=700)
CHANGED!!! (0, 207) Box(left=0, top=207, width=601, height=402) Rect(left=0, top=207, right=601, bottom=609)
MOVE center = (300, 400) Box(left=0, top=200, width=601, height=401) Rect(left=0, top=200, right=601, bottom=601)
CHANGED!!! (0, 200) Box(left=0, top=200, width=601, height=401) Rect(left=0, top=200, right=601, bottom=601)
CHANGED!!! (588, 200) Box(left=588, top=200, width=602, height=401) Rect(left=588, top=200, right=1190, bottom=601)
MOVE centerx = 1000 Box(left=700, top=200, width=601, height=401) Rect(left=700, top=200, right=1301, bottom=601)
CHANGED!!! (700, 200) Box(left=700, top=200, width=601, height=401) Rect(left=700, top=200, right=1301, bottom=601)
MOVE centery = 300 Box(left=700, top=100, width=601, height=401) Rect(left=700, top=100, right=1301, bottom=501)
CHANGED!!! (700, 100) Box(left=700, top=100, width=601, height=401) Rect(left=700, top=100, right=1301, bottom=501)
"""