"""
check_structure.py — where is this tree in the restructure?
═══════════════════════════════════════════════════════════════════════════
Run from inside frontend_py6:

    python check_structure.py

Reports which files are present, which leftovers must still be deleted, and
whether the tree will actually start. Written because two copies of this
project exist on disk (D:\\Projects\\Vectrix and D:\\Personal Documents\\
Screw Conveyor\\screw-conveyor) and edits applied to one will look like they
silently failed if the other is the one being run.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# (path, human label) — must exist after step 4 + Dryer
REQUIRED = [
    ("core/theme.py",                        "core: theme"),
    ("core/api_client.py",                   "core: api_client"),
    ("core/widgets.py",                      "core: widgets"),
    ("modules/base.py",                      "contract: ModuleWorkspace"),
    ("modules/conveyor/workspace.py",        "conveyor workspace"),
    ("modules/conveyor/sidebar.py",          "conveyor sidebar"),
    ("modules/process/common.py",            "process shell"),
    ("modules/process/axial_chart.py",       "axial chart"),
    ("modules/process/mixer/workspace.py",   "mixer"),
    ("modules/process/dryer/workspace.py",   "dryer"),
    ("modules/process/cooler/workspace.py",  "cooler"),
    ("modules/process/reactor/workspace.py", "reactor"),
    ("modules/process/separator/workspace.py","separator"),
    ("modules/process/compactor/workspace.py","compactor"),
    ("modules/process/feeder/workspace.py",  "feeder"),
    ("modules/process/feeder/calibration_chart.py", "feeder calib chart"),
    ("modules/family/workspace.py",          "family designer"),
    ("modules/database/workspace.py",        "database browser"),
    ("modules/manual/workspace.py",          "manual viewer"),
    ("modules/conveyor/detail_panels.py",    "checks/wear/structural/materials"),
    ("app/chrome.py",                        "chrome"),
    ("app/registry.py",                      "registry"),
    ("app/shell.py",                         "shell host"),
    ("app/main.py",                          "entry point"),
]

# (path, why it must go)
LEFTOVERS = [
    ("main.py",                    "superseded by app/main.py"),
    ("modules/stubs.py",           "all modules ported — no stubs remain"),
    ("components",                 "superseded by app/ and modules/"),
    ("theme.py",                   "moved to core/theme.py"),
    ("api_client.py",              "moved to core/api_client.py"),
    ("components/shell.py",        "moved to app/chrome.py"),
    ("components/widgets.py",      "moved to core/widgets.py"),
    ("components/screw_viz.py",    "moved to modules/conveyor/"),
    ("components/model_number.py", "moved to modules/conveyor/"),
    ("components/pages",           "moved to modules/"),
]


def main() -> int:
    print(f"Checking: {HERE}\n")

    missing = []
    print("REQUIRED")
    for rel, label in REQUIRED:
        ok = os.path.exists(os.path.join(HERE, rel))
        print(f"  {'OK  ' if ok else 'MISS'}  {rel:38s} {label}")
        if not ok:
            missing.append(rel)

    stale = []
    print("\nMUST BE DELETED")
    for rel, why in LEFTOVERS:
        present = os.path.exists(os.path.join(HERE, rel))
        if present:
            stale.append(rel)
        print(f"  {'STALE' if present else 'gone '}  {rel:38s} {why}")

    caches = [
        os.path.join(r, d)
        for r, ds, _ in os.walk(HERE) for d in ds if d == "__pycache__"
    ]
    print(f"\n__pycache__ directories: {len(caches)}"
          f"{'  <- delete these; stale .pyc can resolve a moved module'
             if caches else ''}")

    # A file can be present but STALE — an older revision from another copy
    # of the project. Path checks miss that. These markers are strings that
    # only exist in the current revision of a given file; if the file is
    # there but the marker is not, it is out of date.
    print("\nFRESHNESS (present-but-stale detection)")
    markers = [
        ("core/theme.py",              "PROCESS_ACCENT",
         "pre-step-4 theme — missing PROCESS_ACCENT token"),
        ("core/widgets.py",            "from core.theme import",
         "pre-restructure widgets — still imports `from theme import`"),
        ("core/api_client.py",         "def fetch_family",
         "api_client older than the family-designer wiring"),
        ("app/registry.py",            "from modules.process.feeder import",
         "registry still importing Feeder/Separator/Compactor from stubs"),
        ("app/shell.py",               "_on_apply_requested",
         "shell missing cross-module apply mediator"),
        ("modules/base.py",            "apply_requested",
         "base missing cross-module signal"),
        ("modules/conveyor/workspace.py", "def receive_payload",
         "conveyor missing export/receive hooks"),
        ("modules/conveyor/axial_panel.py", "type: ignore",
         "axial_panel missing pyqtgraph type-ignore fixes"),
        ("modules/process/common.py",  "def set_options",
         "process common missing Field.set_options / WarningsPanel"),
        ("app/registry.py",            "from modules.database import",
         "registry still importing Database from stubs"),
        ("modules/conveyor/workspace.py", "MaterialsPanel",
         "conveyor missing the four detail-tab panels"),
    ]
    stale_content = []
    for rel, marker, why in markers:
        path = os.path.join(HERE, rel)
        if not os.path.exists(path):
            continue        # already reported as MISSING above
        text = open(path, encoding="utf-8", errors="replace").read()
        fresh = marker in text
        print(f"  {'OK  ' if fresh else 'OLD '}  {rel:38s} "
              f"{'' if fresh else why}")
        if not fresh:
            stale_content.append(rel)

    print("\n" + "=" * 60)
    if missing:
        print(f"NOT READY — {len(missing)} required file(s) missing:")
        for m in missing:
            print(f"    {m}")
    if stale_content:
        print(f"NOT READY — {len(stale_content)} file(s) are OUT OF DATE "
              f"(present but an older revision):")
        for s in stale_content:
            print(f"    {s}")
    if stale:
        print(f"NOT READY — {len(stale)} leftover(s) to delete:")
        for s in stale:
            print(f"    {s}")
    if not missing and not stale:
        print("Structure looks correct. Start with:  python -m app.main")

    # Does it actually import?
    print("\nIMPORT TEST")
    sys.path.insert(0, HERE)
    try:
        from app.registry import MODULES        # noqa: F401
        print(f"  OK    app.registry imports — {len(MODULES)} modules")
        for cls in MODULES:
            print(f"          {cls.page_id:10s} {cls.__name__}")
    except Exception as exc:
        print(f"  FAIL  {type(exc).__name__}: {exc}")
        return 1
    return 0 if not (missing or stale) else 1


if __name__ == "__main__":
    sys.exit(main())