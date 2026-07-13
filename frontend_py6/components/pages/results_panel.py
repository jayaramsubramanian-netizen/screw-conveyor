"""
components/pages/results_panel.py — VECTRIX™ Results tab for col3
═══════════════════════════════════════════════════════════════════════════
All cards read directly from the engine result dict keys.
No key transformation — names match engine output exactly.

Cards
-----
WarnsBanner     crit / adv / opt warning pills
CapacityCard    Qt, Qv, fill_actual, eta_L, regime
PowerCard       Pe / Pm / Pi / Pf bar decomposition + motor
ShaftCard       auto sel_mm, sf, tau  |  pipe option
BearingCard     L10 vs target, C/P ratio
GearboxCard     Tn_derated vs Ts, agma_sf
EfficiencyCard  score gauge, kWh/t, cap_util, sug_geom
CostCard        steel grade, mass, total USD

ResultsPanel    QScrollArea containing all cards in a VBox
                Public method: set_data(result: dict)
"""

from __future__ import annotations

from typing import Optional, Any
import math

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush

from theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, ACCENT, PURPLE, TEAL,
)
from components.screw_viz import ScrewViz2D
from components.model_number import generate_model_number


# ── formatting helpers ────────────────────────────────────────────────────

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


def _ok_col(ok: Optional[bool]) -> str:
    if ok is True:
        return SUCCESS
    if ok is False:
        return DANGER
    return TEXT3


# ── shared QSS ───────────────────────────────────────────────────────────

_CARD_QSS = f"""
    QFrame#card {{
        background-color: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 8px;
    }}
"""

_HDR_LABEL_QSS = (
    f"color: {TEXT3}; font-size: 9.5px; font-weight: 700; "
    f"letter-spacing: 1px; text-transform: uppercase;"
)

_KEY_QSS   = f"color: {TEXT3}; font-size: 10.5px;"
_VAL_QSS   = f"color: {TEXT};  font-size: 11px; font-family: 'Consolas', monospace; font-weight: 600;"
_BADGE_BASE = (
    "border-radius: 4px; padding: 1px 7px; "
    "font-size: 9px; font-weight: 700;"
)


# ── primitive widgets ─────────────────────────────────────────────────────

def _divider() -> QFrame:
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet(f"background-color: {BORDER};")
    return f


def _badge(text: str, color: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"background-color: {color}22; color: {color}; "
        f"border: 1px solid {color}55; {_BADGE_BASE}"
    )
    lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return lbl


def _ok_badge(ok: bool) -> QLabel:
    return _badge("PASS" if ok else "FAIL", SUCCESS if ok else DANGER)


def _kv_row(key: str, val: str, val_color: str = TEXT) -> QWidget:
    """Single label: value row."""
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(12, 2, 12, 2)
    lay.setSpacing(0)
    k = QLabel(key)
    k.setStyleSheet(_KEY_QSS)
    v = QLabel(val)
    v.setStyleSheet(
        f"color: {val_color}; font-size: 11px; "
        f"font-family: 'Consolas', monospace; font-weight: 600;"
    )
    v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lay.addWidget(k)
    lay.addStretch()
    lay.addWidget(v)
    return w


def _kv_row_badge(key: str, val: str, ok: bool) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(12, 2, 12, 2)
    lay.setSpacing(6)
    k = QLabel(key)
    k.setStyleSheet(_KEY_QSS)
    b = _ok_badge(ok)
    v = QLabel(val)
    v.setStyleSheet(
        f"color: {_ok_col(ok)}; font-size: 11px; "
        f"font-family: 'Consolas', monospace; font-weight: 600;"
    )
    lay.addWidget(k)
    lay.addStretch()
    lay.addWidget(b)
    lay.addWidget(v)
    return w


# ── Card base ─────────────────────────────────────────────────────────────

class _Card(QFrame):
    """Base card — title bar + body layout."""

    def __init__(
        self,
        icon: str,
        title: str,
        accent: str = TEXT3,
        badge: Optional[QWidget] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(_CARD_QSS)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 10)
        outer.setSpacing(0)

        # Header row
        hdr = QWidget()
        hdr.setFixedHeight(34)
        hdr.setStyleSheet(
            f"background-color: {PANEL2}; "
            f"border-top-left-radius: 8px; border-top-right-radius: 8px; "
            f"border-bottom: 1px solid {BORDER};"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(12, 0, 12, 0)
        hdr_lay.setSpacing(7)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 13px;")
        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(
            f"color: {accent}; font-size: 9.5px; font-weight: 700; letter-spacing: 1px;"
        )
        hdr_lay.addWidget(icon_lbl)
        hdr_lay.addWidget(title_lbl)
        hdr_lay.addStretch()
        if badge:
            hdr_lay.addWidget(badge)

        outer.addWidget(hdr)

        # Body
        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 6, 0, 0)
        self._body.setSpacing(2)
        outer.addLayout(self._body)

    def _add(self, widget: QWidget) -> None:
        self._body.addWidget(widget)

    def _add_divider(self) -> None:
        self._body.addWidget(_divider())

    def _add_kv(self, key: str, val: str, color: str = TEXT) -> None:
        self._add(_kv_row(key, val, color))

    def _add_kv_badge(self, key: str, val: str, ok: bool) -> None:
        self._add(_kv_row_badge(key, val, ok))


# ══════════════════════════════════════════════════════════════════════════
# 0. ModelNumberBadge
# ══════════════════════════════════════════════════════════════════════════

class ModelNumberBadge(QFrame):
    """
    VECTOMEC™ model number strip — top of the Results tab, above the
    warnings banner. Shows the full generated string plus a segment
    breakdown row underneath.

    See components/model_number.py for the derivation logic and the
    two flagged gaps (Food Grade / Process / Live Bottom Feeder series
    can't be derived from conveyor-only inputs; drive code always
    resolves to Gearmotor until VFD is wired into EngineInput).
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: rgba(232,160,0,.07); "
            f"border: 1px solid rgba(232,160,0,.3); border-radius: 8px;"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(8)

        icon = QLabel("🔩")
        icon.setStyleSheet("font-size: 13px;")
        top.addWidget(icon)

        self._model_lbl = QLabel("VM-—-—-—-—-—-—")
        self._model_lbl.setStyleSheet(
            f"color: {ACCENT}; font-size: 15px; font-weight: 800; "
            f"font-family: 'Consolas', monospace; letter-spacing: .5px;"
        )
        top.addWidget(self._model_lbl)
        top.addStretch()

        self._series_lbl = QLabel("")
        self._series_lbl.setStyleSheet(
            f"color: {TEXT3}; font-size: 10px; font-weight: 600;"
        )
        top.addWidget(self._series_lbl)

        lay.addLayout(top)

        self._breakdown_lbl = QLabel("")
        self._breakdown_lbl.setStyleSheet(
            f"color: {MUTED}; font-size: 9px; font-family: 'Consolas', monospace;"
        )
        self._breakdown_lbl.setWordWrap(True)
        lay.addWidget(self._breakdown_lbl)

    def set_data(self, result: dict) -> None:
        if not result or result.get("error"):
            return
        mn = generate_model_number(result)

        self._model_lbl.setText(mn.full_string)
        self._series_lbl.setText(mn.series_label.upper())
        self._breakdown_lbl.setText(
            f"{mn.series_code}=Series({mn.series_label})  ·  "
            f"{mn.diameter_mm}=Ø mm  ·  {mn.length_dm}=Length dm  ·  "
            f"{mn.pitch_code}=Pitch({mn.pitch_label})  ·  "
            f"{mn.material_code}=Trough  ·  {mn.drive_code}=Drive(Gearmotor)"
        )


# ══════════════════════════════════════════════════════════════════════════
# 1. WarnsBanner
# ══════════════════════════════════════════════════════════════════════════

class WarnsBanner(QWidget):
    """
    Collapsible warning / advisory / optimisation pills.
    Hidden entirely when warns is empty.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 6)
        self._layout.setSpacing(3)
        self.setVisible(False)

    def set_data(self, warns: dict) -> None:
        # Clear old
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()

        cfg = {
            "crit": ("❌", DANGER,  "CRITICAL"),
            "adv":  ("⚠️",  WARNING, "ADVISORY"),
            "opt":  ("💡", PRIMARY, "OPTIMISE"),
        }
        any_warn = False
        for key, (icon, color, label) in cfg.items():
            for msg in (warns.get(key) or []):
                any_warn = True
                row = QWidget()
                row.setStyleSheet(
                    f"background-color: {color}14; "
                    f"border: 1px solid {color}44; border-radius: 5px;"
                )
                lay = QHBoxLayout(row)
                lay.setContentsMargins(8, 5, 8, 5)
                lay.setSpacing(7)

                tag = QLabel(f"{icon} {label}")
                tag.setStyleSheet(
                    f"color: {color}; font-size: 9px; font-weight: 700;"
                )
                tag.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

                txt = QLabel(msg)
                txt.setStyleSheet(f"color: {color}; font-size: 10px;")
                txt.setWordWrap(True)

                lay.addWidget(tag)
                lay.addWidget(txt, 1)
                self._layout.addWidget(row)

        self.setVisible(any_warn)


# ══════════════════════════════════════════════════════════════════════════
# 2. CapacityCard
# ══════════════════════════════════════════════════════════════════════════

class CapacityCard(_Card):

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("📊", "Capacity", accent=PRIMARY, parent=parent)
        # Headline row
        self._qt_lbl = QLabel("—")
        self._qt_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 22px; font-weight: 800; "
            f"font-family: 'Consolas', monospace;"
        )
        self._qt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._body.addWidget(self._qt_lbl)
        self._body.addWidget(_divider())
        # KV rows — placeholders, populated in set_data
        self._rows: dict[str, QWidget] = {}
        for key in ("Required", "Volumetric", "Fill fraction",
                    "η_L load eff.", "λ used", "Slip S",
                    "v_axial", "Regime"):
            w = _kv_row(key, "—")
            self._rows[key] = w
            self._body.addWidget(w)

    def set_data(self, r: dict) -> None:
        cap   = r.get("cap", {})
        Qt    = cap.get("Qt", 0.0)
        ok    = cap.get("ok", False)
        req   = cap.get("req", 0.0)
        col   = SUCCESS if ok else DANGER

        self._qt_lbl.setText(f"{Qt:.1f} t/h")
        self._qt_lbl.setStyleSheet(
            f"color: {col}; font-size: 22px; font-weight: 800; "
            f"font-family: 'Consolas', monospace;"
        )

        # Rebuild cleanly each call
        for key, w in self._rows.items():
            self._body.removeWidget(w)
            w.deleteLater()
        self._rows.clear()

        rows = [
            ("Required",     f"{req:.1f} t/h",                     TEXT3),
            ("Volumetric",   f"{_f(cap.get('Qv'),1)} m³/h",        TEXT),
            ("Fill fraction",f"{_f(cap.get('fill_actual',0)*100,1)} %", TEXT),
            ("η_L load eff.",f"{_f(cap.get('eta_L',0)*100,1)} %",  TEXT),
            ("λ used",       f"{_f(cap.get('lam_used',0),3)}",      TEXT),
            ("Slip S",       f"{_f(cap.get('slip_S',0),3)}",        TEXT),
            ("v_axial",      f"{_f(cap.get('v_axial',0),4)} m/s",   TEXT),
            ("Regime",       r.get("regime", {}).get("name", "—"),   ACCENT),
        ]
        for key, val, color in rows:
            w = _kv_row(key, val, color)
            self._rows[key] = w
            self._body.addWidget(w)


# ══════════════════════════════════════════════════════════════════════════
# 3. PowerCard
# ══════════════════════════════════════════════════════════════════════════

class PowerCard(_Card):

    _BAR_COLORS = [PRIMARY, ACCENT, WARNING, TEAL]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("⚡", "Power", accent=ACCENT, parent=parent)
        # Bar chart widget
        self._bar = _PowerBar()
        self._body.addWidget(self._bar)
        self._body.addWidget(_divider())
        self._rows: dict[str, QWidget] = {}
        for key in ("Pe friction", "Pm material", "Pi incline",
                    "Pf losses", "Ps shaft", "Pt installed", "Motor"):
            w = _kv_row(key, "—")
            self._rows[key] = w
            self._body.addWidget(w)

    def set_data(self, r: dict) -> None:
        pwr = r.get("pwr", {})
        Pe  = pwr.get("Pe", 0.0)
        Pm  = pwr.get("Pm", 0.0)
        Pi  = pwr.get("Pi", 0.0)
        Pf  = pwr.get("Pf", 0.0)
        Ps  = pwr.get("Ps", 0.0)
        Pt  = pwr.get("Pt", 0.0)
        mot = pwr.get("motor", 0.0)

        self._bar.set_values([
            ("Pe", Pe, PRIMARY),
            ("Pm", Pm, ACCENT),
            ("Pi", Pi, WARNING),
            ("Pf", Pf, TEAL),
        ])

        for key, w in self._rows.items():
            self._body.removeWidget(w)
            w.deleteLater()
        self._rows.clear()

        rows = [
            ("Pe friction",   f"{Pe:.3f} kW",   TEXT),
            ("Pm material",   f"{Pm:.3f} kW",   TEXT),
            ("Pi incline",    f"{Pi:.3f} kW",   TEXT),
            ("Pf losses",     f"{Pf:.3f} kW",   MUTED),
            ("Ps shaft",      f"{Ps:.3f} kW",   TEXT),
            ("Pt installed",  f"{Pt:.3f} kW",   ACCENT),
            ("Motor",         f"{mot:.0f} kW",  SUCCESS),
        ]
        for key, val, color in rows:
            w = _kv_row(key, val, color)
            self._rows[key] = w
            self._body.addWidget(w)


class _PowerBar(QWidget):
    """Stacked horizontal bar showing Pe/Pm/Pi/Pf proportions."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self._segments: list[tuple[str, float, str]] = []

    def set_values(self, segments: list[tuple[str, float, str]]) -> None:
        self._segments = segments
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        total = sum(v for _, v, _ in self._segments) or 1.0
        x = 0
        for i, (label, val, color) in enumerate(self._segments):
            w = int((val / total) * W)
            if i == len(self._segments) - 1:
                w = W - x  # fill remainder
            p.setBrush(QColor(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(x, 0, w, H)
            # label
            if w > 24:
                p.setPen(QColor("#ffffff"))
                f = QFont(); f.setPixelSize(9); f.setBold(True)
                p.setFont(f)
                p.drawText(x + 4, 0, w - 4, H, Qt.AlignmentFlag.AlignVCenter, label)
            x += w
        p.end()


# ══════════════════════════════════════════════════════════════════════════
# 4. ShaftCard
# ══════════════════════════════════════════════════════════════════════════

class ShaftCard(_Card):

    def __init__(self, parent: Optional[QWidget] = None):
        self._ok_badge_ref = _ok_badge(True)
        super().__init__("🔩", "Shaft", accent=PURPLE,
                         badge=self._ok_badge_ref, parent=parent)
        self._rows: dict[str, QWidget] = {}

    def set_data(self, r: dict) -> None:
        tor  = r.get("tor", {})
        sa   = r.get("shaft_auto", {})
        mode = r.get("shaft_mode", "auto")
        ok   = tor.get("shOk", False)

        # Update badge text/style in place (header ref kept at construction)
        self._ok_badge_ref.setText("PASS" if ok else "FAIL")
        self._ok_badge_ref.setStyleSheet(
            f"background-color: {SUCCESS if ok else DANGER}22; "
            f"color: {SUCCESS if ok else DANGER}; "
            f"border: 1px solid {SUCCESS if ok else DANGER}55; {_BADGE_BASE}"
        )

        for w in self._rows.values():
            self._body.removeWidget(w)
            w.deleteLater()
        self._rows.clear()

        sf     = sa.get("sf", 0.0)
        sf_col = SUCCESS if sf >= 2.0 else (WARNING if sf >= 1.5 else DANGER)
        tau    = tor.get("tau", 0.0)
        od     = tor.get("eff_od_mm", sa.get("sel_mm", 0))
        id_mm  = tor.get("eff_id_mm", 0.0)

        rows = [
            ("Mode",        "Auto (VECTRIX™)" if mode == "auto" else "Manual override", TEXT3),
            ("Required OD", f"{_f(sa.get('req_mm',0),1)} mm",  TEXT),
            ("Selected OD", f"{od:.0f} mm",                     TEXT),
        ]
        if id_mm > 0:
            rows.append(("Shaft ID", f"{id_mm:.0f} mm (pipe)", TEAL))
        rows += [
            ("τ startup",   f"{_f(tau,2)} MPa",                 _ok_col(ok)),
            ("Safety factor", f"{_f(sf,2)} ×",                  sf_col),
            ("Tr running",  f"{_f(tor.get('Tr',0),0)} Nm",      TEXT),
            ("Ts startup",  f"{_f(tor.get('Ts',0),0)} Nm",      TEXT),
        ]

        for key, val, color in rows:
            w = _kv_row(key, val, color)
            self._rows[key] = w
            self._body.addWidget(w)

        # Pipe option suggestion
        pipe_opt = sa.get("pipe_opt")
        if pipe_opt and pipe_opt.get("ok"):
            self._body.addWidget(_divider())
            tip = QLabel(
                f"💡 Pipe option: OD {pipe_opt['od_mm']} / ID {pipe_opt['id_mm']} mm "
                f"— saves {pipe_opt['wt_save_pct']}% weight"
            )
            tip.setStyleSheet(
                f"color: {TEAL}; font-size: 9.5px; padding: 4px 12px; "
                f"background: {TEAL}11; border-radius: 4px;"
            )
            tip.setWordWrap(True)
            self._body.addWidget(tip)
            self._rows["_pipe_tip"] = tip


# ══════════════════════════════════════════════════════════════════════════
# 5. BearingCard
# ══════════════════════════════════════════════════════════════════════════

class BearingCard(_Card):

    def __init__(self, parent: Optional[QWidget] = None):
        self._ok_badge_ref = _ok_badge(True)
        super().__init__("⭕", "Bearing", accent=PRIMARY,
                         badge=self._ok_badge_ref, parent=parent)
        self._rows: dict[str, QWidget] = {}

    def set_data(self, r: dict) -> None:
        brg = r.get("brg_r", {})
        hgr = r.get("hgr", {})
        ok  = brg.get("ok", False)

        self._ok_badge_ref.setText("PASS" if ok else "FAIL")
        self._ok_badge_ref.setStyleSheet(
            f"background-color: {SUCCESS if ok else DANGER}22; "
            f"color: {SUCCESS if ok else DANGER}; "
            f"border: 1px solid {SUCCESS if ok else DANGER}55; {_BADGE_BASE}"
        )

        for w in self._rows.values():
            self._body.removeWidget(w)
            w.deleteLater()
        self._rows.clear()

        L10     = brg.get("L10", 0.0)
        L10_tgt = brg.get("L10_target", 20000)
        C       = brg.get("C", 0.0)
        load    = brg.get("load", 0.0)
        cp      = C / load if load > 0 else 0.0
        adequate = brg.get("adequate")

        rows = [
            ("Bearing",    brg.get("name", "—"),                    TEXT),
            ("C dynamic",  f"{_f(C,1)} kN",                         TEXT),
            ("Load",       f"{_f(load,2)} kN",                      TEXT),
            ("C/P ratio",  f"{_f(cp,2)}",                           TEXT),
            ("L10 life",   f"{_fi(L10)} h",                         _ok_col(ok)),
            ("L10 target", f"{_fi(L10_tgt)} h",                     TEXT3),
            ("Hangers",    f"{hgr.get('count',0)} @ {_f(hgr.get('span',0),1)} m", TEXT),
        ]
        for key, val, color in rows:
            w = _kv_row(key, val, color)
            self._rows[key] = w
            self._body.addWidget(w)

        if adequate:
            self._body.addWidget(_divider())
            tip = QLabel(f"💡 Upgrade to {adequate} to meet L10 target")
            tip.setStyleSheet(
                f"color: {WARNING}; font-size: 9.5px; padding: 4px 12px;"
            )
            self._body.addWidget(tip)
            self._rows["_adequate_tip"] = tip


# ══════════════════════════════════════════════════════════════════════════
# 6. GearboxCard
# ══════════════════════════════════════════════════════════════════════════

class GearboxCard(_Card):

    def __init__(self, parent: Optional[QWidget] = None):
        self._ok_badge_ref = _ok_badge(True)
        super().__init__("⚙️", "Gearbox", accent=TEAL,
                         badge=self._ok_badge_ref, parent=parent)
        self._rows: dict[str, QWidget] = {}

    def set_data(self, r: dict) -> None:
        gbx = r.get("gbx_r", {})
        t_ok = gbx.get("tOk", False)
        p_ok = gbx.get("pOk", False)
        ok   = t_ok and p_ok

        self._ok_badge_ref.setText("PASS" if ok else "FAIL")
        self._ok_badge_ref.setStyleSheet(
            f"background-color: {SUCCESS if ok else DANGER}22; "
            f"color: {SUCCESS if ok else DANGER}; "
            f"border: 1px solid {SUCCESS if ok else DANGER}55; {_BADGE_BASE}"
        )

        for w in self._rows.values():
            self._body.removeWidget(w)
            w.deleteLater()
        self._rows.clear()

        rows = [
            ("Model",         gbx.get("model", "—"),                  TEXT),
            ("Rated Tn",      f"{_fi(gbx.get('Tn',0))} Nm",          TEXT),
            ("Derated Tn",    f"{_fi(gbx.get('Tn_derated',0))} Nm",   TEXT),
            ("AGMA SF",       f"{_f(gbx.get('agma_sf',1.0),2)}",      TEXT),
            ("Startup Ts",    f"{_fi(r.get('tor',{}).get('Ts',0))} Nm", _ok_col(t_ok)),
            ("Torque check",  "PASS" if t_ok else "FAIL",              _ok_col(t_ok)),
            ("Power check",   "PASS" if p_ok else "FAIL",              _ok_col(p_ok)),
        ]
        for key, val, color in rows:
            w = _kv_row(key, val, color)
            self._rows[key] = w
            self._body.addWidget(w)


# ══════════════════════════════════════════════════════════════════════════
# 7. EfficiencyCard   (score gauge + kWh/t + sug_geom)
# ══════════════════════════════════════════════════════════════════════════

class EfficiencyCard(_Card):

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("📈", "Design Efficiency", accent=PURPLE, parent=parent)
        self._gauge = _ScoreGauge()
        self._gauge.setFixedHeight(80)
        self._body.addWidget(self._gauge)
        self._body.addWidget(_divider())
        self._rows: dict[str, QWidget] = {}

    def set_data(self, r: dict) -> None:
        eff = r.get("eff", {})
        score   = int(eff.get("score", 0))
        kWh_t   = eff.get("kWh_t", 0.0)
        cap_u   = eff.get("cap_util", 0.0)
        sug     = eff.get("sug_geom", {})
        vib     = r.get("vri_label", "—")
        vib_score = r.get("vibration_risk", 0.0)

        self._gauge.set_score(score)

        for w in self._rows.values():
            self._body.removeWidget(w)
            w.deleteLater()
        self._rows.clear()

        kWh_col = SUCCESS if kWh_t < 1 else (WARNING if kWh_t < 2 else DANGER)
        cap_col = SUCCESS if cap_u < 95 else (WARNING if cap_u < 110 else DANGER)
        vib_col = SUCCESS if vib == "Low" else (WARNING if vib == "Moderate" else DANGER)

        rows = [
            ("Energy",       f"{_f(kWh_t,3)} kWh/t",   kWh_col),
            ("Utilisation",  f"{_f(cap_u,1)} %",         cap_col),
            ("Fill",         f"{_f(eff.get('fill_pct',0),1)} %", TEXT),
            ("Vibration",    f"{vib}  ({_f(vib_score,1)})", vib_col),
        ]
        if sug.get("D_next_sm"):
            rows.append((
                "Smaller D option",
                f"Ø{sug['D_next_sm']} mm", TEAL,
            ))
        if sug.get("N_opt"):
            rows.append((
                "Suggested N",
                f"{sug['N_opt']} RPM", TEAL,
            ))

        for key, val, color in rows:
            w = _kv_row(key, val, color)
            self._rows[key] = w
            self._body.addWidget(w)


class _ScoreGauge(QWidget):
    """Arc gauge — score 0–100."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._score = 0

    def set_score(self, score: int) -> None:
        self._score = max(0, min(100, score))
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cx, cy = W // 2, H - 10
        r = min(cx, cy) - 10

        # Background arc
        p.setPen(QPen(QColor(BORDER), 8, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawArc(cx - r, cy - r, r * 2, r * 2, 0 * 16, 180 * 16)

        # Score arc
        s = self._score
        col = SUCCESS if s >= 70 else (WARNING if s >= 45 else DANGER)
        p.setPen(QPen(QColor(col), 8, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        span = int(s / 100 * 180)
        p.drawArc(cx - r, cy - r, r * 2, r * 2, 180 * 16, -span * 16)

        # Score text
        p.setPen(QColor(col))
        f = QFont(); f.setPixelSize(22); f.setBold(True)
        p.setFont(f)
        p.drawText(0, 0, W, H - 14,
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                   str(s))
        p.setPen(QColor(TEXT3))
        f2 = QFont(); f2.setPixelSize(9)
        p.setFont(f2)
        p.drawText(0, H - 15, W, 14,
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                   "/ 100")
        p.end()


# ══════════════════════════════════════════════════════════════════════════
# 8. CostCard
# ══════════════════════════════════════════════════════════════════════════

class CostCard(_Card):

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("💰", "Cost Estimate", accent=ACCENT, parent=parent)
        self._rows: dict[str, QWidget] = {}

    def set_data(self, r: dict) -> None:
        cost = r.get("cost", {})

        for w in self._rows.values():
            self._body.removeWidget(w)
            w.deleteLater()
        self._rows.clear()

        rows = [
            ("Steel grade",  cost.get("steel", "—"),            TEXT),
            ("Unit cost",    f"$ {_f(cost.get('uc',0),2)}/kg",  TEXT),
            ("Steel mass",   f"{_fi(cost.get('mass',0))} kg",    TEXT),
            ("Est. total",   f"$ {_fi(cost.get('total',0))}",    ACCENT),
        ]
        for key, val, color in rows:
            w = _kv_row(key, val, color)
            self._rows[key] = w
            self._body.addWidget(w)

        self._body.addWidget(_divider())
        note = QLabel("Indicative fabrication cost — material + labour estimate only")
        note.setStyleSheet(f"color: {MUTED}; font-size: 9px; padding: 3px 12px;")
        note.setWordWrap(True)
        self._body.addWidget(note)
        self._rows["_note"] = note


# ══════════════════════════════════════════════════════════════════════════
# ResultsPanel — scrollable container for all cards
# ══════════════════════════════════════════════════════════════════════════

class ResultsPanel(QWidget):
    """
    col3 Results tab content.

    set_data(result: dict)  — called by ShellWindow.run_calculation()
                              distributes to all cards in one pass.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

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
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(10, 8, 10, 10)
        self._body_layout.setSpacing(8)

        # Model number (top, full width)
        self._model_badge = ModelNumberBadge()
        self._body_layout.addWidget(self._model_badge)

        # Warnings banner (top, full width)
        self._warns = WarnsBanner()
        self._body_layout.addWidget(self._warns)

        # 2-column grid for cards
        grid = QWidget()
        self._grid = QGridLayout(grid)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(8)
        self._body_layout.addWidget(grid)

        # Instantiate all cards
        self._cap  = CapacityCard()
        self._pwr  = PowerCard()
        self._sh   = ShaftCard()
        self._brg  = BearingCard()
        self._gbx  = GearboxCard()
        self._eff  = EfficiencyCard()
        self._cost = CostCard()

        # Layout: 2 columns
        #  row 0: cap  | pwr
        #  row 1: sh   | brg
        #  row 2: gbx  | eff
        #  row 3: cost (full width)
        cards_grid = [
            (self._cap,  0, 0), (self._pwr,  0, 1),
            (self._sh,   1, 0), (self._brg,  1, 1),
            (self._gbx,  2, 0), (self._eff,  2, 1),
        ]
        for card, row, col in cards_grid:
            self._grid.addWidget(card, row, col)
        self._grid.addWidget(self._cost, 3, 0, 1, 2)   # full width

        self._grid.setColumnStretch(0, 1)
        self._grid.setColumnStretch(1, 1)

        # ── 2D Visualizer (full width, below the card grid) ──────────────
        self._viz = ScrewViz2D(title="Screw Conveyor")
        self._viz.setFixedHeight(360)
        self._body_layout.addWidget(self._viz)

        self._body_layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)

    def set_data(self, result: dict) -> None:
        """
        Distribute engine result dict to all cards.
        Called from ShellWindow.run_calculation() after fetch_design() succeeds.
        """
        if not result or result.get("error"):
            return

        self._model_badge.set_data(result)
        self._warns.set_data(result.get("warns", {}))
        self._cap.set_data(result)
        self._pwr.set_data(result)
        self._sh.set_data(result)
        self._brg.set_data(result)
        self._gbx.set_data(result)
        self._eff.set_data(result)
        self._cost.set_data(result)
        self._viz.set_data(result)