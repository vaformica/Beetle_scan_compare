# Contributing

## Documentation identity convention

When a repository has a project icon, keep it prominently at the top of the
main `README.md` and every user-facing how-to HTML page. The icon is a visual
identifier that helps distinguish projects quickly, so do not move it into a
footer or secondary branding section.

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

## Build the Apple Silicon DMG

Create a dedicated Python 3.12 build environment, install the packaging
dependencies, then run:

```bash
python3.12 -m venv .venv-build
.venv-build/bin/python -m pip install pyinstaller Pillow
./packaging/build_macos.sh
```

The standalone app and DMG are written beneath `dist/`. Build artifacts are
excluded from Git.

Every successful build also creates two paste-ready GitHub files:

- `dist/GITHUB_RELEASE_SUMMARY.txt` for the short release summary; and
- `dist/GITHUB_RELEASE_DESCRIPTION.md` for the full description, artifact name,
  and automatically calculated SHA-256 checksum.

It also creates GitHub Desktop fallback text:

- `dist/GITHUB_DESKTOP_COMMIT_SUMMARY.txt`; and
- `dist/GITHUB_DESKTOP_COMMIT_DESCRIPTION.txt`.

When GitHub Copilot is available in GitHub Desktop, click **Generate commit
message with Copilot** beside the Summary field instead. The repository-wide
`.github/copilot-instructions.md` file guides the generated Summary and
Description automatically.

Update `packaging/GITHUB_RELEASE_TEMPLATE.md` and
`packaging/GITHUB_RELEASE_SUMMARY.txt` whenever the user-visible release notes
change. The build script adds artifact verification automatically.

The macOS build uses `assets/BeetleScanCompare.icns`. Its 1024-pixel source is
retained beside it so future icon revisions can be resized into a replacement
iconset without degrading a smaller derivative. The original dark icon remains
at `assets/beetle-scan-compare-icon-dark-v1.png`; the unversioned source and
`.icns` are the lighter, high-contrast defaults for the next build.

## Pull requests

Describe the user-visible change, add or update tests, and note any change to
CSV columns or matching behavior. Do not commit real beetle scans, review
exports, personal paths, or other research data.
