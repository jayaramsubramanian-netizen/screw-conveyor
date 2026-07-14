"""
components/pages/calc_page.py — VECTRIX™ Screw Conveyor calc page
═══════════════════════════════════════════════════════════════════════════
InputSidebarPanel  — col2: all EngineInput fields, grouped and collapsible
                     Emits calculate(payload: dict) signal when user
                     clicks Calculate or changes any field (debounced 400ms)

Every field name matches EngineInput exactly so the payload dict can be
passed directly to api_client.fetch_design() with no transformation.

Material / bearing / gearbox ComboBoxes are populated from the backend
via api_client.fetch_materials() on first show.

Layout (col2, 280 px wide, full height, scrollable):
  ┌─ A · Geometry ──────────────────────────────────┐
  │  type  D  L  N  P  ang                          │
  ├─ B · Capacity ──────────────────────────────────┤
  │  mat  cap  surge  duty                          │
  ├─ C · Multi-pitch  [▸ expand] ───────────────────┤
  │  (collapsed by default)                         │
  ├─ D · Shaft ─────────────────────────────────────┤
  │  shaft_mode  sallow  support_cond               │
  │  (manual: shtype  pod  pwall)                   │
  ├─ E · Flight & Wear ─────────────────────────────┤
  │  ft  wa  temp_c                                 │
  ├─ F · Drive  [▸ expand] ─────────────────────────┤
  │  brg  gbx  bload  hangers                       │
  ├─ G · Standards  [▸ expand] ─────────────────────┤
  │  lam_factor  contAFact  use_fill_coupling        │
  └─────────────────────────────────────────────────┘
  [  Calculate  ]  ← full-width button, sticky bottom
"""

from __future__ import annotations

from typing import Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QDoubleSpinBox, QSpinBox,
    QCheckBox, QPushButton, QScrollArea, QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, ACCENT,
)
from api_client import fetch_materials, fetch_bearings, fetch_gearboxes

# ── Default payload — mirrors theme.DEFAULT_PAYLOAD ──────────────────────
_DEFAULTS: dict[str, Any] = {
    "type": "screw", "D": 0.300, "L": 10.0, "N": 60.0,
    "P": 0.300, "ang": 0.0,
    "mat": "Cement", "cap": 30.0, "surge": 1.2, "duty": 8,
    "use_multipitch": False,
    "P_in": 0.150, "P_out": 0.300, "pct_in": 10.0, "pct_out": 10.0,
    "shaft_mode": "auto", "shtype": "bar",
    "pod": 80.0, "pwall": 8.0, "sallow": 40.0,
    "support_cond": "pinfix",
    "ft": 0.008, "wa": 0.003, "temp_c": 20.0,
    "brg": "UC210", "gbx": "GB-40k",
    "bload": 0.0, "hangers": 0,
    "lam_factor": 1.0, "contAFact": False,
    "use_fill_coupling": False,
}

# ── QSS constants ─────────────────────────────────────────────────────────
_INPUT_QSS = f"""
    QDoubleSpinBox, QSpinBox, QComboBox {{
        background-color: {PANEL2};
        color: {TEXT};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 3px 6px;
        font-size: 11.5px;
        font-family: 'Consolas', monospace;
        min-height: 22px;
    }}
    QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {PRIMARY};
    }}
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
    QSpinBox::up-button, QSpinBox::down-button {{
        width: 14px;
        border: none;
        background: transparent;
    }}
    QComboBox::drop-down {{
        border: none; width: 18px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {PANEL2};
        color: {TEXT2};
        border: 1px solid {BORDER};
        selection-background-color: {PRIMARY};
    }}
    QCheckBox {{
        color: {TEXT2};
        font-size: 11.5px;
        spacing: 6px;
    }}
    QCheckBox::indicator {{
        width: 14px; height: 14px;
        border: 1px solid {BORDER};
        border-radius: 3px;
        background: {PANEL2};
    }}
    QCheckBox::indicator:checked {{
        background: {PRIMARY};
        border-color: {PRIMARY};
    }}
"""

_SECTION_HDR_QSS = f"""
    QPushButton {{
        background-color: {PANEL};
        color: {TEXT3};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 5px 10px;
        text-align: left;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.8px;
    }}
    QPushButton:hover {{ color: {TEXT2}; background-color: {PANEL2}; }}
"""

_CALC_BTN_QSS = f"""
    QPushButton {{
        background-color: {PRIMARY};
        color: white;
        border: none;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 700;
        padding: 10px 0;
    }}
    QPushButton:hover {{ background-color: #5aaaff; }}
    QPushButton:pressed {{ background-color: #3a8ee8; }}
"""

_LABEL_QSS = f"color: {TEXT3}; font-size: 10.5px;"
_UNIT_QSS  = f"color: {MUTED}; font-size: 9.5px; padding-left: 3px;"


# ── Helpers ───────────────────────────────────────────────────────────────

def _section_header(title: str, expanded: bool = True) -> QPushButton:
    """Collapsible section header button."""
    arrow = "▾" if expanded else "▸"
    btn = QPushButton(f"  {arrow}  {title.upper()}")
    btn.setFixedHeight(28)
    btn.setStyleSheet(_SECTION_HDR_QSS)
    btn.setCheckable(True)
    btn.setChecked(expanded)
    return btn


def _label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(_LABEL_QSS)
    return lbl


def _unit(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(_UNIT_QSS)
    lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
    return lbl


def _dspin(
    lo: float, hi: float, step: float, val: float, decimals: int = 3
) -> QDoubleSpinBox:
    w = QDoubleSpinBox()
    w.setRange(lo, hi)
    w.setSingleStep(step)
    w.setDecimals(decimals)
    w.setValue(val)
    w.setFixedHeight(26)
    return w


def _spin(lo: int, hi: int, val: int) -> QSpinBox:
    w = QSpinBox()
    w.setRange(lo, hi)
    w.setValue(val)
    w.setFixedHeight(26)
    return w


def _combo(options: list[tuple[str, str]], current: str) -> QComboBox:
    """options = [(display, value), ...]"""
    w = QComboBox()
    for display, value in options:
        w.addItem(display, value)
    # Select by value
    for i in range(w.count()):
        if w.itemData(i) == current:
            w.setCurrentIndex(i)
            break
    w.setFixedHeight(26)
    return w


def _row(label: str, widget: QWidget, unit: str = "") -> QWidget:
    """Label + widget + optional unit, returned as a single row QWidget."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(10, 1, 10, 1)
    layout.setSpacing(5)
    lbl = _label(label)
    lbl.setFixedWidth(86)
    layout.addWidget(lbl)
    layout.addWidget(widget)
    if unit:
        layout.addWidget(_unit(unit))
    return container


def _separator() -> QFrame:
    sep = QFrame()
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background-color: {BORDER};")
    return sep


# ── CollapsibleSection ────────────────────────────────────────────────────

class CollapsibleSection(QWidget):
    """Header + body that shows/hides on toggle."""

    def __init__(self, title: str, expanded: bool = True, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._hdr = _section_header(title, expanded)
        self._hdr.toggled.connect(self._on_toggle)
        self._layout.addWidget(self._hdr)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 2, 0, 4)
        self._body_layout.setSpacing(1)
        self._layout.addWidget(self._body)
        self._body.setVisible(expanded)

    def add_row(self, widget: QWidget) -> None:
        self._body_layout.addWidget(widget)

    def add_widget(self, widget: QWidget) -> None:
        self._body_layout.addWidget(widget)

    def _on_toggle(self, checked: bool) -> None:
        self._body.setVisible(checked)
        arrow = "▾" if checked else "▸"
        title = self._hdr.text().split("  ", 2)[-1]
        self._hdr.setText(f"  {arrow}  {title}")


# ── InputSidebarPanel ─────────────────────────────────────────────────────

class InputSidebarPanel(QWidget):
    """
    Full input sidebar for col2.

    Signal:
        calculate(payload: dict) — emitted on button click or auto-recalc.
        The payload is a flat dict matching EngineInput exactly.
    """

    calculate = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG}; {_INPUT_QSS}")
        self._materials: list[str] = []
        self._bearings:  list[str] = []
        self._gearboxes: list[str] = []
        self._loaded = False

        # Debounce timer — 400 ms after last change before auto-calculating
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(400)
        self._debounce.timeout.connect(self._emit_calculate)

        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: {BG}; }}"
            f"QScrollBar:vertical {{ background: {BG}; width: 5px; }}"
            f"QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 2px; }}"
        )

        body = QWidget()
        body.setStyleSheet(f"background-color: {BG};")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 4, 0, 8)
        body_layout.setSpacing(0)

        # ── A · Geometry ──────────────────────────────────────────────────
        sec_a = CollapsibleSection("A · Geometry", expanded=True)

        self._type = _combo(
            [("Screw (U-trough)", "screw"), ("Tubular (pipe)", "pipe")],
            _DEFAULTS["type"],
        )
        self._D    = _dspin(0.050, 1.200, 0.025, _DEFAULTS["D"])
        self._L    = _dspin(0.5,  100.0,  0.5,   _DEFAULTS["L"], decimals=1)
        self._N    = _dspin(5.0,  300.0,  1.0,   _DEFAULTS["N"], decimals=1)
        self._P    = _dspin(0.050, 2.000, 0.025, _DEFAULTS["P"])
        self._ang  = _dspin(-20.0, 45.0,  1.0,   _DEFAULTS["ang"], decimals=1)

        sec_a.add_row(_row("Type",      self._type))
        sec_a.add_row(_row("Diameter",  self._D,   "m"))
        sec_a.add_row(_row("Length",    self._L,   "m"))
        sec_a.add_row(_row("Speed",     self._N,   "RPM"))
        sec_a.add_row(_row("Pitch",     self._P,   "m"))
        sec_a.add_row(_row("Angle",     self._ang, "°"))
        body_layout.addWidget(sec_a)

        # ── B · Capacity ──────────────────────────────────────────────────
        sec_b = CollapsibleSection("B · Capacity", expanded=True)

        self._mat   = QComboBox()
        self._mat.setFixedHeight(26)
        self._mat.addItem(_DEFAULTS["mat"])    # populated properly in load_combos()
        self._cap   = _dspin(0.01, 5000.0, 1.0,  _DEFAULTS["cap"], decimals=1)
        self._surge = _dspin(1.00,    2.0, 0.05, _DEFAULTS["surge"])
        self._duty  = _spin(1, 24, _DEFAULTS["duty"])

        sec_b.add_row(_row("Material",  self._mat))
        sec_b.add_row(_row("Capacity",  self._cap,   "t/h"))
        sec_b.add_row(_row("Surge",     self._surge))
        sec_b.add_row(_row("Duty",      self._duty,  "h/day"))
        body_layout.addWidget(sec_b)

        # ── C · Multi-pitch (collapsed) ───────────────────────────────────
        sec_c = CollapsibleSection("C · Multi-pitch", expanded=False)

        self._use_mp  = QCheckBox("Enable multi-pitch geometry")
        self._P_in    = _dspin(0.050, 2.000, 0.025, _DEFAULTS["P_in"])
        self._P_out   = _dspin(0.050, 2.000, 0.025, _DEFAULTS["P_out"])
        self._pct_in  = _dspin(5.0, 30.0, 1.0, _DEFAULTS["pct_in"],  decimals=1)
        self._pct_out = _dspin(5.0, 30.0, 1.0, _DEFAULTS["pct_out"], decimals=1)

        self._mp_body = QWidget()
        mb = QVBoxLayout(self._mp_body)
        mb.setContentsMargins(0, 0, 0, 0)
        mb.setSpacing(1)
        mb.addWidget(_row("Inlet pitch",  self._P_in,   "m"))
        mb.addWidget(_row("Outlet pitch", self._P_out,  "m"))
        mb.addWidget(_row("Inlet zone",   self._pct_in, "%"))
        mb.addWidget(_row("Outlet zone",  self._pct_out, "%"))
        self._mp_body.setVisible(False)

        sec_c.add_widget(
            self._padded(self._use_mp, left=10, top=4, bottom=4)
        )
        sec_c.add_widget(self._mp_body)
        body_layout.addWidget(sec_c)

        # ── D · Shaft ─────────────────────────────────────────────────────
        sec_d = CollapsibleSection("D · Shaft", expanded=True)

        self._shaft_mode = _combo(
            [("Auto (VECTRIX™)", "auto"), ("Manual override", "manual")],
            _DEFAULTS["shaft_mode"],
        )
        self._sallow = _dspin(20.0, 160.0, 5.0, _DEFAULTS["sallow"], decimals=1)
        self._sup    = _combo(
            [("Pin-fix (default)", "pinfix"),
             ("Both pinned", "pinned"),
             ("Both fixed", "fixed")],
            _DEFAULTS["support_cond"],
        )

        # Manual-only fields
        self._shtype = _combo(
            [("Solid bar", "bar"), ("Hollow pipe", "pipe")],
            _DEFAULTS["shtype"],
        )
        self._pod   = _dspin(30.0, 400.0, 5.0, _DEFAULTS["pod"], decimals=1)
        self._pwall = _dspin(3.0,  40.0,  1.0, _DEFAULTS["pwall"], decimals=1)

        self._manual_body = QWidget()
        mdb = QVBoxLayout(self._manual_body)
        mdb.setContentsMargins(0, 0, 0, 0)
        mdb.setSpacing(1)
        mdb.addWidget(_row("Shaft type", self._shtype))
        mdb.addWidget(_row("OD",         self._pod,   "mm"))
        mdb.addWidget(_row("Wall",       self._pwall, "mm"))
        self._manual_body.setVisible(False)

        sec_d.add_row(_row("Mode",       self._shaft_mode))
        sec_d.add_row(_row("τ allow",    self._sallow, "MPa"))
        sec_d.add_row(_row("Supports",   self._sup))
        sec_d.add_widget(self._manual_body)
        body_layout.addWidget(sec_d)

        # ── E · Flight & Wear ─────────────────────────────────────────────
        sec_e = CollapsibleSection("E · Flight & Wear", expanded=True)

        self._ft     = _dspin(0.002, 0.050, 0.001, _DEFAULTS["ft"])
        self._wa     = _dspin(0.001, 0.020, 0.001, _DEFAULTS["wa"])
        self._temp_c = _dspin(-20.0, 800.0, 5.0,   _DEFAULTS["temp_c"], decimals=1)

        sec_e.add_row(_row("Flight t",   self._ft,     "m"))
        sec_e.add_row(_row("Wear allow", self._wa,     "m"))
        sec_e.add_row(_row("Temp",       self._temp_c, "°C"))
        body_layout.addWidget(sec_e)

        # ── F · Drive (collapsed) ─────────────────────────────────────────
        sec_f = CollapsibleSection("F · Drive", expanded=False)

        self._brg     = QComboBox()
        self._brg.setFixedHeight(26)
        self._brg.addItem(_DEFAULTS["brg"])
        self._gbx     = QComboBox()
        self._gbx.setFixedHeight(26)
        self._gbx.addItem(_DEFAULTS["gbx"])
        self._bload   = _dspin(0.0, 500.0, 0.5, _DEFAULTS["bload"], decimals=2)
        self._hangers = _spin(0, 20, _DEFAULTS["hangers"])

        self._bload.setSpecialValueText("Auto")
        self._hangers.setSpecialValueText("Auto")

        sec_f.add_row(_row("Bearing",   self._brg))
        sec_f.add_row(_row("Gearbox",   self._gbx))
        sec_f.add_row(_row("Brg load",  self._bload,   "kN"))
        sec_f.add_row(_row("Hangers",   self._hangers))
        body_layout.addWidget(sec_f)

        # ── G · Standards (collapsed) ─────────────────────────────────────
        sec_g = CollapsibleSection("G · Standards", expanded=False)

        self._lam = _dspin(0.80, 2.00, 0.01, _DEFAULTS["lam_factor"])
        self._std_combo = _combo(
            [("CEMA 7th Ed.", "1.00"),
             ("DIN 15262",   "1.01"),
             ("KWS Eng.",    "1.03")],
            "1.00",
        )
        self._cont_a  = QCheckBox("Continuous aFact (exponential)")
        self._fill_cp = QCheckBox("Fill-coupling correction")

        sec_g.add_row(_row("λ factor",  self._lam))
        sec_g.add_row(_row("Standard",  self._std_combo))
        sec_g.add_widget(
            self._padded(self._cont_a, left=10, top=3)
        )
        sec_g.add_widget(
            self._padded(self._fill_cp, left=10, top=3, bottom=4)
        )
        body_layout.addWidget(sec_g)

        body_layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)

        # ── Calculate button (sticky bottom) ─────────────────────────────
        outer.addWidget(_separator())
        calc_btn = QPushButton("▶  Calculate")
        calc_btn.setFixedHeight(42)
        calc_btn.setStyleSheet(_CALC_BTN_QSS)
        calc_btn.clicked.connect(self._emit_calculate)
        outer.addWidget(calc_btn)

        # ── Wire change signals ───────────────────────────────────────────
        self._wire_signals()

    # ── Signal wiring ─────────────────────────────────────────────────────

    def _wire_signals(self) -> None:
        """Connect all widget changes to the debounce timer."""
        spin_widgets = [
            self._D, self._L, self._N, self._P, self._ang,
            self._cap, self._surge, self._P_in, self._P_out,
            self._pct_in, self._pct_out,
            self._sallow, self._pod, self._pwall,
            self._ft, self._wa, self._temp_c,
            self._bload, self._lam,
        ]
        for w in spin_widgets:
            w.valueChanged.connect(self._debounce.start)

        int_widgets = [self._duty, self._hangers]
        for w in int_widgets:
            w.valueChanged.connect(self._debounce.start)

        combo_widgets = [
            self._type, self._mat, self._shaft_mode,
            self._shtype, self._sup, self._brg,
            self._gbx, self._std_combo,
        ]
        for w in combo_widgets:
            w.currentIndexChanged.connect(self._debounce.start)

        check_widgets = [self._use_mp, self._cont_a, self._fill_cp]
        for w in check_widgets:
            w.stateChanged.connect(self._debounce.start)

        # Conditional visibility
        self._shaft_mode.currentIndexChanged.connect(self._on_shaft_mode_changed)
        self._use_mp.stateChanged.connect(self._on_multipitch_toggled)
        self._std_combo.currentIndexChanged.connect(self._on_std_changed)

    # ── Conditional visibility ────────────────────────────────────────────

    def _on_shaft_mode_changed(self) -> None:
        manual = self._shaft_mode.currentData() == "manual"
        self._manual_body.setVisible(manual)

    def _on_multipitch_toggled(self, state: int) -> None:
        self._mp_body.setVisible(state == Qt.CheckState.Checked.value)

    def _on_std_changed(self) -> None:
        try:
            val = float(self._std_combo.currentData())
            self._lam.setValue(val)
        except (TypeError, ValueError):
            pass

    # ── Public API ────────────────────────────────────────────────────────

    def load_combos(self) -> None:
        """
        Populate material / bearing / gearbox ComboBoxes from backend.
        Called once by ShellWindow after health check confirms backend is up.
        """
        if self._loaded:
            return
        self._loaded = True

        result = fetch_materials()
        if not result.get("error"):
            items = result.get("items", [])
            current = self._mat.currentText()
            self._mat.clear()
            for m in items:
                self._mat.addItem(m.get("name", ""), m.get("name", ""))
            # restore selection
            idx = self._mat.findText(current)
            if idx >= 0:
                self._mat.setCurrentIndex(idx)

        # Bearing and gearbox combos — routes confirmed in routes.py
        # (GET /api/v1/bearings, GET /api/v1/gearboxes) since the
        # Auto-Optimiser's Phase 3 sweep already relies on these same
        # endpoints via fetch_bearings()/fetch_gearboxes().
        brg_result = fetch_bearings()
        if not brg_result.get("error"):
            items = brg_result.get("items", [])
            current = self._brg.currentText()
            self._brg.clear()
            for b in items:
                self._brg.addItem(b.get("name", ""), b.get("name", ""))
            idx = self._brg.findText(current)
            if idx >= 0:
                self._brg.setCurrentIndex(idx)

        gbx_result = fetch_gearboxes()
        if not gbx_result.get("error"):
            items = gbx_result.get("items", [])
            current = self._gbx.currentText()
            self._gbx.clear()
            for g in items:
                self._gbx.addItem(g.get("model", ""), g.get("model", ""))
            idx = self._gbx.findText(current)
            if idx >= 0:
                self._gbx.setCurrentIndex(idx)

    def set_payload(self, payload: dict) -> None:
        """Programmatically set all fields from a saved payload dict."""
        def _set_dspin(w: QDoubleSpinBox, key: str) -> None:
            if key in payload:
                w.blockSignals(True)
                w.setValue(float(payload[key]))
                w.blockSignals(False)

        def _set_spin(w: QSpinBox, key: str) -> None:
            if key in payload:
                w.blockSignals(True)
                w.setValue(int(payload[key]))
                w.blockSignals(False)

        def _set_combo(w: QComboBox, key: str) -> None:
            val = payload.get(key)
            if val is not None:
                for i in range(w.count()):
                    if w.itemData(i) == str(val):
                        w.blockSignals(True)
                        w.setCurrentIndex(i)
                        w.blockSignals(False)
                        return
                # Try text match
                idx = w.findText(str(val))
                if idx >= 0:
                    w.blockSignals(True)
                    w.setCurrentIndex(idx)
                    w.blockSignals(False)

        _set_combo(self._type,        "type")
        _set_dspin(self._D,           "D")
        _set_dspin(self._L,           "L")
        _set_dspin(self._N,           "N")
        _set_dspin(self._P,           "P")
        _set_dspin(self._ang,         "ang")
        _set_combo(self._mat,         "mat")
        _set_dspin(self._cap,         "cap")
        _set_dspin(self._surge,       "surge")
        _set_spin (self._duty,        "duty")
        _set_dspin(self._P_in,        "P_in")
        _set_dspin(self._P_out,       "P_out")
        _set_dspin(self._pct_in,      "pct_in")
        _set_dspin(self._pct_out,     "pct_out")
        _set_combo(self._shaft_mode,  "shaft_mode")
        _set_combo(self._shtype,      "shtype")
        _set_dspin(self._pod,         "pod")
        _set_dspin(self._pwall,       "pwall")
        _set_dspin(self._sallow,      "sallow")
        _set_combo(self._sup,         "support_cond")
        _set_dspin(self._ft,          "ft")
        _set_dspin(self._wa,          "wa")
        _set_dspin(self._temp_c,      "temp_c")
        _set_combo(self._brg,         "brg")
        _set_combo(self._gbx,         "gbx")
        _set_dspin(self._bload,       "bload")
        _set_spin (self._hangers,     "hangers")
        _set_dspin(self._lam,         "lam_factor")

        if "use_multipitch" in payload:
            self._use_mp.setChecked(bool(payload["use_multipitch"]))
        if "contAFact" in payload:
            self._cont_a.setChecked(bool(payload["contAFact"]))
        if "use_fill_coupling" in payload:
            self._fill_cp.setChecked(bool(payload["use_fill_coupling"]))

    def get_payload(self) -> dict:
        """
        Read all widgets and return a flat dict matching EngineInput.
        This is what gets posted to /api/calculate.
        """
        bload_raw = self._bload.value()
        han_raw   = self._hangers.value()

        payload: dict[str, Any] = {
            # A
            "type":             self._type.currentData(),
            "D":                self._D.value(),
            "L":                self._L.value(),
            "N":                self._N.value(),
            "P":                self._P.value(),
            "ang":              self._ang.value(),
            # B
            "mat":              self._mat.currentText(),
            "cap":              self._cap.value(),
            "surge":            self._surge.value(),
            "duty":             self._duty.value(),
            # C
            "use_multipitch":   self._use_mp.isChecked(),
            "P_in":             self._P_in.value(),
            "P_out":            self._P_out.value(),
            "pct_in":           self._pct_in.value(),
            "pct_out":          self._pct_out.value(),
            # D
            "shaft_mode":       self._shaft_mode.currentData(),
            "shtype":           self._shtype.currentData(),
            "pod":              self._pod.value(),
            "pwall":            self._pwall.value(),
            "sallow":           self._sallow.value(),
            "support_cond":     self._sup.currentData(),
            # E
            "ft":               self._ft.value(),
            "wa":               self._wa.value(),
            "temp_c":           self._temp_c.value(),
            # F
            "brg":              self._brg.currentText(),
            "gbx":              self._gbx.currentText(),
            "bload":            bload_raw if bload_raw > 0 else None,
            "hangers":          han_raw   if han_raw   > 0 else None,
            # G
            "lam_factor":       self._lam.value(),
            "contAFact":        self._cont_a.isChecked(),
            "use_fill_coupling": self._fill_cp.isChecked(),
        }
        return payload

    # ── Internal ──────────────────────────────────────────────────────────

    def _emit_calculate(self) -> None:
        self._debounce.stop()
        self.calculate.emit(self.get_payload())

    @staticmethod
    def _padded(
        widget: QWidget,
        left: int = 0, top: int = 0,
        right: int = 0, bottom: int = 0,
    ) -> QWidget:
        """Wrap a widget in a container with custom margins."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(left, top, right, bottom)
        layout.addWidget(widget)
        return container