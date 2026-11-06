"""Orchestration shared by the CLI and the GUI.

Both front-ends used to duplicate the "discover → loop → aggregate → write"
logic (and diverged in how they handled errors). They now call one method and
consume :class:`~models.Progress` notifications.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from .discovery import discover_xml_files
from .exceptions import (
    AllInputsFailedError,
    InvalidInputError,
    NmapParserError,
    OutputError,
)
from .models import ConversionOutcome, FileFailure, Progress, ScanDataset, ScanResult
from .parser import NmapParser
from .workbook import write_report

ProgressCallback = Callable[[Progress], None]


class ConversionService:
    """Convert one XML file or a directory of them into an Excel report."""

    def __init__(
        self,
        *,
        parser: NmapParser | None = None,
        progress: ProgressCallback | None = None,
    ) -> None:
        self.parser = parser or NmapParser()
        self.progress = progress

    def convert(
        self,
        input_path: str | Path,
        output: str | Path,
        *,
        recursive: bool = False,
        fail_fast: bool = False,
    ) -> ConversionOutcome:
        """Run a full conversion.

        Raises:
            InputNotFoundError / InvalidInputError: bad input or no XML found.
            AllInputsFailedError: every file failed; no report is written.
            OutputError: the XLSX file could not be written.
            NmapParserError: first parse error when *fail_fast* is set.
        """
        started = time.perf_counter()
        self._emit(Progress("discover"))

        files = discover_xml_files(input_path, recursive=recursive)
        if not files:
            raise InvalidInputError(f"No XML files found under {Path(input_path)}")

        total = len(files)
        self._emit(Progress("discover", 0, total))
        dataset = ScanDataset()
        failures: list[FileFailure] = []
        ok_count = 0

        for index, file in enumerate(files, start=1):
            try:
                result: ScanResult = self.parser.parse(file)
            except (NmapParserError, OSError, ValueError) as exc:
                if fail_fast:
                    raise NmapParserError(f"Aborted at {file.name}: {exc}") from exc
                # Parser errors already include the file name; OSError may not.
                detail = str(exc)
                message = detail if file.name in detail else f"{file.name}: {detail}"
                failures.append(FileFailure(path=file, message=message))
                self._emit(Progress("parse", index, total, path=file, message=message))
            else:
                dataset.extend(result)
                ok_count += 1
                self._emit(Progress("parse", index, total, path=file, message="ok"))

        if ok_count == 0:
            raise AllInputsFailedError(
                f"All {total} XML file(s) failed to parse; no report was generated. "
                f"First error: {failures[0].message}"
            )

        self._emit(Progress("write", total, total))
        try:
            destination = write_report(dataset, output)
        except (OSError, ValueError) as exc:
            raise OutputError(f"Cannot write report: {exc}") from exc

        outcome = ConversionOutcome(
            output=destination,
            dataset=dataset,
            stats=dataset.stats(
                files_total=total,
                files_ok=ok_count,
                files_failed=len(failures),
            ),
            failures=failures,
            elapsed=time.perf_counter() - started,
        )
        self._emit(Progress("done", total, total, path=destination))
        return outcome

    def _emit(self, event: Progress) -> None:
        if self.progress is not None:
            self.progress(event)


__all__ = ["ConversionService", "ProgressCallback"]
