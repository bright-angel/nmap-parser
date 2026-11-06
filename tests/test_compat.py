"""1.x compatibility facade tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import load_workbook

from nmap_parser import NmapConverter, ScanDataset
from nmap_parser.compat import coerce_dataset


@pytest.fixture
def converter() -> NmapConverter:
    with pytest.warns(DeprecationWarning):
        return NmapConverter()


def test_emits_deprecation_warning() -> None:
    with pytest.warns(DeprecationWarning, match="ConversionService"):
        NmapConverter()


def test_get_xml_files_returns_strings(converter: NmapConverter, basic_xml: Path) -> None:
    files = converter.get_xml_files(str(basic_xml))
    assert files == [str(basic_xml)]
    assert all(isinstance(item, str) for item in files)


def test_parse_nmap_xml_legacy_shape(converter: NmapConverter, basic_xml: Path) -> None:
    data = converter.parse_nmap_xml(str(basic_xml))
    assert isinstance(data["task_info"], dict)
    assert data["task_info"]["scanner"] == "nmap"
    assert isinstance(data["hosts"], list)
    assert isinstance(data["vulns"], list)
    assert data["ports"][0]["cpe"]  # CPE fix applies to the legacy API too


def test_write_to_xlsx_accepts_single_task_info_dict(
    converter: NmapConverter,
    basic_xml: Path,
    tmp_path: Path,
) -> None:
    """Regression: 1.x iterated a dict as if it were a list and crashed."""
    data = converter.parse_nmap_xml(str(basic_xml))
    output = tmp_path / "legacy-single.xlsx"
    converter.write_to_xlsx(data, str(output))
    workbook = load_workbook(output)
    assert workbook["Task Info"]["A2"].value == "basic_scan.xml"
    assert workbook["Host Status"].max_row == 4  # header + 3 hosts
    workbook.close()


def test_write_to_xlsx_accepts_task_info_list(
    converter: NmapConverter,
    basic_xml: Path,
    vuln_xml: Path,
    tmp_path: Path,
) -> None:
    first = converter.parse_nmap_xml(str(basic_xml))
    second = converter.parse_nmap_xml(str(vuln_xml))
    combined = {
        "task_info": [first["task_info"], second["task_info"]],
        "hosts": first["hosts"] + second["hosts"],
        "ports": first["ports"] + second["ports"],
        "vulns": first["vulns"] + second["vulns"],
    }
    output = tmp_path / "legacy-multi.xlsx"
    converter.write_to_xlsx(combined, str(output))
    workbook = load_workbook(output)
    assert workbook["Task Info"].max_row == 3
    workbook.close()


def test_get_summary_stats_legacy_keys(
    converter: NmapConverter,
    basic_xml: Path,
) -> None:
    stats = converter.get_summary_stats(converter.parse_nmap_xml(str(basic_xml)), 1)
    assert stats["files_count"] == 1
    assert stats["hosts_total"] == 3
    assert stats["ports_total"] == 2
    assert set(stats) == {
        "files_count",
        "hosts_total",
        "hosts_up",
        "hosts_down",
        "ports_total",
        "ports_open",
        "ports_closed",
        "vulns_total",
        "scripts_count",
    }


def test_coerce_dataset_ignores_unknown_keys() -> None:
    dataset = coerce_dataset(
        {
            "task_info": {"xml_file": "a.xml", "future_field": "x"},
            "hosts": [{"ip_address": "10.0.0.1", "unknown": 42}],
        }
    )
    assert isinstance(dataset, ScanDataset)
    assert dataset.tasks[0].xml_file == "a.xml"
    assert dataset.hosts[0].ip_address == "10.0.0.1"
