"""
View scope resolution helpers.

Supports both explicit structured references (e.g., `HAS_SUBSCRIPTION`)
and prose placeholders (e.g., `All relationships and traversals`).
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from .models import Ontology, View


@dataclass
class ViewScope:
    """Resolved object scopes for a view."""
    entity_names: set[str]
    relationship_names: set[str] | None
    traversal_names: set[str] | None
    rule_names: set[str] | None


def normalize_view_reference(entry: str) -> str:
    """Extract object name from list entries like `Entity (all)`."""
    clean = entry.strip()
    if not clean:
        return clean
    clean = clean.split("(", 1)[0].strip()
    clean = clean.split(":", 1)[0].strip()
    lower = clean.lower()
    if not lower.startswith("all "):
        for suffix in (" traversal", " relationship", " rule"):
            if lower.endswith(suffix):
                clean = clean[: -len(suffix)].strip()
                break
    return clean


def is_entity_placeholder(entry: str) -> bool:
    phrase = _phrase(entry)
    return phrase.startswith("all entities")


def is_relationship_placeholder(entry: str, ontology: Ontology) -> bool:
    phrase = _phrase(entry)
    if phrase in {
        "all relationships",
        "all traversals",
        "all traversal",
        "all relationships and traversals",
        "all traversals and relationships",
    }:
        return True

    group = _extract_group(phrase, "relationships")
    if group:
        return len(_resolve_relationship_group(ontology, group)) > 0
    return False


def is_rule_placeholder(entry: str, ontology: Ontology) -> bool:
    phrase = _phrase(entry)
    if phrase in {"all rules", "all rule"}:
        return True

    group = _extract_group(phrase, "rules")
    if group:
        return len(_resolve_rule_group(ontology, group)) > 0
    return False


def resolve_view_scope(ontology: Ontology, view: View) -> ViewScope:
    """Resolve view prose placeholders and explicit names into concrete sets."""
    entity_names = {e.name for e in ontology.entities}
    relationship_names_all = {r.name for r in ontology.all_relationships}
    traversal_names_all = {t.name for t in ontology.all_traversals}
    rule_names_all = {r.name for r in ontology.all_rules}

    # Entities
    if not view.entities or any(is_entity_placeholder(e) for e in view.entities):
        scoped_entities = set(entity_names)
    else:
        scoped_entities = {
            normalize_view_reference(e)
            for e in view.entities
            if normalize_view_reference(e) in entity_names
        }

    # Relationships + Traversals
    scoped_relationships: set[str] = set()
    scoped_traversals: set[str] = set()
    has_relationship_directive = False
    has_traversal_directive = False
    for entry in view.relationships:
        phrase = _phrase(entry)
        symbol = normalize_view_reference(entry)

        if phrase in {"all relationships and traversals", "all traversals and relationships"}:
            scoped_relationships.update(relationship_names_all)
            scoped_traversals.update(traversal_names_all)
            has_relationship_directive = True
            has_traversal_directive = True
            continue

        if phrase == "all relationships":
            scoped_relationships.update(relationship_names_all)
            has_relationship_directive = True
            continue

        if phrase in {"all traversals", "all traversal"}:
            scoped_traversals.update(traversal_names_all)
            has_traversal_directive = True
            continue

        group = _extract_group(phrase, "relationships")
        if group:
            scoped_relationships.update(_resolve_relationship_group(ontology, group))
            has_relationship_directive = True
            continue

        if symbol in relationship_names_all:
            scoped_relationships.add(symbol)
            has_relationship_directive = True
            continue
        if symbol in traversal_names_all:
            scoped_traversals.add(symbol)
            has_traversal_directive = True
            continue

    relationship_scope = scoped_relationships if has_relationship_directive else None
    traversal_scope = scoped_traversals if has_traversal_directive else None

    # Rules
    scoped_rules: set[str] = set()
    has_rule_directive = False
    for entry in view.rules:
        phrase = _phrase(entry)
        symbol = normalize_view_reference(entry)

        if phrase in {"all rules", "all rule"}:
            scoped_rules.update(rule_names_all)
            has_rule_directive = True
            continue

        group = _extract_group(phrase, "rules")
        if group:
            scoped_rules.update(_resolve_rule_group(ontology, group))
            has_rule_directive = True
            continue

        if symbol in rule_names_all:
            scoped_rules.add(symbol)
            has_rule_directive = True

    rule_scope = scoped_rules if has_rule_directive else None

    return ViewScope(
        entity_names=scoped_entities,
        relationship_names=relationship_scope,
        traversal_names=traversal_scope,
        rule_names=rule_scope,
    )


def _phrase(entry: str) -> str:
    return re.sub(r"\s+", " ", entry.strip().lower())


def _extract_group(phrase: str, suffix: str) -> str:
    # "all scoring rules" -> "scoring"
    m = re.match(rf"^all (.+) {suffix}$", phrase)
    if not m:
        return ""
    group = m.group(1).strip()
    if group in {"", "all"}:
        return ""
    return group


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _token_match(group: str, candidate: str) -> bool:
    group_tokens = _tokenize(group)
    if not group_tokens:
        return False
    candidate_tokens = set(_tokenize(candidate))
    return all(tok in candidate_tokens for tok in group_tokens)


def _resolve_relationship_group(ontology: Ontology, group: str) -> set[str]:
    names: set[str] = set()
    for rf in ontology.relationship_files:
        domain = rf.domain or ""
        source_name = rf.source_file.stem if rf.source_file else ""
        if _token_match(group, domain) or _token_match(group, source_name):
            names.update(r.name for r in rf.relationships)
    return names


def _resolve_rule_group(ontology: Ontology, group: str) -> set[str]:
    names: set[str] = set()
    for rf in ontology.rule_files:
        domain = rf.domain or ""
        source_name = rf.source_file.stem if rf.source_file else ""
        if _token_match(group, domain) or _token_match(group, source_name):
            names.update(r.name for r in rf.rules)
    return names

