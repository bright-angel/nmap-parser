"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def basic_xml(fixtures_dir: Path) -> Path:
    return fixtures_dir / "basic_scan.xml"


@pytest.fixture
def vuln_xml(fixtures_dir: Path) -> Path:
    return fixtures_dir / "vuln_scan.xml"


@pytest.fixture
def sample_dataset():
    """Two parsed files aggregated into one dataset."""
    from nmap_parser import NmapParser, ScanDataset

    parser = NmapParser()
    dataset = ScanDataset()
    dataset.extend(parser.parse(FIXTURES / "basic_scan.xml"))
    dataset.extend(parser.parse(FIXTURES / "vuln_scan.xml"))
    return dataset
