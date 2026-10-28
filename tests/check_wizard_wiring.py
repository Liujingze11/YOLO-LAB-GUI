#!/usr/bin/env python3
"""One-off: the welcome wizard must be wired into main().

Leg 1: on first run the wizard is constructed and executed once.
Leg 2: when not first run, no wizard is shown.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])


def expect(cond, msg):
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    print(f"ok: {msg}")


import gui.welcome_wizard as ww
import main as main_mod


class WizardStub:
    exec_called = 0
    parents = []

    def __init__(self, parent=None):
        WizardStub.parents.append(parent)

    def exec(self):
        WizardStub.exec_called += 1


# Avoid constructing a second QApplication; reuse the existing one while
# still exposing the real class attributes (primaryScreen, quit, ...).
class AppFactory:
    def __call__(self, argv):
        return app

    def __getattr__(self, name):
        return getattr(QApplication, name)


main_mod.QApplication = AppFactory()
QApplication.exec = lambda self, *a: 0  # return from the event loop immediately
ww.WelcomeWizard = WizardStub


def run_main():
    try:
        main_mod.main()
    except SystemExit:
        pass


# ── Leg 1: first run shows the wizard ──
ww.is_first_run = lambda: True
WizardStub.exec_called = 0
WizardStub.parents = []
run_main()
expect(WizardStub.exec_called == 1,
       f"wizard executed once on first run (got {WizardStub.exec_called})")
expect(WizardStub.parents and WizardStub.parents[0] is not None,
       "wizard is parented to the main window")

# ── Leg 2: subsequent runs do not ──
ww.is_first_run = lambda: False
WizardStub.exec_called = 0
run_main()
expect(WizardStub.exec_called == 0,
       f"no wizard when not first run (got {WizardStub.exec_called})")

print("ALL PASS")
