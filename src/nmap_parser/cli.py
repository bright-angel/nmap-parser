"""Command-line interface.

Exit codes are meaningful so the tool can be used in CI:

===== =========================================================
  0   every file parsed and the report was written
  1   the report was written but one or more files failed
  2   fatal error (bad input, all files failed, write failed)
===== =========================================================
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .__about__ import __version__
from .exceptions import NmapParserError
from .models import ConversionOutcome, Progress
from .service import ConversionService

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_FATAL = 2

_LOG_LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40, "quiet": 50}


class Reporter:
    """Small stdout/stderr writer with level filtering."""

    def __init__(self, level: int) -> None:
        self.level = level

    def detail(self, message: str) -> None:
        if self.level <= 10:
            print(message)

    def info(self, message: str) -> None:
        if self.level <= 20:
            print(message)

    def warn(self, message: str) -> None:
        if self.level <= 30:
            print(message, file=sys.stderr)

    def error(self, message: str) -> None:
        if self.level <= 50:
            print(message, file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser (exposed for tests)."""
    parser = argparse.ArgumentParser(
        prog="nmap-parser",
        description="Convert Nmap XML scan results into an Excel report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  nmap-parser scan.xml report.xlsx
  nmap-parser ./scans report.xlsx -r
  nmap-parser ./scans report.xlsx -r --fail-fast --log-level quiet

Exit codes: 0 = success, 1 = partial failures, 2 = fatal error.
""",
    )
    parser.add_argument("input", help="input XML file or a directory of XML files")
    parser.add_argument("output", help="output Excel path (.xlsx appended if missing)")
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="search subdirectories recursively",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="suppress all non-error output (same as --log-level quiet)",
    )
    parser.add_argument(
        "--log-level",
        choices=sorted(_LOG_LEVELS),
        default="info",
        help="output verbosity (default: info)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="abort on the first malformed file, without writing a report",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat any per-file failure as a fatal error (exit 2)",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="do not print the statistics block on success",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _print_summary(reporter: Reporter, outcome: ConversionOutcome, show: bool) -> None:
    if not show:
        return
    stats = outcome.stats
    reporter.info("")
    reporter.info("[=] Summary")
    reporter.info(
        f"  Files : {stats.files_ok} ok, {stats.files_failed} failed ({stats.files_total} total)"
    )
    reporter.info(f"  Hosts : {stats.hosts_total} (up {stats.hosts_up}, down {stats.hosts_down})")
    reporter.info(
        f"  Ports : {stats.ports_total} (open {stats.ports_open}, "
        f"closed/filtered {stats.ports_closed})"
    )
    reporter.info(f"  NSE   : {stats.findings_total} findings, {stats.scripts_total} scripts")
    reporter.detail(f"  Time  : {outcome.elapsed:.3f} s")
    reporter.detail(f"  Output: {outcome.output.resolve()}")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns an exit code rather than calling ``sys.exit``."""
    args = build_parser().parse_args(argv)
    level = _LOG_LEVELS["quiet"] if args.quiet else _LOG_LEVELS[args.log_level]
    reporter = Reporter(level)

    def on_progress(event: Progress) -> None:
        if event.stage == "discover" and event.total:
            reporter.info(f"[>] Found {event.total} XML file(s)")
        elif event.stage == "parse" and event.path is not None:
            if event.message == "ok":
                reporter.info(f"  [OK] {event.path.name}")
                reporter.detail(f"       {event.path}")
            else:
                reporter.warn(f"  [X]  {event.message}")
        elif event.stage == "write":
            reporter.info("[E] Writing Excel report...")

    service = ConversionService(progress=on_progress)
    try:
        reporter.info(f"[>] Scanning {args.input} ...")
        outcome = service.convert(
            args.input,
            args.output,
            recursive=args.recursive,
            fail_fast=args.fail_fast,
        )
    except KeyboardInterrupt:
        reporter.error("[X] Interrupted")
        return 130
    except NmapParserError as exc:
        reporter.error(f"[X] {exc}")
        return EXIT_FATAL

    for failure in outcome.failures:
        reporter.error(f"[X] {failure.message}")

    _print_summary(reporter, outcome, show=not args.no_summary and not args.quiet)
    reporter.info(f"\n[OK] Done! Output: {outcome.output}")

    if outcome.failures:
        return EXIT_FATAL if args.strict else EXIT_PARTIAL
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
