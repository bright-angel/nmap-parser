"""Security regression tests.

The XML being parsed comes from machines that may be controlled by an attacker:
service banners, hostnames and NSE output are all untrusted strings.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import load_workbook

from nmap_parser import NmapParser, ScanDataset, UnsafeXmlError, write_report


def _dataset_from(xml_file: Path) -> ScanDataset:
    dataset = ScanDataset()
    dataset.extend(NmapParser().parse(xml_file))
    return dataset


def test_scan_data_is_never_written_as_a_formula(vuln_xml: Path, tmp_path: Path) -> None:
    output = write_report(_dataset_from(vuln_xml), tmp_path / "injection.xlsx")
    workbook = load_workbook(output)

    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                assert cell.data_type != "f", f"formula in {sheet.title}!{cell.coordinate}"
                assert cell.hyperlink is None

    ports = workbook["Port & Service"]
    assert ports.cell(row=2, column=9).value == "=2+2"  # Service Product
    assert ports.cell(row=2, column=10).value == "+1"  # Service Version
    assert ports.cell(row=2, column=11).value == "-2"  # Service Extra

    vulns = workbook["Vulnerabilities"]
    assert vulns.cell(row=2, column=6).value.startswith("=HYPERLINK(")
    assert vulns.cell(row=2, column=16).value == "@SUM(1+1)"  # CERT
    workbook.close()


def test_formula_like_values_in_hostnames(tmp_path: Path) -> None:
    xml = """<nmaprun scanner="nmap"><host>
      <status state="up"/>
      <address addr="10.0.0.1" addrtype="ipv4"/>
      <hostnames><hostname name="=cmd|'/c calc'!A1"/></hostnames>
    </host></nmaprun>"""
    result = NmapParser().parse_string(xml, source_name="hostile.xml")
    dataset = ScanDataset()
    dataset.extend(result)
    output = write_report(dataset, tmp_path / "hostile.xlsx")
    workbook = load_workbook(output)
    cell = workbook["Host Status"]["C2"]
    assert cell.value == "=cmd|'/c calc'!A1"
    assert cell.data_type == "s"
    workbook.close()


def test_entity_detection_is_case_insensitive() -> None:
    xml = '<!doctype nmaprun [<!entity x "y">]><nmaprun/>'
    with pytest.raises(UnsafeXmlError, match="entity declarations"):
        NmapParser().parse_string(xml)


def test_oversized_input_is_rejected() -> None:
    parser = NmapParser(max_bytes=64)
    with pytest.raises(UnsafeXmlError, match="limit"):
        parser.parse_string("<nmaprun>" + "a" * 100 + "</nmaprun>")
