"""
components/pages/calc_basis_panel.py — VECTRIX™ Calculation Basis + Sweep
═══════════════════════════════════════════════════════════════════════════
Faithful port of the "Calculation Basis & Method Traceability" panel
from CalcPage.tsx, which contains:
    - Static method-traceability text (CEMA §3/§4, ASME B106.1M, ISO 281,
      Archard wear model)
    - PowerBreakdown bar chart — NOT duplicated here; PowerCard's
      _PowerBar in results_panel.py already covers this exact content
      (Pe/Pm/Pi stacked bar), so it isn't rebuilt a second time.
    - ParamSweep — genuinely new, ported below as ParamSweepWidget.

ParamSweepWidget sweeps one dimension (Speed / Diameter / Length) across
10 points via repeated /api/v1/calculate calls, plotting capacity (t/h)
and power (kW) against the swept variable. Matches the React version's
sweep point sets and override logic exactly:
    speed  → N ∈ [10,20,30,40,50,60,80,100,120,150] RPM
    diam   → D and P both set to the same value ∈ [0.1..0.6] m
             (x-axis shown in mm — uniform pitch = diameter)
    length → L ∈ [3,5,8,10,12,15,18,20,25,30] m

Runs on a background QThread (10 sequential HTTP calls) so the UI
doesn't block, consistent with AxialProfilePanel and
AutoOptimizerPanel's worker pattern.
"""

from __future__ import annotations

from typing import Optional, Callable, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PySide6.QtCore import Qt, QThread, QObject, Signal
import pyqtgraph as pg

from theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, ACCENT, TEAL,
)
from api_client import fetch_design

pg.setConfigOptions(antialias=True, background=PANEL2, foreground=TEXT3)


_SWEEP_DEFS = {
    "speed":  {"icon": "⚡", "label": "Speed",  "x_label": "RPM",
               "values": [10, 20, 30, 40, 50, 60, 80, 100, 120, 150]},
    "diam":   {"icon": "⭕", "label": "Diam",   "x_label": "Ø mm",
               "values": [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6]},
    "length": {"icon": "↔️", "label": "Length", "x_label": "L (m)",
               "values": [3, 5, 8, 10, 12, 15, 18, 20, 25, 30]},
}


# ── Background sweep worker ────────────────────────────────────────────────

class _SweepWorker(QObject):
    finished = Signal(list)   # list of {"x": float, "cap": float, "pwr": float}

    def __init__(self, sweep_type: str, base_payload: dict):
        super().__init__()
        self._sweep_type = sweep_type
        self._base = base_payload

    def run(self) -> None:
        cfg = _SWEEP_DEFS[self._sweep_type]
        points: list[dict] = []

        for v in cfg["values"]:
            if self._sweep_type == "diam":
                x = round(v * 1000)
                override = {"D": v, "P": v}
            elif self._sweep_type == "speed":
                x = v
                override = {"N": v}
            else:  # length
                x = v
                override = {"L": v}

            payload = {**self._base, **override}
            r = fetch_design(payload)
            if r.get("error"):
                continue
            points.append({
                "x": x,
                "cap": round((r.get("cap", {}) or {}).get("Qt", 0), 1),
                "pwr": round((r.get("pwr", {}) or {}).get("Pt", 0), 2),
            })

        self.finished.emit(points)


# ── ParamSweepWidget ────────────────────────────────────────────────────────

class ParamSweepWidget(QWidget):
    """
    Constructor:
        get_base_payload  Callable[[], dict] — current sidebar state,
                          same pattern as AutoOptimizerPanel.
    """

    def __init__(
        self,
        get_base_payload: Callable[[], dict],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._get_base_payload = get_base_payload
        self._sweep_type = "speed"
        self._thread: Optional[QThread] = None
        self._worker: Optional[_SweepWorker] = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 12, 0, 0)
        outer.setSpacing(6)

        title = QLabel("📈 PARAMETRIC SWEEP")
        title.setStyleSheet(
            f"color: {ACCENT}; font-size: 10px; font-weight: 800; letter-spacing: 1px;"
        )
        outer.addWidget(title)

        # Toggle row
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(4)
        self._toggle_btns: dict[str, QPushButton] = {}
        for key, cfg in _SWEEP_DEFS.items():
            btn = QPushButton(f"{cfg['icon']} {cfg['label']}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda checked, k=key: self._select_sweep(k))
            toggle_row.addWidget(btn)
            self._toggle_btns[key] = btn
        self._style_toggles()

        self._run_btn = QPushButton("▶ Run")
        self._run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_btn.setFixedHeight(26)
        self._run_btn.clicked.connect(self._run_sweep)
        toggle_row.addWidget(self._run_btn)
        self._style_run_button()

        toggle_row.addStretch()
        outer.addLayout(toggle_row)

        # Chart
        self._plot = pg.PlotWidget()
        self._plot.setBackground(PANEL2)
        self._plot.showGrid(x=True, y=True, alpha=0.15)
        self._plot.setFixedHeight(180)
        self._plot.setMenuEnabled(False)
        self._plot.addLegend(offset=(10, 5))
        self._plot.getAxis("left").setPen(pg.mkPen(BORDER))
        self._plot.getAxis("bottom").setPen(pg.mkPen(BORDER))
        self._plot.getAxis("left").setTextPen(pg.mkPen(TEXT3))
        self._plot.getAxis("bottom").setTextPen(pg.mkPen(TEXT3))
        self._cap_curve = self._plot.plot([], [], pen=pg.mkPen(SUCCESS, width=2),
                                          symbol="o", symbolSize=5,
                                          symbolBrush=SUCCESS, name="Cap (t/h)")
        self._pwr_curve = self._plot.plot([], [], pen=pg.mkPen(WARNING, width=2),
                                          symbol="o", symbolSize=5,
                                          symbolBrush=WARNING, name="Power (kW)")
        outer.addWidget(self._plot)
        self._plot.setVisible(False)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color: {PRIMARY}; font-size: 9.5px;")
        outer.addWidget(self._status_lbl)

    def _select_sweep(self, key: str) -> None:
        self._sweep_type = key
        self._style_toggles()

    def _style_toggles(self) -> None:
        for key, btn in self._toggle_btns.items():
            active = (key == self._sweep_type)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ACCENT if active else 'transparent'};
                    color: {'#0b1522' if active else TEXT3};
                    border: none; border-radius: 4px;
                    padding: 0px 12px; font-size: 10px; font-weight: 700;
                }}
            """)

    def _style_run_button(self) -> None:
        running = self._thread is not None
        self._run_btn.setEnabled(not running)
        self._run_btn.setText("⏳" if running else "▶ Run")
        self._run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'transparent' if running else 'rgba(31,184,110,.1)'};
                color: {MUTED if running else SUCCESS};
                border: 1px solid {SUCCESS if not running else BORDER};
                border-radius: 4px; padding: 0px 14px; font-size: 10px; font-weight: 700;
            }}
        """)

    def _run_sweep(self) -> None:
        if self._thread is not None:
            return

        base_payload = self._get_base_payload()
        self._thread = QThread()
        self._worker = _SweepWorker(self._sweep_type, base_payload)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

        self._style_run_button()
        self._status_lbl.setText(f"⏳ Sweeping {_SWEEP_DEFS[self._sweep_type]['label']}…")

    def _on_finished(self, points: list[dict]) -> None:
        if points:
            xs = [p["x"] for p in points]
            caps = [p["cap"] for p in points]
            pwrs = [p["pwr"] for p in points]
            self._cap_curve.setData(xs, caps)
            self._pwr_curve.setData(xs, pwrs)
            self._plot.setLabel(
                "bottom", _SWEEP_DEFS[self._sweep_type]["x_label"],
                color=TEXT3, **{"font-size": "9pt"},
            )
            self._plot.setVisible(True)
            self._status_lbl.setText(f"{len(points)} points swept.")
        else:
            self._status_lbl.setText("⚠ Sweep returned no valid points.")

    def _cleanup_thread(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self._style_run_button()


# ── CalcBasisPanel ──────────────────────────────────────────────────────────

class CalcBasisPanel(QFrame):
    """
    Full port of the "Calculation Basis & Method Traceability" Panel
    from CalcPage.tsx: static basis text + ParamSweepWidget.
    (PowerBreakdown is intentionally not duplicated — see module docstring.)
    """

    def __init__(
        self,
        get_base_payload: Callable[[], dict],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px;"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(2)

        hdr = QLabel("▶ CALCULATION BASIS & METHOD TRACEABILITY ▼")
        hdr.setStyleSheet(f"color: #3a5470; font-size: 9px;")
        outer.addWidget(hdr)

        basis_text = QLabel(
            "Capacity: CEMA §3 — volumetric with inclination factor<br/>"
            "Power: CEMA §4 — Pe + Pm + Pi split, Pf=(Pe+Pm)×kf<br/>"
            "Shaft: ASME B106.1M torsional section modulus<br/>"
            "Bearings: ISO 281 L10 life<br/>"
            "Wear: Archard model, K_base=0.006 mm/h calibrated to CEMA "
            "Class II field data<br/>"
            "Ce=0.50 empirical friction factor (CEMA-based)"
        )
        basis_text.setStyleSheet(f"color: #3a5470; font-size: 9px; line-height: 1.7;")
        basis_text.setTextFormat(Qt.TextFormat.RichText)
        outer.addWidget(basis_text)

        self._sweep = ParamSweepWidget(get_base_payload)
        outer.addWidget(self._sweep)