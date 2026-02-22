# Lorelang Language Charter

Lorelang is a source language for AI-first, self-improving ontologies.

This document defines Lorelang at language level, separate from any single tool.
The `lore` CLI is the reference implementation of the language toolchain.

## Language Scope

Lorelang core includes:

- File grammar and section semantics for `.lore` files
- Directory-level ontology model (`entities/`, `relationships/`, etc.)
- Frontmatter metadata conventions (`provenance`, `status`, dates)
- Semantic meaning of parsed structures in the `Ontology` model

Tooling built on top (compilers, curators, adapters) is ecosystem layer.

## Language Guarantees

Lorelang uses semantic versioning with language-level guarantees:

- `MAJOR`: breaking grammar or semantic meaning changes
- `MINOR`: additive language features, backward compatible
- `PATCH`: bug fixes and clarifications, no intentional behavior break

For `0.x` releases, changes can still evolve quickly, but the project commits to:

- No silent breaking changes without spec updates
- Conformance fixtures for all new language features
- Migration notes for behavior-impacting changes

## Compatibility Policy

### Backward compatibility

- A valid ontology in `v0.2` should remain parseable in later `0.2.x`.
- Deprecations should remain accepted for at least one minor cycle before removal.
- Parser/validator behavior changes must be reflected in conformance tests.

### Forward compatibility

- Unknown frontmatter keys should be tolerated by parser when safe.
- Unknown prose blocks are preserved; Lorelang remains prose-first.

### Plugin contract stability

Plugin authors target the `Ontology` dataclass contract. Contract changes require:

- Spec update
- Migration guidance

## Governance Model (Current Stage)

Lorelang is in an early build phase and uses a PR-first workflow:

- Open an issue or PR
- Implement missing capability
- Add/update tests
- Merge after maintainer review

## Conformance Suite

Language behavior is pinned by conformance fixtures:

- Location: `conformance/`
- Current core fixture: `conformance/v0.2/core/`
- Validation: `tests/test_language_conformance.py`

Any language-level change should update:

1. `spec/SPECIFICATION.md`
2. Conformance fixtures
3. Conformance tests

## Ecosystem Direction

Lorelang is intended to support an open ecosystem:

- Alternate parsers/compilers in other languages
- Domain packs and ontology starter kits
- Curator and compiler plugin libraries
- Editor tooling (syntax highlighting, linting, LSP)

The language is the product. The CLI is the first implementation.
