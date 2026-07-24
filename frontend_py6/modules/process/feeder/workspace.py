"""
modules/process/feeder/workspace.py — Screw Feeder / Doser (VL series)
═══════════════════════════════════════════════════════════════════════════
Port of frontend/src/components/pages/FeederPage.tsx.

Directory placement: this module lives under modules/process/ even though
its menu group is "conveyor". The grouping is presentation — where a user
expects to find it in the menu — while the directory follows the code: the
route is /api/v1/process/feeder, the engine function is calc_feeder() in
process_engine.py, and the .tsx itself imports ModuleShell from
ProcessPage. Filing it as modules/feeder/ would have meant importing across
family packages, which modules/__init__.py forbids.

Response shape verified against calc_feeder() directly — run_feeder is a
pass-through that only adds {"module": "feeder"}, so unlike Dryer/Cooler/
Reactor/Separator/Compactor the engine IS authoritative here.

Known gap carried over, not invented: the .tsx renders a "Slip factor S"
row from `r.S_f`, but calc_feeder() does not return `S_f`. The .tsx writes
`r.S_f?.toFixed(3) ?? '—'`, so the web app silently shows a dash. This port
shows the same dash rather than dropping the row, so the missing field
stays visible as a gap instead of disappearing from both apps.

Conditional UI mirrored from the .tsx:
  - fill > 0.60           inline flood-risk warning under the geometry group
  - fMode == 'liw'        tare-weight field, plus the LIW load-cell rows
  - fBatchSize > 0        batch fill-time row
  - calibCurve non-empty  calibration chart
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
)

from core.theme import (
    BORDER, MUTED, TEAL, PRIMARY, PURPLE, SUCCESS, WARNING, DANGER,
)
from modules.base import ModuleMeta
from modules.process.common import (
    ModuleShell, Field, Divider, KpiCard, ResultRow, Card, WarningsPanel, fmt,
)
from .calibration_chart import CalibrationChart


def _accuracy_color(cv: Optional[float]) -> str:
    """Mirrors accuracyColor() in the .tsx."""
    if cv is None:
        return DANGER
    if cv < 0.5:
        return SUCCESS
    if cv < 1.5:
        return TEAL
    if cv < 3.0:
        return WARNING
    return DANGER


class FeederWorkspace(ModuleShell):

    page_id = "feeder"
    endpoint = "feeder"
    meta = ModuleMeta(
        label="Feeder / Doser",
        icon="🎚️",
        subtitle="K-factor · Turndown · CV% accuracy · Hopper interface · LIW sizing",
        group="conveyor",
    )
    empty_desc = (
        "K-factor volumetric efficiency · Turndown ratio · Feed accuracy "
        "(CV%) via drive+material+mode RSS · Hopper interface with Jenike "
        "arch analysis · Flood/starve assessment · N vs Q calibration curve. "
        "CEMA 7th Ed. + Jenike principles."
    )

    # ── inputs ────────────────────────────────────────────────────────────

    def build_inputs(self, layout: QVBoxLayout) -> None:
        layout.addWidget(Divider("A — Screw Geometry"))
        self._fDiam = Field("Diameter", 0.15, 0.05, 0.60, 0.01, "m")
        self._fLen = Field("Length", 1.2, 0.2, 6.0, 0.1, "m")
        self._fPitch = Field("Pitch ratio ×D", 1.0, 0.3, 1.5, 0.1)
        self._fFill = Field("Fill fraction", 0.45, 0.15, 0.70, 0.05)
        for f in (self._fDiam, self._fLen, self._fPitch, self._fFill):
            layout.addWidget(f)

        self._flood_warn = QLabel()
        self._flood_warn.setWordWrap(True)
        self._flood_warn.setStyleSheet(
            f"QFrame {{" f"background-color: rgba(224,82,82,0.08); "
            f"border: 1px solid {DANGER}; border-radius: 4px; "
            f"padding: 5px 8px; font-size: 9px; color: {DANGER};" f"}}"
        )
        self._flood_warn.setVisible(False)
        layout.addWidget(self._flood_warn)
        self._fFill.changed.connect(self._sync_fill_warning)

        layout.addWidget(Divider("B — Material & Speed Range"))
        self._fRho = Field("Bulk density", 0.8, 0.05, 3.0, 0.05, "t/m³")
        self._fQ_target = Field("Target flow", 0.5, 0.001, 500.0, 0.01, "t/h",
                                decimals=3)
        self._fN_min = Field("N_min", 2.0, 0.5, 20.0, 0.5, "RPM")
        self._fN_max = Field("N_max", 60, 5, 200, 1, "RPM")
        self._fMat = Field(
            "Material flowability", "easy_flowing",
            options=[
                ("free_flowing",  "Free-flowing (K≈0.90) — sand, grain, pellets"),
                ("easy_flowing",  "Easy-flowing (K≈0.82) — sugar, salt, powder"),
                ("cohesive",      "Cohesive (K≈0.72) — flour, clay, sticky"),
                ("very_cohesive", "Very cohesive (K≈0.58) — wet cake, hygroscopic"),
            ],
        )
        for f in (self._fRho, self._fQ_target, self._fN_min, self._fN_max,
                  self._fMat):
            layout.addWidget(f)

        layout.addWidget(Divider("C — Control Mode & Drive"))
        self._fMode = Field(
            "Control mode", "volumetric",
            options=[
                ("volumetric", "📦 Volumetric — RPM controls Q (±2–5%)"),
                ("liw",        "⚖️ Loss-in-Weight — gravimetric (±0.5%)"),
            ],
        )
        self._fDrive = Field(
            "Drive type", "servo",
            options=[
                ("servo",   "🎯 Servo — highest accuracy"),
                ("vfd",     "⚡ VFD/AC — standard"),
                ("stepper", "🔩 Stepper — digital positioning"),
                ("dc",      "🔋 DC drive — low cost"),
            ],
        )
        layout.addWidget(self._fMode)
        layout.addWidget(self._fDrive)

        self._fLIW_tare = Field("Tare weight", 50, 5, 2000, 5, "kg")
        self._fHopperVol = Field("Hopper volume", 0.5, 0.01, 50.0, 0.05, "m³")
        layout.addWidget(self._fLIW_tare)
        layout.addWidget(self._fHopperVol)
        self._fMode.changed.connect(self._sync_mode)

        layout.addWidget(Divider("D — Hopper Interface (Jenike)"))
        self._fHopperAngle = Field("Hopper angle", 60, 30, 90, 5, "°")
        self._fWallFriction = Field("Wall friction μ", 0.35, 0.1, 0.7, 0.05)
        layout.addWidget(self._fHopperAngle)
        layout.addWidget(self._fWallFriction)

        layout.addWidget(Divider("E — Downstream Matching"))
        self._fDownstreamT = Field("Process cycle", 0, 0, 3600, 10, "s")
        self._fBatchSize = Field("Batch size", 0, 0, 100000, 10, "kg")
        layout.addWidget(self._fDownstreamT)
        layout.addWidget(self._fBatchSize)

        self._sync_fill_warning()
        self._sync_mode()

    def _sync_fill_warning(self) -> None:
        fill = self._fFill.value()
        if fill > 0.60:
            self._flood_warn.setText(
                f"⚠ Fill {fill * 100:.0f}% > 60% — flood risk with "
                f"free-flowing materials"
            )
            self._flood_warn.setVisible(True)
        else:
            self._flood_warn.setVisible(False)

    def _sync_mode(self) -> None:
        """Tare weight is LIW-only; hopper volume shows in both modes."""
        self._fLIW_tare.setVisible(self._fMode.value() == "liw")

    def collect_payload(self) -> dict:
        return {
            "fDiam":            self._fDiam.value(),
            "fLen":             self._fLen.value(),
            "fPitch":           self._fPitch.value(),
            "fFill":            self._fFill.value(),
            "fRho":             self._fRho.value(),
            "fN_min":           self._fN_min.value(),
            "fN_max":           self._fN_max.value(),
            "fQ_target":        self._fQ_target.value(),
            "fMat_flowability": self._fMat.value(),
            "fMode":            self._fMode.value(),
            "fDriveType":       self._fDrive.value(),
            "fHopperVol":       self._fHopperVol.value(),
            "fHopperAngle":     self._fHopperAngle.value(),
            "fWallFriction":    self._fWallFriction.value(),
            "fLIW_tare":        self._fLIW_tare.value(),
            "fDownstreamT":     self._fDownstreamT.value(),
            "fBatchSize":       self._fBatchSize.value(),
        }

    # ── results ───────────────────────────────────────────────────────────

    def build_results(self, layout: QVBoxLayout) -> None:
        kpi_host = QWidget()
        grid = QGridLayout(kpi_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        self._kpi_flow = KpiCard("Target Flow", unit="t/h")
        self._kpi_turn = KpiCard("Turndown", unit=":1", sub="Q_max / Q_min")
        self._kpi_cv = KpiCard("Feed Accuracy", unit="%")
        self._kpi_k = KpiCard("K-factor", col=PRIMARY, sub="volumetric efficiency")
        for col, card in enumerate(
            (self._kpi_flow, self._kpi_turn, self._kpi_cv, self._kpi_k)
        ):
            grid.addWidget(card, 0, col)
            grid.setColumnStretch(col, 1)
        layout.addWidget(kpi_host)

        self._warnings = WarningsPanel()
        layout.addWidget(self._warnings)

        cards = QWidget()
        cgrid = QGridLayout(cards)
        cgrid.setContentsMargins(0, 0, 0, 0)
        cgrid.setSpacing(10)
        cgrid.setColumnStretch(0, 1)
        cgrid.setColumnStretch(1, 1)

        flow = Card("📊 Flow Range")
        self._r_qmin = flow.add_row(ResultRow("Q_min", unit="t/h"))
        self._r_qmax = flow.add_row(ResultRow("Q_max", unit="t/h"))
        self._r_qtgt = flow.add_row(ResultRow("Q_target", unit="t/h"))
        self._r_qact = flow.add_row(ResultRow("Q_actual", unit="t/h"))
        self._r_nreq = flow.add_row(ResultRow("N_required", unit="RPM"))
        self._r_nop = flow.add_row(ResultRow("N_operating", unit="RPM"))
        self._r_qv = flow.add_row(ResultRow("Qv/rev", unit="L/rev"))
        self._r_turn = flow.add_row(ResultRow("Turndown"))
        cgrid.addWidget(flow, 0, 0)

        acc = Card("🎯 K-factor & Accuracy")
        self._r_kbase = acc.add_row(ResultRow("K_base (flowability)"))
        self._r_kfill = acc.add_row(ResultRow("K_fill (correction)"))
        self._r_kfac = acc.add_row(ResultRow("K_factor (total)"))
        self._r_cvd = acc.add_row(ResultRow("CV drive", unit="%"))
        self._r_cvm = acc.add_row(ResultRow("CV material", unit="%"))
        self._r_cvmo = acc.add_row(ResultRow("CV mode", unit="%"))
        self._r_cvt = acc.add_row(ResultRow("CV total (RSS)", unit="%"))
        self._acc_class = QLabel()
        self._acc_class.setStyleSheet(
            f"QFrame {{" "border: none; font-size: 9px;" f"}}"
        )
        acc.add_widget(self._acc_class)
        cgrid.addWidget(acc, 0, 1)

        pwr = Card("⚡ Power & Drive")
        self._r_pe = pwr.add_row(ResultRow("P friction", unit="kW"))
        self._r_pmat = pwr.add_row(ResultRow("P material", unit="kW"))
        self._r_pshaft = pwr.add_row(ResultRow("P shaft", unit="kW"))
        self._r_ptot = pwr.add_row(ResultRow("P total", unit="kW"))
        self._r_motor = pwr.add_row(ResultRow("Motor", unit="kW"))
        self._r_torque = pwr.add_row(ResultRow("Torque", unit="Nm"))
        self._r_tip = pwr.add_row(ResultRow("Tip speed", unit="m/s"))
        self._r_ld = pwr.add_row(ResultRow("L/D ratio"))
        cgrid.addWidget(pwr, 1, 0)

        hop = Card("🪣 Hopper Interface")
        self._r_outlet = hop.add_row(ResultRow("Min outlet size", unit="m"))
        self._r_hangle = hop.add_row(ResultRow("Hopper angle", unit="°"))
        self._r_mfangle = hop.add_row(
            ResultRow("Mass flow angle", unit="° half-angle min")
        )
        self._r_refill = hop.add_row(ResultRow("Refill interval", unit="min"))
        self._r_surge = hop.add_row(ResultRow("Surge capacity", unit="min"))
        self._r_arch = hop.add_row(ResultRow("Arch risk"))
        self._r_flood = hop.add_row(ResultRow("Flood risk"))
        self._r_starve = hop.add_row(ResultRow("Starve risk"))
        cgrid.addWidget(hop, 1, 1)

        ctl = Card("🎛️ Control Sizing")
        self._r_dqdn = ctl.add_row(ResultRow("dQ/dN", unit="t/h/RPM"))
        self._r_rpmres = ctl.add_row(ResultRow("RPM resolution", unit="%/RPM"))
        self._r_ctlok = ctl.add_row(ResultRow("Control OK"))
        self._liw_head = QLabel("⚖️ LIW LOAD CELL")
        self._liw_head.setStyleSheet(
            f"QFrame {{" f"color: {TEAL}; font-size: 9px; font-weight: 700; border: none;" f"}}"
        )
        ctl.add_widget(self._liw_head)
        self._r_lc = ctl.add_row(ResultRow("LC rating", unit="kg"))
        self._r_lcres = ctl.add_row(ResultRow("LC resolution", unit="kg"))
        self._r_tare = ctl.add_row(ResultRow("Tare weight", unit="kg"))
        cgrid.addWidget(ctl, 2, 0)

        dwn = Card("🔁 Downstream Matching")
        self._r_vax = dwn.add_row(ResultRow("V axial", unit="m/s"))
        self._r_slip = dwn.add_row(ResultRow("Slip factor S"))
        self._r_cycle = dwn.add_row(ResultRow("Process cycle"))
        self._r_batch = dwn.add_row(ResultRow("Batch size"))
        self._r_btime = dwn.add_row(ResultRow("Batch fill time", unit="s"))
        cgrid.addWidget(dwn, 2, 1)

        layout.addWidget(cards)

        self._calib = CalibrationChart()
        layout.addWidget(self._calib)

    def apply_result(self, r: dict) -> None:
        achievable = r.get("target_achievable")
        turndown = r.get("turndown")
        cv = r.get("CV_total")
        cv_col = _accuracy_color(cv)
        is_liw = self._fMode.value() == "liw"
        batch = self._fBatchSize.value()

        self._kpi_flow.set_value(
            fmt(r.get("Q_actual"), 3) if achievable else "✗ NOT MET",
            unit="t/h" if achievable else "",
            ok=achievable,
            sub=f"req {self._fQ_target.value():g} t/h",
        )
        self._kpi_turn.set_value(
            fmt(turndown, 1),
            col=SUCCESS if (turndown or 0) >= 10 else WARNING,
            sub="Q_max / Q_min",
        )
        self._kpi_cv.set_value(
            f"CV {fmt(cv, 1)}", col=cv_col, sub=r.get("accuracy_class") or "",
        )
        self._kpi_k.set_value(
            fmt(r.get("K_factor"), 3), col=PRIMARY, sub="volumetric efficiency",
        )

        self._warnings.set_warnings(r.get("warns"))

        self._r_qmin.set_value(fmt(r.get("Q_mass_min"), 4))
        self._r_qmax.set_value(fmt(r.get("Q_mass_max"), 4))
        self._r_qtgt.set_value(f"{self._fQ_target.value():g}")
        self._r_qact.set_value(fmt(r.get("Q_actual"), 4), ok=achievable)
        self._r_nreq.set_value(fmt(r.get("N_required"), 1), ok=achievable)
        self._r_nop.set_value(fmt(r.get("N_req_clamped"), 1))
        self._r_qv.set_value(fmt(r.get("Qv_per_rpm"), 4))
        self._r_turn.set_value(
            f"{fmt(turndown, 1)}:1",
            ok=None if turndown is None else turndown >= 10,
        )

        self._r_kbase.set_value(fmt(r.get("K_base"), 3))
        self._r_kfill.set_value(fmt(r.get("K_fill"), 3))
        self._r_kfac.set_value(fmt(r.get("K_factor"), 3))
        self._r_cvd.set_value(fmt(r.get("CV_drive"), 2))
        self._r_cvm.set_value(fmt(r.get("CV_mat"), 2))
        self._r_cvmo.set_value(fmt(r.get("CV_mode"), 2))
        self._r_cvt.set_value(fmt(cv, 2))
        self._acc_class.setText(r.get("accuracy_class") or "")
        self._acc_class.setStyleSheet(
            f"QFrame {{" f"border: none; font-size: 9px; font-weight: 700; color: {cv_col};" f"}}"
        )

        self._r_pe.set_value(fmt(r.get("P_e"), 4))
        self._r_pmat.set_value(fmt(r.get("P_mat"), 4))
        self._r_pshaft.set_value(fmt(r.get("P_shaft"), 4))
        self._r_ptot.set_value(fmt(r.get("P_total"), 3))
        self._r_motor.set_value(r.get("motor_kW"))
        self._r_torque.set_value(fmt(r.get("torque_Nm"), 1))
        tip = r.get("tip_speed")
        self._r_tip.set_value(
            fmt(tip, 3), ok=None if tip is None else tip <= 2,
        )
        ld = r.get("LD_ratio")
        self._r_ld.set_value(fmt(ld, 1), ok=None if ld is None else ld <= 8)

        self._r_outlet.set_value(fmt(r.get("outlet_min_m"), 4))
        self._r_hangle.set_value(f"{self._fHopperAngle.value():g}")
        self._r_mfangle.set_value(fmt(r.get("mass_flow_angle"), 1))
        refill = r.get("refill_min")
        self._r_refill.set_value(
            fmt(refill, 1), ok=None if refill is None else refill >= 10,
        )
        self._r_surge.set_value(fmt(r.get("surge_time_min"), 1))
        arch = r.get("arch_risk")
        self._r_arch.set_value(
            r.get("arch_risk_msg"), ok=None if arch is None else not arch,
        )
        flood = r.get("flood_risk")
        self._r_flood.set_value(
            "⚠ YES" if flood else "No ✓", ok=None if flood is None else not flood,
        )
        starve = r.get("starve_risk")
        self._r_starve.set_value(
            "⚠ YES" if starve else "No ✓",
            ok=None if starve is None else not starve,
        )

        ctl_ok = r.get("control_ok")
        self._r_dqdn.set_value(fmt(r.get("dQ_per_rpm"), 5))
        self._r_rpmres.set_value(fmt(r.get("rpm_resolution"), 2), ok=ctl_ok)
        self._r_ctlok.set_value(
            "✓ <2%/RPM" if ctl_ok else "✗ >2%/RPM", ok=ctl_ok,
        )
        for w in (self._liw_head, self._r_lc, self._r_lcres, self._r_tare):
            w.setVisible(is_liw)
        if is_liw:
            self._r_lc.set_value(r.get("liw_lcell"))
            self._r_lcres.set_value(fmt(r.get("liw_resolution"), 3))
            self._r_tare.set_value(f"{self._fLIW_tare.value():g}")

        self._r_vax.set_value(fmt(r.get("v_ax_f"), 4))
        self._r_slip.set_value(fmt(r.get("S_f"), 3))   # see module docstring
        cycle = self._fDownstreamT.value()
        self._r_cycle.set_value(f"{cycle:g} s" if cycle else "Continuous")
        self._r_batch.set_value(f"{batch:g} kg" if batch else "N/A")
        self._r_btime.setVisible(batch > 0)
        if batch > 0:
            self._r_btime.set_value(
                fmt(r.get("batch_time_s"), 1), ok=r.get("batch_ok"),
            )

        self._calib.set_data(
            r.get("calibCurve") or [],
            target=self._fQ_target.value(),
            n_operating=r.get("N_req_clamped"),
        )