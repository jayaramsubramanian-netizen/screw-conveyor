"""
modules/conveyor/detail_panels.py — Checks / Wear & Life / Structural tabs
═══════════════════════════════════════════════════════════════════════════
Three of the conveyor's seven tabs were Placeholders after the step-4
restructure: Checks, Wear & Life, Structural (Materials is built separately
against the database). All three render data already present in the
/calculate result — none computes physics here.

Source: the corresponding sections of CalcPage.tsx. In the React app these
are scrollable sections of one long Results view; the PySide6 port splits
them into tabs, so each becomes its own panel fed the same `design` result.

  ChecksPanel      the 11-row engineering-checks table (the `checks` array)
  WearPanel        bearing + wear-life rows (the Wear tab)
  StructuralPanel  the StructuralModule — trough/cover/flange/bolt/weld/
                   hanger sizing, now reading result["structural"] from the
                   backend calc_structural() rather than recomputing
                   client-side. This is the frontend half of
                   STRUCTURAL_REVIEW_NOTE.md option 1: physics moved to the
                   backend, the panel only displays it.

set_data(result) on each panel takes the whole /calculate dict and reads
its own slice. A missing key degrades to "—" via fmt(), the same failure
mode as the process modules.
"""

from __future__ import annotations

from typing import Optional, Any, TypeVar

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
)
from PySide6.QtCore import Qt

from core.theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    ACCENT, PRIMARY, SUCCESS, WARNING, DANGER, TEAL,
)

#: Preserves a widget's concrete type through _Card.add — a bare QWidget
#: return widens every `self._r_x = card.add(_Row(...))` and makes the
#: subsequent .set() call a static-analysis error.
_W = TypeVar("_W", bound=QWidget)


def _fmt(val: Any, dp: int = 2, fallback: str = "—") -> str:
    if val is None:
        return fallback
    try:
        return f"{float(val):.{dp}f}"
    except (TypeError, ValueError):
        return str(val)


def _fmt_int(val: Any, fallback: str = "—") -> str:
    if val is None:
        return fallback
    try:
        return f"{int(round(float(val))):,}"
    except (TypeError, ValueError):
        return str(val)


class _Row(QWidget):
    """label ···· value unit, colour-coded by ok state. Port of RR."""

    def __init__(
        self,
        label: str,
        sub: str = "",
        unit: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setStyleSheet(
            f"QWidget {{" f"border-bottom: 1px solid {BORDER};" f"}}"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(6)

        key = QLabel(label)
        key.setStyleSheet(
            f"QWidget {{" f"color: {MUTED}; font-size: 11px; border: none;" f"}}"
        )
        row.addWidget(key)
        if sub:
            sub_lbl = QLabel(sub)
            sub_lbl.setStyleSheet(
            f"QWidget {{" f"color: {TEXT3}; font-size: 9px; border: none;" f"}}"
        )
            row.addWidget(sub_lbl)
        row.addStretch()

        self._val = QLabel()
        self._val.setTextFormat(Qt.TextFormat.RichText)
        self._val.setStyleSheet(
            f"QWidget {{" "border: none;" f"}}"
        )
        self._val.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(self._val)

        self._unit = unit

    def set(self, value: Any, ok: Optional[bool] = None,
            hl: bool = False) -> None:
        col = (SUCCESS if ok is True else DANGER if ok is False
               else ACCENT if hl else TEXT)
        shown = "—" if value is None else str(value)
        unit_html = (
            f"<span style='color:{MUTED};font-weight:400;'> {self._unit}</span>"
            if self._unit else ""
        )
        self._val.setText(
            f"<span style='font-family:\"JetBrains Mono\",monospace;"
            f"font-weight:700;font-size:11px;color:{col};'>{shown}</span>"
            f"{unit_html}"
        )


class _Card(QFrame):
    """Titled panel; port of Panel + SHdr."""

    def __init__(self, icon: str, title: str, badge: str = "",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{" f"background-color: {PANEL}; border: 1px solid {BORDER}; "
            f"border-radius: 9px;" f"}}"
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(0)

        head = QHBoxLayout()
        head.setSpacing(6)
        ic = QLabel(icon)
        ic.setStyleSheet(
            f"QFrame {{" "border: none; font-size: 11px;" f"}}"
        )
        head.addWidget(ic)
        lbl = QLabel(title.upper())
        lbl.setStyleSheet(
            f"QFrame {{" f"color: {ACCENT}; font-size: 9px; font-weight: 700; "
            f"letter-spacing: 0.09em; border: none; "
            f"font-family: 'Barlow Condensed', sans-serif;" f"}}"
        )
        head.addWidget(lbl)
        head.addStretch()
        if badge:
            bd = QLabel(badge)
            bd.setStyleSheet(
            f"QFrame {{" f"color: {TEXT3}; font-size: 9px; border: none;" f"}}"
        )
            head.addWidget(bd)
        self._layout.addLayout(head)
        self._layout.addSpacing(8)

    def add(self, w: _W) -> _W:
        self._layout.addWidget(w)
        return w


class _ScrollPanel(QScrollArea):
    """Common scroll host for a tab body."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"background-color: {BG};")
        self._body = QWidget()
        self.body_layout = QVBoxLayout(self._body)
        self.body_layout.setContentsMargins(12, 12, 12, 12)
        self.body_layout.setSpacing(10)
        self.setWidget(self._body)


# ── Checks ────────────────────────────────────────────────────────────────

class ChecksPanel(_ScrollPanel):
    """The 11 engineering checks — port of the `checks` array + its render."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._summary = QLabel("Run a calculation to see checks.")
        self._summary.setStyleSheet(
            f"QFrame {{" f"color: {MUTED}; font-size: 11px; border: none;" f"}}"
        )
        self.body_layout.addWidget(self._summary)

        self._host = QWidget()
        self._grid = QVBoxLayout(self._host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(6)
        self.body_layout.addWidget(self._host)
        self.body_layout.addStretch()

    def set_data(self, R: dict) -> None:
        # Clear prior rows.
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None:
                w.deleteLater()

        checks = self._build_checks(R)
        n_fail = sum(1 for c in checks if c["ok"] is False)
        self._summary.setText(
            f"{len(checks)} checks · "
            f"{'all pass' if n_fail == 0 else f'{n_fail} failing'}"
        )
        for c in checks:
            self._grid.addWidget(self._make_row(c))

    def _make_row(self, c: dict) -> QWidget:
        frame = QFrame()
        ok = c["ok"]
        edge = SUCCESS if ok is True else DANGER if ok is False else TEXT3
        frame.setStyleSheet(
            f"QFrame {{" f"background-color: {PANEL}; border: 1px solid {BORDER}; "
            f"border-left: 3px solid {edge}; border-radius: 6px;" f"}}"
        )
        row = QHBoxLayout(frame)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(8)

        icon = QLabel("✓" if ok is True else "✗" if ok is False else "•")
        icon.setStyleSheet(
            f"QFrame {{" f"color: {edge}; font-weight: 700; border: none;" f"}}"
        )
        row.addWidget(icon)

        name = QLabel(c["label"])
        name.setStyleSheet(
            f"QFrame {{" f"color: {TEXT}; font-size: 11px; border: none;" f"}}"
        )
        row.addWidget(name)
        row.addStretch()

        val = QLabel(c["val"])
        val.setStyleSheet(
            f"QFrame {{" f"color: {edge}; font-size: 11px; font-weight: 700; border: none; "
            f"font-family: 'JetBrains Mono', monospace;" f"}}"
        )
        row.addWidget(val)
        if c["req"]:
            req = QLabel(c["req"])
            req.setStyleSheet(
            f"QFrame {{" f"color: {TEXT3}; font-size: 9px; border: none;" f"}}"
        )
            row.addWidget(req)
        return frame

    def _build_checks(self, R: dict) -> list[dict]:
        """Line-for-line port of the `checks` array in CalcPage.tsx."""
        cap = R.get("cap", {}) or {}
        tor = R.get("tor", {}) or {}
        gbx = R.get("gbx_r", {}) or {}
        brg = R.get("brg_r", {}) or {}
        eff = R.get("eff", {}) or {}
        pwr = R.get("pwr", {}) or {}
        mat = R.get("mat", {}) or {}

        fill = cap.get("fill_actual") or cap.get("fill") or 0.3
        util = eff.get("cap_util") or 0
        kwh = eff.get("kWh_t")
        kwh = 9 if kwh is None else kwh
        vib = R.get("vibration_risk") or 0
        sallow = R.get("_sallow_display", tor.get("sallow", 40))

        def yn(v):
            return v if isinstance(v, bool) else None

        return [
            {"label": "Capacity", "ok": yn(cap.get("ok")),
             "val": f"{_fmt(cap.get('Qt'), 1)} t/h",
             "req": f"{cap.get('req', '?')} t/h req"},
            {"label": "Shaft Stress", "ok": yn(tor.get("shOk")),
             "val": f"{_fmt(tor.get('tau'), 1)} MPa",
             "req": f"≤{sallow} MPa"},
            {"label": "Gearbox Torque", "ok": yn(gbx.get("tOk")),
             "val": f"{_fmt_int(tor.get('Ts'))} Nm",
             "req": f"≤{_fmt_int(gbx.get('Tn_derated') or gbx.get('Tn') or 0)} Nm"},
            {"label": "Bearing L10", "ok": yn(brg.get("ok")),
             "val": f"{_fmt_int(brg.get('L10') or 0)} h",
             "req": f"≥{_fmt_int(brg.get('L10_target') or 20000)} h"},
            {"label": "Vibration Risk", "ok": vib < 3,
             "val": R.get("vri_label") or "—", "req": "Low target"},
            {"label": "Energy kWh/t", "ok": kwh < 1,
             "val": _fmt(eff.get("kWh_t") or 0, 3), "req": "<1.0 optimal"},
            {"label": "Fill φ (act)", "ok": 15 <= fill * 100 <= 45,
             "val": f"{_fmt(fill * 100, 1)}%", "req": "15–45% target"},
            {"label": "Utilisation", "ok": 70 <= util <= 100,
             "val": f"{_fmt(util, 0)}%", "req": "70–100% target"},
            {"label": "Shaft Defl.", "ok": yn(R.get("deflection_ok")),
             "val": f"{_fmt((R.get('deflection') or 0) * 1000, 2)} mm",
             "req": f"≤{_fmt((R.get('defl_limit') or 0.01) * 1000, 2)} mm"},
            {"label": "Motor",
             "ok": (pwr.get("motor") or 0) >= (pwr.get("motor_rated") or 0),
             "val": f"{pwr.get('motor', '—')} kW",
             "req": f"{_fmt(pwr.get('motor_rated') or 0, 1)} kW rated"},
            {"label": "Load Class", "ok": None,
             "val": f"Class {mat.get('cls', '—')}", "req": ""},
        ]


# ── Wear & Life ─────────────────────────────────────────────────────────────

class WearPanel(_ScrollPanel):
    """Bearing + wear-life rows. Port of the Wear tab's two panels."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        pair = QWidget()
        grid = QGridLayout(pair)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        brg = _Card("🎯", "Bearing Life")
        self._r_bload = brg.add(_Row("Bearing load", unit="kN"))
        self._r_cp = brg.add(_Row("C/P Ratio"))
        self._r_l10t = brg.add(_Row("Required L10", unit="h"))
        self._r_l10 = brg.add(_Row("L10 Life", unit="h"))
        self._brg_hint = QLabel()
        self._brg_hint.setWordWrap(True)
        self._brg_hint.setStyleSheet(
            f"QFrame {{" f"background-color: rgba(217,142,0,0.08); border: 1px solid {WARNING}; "
            f"border-radius: 4px; padding: 5px 8px; font-size: 9px; color: {WARNING};" f"}}"
        )
        self._brg_hint.setVisible(False)
        brg.add(self._brg_hint)
        grid.addWidget(brg, 0, 0)

        wear = _Card("🔧", "Wear Life")
        self._r_tip = wear.add(_Row("Tip Speed", unit="m/s"))
        self._r_pc = wear.add(_Row("Contact Pressure", unit="kPa"))
        self._r_wb = wear.add(_Row("Wear Rate (body)", unit="mm/h"))
        self._r_wi = wear.add(_Row("Wear Rate (inlet)", sub="3× body rate", unit="mm/h"))
        self._r_thk = wear.add(_Row("Usable Thickness", unit="mm"))
        self._r_lifeb = wear.add(_Row("Flight Life (body)", unit="h"))
        self._r_lifei = wear.add(_Row("Flight Life (inlet)", unit="h"))
        self._r_lifet = wear.add(_Row("Throughput Life", unit="t"))
        grid.addWidget(wear, 0, 1)

        self.body_layout.addWidget(pair)
        self.body_layout.addStretch()

    def set_data(self, R: dict) -> None:
        brg = R.get("brg_r", {}) or {}
        wear = R.get("wear", {}) or {}

        load = brg.get("load")
        self._r_bload.set(_fmt(load, 2))
        C = brg.get("C") or 43
        self._r_cp.set(_fmt(C / (load or 10), 2))
        self._r_l10t.set(_fmt_int(brg.get("L10_target") or 20000))
        self._r_l10.set(_fmt_int(brg.get("L10")), ok=brg.get("ok"), hl=True)
        adequate = brg.get("adequate")
        if brg.get("ok") is False and adequate:
            self._brg_hint.setText(f"💡 Suggested: {adequate} — select to meet target")
            self._brg_hint.setVisible(True)
        else:
            self._brg_hint.setVisible(False)

        wrate = wear.get("wrate_mm_h")
        life_h = wear.get("life_h") or 0
        self._r_tip.set(_fmt(wear.get("v_tip"), 2))
        self._r_pc.set(_fmt(wear.get("P_contact_kPa"), 2))
        self._r_wb.set(_fmt(wrate, 4))
        self._r_wi.set(_fmt((wrate or 0) * 3, 4))
        self._r_thk.set(_fmt(wear.get("thick_mm"), 1))
        self._r_lifeb.set(_fmt_int(wear.get("life_h")), ok=life_h > 8000, hl=True)
        self._r_lifei.set(_fmt_int(life_h / 3), ok=life_h / 3 > 2000)
        self._r_lifet.set(_fmt_int(wear.get("life_t")))


# ── Structural ──────────────────────────────────────────────────────────────

class StructuralPanel(_ScrollPanel):
    """
    Port of StructuralModule in CalcPage.tsx.

    Reads result["structural"] — the backend calc_structural() output — and
    displays it. No stress arithmetic here; the physics now lives in
    backend/core/engine.py. Hanger count and load-per-hanger, which the .tsx
    derived inline (hCount = R.hgr?.count || s.n_supports; hLoad = s.R_kN /
    hCount), are the only values assembled in the panel, and they are simple
    ratios of already-computed scalars, not new engineering.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._header = _Card(
            "🔩", "Structural Engineering Module — U-Trough Screw Conveyor",
        )
        self.body_layout.addWidget(self._header)

        top = QWidget()
        tg = QGridLayout(top)
        tg.setContentsMargins(0, 0, 0, 0)
        tg.setSpacing(10)
        for i in range(3):
            tg.setColumnStretch(i, 1)

        plate = _Card("□", "Trough Plate")
        self._s_wtotal = plate.add(_Row("Load (mat+screw)", unit="kN/m"))
        self._s_mmax = plate.add(_Row("Bending moment", unit="N·m/m"))
        self._s_tplate = plate.add(_Row("Plate thickness", unit="mm"))
        self._s_span = plate.add(_Row("Span used", unit="m"))
        tg.addWidget(plate, 0, 0)

        cover = _Card("⊡", "Cover & Flange")
        self._s_tcover = cover.add(_Row("Cover thickness", unit="mm"))
        self._s_coverbp = cover.add(_Row("Cover bolt pitch", unit="mm"))
        self._s_flanget = cover.add(_Row("Flange thickness", unit="mm"))
        self._s_flangew = cover.add(_Row("Flange width", unit="mm"))
        self._s_boltsize = cover.add(_Row("Bolt size"))
        self._s_nbolts1 = cover.add(_Row("Bolts per flange", unit="pcs"))
        tg.addWidget(cover, 0, 1)

        bolt = _Card("🔩", "Bolting")
        self._s_boltcap = bolt.add(_Row("Bolt capacity", unit="kN"))
        self._s_pload = bolt.add(_Row("Pressure load", unit="kN"))
        self._s_nbolts2 = bolt.add(_Row("Required bolts", unit="pcs"))
        self._s_boltpitch = bolt.add(_Row("Bolt spacing", unit="mm"))
        self._s_weld = bolt.add(_Row("Weld size", unit="mm"))
        tg.addWidget(bolt, 0, 2)
        self.body_layout.addWidget(top)

        bot = QWidget()
        bg = QGridLayout(bot)
        bg.setContentsMargins(0, 0, 0, 0)
        bg.setSpacing(10)
        bg.setColumnStretch(0, 1)
        bg.setColumnStretch(1, 1)

        hang = _Card("🔗", "Hanger Loads")
        self._s_hcount = hang.add(_Row("Hangers", unit="pcs"))
        self._s_hspan = hang.add(_Row("Hanger span", unit="m"))
        self._s_hload = hang.add(_Row("Load per hanger", unit="kN"))
        self._s_react = hang.add(_Row("Reaction force", unit="kN"))
        self._s_recbrg = hang.add(_Row("Recommended brg"))
        bg.addWidget(hang, 0, 0)

        key = _Card("🗝️", "Shaft Key & System")
        self._s_keyb = key.add(_Row("Key width (b)", unit="mm"))
        self._s_smass = key.add(_Row("Screw mass", unit="kg"))
        self._s_tmass = key.add(_Row("Trough mass (est)", unit="kg"))
        self._s_endreact = key.add(_Row("End support reac.", unit="kN"))
        bg.addWidget(key, 0, 1)
        self.body_layout.addWidget(bot)
        self.body_layout.addStretch()

    def set_data(self, R: dict) -> None:
        s = R.get("structural")
        if not s:
            # Backend older than the calc_structural wiring, or an error
            # result — leave every row at its "—" default rather than guess.
            return

        self._s_wtotal.set(_fmt(s.get("w_total"), 3))
        self._s_mmax.set(_fmt(s.get("M_max"), 3))
        self._s_tplate.set(s.get("t_plate"), ok=True)
        self._s_span.set(_fmt(s.get("hanger_span"), 2))

        self._s_tcover.set(s.get("t_cover"))
        self._s_coverbp.set(s.get("cover_bp"))
        self._s_flanget.set(s.get("flange_t"))
        self._s_flangew.set(s.get("flange_w"))
        self._s_boltsize.set(s.get("bolt_size"))
        self._s_nbolts1.set(s.get("n_bolts"))

        self._s_boltcap.set(_fmt(s.get("bolt_cap"), 1), ok=s.get("bolt_ok"))
        self._s_pload.set(_fmt(s.get("pressure_load"), 1))
        self._s_nbolts2.set(s.get("n_bolts"), ok=True)
        self._s_boltpitch.set(s.get("bolt_pitch"))
        self._s_weld.set(s.get("weld_size"))

        # Hanger count/load — derived in the .tsx render, not in calcStructural.
        hgr = R.get("hgr", {}) or {}
        h_count = hgr.get("count") or s.get("n_supports") or 1
        r_kn = s.get("R_kN") or 0
        h_load = r_kn / max(h_count, 1)
        self._s_hcount.set(h_count)
        self._s_hspan.set(_fmt(s.get("hanger_span"), 2))
        self._s_hload.set(_fmt(h_load, 1), ok=h_load <= 10)
        self._s_react.set(_fmt(s.get("R_kN"), 1))
        # Recommended bearing: UC + round(D*100/5)*5 + 200, from the .tsx.
        D = R.get("_D_display")
        if D is None:
            D = (R.get("geom", {}) or {}).get("D")
        if D:
            self._s_recbrg.set(f"UC{int(round(D * 100 / 5) * 5 + 200)}")

        self._s_keyb.set(s.get("key_b"))
        self._s_smass.set(_fmt_int(s.get("screw_mass")))
        self._s_tmass.set(_fmt_int(s.get("trough_mass")))
        self._s_endreact.set(_fmt(s.get("end_react"), 1))


# ── Materials ───────────────────────────────────────────────────────────────

class MaterialsPanel(_ScrollPanel):
    """
    Material properties + surface recommendations.

    Port of the material-properties rows and MatRecs in CalcPage.tsx. Reads
    result["mat"] (the DB record for the selected material),
    result["mat_props"] (engine-derived λ, Ks, wc, psz) and result["recs"]
    (mat_recs() output: trough / flight / shaft / treatments / notes).

    Deliberately NOT a database browser. This tab describes the ONE material
    the current design uses; the standalone Database module is the searchable
    catalogue of all 531. Keeping them separate means this tab does not
    depend on which DatabasePage source is canonical.
    """

    _REC_SECTIONS = [
        ("trough",     "□",  "Trough",     "#60a5fa"),
        ("flight",     "🔩", "Flights",    "#f97316"),
        ("shaft",      "⚙️", "Shaft",      "#a78bfa"),
        ("treatments", "🔥", "Treatments", "#fb923c"),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        pair = QWidget()
        grid = QGridLayout(pair)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        ident = _Card("📦", "Material Identity")
        self._m_name = ident.add(_Row("Name"))
        self._m_cema = ident.add(_Row("CEMA code"))
        self._m_cls = ident.add(_Row("Load class"))
        self._m_pclass = ident.add(_Row("Particle class"))
        self._m_source = ident.add(_Row("Source"))
        self._m_conf = ident.add(_Row("Confidence"))
        grid.addWidget(ident, 0, 0)

        phys = _Card("⚗️", "Physical Properties")
        self._m_rho = phys.add(_Row("Bulk density", unit="t/m³"))
        self._m_abr = phys.add(_Row("Abrasiveness"))
        self._m_flow = phys.add(_Row("Flowability"))
        self._m_moist = phys.add(_Row("Moisture", unit="%"))
        self._m_aor = phys.add(_Row("Angle of repose", unit="°"))
        self._m_temp = phys.add(_Row("Max temperature", unit="°C"))
        grid.addWidget(phys, 0, 1)

        eng = _Card("🧮", "Engine-Derived Factors")
        self._p_lam = eng.add(_Row("λ (lambda)", sub="capacity factor"))
        self._p_fill = eng.add(_Row("Fill max", unit="%"))
        self._p_ks = eng.add(_Row("Ks", sub="material factor"))
        self._p_wc = eng.add(_Row("wc", sub="wear coefficient"))
        self._p_psz = eng.add(_Row("Particle size", unit="m"))
        grid.addWidget(eng, 1, 0)

        risk = _Card("⚠️", "Handling Risk")
        self._m_bridge = risk.add(_Row("Bridging risk"))
        self._m_regime = risk.add(_Row("Flow regime"))
        self._m_cohes = risk.add(_Row("Cohesion"))
        grid.addWidget(risk, 1, 1)
        self.body_layout.addWidget(pair)

        # Recommendations — one bordered block per section, two per row.
        self._recs_card = _Card("🛡️", "Material & Surface Recommendations")
        self._recs_host = QWidget()
        self._recs_grid = QGridLayout(self._recs_host)
        self._recs_grid.setContentsMargins(0, 0, 0, 0)
        self._recs_grid.setSpacing(10)
        self._recs_grid.setColumnStretch(0, 1)
        self._recs_grid.setColumnStretch(1, 1)
        self._recs_card.add(self._recs_host)

        self._notes = QLabel()
        self._notes.setWordWrap(True)
        self._notes.setStyleSheet(
            f"QFrame {{" f"background-color: rgba(74,158,255,0.06); "
            f"border: 1px solid rgba(74,158,255,0.2); border-radius: 6px; "
            f"padding: 7px 10px; font-size: 10px; color: #93c5fd;"
         f"}}"
        )
        self._notes.setVisible(False)
        self._recs_card.add(self._notes)
        self.body_layout.addWidget(self._recs_card)
        self.body_layout.addStretch()

    def set_data(self, R: dict) -> None:
        mat = R.get("mat", {}) or {}
        props = R.get("mat_props", {}) or {}

        self._m_name.set(mat.get("name"))
        self._m_cema.set(mat.get("cema_code"))
        self._m_cls.set(mat.get("cls"))
        self._m_pclass.set(mat.get("particle_class"))
        self._m_source.set(mat.get("source"))
        self._m_conf.set(mat.get("confidence"))

        self._m_rho.set(_fmt(mat.get("rho"), 3))
        self._m_abr.set(mat.get("abr"))
        self._m_flow.set(mat.get("flowability"))
        self._m_moist.set(_fmt(mat.get("moist"), 1))
        self._m_aor.set(_fmt(mat.get("aor"), 1))
        self._m_temp.set(mat.get("temp_max"))

        self._p_lam.set(_fmt(props.get("lam"), 3))
        fill_max = props.get("fill_max")
        self._p_fill.set(_fmt(None if fill_max is None else fill_max * 100, 1))
        self._p_ks.set(_fmt(props.get("Ks"), 3))
        self._p_wc.set(_fmt(props.get("wc"), 4))
        self._p_psz.set(_fmt(props.get("psz"), 4))

        self._m_bridge.set(mat.get("bridging_risk"))
        self._m_regime.set(mat.get("flow_regime"))
        self._m_cohes.set(mat.get("cohesion"))

        self._render_recs(R.get("recs") or {})

    def _render_recs(self, recs: dict) -> None:
        while self._recs_grid.count():
            item = self._recs_grid.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None:
                w.deleteLater()

        # Only sections with entries are rendered, matching the .tsx guard
        # `(recs[s.k]||[]).length>0 && ...` — an empty section shows nothing
        # rather than an empty heading.
        slot = 0
        for key, icon, label, colour in self._REC_SECTIONS:
            items = recs.get(key) or []
            if not items:
                continue
            block = QFrame()
            block.setStyleSheet(
            f"QFrame {{" "background-color: rgba(0,0,0,0.2); border-radius: 7px;"
             f"}}"
        )
            col = QVBoxLayout(block)
            col.setContentsMargins(11, 9, 11, 9)
            col.setSpacing(3)
            head = QLabel(f"{icon} {label}")
            head.setStyleSheet(
            f"QFrame {{" f"color: {colour}; font-size: 10px; font-weight: 700; "
                f"border: none;" f"}}"
        )
            col.addWidget(head)
            for text in items:
                line = QLabel(f"• {text}")
                line.setWordWrap(True)
                line.setStyleSheet(
            f"QFrame {{" f"color: #b0c8e0; font-size: 10px; "
                    f"border: none; border-left: 2px solid {colour}55; "
                    f"padding-left: 8px;" f"}}"
        )
                col.addWidget(line)
            self._recs_grid.addWidget(block, slot // 2, slot % 2)
            slot += 1

        notes = recs.get("notes") or []
        if notes:
            body = "\n".join(f"• {n}" for n in notes)
            self._notes.setText(f"⚠ DESIGN NOTES\n{body}")
            self._notes.setVisible(True)
        else:
            self._notes.setVisible(False)