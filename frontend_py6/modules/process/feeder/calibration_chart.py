"""
modules/process/feeder/calibration_chart.py — N vs Q calibration curve
═══════════════════════════════════════════════════════════════════════════
Port of the Recharts LineChart at the foot of FeederPage.tsx.

Separate from modules/process/axial_chart.py because the axes mean
something different. AxialChart plots a solver `history` array against
axial position — X is always metres down the screw. This plots the feeder's
`calibCurve`, X is speed in RPM, and it carries two reference lines on
different axes at once:

    horizontal   y = target flow            (amber)
    vertical     x = operating speed        (green)

AxialChart supports one horizontal reference only, so bending it to fit
would have meant adding a vertical-line concept that no axial chart uses.

Below the plot sit three sample tiles at curve indices 0, 5 and 10 — the
low, mid and high points of the eleven-point curve the backend returns.
"""

from __future__ import annotations

from typing import Optional, Sequence

import pyqtgraph as pg
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
)
from PySide6.QtCore import Qt

from core.theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, MUTED, PRIMARY, SUCCESS, WARNING,
    PROCESS_ACCENT,
)


class _SampleTile(QFrame):
    """One N / Q readout beneath the curve."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{" f"background-color: {PANEL2}; border-radius: 5px;" f"}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(1)
        self._n = QLabel("—")
        self._n.setStyleSheet(
            f"QFrame {{" f"color: {MUTED}; font-size: 9px; border: none;" f"}}"
        )
        self._q = QLabel("—")
        self._q.setStyleSheet(
            f"QFrame {{" f"color: {TEXT}; font-size: 9px; font-weight: 700; border: none; "
            f"font-family: 'JetBrains Mono', monospace;" f"}}"
        )
        layout.addWidget(self._n)
        layout.addWidget(self._q)

    def set_point(self, pt: Optional[dict]) -> None:
        if not pt:
            self._n.setText("—")
            self._q.setText("—")
            return
        self._n.setText(f"N = {pt.get('N')} RPM")
        q = pt.get("Q")
        self._q.setText("—" if q is None else f"{float(q):.4f} t/h")


class CalibrationChart(QFrame):

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{" f"background-color: {PANEL}; border: 1px solid {BORDER}; "
            f"border-radius: 8px;" f"}}"
        )
        self._target_line = None
        self._speed_line = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel("📈 N VS Q CALIBRATION CURVE")
        title.setStyleSheet(
            f"QFrame {{" f"color: {PROCESS_ACCENT}; font-size: 9px; font-weight: 700; "
            f"letter-spacing: 0.10em; border: none; "
            f"font-family: 'Barlow Condensed', sans-serif;" f"}}"
        )
        layout.addWidget(title)

        sub = QLabel(
            "Speed (RPM) → Mass flow (t/h) — linear relationship for screw feeders"
        )
        sub.setStyleSheet(
            f"QFrame {{" f"color: {MUTED}; font-size: 9px; border: none;" f"}}"
        )
        layout.addWidget(sub)

        pg.setConfigOptions(antialias=True)
        self._plot = pg.PlotWidget(background=BG)
        self._plot.setFixedHeight(160)
        self._plot.showGrid(x=True, y=True, alpha=0.20)
        self._plot.setStyleSheet(
            f"QFrame {{" "border: none;" f"}}"
        )
        for name, text in (("bottom", "Speed (RPM)"), ("left", "t/h")):
            axis = self._plot.getAxis(name)
            axis.setPen(pg.mkPen(BORDER))
            axis.setTextPen(pg.mkPen(MUTED))
            axis.setLabel(text, **{"color": MUTED, "font-size": "8pt"})
        self._curve = self._plot.plot([], [], pen=pg.mkPen(PRIMARY, width=2))
        layout.addWidget(self._plot)

        tiles = QHBoxLayout()
        tiles.setSpacing(6)
        self._tiles = [_SampleTile() for _ in range(3)]
        for t in self._tiles:
            tiles.addWidget(t)
        layout.addLayout(tiles)

        self.setVisible(False)

    def set_data(
        self,
        curve: Sequence[dict],
        target: Optional[float] = None,
        n_operating: Optional[float] = None,
    ) -> None:
        if not curve:
            self.setVisible(False)
            return

        xs, ys = [], []
        for pt in curve:
            n, q = pt.get("N"), pt.get("Q")
            if n is None or q is None:
                continue
            xs.append(float(n))
            ys.append(float(q))
        if not xs:
            self.setVisible(False)
            return

        self._curve.setData(xs, ys)

        for line_attr in ("_target_line", "_speed_line"):
            line = getattr(self, line_attr)
            if line is not None:
                self._plot.removeItem(line)
                setattr(self, line_attr, None)

        if target is not None:
            self._target_line = pg.InfiniteLine(
                pos=float(target), angle=0,
                pen=pg.mkPen(WARNING, width=1, style=Qt.PenStyle.DashLine),
                label=f"Target {target:g} t/h",
                labelOpts={"color": WARNING, "position": 0.95},
            )
            self._plot.addItem(self._target_line)

        if n_operating is not None:
            self._speed_line = pg.InfiniteLine(
                pos=float(n_operating), angle=90,
                pen=pg.mkPen(SUCCESS, width=1, style=Qt.PenStyle.DashLine),
                label=f"{n_operating:.0f} RPM",
                labelOpts={"color": SUCCESS, "position": 0.92},
            )
            self._plot.addItem(self._speed_line)

        # Indices 0/5/10 as in the .tsx. Guarded because the backend returns
        # eleven points today but nothing in the contract fixes that.
        for tile, idx in zip(self._tiles, (0, 5, 10)):
            tile.set_point(curve[idx] if idx < len(curve) else None)

        self.setVisible(True)