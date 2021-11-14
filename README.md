First off, my most sincere thanks and acknowledgement to macdeport (https://github.com/macdeport) and holychowders (https://github.com/holychowders) for their help and moral boost.

PyGetWindow-MP (Multi-Platform)
==============================

This is a fork from asweigart's PyGetWindow module (https://github.com/asweigart/PyGetWindow)

It adds Linux and macOS experimental support, in the hope others can use it, test it or contribute.

You can test it on your system by adding pygetwindow folder to your PYTHONPATH, and then executing: "pytest -vv test_pygetwindow.py" (script located within "tests" folder)

### IMPORTANT NOTICE:

macOS doesn't "like" controlling windows from other apps, so there are two separate classes you can use.

One is based on NSWindow Objects (you have to pass the NSApp() Object. It means you have to be the "owner" of the app).
To test macOS NSWindow class, you can execute "python3 test_MacNSWindow.py" (also located within "test" folder)

The other one is based on Apple Script, so it is not fully trustable, but it's working fine in most cases.
This other class can be tested together with the others modules, as described above.

