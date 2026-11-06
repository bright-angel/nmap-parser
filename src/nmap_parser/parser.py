"""Nmap XML parsing.

This module is deliberately free of any presentation concern: no printing, no
formatting, no file writing. It turns bytes into :class:`~models.ScanResult`.

Security note
-------------
Nmap ``-oX`` output normally starts with a harmless ``<!DOCTYPE nmaprun>``
declaration plus an ``<?xml-stylesheet?>`` processing instruction; those MUST be
accepted. The actual risk is entity expansion ("billion laughs") and external
entity reads, which require an ``<!ENTITY>`` declaration or a DTD internal
subset (``<!DOCTYPE ... [ ... ]>``). We reject those two constructs by default,
allow plain DOCTYPE declarations, and cap the input size. ``allow_dtd=True``
disables these checks and must only be used with fully trusted files.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .exceptions import (
    InvalidInputError,
    InvalidNmapXmlError,
    MalformedXmlError,
    UnsafeXmlError,
)
from .models import Finding, Host, Port, ScanResult, TaskInfo

DEFAULT_MAX_BYTES = 128 * 1024 * 1024

# A plain <!DOCTYPE nmaprun> (with or without SYSTEM/PUBLIC) is safe: expat,
# which backs ElementTree, does not fetch external DTDs. Entity declarations
# and internal subsets are the constructs that enable XXE / expansion attacks.
_ENTITY_DECL_RE = re.compile(rb"<!ENTITY\b", re.IGNORECASE)
_DTD_SUBSET_RE = re.compile(rb"<!DOCTYPE[^>]*\[", re.IGNORECASE)

# Some NSE scripts (notably the ``vuln`` family) use different element keys for
# the same concept; normalise them so the report columns stay populated.
_KEY_ALIASES = {
    "state": "result",
    "ids": "cve",
    "reference": "see_also",
}


def _attr(element: ET.Element | None, name: str) -> str:
    """Read an XML attribute, tolerating a missing element."""
    if element is None:
        return ""
    return element.get(name) or ""


def _local_tag(element: ET.Element) -> str:
    """Strip an optional ``{namespace}`` prefix from a tag name."""
    return element.tag.rsplit("}", 1)[-1]


def _join(values: list[str]) -> str:
    return "; ".join(value for value in values if value)


def _primary_address(host: ET.Element) -> str:
    """Prefer an IPv4/IPv6 address over a MAC or other address type."""
    addresses = host.findall("address")
    for addr in addresses:
        if (addr.get("addrtype") or "").lower() in {"ipv4", "ipv6"}:
            return addr.get("addr") or ""
    return _attr(addresses[0] if addresses else None, "addr")


def _hostnames(host: ET.Element) -> str:
    return _join([name.get("name") or "" for name in host.findall("hostnames/hostname")])


class NmapParser:
    """Parse Nmap XML documents into typed models."""

    def __init__(
        self,
        *,
        allow_dtd: bool = False,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        # Standard Nmap DOCTYPE declarations are always accepted. ``allow_dtd``
        # controls only entity declarations / internal subsets (trusted input).
        self.allow_dtd = allow_dtd
        self.max_bytes = max_bytes

    def parse(self, path: str | Path) -> ScanResult:
        """Parse an XML file from disk."""
        source = Path(path)
        try:
            data = source.read_bytes()
        except OSError as exc:
            raise InvalidInputError(f"Cannot read {source}: {exc}") from exc
        return self.parse_bytes(data, source=source)

    def parse_string(self, xml: str, *, source_name: str = "<string>") -> ScanResult:
        """Parse XML held in memory (handy for tests and library users)."""
        return self.parse_bytes(xml.encode("utf-8"), source=Path(source_name))

    def parse_bytes(self, data: bytes, *, source: Path) -> ScanResult:
        """Parse raw XML bytes, validating safety constraints first."""
        if len(data) > self.max_bytes:
            raise UnsafeXmlError(
                f"{source.name}: file is {len(data)} bytes, limit is {self.max_bytes}"
            )
        if not self.allow_dtd:
            if _ENTITY_DECL_RE.search(data):
                raise UnsafeXmlError(
                    f"{source.name}: XML entity declarations are not allowed "
                    "(possible XXE or entity-expansion payload)"
                )
            if _DTD_SUBSET_RE.search(data):
                raise UnsafeXmlError(
                    f"{source.name}: DTD internal subsets are not allowed "
                    "(possible entity-expansion payload)"
                )
        try:
            root = ET.fromstring(data)
        except ET.ParseError as exc:
            raise MalformedXmlError(f"{source.name}: invalid XML ({exc})") from exc
        return self._parse_root(root, source)

    def _parse_root(self, root: ET.Element, source: Path) -> ScanResult:
        if _local_tag(root).lower() != "nmaprun":
            raise InvalidNmapXmlError(
                f"{source.name}: root element is <{_local_tag(root)}>, expected <nmaprun>"
            )

        filename = source.name
        task = self._parse_task(root, filename)
        hosts: list[Host] = []
        ports: list[Port] = []
        findings: list[Finding] = []

        for host_node in root.findall("host"):
            hosts.append(self._parse_host(host_node, filename))
            self._parse_ports(host_node, filename, ports, findings)

        # <hosthint> entries are speculative hosts; keep them in the report.
        for hint in root.findall("hosthint"):
            hosts.append(self._parse_host(hint, filename))

        # Pre/post-run scripts are not attached to a specific host.
        for container_tag in ("prescript", "postscript"):
            container = root.find(container_tag)
            if container is None:
                continue
            for script in container.findall("script"):
                findings.append(
                    self._parse_script(
                        script,
                        xml_file=filename,
                        ip_address="",
                        port_id="",
                        protocol="",
                    )
                )

        return ScanResult(
            source=source, task_info=task, hosts=hosts, ports=ports, findings=findings
        )

    @staticmethod
    def _parse_task(root: ET.Element, filename: str) -> TaskInfo:
        task = TaskInfo(
            xml_file=filename,
            scanner=_attr(root, "scanner"),
            nmap_version=_attr(root, "version"),
            scan_args=_attr(root, "args"),
            start_time=_attr(root, "start"),
            start_time_str=_attr(root, "startstr"),
            xml_output_version=_attr(root, "xmloutputversion"),
        )
        finished = root.find("runstats/finished")
        if finished is not None:
            task.finish_time = _attr(finished, "time")
            task.finish_time_str = _attr(finished, "timestr")
            task.elapsed_time = _attr(finished, "elapsed")
            task.exit_status = _attr(finished, "exit")
        hoststats = root.find("runstats/hosts")
        if hoststats is not None:
            task.total_hosts = _attr(hoststats, "total")
            task.up_hosts = _attr(hoststats, "up")
            task.down_hosts = _attr(hoststats, "down")
        return task

    @staticmethod
    def _parse_host(host: ET.Element, filename: str) -> Host:
        status = host.find("status")
        return Host(
            xml_file=filename,
            ip_address=_primary_address(host),
            hostname=_hostnames(host),
            status=_attr(status, "state"),
            status_reason=_attr(status, "reason"),
            status_ttl=_attr(status, "reason_ttl"),
            start_time=_attr(host, "starttime"),
            end_time=_attr(host, "endtime"),
        )

    def _parse_ports(
        self,
        host: ET.Element,
        filename: str,
        ports: list[Port],
        findings: list[Finding],
    ) -> None:
        """Walk ``<port>`` nodes once, collecting both ports and scripts."""
        ip = _primary_address(host)
        ports_node = host.find("ports")
        if ports_node is None:
            return

        for node in ports_node.findall("port"):
            port_id = _attr(node, "portid")
            protocol = _attr(node, "protocol")
            state = node.find("state")
            service = node.find("service")

            # CPEs live *inside* <service> in real Nmap output. The 1.x parser
            # looked for <port><cpe> and therefore always produced an empty
            # column; the second lookup tolerates non-standard producers.
            cpe_nodes = list(service.findall("cpe")) if service is not None else []
            cpe_nodes.extend(node.findall("cpe"))

            ports.append(
                Port(
                    xml_file=filename,
                    ip_address=ip,
                    port_id=port_id,
                    protocol=protocol,
                    state=_attr(state, "state"),
                    state_reason=_attr(state, "reason"),
                    state_ttl=_attr(state, "reason_ttl"),
                    service_name=_attr(service, "name"),
                    service_product=_attr(service, "product"),
                    service_version=_attr(service, "version"),
                    service_extrainfo=_attr(service, "extrainfo"),
                    service_method=_attr(service, "method"),
                    service_conf=_attr(service, "conf"),
                    cpe=_join([(cpe.text or "").strip() for cpe in cpe_nodes]),
                )
            )

            for script in node.findall("script"):
                findings.append(
                    self._parse_script(
                        script,
                        xml_file=filename,
                        ip_address=ip,
                        port_id=port_id,
                        protocol=protocol,
                    )
                )

        hostscript = host.find("hostscript")
        if hostscript is not None:
            for script in hostscript.findall("script"):
                findings.append(
                    self._parse_script(
                        script,
                        xml_file=filename,
                        ip_address=ip,
                        port_id="",
                        protocol="",
                    )
                )

    @staticmethod
    def _parse_script(
        script: ET.Element,
        *,
        xml_file: str,
        ip_address: str,
        port_id: str,
        protocol: str,
    ) -> Finding:
        elements: dict[str, list[str]] = {}
        # ``iter`` also reaches <elem> nested inside NSE <table> structures.
        for elem in script.iter("elem"):
            key = (elem.get("key") or "").strip().lower()
            if not key:
                continue
            key = _KEY_ALIASES.get(key, key)
            value = (elem.text or "").strip()
            elements.setdefault(key, []).append(value)

        return Finding.from_elements(
            elements,
            xml_file=xml_file,
            ip_address=ip_address,
            port_id=port_id,
            protocol=protocol,
            script_id=_attr(script, "id"),
            output=(_attr(script, "output")).strip(),
            version=_attr(script, "version"),
        )


__all__ = ["DEFAULT_MAX_BYTES", "NmapParser"]
