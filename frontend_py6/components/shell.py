"""
components/shell.py — VECTRIX™ Screw Conveyor shell chrome
═══════════════════════════════════════════════════════════════════════════
AppTitleBar  48 px  brand + module switcher + backend status + PDF button
PageMenuBar  28 px  Conveyor / Process / Reference pull-down menus
TopNav       76 px  app dropdown + tab pills + KPI chips

Pylance fixes applied:
  - QAction constructed with parent only; shortcut/triggered wired separately
    (PySide6 ≥ 6.4 removed keyword-argument overloads for QAction.__init__)
  - All Optional[] annotations added to parent parameters
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QFrame, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QMenu,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence

from core.theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, ACCENT, BRAND_RED,
    CALC_TABS, PAGE_META, PAGE_GROUPS,
    TAB_PILL_HEIGHT, TAB_PILL_RADIUS,
    MODULE_PILL_HEIGHT, MODULE_PILL_RADIUS,
)
from core.widgets import (
    ColHeader, NavTabButton, ModulePill, KpiChip, fail_warn_badges,
)


# ── helpers ───────────────────────────────────────────────────────────────

def _action(
    label: str,
    parent: QWidget,
    shortcut: Optional[str] = None,
    slot=None,
) -> QAction:
    """
    Build a QAction without using removed keyword overloads.
    PySide6 ≥ 6.4: QAction(parent) is the safe constructor;
    everything else is set via setters.
    """
    act = QAction(label, parent)
    if shortcut:
        act.setShortcut(QKeySequence(shortcut))
    if slot is not None:
        act.triggered.connect(slot)
    return act


# ── AppTitleBar ───────────────────────────────────────────────────────────
class AppTitleBar(QFrame):
    """48 px platform bar — brand | module switcher | backend status | PDF."""

    pdf_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setStyleSheet(
            f"background-color: {PANEL}; border-bottom: 1px solid {BORDER};"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(14)

        # Brand icon
        icon = QLabel("🔩")
        icon.setFixedSize(30, 30)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            f"background-color: {BRAND_RED}; border-radius: 7px; font-size: 15px;"
        )
        layout.addWidget(icon)

        # Brand text
        brand_box = QVBoxLayout()
        brand_box.setSpacing(0)
        brand_title = QLabel("VECTRIX™")
        brand_title.setStyleSheet(
            f"color: {TEXT}; font-size: 13px; font-weight: 700;"
        )
        brand_sub = QLabel("DESIGN PLATFORM")
        brand_sub.setStyleSheet(
            f"color: {TEXT3}; font-size: 8px; font-weight: 600; letter-spacing: 1px;"
        )
        brand_box.addWidget(brand_title)
        brand_box.addWidget(brand_sub)
        layout.addLayout(brand_box)

        # Module switcher
        module_bar = QFrame()
        module_bar.setStyleSheet(
            f"background-color: {BG}; border: 1px solid {BORDER}; border-radius: 999px;"
        )
        module_layout = QHBoxLayout(module_bar)
        module_layout.setContentsMargins(3, 3, 3, 3)
        module_layout.setSpacing(2)

        sc_pill = ModulePill("🔩", "Screw Conveyor", active=True, enabled=True)
        module_layout.addWidget(sc_pill)

        badge = QLabel("VECTOMEC™")
        badge.setStyleSheet(
            f"background-color: rgba(255,255,255,.18); color: white; "
            f"border-radius: 999px; padding: 2px 8px; "
            f"font-size: 8.5px; font-weight: 700;"
        )
        module_layout.addWidget(badge)

        be_pill = ModulePill("⛏", "Bucket Elevator", active=False, enabled=False)
        be_pill.setToolTip("Launch the Bucket Elevator application separately")
        module_layout.addWidget(be_pill)

        layout.addWidget(module_bar)
        layout.addStretch()

        # Backend status dot
        self._backend_dot = QLabel("●")
        self._backend_dot.setToolTip("Backend: checking…")
        self._backend_dot.setStyleSheet(f"color: {MUTED}; font-size: 14px;")
        layout.addWidget(self._backend_dot)

        backend_lbl = QLabel("Backend")
        backend_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 10px;")
        layout.addWidget(backend_lbl)

        # PDF button
        pdf_btn = QPushButton("⬇  PDF Report")
        pdf_btn.setFixedHeight(MODULE_PILL_HEIGHT)
        pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pdf_btn.setStyleSheet(
            f"background-color: {PANEL2}; color: {TEXT2}; "
            f"border: 1px solid {BORDER}; border-radius: {MODULE_PILL_RADIUS}px; "
            f"padding: 0px 14px; font-size: 11.5px; font-weight: 600;"
        )
        pdf_btn.clicked.connect(self.pdf_requested)
        layout.addWidget(pdf_btn)

        # Version label
        version_lbl = QLabel("JAYVEECONS GROUP  ·  V1.0")
        version_lbl.setStyleSheet(
            f"color: {TEXT3}; font-size: 10px; font-weight: 600; letter-spacing: .5px;"
        )
        layout.addWidget(version_lbl)

    def set_backend_status(self, online: bool) -> None:
        if online:
            self._backend_dot.setStyleSheet(f"color: {SUCCESS}; font-size: 14px;")
            self._backend_dot.setToolTip("Backend: connected")
        else:
            self._backend_dot.setStyleSheet(f"color: {DANGER}; font-size: 14px;")
            self._backend_dot.setToolTip(
                "Backend: offline — run: uvicorn backend.main:app --reload"
            )


# ── PageMenuBar ───────────────────────────────────────────────────────────
class PageMenuBar(QFrame):
    """28 px Windows-style pull-down menu row — Conveyor / Process / Reference."""

    page_changed = Signal(str)

    _MENU_QSS = f"""
        QMenu {{
            background-color: {PANEL2}; color: {TEXT2};
            border: 1px solid {BORDER}; border-radius: 8px; padding: 4px;
        }}
        QMenu::item {{ padding: 5px 22px 5px 12px; border-radius: 4px; font-size: 12px; }}
        QMenu::item:selected {{ background-color: {PRIMARY}; color: white; }}
        QMenu::separator {{ height: 1px; background-color: {BORDER}; margin: 3px 6px; }}
    """
    _BTN_QSS = f"""
        QPushButton {{
            background-color: transparent; color: {TEXT2};
            border-style: none; padding: 0px 12px; font-size: 12px;
        }}
        QPushButton:hover {{ background-color: {PANEL2}; }}
        QPushButton::menu-indicator {{ image: none; }}
    """

    def __init__(self, current_page: str = "calc", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current = current_page
        self.setFixedHeight(28)
        self.setStyleSheet(
            f"background-color: {BG}; border-bottom: 1px solid {BORDER};"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(0)

        for group_id, group in PAGE_GROUPS.items():
            btn = QPushButton(group["label"] + "  ▾")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.setStyleSheet(self._BTN_QSS)

            menu = QMenu(btn)
            menu.setStyleSheet(self._MENU_QSS)

            for page_id in group["pages"]:
                meta = PAGE_META[page_id]
                act = _action(f"{meta['icon']}  {meta['label']}", self)
                act.triggered.connect(
                    lambda checked, pid=page_id: self.page_changed.emit(pid)
                )
                menu.addAction(act)

            btn.setMenu(menu)
            layout.addWidget(btn)

        layout.addStretch()

        self._active_lbl = QLabel()
        self._active_lbl.setStyleSheet(
            f"color: {ACCENT}; font-size: 10.5px; font-weight: 700; "
            f"letter-spacing: .5px; padding-right: 8px;"
        )
        self.set_active_page(current_page)
        layout.addWidget(self._active_lbl)

    def set_active_page(self, page_id: str) -> None:
        self._current = page_id
        meta = PAGE_META.get(page_id, {})
        self._active_lbl.setText(
            f"{meta.get('icon', '')}  {meta.get('label', page_id)}"
        )


# ── TopNav ────────────────────────────────────────────────────────────────
class TopNav(QFrame):
    """76 px page-level bar — app dropdown + tab pills + KPI chips."""

    tab_changed = Signal(str)

    _MENU_QSS = f"""
        QMenu {{
            background-color: {PANEL2}; color: {TEXT2};
            border: 1px solid {BORDER}; border-radius: 8px; padding: 4px;
        }}
        QMenu::item {{ padding: 6px 24px 6px 14px; border-radius: 5px; font-size: 12px; }}
        QMenu::item:selected {{ background-color: {PRIMARY}; color: white; }}
        QMenu::separator {{ height: 1px; background-color: {BORDER}; margin: 4px 8px; }}
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(76)
        self.setStyleSheet(
            f"background-color: {PANEL}; border-bottom: 1px solid {BORDER};"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        # App dropdown
        app_btn = QPushButton("Screw Conveyor  ▾")
        app_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        app_btn.setFixedHeight(TAB_PILL_HEIGHT)
        app_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {TEXT2};
                border-style: none; border-radius: {TAB_PILL_RADIUS}px;
                padding: 0px 16px; font-size: 12.5px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {PANEL2}; }}
            QPushButton::menu-indicator {{ image: none; }}
        """)

        app_menu = QMenu(app_btn)
        app_menu.setStyleSheet(self._MENU_QSS)

        # Maximize toggle — needs instance reference so store it
        self._act_maximize = _action("Maximize", self, slot=self._toggle_maximize)

        app_menu.addAction(
            _action("Minimize", self, slot=lambda: self.window().showMinimized())
        )
        app_menu.addAction(self._act_maximize)
        app_menu.addSeparator()
        app_menu.addAction(
            _action("New Project…", self, shortcut="Ctrl+N",
                    slot=lambda: self._stub("New Project"))
        )
        app_menu.addAction(
            _action("Open Design…", self, shortcut="Ctrl+O",
                    slot=lambda: self._stub("Open Design"))
        )
        app_menu.addAction(
            _action("Save Design", self, shortcut="Ctrl+S",
                    slot=lambda: self._stub("Save Design"))
        )
        app_menu.addSeparator()
        app_menu.addAction(
            _action("Exit", self, shortcut="Ctrl+Q",
                    slot=lambda: self.window().close())
        )
        app_btn.setMenu(app_menu)
        layout.addWidget(app_btn)

        # Separator
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background-color: {BORDER};")
        layout.addWidget(sep)

        # Tab pills
        self.tab_buttons: dict[str, NavTabButton] = {}
        for t in CALC_TABS:
            label = t["label"]
            if t.get("badge"):
                label = f"{label}  ·{t['badge']}"
            btn = NavTabButton(label)
            btn.clicked.connect(
                lambda checked, tid=t["id"]: self._select_tab(tid)
            )
            layout.addWidget(btn)
            self.tab_buttons[t["id"]] = btn
        self.tab_buttons["design"].setChecked(True)

        layout.addStretch()

        # KPI chips
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self.kpi_chips: dict[str, KpiChip] = {}
        for label, unit in (("Q", "t/h"), ("P", "kW"), ("η", "%")):
            chip = KpiChip(label, unit)
            kpi_row.addWidget(chip)
            self.kpi_chips[label] = chip
        layout.addLayout(kpi_row)

    # ── public update slots ───────────────────────────────────────────────
    def update_kpis(self, results: dict) -> None:
        r = results or {}

        qt = r.get("Qt")
        if qt is not None:
            cap_ok = r.get("cap_ok")
            col = SUCCESS if cap_ok else (DANGER if cap_ok is False else TEXT3)
            self.kpi_chips["Q"].set_value(f"{qt:.1f}", col)

        pt = r.get("Pt")
        if pt is not None:
            self.kpi_chips["P"].set_value(f"{pt:.2f}", WARNING)

        score = r.get("eff_score")
        if score is not None:
            col = SUCCESS if score >= 70 else (WARNING if score >= 45 else DANGER)
            self.kpi_chips["η"].set_value(str(int(score)), col)

    def update_fail_badge(self, n_fail: int) -> None:
        base = next(
            (t["label"] for t in CALC_TABS if t["id"] == "checks"), "Checks"
        )
        text = f"{base}  ·{n_fail}" if n_fail > 0 else base
        self.tab_buttons["checks"].setText(text)
        self.tab_buttons["checks"]._apply_style()

    # ── internals ─────────────────────────────────────────────────────────
    def _select_tab(self, tab_id: str) -> None:
        for tid, btn in self.tab_buttons.items():
            btn.setChecked(tid == tab_id)
        self.tab_changed.emit(tab_id)

    def _toggle_maximize(self) -> None:
        win = self.window()
        if win.isMaximized():
            win.showNormal()
            self._act_maximize.setText("Maximize")
        else:
            win.showMaximized()
            self._act_maximize.setText("Restore")

    @staticmethod
    def _stub(name: str) -> None:
        print(f"[{name}] not yet wired.")