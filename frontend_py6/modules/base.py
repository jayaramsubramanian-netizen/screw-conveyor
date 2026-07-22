"""
modules/base.py — the module contract
═══════════════════════════════════════════════════════════════════════════
Every main-menu application in VECTRIX™ implements ModuleWorkspace. The
shell renders chrome (title bar, menu bar, nav strip) and nothing else; it
asks the active workspace for the entire body beneath that chrome.

Why this exists
───────────────
The shell was previously built to the Screw Conveyor's shape: a fixed
four-column splitter whose col1/col2/col4 were hardcoded conveyor panels
(equipment tree, InputSidebarPanel, StatusPanel) with only col3 swapping
between modules. Any module that was not the conveyor therefore rendered
*inside* the conveyor's frame — a mixer showed the conveyor's CEMA input
sidebar and design-health column alongside its own, two input rails at
once, one of them wrong.

ModuleWorkspace inverts that. A workspace IS the body. It decides its own
column count, its own inputs, its own status area. The conveyor builds
four columns because it wants four; the mixer builds two; the manual
viewer builds one. The shell imposes nothing.

Import rule
───────────
Implementations import from core/ and from their own package. A module
never imports another module's internals. Shared behaviour is promoted
into core/, or into a family package such as modules/process/common.py
when it is shared by a family rather than by everything.

Lifecycle
─────────
    on_activate()    workspace became visible — cheap place to lazily fire
                     a first calculation or populate combos, so app start
                     is not blocked by every module doing that work up front
    on_deactivate()  workspace hidden — cancel in-flight requests, stop timers

Both default to no-ops. A module that needs neither implements neither.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class ModuleMeta:
    """
    Presentation identity, read by the shell for nav entries, menu items,
    and the body header. Kept as data rather than methods so the registry
    can build the menus without instantiating every workspace at startup.
    """
    label: str                  # "Screw Mixer"
    icon: str = ""              # "🌀"
    subtitle: str = ""          # one-line description under the title
    group: str = "process"      # menu grouping: conveyor | process | reference
    accent: str | None = None   # override the group's accent colour


@dataclass(frozen=True)
class TabSpec:
    """One entry in the nav tab strip. `tab_id` is what on_tab_changed receives."""
    tab_id: str
    label: str


class ModuleWorkspace(QWidget):
    """
    Base class for a main-menu application.

    Subclasses set `page_id` and `meta` as class attributes — the registry
    reads them off the class, without constructing the widget — and build
    their body in __init__ like any QWidget.

    Minimum viable module:

        class ManualWorkspace(ModuleWorkspace):
            page_id = "help"
            meta = ModuleMeta(label="Manual", icon="📖", group="reference")

            def __init__(self, parent=None):
                super().__init__(parent)
                # ... build body ...
    """

    page_id: str = ""
    meta: ModuleMeta = ModuleMeta(label="Untitled")

    #: Emitted with a flat dict when the module has fresh headline numbers
    #: for the nav KPI chips. The shell forwards these to the chrome without
    #: inspecting them — it does not know or care which module is active.
    #: A module with no headline numbers simply never emits, and the shell
    #: blanks the chips on every page change.
    kpis_changed = Signal(dict)

    #: Emitted with the count of critical failures, for the nav fail badge.
    fail_count_changed = Signal(int)

    #: Emitted as (target_page_id, payload) when this module wants to hand a
    #: design to another module — e.g. the Family Designer's "Apply to
    #: Designer", which loads a swept candidate into the Screw Conveyor.
    #:
    #: The shell routes this: it calls the target's receive_payload() and
    #: switches to it. Deliberately indirect. FamilyPage.tsx and CalcPage.tsx
    #: share a global useCalcStore(), but a direct equivalent here would mean
    #: modules/family importing modules/conveyor, which modules/__init__.py
    #: forbids — and would make the two impossible to port, test, or delete
    #: independently.
    apply_requested = Signal(str, dict)

    #: Set True in the class body of an intermediate base that is not itself
    #: a registrable module (e.g. ModuleShell). Deliberately NOT a PEP 487
    #: class keyword argument — PySide6's Shiboken metaclass raises
    #: "sbktype() takes at most 3 arguments" on any QWidget subclass declared
    #: with class kwargs, so `class Foo(ModuleWorkspace, abstract=True)` is
    #: not available to us. Checked via cls.__dict__ below so the flag does
    #: not inherit: a concrete subclass of an abstract base is still required
    #: to declare its own page_id.
    abstract: bool = False

    def __init_subclass__(cls, **kwargs):
        """
        Fail loudly at import time on an incomplete module.

        A workspace missing page_id would otherwise register fine and only
        misbehave later — silently colliding with another module's empty
        key in the registry dict, so one module overwrites the other and
        simply never appears in the menu. Better to never start.
        """
        super().__init_subclass__(**kwargs)
        if cls.__dict__.get("abstract", False):
            return
        if not cls.page_id:
            raise TypeError(
                f"{cls.__name__} must define a non-empty page_id — the "
                f"registry keys on it."
            )

    # ── cross-module exchange (shell-mediated) ────────────────────────────

    def set_peer_resolver(self, resolver) -> None:
        """
        Injected by the shell at construction. `resolver(page_id) -> dict`
        returns another module's current inputs via its export_payload().

        A module asks for a peer by id and gets plain data back — never a
        widget reference — so no module holds a handle on another.
        """
        self._peer_resolver = resolver

    def peer_payload(self, page_id: str) -> dict:
        """Current inputs of another module, or {} if unavailable."""
        resolver = getattr(self, "_peer_resolver", None)
        if resolver is None:
            return {}
        try:
            return resolver(page_id) or {}
        except Exception:
            # A peer failing to export must never break the caller's render.
            return {}

    def export_payload(self) -> dict:
        """This module's current inputs, for a peer to read. {} by default."""
        return {}

    def receive_payload(self, payload: dict) -> None:
        """Accept inputs handed over by another module. No-op by default."""

    # ── optional tab strip ────────────────────────────────────────────────

    def tabs(self) -> Sequence[TabSpec]:
        """Tabs for this module. Empty (the default) hides the strip."""
        return ()

    def on_tab_changed(self, tab_id: str) -> None:
        """Called when the user picks a tab. No-op unless tabs() is non-empty."""

    # ── lifecycle ─────────────────────────────────────────────────────────

    def on_activate(self) -> None:
        """Workspace became the visible one."""

    def on_deactivate(self) -> None:
        """Workspace was hidden."""