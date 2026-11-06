"""Stable PyInstaller entry point for the desktop GUI.

Using a launcher script (instead of pointing PyInstaller at a module inside
``src/``) keeps the build command independent of the package layout.
See docs/packaging.md.
"""

from __future__ import annotations

from nmap_parser.gui import main

if __name__ == "__main__":
    raise SystemExit(main())
