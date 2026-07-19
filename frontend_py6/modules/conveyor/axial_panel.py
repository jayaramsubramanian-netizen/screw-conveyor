"""
components/pages/axial_panel.py — VECTRIX™ Axial Profile chart panel
═══════════════════════════════════════════════════════════════════════════
Full rebuild to match AxialProfiles from CalcPage.tsx exactly — the
previous version had 4 always-visible stacked charts; the real app uses
7 tabs (single chart, one at a time) plus insights text, a hover
readout, a static legend, and a separate Shaft Deflection Profile
sub-panel below. This version replicates all of that.

Consumes two data sources, matching the TSX component's two inputs
(the `profile` query result and the `R`/`inp` props):

  1. POST /api/v1/axial-profile → {"segments": [AxialSegment, ...]}
     fetched lazily (unchanged behavior from before) via
     api_client.fetch_axial_profile(). Drives the 7 tabbed charts.

  2. The main /api/v1/calculate result (already flowing through
     ShellWindow.run_calculation() for every other panel) — fed via
     the new set_main_result() method. Drives the Shaft Deflection
     Profile sub-panel, which needs `deflection`, `defl_limit`,
     `hgr.span`, `nc`, `nc_ratio`, `tor.pipe`, `tor.eff_od_mm`,
     `tor.eff_id_mm`, and `L` — none of which live in AxialSegment.

Shaft Deflection Profile note: the sin² arch curve is a client-side
interpolation of the single already-backend-computed `deflection`
scalar, spread across hanger spans for visualization — not new
physics, same category as ScrewViz2D's rendering. See
STRUCTURAL_REVIEW_NOTE.md for the contrast with calcStructural(),
which *does* compute new physics client-side and is flagged there.

AxialSegment fields (backend/models/schemas.py):
    x, fill_pct, Qt, Qt_cap, pwr_density, torque_pm, torque_cumul,
    wear_rate, axial_velocity, localAng, localPitch, status, isHanger
"""

from __future__ import annotations

import math
from typing import Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QFrame,
)
from PySide6.QtCore import Qt, Signal
import pyqtgraph as pg

from core.theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, ACCENT, PURPLE, TEAL,
)

pg.setConfigOptions(antialias=True, background=PANEL2, foreground=TEXT3)


def _f(val: Any, dp: int = 2, fallback: str = "—") -> str:
    try:
        return f"{float(val):.{dp}f}"
    except (TypeError, ValueError):
        return fallback


# ── 7-tab config — matches AxialProfiles `tabs` object exactly ───────────
_TAB_DEFS = [
    ("Throughput", "Qt",             SUCCESS, "t/h",   True),   # has req. ref line
    ("Fill",       "fill_pct",       PRIMARY, "%",     False),
    ("Power",      "pwr_density",    WARNING, "kW/m",  False),
    ("Torque",     "torque_pm",      PURPLE,  "Nm/m",  False),
    ("Cumulative", "torque_cumul",   ACCENT,  "Nm",    False),
    ("Wear",       "wear_rate",      DANGER,  "mm/h",  False),
    ("Axial",      "axial_velocity", TEAL,    "m/s",   False),
]


# ══════════════════════════════════════════════════════════════════════════
# AxialProfilePanel
# ══════════════════════════════════════════════════════════════════════════

class AxialProfilePanel(QWidget):
    """
    Public interface unchanged from the previous version for
    main.py compatibility:
        refresh_requested(segments: int)  signal
        segments_value() -> int
        set_loading() / set_error(msg) / set_data(response: dict)
    New:
        set_main_result(result: dict) — feeds the Shaft Deflection
        Profile sub-panel. Cheap to call on every calculate (no
        re-render unless this tab is visible would be a further
        optimisation; not needed at this data volume).
    """

    refresh_requested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG};")
        self._segments: list[dict] = []
        self._main_result: dict = {}
        self._active_tab = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 10)
        outer.setSpacing(8)

        # ── Header ───────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        title = QLabel("📈  AXIAL PROFILES")
        title.setStyleSheet(
            f"color: {TEXT}; font-size: 12px; font-weight: 700; letter-spacing: .5px;"
        )
        hdr.addWidget(title)
        hdr.addStretch()

        seg_lbl = QLabel("Segments")
        seg_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 10.5px;")
        hdr.addWidget(seg_lbl)
        self._segments_spin = QSpinBox()
        self._segments_spin.setRange(10, 200)
        self._segments_spin.setValue(60)
        self._segments_spin.setFixedWidth(70)
        self._segments_spin.setStyleSheet(
            f"background-color: {PANEL2}; color: {TEXT}; "
            f"border: 1px solid {BORDER}; border-radius: 4px; padding: 3px 6px; "
            f"font-size: 11px; font-family: 'Consolas', monospace;"
        )
        hdr.addWidget(self._segments_spin)

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
            lambda: self.refresh_requested.emit(self._segments_spin.value())
        )
        hdr.addWidget(refresh_btn)
        outer.addLayout(hdr)

        self._status_lbl = QLabel("Press Refresh to load axial profile for the current design.")
        self._status_lbl.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        self._status_lbl.setWordWrap(True)
        outer.addWidget(self._status_lbl)

        # ── Tab row (7 tabs) ────────────────────────────────────────────
        tab_row = QHBoxLayout()
        tab_row.setSpacing(4)
        self._tab_btns: list[QPushButton] = []
        for i, (label, _key, color, _unit, _req) in enumerate(_TAB_DEFS):
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda checked, idx=i: self._select_tab(idx))
            tab_row.addWidget(btn)
            self._tab_btns.append(btn)
        tab_row.addStretch()
        outer.addLayout(tab_row)
        self._style_tabs()

        # ── Chart ────────────────────────────────────────────────────────
        self._plot = pg.PlotWidget()
        self._plot.setBackground(PANEL2)
        self._plot.showGrid(x=True, y=True, alpha=0.15)
        self._plot.setFixedHeight(220)
        self._plot.setMenuEnabled(False)
        self._plot.setLabel("bottom", "Length (m)", color=TEXT3, **{"font-size": "9pt"})
        self._plot.getAxis("left").setPen(pg.mkPen(BORDER))
        self._plot.getAxis("bottom").setPen(pg.mkPen(BORDER))
        self._plot.getAxis("left").setTextPen(pg.mkPen(TEXT3))
        self._plot.getAxis("bottom").setTextPen(pg.mkPen(TEXT3))
        self._curve = self._plot.plot([], [], pen=pg.mkPen(SUCCESS, width=2.2))
        self._hanger_lines: list[pg.InfiniteLine] = []
        self._req_line: Optional[pg.InfiniteLine] = None
        outer.addWidget(self._plot)

        # Hover readout via SignalProxy
        self._hover_lbl = QLabel("")
        self._hover_lbl.setStyleSheet(
            f"background-color: #081321; border-radius: 6px; padding: 6px 12px; "
            f"color: {TEXT2}; font-size: 10px; font-family: 'Consolas', monospace;"
        )
        self._hover_lbl.setVisible(False)
        outer.addWidget(self._hover_lbl)
        self._proxy = pg.SignalProxy(
            self._plot.scene().sigMouseMoved, rateLimit=30, slot=self._on_mouse_moved
        )

        # ── Legend (static) ─────────────────────────────────────────────
        legend_row = QHBoxLayout()
        legend_row.setSpacing(14)
        for text, color in [
            ("Hanger bearing", PRIMARY), ("Flooding", DANGER),
            ("Choke (<req.)", WARNING), ("Starved (<12%)", MUTED),
        ]:
            lbl = QLabel(f"● {text}")
            lbl.setStyleSheet(f"color: {color}; font-size: 9px;")
            legend_row.addWidget(lbl)
        legend_row.addStretch()
        outer.addLayout(legend_row)

        # ── Insights ─────────────────────────────────────────────────────
        self._insights_layout = QVBoxLayout()
        self._insights_layout.setSpacing(4)
        outer.addLayout(self._insights_layout)

        # ── Shaft Deflection Profile (separate sub-panel) ──────────────
        outer.addWidget(self._divider())

        defl_hdr = QHBoxLayout()
        defl_title = QLabel("📐 SHAFT DEFLECTION PROFILE")
        defl_title.setStyleSheet(
            f"color: {ACCENT}; font-size: 10px; font-weight: 800; letter-spacing: .8px;"
        )
        defl_hdr.addWidget(defl_title)
        defl_hdr.addStretch()
        self._defl_shaft_lbl = QLabel("")
        self._defl_shaft_lbl.setStyleSheet(
            f"color: {PRIMARY}; font-size: 9px; font-family: 'Consolas', monospace;"
        )
        defl_hdr.addWidget(self._defl_shaft_lbl)
        outer.addLayout(defl_hdr)

        self._defl_plot = pg.PlotWidget()
        self._defl_plot.setBackground(PANEL2)
        self._defl_plot.showGrid(x=True, y=True, alpha=0.15)
        self._defl_plot.setFixedHeight(140)
        self._defl_plot.setMenuEnabled(False)
        self._defl_plot.setLabel("bottom", "Length (m)", color=TEXT3, **{"font-size": "9pt"})
        self._defl_plot.setLabel("left", "δ (mm)", color=TEXT3, **{"font-size": "9pt"})
        self._defl_plot.getAxis("left").setPen(pg.mkPen(BORDER))
        self._defl_plot.getAxis("bottom").setPen(pg.mkPen(BORDER))
        self._defl_plot.getAxis("left").setTextPen(pg.mkPen(TEXT3))
        self._defl_plot.getAxis("bottom").setTextPen(pg.mkPen(TEXT3))
        self._defl_curve = self._defl_plot.plot([], [], pen=pg.mkPen(PRIMARY, width=2))
        outer.addWidget(self._defl_plot)

        # Critical speed bar
        nc_row = QHBoxLayout()
        nc_row.setSpacing(8)
        nc_lbl = QLabel("Critical Speed")
        nc_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 9px;")
        nc_row.addWidget(nc_lbl)

        self._nc_bar_bg = QFrame()
        self._nc_bar_bg.setFixedHeight(10)
        self._nc_bar_bg.setStyleSheet(f"background-color: {BORDER}; border-radius: 5px;")
        nc_bar_layout = QHBoxLayout(self._nc_bar_bg)
        nc_bar_layout.setContentsMargins(0, 0, 0, 0)
        nc_bar_layout.setSpacing(0)
        self._nc_bar_fill = QFrame()
        self._nc_bar_fill.setStyleSheet(f"background-color: {SUCCESS}; border-radius: 5px;")
        nc_bar_layout.addWidget(self._nc_bar_fill)
        nc_bar_layout.addStretch()
        nc_row.addWidget(self._nc_bar_bg, 1)

        self._nc_pct_lbl = QLabel("—")
        self._nc_pct_lbl.setStyleSheet(f"color: {MUTED}; font-size: 9px;")
        nc_row.addWidget(self._nc_pct_lbl)
        self._nc_rpm_lbl = QLabel("—")
        self._nc_rpm_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 9px;")
        nc_row.addWidget(self._nc_rpm_lbl)
        outer.addLayout(nc_row)

    @staticmethod
    def _divider() -> QFrame:
        f = QFrame()
        f.setFixedHeight(1)
        f.setStyleSheet(f"background-color: {BORDER};")
        return f

    # ── tab selection / styling ─────────────────────────────────────────

    def _select_tab(self, idx: int) -> None:
        self._active_tab = idx
        self._style_tabs()
        self._render_chart()

    def _style_tabs(self) -> None:
        for i, btn in enumerate(self._tab_btns):
            active = (i == self._active_tab)
            color = _TAB_DEFS[i][2]
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color if active else 'transparent'};
                    color: {'#0b1522' if active else TEXT3};
                    border: 1px solid {color if active else BORDER};
                    border-radius: 4px; padding: 0px 12px; font-size: 10px; font-weight: 700;
                }}
            """)

    # ── public API ────────────────────────────────────────────────────────

    def segments_value(self) -> int:
        return self._segments_spin.value()

    def set_loading(self) -> None:
        self._status_lbl.setText("Loading axial profile…")
        self._status_lbl.setStyleSheet(f"color: {PRIMARY}; font-size: 10px;")

    def set_error(self, message: str) -> None:
        self._status_lbl.setText(f"⚠ {message}")
        self._status_lbl.setStyleSheet(f"color: {DANGER}; font-size: 10px;")

    def set_data(self, response: dict) -> None:
        """response = {"segments": [AxialSegment dict, ...]}"""
        if not response or response.get("error"):
            self._status_lbl.setText(
                response.get("message", "Unknown error") if response else "No response"
            )
            self._status_lbl.setStyleSheet(f"color: {DANGER}; font-size: 10px;")
            self._segments = []
            self._render_chart()
            self._render_insights()
            return

        self._segments = response.get("segments", [])
        if not self._segments:
            self._status_lbl.setText("No segments returned.")
            self._status_lbl.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        else:
            self._status_lbl.setText(f"{len(self._segments)} segments loaded.")
            self._status_lbl.setStyleSheet(f"color: {SUCCESS}; font-size: 10px;")

        self._render_chart()
        self._render_insights()

    def set_main_result(self, result: dict) -> None:
        """Feeds the Shaft Deflection Profile sub-panel."""
        if not result or result.get("error"):
            return
        self._main_result = result
        self._render_deflection()

    # ── chart rendering ──────────────────────────────────────────────────

    def _render_chart(self) -> None:
        label, key, color, unit, has_req = _TAB_DEFS[self._active_tab]
        self._plot.setLabel("left", f"{label} ({unit})", color=TEXT3, **{"font-size": "9pt"})

        for line in self._hanger_lines:
            self._plot.removeItem(line)
        self._hanger_lines.clear()
        if self._req_line is not None:
            self._plot.removeItem(self._req_line)
            self._req_line = None

        if not self._segments:
            self._curve.setData([], [])
            return

        x = [s.get("x", 0.0) for s in self._segments]
        y = [s.get(key, 0.0) for s in self._segments]
        self._curve.setData(x, y, pen=pg.mkPen(color, width=2.2))

        for s in self._segments:
            if s.get("isHanger"):
                line = pg.InfiniteLine(
                    pos=s.get("x", 0.0), angle=90,
                    pen=pg.mkPen(PRIMARY, width=1, style=Qt.PenStyle.DashLine),
                )
                line.setZValue(-10)
                self._plot.addItem(line)
                self._hanger_lines.append(line)

        if has_req:
            req_cap = (self._main_result.get("cap", {}) or {}).get("req")
            if req_cap is not None:
                self._req_line = pg.InfiniteLine(
                    pos=req_cap, angle=0,
                    pen=pg.mkPen(WARNING, width=1.5, style=Qt.PenStyle.DashLine),
                    label=f"Required {req_cap:g} t/h",
                    labelOpts={"color": WARNING, "position": 0.95},
                )
                self._plot.addItem(self._req_line)

    def _on_mouse_moved(self, evt) -> None:
        if not self._segments:
            self._hover_lbl.setVisible(False)
            return
        pos = evt[0]
        if not self._plot.sceneBoundingRect().contains(pos):
            self._hover_lbl.setVisible(False)
            return
        mouse_point = self._plot.getPlotItem().vb.mapSceneToView(pos)
        target_x = mouse_point.x()

        nearest = min(self._segments, key=lambda s: abs(s.get("x", 0.0) - target_x))
        status = nearest.get("status", "ok")
        pitch_mm = (nearest.get("localPitch", 0.0) or 0.0) * 1000

        parts = [
            f"x = {_f(nearest.get('x'), 2)} m",
            f"Throughput: {_f(nearest.get('Qt'), 1)} t/h",
            f"Fill: {_f(nearest.get('fill_pct'), 1)}%",
            f"Pitch: {pitch_mm:.0f} mm",
        ]
        if status != "ok":
            parts.append(f"▲ {str(status).upper()} — capacity limited")

        self._hover_lbl.setText("   ".join(parts))
        self._hover_lbl.setVisible(True)

    def _render_insights(self) -> None:
        while self._insights_layout.count():
            item = self._insights_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()

        if not self._segments:
            return

        n = len(self._segments)
        choke_count = sum(1 for s in self._segments if s.get("status") == "choke")
        insights: list[str] = []

        if n > 0 and choke_count / n > 0.5:
            pitch_mm = (self._main_result.get("P") or 0.3) * 1000
            insights.append(
                f"{round(choke_count / n * 100)}% of length is choking — throughput "
                f"limited by inlet pitch ({pitch_mm:.0f} mm). Increase inlet pitch or "
                f"reduce required capacity."
            )

        wear_rates = [s.get("wear_rate", 0.0) or 0.0 for s in self._segments]
        max_wear = max(wear_rates) if wear_rates else 0.0
        if max_wear > 0.01:
            insights.append(
                f"High inlet wear ({max_wear:.4f} mm/h). Consider AR-lined inlet "
                f"section or reduced inlet pitch."
            )

        for text in insights:
            box = QLabel(f"⚠ {text}")
            box.setStyleSheet(
                f"background-color: rgba(232,160,0,.06); border: 1px solid {WARNING}44; "
                f"border-radius: 5px; padding: 5px 10px; color: {WARNING}; font-size: 10px;"
            )
            box.setWordWrap(True)
            self._insights_layout.addWidget(box)

    # ── shaft deflection sub-panel ───────────────────────────────────────

    def _render_deflection(self) -> None:
        r = self._main_result
        if not r:
            return

        tor = r.get("tor", {}) or {}
        is_pipe = bool(tor.get("pipe", False))
        od = tor.get("eff_od_mm") or tor.get("od") or 70
        id_mm = tor.get("eff_id_mm") or 0

        if is_pipe:
            self._defl_shaft_lbl.setText(f"Pipe Ø{od:.0f}×{id_mm:.0f} mm (hollow)")
            self._defl_shaft_lbl.setStyleSheet(
                f"color: {PURPLE}; font-size: 9px; font-family: 'Consolas', monospace;"
            )
        else:
            self._defl_shaft_lbl.setText(f"Bar Ø{od:.0f} mm (solid)")
            self._defl_shaft_lbl.setStyleSheet(
                f"color: {PRIMARY}; font-size: 9px; font-family: 'Consolas', monospace;"
            )

        L = r.get("L", 10.0) or 10.0
        hgr = r.get("hgr", {}) or {}
        span = max(hgr.get("span", L) or L, 0.1)
        mx_d = max((r.get("deflection", 0.0) or 0.0) * 1000, 0.0)
        limit_mm = (r.get("defl_limit", 0.01) or 0.01) * 1000
        deflection_ok = r.get("deflection_ok")

        num_spans = max(1, round(L / span))
        n_pts = num_spans * 20 + 1
        xs, ys = [], []
        for i in range(n_pts):
            x_frac = i / (num_spans * 20)
            x_in_span = (x_frac * num_spans) % 1.0
            d = mx_d * (math.sin(math.pi * x_in_span) ** 2)
            xs.append(x_frac * L)
            ys.append(d)

        defl_color = PURPLE if is_pipe else PRIMARY
        self._defl_curve.setData(xs, ys, pen=pg.mkPen(defl_color, width=2))

        # Clear and redraw reference lines
        for item in list(self._defl_plot.getPlotItem().items):
            if isinstance(item, pg.InfiniteLine):
                self._defl_plot.removeItem(item)

        for i in range(num_spans - 1):
            pos = (i + 1) * span
            line = pg.InfiniteLine(
                pos=pos, angle=90,
                pen=pg.mkPen(PURPLE, width=1, style=Qt.PenStyle.DashLine),
            )
            line.setZValue(-10)
            self._defl_plot.addItem(line)

        limit_line = pg.InfiniteLine(
            pos=limit_mm, angle=0,
            pen=pg.mkPen(DANGER, width=1.5, style=Qt.PenStyle.DashLine),
            label=f"Limit {limit_mm:.2f} mm",
            labelOpts={"color": DANGER, "position": 0.95},
        )
        self._defl_plot.addItem(limit_line)

        actual_color = SUCCESS if deflection_ok else DANGER
        actual_line = pg.InfiniteLine(
            pos=mx_d, angle=0,
            pen=pg.mkPen(actual_color, width=1, style=Qt.PenStyle.DotLine),
            label=f"δ={mx_d:.3f} mm {'✓' if deflection_ok else '✗'}",
            labelOpts={"color": actual_color, "position": 0.05},
        )
        self._defl_plot.addItem(actual_line)

        # Critical speed bar
        nc = r.get("nc", 0.0) or 0.0
        nc_ratio = r.get("nc_ratio", 0.0) or 0.0
        pct = max(0.0, min(100.0, nc_ratio * 100))
        bar_color = SUCCESS if nc_ratio < 0.7 else WARNING

        total_w = max(self._nc_bar_bg.width(), 120)
        fill_w = int(total_w * pct / 100)
        self._nc_bar_fill.setFixedWidth(fill_w)
        self._nc_bar_fill.setStyleSheet(f"background-color: {bar_color}; border-radius: 5px;")
        self._nc_pct_lbl.setText(f"{pct:.0f}% of Nc")
        self._nc_rpm_lbl.setText(f"Nc={nc:.0f} RPM")