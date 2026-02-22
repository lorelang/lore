# Contributing

PRs are welcome.

If something is missing, build it and open a PR with tests.

## Quick Checklist

1. Implement the change in `src/lore/`.
2. Add or update tests in `tests/`.
3. Update docs/spec if behavior changed.
4. Run:

```bash
PYTHONPATH=src python3 -m pytest -q
```

Or run the launch-ready shortcut:

```bash
make launch-check
```

For version bumps and release flow, see:

- `docs/VERSIONING_RELEASE.md`

## Language-Level Changes

For language behavior changes:

1. Update `spec/SPECIFICATION.md`.
2. Update `conformance/` fixtures.
3. Update `tests/test_language_conformance.py`.
