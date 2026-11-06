"""Typed data models shared by every layer.

The 1.x code passed ``dict[str, Any]`` around, which is why ``write_to_xlsx``
could receive either a single ``task_info`` dict or a list of them. These
dataclasses make the shape explicit and are the only data structure that
crosses layer boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TaskInfo:
    """Scan-level metadata from ``<nmaprun>`` and ``<runstats>``."""

    xml_file: str = ""
    scanner: str = ""
    nmap_version: str = ""
    scan_args: str = ""
    start_time: str = ""
    start_time_str: str = ""
    xml_output_version: str = ""
    total_hosts: str = ""
    up_hosts: str = ""
    down_hosts: str = ""
    finish_time: str = ""
    finish_time_str: str = ""
    elapsed_time: str = ""
    exit_status: str = ""


@dataclass
class Host:
    """One ``<host>`` (or ``<hosthint>``) entry."""

    xml_file: str = ""
    ip_address: str = ""
    hostname: str = ""
    status: str = ""
    status_reason: str = ""
    status_ttl: str = ""
    start_time: str = ""
    end_time: str = ""


@dataclass
class Port:
    """One ``<port>`` entry, including its service and CPE data."""

    xml_file: str = ""
    ip_address: str = ""
    port_id: str = ""
    protocol: str = ""
    state: str = ""
    state_reason: str = ""
    state_ttl: str = ""
    service_name: str = ""
    service_product: str = ""
    service_version: str = ""
    service_extrainfo: str = ""
    service_method: str = ""
    service_conf: str = ""
    cpe: str = ""


# NSE <elem> keys surfaced as dedicated report columns. Anything else is still
# retained in Finding.elements, so no script data is silently discarded.
FINDING_KEYS: tuple[str, ...] = (
    "result",
    "severity",
    "description",
    "risk_factor",
    "see_also",
    "solution",
    "cve",
    "bid",
    "cert",
    "msf_module",
    "osvdb",
)


@dataclass
class Finding:
    """One NSE ``<script>`` result (port-scoped or host-scoped)."""

    xml_file: str = ""
    ip_address: str = ""
    port_id: str = ""
    protocol: str = ""
    script_id: str = ""
    output: str = ""
    version: str = ""
    result: str = ""
    severity: str = ""
    description: str = ""
    risk_factor: str = ""
    see_also: str = ""
    solution: str = ""
    cve: str = ""
    bid: str = ""
    cert: str = ""
    msf_module: str = ""
    osvdb: str = ""
    elements: dict[str, list[str]] = field(default_factory=dict, repr=False)

    @classmethod
    def from_elements(
        cls,
        elements: dict[str, list[str]],
        **identity: str,
    ) -> Finding:
        """Build a Finding, joining repeated ``<elem>`` keys with ``; ``."""
        values = {key: "; ".join(elements.get(key, ())) for key in FINDING_KEYS}
        return cls(**identity, **values, elements={k: list(v) for k, v in elements.items()})


@dataclass
class ScanResult:
    """Everything parsed out of one XML file."""

    source: Path
    task_info: TaskInfo
    hosts: list[Host] = field(default_factory=list)
    ports: list[Port] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


@dataclass
class ScanDataset:
    """Aggregated rows from one or more XML files, ready for the workbook."""

    tasks: list[TaskInfo] = field(default_factory=list)
    hosts: list[Host] = field(default_factory=list)
    ports: list[Port] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def extend(self, result: ScanResult) -> None:
        """Append one file's parsed rows."""
        self.tasks.append(result.task_info)
        self.hosts.extend(result.hosts)
        self.ports.extend(result.ports)
        self.findings.extend(result.findings)

    def stats(
        self,
        *,
        files_total: int = 0,
        files_ok: int = 0,
        files_failed: int = 0,
    ) -> SummaryStats:
        """Compute report statistics from the rows actually present."""
        hosts_up = sum(1 for h in self.hosts if h.status.lower() == "up")
        ports_open = sum(1 for p in self.ports if p.state.lower() == "open")
        return SummaryStats(
            files_total=files_total,
            files_ok=files_ok,
            files_failed=files_failed,
            hosts_total=len(self.hosts),
            hosts_up=hosts_up,
            hosts_down=len(self.hosts) - hosts_up,
            ports_total=len(self.ports),
            ports_open=ports_open,
            ports_closed=len(self.ports) - ports_open,
            findings_total=len(self.findings),
            scripts_total=len({f.script_id for f in self.findings if f.script_id}),
        )


@dataclass(frozen=True)
class SummaryStats:
    """Numbers shown in CLI/GUI summaries."""

    files_total: int = 0
    files_ok: int = 0
    files_failed: int = 0
    hosts_total: int = 0
    hosts_up: int = 0
    hosts_down: int = 0
    ports_total: int = 0
    ports_open: int = 0
    ports_closed: int = 0
    findings_total: int = 0
    scripts_total: int = 0


@dataclass(frozen=True)
class Progress:
    """One progress notification emitted by :class:`ConversionService`."""

    stage: str  # "discover" | "parse" | "write" | "done"
    current: int = 0
    total: int = 0
    path: Path | None = None
    message: str = ""

    @property
    def fraction(self) -> float:
        """Progress in the range 0.0–1.0."""
        if self.total <= 0:
            return 0.0
        return min(1.0, max(0.0, self.current / self.total))


@dataclass(frozen=True)
class FileFailure:
    """A single input file that could not be parsed."""

    path: Path
    message: str


@dataclass
class ConversionOutcome:
    """Result of a full conversion run."""

    output: Path
    dataset: ScanDataset
    stats: SummaryStats
    failures: list[FileFailure] = field(default_factory=list)
    elapsed: float = 0.0

    @property
    def ok(self) -> bool:
        """True when at least one file converted and none failed."""
        return self.stats.files_ok > 0 and not self.failures
