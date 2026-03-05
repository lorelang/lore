"""
AGENTS.md Compiler.

Generates an AGENTS.md-compliant file from an ontology, following
the emerging standard (Linux Foundation AAIF) for agent capability
descriptions.
"""
from __future__ import annotations

from typing import Optional
from ..models import Ontology, View
from ..view_scope import resolve_view_scope


def compile_agents_md(ontology: Ontology, view_name: Optional[str] = None) -> str:
    """
    Compile ontology to AGENTS.md format.

    Includes YAML frontmatter, domain knowledge, rules,
    relationships, and key questions (from view if specified).
    """
    lines: list[str] = []
    name = ontology.manifest.name if ontology.manifest else "domain"
    version = ontology.manifest.version if ontology.manifest else ""
    desc = ontology.manifest.description if ontology.manifest else ""

    # Find view if specified
    view: Optional[View] = None
    if view_name:
        for v in ontology.views:
            if v.name.lower() == view_name.lower():
                view = v
                break

    scope = resolve_view_scope(ontology, view) if view else None
    in_scope_entities = (
        set(scope.entity_names)
        if scope
        else {e.name for e in ontology.entities}
    )

    # YAML frontmatter
    lines.append("---")
    lines.append(f"name: {name}")
    if version:
        lines.append(f"version: {version}")
    if desc:
        lines.append(f"description: >")
        lines.append(f"  {desc.strip()}")
    if view:
        lines.append(f"scope: {view.name}")
    lines.append("---")
    lines.append("")

    # Domain Knowledge section
    lines.append("# Domain Knowledge")
    lines.append("")
    if desc:
        lines.append(desc.strip())
        lines.append("")

    # Entity descriptions
    for entity in ontology.entities:
        if entity.name not in in_scope_entities:
            continue
        lines.append(f"## {entity.name}")
        lines.append("")
        if entity.description:
            lines.append(entity.description.strip())
            lines.append("")
        if entity.attributes:
            lines.append("**Attributes:**")
            for attr in entity.attributes:
                type_str = attr.type
                if attr.type == "enum" and attr.enum_values:
                    type_str = f"enum ({', '.join(attr.enum_values)})"
                if attr.reference_to:
                    type_str = f"reference to {attr.reference_to}"
                lines.append(f"- `{attr.name}`: {type_str}")
            lines.append("")
        if entity.notes:
            lines.append(entity.notes.strip())
            lines.append("")

    # Glossary
    if ontology.glossary and ontology.glossary.entries:
        lines.append("## Glossary")
        lines.append("")
        for entry in ontology.glossary.entries:
            lines.append(f"- **{entry.term}**: {entry.definition}")
        lines.append("")

    # Rules section
    rules = ontology.all_rules
    if scope and scope.rule_names is not None:
        rules = [r for r in rules if r.name in scope.rule_names]
    elif view and in_scope_entities:
        rules = [r for r in rules
                 if not r.applies_to or r.applies_to in in_scope_entities]

    if rules:
        lines.append("# Rules")
        lines.append("")
        for rule in rules:
            if rule.severity == "critical":
                prefix = "MUST"
            elif rule.severity == "warning":
                prefix = "SHOULD"
            else:
                prefix = "MAY"

            rule_desc = rule.action or rule.condition or rule.prose
            if rule_desc:
                lines.append(f"- **{prefix}**: {rule.name} — {rule_desc.strip()}")
            else:
                lines.append(f"- **{prefix}**: {rule.name}")
        lines.append("")

    # Relationships section
    rels = ontology.all_relationships
    if scope and scope.relationship_names is not None:
        rels = [r for r in rels if r.name in scope.relationship_names]
    elif view and in_scope_entities:
        rels = [r for r in rels
                if r.from_entity in in_scope_entities
                or r.to_entity in in_scope_entities]

    if rels:
        lines.append("# Relationships")
        lines.append("")
        for rel in rels:
            lines.append(
                f"- **{rel.name}**: {rel.from_entity} → {rel.to_entity}"
                f" ({rel.cardinality})"
            )
            if rel.description:
                lines.append(f"  {rel.description.strip()}")
        lines.append("")

    # Decisions
    if ontology.decision_files:
        decisions = ontology.all_decisions
        if decisions:
            lines.append("# Decisions")
            lines.append("")
            for dec in decisions:
                lines.append(f"## {dec.heading}")
                lines.append("")
                if dec.resolution:
                    lines.append(f"**Resolution:** {dec.resolution.strip()}")
                    lines.append("")
                if dec.context:
                    first_sentence = dec.context.strip().split(". ")[0]
                    lines.append(f"> {first_sentence}.")
                    lines.append("")
                if dec.affects:
                    lines.append(f"Affects: {', '.join(dec.affects)}")
                    lines.append("")

    # Key Questions (from view)
    if view and view.key_questions:
        lines.append("# Key Questions")
        lines.append("")
        for q in view.key_questions:
            lines.append(f"- {q}")
        lines.append("")

    return "\n".join(lines)
