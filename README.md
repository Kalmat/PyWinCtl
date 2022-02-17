First off, my most sincere thanks and acknowledgement to macdeport (https://github.com/macdeport) and holychowders (https://github.com/holychowders) for their help and moral boost.

PyGetWindow-MP (Multi-Platform)
==============================

This is a fork from asweigart's PyGetWindow module (https://github.com/asweigart/PyGetWindow), intended to obtain GUI information on and control application's windows.

This fork adds Linux and macOS experimental support to the original MS Windows-only original module, in the hope others can use it, test it or contribute

### Features

All these functions are available at the moment, in all three platforms (Windows, Linux and macOS):

|  General, independent functions:  |  Window class methods:  |  Window class properties:  |
|  :---:  |  :---:  |  :---:  |
|  getActiveWindow  |  close  |  title  |
|  getActiveWindowTitle  |  minimize  |  isMinimized  |
|  getAllWindows  |  maximize  |  isMaximized  |
|  getAllTitles  |  restore  |  isActive  |
|  getWindowsWithTitle  |  hide  |  isVisible  |
|  getWindowsAt  |  show  |  | 
|  cursor (mouse position)  |  activate  |    |  
|  resolution (screen size)  |  resize / resizeRel  |  |    
|  |  resizeTo  |  |  
|  |  move / moveRel  |  |    
|  |  moveTo  |  |  
|  |  alwaysOnTop  |    |
|  |  alwaysOnBottom  |    |  
|  |  lowerWindow  |    |  
|  |  raiseWindow  |    |  
|  |  sendBehind  |    |  

##### Only in MS-Windows (by now)

New menu control functions (pending work from asweigart's original ideas), accessible through 'menu' submodule. E.g.:

    subprocess.Popen('notepad')
    windows = pygetwindowmp.getWindowsWithTitle('Untitled - Notepad')
    if windows:
        win = windows[0]
        menu = win.menu.getMenu()
        ret = win.menu.clickMenuItem(["File"]["Exit"])   # Exit program
        if not ret:
            print("Option not found")
    else:
        print("Window not found")

Windows: Menu dictionary (returned by getMenu() method) will likely contain all you may need to handle application menu:

    Key:            item title (text property)
    Values:
      "parent":     parent sub-menu handle
      "hSubMenu":   item handle (!= 0 for sub-menu items only)
      "wID":        item ID (required for other actions, e.g. clickMenuItem())
      "item_info":  MENUITEMINFO structure (use item_info.xxx to access individual fields)
      "shortcut":   shortcut to menu item (if any)
      "rect":       Rect structure of the menu item. It is relative to window position, so it won't likely change if window is moved or resized
      "entries":    sub-items within the sub-menu (if any)

MacOS: Menu dictionary (returned by getMenu() method) will likely contain all you may need to handle application menu:

    Key:            item title (text property)
    Values:
        "wID":      Value required to simulate a click on the menu item
        "items":    sub-items within the sub-menu (if any)

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

### USING THIS CODE

If you want to use this code or contribute, you can either:

* Create a fork of this repository, or 
* Download the repository, uncompress, and open it on your IDE of choice (e.g. PyCharm)

Be sure you install all dependencies described on "docs/requirements.txt" by using pip

In case you have any issues, comments or suggestions, do not hesitate to open an issue, or contact me (palookjones@gmail.com)

### TEST

To test this module on your own system, cd to "tests" folder and run:

    pytest -vv test_pygetwindow.py

### INSTALL

To install this module on your system, download the wheel file (.whl) located in "dist" folder, and run this (don't forget to replace 'x.x.xx' with proper version number):

    python3 -m pip install PyGetWindowMP-x.x.xx-py3-none-any.whl

You may want to add '--force-reinstall' option to be sure you are installing the right dependencies version.

Then, you can use it on your own projects just importing it:

    import pygetwindowmp

The module has a different name, so you don't need to uninstall previous PyGetWindow versions. Besides, the Windows-part of PyGetWindowMP module is exactly the same as in the original module.

### IMPORTANT MacOS NOTICE:

macOS doesn't "like" controlling windows from other apps, so there are two separate classes you can use:

- To control your own application's windows: MacOSNSWindow() is based on NSWindow Objects (you have to pass the NSApp() Object reference. It means you have to be the "owner" of the application you want to control). To test macOS NSWindow class, you can run "python3 test_MacNSWindow.py" (also located in "tests" folder)
- To control other applications' windows: MacOSWindow() is based on Apple Script, so it is not fully trustable, but it's working fine in most cases. This other class can be tested together with the other modules, as described above, using "test_pygetwindow.py" script.
