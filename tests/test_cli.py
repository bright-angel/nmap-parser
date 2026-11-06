"""CLI behaviour and exit-code tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from nmap_parser import __version__
from nmap_parser.cli import EXIT_FATAL, EXIT_OK, EXIT_PARTIAL, main


def test_success_writes_report_and_prints_summary(basic_xml: Path, tmp_path: Path, capsys) -> None:
    output = tmp_path / "report"
    assert main([str(basic_xml), str(output)]) == EXIT_OK
    assert (tmp_path / "report.xlsx").is_file()
    captured = capsys.readouterr()
    assert "Summary" in captured.out
    assert "Done!" in captured.out


def test_version_from_single_metadata_source(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_missing_arguments_exits_two() -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_quiet_suppresses_non_error_output(basic_xml: Path, tmp_path: Path, capsys) -> None:
    assert main([str(basic_xml), str(tmp_path / "r.xlsx"), "--quiet"]) == EXIT_OK
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_log_level_debug_prints_absolute_paths(basic_xml: Path, tmp_path: Path, capsys) -> None:
    main([str(basic_xml), str(tmp_path / "r.xlsx"), "--log-level", "debug"])
    assert "Output:" in capsys.readouterr().out


def test_partial_failure_exit_code(
    basic_xml: Path,
    fixtures_dir: Path,
    tmp_path: Path,
) -> None:
    scans = tmp_path / "scans"
    scans.mkdir()
    shutil.copy(basic_xml, scans / "basic.xml")
    shutil.copy(fixtures_dir / "malformed.xml", scans / "broken.xml")
    assert main([str(scans), str(tmp_path / "r.xlsx")]) == EXIT_PARTIAL
    assert main([str(scans), str(tmp_path / "r2.xlsx"), "--strict"]) == EXIT_FATAL


def test_no_xml_files(tmp_path: Path, capsys) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main([str(empty), str(tmp_path / "r.xlsx")]) == EXIT_FATAL
    assert "No XML files" in capsys.readouterr().err


def test_fail_fast_exits_fatal(
    basic_xml: Path,
    fixtures_dir: Path,
    tmp_path: Path,
) -> None:
    scans = tmp_path / "scans"
    scans.mkdir()
    shutil.copy(basic_xml, scans / "basic.xml")
    shutil.copy(fixtures_dir / "malformed.xml", scans / "broken.xml")
    output = tmp_path / "r.xlsx"
    assert main([str(scans), str(output), "--fail-fast"]) == EXIT_FATAL
    assert not output.exists()


def test_no_summary_flag(basic_xml: Path, tmp_path: Path, capsys) -> None:
    main([str(basic_xml), str(tmp_path / "r.xlsx"), "--no-summary"])
    assert "Summary" not in capsys.readouterr().out


def test_python_m_entrypoint() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "nmap_parser", "--version"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert __version__ in completed.stdout
