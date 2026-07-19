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
    QScrollArea,
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
    Single check tile — label (top), value (bold, colour-coded), req
    (bottom, muted). Matches the CalcPage.tsx grid tile exactly:
    background rgba(0,0,0,.25), 1px border tinted to the status colour.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: rgba(0,0,0,.25); border-radius: 7px;"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(9, 7, 9, 7)
        lay.setSpacing(2)

        self._label_lbl = QLabel("")
        self._label_lbl.setStyleSheet(
            f"color: {TEXT3}; font-size: 9px; font-weight: 700; "
            f"letter-spacing: .5px; text-transform: uppercase;"
        )
        self._label_lbl.setWordWrap(True)
        lay.addWidget(self._label_lbl)

        self._value_lbl = QLabel("")
        self._value_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 12px; font-weight: 800; "
            f"font-family: 'Consolas', monospace;"
        )
        lay.addWidget(self._value_lbl)

        self._req_lbl = QLabel("")
        self._req_lbl.setStyleSheet(f"color: {MUTED}; font-size: 8.5px;")
        self._req_lbl.setWordWrap(True)
        lay.addWidget(self._req_lbl)

    def set_check(self, label: str, value: str, req: str, ok: Optional[bool]) -> None:
        self._label_lbl.setText(label)
        self._value_lbl.setText(value)
        self._req_lbl.setText(req)

        color = SUCCESS if ok else (DANGER if ok is False else TEXT3)
        self._value_lbl.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 800; "
            f"font-family: 'Consolas', monospace;"
        )
        border_color = color if ok is not None else BORDER
        self.setStyleSheet(
            f"background-color: rgba(0,0,0,.25); border-radius: 7px; "
            f"border: 1px solid {border_color}44;"
        )


class StatusPanel(QWidget):
    """
    col4 content — Design Health grid.

    Public:
        set_data(result: dict, payload: dict) — payload only used for
        the Shaft Stress tile's requirement text (inp.sallow).
    """

    _N_COLS = 2   # col4 is narrow (260px) — 2 columns × 6 rows reads
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
        icon.setStyleSheet("font-size: 13px;")
        hl.addWidget(icon)

        title = QLabel("DESIGN HEALTH")
        title.setStyleSheet(
            f"color: {TEXT3}; font-size: 9.5px; font-weight: 700; letter-spacing: 1px;"
        )
        hl.addWidget(title)
        hl.addStretch()

        self._status_badge = QLabel("—")
        self._status_badge.setStyleSheet(
            f"color: {TEXT3}; font-size: 9.5px; font-weight: 700; "
            f"background: rgba(0,0,0,.3); border-radius: 10px; "
            f"padding: 3px 10px; border: 1px solid {BORDER};"
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

        checks = [
            ("Capacity",
             f"{_f(cap.get('Qt'), 1)} t/h",
             f"{cap.get('req', payload.get('cap', 0))} t/h req",
             cap.get("ok")),

            ("Shaft Stress",
             f"{_f(tor.get('tau'), 1)} MPa",
             f"≤{sallow} MPa",
             tor.get("shOk")),

            ("Gearbox Torque",
             f"{_fi(tor.get('Ts'))} Nm",
             f"≤{_fi(tn_derated)} Nm",
             gbx.get("tOk")),

            ("Bearing L10",
             f"{_fi(brg.get('L10'))} h",
             f"≥{_fi(l10_target)} h",
             brg.get("ok")),

            ("Vibration Risk",
             str(vri_label),
             "Low target",
             vib_risk < 3),

            ("Energy kWh/t",
             _f(eff.get("kWh_t", 0.0), 3),
             "<1.0 optimal",
             (eff.get("kWh_t") or 9) < 1),

            ("Fill φ (act)",
             f"{_f(fill_pct, 1)}%",
             "15–45% target",
             15 <= fill_pct <= 45),

            ("Utilisation",
             f"{_f(cap_util, 0)}%",
             "70–100% target",
             70 <= cap_util <= 100),

            ("Shaft Defl.",
             f"{_f(deflection * 1000, 2)} mm",
             f"≤{_f(defl_limit * 1000, 2)} mm",
             deflection_ok),

            ("Motor",
             f"{pwr.get('motor', '—')} kW",
             f"{_f(pwr.get('motor_rated', 0), 1)} kW rated",
             (pwr.get("motor") or 0) >= (pwr.get("motor_rated") or 0)),

            ("Load Class",
             f"Class {mat.get('cls', '—')}",
             "",
             True),
        ]

        n_fail = sum(1 for _, _, _, ok in checks if ok is False)
        if n_fail > 0:
            self._status_badge.setText(f"⛔ {n_fail} Critical")
            self._status_badge.setStyleSheet(
                f"color: {DANGER}; font-size: 9.5px; font-weight: 700; "
                f"background: rgba(0,0,0,.3); border-radius: 10px; "
                f"padding: 3px 10px; border: 1px solid {DANGER};"
            )
        else:
            self._status_badge.setText("✅ Design OK")
            self._status_badge.setStyleSheet(
                f"color: {SUCCESS}; font-size: 9.5px; font-weight: 700; "
                f"background: rgba(0,0,0,.3); border-radius: 10px; "
                f"padding: 3px 10px; border: 1px solid {SUCCESS};"
            )

        for tile, (label, value, req, ok) in zip(self._tiles, checks):
            tile.set_check(label, value, req, ok)