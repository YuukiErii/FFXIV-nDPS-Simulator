"""Compatibility launcher for the unified simulator GUI.

`src/ffxiv_ndps_simulator/sim.py` is the maintained entrypoint. This wrapper keeps old
shortcuts that still run `sim_test.py` working without duplicating the UI.
"""

import tkinter as tk

try:
    from sim import DpsSimulator, DpsSimulatorApp, SamuraiApp, SamuraiSimulator
except ImportError:
    from .sim import DpsSimulator, DpsSimulatorApp, SamuraiApp, SamuraiSimulator


def main():
    root = tk.Tk()
    root.configure(bg="#2b2b2b")
    DpsSimulatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
