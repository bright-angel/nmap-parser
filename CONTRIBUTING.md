# Contributing

Thanks for helping improve nmap-parser.

## Development setup

```bash
git clone https://github.com/bright-angel/nmap-parser.git
cd nmap-parser

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"            # GUI extra, test deps, ruff, mypy, build
```

If you only need the CLI, `pip install -e ".[test]"` is enough — the GUI
dependency is optional.

## Checks

Run these before opening a pull request:

```bash
pytest                             # unit + integration tests
ruff check .                       # lint
ruff format --check .              # formatting
mypy                               # static types
python -m build                    # wheel + sdist
```

CI runs the same checks on Python 3.9–3.13 on Linux and Windows.

## Layout

```
src/nmap_parser/   application code (src layout, nothing importable by accident)
tests/             pytest suite + XML fixtures
docs/              architecture, migration, packaging notes
assets/            icons and other non-code resources
```

See [docs/architecture.md](docs/architecture.md) for how the layers fit
together.

## Adding a column to the report

1. Add a typed field to the relevant dataclass in `models.py`.
2. Populate it in `parser.py`.
3. Add a `Column` entry to the matching sheet in `workbook.py` — the sheet is
   generated from that declaration, so no manual cell loops are needed.
4. Add a fixture assertion in `tests/`.

## Conventions

- Keep `parser.py` free of presentation concerns (no emoji, no printing).
- Never write untrusted scan values without the workbook's string guard.
- Public functions are typed; run `mypy` to verify.
- Add a `CHANGELOG.md` entry under "Unreleased" for user-visible changes.

## Reporting bugs

Please include the Nmap version, a minimal redacted XML sample that reproduces
the issue, the command you ran, and the full traceback. Never attach scan data
containing real IPs or hostnames from a production network.
