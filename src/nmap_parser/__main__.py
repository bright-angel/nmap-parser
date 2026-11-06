"""``python -m nmap_parser`` entry point.

Always routes to the CLI. Running with no arguments prints help instead of
attempting to open a GUI window (which failed on headless systems in 1.x).
Use ``nmap-parser-gui`` when a desktop interface is wanted.
"""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
