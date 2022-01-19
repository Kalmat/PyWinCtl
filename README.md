First off, my most sincere thanks and acknowledgement to macdeport (https://github.com/macdeport) and holychowders (https://github.com/holychowders) for their help and moral boost.

PyGetWindow-MP (Multi-Platform)
==============================

This is a fork from asweigart's PyGetWindow module (https://github.com/asweigart/PyGetWindow), intended to obtain GUI information on and control application's windows.

This fork adds Linux and macOS experimental support to the MS Windows™-only original module, in the hope others can use it, test it or contribute

#### IMPORTANT MacOS NOTICE:

macOS doesn't "like" controlling windows from other apps, so there are two separate classes you can use:

- To Control your own application's windows: MacOSNSWindow() is based on NSWindow Objects (you have to pass the NSApp() Object reference. It means you have to be the "owner" of the application you want to control). To test macOS NSWindow class, you can run "python3 test_MacNSWindow.py" (also located in "tests" folder)
- To control other applications' windows: MacOSWindow() is based on Apple Script, so it is not fully trustable, but it's working fine in most cases. This other class can be tested together with the other modules, as described above, using "test_pygetwindow.py" script.
