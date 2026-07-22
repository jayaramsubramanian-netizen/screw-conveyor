"""
modules/process/separator/workspace.py — Screw Separator module
═══════════════════════════════════════════════════════════════════════════
Port of frontend/src/components/pages/SeparatorPage.tsx.

Field names verified against backend/api/routes.py :: run_separator
(lines 749-789), not process_engine.py.

Note the module_type/endpoint split: the HTTP route is /process/separator,
but internally it calls solve_system(payload, "sep"). `endpoint` below is
the URL segment ("separator"), which is what api_client.fetch_process()
needs; the internal "sep" name never reaches the client.

This module DOES produce a history array and uses AxialChart — an earlier
note in modules/stubs.py claimed Separator and Compactor were scalar-only,
which was wrong. solve_system() marches segments for every module type.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout

from core.theme import PRIMARY, TEAL, PURPLE, WARNING, SUCCESS, DANGER
from modules.base import ModuleMeta
from modules.process.common import (
    ModuleShell, Field, Divider, KpiCard, ResultRow, Card, fmt,
)
from modules.process.axial_chart import AxialChart


def _sep_color(sep: Optional[float]) -> str:
    """Mirrors sep>85 ? green : sep>60 ? amber : red in the .tsx."""
    if sep is None:
        return DANGER
    if sep > 85:
        return SUCCESS
    if sep > 60:
        return WARNING
    return DANGER


class SeparatorWorkspace(ModuleShell):

    page_id = "separator"
    endpoint = "separator"
    meta = ModuleMeta(
        label="Screw Separator",
        icon="⚖️",
        subtitle="Grade efficiency curve · Stokes settling · Axial PSD tracking",
        group="process",
    )
    empty_desc = (
        "Sigmoid grade efficiency curve (engineering) or Stokes settling "
        "(physics). PSD tracked axially. Set d50 cut size and slope k for "
        "grade efficiency."
    )

    # ── inputs ────────────────────────────────────────────────────────────

    def build_inputs(self, layout: QVBoxLayout) -> None:
        layout.addWidget(Divider("Geometry"))
        self._diam = Field("Diameter", 0.3, 0.1, 1.2, 0.05, "m")
        self._lenSep = Field("Length", 3.0, 1.0, 40.0, 0.5, "m")
        for f in (self._diam, self._lenSep):
            layout.addWidget(f)

        layout.addWidget(Divider("Drive"))
        self._speedS = Field("Speed", 30, 2, 120, 1, "RPM")
        self._fill2 = Field("Fill fraction", 0.35, 0.1, 0.6, 0.05)
        for f in (self._speedS, self._fill2):
            layout.addWidget(f)

        layout.addWidget(Divider("Feed"))
        self._feed = Field("Feed rate", 5.0, 0.1, 500.0, 1.0, "t/h")
        self._rho = Field("Bulk density", 1.2, 0.1, 3.0, 0.05, "t/m³")
        self._rhoA = Field("Particle density", 1.5, 0.1, 8.0, 0.05, "t/m³")
        self._d_p = Field("Particle size", 2.0, 0.01, 50.0, 0.1, "mm")
        for f in (self._feed, self._rho, self._rhoA, self._d_p):
            layout.addWidget(f)

        layout.addWidget(Divider("Separation"))
        self._sep_mode = Field(
            "Separation model", "engineering",
            options=[
                ("engineering", "Engineering — sigmoid grade curve"),
                ("physics",     "Physics — Stokes settling"),
            ],
        )
        self._d50 = Field("Cut size d50", 2.0, 0.01, 50.0, 0.1, "mm")
        self._k_sep = Field("Grade slope k", 1.5, 0.1, 10.0, 0.1)
        self._v_ref = Field("Reference velocity", 0.15, 0.01, 1.0, 0.01, "m/s")
        for f in (self._sep_mode, self._d50, self._k_sep, self._v_ref):
            layout.addWidget(f)

        self._d50.changed.connect(self._sync_references)

    def collect_payload(self) -> dict:
        length = self._lenSep.value()
        return {
            "diam":     self._diam.value(),
            "lenSep":   length,
            "len":      length,      # parity with the .tsx spread
            "speedS":   self._speedS.value(),
            "fill2":    self._fill2.value(),
            "feed":     self._feed.value(),
            "rho":      self._rho.value(),
            "rhoA":     self._rhoA.value(),
            "d_p":      self._d_p.value(),
            "d50":      self._d50.value(),
            "k_sep":    self._k_sep.value(),
            "sep_mode": self._sep_mode.value(),
            "v_ref":    self._v_ref.value(),
        }

    # ── results ───────────────────────────────────────────────────────────

    def build_results(self, layout: QVBoxLayout) -> None:
        kpi_host = QWidget()
        grid = QGridLayout(kpi_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        self._kpi_sep = KpiCard("Sep. Efficiency", unit="%")
        self._kpi_d50 = KpiCard("d50 out", unit="mm", col=PRIMARY)
        self._kpi_rot = KpiCard("η rotation", unit="%", col=TEAL)
        self._kpi_tres = KpiCard("t_res", unit="s", col=PURPLE)
        for col, card in enumerate(
            (self._kpi_sep, self._kpi_d50, self._kpi_rot, self._kpi_tres)
        ):
            grid.addWidget(card, 0, col)
            grid.setColumnStretch(col, 1)
        layout.addWidget(kpi_host)

        summary = Card("📊 Separation Summary")
        self._r_sep = summary.add_row(ResultRow("Separation eff.", unit="%"))
        self._r_d10 = summary.add_row(ResultRow("d10 out", unit="mm"))
        self._r_d50 = summary.add_row(ResultRow("d50 out", unit="mm"))
        self._r_d90 = summary.add_row(ResultRow("d90 out", unit="mm"))
        self._r_fines = summary.add_row(ResultRow("Fines fraction", unit="%"))
        self._r_rot = summary.add_row(ResultRow("η rotation", unit="%"))
        self._r_fill = summary.add_row(ResultRow("η fill", unit="%"))
        self._r_time = summary.add_row(ResultRow("η time", unit="%"))
        self._r_tres = summary.add_row(ResultRow("Residence time", unit="s"))
        layout.addWidget(summary)

        self._chart_d50 = AxialChart(
            "d50 Particle Size", "d50", "mm", PRIMARY,
            ref_value=self._d50.value(),
            ref_label=f"Cut {self._d50.value():.2f}mm",
        )
        self._chart_flow = AxialChart(
            "Mass Flow", "mass_flow", "t/h", WARNING,
        )
        for c in (self._chart_d50, self._chart_flow):
            layout.addWidget(c)

    def _sync_references(self) -> None:
        d = self._d50.value()
        self._chart_d50.set_reference(d, f"Cut {d:.2f}mm")

    def apply_result(self, r: dict) -> None:
        summary = r.get("summary") or {}
        sep = r.get("sep")

        def pct(key: str) -> Optional[float]:
            v = r.get(key)
            return None if v is None else v * 100

        self._kpi_sep.set_value(fmt(sep, 1), col=_sep_color(sep))
        self._kpi_d50.set_value(fmt(summary.get("d50_out_mm"), 2), col=PRIMARY)
        self._kpi_rot.set_value(fmt(pct("eta_rot"), 0), col=TEAL)
        self._kpi_tres.set_value(fmt(summary.get("t_res_s"), 0), col=PURPLE)

        self._r_sep.set_value(
            fmt(sep, 1), ok=None if sep is None else sep > 70,
        )
        self._r_d10.set_value(fmt(summary.get("d10_out_mm"), 2))
        self._r_d50.set_value(fmt(summary.get("d50_out_mm"), 2))
        self._r_d90.set_value(fmt(summary.get("d90_out_mm"), 2))
        fines = summary.get("fines_frac")
        self._r_fines.set_value(fmt(None if fines is None else fines * 100, 1))
        self._r_rot.set_value(fmt(pct("eta_rot"), 1))
        self._r_fill.set_value(fmt(pct("eta_fill"), 1))
        self._r_time.set_value(fmt(pct("eta_time"), 1))
        self._r_tres.set_value(fmt(summary.get("t_res_s"), 0))

        history = r.get("history") or []
        for chart in (self._chart_d50, self._chart_flow):
            chart.set_history(history)