"""No-console launcher for EQGPS.

Double-click this file on Windows. The .pyw extension uses pythonw.exe,
which opens the Tkinter UI without a command prompt window.
"""

from __future__ import annotations

import os
from pathlib import Path

from eqgps.app import main

os.chdir(Path(__file__).resolve().parent)
main()