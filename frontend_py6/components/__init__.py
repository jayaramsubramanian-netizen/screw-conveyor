"""
components/ — transitional package.

Holds only the app chrome (shell.py) and the not-yet-migrated page
placeholders. Its previous role as a re-export barrel for core.widgets has
been removed: forwarding core primitives through here let callers reach
core sideways via `components`, which undercuts the one-way import rule
documented in modules/__init__.py. Import from core.widgets directly.

Dissolves in step 4 — shell.py moves to app/, pages/ moves to modules/.
"""
from components.shell import AppTitleBar, TopNav, PageMenuBar
from components.pages import (
    FamilyPage, FeederPage,
    DryerPage, CoolerPage,
    SeparatorPage, ReactorPage, CompactorPage,
    DatabasePage, ManualPage,
)