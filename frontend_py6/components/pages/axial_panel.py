"""
components/pages/axial_panel.py — VECTRIX™ Axial Profile chart panel
═══════════════════════════════════════════════════════════════════════════
Step 4 of the PySide6 migration.

Consumes POST /api/v1/axial-profile via api_client.fetch_axial_profile():
    request  {"inp": <EngineInput dict>, "segments": <int, 10-200>}
    response {"segments": [AxialSegment, ...]}

AxialSegment fields (from backend/models/schemas.py):
    x               float   position along conveyor [m]
    fill_pct        float   local fill fraction [%]
    Qt              float   local achieved capacity [t/h]
    Qt_cap          float   local capacity ceiling [t/h]
    pwr_density     float   local power density [kW/m]
    torque_pm       float   incremental torque per metre [Nm/m]
    torque_cumul    float   cumulative torque at this position [Nm]
    wear_rate       float   local wear rate [mm/h]
    axial_velocity  float   local axial velocity [m/s]
    localAng        float   local inclination [°]
    localPitch      float   local pitch [m]
    status          str     e.g. "ok" | "warn" | "choke" (backend-defined)
    isHanger        bool    True if this x position is a hanger bearing

Layout
------
Header row : title · Segments spinbox · Refresh button · status label
Summary row: 4 KPI chips (Peak fill%, Peak torque, Wear @ discharge, Avg v_ax)
4 stacked, X-linked pyqtgraph PlotWidgets:
    1. Fill % vs Length          — hanger markers as vertical lines
    2. Cumulative Torque vs Length
    3. Wear Rate vs Length       — coloured red where status != "ok"
    4. Axial Velocity vs Length

Not auto-triggered on every keystroke (that would double network traffic
during debounced input changes). ShellWindow fetches only when:
  - the user switches to the "Axial Profile" tab, or
  - the user clicks Refresh, or
  - Segments spinbox changes and Refresh is clicked
"""

from __future__ import annotations

from typing import Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
import pyqtgraph as pg

from theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, ACCENT, PURPLE, TEAL,
)

pg.setConfigOptions(antialias=True, background=PANEL, foreground=TEXT3)


# ── formatting helpers ────────────────────────────────────────────────────

def _f(val: Any, dp: int = 2, fallback: str = "—") -> str:
    try:
        return f"{float(val):.{dp}f}"
    except (TypeError, ValueError):
        return fallback


# ── KPI chip (simple label pair, not the custom-painted one from widgets.py
#    since this needs 4 in a row with distinct accent colours) ─────────────

class _SummaryChip(QFrame):
    def __init__(self, label: str, unit: str, color: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {PANEL2}; border: 1px solid {BORDER}; border-radius: 7px;"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(1)

        top = QHBoxLayout()
        top.setSpacing(4)
        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"color: {TEXT3}; font-size: 9px; font-weight: 700; letter-spacing: .6px;"
        )
        top.addWidget(lbl)
        top.addStretch()
        unit_lbl = QLabel(unit)
        unit_lbl.setStyleSheet(f"color: {MUTED}; font-size: 8.5px;")
        top.addWidget(unit_lbl)
        lay.addLayout(top)

        self._val = QLabel("—")
        self._val.setStyleSheet(
            f"color: {color}; font-size: 17px; font-weight: 800; "
            f"font-family: 'Consolas', monospace;"
        )
        lay.addWidget(self._val)

    def set_value(self, text: str) -> None:
        self._val.setText(text)


# ── Single stacked chart row (title + PlotWidget) ─────────────────────────

class _ChartRow(QWidget):
    def __init__(
        self,
        title: str,
        y_label: str,
        color: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {TEXT3}; font-size: 9.5px; font-weight: 700; "
            f"letter-spacing: .6px; padding-left: 4px;"
        )
        lay.addWidget(title_lbl)

        self.plot = pg.PlotWidget()
        self.plot.setBackground(PANEL2)
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.setLabel("left", y_label, color=TEXT3, **{"font-size": "9pt"})
        self.plot.setLabel("bottom", "Length (m)", color=TEXT3, **{"font-size": "9pt"})
        self.plot.getAxis("left").setPen(pg.mkPen(BORDER))
        self.plot.getAxis("bottom").setPen(pg.mkPen(BORDER))
        self.plot.getAxis("left").setTextPen(pg.mkPen(TEXT3))
        self.plot.getAxis("bottom").setTextPen(pg.mkPen(TEXT3))
        self.plot.setFixedHeight(130)
        self.plot.setMenuEnabled(False)

        self._curve = self.plot.plot(
            [], [], pen=pg.mkPen(color, width=2.2)
        )
        self._color = color
        self._hanger_lines: list[pg.InfiniteLine] = []

        lay.addWidget(self.plot)

    def set_data(self, x: list[float], y: list[float]) -> None:
        self._curve.setData(x, y)

    def set_segment_colors(
        self, x: list[float], y: list[float], statuses: list[str]
    ) -> None:
        """
        Colour-coded scatter overlay for wear-rate row — red dots where
        status != 'ok', otherwise the base line colour.
        """
        self._curve.setData(x, y)
        bad_x = [xi for xi, s in zip(x, statuses) if s and s != "ok"]
        bad_y = [yi for yi, s in zip(y, statuses) if s and s != "ok"]
        # Remove any previous overlay
        if hasattr(self, "_bad_scatter"):
            self.plot.removeItem(self._bad_scatter)
        self._bad_scatter = pg.ScatterPlotItem(
            bad_x, bad_y, size=7, brush=pg.mkBrush(DANGER),
            pen=pg.mkPen(None),
        )
        self.plot.addItem(self._bad_scatter)

    def set_hangers(self, x_positions: list[float]) -> None:
        for line in self._hanger_lines:
            self.plot.removeItem(line)
        self._hanger_lines.clear()
        for xp in x_positions:
            line = pg.InfiniteLine(
                pos=xp, angle=90,
                pen=pg.mkPen(PRIMARY, width=1, style=Qt.PenStyle.DashLine),
            )
            line.setZValue(-10)
            self.plot.addItem(line)
            self._hanger_lines.append(line)

    def clear(self) -> None:
        self._curve.setData([], [])
        for line in self._hanger_lines:
            self.plot.removeItem(line)
        self._hanger_lines.clear()
        if hasattr(self, "_bad_scatter"):
            self.plot.removeItem(self._bad_scatter)
            del self._bad_scatter


# ── AxialProfilePanel ──────────────────────────────────────────────────────

class AxialProfilePanel(QWidget):
    """
    Full Axial Profile tab content.

    Signal:
        refresh_requested(segments: int) — emitted when the user clicks
        Refresh or changes the Segments spinbox and clicks Refresh.
        ShellWindow connects this to a fetch_axial_profile() call using
        the current sidebar payload.

    Public:
        set_data(response: dict)  — response = {"segments": [...]}, called
                                     after a successful backend fetch
        set_loading(bool)
        set_error(message: str)
    """

    refresh_requested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 10)
        outer.setSpacing(8)

        # ── Header ───────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        title = QLabel("⚙  AXIAL PROFILE")
        title.setStyleSheet(
            f"color: {TEXT}; font-size: 12px; font-weight: 700; letter-spacing: .5px;"
        )
        hdr.addWidget(title)
        hdr.addStretch()

        seg_lbl = QLabel("Segments")
        seg_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 10.5px;")
        hdr.addWidget(seg_lbl)

        self._segments = QSpinBox()
        self._segments.setRange(10, 200)
        self._segments.setValue(60)
        self._segments.setFixedWidth(70)
        self._segments.setStyleSheet(
            f"background-color: {PANEL2}; color: {TEXT}; "
            f"border: 1px solid {BORDER}; border-radius: 4px; padding: 3px 6px; "
            f"font-size: 11px; font-family: 'Consolas', monospace;"
        )
        hdr.addWidget(self._segments)

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY}; color: white; border: none;
                border-radius: 5px; padding: 5px 14px; font-size: 11px; font-weight: 700;
            }}
            QPushButton:hover {{ background-color: #5aaaff; }}
        """)
        refresh_btn.clicked.connect(
            lambda: self.refresh_requested.emit(self._segments.value())
        )
        hdr.addWidget(refresh_btn)

        outer.addLayout(hdr)

        self._status_lbl = QLabel("Press Refresh to load axial profile for the current design.")
        self._status_lbl.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        self._status_lbl.setWordWrap(True)
        outer.addWidget(self._status_lbl)

        # ── Summary chips ────────────────────────────────────────────────
        summary_row = QHBoxLayout()
        summary_row.setSpacing(8)
        self._chip_fill  = _SummaryChip("Peak fill",       "%",    WARNING)
        self._chip_tor   = _SummaryChip("Peak torque",     "Nm",   ACCENT)
        self._chip_wear  = _SummaryChip("Wear @ discharge", "mm/h", DANGER)
        self._chip_vax   = _SummaryChip("Avg velocity",    "m/s",  TEAL)
        for chip in (self._chip_fill, self._chip_tor, self._chip_wear, self._chip_vax):
            summary_row.addWidget(chip)
        outer.addLayout(summary_row)

        # ── Charts ───────────────────────────────────────────────────────
        self._row_fill  = _ChartRow("FILL FRACTION",      "Fill %",       WARNING)
        self._row_tor   = _ChartRow("CUMULATIVE TORQUE",  "Torque (Nm)",  ACCENT)
        self._row_wear  = _ChartRow("WEAR RATE",          "Wear (mm/h)",  DANGER)
        self._row_vax   = _ChartRow("AXIAL VELOCITY",     "v (m/s)",      TEAL)

        for row in (self._row_fill, self._row_tor, self._row_wear, self._row_vax):
            outer.addWidget(row)

        # Link all X axes together for synced pan/zoom
        self._row_tor.plot.setXLink(self._row_fill.plot)
        self._row_wear.plot.setXLink(self._row_fill.plot)
        self._row_vax.plot.setXLink(self._row_fill.plot)

        outer.addStretch()

    # ── Public API ────────────────────────────────────────────────────────

    def segments_value(self) -> int:
        """Current value of the Segments spinbox — used by ShellWindow
        for the initial lazy fetch (before the user has clicked Refresh)."""
        return self._segments.value()

    def set_loading(self) -> None:
        self._status_lbl.setText("Loading axial profile…")
        self._status_lbl.setStyleSheet(f"color: {PRIMARY}; font-size: 10px;")

    def set_error(self, message: str) -> None:
        self._status_lbl.setText(f"⚠ {message}")
        self._status_lbl.setStyleSheet(f"color: {DANGER}; font-size: 10px;")

    def set_data(self, response: dict) -> None:
        """
        response = {"segments": [AxialSegment dict, ...]}
        Each segment dict has keys: x, fill_pct, Qt, Qt_cap, pwr_density,
        torque_pm, torque_cumul, wear_rate, axial_velocity, localAng,
        localPitch, status, isHanger.
        """
        if not response or response.get("error"):
            self.set_error(response.get("message", "Unknown error") if response else "No response")
            self._clear_all()
            return

        segments = response.get("segments", [])
        if not segments:
            self._status_lbl.setText("No segments returned.")
            self._status_lbl.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
            self._clear_all()
            return

        n = len(segments)
        self._status_lbl.setText(f"{n} segments loaded.")
        self._status_lbl.setStyleSheet(f"color: {SUCCESS}; font-size: 10px;")

        x       = [s.get("x", 0.0)              for s in segments]
        fill    = [s.get("fill_pct", 0.0)        for s in segments]
        torque  = [s.get("torque_cumul", 0.0)    for s in segments]
        wear    = [s.get("wear_rate", 0.0)       for s in segments]
        v_ax    = [s.get("axial_velocity", 0.0)  for s in segments]
        status  = [s.get("status", "ok")         for s in segments]
        hangers = [s.get("x", 0.0) for s in segments if s.get("isHanger")]

        self._row_fill.set_data(x, fill)
        self._row_fill.set_hangers(hangers)

        self._row_tor.set_data(x, torque)
        self._row_tor.set_hangers(hangers)

        self._row_wear.set_segment_colors(x, wear, status)
        self._row_wear.set_hangers(hangers)

        self._row_vax.set_data(x, v_ax)
        self._row_vax.set_hangers(hangers)

        # Summary chips
        self._chip_fill.set_value(_f(max(fill, default=0.0), 1))
        self._chip_tor.set_value(_f(max(torque, default=0.0), 0))
        self._chip_wear.set_value(_f(wear[-1] if wear else 0.0, 4))
        avg_v = sum(v_ax) / len(v_ax) if v_ax else 0.0
        self._chip_vax.set_value(_f(avg_v, 4))

    def _clear_all(self) -> None:
        for row in (self._row_fill, self._row_tor, self._row_wear, self._row_vax):
            row.clear()
        for chip in (self._chip_fill, self._chip_tor, self._chip_wear, self._chip_vax):
            chip.set_value("—")