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
    ("modules/stubs.py",                     "stub workspaces"),
    ("modules/conveyor/workspace.py",        "conveyor workspace"),
    ("modules/conveyor/sidebar.py",          "conveyor sidebar"),
    ("modules/process/common.py",            "process shell"),
    ("modules/process/axial_chart.py",       "axial chart"),
    ("modules/process/mixer/workspace.py",   "mixer"),
    ("modules/process/dryer/workspace.py",   "dryer"),
    ("app/chrome.py",                        "chrome"),
    ("app/registry.py",                      "registry"),
    ("app/shell.py",                         "shell host"),
    ("app/main.py",                          "entry point"),
]

# (path, why it must go)
LEFTOVERS = [
    ("main.py",                    "superseded by app/main.py"),
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

    print("\n" + "=" * 60)
    if missing:
        print(f"NOT READY — {len(missing)} required file(s) missing:")
        for m in missing:
            print(f"    {m}")
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