"""Excel report generation tests (read back with openpyxl)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from nmap_parser import Finding, ScanDataset, ensure_xlsx_suffix, write_report
from nmap_parser.workbook import MAX_CELL_CHARS, SHEETS


def _read(path: Path):
    return load_workbook(path, read_only=False, data_only=False)


def test_four_sheets_with_headers(sample_dataset, tmp_path: Path) -> None:
    output = write_report(sample_dataset, tmp_path / "report.xlsx")
    workbook = _read(output)
    assert workbook.sheetnames == [spec.name for spec in SHEETS]
    for spec in SHEETS:
        headers = [cell.value for cell in workbook[spec.name][1]]
        assert headers == [column.header for column in spec.columns]
    workbook.close()


def test_numeric_columns_are_real_numbers(sample_dataset, tmp_path: Path) -> None:
    output = write_report(sample_dataset, tmp_path / "report.xlsx")
    workbook = _read(output)
    ports = workbook["Port & Service"]
    port_ids = [ports.cell(row=r, column=3).value for r in range(2, ports.max_row + 1)]
    assert 22 in port_ids
    assert all(isinstance(value, int) for value in port_ids if value is not None)
    tasks = workbook["Task Info"]
    assert tasks.cell(row=2, column=8).value == 3  # Total Hosts
    assert isinstance(tasks.cell(row=2, column=13).value, float)  # Elapsed 20.5
    workbook.close()


def test_header_is_frozen_and_filtered(sample_dataset, tmp_path: Path) -> None:
    output = write_report(sample_dataset, tmp_path / "report.xlsx")
    workbook = _read(output)
    for name in workbook.sheetnames:
        sheet = workbook[name]
        assert sheet.freeze_panes == "A2"
        assert sheet.auto_filter.ref is not None
    workbook.close()


def test_empty_dataset_still_has_headers(tmp_path: Path) -> None:
    output = write_report(ScanDataset(), tmp_path / "empty.xlsx")
    workbook = _read(output)
    assert len(workbook.sheetnames) == 4
    assert workbook["Host Status"]["A1"].value == "XML File"
    workbook.close()


def test_creates_missing_parent_directories(sample_dataset, tmp_path: Path) -> None:
    output = write_report(sample_dataset, tmp_path / "deep" / "nested" / "report.xlsx")
    assert output.is_file()


def test_long_text_is_truncated(tmp_path: Path) -> None:
    dataset = ScanDataset(findings=[Finding(output="x" * 40_000)])
    output = write_report(dataset, tmp_path / "long.xlsx")
    workbook = _read(output)
    value = workbook["Vulnerabilities"]["F2"].value
    assert value is not None
    assert len(value) <= MAX_CELL_CHARS
    assert value.endswith("...[truncated]")
    workbook.close()


def test_workbook_properties(sample_dataset, tmp_path: Path) -> None:
    output = write_report(
        sample_dataset,
        tmp_path / "props.xlsx",
        generated_on=datetime(2026, 1, 1, 12, 0, 0),
    )
    workbook = _read(output)
    assert workbook.properties.title == "Nmap scan report"
    assert workbook.properties.created.year == 2026
    workbook.close()


def test_ensure_xlsx_suffix() -> None:
    assert ensure_xlsx_suffix("report") == Path("report.xlsx")
    assert ensure_xlsx_suffix("report.XLSX") == Path("report.XLSX")
    assert ensure_xlsx_suffix("dir/report.csv") == Path("dir/report.csv.xlsx")
