"""
modules/process/compactor/workspace.py — Screw Compactor module
═══════════════════════════════════════════════════════════════════════════
Port of frontend/src/components/pages/CompactorPage.tsx.

Field names verified against backend/api/routes.py :: run_compactor
(lines 792-828), not process_engine.py.

Endpoint vs module_type: the HTTP route is /process/compactor but calls
solve_system(payload, "compact") internally. `endpoint` below is the URL
segment, which is what api_client.fetch_process() needs.

Speed key: run_compactor's docstring lists `fN_max`, but its code reads
payload.get("Nc", 30), and the .tsx state uses `Nc`. solve_system() accepts
either via its fallback chain. `Nc` is sent because that is what both the
route body and the web app actually use — the docstring is stale.

Axial velocity is read from r["tr"]["v_ax"] rather than the summary,
matching the .tsx (`r?.tr?.v_ax`). The value also appears at
summary.v_ax; both are the same number, and the .tsx path is kept so a
future change to either is visible as a difference rather than masked.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout

from core.theme import PRIMARY, WARNING, DANGER
from modules.base import ModuleMeta
from modules.process.common import (
    ModuleShell, Field, Divider, KpiCard, ResultRow, Card, fmt,
)
from modules.process.axial_chart import AxialChart


class CompactorWorkspace(ModuleShell):

    page_id = "compactor"
    endpoint = "compactor"
    meta = ModuleMeta(
        label="Screw Compactor",
        icon="🗜️",
        subtitle="Janssen back-pressure · Power-law compaction · Plug risk",
        group="process",
    )
    empty_desc = (
        "Janssen back-pressure model with power-law stress-density "
        "compaction. Plug risk assessment at σ>200kPa. Conservative "
        "preliminary design."
    )

    # ── inputs ────────────────────────────────────────────────────────────

    def build_inputs(self, layout: QVBoxLayout) -> None:
        layout.addWidget(Divider("Geometry"))
        self._diam = Field("Diameter", 0.3, 0.1, 1.2, 0.05, "m")
        self._fLen = Field("Length", 2.0, 0.5, 20.0, 0.5, "m")
        for f in (self._diam, self._fLen):
            layout.addWidget(f)

        layout.addWidget(Divider("Drive"))
        self._Nc = Field("Speed", 20, 2, 120, 1, "RPM")
        self._fFill = Field("Fill fraction", 0.60, 0.1, 0.95, 0.05)
        for f in (self._Nc, self._fFill):
            layout.addWidget(f)

        layout.addWidget(Divider("Feed"))
        self._feed = Field("Feed rate", 3.0, 0.1, 500.0, 1.0, "t/h")
        self._fRho = Field("Bulk density in", 0.4, 0.05, 3.0, 0.05, "t/m³")
        self._tgtR = Field("Target density", 0.85, 0.1, 3.0, 0.05, "t/m³")
        for f in (self._feed, self._fRho, self._tgtR):
            layout.addWidget(f)

        layout.addWidget(Divider("Compaction"))
        self._mu_wall = Field("Wall friction μ", 0.35, 0.05, 1.0, 0.05)
        self._k_lat = Field("Lateral stress ratio k", 0.45, 0.1, 1.0, 0.05)
        self._alpha_c = Field("Compaction α", 0.005, 0.0001, 0.05, 0.001,
                              decimals=4)
        for f in (self._mu_wall, self._k_lat, self._alpha_c):
            layout.addWidget(f)

        self._tgtR.changed.connect(self._sync_references)

    def collect_payload(self) -> dict:
        length = self._fLen.value()
        return {
            "diam":    self._diam.value(),
            "fLen":    length,
            "len":     length,      # parity with the .tsx spread
            "Nc":      self._Nc.value(),
            "fFill":   self._fFill.value(),
            "feed":    self._feed.value(),
            "fRho":    self._fRho.value(),
            "tgtR":    self._tgtR.value(),
            "mu_wall": self._mu_wall.value(),
            "k_lat":   self._k_lat.value(),
            "alpha_c": self._alpha_c.value(),
        }

    # ── results ───────────────────────────────────────────────────────────

    def build_results(self, layout: QVBoxLayout) -> None:
        kpi_host = QWidget()
        grid = QGridLayout(kpi_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        self._kpi_rho = KpiCard("ρ out", unit="t/m³")
        self._kpi_cr = KpiCard("CR", col=PRIMARY, sub="compression ratio")
        self._kpi_sigma = KpiCard("σ Janssen", unit="kPa", col=WARNING)
        self._kpi_plug = KpiCard("Plug Risk")
        for col, card in enumerate(
            (self._kpi_rho, self._kpi_cr, self._kpi_sigma, self._kpi_plug)
        ):
            grid.addWidget(card, 0, col)
            grid.setColumnStretch(col, 1)
        layout.addWidget(kpi_host)

        summary = Card("📊 Compaction Summary")
        self._r_rho_in = summary.add_row(ResultRow("ρ in", unit="t/m³"))
        self._r_rho_out = summary.add_row(ResultRow("ρ out", unit="t/m³"))
        self._r_cr = summary.add_row(ResultRow("CR"))
        self._r_sigma = summary.add_row(ResultRow("σ Janssen", unit="kPa"))
        self._r_tau = summary.add_row(ResultRow("τ shear", unit="kPa"))
        self._r_torque = summary.add_row(ResultRow("Torque", unit="Nm"))
        self._r_plug = summary.add_row(ResultRow("Plugging risk"))
        self._r_vax = summary.add_row(ResultRow("Axial velocity", unit="m/s"))
        layout.addWidget(summary)

        self._chart_sigma = AxialChart(
            "Back Pressure σ", "sigma", "kPa", WARNING,
        )
        self._chart_rho = AxialChart(
            "Bulk Density", "rho", "t/m³", PRIMARY,
            ref_value=self._tgtR.value(),
            ref_label=f"Target {self._tgtR.value():.2f}",
        )
        for c in (self._chart_sigma, self._chart_rho):
            layout.addWidget(c)

    def _sync_references(self) -> None:
        t = self._tgtR.value()
        self._chart_rho.set_reference(t, f"Target {t:.2f}")

    def apply_result(self, r: dict) -> None:
        summary = r.get("summary") or {}
        rho_out = r.get("rho_out")
        plugging = r.get("plugging")
        target = self._tgtR.value()
        # .tsx: ok={r.rho_out >= inp.tgtR*0.95} — 5% under target still passes
        rho_ok = None if rho_out is None else rho_out >= target * 0.95

        self._kpi_rho.set_value(
            fmt(rho_out, 3), ok=rho_ok, sub=f"target {target:.2f}",
        )
        self._kpi_cr.set_value(
            fmt(r.get("CR"), 2), col=PRIMARY, sub="compression ratio",
        )
        self._kpi_sigma.set_value(
            fmt(r.get("sigma_janssen"), 1),
            col=DANGER if plugging else WARNING,
        )
        self._kpi_plug.set_value(
            "⚠ HIGH" if plugging else "✓ OK",
            ok=None if plugging is None else not plugging,
        )

        self._r_rho_in.set_value(fmt(summary.get("rho_in"), 3))
        self._r_rho_out.set_value(fmt(rho_out, 3), ok=rho_ok)
        self._r_cr.set_value(fmt(r.get("CR"), 3))
        self._r_sigma.set_value(
            fmt(r.get("sigma_janssen"), 1),
            ok=None if plugging is None else not plugging,
        )
        self._r_tau.set_value(fmt(summary.get("tau_shear_kPa"), 2))
        self._r_torque.set_value(fmt(summary.get("torque_Nm"), 0))
        self._r_plug.set_value(
            "HIGH — reduce speed/fill" if plugging else "OK",
            ok=None if plugging is None else not plugging,
        )
        self._r_vax.set_value(fmt((r.get("tr") or {}).get("v_ax"), 4))

        history = r.get("history") or []
        for chart in (self._chart_sigma, self._chart_rho):
            chart.set_history(history)