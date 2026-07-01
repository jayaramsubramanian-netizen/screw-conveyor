"""
main.py — VECTRIX™ Screw Conveyor Designer entry point
═══════════════════════════════════════════════════════════════════════════
Architecture mirrors the bucket-elevator main.py exactly:

  AppTitleBar  (48 px)  — VECTRIX™ brand + module switcher + PDF + version
  PageMenuBar  (28 px)  — Conveyor / Process / Reference pull-down menus
  TopNav       (76 px)  — 'Screw Conveyor ▾' dropdown + tab pills + KPIs
  body QSplitter        — col1 Equipment | col2 Parameters | col3 Results
                          | col4 Status

Each module page is loaded into a QStackedWidget controlled by PageMenuBar.
The Screw Conveyor calc page itself has a second QStackedWidget inside col3
that switches between tab views (Results, Optimizer, Checks, …).

Run:
    python main.py
"""

import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QSplitter, QStackedWidget,
)
from PySide6.QtCore import Qt

from theme import (
    BG, PANEL, BORDER, TEXT, TEXT3, PRIMARY, CALC_TABS,
)
from components import (
    AppTitleBar, TopNav, PageMenuBar, ColHeader, Placeholder,
    fail_warn_badges,
    CalcPage, FamilyPage, FeederPage,
    MixerPage, DryerPage, CoolerPage,
    SeparatorPage, ReactorPage, CompactorPage,
    DatabasePage, ManualPage,
)

# ── Page registry ─────────────────────────────────────────────────────────
# Order must match PAGE_META in theme.py.
# Each entry: (page_id, widget_class)
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

# ── Calc-page tab → stack index mapping ──────────────────────────────────
CALC_TAB_INDEX = {t["id"]: i for i, t in enumerate(CALC_TABS)}


# ── ShellWindow ───────────────────────────────────────────────────────────
class ShellWindow(QMainWindow):
    """
    Full application shell.

    Column layout (QSplitter, horizontal):
      col1  200 px  Equipment / tree panel
      col2  280 px  Parameters / input sidebar
      col3  flex    Results / visualiser (tab-aware QStackedWidget)
      col4  260 px  Status / KPI panel

    This matches the bucket-elevator four-column pattern 1-for-1 so both
    apps look unified when running side by side.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VECTRIX™ — Screw Conveyor Designer")
        self.resize(1440, 900)
        self.setStyleSheet(f"background-color: {BG};")

        self._current_page = "calc"
        self._current_tab  = "design"
        self._last_results: dict = {}

        self._build_chrome()
        self._build_body()
        self._assemble()

    # ── Chrome ────────────────────────────────────────────────────────────
    def _build_chrome(self):
        self.title_bar  = AppTitleBar()
        self.menu_bar_w = PageMenuBar(current_page="calc")
        self.top_nav    = TopNav()

        self.title_bar.pdf_requested.connect(self._on_pdf_requested)
        self.menu_bar_w.page_changed.connect(self._on_page_changed)
        self.top_nav.tab_changed.connect(self._on_tab_changed)

    # ── Body ──────────────────────────────────────────────────────────────
    def _build_body(self):
        # ── col1 : Equipment / project tree ───────────────────────────────
        self._col1 = QWidget()
        c1l = QVBoxLayout(self._col1)
        c1l.setContentsMargins(0, 0, 0, 0)
        c1l.setSpacing(0)
        c1l.addWidget(ColHeader("Equipment", "SC-001"))
        c1l.addWidget(Placeholder(
            "Equipment Tree",
            "EquipmentTreePanel — not yet ported",
        ))

        # ── col2 : Parameters / input sidebar ─────────────────────────────
        self._col2 = QWidget()
        c2l = QVBoxLayout(self._col2)
        c2l.setContentsMargins(0, 0, 0, 0)
        c2l.setSpacing(0)
        c2l.addWidget(ColHeader("Parameters", "CEMA 7th Ed. inputs"))
        c2l.addWidget(Placeholder(
            "Input Sidebar",
            "InputSidebarPanel — material, geometry, speed, capacity",
        ))

        # ── col3 : Results (tab-aware stack + page stack) ─────────────────
        self._col3 = QWidget()
        c3l = QVBoxLayout(self._col3)
        c3l.setContentsMargins(0, 0, 0, 0)
        c3l.setSpacing(0)

        self._col3_header = ColHeader("Results")
        c3l.addWidget(self._col3_header)
        self._c3l = c3l   # keep ref for header swap

        # Outer stack: one widget per application page
        self._page_stack = QStackedWidget()
        self._page_widgets: dict[str, QWidget] = {}
        for page_id, PageClass in PAGE_REGISTRY:
            w = PageClass()
            self._page_stack.addWidget(w)
            self._page_widgets[page_id] = w

        # Inner stack inside CalcPage position: tab-aware sub-views
        # (when CalcPage is replaced with a real implementation these
        # live inside that widget; for now they sit here as named
        # placeholders so the tab switching already works end-to-end)
        self._calc_tab_stack = QStackedWidget()
        self._calc_tab_widgets: dict[str, QWidget] = {}
        for t in CALC_TABS:
            w = Placeholder(
                t["label"],
                f"CalcPage › {t['label']} tab — not yet implemented",
            )
            self._calc_tab_stack.addWidget(w)
            self._calc_tab_widgets[t["id"]] = w

        # Show either the page stack (non-calc pages) or the calc-tab
        # stack (calc page) via a wrapper stack
        self._content_stack = QStackedWidget()
        self._content_stack.addWidget(self._calc_tab_stack)  # index 0 — calc page
        self._content_stack.addWidget(self._page_stack)      # index 1 — other pages
        c3l.addWidget(self._content_stack)

        # ── col4 : Status / KPI ───────────────────────────────────────────
        self._col4 = QWidget()
        c4l = QVBoxLayout(self._col4)
        c4l.setContentsMargins(0, 0, 0, 0)
        c4l.setSpacing(0)
        c4l.addWidget(ColHeader("Status"))
        c4l.addWidget(Placeholder(
            "Status Panel",
            "KpiGrid — capacity, power, torque, wear, bearing L10",
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

        # Initialise to calc page, design tab
        self._show_page("calc")

    # ── Slots ─────────────────────────────────────────────────────────────
    def _on_page_changed(self, page_id: str):
        self._current_page = page_id
        self.menu_bar_w.set_active_page(page_id)
        self._show_page(page_id)

    def _on_tab_changed(self, tab_id: str):
        """Only meaningful when the current page is 'calc'."""
        self._current_tab = tab_id
        if self._current_page == "calc":
            idx = CALC_TAB_INDEX.get(tab_id, 0)
            self._calc_tab_stack.setCurrentIndex(idx)
            self._swap_col3_header(tab_id)

    def _show_page(self, page_id: str):
        if page_id == "calc":
            self._content_stack.setCurrentIndex(0)  # calc-tab stack
            self._swap_col3_header(self._current_tab)
        else:
            # Switch page_stack to the right widget
            w = self._page_widgets.get(page_id)
            if w:
                self._page_stack.setCurrentWidget(w)
            self._content_stack.setCurrentIndex(1)  # page stack
            from theme import PAGE_META
            label = PAGE_META.get(page_id, {}).get("label", page_id.upper())
            self._swap_col3_header_raw(label)

    def _swap_col3_header(self, tab_id: str):
        """Replace the col3 header with a tab-appropriate one."""
        from theme import CALC_TABS
        label = next(
            (t["label"] for t in CALC_TABS if t["id"] == tab_id), "Results"
        )
        action = None
        if tab_id == "design":
            n_fail, n_warn = self._fail_warn(self._last_results)
            action = fail_warn_badges(n_fail, n_warn)
        self._swap_col3_header_raw(label, action)

    def _swap_col3_header_raw(self, label: str, action=None):
        new_header = ColHeader(label, action=action)
        self._c3l.replaceWidget(self._col3_header, new_header)
        self._col3_header.deleteLater()
        self._col3_header = new_header

    @staticmethod
    def _fail_warn(results: dict):
        checks = (results or {}).get("checks", []) or []
        n_fail = sum(1 for c in checks if c.get("type") == "fail")
        n_warn = sum(1 for c in checks if c.get("type") == "warn")
        return n_fail, n_warn

    def _on_pdf_requested(self):
        print("[PDF Report] not yet wired — matplotlib report generator to be added.")

    # ── Public API (called by future InputSidebarPanel) ───────────────────
    def run_calculation(self, payload: dict = None):
        """
        Entry point for all calculation updates.

        Currently a stub — will call the VECTRIX™ Python engine
        (ported from calcEngine() in screw-process-v4.html) and
        distribute results to all panels.
        """
        if payload is None:
            payload = {
                "mat": "Cement", "D": 0.3, "L": 10.0,
                "N": 60, "P": 0.3, "ang": 0, "cap": 30,
                "surge": 1.2, "type": "screw", "shaft_mode": "auto",
            }
        # TODO: call engine.calc_engine(payload) once engine.py is ported
        results = {}
        self._last_results = results
        self.top_nav.update_kpis(results)
        self.top_nav.update_fail_badge(0)


# ── Entry point ───────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Global font — Segoe UI on Windows, system-ui elsewhere
    from PySide6.QtGui import QFont
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    window = ShellWindow()
    window.run_calculation()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()