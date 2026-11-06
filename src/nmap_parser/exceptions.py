"""Exception hierarchy for the package.

Keeping errors in one module lets callers (CLI, GUI, library users) handle a
small, stable set of types instead of catching ``Exception``.
"""

from __future__ import annotations


class NmapParserError(Exception):
    """Base class for all expected errors raised by this package."""


class InputNotFoundError(NmapParserError):
    """The input path does not exist."""


class InvalidInputError(NmapParserError):
    """The input path exists but is not a usable XML file or directory."""


class UnsafeXmlError(NmapParserError):
    """The XML contains a DTD/entity declaration and was refused."""


class InvalidNmapXmlError(NmapParserError):
    """The file is XML, but not an Nmap ``<nmaprun>`` document."""


class MalformedXmlError(NmapParserError):
    """The file could not be parsed as XML."""


class OutputError(NmapParserError):
    """The report could not be written (bad path, permission, file in use)."""


class AllInputsFailedError(NmapParserError):
    """Every discovered XML file failed to parse; no report was produced."""


class MissingGuiDependencyError(NmapParserError):
    """The GUI was requested but the ``[gui]`` extra is not installed."""
