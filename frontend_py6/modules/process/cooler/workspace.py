"""
modules/process/cooler/workspace.py — Screw Cooler module
═══════════════════════════════════════════════════════════════════════════
Port of frontend/src/components/pages/CoolerPage.tsx.

Field names verified against backend/api/routes.py :: run_cooler
(lines 636-680), not process_engine.py — solve_system() returns only
{history, final, tr}, and the route assembles the eps_actual / NTU /
Q_actual_kW / summary shape this page reads. See the same note in the
Dryer module.

Payload naming is this module's own dialect and matches run_cooler's
inp.get() reads exactly: `Lc` for length, `speedCool` for RPM, `fillC2`
for fill, `tInC` / `tTgtC` / `coolIn` for temperatures, `d_p_c` / `k_sol_c`
for the particle properties. Every process module names these differently
in the backend contract; do not normalise them.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout

from core.theme import PRIMARY, TEAL, PURPLE
from modules.base import ModuleMeta
from modules.process.common import (
    ModuleShell, Field, Divider, KpiCard, ResultRow, Card, fmt,
)
from modules.process.axial_chart import AxialChart


class CoolerWorkspace(ModuleShell):

    page_id = "cooler"
    endpoint = "cooler"
    meta = ModuleMeta(
        label="Screw Cooler",
        icon="❄️",
        subtitle="NTU-effectiveness · Moving-bed correction · Composite wall resistance",
        group="process",
    )
    empty_desc = (
        "NTU-effectiveness method with moving-bed non-ideality correction. "
        "Composite wall + particle contact resistance tracked per segment."
    )

    # ── inputs ────────────────────────────────────────────────────────────

    def build_inputs(self, layout: QVBoxLayout) -> None:
        layout.addWidget(Divider("Geometry"))
        self._diam = Field("Diameter", 0.4, 0.1, 1.2, 0.05, "m")
        self._Lc = Field("Length", 6.0, 1.0, 40.0, 0.5, "m")
        for f in (self._diam, self._Lc):
            layout.addWidget(f)

        layout.addWidget(Divider("Drive"))
        self._speed = Field("Speed", 40, 5, 120, 1, "RPM")
        self._fill = Field("Fill fraction", 0.35, 0.1, 0.6, 0.05)
        for f in (self._speed, self._fill):
            layout.addWidget(f)

        layout.addWidget(Divider("Feed"))
        self._feed = Field("Feed rate", 5.0, 0.1, 500.0, 1.0, "t/h")
        self._rho = Field("Bulk density", 1.2, 0.1, 3.0, 0.05, "t/m³")
        self._tInC = Field("Material temp in", 200, 20, 800, 5, "°C")
        self._tTgtC = Field("Target temp out", 80, 10, 300, 5, "°C")
        for f in (self._feed, self._rho, self._tInC, self._tTgtC):
            layout.addWidget(f)

        layout.addWidget(Divider("Cooling"))
        self._coolIn = Field("Coolant temperature", 20, -20, 100, 1, "°C")
        self._U = Field("Overall U", 50, 5, 300, 5, "W/m²K")
        for f in (self._coolIn, self._U):
            layout.addWidget(f)

        layout.addWidget(Divider("Material"))
        self._Cp = Field("Cp solid", 900, 200, 4000, 50, "J/kgK")
        self._d_p_c = Field("Particle size", 0.005, 0.0001, 0.05, 0.001, "m",
                            decimals=4)
        self._k_sol_c = Field("k solid", 0.4, 0.05, 2.0, 0.05, "W/mK")
        for f in (self._Cp, self._d_p_c, self._k_sol_c):
            layout.addWidget(f)

        self._tTgtC.changed.connect(self._sync_references)

    def collect_payload(self) -> dict:
        return {
            "diam":      self._diam.value(),
            "Lc":        self._Lc.value(),
            "speedCool": self._speed.value(),
            "fillC2":    self._fill.value(),
            "feed":      self._feed.value(),
            "rho":       self._rho.value(),
            "tInC":      self._tInC.value(),
            "tTgtC":     self._tTgtC.value(),
            "coolIn":    self._coolIn.value(),
            "U":         self._U.value(),
            "Cp":        self._Cp.value(),
            "d_p_c":     self._d_p_c.value(),
            "k_sol_c":   self._k_sol_c.value(),
        }

    # ── results ───────────────────────────────────────────────────────────

    def build_results(self, layout: QVBoxLayout) -> None:
        kpi_host = QWidget()
        grid = QGridLayout(kpi_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        self._kpi_tout = KpiCard("T out", unit="°C")
        self._kpi_eps = KpiCard("ε Effectiveness", unit="%", col=PRIMARY)
        self._kpi_q = KpiCard("Q Actual", unit="kW", col=TEAL)
        self._kpi_ntu = KpiCard("NTU", col=PURPLE)
        for col, card in enumerate(
            (self._kpi_tout, self._kpi_eps, self._kpi_q, self._kpi_ntu)
        ):
            grid.addWidget(card, 0, col)
            grid.setColumnStretch(col, 1)
        layout.addWidget(kpi_host)

        summary = Card("📊 Cooling Summary")
        self._r_tin = summary.add_row(ResultRow("T material in", unit="°C"))
        self._r_tout = summary.add_row(ResultRow("T material out", unit="°C"))
        self._r_target = summary.add_row(ResultRow("Target", unit="°C"))
        self._r_qd = summary.add_row(ResultRow("Q design duty", unit="kW"))
        self._r_qa = summary.add_row(ResultRow("Q achieved", unit="kW"))
        self._r_eps = summary.add_row(ResultRow("Effectiveness ε", unit="%"))
        self._r_ntu = summary.add_row(ResultRow("NTU"))
        self._r_tres = summary.add_row(ResultRow("Residence time", unit="s"))
        self._r_vax = summary.add_row(ResultRow("Axial velocity", unit="m/s"))
        layout.addWidget(summary)

        self._chart_temp = AxialChart(
            "Temperature", "T", "°C", PRIMARY,
            ref_value=self._tTgtC.value(),
            ref_label=f"Target {self._tTgtC.value():.0f}°C",
        )
        self._chart_heat = AxialChart(
            "Cumulative Heat Removed", "Q_cumul", "kW·s", TEAL,
        )
        for c in (self._chart_temp, self._chart_heat):
            layout.addWidget(c)

    def _sync_references(self) -> None:
        t = self._tTgtC.value()
        self._chart_temp.set_reference(t, f"Target {t:.0f}°C")

    def apply_result(self, r: dict) -> None:
        summary = r.get("summary") or {}
        target_met = r.get("target_met")
        eps = r.get("eps_actual")
        eps_pct = None if eps is None else eps * 100

        self._kpi_tout.set_value(
            fmt(summary.get("T_out"), 0), ok=target_met,
            sub=f"target ≤{self._tTgtC.value():.0f}°C",
        )
        self._kpi_eps.set_value(fmt(eps_pct, 1), col=PRIMARY)
        self._kpi_q.set_value(fmt(r.get("Q_actual_kW"), 1), col=TEAL)
        self._kpi_ntu.set_value(fmt(r.get("NTU"), 2), col=PURPLE)

        self._r_tin.set_value(fmt(summary.get("T_in"), 1))
        self._r_tout.set_value(fmt(summary.get("T_out"), 1), ok=target_met)
        self._r_target.set_value(f"≤{fmt(summary.get('target_C'), 0)}")
        self._r_qd.set_value(fmt(r.get("Qd_target"), 1))
        self._r_qa.set_value(fmt(r.get("Q_actual_kW"), 1))
        self._r_eps.set_value(fmt(eps_pct, 1))
        self._r_ntu.set_value(fmt(r.get("NTU"), 3))
        self._r_tres.set_value(fmt(summary.get("t_res_s"), 0))
        self._r_vax.set_value(fmt(summary.get("v_ax"), 4))

        history = r.get("history") or []
        for chart in (self._chart_temp, self._chart_heat):
            chart.set_history(history)