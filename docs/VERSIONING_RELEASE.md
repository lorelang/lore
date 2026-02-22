# Versioning and Release Cycle

This is the canonical release process for Lorelang.

## Versioning Policy

Lorelang follows semantic versioning at language and package level:

- `MAJOR` for breaking changes
- `MINOR` for backward-compatible feature additions
- `PATCH` for backward-compatible fixes and clarifications

Current single-version model uses the same number across:

- `pyproject.toml` (`project.version`)
- `src/lore/__init__.py` (`__version__`)
- spec heading in `spec/SPECIFICATION.md`

## How to Choose a Bump

Use these rules:

- Bump `PATCH` when behavior is fixed without intended break.
- Bump `MINOR` when adding language/tooling features that keep existing `.lore` files working.
- Bump `MAJOR` when grammar/semantics become incompatible or defaults break existing usage.

## Release Steps

1. Freeze scope for the release.
2. Update docs/spec for all user-visible changes.
3. Bump version in:
   - `pyproject.toml`
   - `src/lore/__init__.py`
   - `spec/SPECIFICATION.md` (if language version changed)
   - tests that pin the version (for example `tests/test_v02_features.py`)
4. Run quality gates:
   - `make launch-check`
   - `make dist-check`
5. Commit and tag:
   - `git tag vX.Y.Z`
   - `git push origin vX.Y.Z`
6. Let CI run:
   - `.github/workflows/ci.yml`
   - `.github/workflows/release-check.yml`
7. Publish release notes and artifacts.

## Suggested Cadence

- `PATCH`: as needed for bug fixes
- `MINOR`: grouped feature release after stability checks
- `MAJOR`: rare, explicit migration release

## Required Output per Release

- Passing `make launch-check`
- Passing `make dist-check`
- Updated docs for new commands or behavior
- Clear release notes with upgrade impact
