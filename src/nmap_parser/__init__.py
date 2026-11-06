"""nmap-parser — convert Nmap XML scan results into Excel reports.

Public API (stable):

    from nmap_parser import ConversionService

    outcome = ConversionService().convert("scan.xml", "report.xlsx")
    print(outcome.stats)

For lower-level access use ``NmapParser``, ``discover_xml_files`` and
``write_report``. The 1.x ``NmapConverter`` facade remains available but is
deprecated.
"""

from __future__ import annotations

from .__about__ import __author__, __license__, __version__
from .compat import NmapConverter
from .discovery import discover_xml_files
from .exceptions import (
    AllInputsFailedError,
    InputNotFoundError,
    InvalidInputError,
    InvalidNmapXmlError,
    MalformedXmlError,
    MissingGuiDependencyError,
    NmapParserError,
    OutputError,
    UnsafeXmlError,
)
from .models import (
    ConversionOutcome,
    FileFailure,
    Finding,
    Host,
    Port,
    Progress,
    ScanDataset,
    ScanResult,
    SummaryStats,
    TaskInfo,
)
from .parser import NmapParser
from .service import ConversionService
from .workbook import SHEETS, Column, SheetSpec, ensure_xlsx_suffix, write_report

__all__ = [
    # workbook declarations
    "SHEETS",
    "AllInputsFailedError",
    "Column",
    # models
    "ConversionOutcome",
    # high-level API
    "ConversionService",
    "FileFailure",
    "Finding",
    "Host",
    "InputNotFoundError",
    "InvalidInputError",
    "InvalidNmapXmlError",
    "MalformedXmlError",
    "MissingGuiDependencyError",
    "NmapConverter",
    "NmapParser",
    # errors
    "NmapParserError",
    "OutputError",
    "Port",
    "Progress",
    "ScanDataset",
    "ScanResult",
    "SheetSpec",
    "SummaryStats",
    "TaskInfo",
    "UnsafeXmlError",
    "__author__",
    "__license__",
    # metadata
    "__version__",
    "discover_xml_files",
    "ensure_xlsx_suffix",
    "write_report",
]
