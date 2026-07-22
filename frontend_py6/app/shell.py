"""
app/shell.py — the application shell
═══════════════════════════════════════════════════════════════════════════
Renders chrome (title bar, menu bar, nav strip) and hosts exactly one
ModuleWorkspace beneath it. It has no column layout, no calculation logic,
and no knowledge of any specific module.

What changed in step 4
──────────────────────
The previous ShellWindow *was* the Screw Conveyor calculator. It owned a
four-column splitter in which col1 (equipment tree), col2 (the CEMA input
sidebar) and col4 (design health) were mounted permanently, and only col3
swapped between modules. Every non-conveyor module therefore rendered
inside the conveyor's frame, showing the conveyor's input sidebar next to
its own — two input rails, one belonging to a different machine.

Those columns now live in modules/conveyor/workspace.py, mounted only
while the conveyor is active. The shell swaps whole workspaces.

Deleted along with the old layout, because each existed only to work
around the conveyor being privileged:

    PROCESS_PAGES           the six-id set used to choose an endpoint —
                            each workspace now routes its own backend call
    CALC_TAB_INDEX/_LABELS   moved into the conveyor workspace
    _show_page()             the calc/not-calc branch
    _update_col3_header()    col3 is conveyor-internal now
    _swap_col3_header()      "
    run_calculation()        conveyor behaviour, not application behaviour
    _maybe_fetch_axial()     "
    _fetch_axial()           "
    _on_axial_refresh()      "
    _on_sidebar_calculate()  "
    _on_optimizer_apply()    "
    _fail_warn()             "

What the shell still owns: window chrome, the workspace stack, backend
health checking, and forwarding nav events to the active workspace.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QStackedWidget,
)
from PySide6.QtCore import QThread, QObject, Signal

from core.theme import BG
from core.api_client import health_check
from modules.base import ModuleWorkspace

from .chrome import AppTitleBar, PageMenuBar, TopNav
from .registry import MODULES, DEFAULT_MODULE, by_id


class _HealthWorker(QObject):
    finished = Signal(bool)

    def run(self) -> None:
        self.finished.emit(health_check())


class ShellWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VECTRIX™ — Design Platform")
        self.resize(1440, 900)
        self.setStyleSheet(f"background-color: {BG};")

        self._active: Optional[ModuleWorkspace] = None
        self._active_id: Optional[str] = None

        self._build_chrome()
        self._build_workspaces()
        self._assemble()
        self._show_module(DEFAULT_MODULE)
        self._check_backend()

    # ── chrome ────────────────────────────────────────────────────────────

    def _build_chrome(self) -> None:
        self.title_bar = AppTitleBar()
        self.menu_bar_w = PageMenuBar(current_page=DEFAULT_MODULE)
        self.top_nav = TopNav()

        self.title_bar.pdf_requested.connect(self._on_pdf_requested)
        self.menu_bar_w.page_changed.connect(self._show_module)
        self.top_nav.tab_changed.connect(self._on_tab_changed)

    # ── workspaces ────────────────────────────────────────────────────────

    def _build_workspaces(self) -> None:
        """
        Instantiate every registered workspace up front and keep them in a
        QStackedWidget, so switching modules preserves each one's state
        (entered values, fetched results) instead of rebuilding it.

        by_id() raises on a duplicate page_id, so a registration mistake
        fails at startup rather than silently dropping a module from the
        menu.
        """
        by_id()          # validate before building
        self._stack = QStackedWidget()
        self._workspaces: dict[str, ModuleWorkspace] = {}

        for cls in MODULES:
            w = cls()
            w.kpis_changed.connect(self.top_nav.update_kpis)
            w.fail_count_changed.connect(self.top_nav.update_fail_badge)
            w.apply_requested.connect(self._on_apply_requested)
            w.set_peer_resolver(self._peer_payload)
            self._stack.addWidget(w)
            self._workspaces[cls.page_id] = w

    def _assemble(self) -> None:
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.title_bar)
        outer.addWidget(self.menu_bar_w)
        outer.addWidget(self.top_nav)
        outer.addWidget(self._stack, 1)
        self.setCentralWidget(container)

    # ── module switching ──────────────────────────────────────────────────

    def _show_module(self, page_id: str) -> None:
        w = self._workspaces.get(page_id)
        if w is None or page_id == self._active_id:
            return

        if self._active is not None:
            self._active.on_deactivate()

        self._active = w
        self._active_id = page_id
        self._stack.setCurrentWidget(w)
        self.menu_bar_w.set_active_page(page_id)

        # Chrome reflects the incoming module, not the outgoing one.
        self.top_nav.clear_kpis()
        self.top_nav.set_tabs(w.tabs())
        self.setWindowTitle(f"VECTRIX™ — {w.meta.label}")

        w.on_activate()

    def _on_tab_changed(self, tab_id: str) -> None:
        if self._active is not None:
            self._active.on_tab_changed(tab_id)

    # ── cross-module exchange ─────────────────────────────────────────────

    def _peer_payload(self, page_id: str) -> dict:
        """Resolver handed to every workspace. Returns a peer's current
        inputs as plain data — never the widget — so modules stay decoupled."""
        w = self._workspaces.get(page_id)
        return w.export_payload() if w is not None else {}

    def _on_apply_requested(self, target_id: str, payload: dict) -> None:
        """Hand a design from one module to another and switch to it.

        The switch is deliberate: applying a design the user cannot see the
        effect of is a silent state change. FamilyPage.tsx gets this free
        because both pages read one store; here the move has to be explicit.
        """
        target = self._workspaces.get(target_id)
        if target is None:
            return
        target.receive_payload(payload)
        self._show_module(target_id)

    # ── backend health ────────────────────────────────────────────────────

    def _check_backend(self) -> None:
        self._health_thread = QThread()
        self._health_worker = _HealthWorker()
        self._health_worker.moveToThread(self._health_thread)
        self._health_thread.started.connect(self._health_worker.run)
        self._health_worker.finished.connect(self._on_health_result)
        self._health_worker.finished.connect(self._health_thread.quit)
        self._health_thread.start()

    def _on_health_result(self, online: bool) -> None:
        self.title_bar.set_backend_status(online)
        if online and self._active is not None:
            # Re-run activation now that the backend is known reachable.
            # on_activate() is idempotent by contract — the conveyor guards
            # on a _combos_loaded flag — so calling it twice is safe and
            # avoids a module doing network work before there is a backend.
            self._active.on_activate()

    # ── misc ──────────────────────────────────────────────────────────────

    def _on_pdf_requested(self) -> None:
        print("[PDF Report] matplotlib report generator — to be wired.")