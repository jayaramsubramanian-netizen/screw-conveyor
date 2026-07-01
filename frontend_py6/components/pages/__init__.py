"""
pages/__init__.py — one QWidget subclass per application page.

Each class is an honest Placeholder at this stage.  They will be
replaced with real implementations one by one, starting with CalcPage.
"""

from components.widgets import Placeholder
from theme import BG, TEXT3, MUTED, BORDER, ACCENT, PANEL, PANEL2


class CalcPage(Placeholder):
    """🔩 Screw Conveyor Designer — main calculator page.
    Will host: InputSidebar | ScrewViz2D | ResultsPanel | StatusPanel
    """
    def __init__(self, parent=None):
        super().__init__(
            "🔩  Screw Conveyor Designer",
            "CalcPage — input sidebar + 2D visualiser + results cards",
            parent,
        )


class FamilyPage(Placeholder):
    """📊 Family Designer — diameter × speed performance matrix."""
    def __init__(self, parent=None):
        super().__init__(
            "📊  Family Designer",
            "FamilyPage — D×N performance matrix + capacity curves",
            parent,
        )


class FeederPage(Placeholder):
    """🎚️ Feeder / Doser — live-bottom and hopper-extraction design."""
    def __init__(self, parent=None):
        super().__init__(
            "🎚️  Feeder / Doser",
            "FeederPage — live-bottom feeder + hopper extraction",
            parent,
        )


class MixerPage(Placeholder):
    """🌀 Screw Mixer — Lacey M, RTD, Froude regime, twin/triple shaft."""
    def __init__(self, parent=None):
        super().__init__(
            "🌀  Screw Mixer",
            "MixerPage — Lacey mixing index + RPM regime map",
            parent,
        )


class DryerPage(Placeholder):
    """🌡️ Screw Dryer — LMTD, two-zone kinetics, U_eff with solids resistance."""
    def __init__(self, parent=None):
        super().__init__(
            "🌡️  Screw Dryer",
            "DryerPage — LMTD + Arrhenius drying kinetics",
            parent,
        )


class CoolerPage(Placeholder):
    """❄️ Screw Cooler — NTU-effectiveness, moving-bed correction."""
    def __init__(self, parent=None):
        super().__init__(
            "❄️  Screw Cooler",
            "CoolerPage — NTU-effectiveness + axial T(x) profile",
            parent,
        )


class SeparatorPage(Placeholder):
    """🔀 Separator — Stokes settling, physics-based d50, grade curve."""
    def __init__(self, parent=None):
        super().__init__(
            "🔀  Separator",
            "SeparatorPage — Stokes d50 + grade efficiency curve",
            parent,
        )


class ReactorPage(Placeholder):
    """⚗️ Screw Reactor — Axial Dispersion, Damköhler, Arrhenius k(T)."""
    def __init__(self, parent=None):
        super().__init__(
            "⚗️  Screw Reactor",
            "ReactorPage — Axial Dispersion Model + Arrhenius kinetics",
            parent,
        )


class CompactorPage(Placeholder):
    """🗜️ Compactor — Janssen pressure, torque from shear stress."""
    def __init__(self, parent=None):
        super().__init__(
            "🗜️  Compactor",
            "CompactorPage — Janssen σ(x) + density profile",
            parent,
        )


class DatabasePage(Placeholder):
    """🗄️ Material Database — 24-material table with properties."""
    def __init__(self, parent=None):
        super().__init__(
            "🗄️  Material Database",
            "DatabasePage — bulk density, abrasion, λ, fill, moisture",
            parent,
        )


class ManualPage(Placeholder):
    """📘 User Manual — engineering basis, CEMA references, disclaimer."""
    def __init__(self, parent=None):
        super().__init__(
            "📘  User Manual",
            "ManualPage — engineering basis + CEMA 7th Ed. references",
            parent,
        )