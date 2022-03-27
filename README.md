# PyWinCtl

Cross-Platform module to get info on and control windows on screen.

This module is a Python 3 fork from [asweigart's PyGetWindow module](https://github.com/asweigart/PyGetWindow), which adds Linux and macOS experimental support to the MS Windows-only original module, in the hope others can use it, test it or contribute.

With PyWinCtl you can retrieve info or control windows from other open applications, as well as use it as a cross-platform toolkit to manipulate your own application windows.

My most sincere thanks and acknowledgement to [macdeport](https://github.com/macdeport) and [holychowders](https://github.com/holychowders) for their help and moral boost.

## Window Features

All these functions are available at the moment, in all three platforms (Windows, Linux and macOS):

|  General, independent functions:  |  Window class methods:  |  Window class properties:  |
|  :---:  |  :---:  |  :---:  |
|  getActiveWindow  |  close  |  title  |
|  getActiveWindowTitle  |  minimize  |  isMinimized  |
|  getAllWindows  |  maximize  |  isMaximized  |
|  getAllTitles  |  restore  |  isActive  |
|  getWindowsWithTitle  |  hide  |  isVisible  |
|  getWindowsAt  |  show  |  | 
|  getAllAppsTitles  |  activate  |    |  
|  getAllAppsWindowsTitles  |  resize / resizeRel  |  |   
|  getAllScreens  |  resizeTo  |  |
|  getMousePos  |  move / moveRel  |  |  
|  getScreenSize |  moveTo  |  |  
|  getWorkArea  |  raiseWindow  |    |
|  version  |  lowerWindow  |    |  
|  |  alwaysOnTop  |    |  
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

#### Important macOS notice:

macOS doesn't "like" controlling windows from other apps, so there are two separate classes you can use:

- To control your own application's windows: MacOSNSWindow() is based on NSWindow Objects (you have to pass the NSApp() Object reference).
- To control other applications' windows: MacOSWindow() is based on Apple Script, so it is not standard, slower and, in some cases, tricky (uses window name as reference, which may change or be duplicate), but it's working fine in most cases. You will likely need to grant permissions on Settings -> Security&Privacy -> Accessibility. ***Notice some applications will have limited Apple Script support or no support at all, so some or even all methods may fail!***

## Menu Features

#### Available in: MS-Windows and macOS Apple Script version (MacOSWindow() class)

Menu info and control methods (from asweigart's original ideas), accessible through 'menu' submodule. E.g.:

    subprocess.Popen('notepad')
    windows = pywinctl.getWindowsWithTitle('Untitled - Notepad')
    if windows:
        win = windows[0]
        menu = win.menu.getMenu()
        ret = win.menu.clickMenuItem(["File", "Exit"])   # Exit program
        if not ret:
            print("Option not found")
    else:
        print("Window not found")

Menu dictionary (returned by getMenu() method) will likely contain all you may need to handle application menu:

    Key:            item title
    Values:
      "parent":     parent sub-menu handle
      "hSubMenu":   item handle (!= 0 for sub-menu items only)
      "wID":        item ID (required for other actions, e.g. clickMenuItem())
      "rect":       Rect struct of the menu item. (Windows: It is relative to window position, so it won't likely change if window is moved or resized)
      "item_info":  [Optional] Python dictionary (macOS) / MENUITEMINFO struct (Windows)
      "shortcut":   shortcut to menu item, if any (macOS: only if item_info is included)
      "entries":    sub-items within the sub-menu (if any)

Functions included in this subclass:

|  Menu sub-module functions:  |
|  :---:  |
|  getMenu  |
|  getMenuInfo  |
|  getMenuItemCount  |
|  getMenuItemInfo  |
|  getMenuItemRect  |
|  clickMenuItem  |

Note not all windows/applications will have a menu accessible by these methods.

## INSTALL

To install this module on your system, you can use pip: 

    pip install pywinctl

Alternatively, you can download the wheel file (.whl) available in the [Donwnload page](https://pypi.org/project/pywin32/#files) and the [dist folder](https://github.com/Kalmat/PyWinCtl/tree/master/dist), and run this (don't forget to replace 'x.x.xx' with proper version number):

    pip install PyWinCtl-x.x.xx-py3-none-any.whl

You may want to add `--force-reinstall` option to be sure you are installing the right dependencies version.

Then, you can use it on your own projects just importing it:

    import pywinctl

## SUPPORT

In case you have a problem, comments or suggestions, do not hesitate to [open issues](https://github.com/Kalmat/PyWinCtl/issues) on the [project homepage](https://github.com/Kalmat/PyWinCtl)

## USING THIS CODE

If you want to use this code or contribute, you can either:

* Create a fork of the [repository](https://github.com/Kalmat/PyWinCtl), or 
* [Download the repository](https://github.com/Kalmat/PyWinCtl/archive/refs/heads/master.zip), uncompress, and open it on your IDE of choice (e.g. PyCharm)

Be sure you install all dependencies described on "docs/requirements.txt" by using pip

## TEST

To test this module on your own system, cd to "tests" folder and run:

    pytest -vv test_pywinctl.py

or, in case you get an import error, try this:

    python3 -m pytest -vv test_pywinctl.py

MacOSNSWindow class and methods can be tested by running this, also on "tests" folder:

    python3 test_MacNSWindow.py
