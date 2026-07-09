"""
main.py — VECTRIX™ Screw Conveyor Designer entry point
═══════════════════════════════════════════════════════════════════════════
Architecture mirrors the bucket-elevator main.py exactly:

  AppTitleBar  (48 px)  — brand + module switcher + backend status + PDF
  PageMenuBar  (28 px)  — Conveyor / Process / Reference pull-down menus
  TopNav       (76 px)  — app dropdown + tab pills + KPI chips
  QSplitter             — col1 Equipment | col2 Parameters
                          | col3 Results (tab-aware) | col4 Status

Backend connection:
  All calculation calls go through api_client.py → FastAPI backend.
  Endpoint map:
    POST /api/calculate         → main conveyor calc (backend/core/engine.py)
    POST /api/calculate/process → process modules   (backend/core/process_engine.py)
    GET  /api/materials         → material list     (backend/db/database.py)
    POST /api/projects          → save project meta (backend/api/project_meta.py)

Run backend first:
    uvicorn backend.main:app --reload

Then run this app:
    python main.py
"""

from __future__ import annotations

from typing import Optional
import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QSplitter, QStackedWidget, QLabel,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont

from theme import (
    BG, PANEL, BORDER, TEXT3, PRIMARY,
    CALC_TABS, DEFAULT_PAYLOAD,
)
from api_client import fetch_design, fetch_process, health_check
from components import (
    AppTitleBar, TopNav, PageMenuBar,
    ColHeader, Placeholder, fail_warn_badges,
    CalcPage, FamilyPage, FeederPage,
    MixerPage, DryerPage, CoolerPage,
    SeparatorPage, ReactorPage, CompactorPage,
    DatabasePage, ManualPage,
)

# ── Page registry — order must match theme.PAGE_META ─────────────────────
PAGE_REGISTRY = [
    ("calc",      CalcPage),
    ("family",    FamilyPage),
    ("feeder",    FeederPage),
    ("mixer",     MixerPage),
    ("dryer",     DryerPage),
    ("cooler",    CoolerPage),
    ("separator", SeparatorPage),
    ("reactor",   ReactorPage),
    ("compactor", CompactorPage),
    ("db",        DatabasePage),
    ("help",      ManualPage),
]

# Process pages that call /api/calculate/process instead of /api/calculate
PROCESS_PAGES = {"mixer", "dryer", "cooler", "separator", "reactor", "compactor"}

# Calc-tab index map
CALC_TAB_INDEX  = {t["id"]: i for i, t in enumerate(CALC_TABS)}
CALC_TAB_LABELS = {t["id"]: t["label"] for t in CALC_TABS}


# ── Background health check ───────────────────────────────────────────────
class _HealthWorker(QObject):
    """Runs health_check() off the main thread so the window opens immediately."""
    finished = Signal(bool)

    def run(self):
        self.finished.emit(health_check())


# ── ShellWindow ───────────────────────────────────────────────────────────
class ShellWindow(QMainWindow):
    """
    Full application shell — identical four-column layout to bucket elevator.

    col1  200 px  Equipment / project tree
    col2  280 px  Parameters / input sidebar
    col3  flex    Results (tab-aware QStackedWidget)
    col4  260 px  Status / KPI panel
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VECTRIX™ — Screw Conveyor Designer")
        self.resize(1440, 900)
        self.setStyleSheet(f"background-color: {BG};")

        self._current_page    = "calc"
        self._current_tab     = "design"
        self._last_results: dict = {}
        self._last_payload    = dict(DEFAULT_PAYLOAD)

        self._build_chrome()
        self._build_body()
        self._assemble()
        self._check_backend()

    # ── Chrome ────────────────────────────────────────────────────────────
    def _build_chrome(self):
        self.title_bar   = AppTitleBar()
        self.menu_bar_w  = PageMenuBar(current_page="calc")
        self.top_nav     = TopNav()

        self.title_bar.pdf_requested.connect(self._on_pdf_requested)
        self.menu_bar_w.page_changed.connect(self._on_page_changed)
        self.top_nav.tab_changed.connect(self._on_tab_changed)

    # ── Body ──────────────────────────────────────────────────────────────
    def _build_body(self):
        # col1 — Equipment / project tree
        self._col1 = QWidget()
        c1l = QVBoxLayout(self._col1)
        c1l.setContentsMargins(0, 0, 0, 0)
        c1l.setSpacing(0)
        c1l.addWidget(ColHeader("Equipment", "SC-001"))
        c1l.addWidget(Placeholder(
            "Equipment Tree",
            "EquipmentTreePanel — to be ported",
        ))

        # col2 — Parameters / input sidebar
        self._col2 = QWidget()
        c2l = QVBoxLayout(self._col2)
        c2l.setContentsMargins(0, 0, 0, 0)
        c2l.setSpacing(0)
        c2l.addWidget(ColHeader("Parameters", "CEMA 7th Ed."))
        c2l.addWidget(Placeholder(
            "Input Sidebar",
            "InputSidebarPanel — material, geometry, speed, capacity",
        ))

        # col3 — Results
        self._col3 = QWidget()
        self._c3l  = QVBoxLayout(self._col3)
        self._c3l.setContentsMargins(0, 0, 0, 0)
        self._c3l.setSpacing(0)
        self._col3_header = ColHeader("Results")
        self._c3l.addWidget(self._col3_header)

        # Inner stack for calc-page tab views
        self._calc_tab_stack = QStackedWidget()
        for t in CALC_TABS:
            self._calc_tab_stack.addWidget(Placeholder(
                t["label"],
                f"CalcPage › {t['label']} — to be implemented",
            ))

        # Outer stack: index 0 = calc tabs, index 1+ = other pages
        self._page_stack = QStackedWidget()
        self._page_widgets: dict[str, QWidget] = {}

        # Index 0: calc tab stack wrapper
        self._page_stack.addWidget(self._calc_tab_stack)

        # Index 1+: all other pages
        for page_id, PageClass in PAGE_REGISTRY:
            if page_id == "calc":
                self._page_widgets["calc"] = self._calc_tab_stack
                continue
            w = PageClass()
            self._page_stack.addWidget(w)
            self._page_widgets[page_id] = w

        self._c3l.addWidget(self._page_stack)

        # col4 — Status / KPI
        self._col4 = QWidget()
        c4l = QVBoxLayout(self._col4)
        c4l.setContentsMargins(0, 0, 0, 0)
        c4l.setSpacing(0)
        c4l.addWidget(ColHeader("Status"))
        c4l.addWidget(Placeholder(
            "Status Panel",
            "KpiGrid — capacity, power, torque, wear, bearing L10",
        ))

        # Splitter
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setStyleSheet(f"""
            QSplitter::handle {{ background-color: {BORDER}; }}
            QSplitter::handle:hover {{ background-color: {PRIMARY}; }}
        """)
        self._splitter.setHandleWidth(2)
        for col in (self._col1, self._col2, self._col3, self._col4):
            self._splitter.addWidget(col)
        self._splitter.setSizes([200, 280, 720, 260])
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 0)
        self._splitter.setStretchFactor(2, 1)
        self._splitter.setStretchFactor(3, 0)

    # ── Assemble ──────────────────────────────────────────────────────────
    def _assemble(self):
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.title_bar)
        outer.addWidget(self.menu_bar_w)
        outer.addWidget(self.top_nav)
        outer.addWidget(self._splitter)
        self.setCentralWidget(container)
        self._show_page("calc")

    # ── Backend health check (off main thread) ────────────────────────────
    def _check_backend(self):
        self._health_thread = QThread()
        self._health_worker = _HealthWorker()
        self._health_worker.moveToThread(self._health_thread)
        self._health_thread.started.connect(self._health_worker.run)
        self._health_worker.finished.connect(self._on_health_result)
        self._health_worker.finished.connect(self._health_thread.quit)
        self._health_thread.start()

    def _on_health_result(self, online: bool):
        self.title_bar.set_backend_status(online)
        if online:
            self.run_calculation()

    # ── Slots ─────────────────────────────────────────────────────────────
    def _on_page_changed(self, page_id: str):
        self._current_page = page_id
        self.menu_bar_w.set_active_page(page_id)
        self._show_page(page_id)

    def _on_tab_changed(self, tab_id: str):
        self._current_tab = tab_id
        if self._current_page == "calc":
            self._calc_tab_stack.setCurrentIndex(
                CALC_TAB_INDEX.get(tab_id, 0)
            )
        self._update_col3_header(tab_id if self._current_page == "calc" else None)

    def _show_page(self, page_id: str):
        if page_id == "calc":
            self._page_stack.setCurrentIndex(0)           # calc tab stack
            self._calc_tab_stack.setCurrentIndex(
                CALC_TAB_INDEX.get(self._current_tab, 0)
            )
            self._update_col3_header(self._current_tab)
        else:
            w = self._page_widgets.get(page_id)
            if w:
                self._page_stack.setCurrentWidget(w)
            from theme import PAGE_META
            label = PAGE_META.get(page_id, {}).get("label", page_id.upper())
            self._swap_col3_header(label)

    def _update_col3_header(self, tab_id: Optional[str]) -> None:
        if tab_id is None:
            return
        label  = CALC_TAB_LABELS.get(tab_id, "Results")
        action = None
        if tab_id == "design":
            n_fail, n_warn = self._fail_warn(self._last_results)
            action = fail_warn_badges(n_fail, n_warn)
        self._swap_col3_header(label, action)

    def _swap_col3_header(self, label: str, action: Optional[QWidget] = None) -> None:
        new_header = ColHeader(label, action=action)
        self._c3l.replaceWidget(self._col3_header, new_header)
        self._col3_header.deleteLater()
        self._col3_header = new_header

    # ── Calculation ───────────────────────────────────────────────────────
    def run_calculation(self, payload: Optional[dict] = None) -> None:
        """
        Called whenever inputs change.
        Mirrors bucket-elevator run_calculation() exactly:
          1. Call backend via api_client
          2. Store results
          3. Distribute to all panels
          4. Update KPI chips + fail badge

        Currently distributes to placeholder panels (set_data is a no-op).
        Each panel will handle set_data() when it is implemented.
        """
        if payload is None:
            payload = self._last_payload
        else:
            self._last_payload = payload

        # Route: process pages → /api/calculate/process
        #        conveyor pages → /api/calculate
        if self._current_page in PROCESS_PAGES:
            module_map = {
                "mixer":     "mixer",
                "dryer":     "dryer",
                "cooler":    "cooler",
                "separator": "sep",
                "reactor":   "reactor",
                "compactor": "compact",
            }
            results = fetch_process(module_map[self._current_page], payload)
        else:
            results = fetch_design(payload)

        if results.get("error"):
            print(f"[Backend error] {results.get('message')}")
            return

        self._last_results = results

        # Distribute to panels
        # Each panel's set_data(payload, results) will be wired when
        # it replaces its Placeholder — same pattern as bucket elevator.
        self.top_nav.update_kpis(results)

        n_fail, n_warn = self._fail_warn(results)
        self.top_nav.update_fail_badge(n_fail)

        if self._current_tab == "design" and self._current_page == "calc":
            self._update_col3_header("design")

    def _on_pdf_requested(self):
        """
        Generates a PDF report via matplotlib.
        Wired to AppTitleBar.pdf_requested signal.
        Implementation: next session (matplotlib report generator).
        """
        print("[PDF Report] matplotlib report generator — to be wired.")

    # ── Helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _fail_warn(results: dict):
        checks = (results or {}).get("checks", []) or []
        n_fail = sum(1 for c in checks if c.get("type") == "fail")
        n_warn = sum(1 for c in checks if c.get("type") == "warn")
        return n_fail, n_warn


# ── Entry point ───────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    window = ShellWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()