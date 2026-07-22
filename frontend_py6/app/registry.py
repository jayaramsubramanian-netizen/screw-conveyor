"""
app/registry.py — the module table
═══════════════════════════════════════════════════════════════════════════
The one place a module is registered. Adding a main-menu application means
importing its workspace class and appending it to MODULES; nothing else in
the application needs to change.

This replaces three parallel structures that previously had to be kept in
sync by hand:

    PAGE_REGISTRY   list of (page_id, PageClass), excluding the conveyor
                    because the conveyor was not a page but the shell itself
    PROCESS_PAGES   a set of six ids, consulted by run_calculation() to pick
                    between fetch_process() and fetch_design()
    PAGE_META       label/icon/group dict in theme.py, keyed by the same ids

A module's identity now travels with the module — page_id and meta are
class attributes on the workspace — so the registry is a list of classes
rather than a mapping that can drift from what it describes. PROCESS_PAGES
disappears entirely: each workspace routes its own backend call, so nothing
outside a module needs to know which endpoint family it belongs to.

Order here is menu order.
"""

from __future__ import annotations

from typing import Iterator, Sequence

from modules.base import ModuleWorkspace
from modules.conveyor.workspace import ConveyorWorkspace
from modules.process.mixer import MixerWorkspace
from modules.process.dryer import DryerWorkspace
from modules.process.cooler import CoolerWorkspace
from modules.process.reactor import ReactorWorkspace
from modules.process.separator import SeparatorWorkspace
from modules.process.compactor import CompactorWorkspace
from modules.process.feeder import FeederWorkspace
from modules.family import FamilyWorkspace
from modules.stubs import DatabaseWorkspace, ManualWorkspace


MODULES: Sequence[type[ModuleWorkspace]] = (
    # conveyor group
    ConveyorWorkspace,
    FamilyWorkspace,
    FeederWorkspace,
    # process group
    MixerWorkspace,
    DryerWorkspace,
    CoolerWorkspace,
    SeparatorWorkspace,
    ReactorWorkspace,
    CompactorWorkspace,
    # reference group
    DatabaseWorkspace,
    ManualWorkspace,
)

#: The module shown at startup.
DEFAULT_MODULE = ConveyorWorkspace.page_id


def by_id() -> dict[str, type[ModuleWorkspace]]:
    """
    page_id → workspace class.

    Raises on a duplicate id rather than letting one module silently
    overwrite another and vanish from the menu. ModuleWorkspace already
    rejects an empty page_id at class-definition time; this covers the
    other half — two modules that both declare a valid but identical id.
    """
    table: dict[str, type[ModuleWorkspace]] = {}
    for cls in MODULES:
        if cls.page_id in table:
            raise ValueError(
                f"Duplicate page_id {cls.page_id!r}: "
                f"{table[cls.page_id].__name__} and {cls.__name__}"
            )
        table[cls.page_id] = cls
    return table


def grouped() -> Iterator[tuple[str, list[type[ModuleWorkspace]]]]:
    """
    Yield (group_name, [workspace classes]) in registration order, for
    building the menu bar. Groups appear in the order first encountered.
    """
    order: list[str] = []
    buckets: dict[str, list[type[ModuleWorkspace]]] = {}
    for cls in MODULES:
        g = cls.meta.group
        if g not in buckets:
            buckets[g] = []
            order.append(g)
        buckets[g].append(cls)
    for g in order:
        yield g, buckets[g]