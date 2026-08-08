"""
components/pages/status_panel.py — VECTRIX™ Design Health / KPI grid (col4)
═══════════════════════════════════════════════════════════════════════════
Faithful port of DesignHealth from CalcPage.tsx — this is the exact
"col4 KpiGrid" content that was unresolved at Step 6; the React source
confirmed the 11-check grid below is what belongs here, so this is a
direct translation, not a redesign.

Checks (order matches CalcPage.tsx exactly):
    1.  Capacity          R.cap.ok
    2.  Shaft Stress       R.tor.shOk           (req uses payload.sallow)
    3.  Gearbox Torque     R.gbx_r.tOk
    4.  Bearing L10        R.brg_r.ok
    5.  Vibration Risk     vibration_risk < 3
    6.  Energy kWh/t       eff.kWh_t < 1
    7.  Fill φ (actual)    15% ≤ fill ≤ 45%
    8.  Utilisation        70% ≤ cap_util ≤ 100%
    9.  Shaft Deflection   R.deflection_ok
    10. Motor              motor >= motor_rated
    11. Load Class         always "ok" (informational, CEMA class display)

Layout: 6-column grid (2 rows for 11 tiles — 6 + 5), header badge shows
"✅ Design OK" or "⛔ N Critical" exactly as in the React version.

set_data(result, payload) needs payload only for `sallow` — the one
field DesignHealth reads from inputs rather than the engine result
(inp.sallow appears in the Shaft Stress requirement text). Everything
else comes from result alone.
"""

from __future__ import annotations

from typing import Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QScrollArea, QPushButton,
)
from PySide6.QtCore import Qt

from core.theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, ACCENT,
)


def _f(val: Any, dp: int = 2, fallback: str = "—") -> str:
    try:
        return f"{float(val):.{dp}f}"
    except (TypeError, ValueError):
        return fallback


def _fi(val: Any, fallback: str = "—") -> str:
    try:
        return f"{int(round(float(val))):,}"
    except (TypeError, ValueError):
        return fallback


class _HealthTile(QFrame):
    """
    Single design-health tile: label, colour-coded value, requirement, and
    an expandable governing-equation panel.

    Matches the reference design health card: no nested borders (one border
    on the tile, scoped by objectName so it does not cascade to the labels
    inside), and a SHOW/HIDE FORMULA toggle that reveals the governing
    equation with the actual numbers substituted — so the card shows not
    just the value and its pass/fail state, but the engineering basis for
    it. The formula stays collapsed by default to keep the column compact.
    """

    #: Scoped by objectName, NOT by type. A `QFrame{...}` selector also
    #: matches every QLabel inside this tile, because QLabel inherits
    #: QFrame — which draws a border around each label and produces the
    #: "box in box" look. `#healthTile` matches this widget alone.
    _OBJ = "healthTile"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName(self._OBJ)
        self._apply_border(BORDER)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(3)

        self._label_lbl = QLabel("")
        self._label_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 16px; font-weight: 700; "
            f"letter-spacing: .5px; text-transform: uppercase; border: none;"
        )
        self._label_lbl.setWordWrap(True)
        lay.addWidget(self._label_lbl)

        self._value_lbl = QLabel("")
        self._value_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 20px; font-weight: 800; "
            f"font-family: 'Consolas', monospace; border: none;"
        )
        lay.addWidget(self._value_lbl)

        self._req_lbl = QLabel("")
        self._req_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 16px; border: none;"
        )
        self._req_lbl.setWordWrap(True)
        lay.addWidget(self._req_lbl)

        # Formula toggle — hidden until a formula is supplied.
        self._toggle = QPushButton("▸ SHOW FORMULA")
        self._toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle.setStyleSheet(
            f"QPushButton {{ color: {ACCENT}; font-size: 16px; "
            f"font-weight: 700; border: none; background: transparent; "
            f"text-align: left; padding: 2px 0; }} "
            f"QPushButton:hover {{ color: {TEXT}; }}"
        )
        self._toggle.clicked.connect(self._toggle_formula)
        lay.addWidget(self._toggle)

        self._formula_lbl = QLabel("")
        self._formula_lbl.setWordWrap(True)
        self._formula_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._formula_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 16px; "
            f"font-family: 'Consolas', monospace; "
            f"background: rgba(0,0,0,.30); border-radius: 5px; "
            f"padding: 7px 9px; border: none;"
        )
        self._formula_lbl.setVisible(False)
        lay.addWidget(self._formula_lbl)

    def _apply_border(self, colour: str) -> None:
        self.setStyleSheet(
            f"#{self._OBJ} {{ background-color: rgba(0,0,0,.25); "
            f"border-radius: 7px; border: 1px solid {colour}; }}"
        )

    def _toggle_formula(self) -> None:
        shown = not self._formula_lbl.isVisible()
        self._formula_lbl.setVisible(shown)
        self._toggle.setText("▾ HIDE FORMULA" if shown else "▸ SHOW FORMULA")

    def set_check(
        self,
        label: str,
        value: str,
        req: str,
        ok: Optional[bool],
        formula: str = "",
    ) -> None:
        self._label_lbl.setText(label)
        self._value_lbl.setText(value)
        self._req_lbl.setText(req)

        color = SUCCESS if ok else (DANGER if ok is False else TEXT)
        self._value_lbl.setStyleSheet(
            f"color: {color}; font-size: 20px; font-weight: 800; "
            f"font-family: 'Consolas', monospace; border: none;"
        )
        # Border tint follows status; neutral grey for informational tiles.
        # The 44 alpha suffix keeps it subtle, matching the reference.
        self._apply_border(f"{color}66" if ok is not None else BORDER)

        has_formula = bool(formula)
        self._toggle.setVisible(has_formula)
        if has_formula:
            self._formula_lbl.setText(formula)
        else:
            self._formula_lbl.setVisible(False)
            self._toggle.setText("▸ SHOW FORMULA")


class StatusPanel(QWidget):
    """
    col4 content — Design Health grid.

    Public:
        set_data(result: dict, payload: dict) — payload only used for
        the Shaft Stress tile's requirement text (inp.sallow).
    """

    _N_COLS = 1   # single column — full-width tiles so the governing-equation
                  # panel has room to render. The reference design health
                  # card is single-column for exactly this reason; two
                  # narrow columns cannot hold a substituted formula.
                  # far better than 6 columns squeezed into that width;
                  # content and order are identical to CalcPage.tsx,
                  # only the grid geometry is adapted to the panel width

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header — icon + title + PASS/FAIL badge
        header = QFrame()
        header.setStyleSheet(f"background-color: {PANEL};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 8, 12, 8)
        hl.setSpacing(6)

        icon = QLabel("🏥")
        icon.setStyleSheet("font-size: 17px;")
        hl.addWidget(icon)

        title = QLabel("DESIGN HEALTH")
        title.setStyleSheet(
            f"color: {TEXT3}; font-size: 16px; font-weight: 700; letter-spacing: 1px;"
        )
        hl.addWidget(title)
        hl.addStretch()

        self._status_badge = QLabel("—")
        self._status_badge.setStyleSheet(
            f"QWidget {{" f"color: {TEXT3}; font-size: 16px; font-weight: 700; "
            f"background: rgba(0,0,0,.3); border-radius: 10px; "
            f"padding: 3px 10px; border: 1px solid {BORDER};" f"}}"
        )
        hl.addWidget(self._status_badge)

        outer.addWidget(header)

        # Scrollable tile grid
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
        body_layout.setContentsMargins(10, 8, 10, 10)
        body_layout.setSpacing(0)

        grid_widget = QWidget()
        self._grid = QGridLayout(grid_widget)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(6)
        for c in range(self._N_COLS):
            self._grid.setColumnStretch(c, 1)

        self._tiles: list[_HealthTile] = []
        for i in range(11):
            tile = _HealthTile()
            self._grid.addWidget(tile, i // self._N_COLS, i % self._N_COLS)
            self._tiles.append(tile)

        body_layout.addWidget(grid_widget)
        body_layout.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll)

    def set_data(self, result: dict, payload: Optional[dict] = None) -> None:
        if not result or result.get("error"):
            return
        payload = payload or {}

        cap  = result.get("cap", {})
        tor  = result.get("tor", {})
        gbx  = result.get("gbx_r", {})
        brg  = result.get("brg_r", {})
        eff  = result.get("eff", {})
        pwr  = result.get("pwr", {})
        mat  = result.get("mat", {})

        vib_risk = result.get("vibration_risk", 0.0) or 0.0
        vri_label = result.get("vri_label", "—")

        fill_frac = cap.get("fill_actual", cap.get("fill", 0.30)) or 0.30
        fill_pct = fill_frac * 100
        cap_util = eff.get("cap_util", 0.0) or 0.0

        deflection = result.get("deflection", 0.0) or 0.0
        defl_limit = result.get("defl_limit", 0.01) or 0.01
        deflection_ok = result.get("deflection_ok")

        sallow = payload.get("sallow", 40)
        l10_target = brg.get("L10_target", 20000)
        tn_derated = gbx.get("Tn_derated") or gbx.get("Tn") or 0

        # Values feeding the governing equations shown in the formula panels.
        D = payload.get("D", 0) or 0
        N = payload.get("N", 0) or 0
        P = payload.get("P", D) or D
        rho = mat.get("rho", 0) or 0
        Qt = cap.get("Qt", 0) or 0
        tau = tor.get("tau", 0) or 0
        Ts = tor.get("Ts", 0) or 0
        Tn = tn_derated
        L10 = brg.get("L10", 0) or 0
        motor = pwr.get("motor", 0) or 0
        motor_rated = pwr.get("motor_rated", 0) or 0
        kwh_t = eff.get("kWh_t", 0) or 0

        # Each entry: (label, value, req, ok, formula). The formula is the
        # governing equation with the actual numbers substituted, so a
        # reviewer can trace the value to its basis — matching the reference
        # design health card's SHOW FORMULA panels.
        checks = [
            ("Capacity",
             f"{_f(Qt, 1)} t/h",
             f"{cap.get('req', payload.get('cap', 0))} t/h req",
             cap.get("ok"),
             f"Q = (π/4)·D²·P·N·φ·ρ·60·η_L\n"
             f"D = {D:.3f} m   P = {P:.3f} m   N = {N:.0f} rpm\n"
             f"φ = {fill_pct:.1f}%   ρ = {rho:.2f} t/m³\n"
             f"→ Q = {_f(Qt, 1)} t/h   [CEMA §4]"),

            ("Shaft Stress",
             f"{_f(tau, 1)} MPa",
             f"≤{sallow} MPa",
             tor.get("shOk"),
             f"τ = 16·T / (π·d³)   (solid) or annular for pipe\n"
             f"T = {_fi(Ts)} Nm\n"
             f"→ τ = {_f(tau, 1)} MPa   (allow ≤ {sallow} MPa)"),

            ("Gearbox Torque",
             f"{_fi(Ts)} Nm",
             f"≤{_fi(tn_derated)} Nm",
             gbx.get("tOk"),
             f"T_shaft = 9550·P_shaft / N\n"
             f"required = {_fi(Ts)} Nm\n"
             f"gearbox rated (derated) = {_fi(Tn)} Nm"),

            ("Bearing L10",
             f"{_fi(L10)} h",
             f"≥{_fi(l10_target)} h",
             brg.get("ok"),
             f"L10 = (C/P)^p · 10⁶ / (60·N)\n"
             f"→ L10 = {_fi(L10)} h   (target ≥ {_fi(l10_target)} h)"),

            ("Vibration Risk",
             str(vri_label),
             "Low target",
             vib_risk < 3,
             f"VRI from N vs critical speed & fill\n"
             f"index = {vib_risk:.2f}   → {vri_label}"),

            ("Energy kWh/t",
             _f(kwh_t, 3),
             "<1.0 optimal",
             (eff.get("kWh_t") or 9) < 1,
             f"E = P_total / Q\n"
             f"→ {_f(kwh_t, 3)} kWh/t   (optimal < 1.0)"),

            ("Fill φ (act)",
             f"{_f(fill_pct, 1)}%",
             "15–45% target",
             15 <= fill_pct <= 45,
             f"φ_act = φ_max·f(θ)·feed_ratio  (CEMA)\n"
             f"→ {_f(fill_pct, 1)}%   (target 15–45%)"),

            ("Utilisation",
             f"{_f(cap_util, 0)}%",
             "70–100% target",
             70 <= cap_util <= 100,
             f"util = Q_required / Q_capacity\n"
             f"→ {_f(cap_util, 0)}%   (target 70–100%)"),

            ("Shaft Defl.",
             f"{_f(deflection * 1000, 2)} mm",
             f"≤{_f(defl_limit * 1000, 2)} mm",
             deflection_ok,
             f"δ = 5·w·L⁴ / (384·E·I)   (UDL, span)\n"
             f"→ δ = {_f(deflection * 1000, 2)} mm  "
             f"(limit {_f(defl_limit * 1000, 2)} mm)"),

            ("Motor",
             f"{motor} kW",
             f"{_f(motor_rated, 1)} kW rated",
             (motor or 0) >= (motor_rated or 0),
             f"P_motor = next standard ≥ P_shaft·SF\n"
             f"required {_f(motor_rated, 1)} kW → selected {motor} kW"),

            ("Load Class",
             f"Class {mat.get('cls', '—')}",
             "",
             True,
             ""),
        ]

        n_fail = sum(1 for _, _, _, ok, _ in checks if ok is False)
        if n_fail > 0:
            self._status_badge.setText(f"⛔ {n_fail} Critical")
            self._status_badge.setStyleSheet(
            f"QWidget {{" f"color: {DANGER}; font-size: 16px; font-weight: 700; "
                f"background: rgba(0,0,0,.3); border-radius: 10px; "
                f"padding: 3px 10px; border: 1px solid {DANGER};" f"}}"
        )
        else:
            self._status_badge.setText("✅ Design OK")
            self._status_badge.setStyleSheet(
            f"QWidget {{" f"color: {SUCCESS}; font-size: 16px; font-weight: 700; "
                f"background: rgba(0,0,0,.3); border-radius: 10px; "
                f"padding: 3px 10px; border: 1px solid {SUCCESS};" f"}}"
        )

        for tile, (label, value, req, ok, formula) in zip(self._tiles, checks):
            tile.set_check(label, value, req, ok, formula)