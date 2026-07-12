"""
components/screw_viz.py — VECTRIX™ 2D Screw Visualizer (QPainter)
═══════════════════════════════════════════════════════════════════════════
Step 5 of the PySide6 migration.

Faithful port of the ScrewViz2D React component from screw-process-v4.html
(renderAxial / renderCross), scoped to the SCREW CONVEYOR calculator only:

  IN SCOPE   — single-shaft screw/pipe conveyor axial + cross-section views,
               pan/zoom, play/pause animation with speed control, hanger
               bearing markers, drive/tail labels, Froude-based flow-regime
               badge, axial velocity arrow, animated material particles.

  OUT OF SCOPE (documented, not silently dropped) — twin/triple-shaft
  rendering (ns>=2, mixer-only), process-module overlays (dryer steam
  wisps, cooler pulse rings, reactor glow, compactor density bar,
  separator split arrows), multi-pitch PitchViz. These return when the
  process modules are ported ("processes come next").

Consumes the engine result dict directly — no extra backend call needed.
Reads: D, L, N, P_eff, is_pipe, cap.fill_actual, cap.v_axial, hgr.count.
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QRect, Signal
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QBrush, QFont,
    QLinearGradient, QRadialGradient,
)

from theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, ACCENT, PURPLE, TEAL,
)

# ── Drawing-specific colours not in the shared UI palette ────────────────
# (same pattern as bucket-elevator's ElevatorSchematic DRAWING dict —
# kept local since these are only meaningful inside this drawing)
_DRAW = {
    "trough_top":    "#17304d",
    "trough_bottom": "#0a1e30",
    "trough_stroke": "#2a5070",
    "dim_line":      "#2a4060",
    "shaft_metal_a": "#c0c8d0",
    "shaft_metal_b": "#4a5568",
    "hatch":         "rgba(255,255,255,0.08)",
}

_FLIGHT_COLOR = ACCENT   # amber — matches JS default (non-process) fill colour


# ── Froude-based flow regime classification ───────────────────────────────
# Mirrors classifyFlowRegime(Fr) from the JS engine exactly. Computed
# locally here (D, N only) rather than fetched from the backend, since
# the JS component also computed it client-side inside the visualizer.
def _classify_regime(Fr: float) -> tuple[str, str, str]:
    """Returns (name, icon, color_hex)."""
    if Fr < 0.10:
        return "Sliding", "🔴", DANGER
    if Fr < 0.50:
        return "Rolling", "🟢", SUCCESS
    if Fr < 2.00:
        return "Cascading", "🟡", WARNING
    return "Centrifugal", "🔴", DANGER


# ══════════════════════════════════════════════════════════════════════════
# _Canvas — pan/zoom capable drawing surface
# ══════════════════════════════════════════════════════════════════════════

class _Canvas(QWidget):
    """
    Owns pan (drag) + zoom (wheel) transform state and delegates the
    actual drawing to a callback supplied by the parent ScrewViz2D.
    """

    def __init__(self, draw_fn, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._draw_fn = draw_fn          # (painter, draw_w, draw_h) -> None
        self._draw_w = 700.0
        self._draw_h = 280.0
        self.setMinimumHeight(260)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setStyleSheet(f"background-color: #081321; border-radius: 0px;")

        self.pan_x = 0.0
        self.pan_y = 0.0
        self.scale = 1.0

        self._dragging = False
        self._drag_start = QPointF()
        self._pan_start = (0.0, 0.0)

    def set_draw_size(self, w: float, h: float) -> None:
        self._draw_w = w
        self._draw_h = h
        self.update()

    def reset_view(self) -> None:
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.scale = 1.0
        self.update()

    # ── mouse / wheel ────────────────────────────────────────────────────
    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self._dragging = True
        self._drag_start = event.position()
        self._pan_start = (self.pan_x, self.pan_y)
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if not self._dragging:
            return
        delta = event.position() - self._drag_start
        self.pan_x = self._pan_start[0] + delta.x()
        self.pan_y = self._pan_start[1] + delta.y()
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._dragging = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        factor = 1.15 if event.angleDelta().y() > 0 else 0.88
        self.scale = max(0.25, min(8.0, self.scale * factor))
        self.update()
        event.accept()

    # ── paint ────────────────────────────────────────────────────────────
    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        p.save()
        # Centre the drawing, then apply pan + zoom around that centre —
        # mirrors the CSS `transform: translate(pan) scale(s); transform-
        # origin: center center;` used in the original JS component.
        fit = min(w / self._draw_w, h / self._draw_h) if self._draw_w and self._draw_h else 1.0
        fit = max(fit, 0.05)
        p.translate(w / 2 + self.pan_x, h / 2 + self.pan_y)
        p.scale(self.scale * fit, self.scale * fit)
        p.translate(-self._draw_w / 2, -self._draw_h / 2)

        self._draw_fn(p, self._draw_w, self._draw_h)
        p.restore()
        p.end()


# ══════════════════════════════════════════════════════════════════════════
# ScrewViz2D — full widget (header toolbar + canvas + footer)
# ══════════════════════════════════════════════════════════════════════════

class ScrewViz2D(QWidget):
    """
    2D screw conveyor visualizer.

    Public:
        set_data(result: dict) — feeds D, L, N, P_eff, is_pipe,
                                  cap.fill_actual, cap.v_axial, hgr.count
                                  from the engine result dict directly.
    """

    _SPEEDS = [0.25, 0.5, 1.0, 2.0, 4.0]
    _TICK_MS = 33   # ~30 fps

    def __init__(self, title: str = "2D Visualizer", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = title

        # ── design data (populated via set_data) ────────────────────────
        self._D = 0.300
        self._L = 10.0
        self._N = 60.0
        self._P_eff = 0.300
        self._is_pipe = False
        self._fill = 0.30
        self._v_axial = 0.0
        self._hangers = 0

        # ── view / animation state ───────────────────────────────────────
        self._view = "axial"          # "axial" | "cross"
        self._playing = False
        self._speed = 1.0
        self._phase = 0.0             # radians, screw rotation phase
        self._rev_count = 0
        self._particles: list[dict] = []
        self._n_particles = 18

        self._timer = QTimer(self)
        self._timer.setInterval(self._TICK_MS)
        self._timer.timeout.connect(self._on_tick)

        self._init_particles()
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setStyleSheet(
            f"background-color: #081321; border: 1px solid {BORDER}; border-radius: 10px;"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ───────────────────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(38)
        header.setStyleSheet(
            f"background-color: rgba(0,0,0,0.35); "
            f"border-bottom: 1px solid {BORDER}; border-top-left-radius: 10px; "
            f"border-top-right-radius: 10px;"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 0, 12, 0)
        hl.setSpacing(8)

        icon = QLabel("📐")
        icon.setStyleSheet("font-size: 13px;")
        hl.addWidget(icon)

        title_lbl = QLabel(self._title.upper())
        title_lbl.setStyleSheet(
            f"color: {TEXT3}; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        hl.addWidget(title_lbl)

        self._live_badge = QLabel("● LIVE")
        self._live_badge.setStyleSheet(
            f"background-color: rgba(31,184,110,.15); color: {SUCCESS}; "
            f"border: 1px solid {SUCCESS}; border-radius: 3px; "
            f"padding: 0px 5px; font-size: 9px; font-weight: 700;"
        )
        self._live_badge.setVisible(False)
        hl.addWidget(self._live_badge)

        hl.addStretch()

        # Play/Pause
        self._play_btn = QPushButton("▶ Play")
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.setFixedHeight(24)
        self._play_btn.clicked.connect(self._toggle_play)
        hl.addWidget(self._play_btn)
        self._style_play_button()

        # Speed selector
        speed_box = QFrame()
        speed_box.setStyleSheet(
            f"background-color: #0a1929; border: 1px solid {BORDER}; border-radius: 5px;"
        )
        speed_lay = QHBoxLayout(speed_box)
        speed_lay.setContentsMargins(0, 0, 0, 0)
        speed_lay.setSpacing(0)
        self._speed_btns: dict[float, QPushButton] = {}
        for s in self._SPEEDS:
            btn = QPushButton(f"{s:g}×")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(22)
            btn.clicked.connect(lambda checked, sv=s: self._set_speed(sv))
            speed_lay.addWidget(btn)
            self._speed_btns[s] = btn
        hl.addWidget(speed_box)
        self._style_speed_buttons()

        hl.addStretch()

        # View toggle
        self._axial_btn = QPushButton("↔ Axial")
        self._cross_btn = QPushButton("⊙ Cross")
        for btn in (self._axial_btn, self._cross_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(24)
        self._axial_btn.clicked.connect(lambda: self._set_view("axial"))
        self._cross_btn.clicked.connect(lambda: self._set_view("cross"))
        hl.addWidget(self._axial_btn)
        hl.addWidget(self._cross_btn)
        self._style_view_buttons()

        # Reset
        reset_btn = QPushButton("⌂")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setFixedSize(24, 24)
        reset_btn.setToolTip("Reset pan/zoom")
        reset_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {TEXT3}; "
            f"border: 1px solid {BORDER}; border-radius: 5px; font-size: 11px; }}"
            f"QPushButton:hover {{ color: {TEXT2}; }}"
        )
        reset_btn.clicked.connect(lambda: self._canvas.reset_view())
        hl.addWidget(reset_btn)

        outer.addWidget(header)

        # ── Canvas ───────────────────────────────────────────────────────
        self._canvas = _Canvas(self._draw)
        self._canvas.set_draw_size(700, 280)
        outer.addWidget(self._canvas, 1)

        # ── Footer ───────────────────────────────────────────────────────
        footer = QFrame()
        footer.setFixedHeight(26)
        footer.setStyleSheet(
            f"background-color: rgba(0,0,0,0.2); border-top: 1px solid {BORDER}; "
            f"border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;"
        )
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(10, 0, 10, 0)

        hint = QLabel("🖱 Scroll to zoom · Drag to pan · ⌂ Reset")
        hint.setStyleSheet(f"color: #2a4060; font-size: 8.5px;")
        fl.addWidget(hint)
        fl.addStretch()

        self._telemetry_lbl = QLabel("")
        self._telemetry_lbl.setStyleSheet(
            f"color: {SUCCESS}; font-size: 8.5px; font-family: 'Consolas', monospace;"
        )
        fl.addWidget(self._telemetry_lbl)

        self._zoom_lbl = QLabel("zoom 1.00×")
        self._zoom_lbl.setStyleSheet(f"color: #2a4060; font-size: 8.5px; padding-left: 10px;")
        fl.addWidget(self._zoom_lbl)

        outer.addWidget(footer)

        # Poll zoom label (cheap; only while widget visible/animating or on demand)
        self._zoom_poll = QTimer(self)
        self._zoom_poll.setInterval(150)
        self._zoom_poll.timeout.connect(self._update_zoom_label)
        self._zoom_poll.start()

    # ── button styling helpers ──────────────────────────────────────────

    def _style_play_button(self) -> None:
        if self._playing:
            self._play_btn.setText("⏸ Pause")
            self._play_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(31,184,110,.12); color: {SUCCESS};
                    border: 1px solid {SUCCESS}; border-radius: 5px;
                    padding: 0px 10px; font-size: 11px; font-weight: 800;
                }}
            """)
        else:
            self._play_btn.setText("▶ Play")
            self._play_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(232,160,0,.12); color: {ACCENT};
                    border: 1px solid {ACCENT}; border-radius: 5px;
                    padding: 0px 10px; font-size: 11px; font-weight: 800;
                }}
            """)

    def _style_speed_buttons(self) -> None:
        for s, btn in self._speed_btns.items():
            active = (s == self._speed)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {'rgba(232,160,0,.18)' if active else 'transparent'}; "
                f"color: {ACCENT if active else TEXT3}; border: none; "
                f"padding: 0px 7px; font-size: 9px; font-weight: 700; }}"
            )

    def _style_view_buttons(self) -> None:
        for btn, key in ((self._axial_btn, "axial"), (self._cross_btn, "cross")):
            active = (self._view == key)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'rgba(232,160,0,.12)' if active else 'transparent'};
                    color: {ACCENT if active else TEXT3};
                    border: 1px solid {ACCENT if active else BORDER};
                    border-radius: 5px; padding: 0px 10px; font-size: 10px; font-weight: 700;
                }}
            """)

    # ── control handlers ─────────────────────────────────────────────────

    def _toggle_play(self) -> None:
        self._playing = not self._playing
        if self._playing:
            self._phase = 0.0
            self._rev_count = 0
            self._timer.start()
        else:
            self._timer.stop()
        self._live_badge.setVisible(self._playing)
        self._style_play_button()
        self._canvas.update()

    def _set_speed(self, s: float) -> None:
        self._speed = s
        self._style_speed_buttons()

    def _set_view(self, view: str) -> None:
        self._view = view
        self._style_view_buttons()
        w, h = (700, 280) if view == "axial" else (400, 400)
        self._canvas.set_draw_size(w, h)
        self._canvas.reset_view()

    def _update_zoom_label(self) -> None:
        self._zoom_lbl.setText(f"zoom {self._canvas.scale:.2f}×")

    # ── animation tick ───────────────────────────────────────────────────

    def _on_tick(self) -> None:
        dt = (self._TICK_MS / 1000.0) * self._speed
        rad_s = (self._N / 60.0) * 2 * math.pi
        v_ax = self._v_axial if self._v_axial > 0 else (self._P_eff * self._N / 60.0) * 0.85

        new_phase = (self._phase + rad_s * dt) % (2 * math.pi)
        if new_phase < self._phase:
            self._rev_count += 1
        self._phase = new_phase

        for p in self._particles:
            nx = p["x"] + v_ax * dt * p["jit"]
            if nx > self._L * 1.05:
                nx = -0.05 * self._L
            p["x"] = nx
            p["ang"] = p["ang"] + rad_s * dt * (0.4 + p["r"] * 0.6)
            r_new = 0.08 + abs(math.sin(p["ang"] * 1.3 + self._phase * 0.5)) * 0.72
            p["r"] = min(0.92, max(0.08, r_new))

        telemetry = f"N={self._N:.0f} rpm · v={v_ax:.3f} m/s · {self._speed:g}× speed"
        self._telemetry_lbl.setText(telemetry)

        self._canvas.update()

    def _init_particles(self) -> None:
        import random
        self._particles = [
            {
                "x": (i / self._n_particles) * self._L,
                "r": 0.08 + random.random() * 0.76,
                "ang": random.random() * 2 * math.pi,
                "sz": 2 + random.random() * 3,
                "jit": 0.85 + random.random() * 0.30,
            }
            for i in range(self._n_particles)
        ]

    # ── public API ────────────────────────────────────────────────────────

    def set_data(self, result: dict) -> None:
        """Feed the engine result dict directly — no transformation needed."""
        if not result or result.get("error"):
            return
        self._D = float(result.get("D", self._D))
        self._L = float(result.get("L", self._L))
        self._N = float(result.get("N", self._N))
        self._P_eff = float(result.get("P_eff", self._D))
        self._is_pipe = bool(result.get("is_pipe", False))

        cap = result.get("cap", {})
        self._fill = float(cap.get("fill_actual", cap.get("fill", 0.30)))
        self._v_axial = float(cap.get("v_axial", 0.0))

        hgr = result.get("hgr", {})
        self._hangers = int(hgr.get("count", 0))

        self._init_particles()
        self._canvas.update()

    # ══════════════════════════════════════════════════════════════════
    # Drawing — axial view
    # ══════════════════════════════════════════════════════════════════

    def _draw(self, p: QPainter, W: float, H: float) -> None:
        if self._view == "axial":
            self._draw_axial(p, W, H)
        else:
            self._draw_cross(p, W, H)

    def _draw_axial(self, p: QPainter, W: float, H: float) -> None:
        PL, PR, PT, PB = 50.0, 30.0, 40.0, 40.0
        iW, iH = W - PL - PR, H - PT - PB
        D_px = iH * 0.75
        cy = PT + iH / 2
        tY = cy - D_px / 2
        bY = cy + D_px / 2

        def xfrac(pos: float) -> float:
            return PL + (pos / max(self._L, 1e-6)) * iW

        # Title
        p.setPen(QColor(TEXT3))
        f = QFont(); f.setPixelSize(10); f.setBold(True)
        p.setFont(f)
        title = (
            f"{self._title.upper()} — AXIAL VIEW  "
            f"Ø{self._D*1000:.0f}mm × {self._L:g}m  fill={self._fill*100:.0f}%"
        )
        p.drawText(QRectF(0, 2, W, 14), Qt.AlignmentFlag.AlignHCenter, title)

        # Dimension lines
        p.setPen(QPen(QColor(_DRAW["dim_line"]), 1))
        p.drawLine(QPointF(PL, H - 10), QPointF(W - PR, H - 10))
        p.setPen(QColor("#5d7d99"))
        f2 = QFont(); f2.setPixelSize(8)
        p.setFont(f2)
        p.drawText(QRectF(0, H - 12, W, 12), Qt.AlignmentFlag.AlignHCenter, f"{self._L:g} m")

        # Trough shell
        grad = QLinearGradient(0, tY, 0, bY)
        grad.setColorAt(0.0, QColor(_DRAW["trough_top"]))
        grad.setColorAt(1.0, QColor(_DRAW["trough_bottom"]))
        p.setPen(QPen(QColor(_DRAW["trough_stroke"]), 2))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(QRectF(PL, tY, iW, D_px), 4, 4)

        # Fill level
        fillH = D_px * self._fill
        fillY = bY - fillH
        fgrad = QLinearGradient(0, fillY, 0, bY)
        c1 = QColor(_FLIGHT_COLOR); c1.setAlphaF(0.30)
        c2 = QColor(_FLIGHT_COLOR); c2.setAlphaF(0.80)
        fgrad.setColorAt(0.0, c1)
        fgrad.setColorAt(1.0, c2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(fgrad))
        p.drawRect(QRectF(PL + 2, fillY, iW - 4, fillH - 2))

        # Shaft centreline
        pen = QPen(QColor(PURPLE), 2, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawLine(QPointF(PL, cy), QPointF(W - PR, cy))

        # Shaft tube overlay
        shaft_col = QColor(PURPLE); shaft_col.setAlphaF(0.20)
        p.setPen(QPen(QColor(PURPLE, ), 1))
        p.setBrush(QBrush(shaft_col))
        p.drawRect(QRectF(PL, cy - D_px * 0.09, iW, D_px * 0.18))

        # Helix flights — two offset sine curves (amber)
        n_turns = max(1.0, self._L / max(self._P_eff, 0.01))
        path1 = self._make_helix_path(PL, iW, cy, D_px, n_turns, self._phase, 0.0)
        path2 = self._make_helix_path(PL, iW, cy, D_px, n_turns, self._phase, math.pi)
        p.setPen(QPen(QColor(_FLIGHT_COLOR), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path1)
        pen2 = QPen(QColor(_FLIGHT_COLOR), 1.5)
        col2 = QColor(_FLIGHT_COLOR); col2.setAlphaF(0.5)
        pen2.setColor(col2)
        p.setPen(pen2)
        p.drawPath(path2)

        # Animated particles (clipped to trough)
        p.save()
        p.setClipRect(QRectF(PL, tY, iW, D_px))
        for particle in self._particles:
            if particle["x"] < 0 or particle["x"] > self._L:
                continue
            px = xfrac(particle["x"])
            fill_band = D_px * self._fill
            y_center = bY - fill_band * 0.5
            y_spread = fill_band * 0.40
            y_off = math.sin(particle["ang"] + self._phase * 0.5) * y_spread * particle["r"]
            py = y_center + y_off
            p.setPen(Qt.PenStyle.NoPen)
            pc = QColor(_FLIGHT_COLOR); pc.setAlphaF(0.88)
            p.setBrush(QBrush(pc))
            p.drawEllipse(QPointF(px, py), particle["sz"], particle["sz"])
        p.restore()

        # Hanger bearing markers
        if self._hangers > 0:
            n_supports = self._hangers + 2  # drive + hangers + tail
            for i in range(n_supports):
                hx = PL + (i / (n_supports - 1)) * iW
                p.setPen(QPen(QColor(PRIMARY), 1.5, Qt.PenStyle.DashLine))
                p.drawLine(QPointF(hx, tY - 6), QPointF(hx, bY + 6))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(PANEL2)))
                p.drawRoundedRect(QRectF(hx - 6, tY - 10, 12, 8), 2, 2)
                p.setPen(QColor(PRIMARY))
                f3 = QFont(); f3.setPixelSize(7)
                p.setFont(f3)
                label = "Dr" if i == 0 else ("Tl" if i == n_supports - 1 else f"H{i}")
                p.drawText(QRectF(hx - 10, tY - 21, 20, 10), Qt.AlignmentFlag.AlignHCenter, label)

        # Drive / Tail labels
        p.setPen(QColor(ACCENT))
        f4 = QFont(); f4.setPixelSize(9); f4.setBold(True)
        p.setFont(f4)
        p.drawText(QRectF(PL + 5, tY - 6, 60, 12), Qt.AlignmentFlag.AlignLeft, "DRIVE")
        p.setPen(QColor(TEXT3))
        p.drawText(QRectF(W - PR - 60, tY - 6, 60, 12), Qt.AlignmentFlag.AlignRight, "TAIL")

        # Flow regime badge
        Fr = (2 * math.pi * self._N / 60) ** 2 * (self._D / 2) / 9.81 if self._N > 0 else 0.0
        name, icon, color = _classify_regime(Fr)
        badge_rect = QRectF(PL + 4, bY + 8, 130, 16)
        bcol = QColor(color); bcol.setAlphaF(0.13)
        p.setPen(QPen(QColor(color)))
        p.setBrush(QBrush(bcol))
        p.drawRoundedRect(badge_rect, 3, 3)
        p.setPen(QColor(color))
        f5 = QFont(); f5.setPixelSize(8); f5.setBold(True)
        p.setFont(f5)
        p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, f"{icon} {name.upper()} Fr={Fr:.3f}")

        # Axial velocity arrow
        v_show = self._v_axial if self._v_axial > 0 else 0.0
        p.setPen(QPen(QColor(TEAL), 2))
        p.drawLine(QPointF(PL + 20, cy), QPointF(PL + 70, cy))
        p.setPen(QColor(TEAL))
        f6 = QFont(); f6.setPixelSize(8)
        p.setFont(f6)
        p.drawText(QRectF(PL + 15, cy - 18, 60, 12), Qt.AlignmentFlag.AlignHCenter, f"v={v_show:.3f} m/s")

        # Rotation counter overlay (while playing)
        if self._playing:
            box = QRectF(W - PR - 80, PT - 2, 78, 18)
            p.setPen(QPen(QColor(SUCCESS), 1))
            bcol2 = QColor(0, 0, 0); bcol2.setAlphaF(0.55)
            p.setBrush(QBrush(bcol2))
            p.drawRect(box)
            p.setPen(QColor(SUCCESS))
            f7 = QFont(); f7.setPixelSize(9); f7.setBold(True)
            p.setFont(f7)
            deg = self._phase * 180 / math.pi
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, f"{self._rev_count} rev  {deg:.0f}°")

        # Scale bar
        p.setPen(QPen(QColor(_DRAW["dim_line"]), 2))
        p.drawLine(QPointF(W - PR - 50, H - 22), QPointF(W - PR, H - 22))
        p.setPen(QColor("#5d7d99"))
        p.setFont(f2)
        scale_txt = f"{self._L*1000:.0f} mm" if self._L < 2 else f"{self._L:.1f} m"
        p.drawText(QRectF(W - PR - 60, H - 32, 60, 12), Qt.AlignmentFlag.AlignHCenter, scale_txt)

    def _make_helix_path(
        self, PL: float, iW: float, cy: float, D_px: float,
        n_turns: float, phase: float, phase_off: float,
    ) -> QPainterPath:
        path = QPainterPath()
        n_pts = max(2, math.ceil(n_turns * 16))
        for i in range(n_pts + 1):
            t = i / n_pts
            x = PL + t * iW
            ph = t * n_turns * 2 * math.pi + phase + phase_off
            y_off = math.sin(ph) * (D_px / 2 - D_px * 0.12)
            y = cy + y_off
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        return path

    # ══════════════════════════════════════════════════════════════════
    # Drawing — cross-section view
    # ══════════════════════════════════════════════════════════════════

    def _draw_cross(self, p: QPainter, W: float, H: float) -> None:
        R = min(W, H) * 0.36
        cx, cy = W / 2, H / 2
        r_shaft = R * 0.18
        r_flight = R * 0.94
        t_wall = max(5.0, R * 0.035)

        # Title
        p.setPen(QColor(TEXT3))
        f = QFont(); f.setPixelSize(10); f.setBold(True)
        p.setFont(f)
        title = f"CROSS SECTION — Ø{self._D*1000:.0f}mm  fill={self._fill*100:.0f}%"
        p.drawText(QRectF(0, 4, W, 14), Qt.AlignmentFlag.AlignHCenter, title)

        # Trough wall + bore
        p.setPen(QPen(QColor("#4a6080"), t_wall))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), R + t_wall / 2, R + t_wall / 2)

        radial = QRadialGradient(cx, cy, R)
        radial.setColorAt(0.0, QColor(_DRAW["trough_top"]))
        radial.setColorAt(1.0, QColor("#061420"))
        p.setPen(QPen(QColor(_DRAW["trough_stroke"]), 1.5))
        p.setBrush(QBrush(radial))
        p.drawEllipse(QPointF(cx, cy), R, R)

        # Fill chord (pie-slice at bottom)
        fill_angle_deg = min(180.0, self._fill * 1.4 * 180.0)
        start_deg = 90 - fill_angle_deg / 2
        pie_rect = QRectF(cx - R, cy - R, 2 * R, 2 * R)
        fcol = QColor(_FLIGHT_COLOR); fcol.setAlphaF(0.70)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(fcol))
        # Qt angles: 0 = 3 o'clock, positive = counter-clockwise, in 1/16 deg
        p.drawPie(pie_rect, int((90 - start_deg - fill_angle_deg) * -16), int(fill_angle_deg * 16))

        # Shaft + rotating flight spokes
        p.save()
        p.translate(cx, cy)
        p.rotate(self._phase * 180 / math.pi)
        p.setPen(QPen(QColor(ACCENT), 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(0, 0), r_flight, r_flight)
        for k in range(4):
            ang = k * math.pi / 2
            x1, y1 = r_shaft * math.cos(ang), r_shaft * math.sin(ang)
            x2, y2 = r_flight * math.cos(ang), r_flight * math.sin(ang)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        p.restore()

        # Shaft hub
        hub_grad = QRadialGradient(cx, cy, r_shaft)
        hub_grad.setColorAt(0.0, QColor(_DRAW["shaft_metal_a"]))
        hub_grad.setColorAt(1.0, QColor(_DRAW["shaft_metal_b"]))
        p.setPen(QPen(QColor(PURPLE), 2))
        p.setBrush(QBrush(hub_grad))
        p.drawEllipse(QPointF(cx, cy), r_shaft, r_shaft)
        p.setPen(QPen(QColor(PURPLE), 1.8))
        ex = cx + r_shaft * math.cos(self._phase)
        ey = cy + r_shaft * math.sin(self._phase)
        p.drawLine(QPointF(cx, cy), QPointF(ex, ey))

        # Static particle dots within fill arc (simple decorative fill)
        for i in range(10):
            frac = i / 9
            ang = math.radians(start_deg) + math.radians(fill_angle_deg) * frac
            rad = r_shaft + (R - r_shaft) * 0.4
            dx = cx + rad * math.cos(ang)
            dy = cy + rad * math.sin(ang)
            sz = 2 + (i % 3)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(_FLIGHT_COLOR)))
            p.drawEllipse(QPointF(dx, dy), sz, sz)

        # Flow regime badge (bottom-left)
        Fr = (2 * math.pi * self._N / 60) ** 2 * (self._D / 2) / 9.81 if self._N > 0 else 0.0
        name, icon, color = _classify_regime(Fr)
        badge_rect = QRectF(8, H - 28, 160, 20)
        bcol = QColor(color); bcol.setAlphaF(0.13)
        p.setPen(QPen(QColor(color)))
        p.setBrush(QBrush(bcol))
        p.drawRoundedRect(badge_rect, 4, 4)
        p.setPen(QColor(color))
        f2 = QFont(); f2.setPixelSize(9); f2.setBold(True)
        p.setFont(f2)
        p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, f"{icon} {name}  Fr={Fr:.3f}")

        # Wall thickness + radius annotations
        p.setPen(QPen(QColor(PRIMARY), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(cx, cy), QPointF(cx - R - t_wall - 8, cy))
        p.setPen(QColor(PRIMARY))
        f3 = QFont(); f3.setPixelSize(8)
        p.setFont(f3)
        t_mm = max(3, round(t_wall / R * self._D * 500)) if R > 0 else 3
        p.drawText(QRectF(cx - R - t_wall - 70, cy - 14, 60, 12),
                   Qt.AlignmentFlag.AlignRight, f"t≈{t_mm}mm")

        p.setPen(QPen(QColor(ACCENT), 1))
        p.drawLine(QPointF(cx, cy - 6), QPointF(cx + r_flight, cy - 6))
        p.setPen(QColor(ACCENT))
        p.drawText(QRectF(cx, cy - 22, r_flight, 12),
                   Qt.AlignmentFlag.AlignHCenter, f"R={self._D/2*1000:.0f}mm")

        # Rotation indicator (bottom-right) while playing
        if self._playing:
            a_r = 18
            a_cx, a_cy = W - 28, H - 26
            p.setPen(QPen(QColor(BORDER), 3))
            p.drawEllipse(QPointF(a_cx, a_cy), a_r, a_r)
            start_ang = -90
            span = int(self._phase * 180 / math.pi)
            p.setPen(QPen(QColor(SUCCESS), 3))
            p.drawArc(QRectF(a_cx - a_r, a_cy - a_r, 2 * a_r, 2 * a_r),
                      start_ang * 16, span * 16)
            p.setPen(QColor(SUCCESS))
            f4 = QFont(); f4.setPixelSize(7); f4.setBold(True)
            p.setFont(f4)
            p.drawText(QRectF(a_cx - a_r, a_cy - 6, 2 * a_r, 12),
                       Qt.AlignmentFlag.AlignCenter, str(self._rev_count))