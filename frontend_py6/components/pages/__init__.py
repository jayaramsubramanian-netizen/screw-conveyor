"""
components/pages/__init__.py — one QWidget per application page.
All honest Placeholders at this stage, replaced one by one in later sessions.
"""
from components.widgets import Placeholder


class CalcPage(Placeholder):
    def __init__(self, parent=None):
        super().__init__(
            "🔩  Screw Conveyor Designer",
            "InputSidebarPanel + ScrewViz2D + ResultsCards — next to implement",
            parent,
        )


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


class MixerPage(Placeholder):
    def __init__(self, parent=None):
        super().__init__(
            "🌀  Screw Mixer",
            "POST /api/calculate/process  module=mixer",
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
            "GET /api/materials  →  24-material table",
            parent,
        )


class ManualPage(Placeholder):
    def __init__(self, parent=None):
        super().__init__(
            "📘  User Manual",
            "Engineering basis + CEMA 7th Ed. references",
            parent,
        )