"""
Agent Context Compiler.

Generates a structured system prompt / context document that gives
an AI agent complete understanding of the domain ontology. This is
what makes the agent "ontology-aware" — it can reason about entities,
relationships, rules, and glossary terms because they're in its context.
"""
from __future__ import annotations
import re
from ..models import Ontology, View, TaxonomyNode
from typing import Optional
from ..view_scope import resolve_view_scope


def compile_agent_context(ontology: Ontology, view_name: Optional[str] = None) -> str:
    """
    Compile ontology to an AI agent context document.

    If view_name is provided, scopes the context to that view.
    Otherwise, includes the full ontology.
    """
    lines: list[str] = []
    name = ontology.manifest.name if ontology.manifest else "domain"
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

    lines.append(f"<domain_ontology>")
    lines.append(f"<overview>")
    lines.append(f"Domain: {name}")
    if desc:
        lines.append(f"Description: {desc}")
    if view:
        lines.append(f"Scoped to view: {view.name}")
        lines.append(f"Audience: {view.audience}")
        if view.description:
            lines.append(f"View purpose: {view.description}")
    lines.append("Interpretation mode: unstructured-first")
    lines.append(f"</overview>")
    lines.append("")

    lines.append("<agent_guidance>")
    lines.append("Treat this ontology as narrative domain knowledge first, schema second.")
    lines.append("Prioritize prose sections (notes, lifecycle, observations, outcomes) when reasoning.")
    lines.append("Use structured fields (types, constraints, traversals) as guardrails, not as the sole truth source.")
    lines.append("When claims conflict, weigh recency, confidence, and precedents before deciding.")
    lines.append("</agent_guidance>")
    lines.append("")

    # Entities
    lines.append("<entities>")
    for entity in ontology.entities:
        # If view is specified, check if entity is in scope
        if view and entity.name not in in_scope_entities:
            continue

        lines.append(f"<entity name=\"{entity.name}\">")
        if entity.status:
            lines.append(f"  Status: {entity.status}")
        if entity.provenance:
            prov_parts = []
            if entity.provenance.source:
                prov_parts.append(f"source={entity.provenance.source}")
            if entity.provenance.confidence is not None:
                prov_parts.append(f"confidence={entity.provenance.confidence}")
            if entity.provenance.author:
                prov_parts.append(f"author={entity.provenance.author}")
            if entity.provenance.created:
                prov_parts.append(f"created={entity.provenance.created}")
            if prov_parts:
                lines.append(f"  Provenance: {', '.join(prov_parts)}")
        if entity.description:
            lines.append(f"  {entity.description}")
        if entity.inherits:
            lines.append(f"  Inherits from: {entity.inherits}")
        lines.append("")

        if entity.attributes:
            lines.append("  Attributes:")
            for attr in entity.attributes:
                type_str = attr.type
                if attr.type == "enum" and attr.enum_values:
                    type_str = f"enum [{', '.join(attr.enum_values)}]"
                if attr.reference_to:
                    type_str = f"reference to {attr.reference_to}"
                constraint_str = f" [{', '.join(attr.constraints)}]" if attr.constraints else ""
                lines.append(f"    - {attr.name}: {type_str}{constraint_str}")
                if attr.description:
                    lines.append(f"      {attr.description}")
            lines.append("")

        if entity.identity:
            lines.append(f"  Identity: {entity.identity}")
            lines.append("")

        if entity.lifecycle:
            lines.append(f"  Lifecycle: {entity.lifecycle}")
            lines.append("")

        if entity.notes:
            lines.append(f"  Notes: {entity.notes}")
            lines.append("")

        lines.append(f"</entity>")
        lines.append("")

    lines.append("</entities>")
    lines.append("")

    # Relationships
    lines.append("<relationships>")
    relationship_scope = scope.relationship_names if scope else None
    traversal_scope = scope.traversal_names if scope else None

    for rel in ontology.all_relationships:
        if view:
            if relationship_scope is not None:
                if rel.name not in relationship_scope:
                    continue
            elif in_scope_entities:
                if rel.from_entity not in in_scope_entities and rel.to_entity not in in_scope_entities:
                    continue

        lines.append(
            f"  {rel.from_entity} -[{rel.name}]-> {rel.to_entity} "
            f"({rel.cardinality})"
        )
        if rel.description:
            lines.append(f"    {rel.description}")
        if rel.properties:
            props = ", ".join(f"{p.name}: {p.type}" for p in rel.properties)
            lines.append(f"    Properties: {props}")
    lines.append("</relationships>")
    lines.append("")

    # Traversals (reasoning paths)
    lines.append("<traversals>")
    lines.append("These are valid multi-hop reasoning paths in this domain:")
    lines.append("")
    for trav in ontology.all_traversals:
        if view:
            include = True
            if traversal_scope is not None:
                include = trav.name in traversal_scope
                if not include and relationship_scope is not None:
                    rel_refs = set(re.findall(r"\[([^\]]+)\]", trav.path))
                    rel_tokens = {r.strip() for r in rel_refs if "=" not in r}
                    include = bool(rel_tokens & relationship_scope)
            elif relationship_scope is not None:
                rel_refs = set(re.findall(r"\[([^\]]+)\]", trav.path))
                rel_tokens = {r.strip() for r in rel_refs if "=" not in r}
                include = bool(rel_tokens & relationship_scope)
            elif in_scope_entities:
                include = any(entity in trav.path for entity in in_scope_entities)

            if not include:
                continue
        lines.append(f"  {trav.name}:")
        lines.append(f"    Path: {trav.path}")
        if trav.description:
            lines.append(f"    Use: {trav.description}")
        lines.append("")
    lines.append("</traversals>")
    lines.append("")

    # Rules
    lines.append("<rules>")
    rule_scope = scope.rule_names if scope else None

    for rule in ontology.all_rules:
        if view:
            if rule_scope is not None:
                if rule.name not in rule_scope:
                    continue
            elif rule.applies_to and in_scope_entities and rule.applies_to not in in_scope_entities:
                continue

        lines.append(f"<rule name=\"{rule.name}\">")
        if rule.applies_to:
            lines.append(f"  Applies to: {rule.applies_to}")
        if rule.severity:
            lines.append(f"  Severity: {rule.severity}")
        if rule.trigger:
            lines.append(f"  Trigger: {rule.trigger}")
        if rule.outputs:
            lines.append(f"  Computes: {rule.outputs}")
        if rule.condition:
            lines.append(f"  Condition: {rule.condition}")
        if rule.action:
            lines.append(f"  Action: {rule.action}")
        if rule.prose:
            lines.append(f"  Context: {rule.prose}")
        lines.append(f"</rule>")
        lines.append("")

    lines.append("</rules>")
    lines.append("")

    # Taxonomies
    if ontology.taxonomies:
        lines.append("<taxonomies>")
        for tax in ontology.taxonomies:
            lines.append(f"<taxonomy name=\"{tax.name}\" applied_to=\"{tax.applied_to}\">")
            if tax.root:
                _render_taxonomy_text(tax.root, lines, indent=2)
            if tax.inheritance_rules:
                lines.append(f"  Inheritance rules: {tax.inheritance_rules}")
            lines.append(f"</taxonomy>")
            lines.append("")
        lines.append("</taxonomies>")
        lines.append("")

    # Glossary
    if ontology.glossary and ontology.glossary.entries:
        lines.append("<glossary>")
        lines.append("Canonical definitions — use these when interpreting user queries:")
        lines.append("")
        for entry in ontology.glossary.entries:
            lines.append(f"  {entry.term}: {entry.definition}")
            lines.append("")
        lines.append("</glossary>")
        lines.append("")

    # Observations — with conflict detection
    if ontology.observation_files:
        # Detect conflicts: observations about the same entity with opposing signals
        conflicting_obs = _detect_observation_conflicts(ontology)

        lines.append("<observations>")
        lines.append("Field notes from AI agents and domain experts:")
        lines.append("")
        for of in ontology.observation_files:
            if view and of.about and of.about not in in_scope_entities:
                continue
            meta_parts = []
            if of.observed_by:
                meta_parts.append(f"by {of.observed_by}")
            if of.date:
                meta_parts.append(f"on {of.date}")
            if of.confidence is not None:
                meta_parts.append(f"confidence={of.confidence}")
            if of.about:
                meta_parts.append(f"about {of.about}")
            meta = f" ({', '.join(meta_parts)})" if meta_parts else ""
            for obs in of.observations:
                source_key = str(of.source_file) if of.source_file else of.name
                obs_key = (of.about, source_key, obs.heading)
                if obs_key in conflicting_obs:
                    lines.append(f"  <observation conflict=\"true\">{obs.heading}{meta}")
                    lines.append(f"    {obs.prose}")
                    if obs.claims:
                        lines.append("    Claims:")
                        for claim in obs.claims:
                            lines.append(f"      - {claim.kind}: {claim.text}")
                    for contradiction in conflicting_obs[obs_key]:
                        lines.append(f"    [CONFLICT: {contradiction}]")
                    lines.append(f"  </observation>")
                else:
                    lines.append(f"  <observation>{obs.heading}{meta}")
                    lines.append(f"    {obs.prose}")
                    if obs.claims:
                        lines.append("    Claims:")
                        for claim in obs.claims:
                            lines.append(f"      - {claim.kind}: {claim.text}")
                    lines.append(f"  </observation>")
                lines.append("")
        lines.append("</observations>")
        lines.append("")

    # Outcomes
    if ontology.outcome_files:
        lines.append("<outcomes>")
        lines.append("Retrospectives comparing predictions to reality:")
        lines.append("")
        for of in ontology.outcome_files:
            meta_parts = []
            if of.reviewed_by:
                meta_parts.append(f"by {of.reviewed_by}")
            if of.date:
                meta_parts.append(f"on {of.date}")
            meta = f" ({', '.join(meta_parts)})" if meta_parts else ""
            for outcome in of.outcomes:
                lines.append(f"  <outcome>{outcome.heading}{meta}")
                lines.append(f"    {outcome.prose}")
                if outcome.takeaways:
                    for t in outcome.takeaways:
                        lines.append(f"    Takeaway: {t}")
                lines.append(f"  </outcome>")
                lines.append("")
        lines.append("</outcomes>")
        lines.append("")

    # Key questions (from view)
    if view and view.key_questions:
        lines.append("<key_questions>")
        lines.append("This view is designed to answer these types of questions:")
        for q in view.key_questions:
            lines.append(f"  - {q}")
        lines.append("</key_questions>")
        lines.append("")

    lines.append("</domain_ontology>")

    return "\n".join(lines)


def _detect_observation_conflicts(ontology: Ontology) -> dict[tuple[str, str, str], list[str]]:
    """
    Detect contradicting observations about the same entity.

    Returns a dict mapping (about, source_key, heading) to a list of
    contradiction descriptions.
    """
    _POSITIVE = {
        "expansion", "growth", "increase", "uptick", "readiness",
        "adoption", "engagement", "upgrade", "upsell", "healthy",
        "renewed", "active", "improving", "positive",
    }
    _NEGATIVE = {
        "churn", "decline", "decrease", "contraction", "risk",
        "disengagement", "downgrade", "cancellation", "inactive",
        "deteriorating", "negative", "attrition", "drop", "loss",
    }

    # Group observations by entity
    obs_by_entity: dict[str, list[dict]] = {}
    for of in ontology.observation_files:
        if of.about:
            for obs in of.observations:
                source_key = str(of.source_file) if of.source_file else of.name
                obs_by_entity.setdefault(of.about, []).append({
                    "about": of.about,
                    "heading": obs.heading,
                    "text": (obs.heading + " " + obs.prose).lower(),
                    "source_key": source_key,
                    "observed_by": of.observed_by,
                    "date": of.date,
                    "confidence": of.confidence,
                })

    conflicts: dict[tuple[str, str, str], list[str]] = {}
    for entity, obs_list in obs_by_entity.items():
        if len(obs_list) < 2:
            continue
        for i in range(len(obs_list)):
            for j in range(i + 1, len(obs_list)):
                o1 = obs_list[i]
                o2 = obs_list[j]
                text1 = o1["text"]
                text2 = o2["text"]
                pos1 = any(s in text1 for s in _POSITIVE)
                neg1 = any(s in text1 for s in _NEGATIVE)
                pos2 = any(s in text2 for s in _POSITIVE)
                neg2 = any(s in text2 for s in _NEGATIVE)
                if (pos1 and not neg1 and neg2 and not pos2) or \
                   (neg1 and not pos1 and pos2 and not neg2):
                    k1 = (entity, o1["source_key"], o1["heading"])
                    k2 = (entity, o2["source_key"], o2["heading"])

                    details_1 = (
                        f"This observation conflicts with '{o2['heading']}' "
                        f"({_render_observation_meta(o2)}). "
                        "Consider recency and confidence before acting."
                    )
                    details_2 = (
                        f"This observation conflicts with '{o1['heading']}' "
                        f"({_render_observation_meta(o1)}). "
                        "Consider recency and confidence before acting."
                    )
                    conflicts.setdefault(k1, []).append(details_1)
                    conflicts.setdefault(k2, []).append(details_2)

    return conflicts


def _render_observation_meta(record: dict) -> str:
    parts = []
    if record.get("observed_by"):
        parts.append(f"by {record['observed_by']}")
    if record.get("date"):
        parts.append(f"on {record['date']}")
    if record.get("confidence") is not None:
        parts.append(f"confidence={record['confidence']}")
    return ", ".join(parts) if parts else "no metadata"


def _render_taxonomy_text(node: TaxonomyNode, lines: list[str], indent: int = 0):
    """Render taxonomy tree as indented text."""
    prefix = " " * indent
    tag_str = f" [tags: {', '.join(node.tags)}]" if node.tags else ""
    desc_str = f" — {node.description}" if node.description else ""
    lines.append(f"{prefix}{node.name}{tag_str}{desc_str}")
    for child in node.children:
        _render_taxonomy_text(child, lines, indent + 2)
