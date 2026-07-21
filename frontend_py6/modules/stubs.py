"""
modules/stubs.py — placeholder workspaces for modules not yet ported
═══════════════════════════════════════════════════════════════════════════
TEMPORARY. Every class here is a stand-in that satisfies the
ModuleWorkspace contract so the registry stays uniform and the shell needs
no "is this module real yet?" branch.

When a module is ported for real, it moves to its own package
(modules/<family>/<name>/workspace.py, as Mixer did) and its stub is
deleted from this file. When the file is empty, delete the file.

These are deliberately kept in one place rather than as nine near-empty
packages: nine directories containing a four-line class each would imply
structure that does not exist yet, and would have to be rewritten anyway
once the real module lands with its own panels and helpers.

Remaining, roughly in porting order:

    separator, compactor        → modules/process/<name>/  — scalar results
                                  only, no history array, so no AxialChart
    feeder                      → modules/feeder/   (VL series, §2.3)
    family                      → modules/family/
    db                          → modules/database/ — canonical source still
                                  unresolved: root DatabasePage.jsx (3,281
                                  lines) vs frontend/src DatabasePage.tsx
                                  (898 lines)
    help                        → modules/manual/
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout

from core.widgets import Placeholder
from modules.base import ModuleWorkspace, ModuleMeta


class StubWorkspace(ModuleWorkspace):
    """Renders an honest placeholder. Subclasses set page_id, meta, note."""

    abstract = True
    note: str = "Not yet ported."

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(Placeholder(
            f"{self.meta.icon}  {self.meta.label}", self.note,
        ))


class FamilyWorkspace(StubWorkspace):
    page_id = "family"
    meta = ModuleMeta(label="Family Designer", icon="📊", group="conveyor")
    note = "Source: FamilyPage.tsx (447 lines) → modules/family/"


class FeederWorkspace(StubWorkspace):
    page_id = "feeder"
    meta = ModuleMeta(label="Feeder / Doser", icon="🎚️", group="conveyor")
    note = "Source: FeederPage.tsx (299 lines) → modules/feeder/  ·  VL series"


class SeparatorWorkspace(StubWorkspace):
    page_id = "separator"
    meta = ModuleMeta(label="Separator", icon="🔀", group="process")
    note = "Source: SeparatorPage.tsx → modules/process/separator/"


class CompactorWorkspace(StubWorkspace):
    page_id = "compactor"
    meta = ModuleMeta(label="Compactor", icon="🗜️", group="process")
    note = "Source: CompactorPage.tsx → modules/process/compactor/"


class DatabaseWorkspace(StubWorkspace):
    page_id = "db"
    meta = ModuleMeta(label="Material Database", icon="🗄️", group="reference")
    note = "Canonical source unresolved — DatabasePage.jsx (3,281) vs .tsx (898)"


class ManualWorkspace(StubWorkspace):
    page_id = "help"
    meta = ModuleMeta(label="User Manual", icon="📘", group="reference")
    note = "Source: ManualPage.tsx → modules/manual/  ·  renders manual.html"