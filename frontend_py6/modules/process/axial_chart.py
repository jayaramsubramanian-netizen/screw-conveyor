"""
modules/process/axial_chart.py — axial profile chart
═══════════════════════════════════════════════════════════════════════════
Port of AxialChart in frontend/src/components/pages/ProcessPage.tsx
(Recharts LineChart) to pyqtgraph.

Kept out of modules/process/common.py deliberately: only the three
marching-solver modules produce a `history` array — Dryer, Cooler, Reactor
— while Mixer, Separator and Compactor return scalars only. Putting it in
common.py would make every process module import pyqtgraph to get a chart
half of them never draw.

Data contract
─────────────
`history` is the array returned by solve_system() in
backend/core/process_engine.py, one entry per segment. Every entry carries
the same keys regardless of module — the marching loop appends a fixed
dict — so a chart is selected by `data_key`:

    x          axial position (m)          — always the X axis
    T          temperature (°C)
    moisture   moisture (% wb)
    Q_cumul    cumulative heat (kW·s)
    X_conv     conversion (%)
    sigma      compaction stress
    rho        density (t/m³)
    d50/d10/d90, mass_flow, energy, torque

Rendering only. Nothing here derives an engineering value; it plots numbers
the backend already computed, which is the same category as ScrewViz2D
under the note in STRUCTURAL_REVIEW_NOTE.md.
"""

from __future__ import annotations

from typing import Optional, Sequence

import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from core.theme import (
    BG, PANEL, BORDER, MUTED, TEXT3, WARNING, PROCESS_ACCENT,
)


class AxialChart(QFrame):
    """
    One titled line chart over a solver history array.

    Mirrors the .tsx component's early return — `if(!history?.length)
    return null` — by hiding itself when handed an empty history, so a
    module whose backend response carries no history simply shows nothing
    rather than an empty set of axes.
    """

    def __init__(
        self,
        label: str,
        data_key: str,
        unit: str,
        color: str,
        ref_value: Optional[float] = None,
        ref_label: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._data_key = data_key
        self._color = color
        self._ref_value = ref_value
        self._ref_label = ref_label
        self._ref_line = None

        self.setStyleSheet(
            f"QFrame {{" f"background-color: {PANEL}; border: 1px solid {BORDER}; "
            f"border-radius: 8px;" f"}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        title = QLabel(f"{label} AXIAL PROFILE".upper())
        title.setStyleSheet(
            f"QFrame {{" f"color: {PROCESS_ACCENT}; font-size: 9px; font-weight: 700; "
            f"letter-spacing: 0.10em; border: none; "
            f"font-family: 'Barlow Condensed', sans-serif;" f"}}"
        )
        layout.addWidget(title)

        pg.setConfigOptions(antialias=True)
        self._plot = pg.PlotWidget(background=BG)
        self._plot.setFixedHeight(160)
        self._plot.showGrid(x=True, y=True, alpha=0.20)
        self._plot.setStyleSheet(
            f"QFrame {{" "border: none;" f"}}"
        )

        for axis_name, text in (("bottom", "Length (m)"), ("left", unit)):
            axis = self._plot.getAxis(axis_name)
            axis.setPen(pg.mkPen(BORDER))
            axis.setTextPen(pg.mkPen(MUTED))
            axis.setLabel(text, **{"color": MUTED, "font-size": "8pt"})

        self._curve = self._plot.plot(
            [], [], pen=pg.mkPen(color, width=2),
        )
        layout.addWidget(self._plot)

        self.setVisible(False)      # nothing plotted yet

    # ── data ──────────────────────────────────────────────────────────────

    def set_history(self, history: Sequence[dict]) -> None:
        if not history:
            self.setVisible(False)
            return

        xs, ys = [], []
        for row in history:
            x = row.get("x")
            y = row.get(self._data_key)
            # Skip rather than substitute: a missing key means the backend
            # did not produce that series for this module, and plotting a
            # zero would read as a real measured value on the chart.
            if x is None or y is None:
                continue
            xs.append(float(x))
            ys.append(float(y))

        if not xs:
            self.setVisible(False)
            return

        self._curve.setData(xs, ys)
        self._draw_reference()
        self.setVisible(True)

    def set_reference(self, value: Optional[float], label: str = "") -> None:
        """Update the target/limit line — the .tsx passes this from the
        input panel (e.g. target moisture), so it changes with the form."""
        self._ref_value = value
        self._ref_label = label
        self._draw_reference()

    def _draw_reference(self) -> None:
        if self._ref_line is not None:
            self._plot.removeItem(self._ref_line)
            self._ref_line = None
        if self._ref_value is None:
            return
        self._ref_line = pg.InfiniteLine(
            pos=float(self._ref_value),
            angle=0,
            pen=pg.mkPen(WARNING, width=1, style=Qt.PenStyle.DashLine),
            label=self._ref_label or None,
            labelOpts={
                "color": WARNING, "position": 0.95,
                "fill": (0, 0, 0, 0), "movable": False,
            },
        )
        self._plot.addItem(self._ref_line)