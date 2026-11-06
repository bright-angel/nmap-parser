"""Backwards-compatible 1.x API.

``NmapConverter`` is deprecated but kept so existing scripts that call
``get_xml_files`` / ``parse_nmap_xml`` / ``write_to_xlsx`` keep working. New
code should use :class:`~service.ConversionService`.
"""

from __future__ import annotations

import warnings
from dataclasses import asdict, fields
from typing import Any

from .discovery import discover_xml_files
from .models import Finding, Host, Port, ScanDataset, TaskInfo
from .parser import NmapParser
from .workbook import write_report


def _to_dataclass(cls: type, rows: Any) -> list[Any]:
    """Coerce legacy dict rows into a dataclass, ignoring unknown keys."""
    if not isinstance(rows, (list, tuple)):
        return []
    valid = {f.name for f in fields(cls)}
    return [
        cls(**{k: v for k, v in row.items() if k in valid}) for row in rows if isinstance(row, dict)
    ]


def coerce_dataset(data: Any) -> ScanDataset:
    """Accept a :class:`ScanDataset` or a 1.x-shaped dictionary.

    In 1.x ``task_info`` was a dict for one file and a list for many; both
    forms are normalised here. This is the root cause of the old
    ``TypeError: string indices must be integers`` crash.
    """
    if isinstance(data, ScanDataset):
        return data
    if not isinstance(data, dict):
        raise TypeError(f"Expected ScanDataset or dict, got {type(data).__name__}")

    tasks = data.get("task_info", [])
    if isinstance(tasks, dict):
        tasks = [tasks]
    findings = data.get("findings", data.get("vulns", []))

    return ScanDataset(
        tasks=_to_dataclass(TaskInfo, tasks),
        hosts=_to_dataclass(Host, data.get("hosts", [])),
        ports=_to_dataclass(Port, data.get("ports", [])),
        findings=_to_dataclass(Finding, findings),
    )


class NmapConverter:
    """Deprecated 1.x facade. Use :class:`~service.ConversionService` instead."""

    def __init__(self) -> None:
        warnings.warn(
            "NmapConverter is deprecated; use nmap_parser.ConversionService",
            DeprecationWarning,
            stacklevel=2,
        )
        self._parser = NmapParser()
        self.emoji_success = "[OK]"
        self.emoji_info = "[*]"
        self.emoji_warning = "[!]"
        self.emoji_error = "[X]"
        self.emoji_scan = "[>]"
        self.emoji_file = "[F]"
        self.emoji_folder = "[D]"
        self.emoji_excel = "[E]"
        self.emoji_stats = "[=]"

    def get_xml_files(self, input_path: str, recursive: bool = False) -> list[str]:
        """Return XML paths as strings (1.x signature)."""
        return [str(path) for path in discover_xml_files(input_path, recursive=recursive)]

    def parse_nmap_xml(self, xml_path: str) -> dict[str, Any]:
        """Return the 1.x dictionary shape for one file."""
        result = self._parser.parse(xml_path)
        return {
            "task_info": asdict(result.task_info),
            "hosts": [asdict(row) for row in result.hosts],
            "ports": [asdict(row) for row in result.ports],
            "vulns": [
                {k: v for k, v in asdict(row).items() if k != "elements"} for row in result.findings
            ],
        }

    def write_to_xlsx(self, data: dict[str, Any] | ScanDataset, output_file: str) -> None:
        """Write legacy or modern data to an XLSX file."""
        write_report(coerce_dataset(data), output_file)

    def get_summary_stats(
        self,
        all_data: dict[str, Any] | ScanDataset,
        xml_files_count: int,
    ) -> dict[str, Any]:
        """Return the 1.x statistics key names."""
        stats = coerce_dataset(all_data).stats(
            files_total=xml_files_count,
            files_ok=xml_files_count,
        )
        return {
            "files_count": stats.files_total,
            "hosts_total": stats.hosts_total,
            "hosts_up": stats.hosts_up,
            "hosts_down": stats.hosts_down,
            "ports_total": stats.ports_total,
            "ports_open": stats.ports_open,
            "ports_closed": stats.ports_closed,
            "vulns_total": stats.findings_total,
            "scripts_count": stats.scripts_total,
        }


__all__ = ["NmapConverter", "coerce_dataset"]
