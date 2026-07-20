"""
app/ — application layer.

    chrome.py    AppTitleBar / PageMenuBar / TopNav — the frame around a
                 workspace. Knows nothing about any specific module.
    registry.py  the module table; the single place a module is registered
    shell.py     ShellWindow — hosts one ModuleWorkspace at a time
    main.py      entry point

Imports from modules/ and core/. Nothing imports app/.
"""