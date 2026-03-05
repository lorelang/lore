"""
Ontology Diff.

Compare two Ontology instances and return structured changes:
added, removed, and modified entities, relationships, and rules.
Supports evolution proposals and PR reviews.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from .models import Ontology
from .parser import parse_ontology
from pathlib import Path


@dataclass
class DiffEntry:
    """A single change between two ontologies."""
    kind: str       # "entity", "relationship", "rule", "taxonomy", "glossary"
    action: str     # "added", "removed", "modified"
    name: str
    details: str = ""


@dataclass
class OntologyDiff:
    """Structured diff between two ontologies."""
    changes: list[DiffEntry] = field(default_factory=list)

    @property
    def added(self) -> list[DiffEntry]:
        return [c for c in self.changes if c.action == "added"]

    @property
    def removed(self) -> list[DiffEntry]:
        return [c for c in self.changes if c.action == "removed"]

    @property
    def modified(self) -> list[DiffEntry]:
        return [c for c in self.changes if c.action == "modified"]

    @property
    def summary(self) -> str:
        parts = []
        if self.added:
            parts.append(f"{len(self.added)} added")
        if self.removed:
            parts.append(f"{len(self.removed)} removed")
        if self.modified:
            parts.append(f"{len(self.modified)} modified")
        return ", ".join(parts) if parts else "no changes"

    def to_text(self) -> str:
        """Human-readable diff output."""
        lines: list[str] = []
        lines.append(f"Ontology Diff: {self.summary}")
        lines.append("")

        if self.added:
            lines.append("Added:")
            for entry in self.added:
                lines.append(f"  + [{entry.kind}] {entry.name}")
                if entry.details:
                    lines.append(f"    {entry.details}")
            lines.append("")

        if self.removed:
            lines.append("Removed:")
            for entry in self.removed:
                lines.append(f"  - [{entry.kind}] {entry.name}")
                if entry.details:
                    lines.append(f"    {entry.details}")
            lines.append("")

        if self.modified:
            lines.append("Modified:")
            for entry in self.modified:
                lines.append(f"  ~ [{entry.kind}] {entry.name}")
                if entry.details:
                    lines.append(f"    {entry.details}")
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> str:
        """JSON diff output."""
        data = {
            "summary": self.summary,
            "changes": [
                {
                    "kind": c.kind,
                    "action": c.action,
                    "name": c.name,
                    "details": c.details,
                }
                for c in self.changes
            ],
        }
        return json.dumps(data, indent=2)


def diff_ontologies(ont_a: Ontology, ont_b: Ontology) -> OntologyDiff:
    """
    Compare two Ontology instances.

    ont_a is the "before" (baseline), ont_b is the "after" (current).
    """
    result = OntologyDiff()

    # Entities
    names_a = {e.name for e in ont_a.entities}
    names_b = {e.name for e in ont_b.entities}
    entities_a = {e.name: e for e in ont_a.entities}
    entities_b = {e.name: e for e in ont_b.entities}

    for name in names_b - names_a:
        e = entities_b[name]
        result.changes.append(DiffEntry(
            kind="entity", action="added", name=name,
            details=e.description[:100] if e.description else "",
        ))

    for name in names_a - names_b:
        result.changes.append(DiffEntry(
            kind="entity", action="removed", name=name,
        ))

    for name in names_a & names_b:
        diffs = _diff_entity(entities_a[name], entities_b[name])
        if diffs:
            result.changes.append(DiffEntry(
                kind="entity", action="modified", name=name,
                details="; ".join(diffs),
            ))

    # Relationships
    rels_a = {r.name: r for r in ont_a.all_relationships}
    rels_b = {r.name: r for r in ont_b.all_relationships}

    for name in set(rels_b) - set(rels_a):
        r = rels_b[name]
        result.changes.append(DiffEntry(
            kind="relationship", action="added", name=name,
            details=f"{r.from_entity} -> {r.to_entity}",
        ))

    for name in set(rels_a) - set(rels_b):
        result.changes.append(DiffEntry(
            kind="relationship", action="removed", name=name,
        ))

    for name in set(rels_a) & set(rels_b):
        diffs = _diff_relationship(rels_a[name], rels_b[name])
        if diffs:
            result.changes.append(DiffEntry(
                kind="relationship", action="modified", name=name,
                details="; ".join(diffs),
            ))

    # Rules
    rules_a = {r.name: r for r in ont_a.all_rules}
    rules_b = {r.name: r for r in ont_b.all_rules}

    for name in set(rules_b) - set(rules_a):
        result.changes.append(DiffEntry(
            kind="rule", action="added", name=name,
        ))

    for name in set(rules_a) - set(rules_b):
        result.changes.append(DiffEntry(
            kind="rule", action="removed", name=name,
        ))

    for name in set(rules_a) & set(rules_b):
        diffs = _diff_rule(rules_a[name], rules_b[name])
        if diffs:
            result.changes.append(DiffEntry(
                kind="rule", action="modified", name=name,
                details="; ".join(diffs),
            ))

    # Taxonomies
    tax_a = {t.name for t in ont_a.taxonomies}
    tax_b = {t.name for t in ont_b.taxonomies}

    for name in tax_b - tax_a:
        result.changes.append(DiffEntry(
            kind="taxonomy", action="added", name=name,
        ))
    for name in tax_a - tax_b:
        result.changes.append(DiffEntry(
            kind="taxonomy", action="removed", name=name,
        ))

    # Glossary
    terms_a = {e.term for e in ont_a.all_glossary_entries}
    terms_b = {e.term for e in ont_b.all_glossary_entries}

    for term in terms_b - terms_a:
        result.changes.append(DiffEntry(
            kind="glossary", action="added", name=term,
        ))
    for term in terms_a - terms_b:
        result.changes.append(DiffEntry(
            kind="glossary", action="removed", name=term,
        ))

    # Decisions
    decs_a = {d.heading for d in ont_a.all_decisions}
    decs_b = {d.heading for d in ont_b.all_decisions}

    for name in decs_b - decs_a:
        result.changes.append(DiffEntry(
            kind="decision", action="added", name=name,
        ))
    for name in decs_a - decs_b:
        result.changes.append(DiffEntry(
            kind="decision", action="removed", name=name,
        ))

    return result


def diff_paths(path_a: str | Path, path_b: str | Path) -> OntologyDiff:
    """Compare two ontology directories."""
    ont_a = parse_ontology(path_a)
    ont_b = parse_ontology(path_b)
    return diff_ontologies(ont_a, ont_b)


# ── Internal diff helpers ─────────────────────────────────────

def _diff_entity(a, b) -> list[str]:
    """Find differences between two entities."""
    diffs = []
    if a.description != b.description:
        diffs.append("description changed")
    if a.status != b.status:
        diffs.append(f"status: {a.status or 'unset'} -> {b.status or 'unset'}")

    attrs_a = {attr.name for attr in a.attributes}
    attrs_b = {attr.name for attr in b.attributes}
    added = attrs_b - attrs_a
    removed = attrs_a - attrs_b
    if added:
        diffs.append(f"attributes added: {', '.join(sorted(added))}")
    if removed:
        diffs.append(f"attributes removed: {', '.join(sorted(removed))}")

    if a.notes != b.notes:
        diffs.append("notes changed")
    if a.identity != b.identity:
        diffs.append("identity changed")
    if a.lifecycle != b.lifecycle:
        diffs.append("lifecycle changed")

    return diffs


def _diff_relationship(a, b) -> list[str]:
    diffs = []
    if a.from_entity != b.from_entity or a.to_entity != b.to_entity:
        diffs.append(
            f"endpoints: {a.from_entity}->{a.to_entity} "
            f"to {b.from_entity}->{b.to_entity}"
        )
    if a.cardinality != b.cardinality:
        diffs.append(f"cardinality: {a.cardinality} -> {b.cardinality}")
    if a.description != b.description:
        diffs.append("description changed")
    return diffs


def _diff_rule(a, b) -> list[str]:
    diffs = []
    if a.applies_to != b.applies_to:
        diffs.append(f"applies_to: {a.applies_to} -> {b.applies_to}")
    if a.severity != b.severity:
        diffs.append(f"severity: {a.severity} -> {b.severity}")
    if a.condition != b.condition:
        diffs.append("condition changed")
    if a.action != b.action:
        diffs.append("action changed")
    if a.prose != b.prose:
        diffs.append("prose changed")
    return diffs
