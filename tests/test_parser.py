"""Nmap XML parsing tests, including regressions for the 1.x bugs."""

from __future__ import annotations

from pathlib import Path

import pytest

from nmap_parser import (
    InvalidNmapXmlError,
    MalformedXmlError,
    NmapParser,
    UnsafeXmlError,
)


def test_task_info(basic_xml: Path) -> None:
    task = NmapParser().parse(basic_xml).task_info
    assert task.xml_file == "basic_scan.xml"
    assert task.scanner == "nmap"
    assert task.nmap_version == "7.95"
    assert task.scan_args.startswith("nmap -sV")
    assert task.start_time == "1730000000"
    assert task.xml_output_version == "1.05"
    assert (task.total_hosts, task.up_hosts, task.down_hosts) == ("3", "2", "1")
    assert task.elapsed_time == "20.5"
    assert task.exit_status == "success"


def test_hosts_include_hints_and_prefer_ipv4(basic_xml: Path) -> None:
    result = NmapParser().parse(basic_xml)
    assert len(result.hosts) == 3  # 2 <host> + 1 <hosthint>
    first = result.hosts[0]
    # The MAC address comes first in the fixture: 1.x used host.find('address')
    # and would have written the MAC into the IP column.
    assert first.ip_address == "192.168.1.10"
    assert first.hostname == "web.example.test; web"
    assert first.status == "up"
    assert first.status_reason == "syn-ack"
    assert first.status_ttl == "64"
    assert result.hosts[1].status == "down"


def test_ports_and_cpe(basic_xml: Path) -> None:
    ports = NmapParser().parse(basic_xml).ports
    assert len(ports) == 2
    ssh = ports[0]
    assert ssh.port_id == "22"
    assert ssh.protocol == "tcp"
    assert ssh.state == "open"
    assert ssh.service_name == "ssh"
    assert ssh.service_product == "OpenSSH"
    assert ssh.service_version == "9.2p1"
    assert ssh.service_conf == "10"
    # Regression: CPEs are children of <service>, not of <port>.
    assert "cpe:/a:openbsd:openssh:9.2p1" in ssh.cpe
    assert "cpe:/o:linux:linux_kernel" in ssh.cpe
    assert ports[1].state == "closed"


def test_script_findings_and_nested_elements(vuln_xml: Path) -> None:
    findings = NmapParser().parse(vuln_xml).findings
    assert len(findings) == 2  # one port script + one host-level script

    heartbleed = findings[0]
    assert heartbleed.script_id == "ssl-heartbleed"
    assert heartbleed.port_id == "443"
    assert heartbleed.protocol == "tcp"
    assert heartbleed.result == "VULNERABLE"  # <elem key="state"> alias
    assert heartbleed.severity == "HIGH"
    assert heartbleed.risk_factor == "High"
    assert heartbleed.solution == "Upgrade OpenSSL."
    assert heartbleed.cert == "@SUM(1+1)"
    # Repeated keys plus a nested <table><elem key="ids"> are all retained.
    assert "CVE-2014-0160" in heartbleed.cve
    assert "CVE-2014-0346" in heartbleed.cve
    assert "CVE-2014-9999" in heartbleed.cve
    assert heartbleed.bid == "66666"
    assert heartbleed.elements["cve"] == [
        "CVE-2014-0160",
        "CVE-2014-0346",
        "CVE-2014-9999",
    ]

    host_script = findings[1]
    assert host_script.port_id == ""
    assert host_script.elements["title"] == ["Host-level script result"]


def test_prescript_and_postscript() -> None:
    xml = """<nmaprun scanner="nmap">
      <prescript><script id="pre" output="a"><elem key="state">ok</elem></script></prescript>
      <postscript><script id="post" output="b"/></postscript>
    </nmaprun>"""
    findings = NmapParser().parse_string(xml).findings
    assert [f.script_id for f in findings] == ["pre", "post"]
    assert findings[0].result == "ok"


def test_malformed_xml(fixtures_dir: Path) -> None:
    with pytest.raises(MalformedXmlError):
        NmapParser().parse(fixtures_dir / "malformed.xml")


def test_non_nmap_document(fixtures_dir: Path) -> None:
    with pytest.raises(InvalidNmapXmlError):
        NmapParser().parse(fixtures_dir / "not_nmap.xml")


def test_standard_nmap_doctype_is_accepted(basic_xml: Path) -> None:
    """Regression: ``nmap -oX`` emits ``<!DOCTYPE nmaprun>`` by default."""
    result = NmapParser().parse(basic_xml)
    assert result.task_info.scanner == "nmap"
    assert len(result.hosts) == 3


def test_external_dtd_reference_is_accepted() -> None:
    # expat does not fetch external DTDs, so this is safe and must not be
    # rejected (some Nmap wrappers emit a SYSTEM reference).
    xml = '<!DOCTYPE nmaprun SYSTEM "file:///usr/share/nmap/nmap.dtd"><nmaprun scanner="nmap"/>'
    assert NmapParser().parse_string(xml).task_info.scanner == "nmap"


def test_entity_declarations_are_rejected(fixtures_dir: Path) -> None:
    with pytest.raises(UnsafeXmlError, match="entity declarations"):
        NmapParser().parse(fixtures_dir / "xxe.xml")


def test_dtd_internal_subset_is_rejected() -> None:
    xml = "<!DOCTYPE nmaprun [ ]><nmaprun/>"
    with pytest.raises(UnsafeXmlError, match="internal subsets"):
        NmapParser().parse_string(xml)


def test_entity_dtd_can_be_explicitly_allowed(fixtures_dir: Path) -> None:
    result = NmapParser(allow_dtd=True).parse(fixtures_dir / "xxe.xml")
    assert result.hosts[0].ip_address == "10.0.0.1"


def test_size_limit() -> None:
    xml = "<nmaprun>" + "x" * 200 + "</nmaprun>"
    with pytest.raises(UnsafeXmlError, match="limit"):
        NmapParser(max_bytes=100).parse_string(xml)


def test_parse_string_source_name() -> None:
    result = NmapParser().parse_string("<nmaprun/>", source_name="inline.xml")
    assert result.task_info.xml_file == "inline.xml"
    assert result.hosts == []
