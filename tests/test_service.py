"""Conversion orchestration tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from nmap_parser import (
    AllInputsFailedError,
    ConversionService,
    InputNotFoundError,
    InvalidInputError,
    NmapParserError,
    Progress,
)


@pytest.fixture
def scan_dir(tmp_path: Path, basic_xml: Path, fixtures_dir: Path) -> Path:
    directory = tmp_path / "scans"
    directory.mkdir()
    shutil.copy(basic_xml, directory / "basic.xml")
    (directory / "nested").mkdir()
    shutil.copy(fixtures_dir / "nested" / "inner.xml", directory / "nested" / "inner.xml")
    return directory


def test_single_file(basic_xml: Path, tmp_path: Path) -> None:
    outcome = ConversionService().convert(basic_xml, tmp_path / "out.xlsx")
    assert outcome.output.is_file()
    assert outcome.ok
    assert outcome.stats.files_total == 1
    assert outcome.stats.files_ok == 1
    assert outcome.stats.hosts_total == 3
    assert outcome.stats.hosts_up == 2
    assert outcome.stats.ports_total == 2
    assert outcome.stats.ports_open == 1
    assert outcome.elapsed >= 0


def test_non_recursive_directory(scan_dir: Path, tmp_path: Path) -> None:
    outcome = ConversionService().convert(scan_dir, tmp_path / "out.xlsx")
    assert outcome.stats.files_total == 1


def test_recursive_directory(scan_dir: Path, tmp_path: Path) -> None:
    outcome = ConversionService().convert(scan_dir, tmp_path / "out.xlsx", recursive=True)
    assert outcome.stats.files_total == 2
    assert outcome.stats.ports_total == 3


def test_partial_failure_still_produces_a_report(
    scan_dir: Path,
    fixtures_dir: Path,
    tmp_path: Path,
) -> None:
    shutil.copy(fixtures_dir / "malformed.xml", scan_dir / "broken.xml")
    output = tmp_path / "out.xlsx"
    outcome = ConversionService().convert(scan_dir, output)
    assert output.is_file()
    assert outcome.stats.files_ok == 1
    assert outcome.stats.files_failed == 1
    assert outcome.ok is False
    assert outcome.failures[0].path.name == "broken.xml"


def test_all_failed_writes_nothing(fixtures_dir: Path, tmp_path: Path) -> None:
    only_broken = tmp_path / "broken"
    only_broken.mkdir()
    shutil.copy(fixtures_dir / "malformed.xml", only_broken / "a.xml")
    output = tmp_path / "out.xlsx"
    with pytest.raises(AllInputsFailedError):
        ConversionService().convert(only_broken, output)
    assert not output.exists()


def test_fail_fast_aborts_without_report(
    scan_dir: Path,
    fixtures_dir: Path,
    tmp_path: Path,
) -> None:
    shutil.copy(fixtures_dir / "malformed.xml", scan_dir / "aaa_broken.xml")
    output = tmp_path / "out.xlsx"
    with pytest.raises(NmapParserError):
        ConversionService().convert(scan_dir, output, fail_fast=True)
    assert not output.exists()


def test_empty_directory(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(InvalidInputError, match="No XML files"):
        ConversionService().convert(empty, tmp_path / "out.xlsx")


def test_missing_input(tmp_path: Path) -> None:
    with pytest.raises(InputNotFoundError):
        ConversionService().convert(tmp_path / "nope", tmp_path / "out.xlsx")


def test_progress_events(scan_dir: Path, tmp_path: Path) -> None:
    events: list[Progress] = []
    ConversionService(progress=events.append).convert(
        scan_dir,
        tmp_path / "out.xlsx",
        recursive=True,
    )
    stages = [event.stage for event in events]
    assert "discover" in stages
    assert "parse" in stages
    assert "write" in stages
    assert "done" in stages
    parse_events = [e for e in events if e.stage == "parse"]
    assert len(parse_events) == 2
    assert all(0 < e.current <= e.total for e in parse_events)
    assert parse_events[0].message == "ok"
