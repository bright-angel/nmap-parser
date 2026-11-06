# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2026-11-07

### Fixed

- **Normal Nmap output was rejected.** ``nmap -oX`` emits a
  ``<!DOCTYPE nmaprun>`` declaration (and usually an ``<?xml-stylesheet?>``
  processing instruction) at the top of every file. 2.0.0 treated *all* DTD
  declarations as hostile, so converting a single scan failed with
  ``DTD/ENTITY declarations are not allowed``. Detection now distinguishes the
  harmless case from the real attack surface: plain DOCTYPE declarations are
  accepted, while ``<!ENTITY>`` declarations and DTD internal subsets
  (``<!DOCTYPE ... [ ... ]>``) are still refused. External DTD references via
  SYSTEM/PUBLIC are accepted because expat never fetches them.
- CLI failure lines repeated the file name
  (``vuln.xml: failed: vuln.xml: ...``); progress messages now carry the
  already-qualified error once, in CLI and GUI alike.

### Changed

- ``NmapParser(allow_dtd=True)`` now means "allow entity declarations and DTD
  internal subsets for fully trusted input"; a standard Nmap DOCTYPE no longer
  needs it.
- Regression fixture ``tests/fixtures/basic_scan.xml`` now carries the real
  Nmap XML prologue, and the DTD boundary cases have dedicated tests.

## [2.0.0] - 2026-11-06

A structural rewrite. The public behaviour (Nmap XML in → 4-sheet XLSX out,
CLI + GUI) is preserved, but the internal API is now layered and typed. See
[MIGRATION.md](docs/migration.md) for upgrading from 1.x.

### Added

- Standard `src/` layout with a proper `[build-system]` and PEP 621 metadata.
- Typed data models (`ScanResult`, `TaskInfo`, `Host`, `Port`, `Finding`) — no
  more loosely-shaped dictionaries.
- `ConversionService`: one orchestration path shared by CLI and GUI, with a
  progress callback and per-file error reporting.
- `NmapParser` handles host-level scripts (`<hostscript>`), all hostname and
  address entries, and multiple `<elem>` values for the same vulnerability key.
- Excel reports now have frozen headers, autofilters, sensible numeric types,
  a severity-highlighting conditional format, and a generation timestamp in
  the workbook properties.
- `--fail-fast`, `--no-summary`, `--strict`, and `--log-level` CLI flags;
  meaningful exit codes for partial and total failure.
- A real test suite (discovery, parsing, workbook output, security, CLI,
  service) with XML fixtures, plus GitHub Actions CI across Python 3.9–3.13.
- `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/`, `py.typed`, and
  ruff/mypy/pytest configuration.
- `customtkinter` is now an optional `[gui]` extra; the CLI works headless.

### Fixed

- **Single-file conversion crashed**: `parse_nmap_xml()` returns a single
  `task_info` dict but `write_to_xlsx()` iterated it as a list. The unified
  pipeline now always works with a `ScanResult` collection.
- **CPE was always empty**: CPE nodes live under `<service>`, not directly
  under `<port>`; the parser looked in the wrong place.
- **Formula injection**: attacker-controlled scan data beginning with `=`,
  `+`, `-` or `@` was written as an Excel formula. All cells are now written
  as literal strings with `strings_to_formulas=False`.
- **GUI thread-safety**: the worker thread mutated Tk widgets directly. All UI
  updates are now marshalled onto the main thread via `after()`.
- **GUI input controls**: directory selection now works, and paths typed by
  hand into the entry fields are honoured (previously only the file-dialog
  results were used).
- **Silent failures**: parse errors were logged but the CLI still exited 0 and
  produced a report. Failures are counted and reflected in the exit code.
- **Version drift**: `--version` was hardcoded `1.0.0`; it now reads the single
  metadata source.
- Duplicate `nmap-parser-gui` declaration in both `[project.scripts]` and
  `[project.gui-scripts]` (colliding Windows launchers).
- Missing output directory, unclosed workbook on exception, redundant
  `try/except: raise`, double iteration over `<port>` nodes, case-sensitive
  `.xml` matching, and `.gitignore` excluding test fixtures.
- `python -m nmap_parser` with no arguments used to import the GUI on headless
  systems; it now prints help instead.

### Changed

- Minimum Python version raised from 3.8 to 3.9 (typed models, modern
  setuptools). Behaviour on 3.8 is not guaranteed.
- Bumped version to 2.0.0 to reflect the internal API break; a deprecated
  `NmapConverter` compatibility shim keeps simple 1.x integrations working.

## [1.0.0] - 2026-06-15

Initial release: Nmap XML → 4-sheet XLSX, CLI and CustomTkinter GUI.
