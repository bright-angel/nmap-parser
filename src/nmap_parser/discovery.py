"""Input discovery: turn a file or directory into a deterministic file list."""

from __future__ import annotations

from pathlib import Path

from .exceptions import InputNotFoundError, InvalidInputError

XML_SUFFIX = ".xml"


def _is_xml(path: Path) -> bool:
    # Nmap output is always lower-case on Unix, but Windows tooling and some
    # scanners produce ".XML"; match case-insensitively.
    return path.suffix.lower() == XML_SUFFIX


def discover_xml_files(input_path: str | Path, *, recursive: bool = False) -> list[Path]:
    """Return a sorted, de-duplicated list of XML files for *input_path*.

    A single file is accepted only when it has an ``.xml`` suffix. A directory
    is scanned with ``glob`` (or ``rglob`` when *recursive* is set).

    Raises:
        InputNotFoundError: the path does not exist.
        InvalidInputError: the path is a non-XML file or a non-directory.
    """
    root = Path(input_path).expanduser()
    if not root.exists():
        raise InputNotFoundError(f"Input path does not exist: {root}")

    if root.is_file():
        if not _is_xml(root):
            raise InvalidInputError(f"Input file is not an XML document: {root}")
        return [root]

    if not root.is_dir():
        raise InvalidInputError(f"Input path is neither a file nor a directory: {root}")

    candidates = root.rglob("*") if recursive else root.glob("*")
    seen: set[str] = set()
    files: list[Path] = []
    for candidate in candidates:
        if not candidate.is_file() or not _is_xml(candidate):
            continue
        try:
            key = str(candidate.resolve()).casefold()
        except OSError:  # broken symlink or inaccessible path
            continue
        if key in seen:
            continue
        seen.add(key)
        files.append(candidate)

    files.sort(key=lambda p: str(p).casefold())
    return files
