# PyWinCtl

Cross-Platform module to get info on and control windows on screen.

This module is a Python 3 fork from [asweigart's PyGetWindow module](https://github.com/asweigart/PyGetWindow), which adds Linux and macOS support to the MS Windows-only original module, in the hope others can use it, test it or contribute.

With PyWinCtl you can retrieve info or control windows from other open applications, as well as use it as a cross-platform toolkit to manipulate your own application windows.

My most sincere thanks and acknowledgement to [macdeport](https://github.com/macdeport) and [holychowders](https://github.com/holychowders) for their help and moral boost.

1. [Window Features](#window-features)
   1. [Important macOS notice](#macos-notice)
   2. [Important Linux notice](#linux-notice)
2. [Window Change Notifications](#watchdog])
   1. [Important comments](#watchdog-comments)
   2. [Important macOS Apple Script version notice](#watchdog-macos-comments)
3. [Menu Features](#menu-features)
4. [Install](#install)
5. [Support](#support)
6. [Using this code](#using)
7. [Test](#test)

## Window Features <a name="window-features"></a>

All these functions are available at the moment, in all three platforms (Windows, Linux and macOS):

|  General, independent functions:  |  Window class methods:  |  Window class properties:  |
|  :---:  |  :---:  |  :---:  |  
|  getActiveWindow  |  close  |  title  |  
|  getActiveWindowTitle  |  minimize  |  updatedTitle (MacOSWindow only)  |  
|  getAllWindows  |  maximize  |  isMaximized  |  
|  getAllTitles  |  restore  |  isMinimized  |  
|  getWindowsWithTitle  |  hide  |  isActive  |  
|  getAllAppsNames  |  show  |  isVisible  |  
|  getAppsWithName  |  activate  |  isAlive  |  
|  getAllAppsWindowsTitles  |  resize / resizeRel  |  |  
|  getWindowsAt  |  resizeTo  |  |  
|  getAllScreens  |  move / moveRel  |  |  
|  getMousePos |  moveTo  |  |  
|  getScreenSize  |  raiseWindow  |    |  
|  getWorkArea  |  lowerWindow  |    |  
|  version  |  alwaysOnTop  |    |  
|  |  alwaysOnBottom  |    |  
|  |  getAppName  |    |  
|  |  getHandle  |    |  
|  |  getParent  |    |  
|  |  getChildren  |    |  
|  |  isParent  |    |  
|  |  isChild  |    |  
|  |  getDisplay  |    |  
|  |  getExtraFrame  |    |  
|  |  getClientFrame  |    |  

***Important macOS notice <a name="macos-notice"></a>***

macOS doesn't "like" controlling windows from other apps, so there are two separate classes you can use:
- To control your own application's windows: MacOSNSWindow() is based on NSWindow Objects (you have to pass the NSApp() Object reference).
- To control other applications' windows: MacOSWindow() is based on Apple Script, so it is non-standard, slower and, in some cases, tricky (uses window name as reference, which may change or be duplicate), but it's working fine in most cases. You will likely need to grant permissions on Settings -> Security&Privacy -> Accessibility. ***Notice some applications will have limited Apple Script support or no support at all, so some or even all methods may fail!***

***Important Linux notice <a name="linux-notice"></a>***

The enormous variety of Linux distributions, Desktop Environments, Window Managers, and their combinations, make it impossible to test in all scenarios.

This module has been tested OK in Ubuntu/Gnome, Ubuntu/Unity, Mint/Cinnamon and Raspbian/LXDE.

In case you find problems in other configs, please [open an issue](https://github.com/Kalmat/PyWinCtl/issues). Furthermore, if you have knowledge in these other configs, do not hesitate to contribute!

## Window Change Notifications <a name="watchdog"></a>

watchdog sub-class, running in a separate Thread, will allow you to define hooks and its callbacks to be notified when some window states change.

The watchdog will automatically stop when window doesn't exist anymore or program exits.

    isAliveCB:      callback to invoke when window is not alive anymore. Set to None to not to watch this
                    Passes the new alive status value (False)
    
    isActiveCB:     callback to invoke if window changes its active status. Set to None to not to watch this
                    Passes the new active status value (True/False)
    
    isVisibleCB:    callback to invoke if window changes its visible status. Set to None to not to watch this
                    Passes the new visible status value (True/False)

    isMinimizedCB:  callback to invoke if window changes its minimized status. Set to None to not to watch this
                    Passes the new minimized status value (True/False)

    isMaximizedCB:  callback to invoke if window changes its maximized status. Set to None to not to watch this
                    Passes the new maximized status value (True/False)
    
    resizedCB:      callback to invoke if window changes its size. Set to None to not to watch this
                    Passes the new size (width, height)
    
    movedCB:        callback to invoke if window changes its position. Set to None to not to watch this
                    Passes the new position (x, y)
    
    changedTitleCB: callback to invoke if window changes its title. Set to None to not to watch this
                    Passes the new title (as string)
                    IMPORTANT: In MacOS AppScript version, if title changes, it will try to find a similar title and will stop

    changedDisplayCB: callback to invoke if window changes display. Set to None to not to watch this
                      Passes the new display name (as string)

|  watchdog sub-module methods:  |
|  :---:  |
|  start  |
|  updateCallbacks  |
|  updateInterval  |
|  setTryToFind  |
|  isAlive  |
|  stop  |

Example:

    import pywinctl as pwc
    import time

    def activeCB(active):
        print("NEW ACTIVE STATUS", active)

    def movedCB(pos):
        print("NEW POS", pos)

    npw = pwc.getActiveWindow()
    npw.watchdog.start(isActiveCB=activeCB)
    npw.watchdog.setTryToFind(True)
    print("toggle focus and move active window")
    print("Press Ctl-C to Quit")
    i = 0
    while True:
        try:
            if i == 50:
                npw.watchdog.updateCallbacks(isActiveCB=activeCB, movedCB=movedCB)
            if i == 100:
                npw.watchdog.updateInterval(0.1)
                npw.setTryToFind(False)
            time.sleep(0.1)
        except KeyboardInterrupt:
            break
        i += 1
    npw.watchdog.stop()


***Important comments <a name="watchdog-comments"></a>***

- The callbacks definition MUST MATCH their invocation params (boolean, string or (int, int))
- The watchdog is asynchronous, so notifications won't be immediate (adjust interval value to your needs). Use window object properties instead (e.g. isAlive)
- Position and size notifications will trigger several times between initial and final values
- When updating callbacks, remember to set ALL desired callbacks. Non-present (None) callbacks will be deactivated

***Important macOS Apple Script version notice <a name="watchdog-macos-comments"></a>***
- Might be very slow and resource-consuming
- It uses the title to identify the window, so if it changes, the watchdog will consider it is not available anymore and will stop
- Use ''updatedTitle()'' to try to get the new title (not fully guaranteed since it uses a similarity check)


## Menu Features <a name="menu-features"></a>

#### Available in: MS-Windows and macOS Apple Script version (Win32Window() and MacOSWindow() classes)

menu sub-class for Menu info and control methods (from asweigart's original ideas), accessible through 'menu' submodule.

|  menu sub-module methods:  |
|  :---:  |
|  getMenu  |
|  getMenuInfo  |
|  getMenuItemCount  |
|  getMenuItemInfo  |
|  getMenuItemRect  |
|  clickMenuItem  |

Example:

    import pywinctl as pwc
    import subprocess
    # import json

    subprocess.Popen('notepad')
    windows = pwc.getWindowsWithTitle('notepad', condition=pwc.Re.CONTAINS, flags=Re.IGNORECASE)
    if windows:
        win = windows[0]
        menu = win.menu.getMenu()
        # print(json.dumps(menu, indent=4, ensure_ascii=False))  # Prints menu dict in legible format
        ret = win.menu.clickMenuItem(["File", "Exit"])           # Exit program
        if not ret:
            print("Option not found")
    else:
        print("Window not found")

Menu dictionary (returned by getMenu() method) will likely contain all you may need to handle application menu:

    Key:            item title
    Values:
      "parent":     parent sub-menu handle
      "hSubMenu":   item handle (!= 0 for sub-menus only)
      "wID":        item ID (required for other actions, e.g. clickMenuItem())
      "rect":       Rect struct of the menu item. (Windows: It is relative to window position, so it won't likely change if window is moved or resized)
      "item_info":  [Optional] Python dictionary (macOS) / MENUITEMINFO struct (Windows)
      "shortcut":   shortcut to menu item, if any (macOS: only if item_info is included)
      "entries":    sub-items within the sub-menu (or not present otherwise)
                    these sub-items will have this very same format, in a nested struct.

Note not all windows/applications will have a menu accessible by these methods.

## INSTALL <a name="install"></a>

To install this module on your system, you can use pip: 

    pip install pywinctl

Alternatively, you can download the wheel file (.whl) available in the [Donwnload page](https://pypi.org/project/pywin32/#files) and the [dist folder](https://github.com/Kalmat/PyWinCtl/tree/master/dist), and run this (don't forget to replace 'x.x.xx' with proper version number):

    pip install PyWinCtl-x.x.xx-py3-none-any.whl

You may want to add `--force-reinstall` option to be sure you are installing the right dependencies version.

Then, you can use it on your own projects just importing it:

    import pywinctl

## SUPPORT <a name="support"></a>

In case you have a problem, comments or suggestions, do not hesitate to [open issues](https://github.com/Kalmat/PyWinCtl/issues) on the [project homepage](https://github.com/Kalmat/PyWinCtl)

## USING THIS CODE <a name="using"></a>

If you want to use this code or contribute, you can either:

* Create a fork of the [repository](https://github.com/Kalmat/PyWinCtl), or 
* [Download the repository](https://github.com/Kalmat/PyWinCtl/archive/refs/heads/master.zip), uncompress, and open it on your IDE of choice (e.g. PyCharm)

Be sure you install all dependencies described on "docs/requirements.txt" by using pip

## TEST <a name="test"></a>

To test this module on your own system, cd to "tests" folder and run:

    pytest -vv test_pywinctl.py

or, in case you get an import error, try this:

    python3 -m pytest -vv test_pywinctl.py

MacOSNSWindow class and methods can be tested by running this, also on "tests" folder:

    python3 test_MacNSWindow.py
