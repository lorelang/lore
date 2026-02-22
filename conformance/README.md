# Lorelang Conformance Suite

This directory pins language behavior with reference fixtures.

## Purpose

Conformance fixtures help:

- keep language semantics stable
- prevent silent parser/compiler regressions
- support external implementations of Lorelang

## Layout

- `v0.2/core/`: canonical fixture for core Lorelang v0.2 behavior

## Validation

Conformance checks run in:

- `tests/test_language_conformance.py`

Run manually:

```bash
PYTHONPATH=src python3 -m pytest -q tests/test_language_conformance.py
```

## Contributor Rule

Any language-level change must update:

1. `spec/SPECIFICATION.md`
2. Relevant fixture(s) in this directory
3. Conformance tests
