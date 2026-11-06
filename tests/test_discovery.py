"""Input discovery tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from nmap_parser import InputNotFoundError, InvalidInputError, discover_xml_files


def test_single_xml_file(basic_xml: Path) -> None:
    assert discover_xml_files(basic_xml) == [basic_xml]


def test_single_file_rejects_non_xml(tmp_path: Path) -> None:
    text_file = tmp_path / "notes.txt"
    text_file.write_text("not xml", encoding="utf-8")
    with pytest.raises(InvalidInputError):
        discover_xml_files(text_file)


def test_missing_path(tmp_path: Path) -> None:
    with pytest.raises(InputNotFoundError):
        discover_xml_files(tmp_path / "does-not-exist")


def test_directory_non_recursive_excludes_nested(fixtures_dir: Path) -> None:
    files = discover_xml_files(fixtures_dir)
    assert fixtures_dir / "basic_scan.xml" in files
    assert fixtures_dir / "nested" / "inner.xml" not in files
    assert all(p.parent == fixtures_dir for p in files)


def test_directory_recursive_includes_nested(fixtures_dir: Path) -> None:
    files = discover_xml_files(fixtures_dir, recursive=True)
    assert fixtures_dir / "nested" / "inner.xml" in files
    assert len(files) >= 6


def test_suffix_is_case_insensitive(fixtures_dir: Path) -> None:
    files = discover_xml_files(fixtures_dir)
    assert fixtures_dir / "UPPERCASE.XML" in files


def test_results_are_sorted(fixtures_dir: Path) -> None:
    files = discover_xml_files(fixtures_dir, recursive=True)
    assert [str(p).casefold() for p in files] == sorted(str(p).casefold() for p in files)


def test_empty_directory(tmp_path: Path) -> None:
    assert discover_xml_files(tmp_path) == []
