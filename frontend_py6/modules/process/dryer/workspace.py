"""
modules/process/dryer/workspace.py — Screw Dryer module
═══════════════════════════════════════════════════════════════════════════
Port of frontend/src/components/pages/DryerPage.tsx.

Canonical source is the .tsx, not app-standalone.html — see
modules/process/__init__.py. Field names below were verified against the
authoritative response shape, which for this module is assembled in
backend/api/routes.py (run_dryer, lines 586-634) rather than in
process_engine.py: solve_system() returns only {history, final, tr}, and
the route flattens that into the mOut_actual / eff / summary shape the page
actually reads. Reading process_engine.py alone would have produced a page
bound to keys that never reach the client.

Input naming note: this module's payload keys are camelCase and abbreviated
(diam, len, speedDry, fillDry, tTr, mIn, mOut) rather than the mixer's
short lowercase (D, L, N, rho, fill). That inconsistency is in the backend
contract, not introduced here — run_dryer reads exactly these names, so the
payload matches them exactly. Do not "tidy" them.

`len` shadows the builtin as a dict key only, never as a variable.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout

from core.theme import PRIMARY, WARNING, PURPLE, DANGER, TEAL
from modules.base import ModuleMeta
from modules.process.common import (
    ModuleShell, Field, Divider, KpiCard, ResultRow, Card, fmt,
)
from modules.process.axial_chart import AxialChart


class DryerWorkspace(ModuleShell):

    page_id = "dryer"
    endpoint = "dryer"
    meta = ModuleMeta(
        label="Screw Dryer",
        icon="🌡️",
        subtitle="LMTD heat transfer · Two-phase drying kinetics · D_factor scale correction",
        group="process",
    )
    empty_desc = (
        "LMTD heat transfer with two-phase drying kinetics. Constant-rate "
        "phase (heat limited) and falling-rate phase (diffusion limited) "
        "tracked per segment."
    )

    # ── inputs ────────────────────────────────────────────────────────────

    def build_inputs(self, layout: QVBoxLayout) -> None:
        layout.addWidget(Divider("Geometry"))
        self._diam = Field("Diameter", 0.4, 0.1, 1.2, 0.05, "m")
        self._len = Field("Length", 6.0, 1.0, 40.0, 0.5, "m")
        for f in (self._diam, self._len):
            layout.addWidget(f)

        layout.addWidget(Divider("Drive"))
        self._speed = Field("Speed", 40, 5, 120, 1, "RPM")
        self._fill = Field("Fill fraction", 0.35, 0.1, 0.6, 0.05)
        for f in (self._speed, self._fill):
            layout.addWidget(f)

        layout.addWidget(Divider("Feed"))
        self._feed = Field("Feed rate", 5.0, 0.1, 500.0, 1.0, "t/h")
        self._rho = Field("Bulk density", 1.2, 0.1, 3.0, 0.05, "t/m³")
        self._mIn = Field("Moisture in", 18, 1, 80, 1, "% wb")
        self._mOut = Field("Target moisture", 5.0, 0.1, 20.0, 0.5, "% wb")
        for f in (self._feed, self._rho, self._mIn, self._mOut):
            layout.addWidget(f)

        layout.addWidget(Divider("Thermal"))
        self._tTr = Field("Wall temperature", 120, 40, 400, 5, "°C")
        self._tIn = Field("Feed temperature", 20, 0, 100, 1, "°C")
        self._U = Field("Overall U", 50, 5, 300, 5, "W/m²K")
        for f in (self._tTr, self._tIn, self._U):
            layout.addWidget(f)

        layout.addWidget(Divider("Material"))
        self._d_p = Field("Particle size", 0.003, 0.0001, 0.05, 0.001, "m",
                          decimals=4)
        self._k_solid = Field("k solid", 0.3, 0.05, 2.0, 0.05, "W/mK")
        self._CpDry = Field("Cp dry solid", 1800, 200, 4000, 50, "J/kgK")
        for f in (self._d_p, self._k_solid, self._CpDry):
            layout.addWidget(f)

        # Target moisture and wall temperature drive the two chart reference
        # lines; keep them live so the lines track the form as the .tsx does
        # (it passes inp.mOut / inp.tTr straight into AxialChart props).
        self._mOut.changed.connect(self._sync_references)
        self._tTr.changed.connect(self._sync_references)

    def collect_payload(self) -> dict:
        return {
            "diam":     self._diam.value(),
            "len":      self._len.value(),
            "speedDry": self._speed.value(),
            "fillDry":  self._fill.value(),
            "feed":     self._feed.value(),
            "rho":      self._rho.value(),
            "tIn":      self._tIn.value(),
            "mIn":      self._mIn.value(),
            "mOut":     self._mOut.value(),
            "tTr":      self._tTr.value(),
            "U":        self._U.value(),
            "d_p":      self._d_p.value(),
            "k_solid":  self._k_solid.value(),
            "CpDry":    self._CpDry.value(),
        }

    # ── results ───────────────────────────────────────────────────────────

    def build_results(self, layout: QVBoxLayout) -> None:
        kpi_host = QWidget()
        grid = QGridLayout(kpi_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        self._kpi_mout = KpiCard("Moisture Out", unit="%")
        self._kpi_energy = KpiCard("Energy Intensity", unit="kWh/kg", col=WARNING)
        self._kpi_eff = KpiCard("Thermal Eff.", unit="%", col=PRIMARY)
        self._kpi_tout = KpiCard("T out", unit="°C", col=PURPLE)
        for col, card in enumerate(
            (self._kpi_mout, self._kpi_energy, self._kpi_eff, self._kpi_tout)
        ):
            grid.addWidget(card, 0, col)
            grid.setColumnStretch(col, 1)
        layout.addWidget(kpi_host)

        summary = Card("📊 Drying Summary")
        self._r_min = summary.add_row(ResultRow("Moisture in", unit="%"))
        self._r_mout = summary.add_row(ResultRow("Moisture out", unit="%"))
        self._r_target = summary.add_row(ResultRow("Target", unit="%"))
        self._r_wevap = summary.add_row(ResultRow("Water evap'd", unit="t/h"))
        self._r_duty = summary.add_row(ResultRow("Heat duty", unit="kW"))
        self._r_kwh = summary.add_row(ResultRow("kWh/kg water", unit="kWh/kg"))
        self._r_eff = summary.add_row(ResultRow("Thermal eff.", unit="%"))
        self._r_tres = summary.add_row(ResultRow("Residence time", unit="s"))
        self._r_vax = summary.add_row(ResultRow("Axial velocity", unit="m/s"))
        layout.addWidget(summary)

        self._chart_moisture = AxialChart(
            "Moisture", "moisture", "% wb", PRIMARY,
            ref_value=self._mOut.value(), ref_label=f"Target {self._mOut.value():.1f}%",
        )
        self._chart_temp = AxialChart(
            "Temperature", "T", "°C", DANGER,
            ref_value=self._tTr.value(), ref_label=f"Wall {self._tTr.value():.0f}°C",
        )
        self._chart_heat = AxialChart(
            "Cumulative Heat", "Q_cumul", "kW·s", WARNING,
        )
        for c in (self._chart_moisture, self._chart_temp, self._chart_heat):
            layout.addWidget(c)

    def _sync_references(self) -> None:
        m = self._mOut.value()
        t = self._tTr.value()
        self._chart_moisture.set_reference(m, f"Target {m:.1f}%")
        self._chart_temp.set_reference(t, f"Wall {t:.0f}°C")

    def apply_result(self, r: dict) -> None:
        summary = r.get("summary") or {}
        target_met = r.get("target_met")
        m_out = r.get("mOut_actual")
        eff = r.get("eff")
        eff_pct = None if eff is None else eff * 100

        self._kpi_mout.set_value(
            fmt(m_out, 1), ok=target_met,
            sub=f"target ≤{self._mOut.value():.1f}%",
        )
        self._kpi_energy.set_value(fmt(r.get("kWh_kgWater"), 3), col=WARNING)
        self._kpi_eff.set_value(fmt(eff_pct, 1), col=PRIMARY)
        self._kpi_tout.set_value(fmt(summary.get("T_out"), 0), col=PURPLE)

        self._r_min.set_value(fmt(summary.get("moisture_in_pct"), 1))
        self._r_mout.set_value(fmt(m_out, 2), ok=target_met)
        self._r_target.set_value(f"≤{fmt(summary.get('target_pct'), 1)}")
        self._r_wevap.set_value(fmt(summary.get("W_evap_tph"), 3))
        self._r_duty.set_value(fmt(summary.get("Q_total_kW"), 1))
        self._r_kwh.set_value(fmt(r.get("kWh_kgWater"), 3))
        self._r_eff.set_value(fmt(eff_pct, 1))
        self._r_tres.set_value(fmt(summary.get("t_res_s"), 0))
        self._r_vax.set_value(fmt(summary.get("v_ax"), 4))

        history = r.get("history") or []
        for chart in (self._chart_moisture, self._chart_temp, self._chart_heat):
            chart.set_history(history)