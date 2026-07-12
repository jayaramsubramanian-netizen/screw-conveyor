"""
main.py — VECTRIX™ Screw Conveyor Designer entry point
═══════════════════════════════════════════════════════════════════════════
Architecture mirrors the bucket-elevator main.py exactly:

  AppTitleBar  (48 px)  — brand + module switcher + backend status + PDF
  PageMenuBar  (28 px)  — Conveyor / Process / Reference pull-down menus
  TopNav       (76 px)  — app dropdown + tab pills + KPI chips
  QSplitter             — col1 Equipment | col2 Parameters
                          | col3 Results (tab-aware) | col4 Status

col2 is now the live InputSidebarPanel.  It emits calculate(payload) on
every field change (debounced 400 ms) and on the Calculate button click.
ShellWindow receives that signal, calls api_client.fetch_design(), and
distributes results to all panels.

Backend:
  POST /api/calculate         → backend/core/engine.py → calc_engine()
  POST /api/calculate/process → backend/core/process_engine.py
  GET  /api/materials         → backend/db/database.py

Run backend first:
    uvicorn backend.main:app --reload
Then:
    python main.py
"""

from __future__ import annotations

from typing import Optional
import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QSplitter, QStackedWidget,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont

from theme import (
    BG, PANEL, BORDER, PRIMARY,
    CALC_TABS, DEFAULT_PAYLOAD,
)
from api_client import fetch_design, fetch_process, fetch_axial_profile, health_check
from components import (
    AppTitleBar, TopNav, PageMenuBar,
    ColHeader, Placeholder, fail_warn_badges,
    FamilyPage, FeederPage,
    MixerPage, DryerPage, CoolerPage,
    SeparatorPage, ReactorPage, CompactorPage,
    DatabasePage, ManualPage,
)
from components.pages.calc_page import InputSidebarPanel
from components.pages.results_panel import ResultsPanel
from components.pages.axial_panel import AxialProfilePanel

# ── Page registry — non-calc pages only (calc uses InputSidebarPanel) ─────
PAGE_REGISTRY = [
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

PROCESS_PAGES = {"mixer", "dryer", "cooler", "separator", "reactor", "compactor"}

CALC_TAB_INDEX  = {t["id"]: i for i, t in enumerate(CALC_TABS)}
CALC_TAB_LABELS = {t["id"]: t["label"] for t in CALC_TABS}


# ── Background health check worker ───────────────────────────────────────
class _HealthWorker(QObject):
    finished = Signal(bool)

    def run(self) -> None:
        self.finished.emit(health_check())


# ── ShellWindow ───────────────────────────────────────────────────────────
class ShellWindow(QMainWindow):
    """
    Full application shell — four-column layout identical to bucket elevator.

    col1  200 px  Equipment / project tree     (Placeholder, next session)
    col2  280 px  InputSidebarPanel            (LIVE — all EngineInput fields)
    col3  flex    Results tab stack             (Placeholders, next session)
    col4  260 px  Status / KPI panel            (Placeholder, next session)
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VECTRIX™ — Screw Conveyor Designer")
        self.resize(1440, 900)
        self.setStyleSheet(f"background-color: {BG};")

        self._current_page   = "calc"
        self._current_tab    = "design"
        self._last_results: dict = {}
        self._last_payload   = dict(DEFAULT_PAYLOAD)

        self._build_chrome()
        self._build_body()
        self._assemble()
        self._check_backend()

    # ── Chrome ────────────────────────────────────────────────────────────
    def _build_chrome(self) -> None:
        self.title_bar  = AppTitleBar()
        self.menu_bar_w = PageMenuBar(current_page="calc")
        self.top_nav    = TopNav()

        self.title_bar.pdf_requested.connect(self._on_pdf_requested)
        self.menu_bar_w.page_changed.connect(self._on_page_changed)
        self.top_nav.tab_changed.connect(self._on_tab_changed)

    # ── Body ──────────────────────────────────────────────────────────────
    def _build_body(self) -> None:

        # ── col1 : Equipment tree (placeholder) ───────────────────────────
        self._col1 = QWidget()
        c1l = QVBoxLayout(self._col1)
        c1l.setContentsMargins(0, 0, 0, 0)
        c1l.setSpacing(0)
        c1l.addWidget(ColHeader("Equipment", "SC-001"))
        c1l.addWidget(Placeholder(
            "Equipment Tree",
            "Conveyor list + project tree — next session",
        ))

        # ── col2 : InputSidebarPanel (LIVE) ───────────────────────────────
        self._col2 = QWidget()
        c2l = QVBoxLayout(self._col2)
        c2l.setContentsMargins(0, 0, 0, 0)
        c2l.setSpacing(0)
        c2l.addWidget(ColHeader("Parameters", "CEMA 7th Ed."))

        self._sidebar = InputSidebarPanel()
        self._sidebar.calculate.connect(self._on_sidebar_calculate)
        c2l.addWidget(self._sidebar)

        # ── col3 : Results tab stack ───────────────────────────────────────
        self._col3 = QWidget()
        self._c3l  = QVBoxLayout(self._col3)
        self._c3l.setContentsMargins(0, 0, 0, 0)
        self._c3l.setSpacing(0)
        self._col3_header = ColHeader("Results")
        self._c3l.addWidget(self._col3_header)

        # Inner stack: one view per calc tab.
        # "design" is the live ResultsPanel, "axial" is the live
        # AxialProfilePanel — all others remain honest Placeholders
        # until their session arrives.
        self._calc_tab_stack = QStackedWidget()
        self._results_panel: Optional[ResultsPanel] = None
        self._axial_panel: Optional[AxialProfilePanel] = None
        self._axial_loaded_for: Optional[str] = None  # payload signature cache
        for t in CALC_TABS:
            if t["id"] == "design":
                self._results_panel = ResultsPanel()
                self._calc_tab_stack.addWidget(self._results_panel)
            elif t["id"] == "axial":
                self._axial_panel = AxialProfilePanel()
                self._axial_panel.refresh_requested.connect(self._on_axial_refresh)
                self._calc_tab_stack.addWidget(self._axial_panel)
            else:
                self._calc_tab_stack.addWidget(Placeholder(
                    t["label"],
                    f"CalcPage › {t['label']} — next session",
                ))

        # Outer stack: index 0 = calc tab stack, index 1+ = module pages
        self._page_stack = QStackedWidget()
        self._page_widgets: dict[str, QWidget] = {
            "calc": self._calc_tab_stack,
        }
        self._page_stack.addWidget(self._calc_tab_stack)   # index 0

        for page_id, PageClass in PAGE_REGISTRY:
            w = PageClass()
            self._page_stack.addWidget(w)
            self._page_widgets[page_id] = w

        self._c3l.addWidget(self._page_stack)

        # ── col4 : Status / KPI (placeholder) ────────────────────────────
        self._col4 = QWidget()
        c4l = QVBoxLayout(self._col4)
        c4l.setContentsMargins(0, 0, 0, 0)
        c4l.setSpacing(0)
        c4l.addWidget(ColHeader("Status"))
        c4l.addWidget(Placeholder(
            "Status Panel",
            "KpiGrid — capacity, power, torque, wear, L10 — next session",
        ))

        # ── Splitter ──────────────────────────────────────────────────────
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
    def _assemble(self) -> None:
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

    # ── Backend health check ──────────────────────────────────────────────
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
        if online:
            # Populate material / bearing / gearbox combos
            self._sidebar.load_combos()
            # Fire first calculation with defaults
            self.run_calculation(self._last_payload)

    # ── Slots ─────────────────────────────────────────────────────────────
    def _on_sidebar_calculate(self, payload: dict) -> None:
        """Received from InputSidebarPanel.calculate signal."""
        self._last_payload = payload
        self.run_calculation(payload)

    def _on_page_changed(self, page_id: str) -> None:
        self._current_page = page_id
        self.menu_bar_w.set_active_page(page_id)
        self._show_page(page_id)

    def _on_tab_changed(self, tab_id: str) -> None:
        self._current_tab = tab_id
        if self._current_page == "calc":
            self._calc_tab_stack.setCurrentIndex(
                CALC_TAB_INDEX.get(tab_id, 0)
            )
            if tab_id == "axial":
                self._maybe_fetch_axial()
        self._update_col3_header(
            tab_id if self._current_page == "calc" else None
        )

    def _show_page(self, page_id: str) -> None:
        if page_id == "calc":
            self._page_stack.setCurrentIndex(0)
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

    def _swap_col3_header(
        self, label: str, action: Optional[QWidget] = None
    ) -> None:
        new_header = ColHeader(label, action=action)
        self._c3l.replaceWidget(self._col3_header, new_header)
        self._col3_header.deleteLater()
        self._col3_header = new_header

    # ── Calculation ───────────────────────────────────────────────────────
    def run_calculation(self, payload: Optional[dict] = None) -> None:
        """
        Route payload to the correct backend endpoint, then distribute
        results to all live panels.

        Panels currently receiving results:
          • top_nav KPI chips  — Qt, Pt, eff_score
          • top_nav fail badge — warns.crit count

        When results cards (col3) and status panel (col4) are implemented
        they will be wired here via their set_data(payload, results) methods,
        identical to the bucket elevator pattern.
        """
        if payload is None:
            payload = self._last_payload

        if self._current_page in PROCESS_PAGES:
            # Page ids match backend route segments exactly:
            # /api/v1/process/{mixer,dryer,cooler,separator,reactor,compactor}
            # api_client.fetch_process() validates the name and 404-guards
            # against a typo here, so no local mapping dict is needed.
            results = fetch_process(self._current_page, payload)
        else:
            results = fetch_design(payload)

        if results.get("error"):
            print(f"[Backend error] {results.get('message')}")
            return

        self._last_results = results

        # ── Distribute to panels ──────────────────────────────────────────
        # Build a flat-key dict for the KPI chips from nested engine result
        kpi = {
            "Qt":      results.get("cap", {}).get("Qt"),
            "cap_ok":  results.get("cap", {}).get("ok"),
            "Pt":      results.get("pwr", {}).get("Pt"),
            "eff_score": results.get("eff", {}).get("score"),
        }
        self.top_nav.update_kpis(kpi)

        # Fail badge — count critical warnings
        n_crit = len(results.get("warns", {}).get("crit", []))
        n_adv  = len(results.get("warns", {}).get("adv",  []))
        self.top_nav.update_fail_badge(n_crit)

        # Results tab cards — only meaningful for the conveyor calculator,
        # not process modules (those get their own results view later)
        if self._current_page == "calc" and self._results_panel is not None:
            self._results_panel.set_data(results)

        if self._current_tab == "design" and self._current_page == "calc":
            self._update_col3_header("design")

        # New payload → axial profile (if previously loaded) is stale.
        # Don't auto-refetch here (avoids a network call on every
        # debounced keystroke) — just invalidate the cache so the next
        # time the Axial Profile tab is opened it fetches fresh data.
        self._axial_loaded_for = None

    # ── Axial profile (lazy fetch) ──────────────────────────────────────────
    def _maybe_fetch_axial(self) -> None:
        """
        Called when the Axial Profile tab becomes active. Fetches only if
        the current payload hasn't already been loaded (avoids refetching
        on every tab click when nothing has changed).
        """
        sig = str(self._last_payload)
        if sig == self._axial_loaded_for:
            return
        self._fetch_axial(self._axial_panel.segments_value() if self._axial_panel else 60)

    def _on_axial_refresh(self, segments: int) -> None:
        """User clicked Refresh or changed the Segments spinbox + Refresh."""
        self._fetch_axial(segments)

    def _fetch_axial(self, segments: int) -> None:
        if self._axial_panel is None:
            return
        self._axial_panel.set_loading()
        response = fetch_axial_profile({
            "inp": self._last_payload,
            "segments": segments,
        })
        if response.get("error"):
            self._axial_panel.set_error(response.get("message", "Unknown error"))
            return
        self._axial_panel.set_data(response)
        self._axial_loaded_for = str(self._last_payload)

    # ── PDF ───────────────────────────────────────────────────────────────
    def _on_pdf_requested(self) -> None:
        print("[PDF Report] matplotlib report generator — to be wired.")

    # ── Helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _fail_warn(results: dict) -> tuple[int, int]:
        warns = (results or {}).get("warns", {})
        return (
            len(warns.get("crit", [])),
            len(warns.get("adv",  [])),
        )


# ── Entry point ───────────────────────────────────────────────────────────
def main() -> None:
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