# PyWinCtl

[![CI](https://github.com/Kalmat/PyWinCtl/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/Kalmat/PyWinCtl/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/PyWinCtl.svg)](https://badge.fury.io/py/PyWinCtl)
[![Documentation Status](https://readthedocs.org/projects/pywinctl/badge/?version=latest)](https://pywinctl.readthedocs.io/en/latest/?badge=latest)
[![Downloads](https://static.pepy.tech/badge/pywinctl/month)](https://pepy.tech/project/pywinctl)
[![Stars](https://img.shields.io/github/stars/Kalmat/PyWinCtl?style=flat)](https://github.com/Kalmat/PyWinCtl/stargazers)
[![License](https://img.shields.io/badge/license-BSD%203--Clause-blue)](LICENSE.txt)

**Cross-platform window management for Python.** Discover, control, and monitor any open window on your desktop — across Windows, macOS, and Linux — with a single, unified API.

With PyWinCtl you can list open windows, retrieve their properties, move and resize them, minimize, maximize, restore, activate, close, and even track window state changes in real time; making it an ideal solution for desktop automation, screen recording, UI testing, window monitoring or tiling, kiosks, overlays, and multi-monitor workflows.

*Sincere thanks to [MestreLion](https://github.com/MestreLion), [super-ibby](https://github.com/super-ibby), [Avasam](https://github.com/Avasam), [macdeport](https://github.com/macdeport), [holychowders](https://github.com/holychowders), and all other contributors (see [AUTHORS.txt](AUTHORS.txt)) for their help, feedback, and moral support.*

---

## What is this for?

If you've ever needed to do any of the following from a Python script, this library is for you:

- **Find a window** — get the active window or find any other window by its title, getting an object to query or modify its properties
- **Move or resize a window** — position a browser at exactly (0, 0) before taking a screenshot, or snap two windows side-by-side automatically
- **Bring a window to the front** — activate a specific app after launching it via `subprocess`
- **Get notified when a window closes, moves, or changes title** — react in real time from a background thread
- **Automate GUI workflows** — launch an app, wait for its window, interact with its menu, and close it programmatically
- **Manage a multi-window test harness** — enumerate all open windows, find ones by title or PID, check their state
- **Build a screen capture tool** — get the exact position and size of a window to pass to `mss`, `PIL`, or `OpenCV`
- **Control your own app's windows** — manage Tkinter/Qt/wx window geometry or state from outside the main loop

PyWinCtl uses native backends under the hood: Win32 API on Windows, Apple Script on macOS, and [EWMHlib](https://github.com/Kalmat/EWMHlib)/Xlib on Linux; 

```python
import pywinctl as pwc

# Find a window and take full control
win = pwc.getWindowsWithTitle("Notepad")[0]

win.activate()            # bring to front
win.resizeTo(1280, 720)   # set exact size
win.moveTo(0, 0)          # snap to top-left corner
win.alwaysOnTop(True)     # pin it above everything else

# Read live properties
print(win.title, win.size, win.isMaximized, win.isAlive)
```

---

## Real-world use cases

**Screen capture with exact client frame coordinates (skip borders and title bar)**

```python
import pywinctl as pwc
import mss

win = pwc.getWindowsWithTitle("My App")[0]
frame = win.getClientFrame()
box = {"left": frame.left, "top": frame.top, "width": frame.right - frame.left, "height": frame.bottom - frame.top}
with mss.mss() as sct:
    win.activate()
    screenshot = sct.grab(box)
```

**Wait for a launched app to appear**

```python
import subprocess, time, pywinctl as pwc

subprocess.Popen("notepad")
win = None
while not win:
    time.sleep(0.2)
    windows = pwc.getWindowsWithTitle("Notepad")
    if windows:
        win = windows[0]
win.activate()
win.resizeTo(800, 600)
```

**React when a window closes**

```python
import pywinctl as pwc

def on_closed(is_alive):
    print("Window gone!")

win = pwc.getActiveWindow()
win.watchdog.start(isAliveCB=on_closed)
```

**Tile two windows side by side, regardless of which monitor they are on**

```python
import pywinctl as pwc
import pymonctl as pmc

def get_coordinates(win):
   window_monitor = win.getMonitor()[0]
   monitor_info = pmc.getAllMonitorsDict()[window_monitor]
   return monitor_info["position"], monitor_info["size"]
   
wins = pwc.getWindowsWithTitle("brave|notepad", None, pwc.Re.MATCH, pwc.Re.IGNORECASE)
brave, notepad = wins

pos, size = get_coordinates(brave)

brave.moveTo(pos.x, pos.y)
brave.resizeTo(size.width // 2, size.height)
notepad.moveTo(size.width // 2, pos.y)
notepad.resizeTo(size.width // 2, size.height)
```
---

## Ecosystem

PyWinCtl is based on these other libraries, which offer a rich set of additional, useful features:
* [PyMonCtl](https://github.com/Kalmat/PyMonCtl) → monitor management (especially for multi-monitor awareness)
* [PyWinBox](https://github.com/Kalmat/PyWinBox) → geometry utilities (similar to PyGame.Rect object, but enhanced)
* [EWMHlib](https://github.com/Kalmat/EWMHlib) → Extended Window Manager Hints (EWMH) implementation (X11 only)

---

## Table of contents

1. [Window features](#window-features)
   - [Important macOS notice](#important-macos-notice)
   - [Important Linux notice](#important-linux-notice)
2. [Window change notifications (watchdog)](#window-change-notifications)
   - [Important comments](#important-comments)
   - [Important macOS Apple Script notice](#important-macos-apple-script-notice)
3. [Menu features](#menu-features)
4. [Known gotchas](#known-gotchas)
5. [Install](#install)
6. [Support](#support)
7. [Using this code](#using-this-code)
8. [Test](#test)

---

## Window features

PyWinCtl exposes three layers of API:

- **Module-level functions** — call directly without a Window object (e.g. `pwc.getActiveWindow()`, `pwc.getAllTitles()`)
- **Window methods** — actions on a specific window object (e.g. `win.resizeTo(800, 600)`, `win.close()`)
- **Window properties** — readable and writable attributes (e.g. `win.title`, `win.center = (500, 300)`)

All three layers are available on Windows, Linux, and macOS.

| Module-level functions | Window methods                                                                                      | Window properties |
|---|-----------------------------------------------------------------------------------------------------|---|
| [getActiveWindow](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getactivewindow) | [close](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#close)                         | (GET) [title](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#title) |
| [getActiveWindowTitle](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getactivewindowtitle) | [minimize](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#minimize)                   | (GET) [updatedTitle](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#updatedtitle) *(MacOSWindow only)* |
| [getAllWindows](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getallwindows) | [maximize](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#maximize)                   | (GET) [isMaximized](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#ismaximized) |
| [getAllTitles](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getalltitles) | [restore](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#restore)                     | (GET) [isMinimized](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#isminimized) |
| [getWindowsWithTitle](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getwindowswithtitle) | [hide](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#hide)                           | (GET) [isActive](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#isactive) |
| [getAllAppsNames](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getallappsnames) | [show](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#show)                           | (GET) [isVisible](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#isvisible) |
| [getAppsWithName](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getappswithname) | [activate](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#activate)                   | (GET) [isAlive](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#isalive) |
| [getAllAppsWindowsTitles](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getallappswindowstitles) | [resize / resizeRel](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#resize)           | **Position / Size** *(via [PyWinBox](https://github.com/Kalmat/PyWinBox))* |
| [getWindowsAt](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getwindowsat) | [resizeTo](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#resizeto)                   | (GET/SET) position (x, y) |
| [getTopWindowAt](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#gettopwindowat) | [move / moveRel](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#move)                 | (GET/SET) left, top, right, bottom |
| [displayWindowsUnderMouse](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#displaywindowsundermouse) | [moveTo](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#moveto)                       | (GET/SET) topleft, topright, bottomleft, bottomright |
| [version](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#version) | [raiseWindow](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#raisewindow)             | (GET/SET) midtop, midleft, midbottom, midright |
| [checkPermissions](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#checkpermissions) *(macOS only)* | [lowerWindow](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#lowerwindow)             | (GET/SET) center, centerx, centery |
| | [alwaysOnTop](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#alwaysontop)             | (GET/SET) size (width, height) |
| | [alwaysOnBottom](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#alwaysonbottom)       | (GET/SET) width, height |
| | [sendBehind](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#sendbehind)               | (GET/SET) box (x, y, width, height) |
| | [acceptInput](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#acceptinput)             | (GET/SET) rect (x, y, right, bottom) |
| | [getAppName](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getappname)               | |
| | [getHandle](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#gethandle)                 | |
| | [getParent](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getparent)                 | |
| | [setParent](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#setparent)                 | |
| | [getChildren](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getchildren)             | |
| | [isParent](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#isparent)                   | |
| | [isChild](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#ischild)                     | |
| | [getDisplay](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getdisplay)               | |
| | [getExtraFrameSize](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getextraframesize) | |
| | [getClientFrame](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getclientframe)       | |
| | [getPID](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getPID)                       | |

### Important macOS notice

macOS restricts controlling windows belonging to other processes. The `MacOSWindow()` class works via Apple Script, which makes it slower, non-standard, and occasionally tricky (it uses the window name as a reference, which may change or be duplicated). **You will likely need to grant permissions under Settings → Security & Privacy → Accessibility.** Be aware that some applications have limited or no Apple Script support, so some methods may not work. Calls like `getActiveWindowTitle()` have observed latencies of 400–500 ms on Apple Silicon — if your use case is latency-sensitive, account for this.

### Important Linux notice

The wide variety of Linux distributions, desktop environments, and window managers makes it impossible to test every combination.

PyWinCtl has been tested successfully on these X11 setups: Ubuntu/GNOME, Ubuntu/KDE, Ubuntu/Unity, Mint/Cinnamon, and Raspbian/LXDE. The `sendBehind()` method does not work correctly on most setups except Mint/Cinnamon and Ubuntu 22.04+.

On **Wayland** (the default display protocol on Ubuntu 22.04+ and many modern distros), `getActiveWindow()` and `getAllWindows()` are unreliable — built-in and "official" applications do not expose their X Window ID, so these calls may fail even with unsafe mode enabled. They may still work for third-party applications such as Chrome, or for your own application's windows.

**WSL2** is not supported — the X server environment WSL2 provides does not expose the information PyWinCtl requires.

If you encounter problems on a configuration not listed above, please [open an issue](https://github.com/Kalmat/PyWinCtl/issues). Contributions for untested configs are very welcome.

---

## Window change notifications

PyWinCtl includes a **watchdog** — a background thread that monitors a window and fires your callbacks whenever its state changes.

Access it via `window.watchdog`. The watchdog stops automatically when the window is closed or the main program exits.

Available callbacks:

```
isAliveCB:        fires when the window is no longer alive
                  passes: False

isActiveCB:       fires when the window gains or loses focus
                  passes: True / False

isVisibleCB:      fires when the window is shown or hidden
                  passes: True / False

isMinimizedCB:    fires when the window is minimized or restored
                  passes: True / False

isMaximizedCB:    fires when the window is maximized or restored
                  passes: True / False

resizedCB:        fires when the window is resized
                  passes: (width, height)

movedCB:          fires when the window is moved
                  passes: (x, y)

changedTitleCB:   fires when the window title changes
                  passes: new title (str)
                  IMPORTANT: on macOS AppScript, if the title changes the watchdog will stop
                  unless setTryToFind(True) is used

changedDisplayCB: fires when the window moves to a different display
                  passes: new display name (str)
```

| Watchdog methods | |
|---|---|
| [start](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#start) | Start watching with the given callbacks |
| [updateCallbacks](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#updatecallbacks) | Replace active callbacks (pass all desired ones) |
| [updateInterval](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#updateinterval) | Change the polling interval |
| [setTryToFind](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#settrytofind) *(macOS only)* | Try to locate window after title change |
| [isAlive](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#-watchdog-isalive) | Check if the watchdog is still running |
| [stop](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#stop) | Stop the watchdog |

**Example:**

```python
import pywinctl as pwc
import time

def activeCB(active):
    print("NEW ACTIVE STATUS", active)

def movedCB(pos):
    print("NEW POS", pos)

npw = pwc.getActiveWindow()
npw.watchdog.start(isActiveCB=activeCB)
npw.watchdog.setTryToFind(True)
print("Toggle focus and move the active window — press Ctrl-C to quit")
i = 0
while True:
    try:
        if i == 50:
            npw.watchdog.updateCallbacks(isActiveCB=activeCB, movedCB=movedCB)
        if i == 100:
            npw.watchdog.updateInterval(0.1)
            npw.watchdog.setTryToFind(False)
        time.sleep(0.1)
    except KeyboardInterrupt:
        break
    i += 1
npw.watchdog.stop()
```

### Important comments

- Callback signatures **must match** their invocation parameters: `bool`, `str`, or `(int, int)`.
- The watchdog is asynchronous — notifications are not immediate. Adjust the polling interval to suit your needs, or read window properties directly (e.g. `win.isAlive`) for synchronous checks.
- Move and resize callbacks will fire multiple times as the window transitions between positions.
- When calling `updateCallbacks()`, always pass **all** desired callbacks — any omitted callback (passed as `None`) will be deactivated.

### Important macOS Apple Script notice

- The Apple Script backend can be slow and resource-intensive.
- The watchdog identifies the window by its title. If the title changes, the watchdog will consider the window gone and stop — unless `setTryToFind(True)` is used. This uses a similarity check, so the result is not fully guaranteed.

---

## Menu features

> **Available on:** MS-Windows (`Win32Window`) and macOS Apple Script (`MacOSWindow`)

The `menu` sub-module lets you inspect and interact with native application menus programmatically — traverse the full menu tree, read item metadata, and trigger menu actions by path.

| Menu methods | |
|---|---|
| [getMenu](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getmenu) | Returns the full menu structure as a nested dict |
| [getMenuInfo](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getmenuinfo) | Returns info about a specific menu |
| [getMenuItemCount](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getmenuitemcount) | Returns the number of items in a menu |
| [getMenuItemInfo](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getmenuiteminfo) | Returns info about a specific menu item |
| [getMenuItemRect](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#getmenuitemrect) | Returns the bounding rect of a menu item |
| [clickMenuItem](https://github.com/Kalmat/PyWinCtl/blob/master/docs/docstrings.md#clickmenuitem) | Clicks a menu item by path |

**Example (Windows — note: menu labels are language-dependent):**

```python
import pywinctl as pwc
import subprocess
# import json

subprocess.Popen('notepad')
windows = pwc.getWindowsWithTitle('notepad', condition=pwc.Re.CONTAINS, flags=pwc.Re.IGNORECASE)
if windows:
    win = windows[0]
    menu = win.menu.getMenu()
    # print(json.dumps(menu, indent=4, ensure_ascii=False))  # pretty-print the full menu tree
    ret = win.menu.clickMenuItem(["File", "Exit"])
    if not ret:
        print("Option not found. Check the item path and language.")
else:
    print("Window not found. Check the application name and language.")
```

The dict returned by `getMenu()` contains everything you need to navigate the menu tree:

```
Key:           item title
Values:
  "parent":    handle of the parent sub-menu
  "hSubMenu":  handle of this item (non-zero for sub-menus only)
  "wID":       item ID (used by clickMenuItem() and other actions)
  "rect":      bounding rect of the item
               (Windows: relative to window position — unaffected by move/resize)
  "item_info": [optional] Python dict (macOS) / MENUITEMINFO struct (Windows)
  "shortcut":  keyboard shortcut, if any (macOS: only when item_info is included)
  "entries":   nested sub-items, in the same format (only present for sub-menus)
```

> Note: not all windows or applications expose a menu accessible via these methods.

---

## Known gotchas

These are the most common surprises reported by users — knowing them upfront will save you time.

**Minimized windows may not appear in search results**

`getWindowsWithTitle()` and `getAllWindows()` may not return minimized windows on some platforms. If you need to find a window that might be minimized, restore it first or use `getAllWindows()` and filter by title manually.

**`getWindowsWithTitle()` is a substring search by default**

Pass `condition=pwc.Re.EQUALS` for an exact match, or `condition=pwc.Re.CONTAINS` with `flags=pwc.Re.IGNORECASE` for case-insensitive partial matching. Window titles are language-dependent on some platforms (notably menu labels on Windows).

**macOS is slow for Apple Script calls**

Calls like `getActiveWindowTitle()` can take 400–500 ms on Apple Silicon Macs. This is an Apple Script limitation. For high-frequency polling, use the watchdog with a tuned interval rather than calling these methods in a tight loop.

**Wayland support is limited**

On Wayland (Ubuntu 22.04+, Fedora, and others), most window enumeration functions will fail or return empty results for system applications. Use X11/XWayland mode if you need full functionality, or instantiate `Window` directly with a known XID.

**WSL2 is not supported**

PyWinCtl requires a native X server environment. WSL2 does not expose the X Window information the library relies on.

**`sendBehind()` only works reliably on Mint/Cinnamon and Ubuntu 22.04+**

On other Linux setups, this method may silently fail. Check the Linux notice section for the tested configurations.

---

## Install

**Via pip:**

```bash
python -m pip install pywinctl
```

**Via uv:**

```bash
uv add pywinctl
```

**From a wheel file** (replace `x.xx` with the actual version):

```bash
python -m pip install PyWinCtl-x.xx-py3-none-any.whl
```

Add `--force-reinstall` if you need to ensure the correct dependency versions are installed.

Then import it in your project:

```python
import pywinctl as pwc
```

Requirements: Python ≥ 3.9. Platform dependencies are installed automatically: `pywin32` on Windows, `python-xlib` + `ewmhlib` on Linux, `pyobjc` on macOS.

---

## Support

Found a bug? Have a question or a suggestion? [Open an issue](https://github.com/Kalmat/PyWinCtl/issues) on the project page. The maintainer is very responsive and typically replies within days.

You can also browse [existing discussions](https://github.com/Kalmat/PyWinCtl/discussions) — many common questions and platform-specific workarounds are already documented there.

---

## Using this code

To contribute or run the code locally, fork the [repository](https://github.com/Kalmat/PyWinCtl) or [download and unzip it](https://github.com/Kalmat/PyWinCtl/archive/refs/heads/master.zip), then install dev dependencies:

```bash
uv sync
```

or

```bash
python -m venv .venv
python -m pip install -e . --group=dev
```

---

## Test

To run the test suite on your system, navigate to the `tests` folder and run:

```bash
uv run test_pywinctl.py
```
