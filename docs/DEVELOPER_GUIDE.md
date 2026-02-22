# Developer Guide

This guide is for contributors building Lorelang itself.

## Prerequisites

- Python 3.10+
- `pip`

## Local Setup

```bash
git clone <repo-url>
cd lore
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Daily Commands

```bash
# full test suite
PYTHONPATH=src python3 -m pytest -q

# validate an example ontology
lore validate examples/b2b-saas-gtm

# compile sample agent context
lore compile examples/b2b-saas-gtm -t agent --view "RevOps"

# run curation checks
lore curate examples/b2b-saas-gtm --dry-run
```

Shortcut equivalents:

```bash
make test
make conformance
make validate-examples
make compile-matrix
make smoke
make launch-check
```

## Repo Map

- `src/lore/` — parser, validator, CLI, compilers, curation, ingestion
- `tests/` — unit and integration tests
- `spec/SPECIFICATION.md` — language spec
- `examples/` — real ontology examples
- `conformance/` — language conformance fixtures

## Contribution Workflow

1. Pick missing capability or bug.
2. Implement change in `src/lore/`.
3. Add or update tests in `tests/`.
4. Update docs/spec if behavior changed.
5. Run `PYTHONPATH=src python3 -m pytest -q`.
6. Open PR.

## Language-Level Changes

If your change affects language behavior:

1. Update `spec/SPECIFICATION.md`.
2. Update fixtures in `conformance/`.
3. Update `tests/test_language_conformance.py`.
