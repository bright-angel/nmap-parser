"""Excel report generation.

Sheets are declared once as :class:`SheetSpec` tables instead of four copies of
the same hand-written cell loop. Every untrusted value is written with
``write_string`` and the workbook disables formula/URL interpretation, which
closes the spreadsheet-injection hole present in 1.x.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import xlsxwriter
from xlsxwriter.exceptions import FileCreateError

from .exceptions import OutputError
from .models import ScanDataset

MAX_CELL_CHARS = 32767  # Excel hard limit for a single cell
HEADER_COLOR = "#1F4E79"
_NUMBER_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")


@dataclass(frozen=True)
class Column:
    """One report column."""

    header: str
    key: str
    width: float = 16.0
    kind: str = "text"  # "text" | "number"
    wrap: bool = False


@dataclass(frozen=True)
class SheetSpec:
    """Declaration of a worksheet."""

    name: str
    columns: tuple[Column, ...]


TASK_SHEET = SheetSpec(
    "Task Info",
    (
        Column("XML File", "xml_file", 24),
        Column("Scanner", "scanner", 12),
        Column("Nmap Version", "nmap_version", 14),
        Column("Scan Args", "scan_args", 60, wrap=True),
        Column("Start Time", "start_time", 15, kind="number"),
        Column("Start Time Str", "start_time_str", 24),
        Column("XML Version", "xml_output_version", 13),
        Column("Total Hosts", "total_hosts", 12, kind="number"),
        Column("Up Hosts", "up_hosts", 11, kind="number"),
        Column("Down Hosts", "down_hosts", 12, kind="number"),
        Column("Finish Time", "finish_time", 15, kind="number"),
        Column("Finish Time Str", "finish_time_str", 24),
        Column("Elapsed (s)", "elapsed_time", 13, kind="number"),
        Column("Exit Status", "exit_status", 12),
    ),
)

HOST_SHEET = SheetSpec(
    "Host Status",
    (
        Column("XML File", "xml_file", 24),
        Column("IP Address", "ip_address", 18),
        Column("Hostname", "hostname", 28),
        Column("Status", "status", 11),
        Column("Status Reason", "status_reason", 24),
        Column("Status TTL", "status_ttl", 12, kind="number"),
        Column("Start Time", "start_time", 16, kind="number"),
        Column("End Time", "end_time", 16, kind="number"),
    ),
)

PORT_SHEET = SheetSpec(
    "Port & Service",
    (
        Column("XML File", "xml_file", 24),
        Column("IP Address", "ip_address", 18),
        Column("Port", "port_id", 9, kind="number"),
        Column("Protocol", "protocol", 10),
        Column("State", "state", 14),
        Column("State Reason", "state_reason", 24),
        Column("State TTL", "state_ttl", 12, kind="number"),
        Column("Service Name", "service_name", 18),
        Column("Service Product", "service_product", 24),
        Column("Service Version", "service_version", 20),
        Column("Service Extra", "service_extrainfo", 30, wrap=True),
        Column("Method", "service_method", 12),
        Column("Confidence", "service_conf", 12, kind="number"),
        Column("CPE", "cpe", 50, wrap=True),
    ),
)

VULN_SHEET = SheetSpec(
    "Vulnerabilities",
    (
        Column("XML File", "xml_file", 24),
        Column("IP Address", "ip_address", 18),
        Column("Port", "port_id", 9, kind="number"),
        Column("Protocol", "protocol", 10),
        Column("Script ID", "script_id", 22),
        Column("Output", "output", 60, wrap=True),
        Column("Version", "version", 12),
        Column("Result", "result", 18),
        Column("Severity", "severity", 12),
        Column("Description", "description", 60, wrap=True),
        Column("Risk Factor", "risk_factor", 14),
        Column("See Also", "see_also", 50, wrap=True),
        Column("Solution", "solution", 40, wrap=True),
        Column("CVE", "cve", 26, wrap=True),
        Column("BID", "bid", 14),
        Column("CERT", "cert", 14),
        Column("MSF Module", "msf_module", 26),
        Column("OSVDB", "osvdb", 14),
    ),
)

SHEETS: tuple[SheetSpec, ...] = (TASK_SHEET, HOST_SHEET, PORT_SHEET, VULN_SHEET)


def ensure_xlsx_suffix(output: str | Path) -> Path:
    """Append ``.xlsx`` when the output path has no xlsx extension."""
    path = Path(output).expanduser()
    if path.suffix.lower() != ".xlsx":
        return path.with_name(path.name + ".xlsx")
    return path


def _truncate(value: str) -> str:
    if len(value) <= MAX_CELL_CHARS:
        return value
    return value[: MAX_CELL_CHARS - 16] + " ...[truncated]"


def _write_cell(
    worksheet: Any,
    row: int,
    col: int,
    raw: object,
    column: Column,
    text_format: Any,
    wrap_format: Any,
    number_format: Any,
) -> None:
    value = "" if raw is None else str(raw)
    if column.kind == "number" and _NUMBER_RE.match(value):
        number = float(value)
        if number.is_integer():
            worksheet.write_number(row, col, int(number), number_format)
        else:
            worksheet.write_number(row, col, number, number_format)
        return
    # write_string never interprets a leading '=' / '+' / '-' / '@' as a
    # formula, even when a scanned service name is attacker-controlled.
    worksheet.write_string(
        row,
        col,
        _truncate(value),
        wrap_format if column.wrap else text_format,
    )


def _write_sheet(
    workbook: Any, spec: SheetSpec, rows: Sequence[Any], formats: dict[str, Any]
) -> None:
    worksheet = workbook.add_worksheet(spec.name)
    last_col = len(spec.columns) - 1
    last_row = max(len(rows), 1)

    for col, column in enumerate(spec.columns):
        worksheet.write_string(0, col, column.header, formats["header"])
        worksheet.set_column(col, col, column.width)

    for row_index, row in enumerate(rows, start=1):
        for col, column in enumerate(spec.columns):
            _write_cell(
                worksheet,
                row_index,
                col,
                getattr(row, column.key, ""),
                column,
                formats["text"],
                formats["wrap"],
                formats["number"],
            )

    worksheet.freeze_panes(1, 0)
    worksheet.autofilter(0, 0, last_row, last_col)
    worksheet.set_row(0, 24)

    if spec.name == "Host Status" and rows:
        worksheet.conditional_format(
            1,
            3,
            len(rows),
            3,
            {"type": "text", "criteria": "containing", "value": "up", "format": formats["good"]},
        )
    elif spec.name == "Port & Service" and rows:
        worksheet.conditional_format(
            1,
            4,
            len(rows),
            4,
            {"type": "text", "criteria": "containing", "value": "open", "format": formats["good"]},
        )
    elif spec.name == "Vulnerabilities" and rows:
        for col in (8, 10):  # Severity, Risk Factor
            worksheet.conditional_format(
                1,
                col,
                len(rows),
                col,
                {
                    "type": "text",
                    "criteria": "containing",
                    "value": "CRITICAL",
                    "format": formats["danger"],
                },
            )
            worksheet.conditional_format(
                1,
                col,
                len(rows),
                col,
                {
                    "type": "text",
                    "criteria": "containing",
                    "value": "HIGH",
                    "format": formats["danger"],
                },
            )
            worksheet.conditional_format(
                1,
                col,
                len(rows),
                col,
                {
                    "type": "text",
                    "criteria": "containing",
                    "value": "MEDIUM",
                    "format": formats["warn"],
                },
            )


def _build_formats(workbook: Any) -> dict[str, Any]:
    base: dict[str, Any] = {"border": 1, "valign": "top"}
    return {
        "header": workbook.add_format(
            {
                **base,
                "bold": True,
                "bg_color": HEADER_COLOR,
                "font_color": "white",
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
            }
        ),
        "text": workbook.add_format(base),
        "wrap": workbook.add_format({**base, "text_wrap": True}),
        "number": workbook.add_format({**base, "align": "right"}),
        "good": workbook.add_format({"bg_color": "#E2EFDA", "font_color": "#375623"}),
        "warn": workbook.add_format({"bg_color": "#FFF2CC", "font_color": "#7F6000"}),
        "danger": workbook.add_format(
            {"bg_color": "#FCE4E4", "font_color": "#9C0006", "bold": True}
        ),
    }


def write_report(
    dataset: ScanDataset,
    output: str | Path,
    *,
    generated_on: datetime | None = None,
) -> Path:
    """Write *dataset* to an XLSX file and return the resolved output path.

    Parent directories are created automatically. The workbook is always
    closed, including when a cell fails to write.
    """
    destination = ensure_xlsx_suffix(output)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        workbook = xlsxwriter.Workbook(
            str(destination),
            {
                "strings_to_formulas": False,
                "strings_to_urls": False,
            },
        )
    except (OSError, FileCreateError) as exc:
        raise OutputError(f"Cannot create {destination}: {exc}") from exc

    closed = False
    try:
        created = generated_on or datetime.now()
        workbook.set_properties(
            {
                "title": "Nmap scan report",
                "subject": "Nmap XML scan results",
                "author": "nmap-parser",
                "comments": f"Generated by nmap-parser at {created:%Y-%m-%d %H:%M:%S}",
                "created": created,
            }
        )
        formats = _build_formats(workbook)
        rows_by_sheet: tuple[Sequence[Any], ...] = (
            dataset.tasks,
            dataset.hosts,
            dataset.ports,
            dataset.findings,
        )
        for spec, rows in zip(SHEETS, rows_by_sheet):
            _write_sheet(workbook, spec, rows, formats)
        # On Windows this is where "file is open in Excel" surfaces.
        workbook.close()
        closed = True
    except (OSError, FileCreateError, ValueError, TypeError) as exc:
        raise OutputError(f"Cannot write {destination}: {exc}") from exc
    finally:
        # Best-effort cleanup that never masks the original error.
        if not closed:
            with suppress(Exception):
                workbook.close()

    return destination


__all__ = ["SHEETS", "Column", "SheetSpec", "ensure_xlsx_suffix", "write_report"]
