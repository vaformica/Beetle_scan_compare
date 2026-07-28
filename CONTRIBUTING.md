# Contributing

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
ruff check .
```

Keep filename matching separate from the GUI so it remains testable. Matching
changes must preserve one-to-one pairing and include tests for ambiguous cases.
Never add behavior that modifies source images without an explicit, separately
reviewed design change.

## Pull requests

Describe the user-visible change, add or update tests, and note any change to
CSV columns or matching behavior. Do not commit real beetle scans, review
exports, personal paths, or other research data.
