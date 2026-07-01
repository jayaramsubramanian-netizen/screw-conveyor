"""
shell.py — VECTRIX™ Screw Conveyor shell chrome
═══════════════════════════════════════════════════════════════════════════
AppTitleBar   — 48 px platform bar: VECTRIX™ brand + module switcher
                (Bucket Elevator ←→ Screw Conveyor) + PDF Report + version
TopNav        — 76 px page bar: app dropdown menu + tab pills + KPI chips
MenuBar       — Windows-style pull-down menu row (mirrors App.tsx MenuBar)

Mirrors the structure of main.py in the bucket-elevator app exactly so
both applications have the same chrome when viewed side by side.
"""

from PySide6.QtWidgets import (
    QFrame, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QMenu, QSplitter,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, WARNING, SUCCESS, DANGER, ACCENT, BRAND_RED,
    CALC_TABS, PAGE_META, PAGE_GROUPS,
    TAB_PILL_HEIGHT, TAB_PILL_RADIUS,
    MODULE_PILL_HEIGHT, MODULE_PILL_RADIUS,
)
from components.widgets import (
    ColHeader, NavTabButton, ModulePill, KpiChip, fail_warn_badges,
)


# ── AppTitleBar ───────────────────────────────────────────────────────────
class AppTitleBar(QFrame):
    """48 px platform bar.

    Left  : ⚙ icon (brand-red square) + VECTRIX™ / DESIGN PLATFORM text
    Centre: module switcher pill-bar  (Bucket Elevator | Screw Conveyor)
    Right : PDF Report button + version label

    The Screw Conveyor pill is ACTIVE here (inverse of bucket elevator).
    The Bucket Elevator pill is present but disabled — user launches the
    other application separately; we do not embed it.
    """

    pdf_requested = Signal()

    def __init__(self, parent=None):
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
            f"background-color: {BRAND_RED}; border-radius: 7px; "
            f"font-size: 15px;"
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

        # Module switcher pill-bar
        module_bar = QFrame()
        module_bar.setStyleSheet(
            f"background-color: {BG}; border: 1px solid {BORDER}; border-radius: 999px;"
        )
        module_layout = QHBoxLayout(module_bar)
        module_layout.setContentsMargins(3, 3, 3, 3)
        module_layout.setSpacing(2)

        # Screw Conveyor — ACTIVE
        sc_pill = ModulePill("🔩", "Screw Conveyor", active=True, enabled=True)
        module_layout.addWidget(sc_pill)

        # VECTOMEC™ badge on active pill
        badge_lbl = QLabel("VECTOMEC™")
        badge_lbl.setStyleSheet(
            f"background-color: rgba(255,255,255,.18); color: white; "
            f"border-radius: 999px; padding: 2px 8px; "
            f"font-size: 8.5px; font-weight: 700; margin-left: -8px;"
        )
        module_layout.addWidget(badge_lbl)

        # Bucket Elevator — inactive / disabled (other app)
        be_pill = ModulePill("⛏", "Bucket Elevator", active=False, enabled=False)
        module_layout.addWidget(be_pill)

        layout.addWidget(module_bar)
        layout.addStretch()

        # PDF Report button
        pdf_btn = QPushButton("⬇  PDF Report")
        pdf_btn.setFixedHeight(MODULE_PILL_HEIGHT)
        pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pdf_btn.setStyleSheet(
            f"background-color: {PANEL2}; color: {TEXT2}; "
            f"border-style: solid; border-width: 1px; border-color: {BORDER}; "
            f"border-radius: {MODULE_PILL_RADIUS}px; "
            f"padding: 0px 14px; font-size: 11.5px; font-weight: 600;"
        )
        pdf_btn.clicked.connect(self.pdf_requested)
        layout.addWidget(pdf_btn)

        # Version / company label
        version_lbl = QLabel("JAYVEECONS GROUP · V1.0")
        version_lbl.setStyleSheet(
            f"color: {TEXT3}; font-size: 10.5px; font-weight: 600; letter-spacing: .5px;"
        )
        layout.addWidget(version_lbl)


# ── TopNav ────────────────────────────────────────────────────────────────
class TopNav(QFrame):
    """76 px page-level bar.

    Left  : 'Screw Conveyor ▾' dropdown (window controls + file ops)
    Centre: tab pill row (Results / Optimizer / Checks / Components /
            Wear & Life / Structural / Materials)
    Right : KPI chips (Q t/h · P kW · η %)

    Mirror of the bucket-elevator TopNav — same fixed height, same pill
    geometry, same menu QSS, same KPI chip style.
    """

    tab_changed = Signal(str)   # emits tab id string

    _MENU_QSS = f"""
        QMenu {{
            background-color: {PANEL2}; color: {TEXT2};
            border: 1px solid {BORDER}; border-radius: 8px; padding: 4px;
        }}
        QMenu::item {{ padding: 6px 24px 6px 14px; border-radius: 5px; font-size: 12px; }}
        QMenu::item:selected {{ background-color: {PRIMARY}; color: white; }}
        QMenu::separator {{ height: 1px; background-color: {BORDER}; margin: 4px 8px; }}
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(76)
        self.setStyleSheet(
            f"background-color: {PANEL}; border-bottom: 1px solid {BORDER};"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        # ── App dropdown ─────────────────────────────────────────────────
        app_btn = QPushButton("Screw Conveyor  ▾")
        app_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        app_btn.setFixedHeight(TAB_PILL_HEIGHT)
        app_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {TEXT2};
                border-style: none; border-width: 0px;
                border-radius: {TAB_PILL_RADIUS}px;
                padding: 0px 16px; font-size: 12.5px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {PANEL2}; }}
            QPushButton::menu-indicator {{ image: none; }}
        """)
        app_menu = QMenu(app_btn)
        app_menu.setStyleSheet(self._MENU_QSS)

        self._act_maximize = QAction("Maximize", self)
        self._act_maximize.triggered.connect(self._toggle_maximize)
        app_menu.addAction(QAction("Minimize", self,
            triggered=lambda: self.window().showMinimized()))
        app_menu.addAction(self._act_maximize)
        app_menu.addSeparator()
        app_menu.addAction(QAction("New Project…", self,
            shortcut="Ctrl+N", triggered=lambda: self._stub("New Project")))
        app_menu.addAction(QAction("Open Design…", self,
            shortcut="Ctrl+O", triggered=lambda: self._stub("Open Design")))
        app_menu.addAction(QAction("Save Design", self,
            shortcut="Ctrl+S", triggered=lambda: self._stub("Save Design")))
        app_menu.addAction(QAction("Save As…", self,
            triggered=lambda: self._stub("Save As")))
        app_menu.addSeparator()
        app_menu.addAction(QAction("Exit", self,
            shortcut="Ctrl+Q", triggered=lambda: self.window().close()))
        app_btn.setMenu(app_menu)
        layout.addWidget(app_btn)

        # Separator
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background-color: {BORDER};")
        layout.addWidget(sep)

        # ── Tab pills ────────────────────────────────────────────────────
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

        # ── KPI chips ─────────────────────────────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self.kpi_chips: dict[str, KpiChip] = {}
        for label, unit in (("Q", "t/h"), ("P", "kW"), ("η", "%")):
            chip = KpiChip(label, unit)
            kpi_row.addWidget(chip)
            self.kpi_chips[label] = chip
        layout.addLayout(kpi_row)

    # ── public update slots ───────────────────────────────────────────────
    def update_kpis(self, results: dict):
        r = results or {}
        q = r.get("Qt")
        if q is not None:
            ok = r.get("cap_ok")
            col = SUCCESS if ok else (DANGER if ok is False else TEXT3)
            self.kpi_chips["Q"].set_value(f"{q:.1f}", col)
        p = r.get("Pt")
        if p is not None:
            self.kpi_chips["P"].set_value(f"{p:.2f}", WARNING)
        score = r.get("eff_score")
        if score is not None:
            col = SUCCESS if score >= 70 else (WARNING if score >= 45 else DANGER)
            self.kpi_chips["η"].set_value(str(int(score)), col)

    def update_fail_badge(self, n_fail: int):
        base = next(
            (t["label"] for t in CALC_TABS if t["id"] == "checks"), "Checks"
        )
        text = f"{base}  ·{n_fail}" if n_fail > 0 else base
        self.tab_buttons["checks"].setText(text)
        self.tab_buttons["checks"]._apply_style()

    # ── internals ─────────────────────────────────────────────────────────
    def _select_tab(self, tab_id: str):
        for tid, btn in self.tab_buttons.items():
            btn.setChecked(tid == tab_id)
        self.tab_changed.emit(tab_id)

    def _toggle_maximize(self):
        win = self.window()
        if win.isMaximized():
            win.showNormal()
            self._act_maximize.setText("Maximize")
        else:
            win.showMaximized()
            self._act_maximize.setText("Restore")

    @staticmethod
    def _stub(name: str):
        print(f"[{name}] not yet wired.")


# ── PageMenuBar ───────────────────────────────────────────────────────────
class PageMenuBar(QFrame):
    """28 px Windows-style pull-down menu row.

    Mirrors App.tsx MenuBar — three groups:
      Conveyor   : Screw Conveyor, Family Designer, Feeder/Doser
      Process    : Mixer, Dryer, Cooler, Separator, Reactor, Compactor
      Reference  : Material Database, User Manual

    Emits page_changed(page_id) when user picks a module.
    """

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
            border-style: none; border-width: 0px;
            padding: 0px 12px; font-size: 12px;
        }}
        QPushButton:hover {{ background-color: {PANEL2}; }}
        QPushButton::menu-indicator {{ image: none; }}
    """

    def __init__(self, current_page: str = "calc", parent=None):
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
                action = QAction(
                    f"{meta['icon']}  {meta['label']}", self
                )
                action.triggered.connect(
                    lambda checked, pid=page_id: self.page_changed.emit(pid)
                )
                menu.addAction(action)

            btn.setMenu(menu)
            layout.addWidget(btn)

        layout.addStretch()

        # Active module indicator (right side, mirrors TitleBar in App.tsx)
        self._active_lbl = QLabel()
        self._active_lbl.setStyleSheet(
            f"color: {ACCENT}; font-size: 10.5px; font-weight: 700; "
            f"letter-spacing: .5px; padding-right: 8px;"
        )
        self.set_active_page(current_page)
        layout.addWidget(self._active_lbl)

    def set_active_page(self, page_id: str):
        self._current = page_id
        meta = PAGE_META.get(page_id, {})
        icon  = meta.get("icon", "")
        label = meta.get("label", page_id.upper())
        self._active_lbl.setText(f"{icon}  {label}")