"""
components/pages/__init__.py — one QWidget per application page.

CalcPage is now InputSidebarPanel in components/pages/calc_page.py.
Mixer has migrated out to modules/process/mixer/ as MixerWorkspace, the
first implementation of the modules/base.py contract. The remaining five
process modules follow it there, not here.
Everything left in this file is an honest Placeholder until its session
arrives; this package dissolves in step 4.
"""
from core.widgets import Placeholder

__all__ = [
    "FamilyPage", "FeederPage", "DryerPage", "CoolerPage",
    "SeparatorPage", "ReactorPage", "CompactorPage", "DatabasePage",
    "ManualPage",
]


# ── Non-calc pages ────────────────────────────────────────────────────────

class FamilyPage(Placeholder):
    def __init__(self, parent=None):
        super().__init__(
            "📊  Family Designer",
            "D×N performance matrix + capacity curves",
            parent,
        )


class FeederPage(Placeholder):
    def __init__(self, parent=None):
        super().__init__(
            "🎚️  Feeder / Doser",
            "Live-bottom feeder + hopper extraction",
            parent,
        )


class DryerPage(Placeholder):
    def __init__(self, parent=None):
        super().__init__(
            "🌡️  Screw Dryer",
            "POST /api/calculate/process  module=dryer",
            parent,
        )


class CoolerPage(Placeholder):
    def __init__(self, parent=None):
        super().__init__(
            "❄️  Screw Cooler",
            "POST /api/calculate/process  module=cooler",
            parent,
        )


class SeparatorPage(Placeholder):
    def __init__(self, parent=None):
        super().__init__(
            "🔀  Separator",
            "POST /api/calculate/process  module=sep",
            parent,
        )


class ReactorPage(Placeholder):
    def __init__(self, parent=None):
        super().__init__(
            "⚗️  Screw Reactor",
            "POST /api/calculate/process  module=reactor",
            parent,
        )


class CompactorPage(Placeholder):
    def __init__(self, parent=None):
        super().__init__(
            "🗜️  Compactor",
            "POST /api/calculate/process  module=compact",
            parent,
        )


class DatabasePage(Placeholder):
    def __init__(self, parent=None):
        super().__init__(
            "🗄️  Material Database",
            "GET /api/materials  →  full material table",
            parent,
        )


class ManualPage(Placeholder):
    def __init__(self, parent=None):
        super().__init__(
            "📘  User Manual",
            "Engineering basis + CEMA 7th Ed. references",
            parent,
        )